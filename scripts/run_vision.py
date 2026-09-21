"""Run the camera-compensation study (docs/vision_preregistration.md).

Each item runs twice and is its own control: the same telemetry text, then the same text plus six
frames from the plant's own camera over the same window.

  ./.venv/bin/python scripts/run_vision.py --backend opus-5 [--arm frames] [--limit 2]
"""
import argparse
import asyncio
import json
import os
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


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="opus-5", choices=sorted(MODELS))
    ap.add_argument("--arm", nargs="*", default=["telemetry", "frames"],
                    choices=["telemetry", "frames"])
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

        async def ask(text, frames):
            return await asker(SYSTEM_INSTRUCTION + (SEEN if frames else ""), tools, required,
                               text, images=frames)
    else:
        connect = real_connect(model)

        async def ask(text, frames):
            blobs = [("image/jpeg", Path(f).read_bytes()) for f in frames]
            return await run_single_turn(connect, SYSTEM_INSTRUCTION + (SEEN if frames else ""),
                                         tools, required, text, model_id=model,
                                         patience=PATIENCE_S, images=blobs)

    _, tools, required = variant_setup("B0")
    done = failed = 0
    for n, it in enumerate(items, 1):
        for arm in args.arm:
            out = out_root / arm / f"{it['item_id']}.json"
            if out.exists():
                continue
            frames = [str(VISION / f) for f in it["frames"]] if arm == "frames" else []
            res = None
            for attempt in range(3):
                try:
                    res = await asyncio.wait_for(ask(it["prefix"], frames), 900)
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
            a = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"model": model, "arm": arm,
                                       **{k: it[k] for k in ("item_id", "condition", "supported",
                                                             "observing_sensor", "removed_group",
                                                             "decision_time")},
                                       "frames": it["frames"] if frames else [],
                                       "calls": res["calls"], "spoken": res["spoken"],
                                       "usage": res["usage"]}, indent=1))
            done += 1
            print(f"[{n}/{len(items)}] {arm:9} {it['condition']:7} 应为 {it['supported']:9} -> "
                  f"{a.get('execution_state')}", flush=True)
    print(f"done; {done} answered, {failed} without an answer")


if __name__ == "__main__":
    asyncio.run(main())
