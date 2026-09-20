"""Run the undersampling study (docs/undersampling_preregistration.md).

Each item is one comparison window at one cadence, asked as a single turn under the frozen v4
wording — B2's added definition is deliberately not used, because this study measures the default
contract. Answers land in results/transients/<model>/<item_id>.json.

  ./.venv/bin/python scripts/run_transients.py --backend gemini
  ./.venv/bin/python scripts/run_transients.py --backend opus-5 --limit 3
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
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import CONTROL_FOR, MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

RETRY_WAIT_S = 20


async def main(ask=None, out_root=None, argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="gemini", choices=sorted(MODELS))
    ap.add_argument("--limit", type=int, help="at most this many items (smoke test)")
    ap.add_argument("--cadence", type=int, nargs="*", help="only these cadences")
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    thinking = "HIGH" if "extended" in model else None
    out_root = Path(out_root or ROOT / "results" / "transients" / model)
    items = json.load(open(ROOT / "data/transients/items.json"))["items"]
    if args.cadence:
        items = [i for i in items if i["cadence_s"] in args.cadence]
    items = items[:args.limit] if args.limit else items

    if ask is None:
        if model in PROVIDER:
            load_dotenv()
            provider = PROVIDER[model]
            env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
            if not os.environ.get(env):
                sys.exit(f"Set {env} in livelab/.env (never commit it).")
            asker = StandardAsker(provider, model)
            ask = lambda i, t, r, x: asker(i, t, r, x)          # noqa: E731
        else:
            connect = real_connect(model)
            ask = lambda i, t, r, x: run_single_turn(           # noqa: E731
                connect, i, t, r, x, model_id=model, thinking_level=thinking, patience=PATIENCE_S)

    instruction, tools, required = variant_setup("B0")
    done = failed = 0
    for it in items:
        out = out_root / f"{it['item_id']}.json"
        if out.exists():
            continue
        res = None
        for attempt in range(3):
            try:
                res = await asyncio.wait_for(ask(instruction, tools, required, it["prefix"]), 600)
            except Exception as exc:  # noqa: BLE001 - provider errors are retried, never saved
                print(f"{it['item_id']} attempt {attempt + 1} failed: {type(exc).__name__}: "
                      f"{str(exc)[:110]}", flush=True)
                await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
                res = None
                continue
            if [r for r in required if r not in {c["name"] for c in res["calls"]}]:
                print(f"{it['item_id']} attempt {attempt + 1}: no answer", flush=True)
                res = None
                continue
            break
        if res is None:
            failed += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        answer = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1]
        out.write_text(json.dumps({"model": model, **{k: it[k] for k in
                                   ("item_id", "episode", "fault_type", "duration_s", "cadence_s",
                                    "events", "class", "supported")},
                                   "calls": res["calls"], "spoken": res["spoken"],
                                   "usage": res["usage"]}, indent=1))
        done += 1
        print(f"{it['item_id']:52} {it['class']:9} -> {answer.get('execution_state')}", flush=True)
    print(f"done; {done} answered, {failed} without an answer")


if __name__ == "__main__":
    asyncio.run(main())
