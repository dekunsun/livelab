"""Run LiveLab Core with runner v2 (docs/core_runner_v2.md). Same items, arms and scoring as
scripts/run_core.py; every exchange recorded; results in results/core_v2/, never over a v1 record.

  ./.venv/bin/python scripts/run_core_v2.py --backend gemini --arm V1 --limit 3      # smoke test
  ./.venv/bin/python scripts/run_core_v2.py --backend gemini-flash --arm V1 --items core_leak_lp_01__visible
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
from livelab.core import ALL_ARMS, DATA, load_items, setup_for, text_for  # noqa: E402
from livelab.runner_v2 import RUNNER_VERSION, live_item, rest_item, sha256  # noqa: E402
from livelab.standard_api import _headers, _post  # noqa: E402
from scripts.run_core import PRICE  # noqa: E402
from scripts.run_probes import MODELS, PROVIDER, real_connect  # noqa: E402

OUT = ROOT / "results/core_v2"
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def evidence_of(item):
    """What the frozen item says the model should see: the replay file itself, and the manifest."""
    replay = DATA / "replays" / f"{item['replay_id']}.jsonl"
    return {"replay_id": item["replay_id"], "replay_sha256": sha256(replay.read_bytes()), "k": item["k"],
            "missing_required": item["missing_required"]}


def spent(model):
    if model not in PRICE:
        return None
    pin, pout = PRICE[model]
    total = 0.0
    for f in glob.glob(str(OUT / model / "*" / "*.json")):
        rec = json.loads(Path(f).read_text())
        for a in [rec] + rec.get("attempts", []):
            for u in a.get("usage_messages", []):
                total += (u["usage"].get("prompt_token_count") or 0) * pin / 1e6
                total += (u["usage"].get("response_token_count") or 0) * pout / 1e6
    return total


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=sorted(MODELS))
    ap.add_argument("--arm", nargs="*", default=["V1"], choices=ALL_ARMS)
    ap.add_argument("--items", nargs="*", help="only these item ids")
    ap.add_argument("--limit", type=int, help="only the first N items")
    ap.add_argument("--remedy", choices=["fixed", "none"], default="fixed")
    ap.add_argument("--tool-choice", choices=["forced", "auto"], default="forced")
    ap.add_argument("--cap", type=float, default=5.0, help="stop once this model's v2 spend passes this many USD")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    out = Path(args.out)
    model = MODELS[args.backend]
    items = load_items()
    if args.items:
        items = [i for i in items if i["item_id"] in set(args.items)]
    if args.limit:
        items = items[:args.limit]
    load_dotenv()
    if model in PROVIDER:
        provider = PROVIDER[model]
        env = KEYS.get(provider, "OPENAI_API_KEY")
        key = os.environ.get(env) or (os.environ.get("GOOGLE_API_KEY") if provider == "gemini" else None)
        if not key:
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        headers = _headers(provider, key)          # used to send; never written anywhere
    else:
        connect = real_connect(model)
    thinking = "HIGH" if "extended" in model else None

    for it in items:
        for arm in args.arm:
            dirname = arm + (".auto" if args.tool_choice == "auto" else "") + (".noremedy" if args.remedy == "none" else "")
            dest = out / model / dirname / f"{it['item_id']}.json"
            if dest.exists():
                continue
            cost = spent(model)
            if cost is not None and cost > args.cap:
                sys.exit(f"v2 spend for {model} is US${cost:.2f}, past the US${args.cap:.2f} cap. Stopped.")
            instruction, tools, required = setup_for(arm)
            text = text_for(it, arm)
            attempts, rec = [], None
            for attempt in range(3):
                try:
                    if model in PROVIDER:
                        rec = await rest_item(provider, model, instruction, tools, required, text, post=_post,
                                              headers=headers, remedy=args.remedy,
                                              tool_choice="auto" if args.tool_choice == "auto" else None)
                    else:
                        rec = await live_item(connect, model, instruction, tools, required, text, remedy=args.remedy,
                                              thinking_level=thinking,
                                              submit_deadline=600.0 if thinking else 300.0)
                except Exception as exc:  # noqa: BLE001 - a transport error before any record
                    attempts.append({"attempt": attempt + 1, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
                    print(f"  {arm} {it['item_id']} attempt {attempt + 1} failed: {attempts[-1]['error'][:100]}", flush=True)
                    rec = None
                    await asyncio.sleep(20 * (attempt + 1))
                    continue
                if rec["submission"]["status"] == "obtained" or not str(rec["collection"]["status"]).startswith("error"):
                    break                       # only a transport error with nothing obtained is retried
                attempts.append(dict(rec, attempt=attempt + 1))
                await asyncio.sleep(20 * (attempt + 1))
            if rec is None:
                rec = {"runner": RUNNER_VERSION, "calls": [], "outcome": "transport_error",
                       "submission": {"status": "none"}, "collection": {"status": "transport_error"}}
            rec.update({"model": model, "arm": arm, "item_id": it["item_id"], "role": it["role"], "truth": it["truth"],
                        "remedy": args.remedy, "tool_choice": args.tool_choice, "evidence": evidence_of(it),
                        "attempts": attempts})
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            said = rec["calls"][-1]["args"].get("execution_state") if rec["calls"] else None
            print(f"[{arm}] {it['item_id']:32} {it['role']:7} truth {it['truth']:9} -> {said} "
                  f"({rec['outcome']}; collection {rec['collection']['status']})", flush=True)
    cost = spent(model)
    print("done" + (f"; v2 spend so far US${cost:.2f}" if cost is not None else "; spend not metered for this backend"))


if __name__ == "__main__":
    asyncio.run(main())
