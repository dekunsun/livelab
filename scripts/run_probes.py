"""Run the pre-registered UNKNOWN probes (docs/probe_preregistration.md) on Gemini 3.8 Live.

  ./.venv/bin/python scripts/run_probes.py             # all variants; resumes, skipping finished items
  ./.venv/bin/python scripts/run_probes.py --only B0 --limit 2    # a cheap smoke test

Each answer is saved to results/probes/<model>/<variant>/<item_id>.json as soon as it arrives.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import (PROBE_VERSION, p1_message, p1_setup, prefix_message, run_single_turn,  # noqa: E402
                            variant_setup)

MODELS = {"gemini": "gemini-3.8-live", "gemini-extended": "gemini-3.8-live-extended-thinking"}
VARIANTS = ["P1", "B0", "B1", "B2", "B3"]
RETRY_WAIT_S = 30


def real_connect(model):
    import os
    from google import genai
    load_dotenv()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("Set GEMINI_API_KEY in livelab/.env (never commit it).")
    client = genai.Client()
    return lambda cfg: client.aio.live.connect(model=model, config=cfg)


def jobs(items, only):
    for v in VARIANTS:
        if only and v not in only:
            continue
        if v == "P1":
            for it in items["p1"]:
                yield v, it["item_id"], (*p1_setup(it), p1_message(it))
        else:
            for it in items["in_context"]:
                yield v, it["item_id"], (*variant_setup(v), prefix_message(it["replay_id"], it["k"]))


async def main(connect=None, out_root=None, argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=VARIANTS)
    ap.add_argument("--limit", type=int, help="at most this many items per variant (smoke test)")
    ap.add_argument("--backend", default="gemini", choices=sorted(MODELS))
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    out_root = out_root or ROOT / "results" / "probes" / model
    items = json.load(open(ROOT / "data/probes/items.json"))
    connect = connect or real_connect(model)
    per_variant, failures = {}, 0
    for v, item_id, (instruction, tools, required, text) in jobs(items, args.only):
        if args.limit and per_variant.get(v, 0) >= args.limit:
            continue
        per_variant[v] = per_variant.get(v, 0) + 1
        out = Path(out_root) / v / f"{item_id}.json"
        if out.exists():
            continue
        for attempt in range(3):
            try:
                res = await asyncio.wait_for(run_single_turn(connect, instruction, tools, required, text, model_id=model,
                                                             thinking_level="HIGH" if "extended" in model else None), 600)
                break
            except Exception as exc:  # noqa: BLE001 - free-tier transient errors; retry the whole item
                print(f"{v} {item_id} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:120]}")
                res = None
                await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
        if res is None:
            failures += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"probe_version": PROBE_VERSION, "model": model,
                                   "thinking_level": "HIGH" if "extended" in model else None, "variant": v,
                                   "item_id": item_id, **res}, indent=1))
        names = [c["name"] for c in res["calls"]]
        print(f"{v} {item_id}: {names} reminders={res['reminders']}")
    print(f"done; {failures} item(s) failed and can be retried by rerunning the same command")


if __name__ == "__main__":
    asyncio.run(main())
