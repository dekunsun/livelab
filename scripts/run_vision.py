"""Run the camera-compensation study (docs/vision_preregistration.md).

Each item runs twice and is its own control: the same telemetry text, then the same text plus six
frames from the plant's own camera over the same window.

  ./.venv/bin/python scripts/run_vision.py --backend opus-5 [--arm frames] [--limit 2]
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import run_single_turn, variant_setup  # noqa: E402
from livelab.realdata_prompt import SYSTEM_INSTRUCTION  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

VISION = ROOT / "data/vision"
RETRY_WAIT_S = 20
SEEN = ("\n\nSix photographs of the column, taken by the plant's camera at even intervals across "
        "the same window, are attached in time order.")
# What each arm sends: (announce the photographs?, whose frames). The follow-up arms are registered
# in docs/vision_followup_preregistration.md.
ARMS = {"telemetry": (False, None), "frames": (True, "own"),
        "sentence": (True, None), "other_frames": (True, "donor")}
DONOR_SEED = 0


def donor_map(items, seed=DONOR_SEED):
    """item_id -> the control item whose frames it gets in the other_frames arm.

    Footage of a column running normally, never from the item's own experiment. Fixed by a seed and
    written out before the run, so the assignment cannot be chosen after seeing answers.
    """
    import random
    controls = sorted((i for i in items if i["condition"] == "control"), key=lambda i: i["item_id"])
    random.Random(seed).shuffle(controls)
    out = {}
    for k, it in enumerate(sorted(items, key=lambda i: i["item_id"])):
        for step in range(len(controls)):
            donor = controls[(k + step) % len(controls)]
            if donor["experiment"] != it["experiment"]:
                out[it["item_id"]] = donor["item_id"]
                break
    return out


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="opus-5", choices=sorted(MODELS))
    ap.add_argument("--arm", nargs="*", default=["telemetry", "frames"], choices=sorted(ARMS))
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    items = json.load(open(VISION / "items.json"))["items"]
    items = items[:args.limit] if args.limit else items
    out_root = ROOT / "results" / "vision" / model

    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)

        async def ask(text, frames, announce):
            return await asker(SYSTEM_INSTRUCTION + (SEEN if announce else ""), tools, required,
                               text, images=frames)
    else:
        connect = real_connect(model)

        async def ask(text, frames, announce):
            blobs = [("image/jpeg", Path(f).read_bytes()) for f in frames]
            return await run_single_turn(connect, SYSTEM_INSTRUCTION + (SEEN if announce else ""),
                                         tools, required, text, model_id=model,
                                         patience=PATIENCE_S, images=blobs)

    def save_request_sample(arm):
        """What this model was actually sent, once per arm, with the image bytes elided.

        The same parity evidence the probes commit. Here it also answers the question a reader
        of a null result will ask: was anything attached at all, and did the two arms differ in
        anything besides the frames?
        """
        sample = out_root / f"request_sample_{arm}.json"
        body = getattr(asker, "last_request", None) if model in PROVIDER else None
        if sample.exists() or not body:
            return
        text = json.dumps(body)
        for blob in re.findall(r'"[A-Za-z0-9+/]{200,}={0,2}"', text):
            text = text.replace(blob, f'"<{len(blob) - 2} base64 chars elided>"')
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text(json.dumps({"model": model, "arm": arm,
                                      "request": json.loads(text)}, indent=1))

    _, tools, required = variant_setup("B0")
    all_items = json.load(open(VISION / "items.json"))["items"]
    by_id = {i["item_id"]: i for i in all_items}
    donors = donor_map(all_items)
    if "other_frames" in args.arm:
        record = out_root / "other_frames_donors.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        if record.exists() and json.loads(record.read_text()) != donors:
            sys.exit("the donor assignment differs from the one recorded before the run; refusing")
        record.write_text(json.dumps(donors, indent=1))
    done = failed = 0
    for n, it in enumerate(items, 1):
        for arm in args.arm:
            out = out_root / arm / f"{it['item_id']}.json"
            if out.exists():
                continue
            announce, source = ARMS[arm]
            donor = donors[it["item_id"]] if source == "donor" else None
            frames = ([str(VISION / f) for f in it["frames"]] if source == "own" else
                      [str(VISION / f) for f in by_id[donor]["frames"]] if donor else [])
            res = None
            for attempt in range(3):
                try:
                    res = await asyncio.wait_for(ask(it["prefix"], frames, announce), 900)
                except Exception as exc:  # noqa: BLE001
                    print(f"{it['item_id'][:40]} {arm} attempt {attempt + 1} failed: "
                          f"{type(exc).__name__}: {str(exc)[:90]}", flush=True)
                    await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
                    res = None
                    continue
                if [r for r in required if r not in {c["name"] for c in res["calls"]}]:
                    print(f"{it['item_id'][:40]} {arm} attempt {attempt + 1}: no answer", flush=True)
                    res = None
                    continue
                break
            if res is None:
                failed += 1
                continue
            save_request_sample(arm)
            a = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"model": model, "arm": arm,
                                       # a control item has no removed group; .get keeps the
                                       # record shape the same across conditions
                                       **{k: it.get(k) for k in ("item_id", "condition",
                                                                 "supported", "observing_sensor",
                                                                 "removed_group", "decision_time",
                                                                 "frame_span_s")},
                                       "frames": ([str(Path(f).relative_to(VISION))
                                                   for f in frames]),
                                       "announced": announce, "donor": donor,
                                       "calls": res["calls"], "spoken": res["spoken"],
                                       "usage": res["usage"]}, indent=1))
            done += 1
            print(f"[{n}/{len(items)}] {arm:9} {it['condition']:7} 应为 {it['supported']:9} -> "
                  f"{a.get('execution_state')}", flush=True)
    print(f"done; {done} answered, {failed} without an answer")


if __name__ == "__main__":
    asyncio.run(main())
