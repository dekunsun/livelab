"""Run the real-plant replication (docs/realdata_preregistration.md).

  ./.venv/bin/python scripts/run_realdata.py --backend opus-5 [--limit 3]
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
from livelab.realdata_prompt import SYSTEM_INSTRUCTION_V1, SYSTEM_INSTRUCTION_V2  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

RETRY_WAIT_S = 20
# v1 is what the original study used, and writes where it always did; v2 is the corrected legend
# (docs/realdata_v2_preregistration.md) and writes beside it, never over it.
LEGENDS = {"v1": (SYSTEM_INSTRUCTION_V1, "realdata"), "v2": (SYSTEM_INSTRUCTION_V2, "realdata_v2")}


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="opus-5", choices=sorted(MODELS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--condition", nargs="*", choices=["full", "blind", "control"])
    ap.add_argument("--legend", default="v1", choices=sorted(LEGENDS))
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    thinking = "HIGH" if "extended" in model else None
    instruction, results_dir = LEGENDS[args.legend]
    out_root = ROOT / "results" / results_dir / model
    items = json.load(open(ROOT / "data/realdata/items.json"))["items"]
    if args.condition:
        items = [i for i in items if i["condition"] in args.condition]
    items = items[:args.limit] if args.limit else items

    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)
        ask = lambda i, t, r, x: asker(i, t, r, x)                      # noqa: E731
    else:
        connect = real_connect(model)
        ask = lambda i, t, r, x: run_single_turn(                       # noqa: E731
            connect, i, t, r, x, model_id=model, thinking_level=thinking, patience=PATIENCE_S)

    _, tools, required = variant_setup("B0")        # same schema; only the instruction is ported
    done = failed = 0
    for n, it in enumerate(items):
        key = f"{it['experiment'].replace('/', '__')}__{it['condition']}"
        out = out_root / f"{key}.json"
        if out.exists():
            continue
        res = None
        for attempt in range(3):
            try:
                res = await asyncio.wait_for(
                    ask(instruction, tools, required, it["prefix"]), 600)
            except Exception as exc:  # noqa: BLE001
                print(f"{key} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:100]}",
                      flush=True)
                await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
                res = None
                continue
            if [r for r in required if r not in {c["name"] for c in res["calls"]}]:
                print(f"{key} attempt {attempt + 1}: no answer", flush=True)
                res = None
                continue
            break
        if res is None:
            failed += 1
            continue
        a = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"model": model, "legend": args.legend, **{k: it[k] for k in
                                   ("experiment", "condition", "supported", "observing_sensor",
                                    "anomaly_label", "decision_time")},
                                   "removed": it.get("removed"), "calls": res["calls"],
                                   "spoken": res["spoken"], "usage": res["usage"]}, indent=1))
        done += 1
        print(f"[{n + 1:3}/{len(items)}] {it['condition']:7} 应为 {it['supported']:9} -> "
              f"{a.get('execution_state')}", flush=True)
    print(f"done; {done} answered, {failed} without an answer")


if __name__ == "__main__":
    asyncio.run(main())
