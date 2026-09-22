"""Run LiveLab Core (docs/core.md, docs/core_preregistration.md) on one model.

Each item is asked under the three arms back to back, so no arm is collected in different hours
from another. Answers are saved to results/core/<model>/<arm>/<item_id>.json as they arrive, and a
rerun resumes where it stopped.

  ./.venv/bin/python scripts/run_core.py --backend opus-5 --limit 2     # smoke test: 2 items x 3 arms
  ./.venv/bin/python scripts/run_core.py --backend opus-5               # the full suite: 80 x 3 calls
"""
import argparse
import asyncio
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.core import ARMS, load_items, setup_for, text_for  # noqa: E402
from livelab.probes import run_single_turn  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

OUT = ROOT / "results/core"
# USD per million tokens (input, output). Opus 5 from the vendor's page (scripts/measure_frame_tokens.py);
# Astra's output price inferred from the cross-model study's billed spend, US$5.46 for 378,014 in and 33,571 out.
PRICE = {"claude-opus-5": (5.0, 25.0), "gpt-6-astra": (10.0, 50.0)}


def spent(model):
    """Spend so far for this model, from the usage saved with each answer. None if not priced."""
    if model not in PRICE:
        return None
    pin, pout = PRICE[model]
    total = 0.0
    for f in glob.glob(str(OUT / model / "*" / "*.json")):
        u = json.loads(Path(f).read_text()).get("usage") or {}
        total += (u.get("prompt_token_count") or 0) * pin / 1e6
        total += (u.get("response_token_count") or 0) * pout / 1e6    # includes any reasoning tokens
    return total


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=sorted(MODELS))
    ap.add_argument("--arm", nargs="*", default=list(ARMS), choices=ARMS)
    ap.add_argument("--limit", type=int, help="only the first N items (smoke test)")
    ap.add_argument("--cap", type=float, default=15.0, help="stop once this model's spend passes this many USD")
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    items = load_items()[:args.limit] if args.limit else load_items()

    def ask_for(arm):
        instruction, tools, required = setup_for(arm)
        if model in PROVIDER:
            return (lambda text: asker(instruction, tools, required, text)), required  # noqa: E731
        return (lambda text: run_single_turn(connect, instruction, tools, required, text,  # noqa: E731
                                             model_id=model, patience=PATIENCE_S)), required

    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)
    else:
        connect = real_connect(model)
    askers = {arm: ask_for(arm) for arm in args.arm}

    for it in items:
        for arm in args.arm:
            dest = OUT / model / arm / f"{it['item_id']}.json"
            if dest.exists():
                continue
            cost = spent(model)
            if cost is not None and cost > args.cap:
                sys.exit(f"Spend for {model} is US${cost:.2f}, past the US${args.cap:.2f} cap. Stopped.")
            ask, required = askers[arm]
            text = text_for(it, arm)
            res = None
            for attempt in range(3):
                try:
                    got = await asyncio.wait_for(ask(text), 600)
                except Exception as exc:  # noqa: BLE001
                    print(f"  {arm} {it['item_id']} attempt {attempt + 1} failed: "
                          f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
                    await asyncio.sleep(20 * (attempt + 1))
                    continue
                if all(r in {c["name"] for c in got["calls"]} for r in required):
                    res = got
                    break
                print(f"  {arm} {it['item_id']} attempt {attempt + 1}: no answer", flush=True)
            if res is None:
                continue        # not saved: counts against coverage, and a rerun tries it again
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps({"model": model, "arm": arm, "item_id": it["item_id"],
                                        "role": it["role"], "truth": it["truth"], "text_tail": text[-400:],
                                        "calls": res["calls"], "usage": res.get("usage")}, indent=1))
            said = [c["args"] for c in res["calls"] if c["name"] == "report_assessment"][-1].get("execution_state")
            print(f"[{arm}] {it['item_id']:32} {it['role']:7} truth {it['truth']:9} -> {said}", flush=True)
    cost = spent(model)
    print("done" + (f"; spend so far US${cost:.2f}" if cost is not None else "; spend not metered for this backend"))


if __name__ == "__main__":
    asyncio.run(main())
