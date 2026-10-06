"""Single-image test of model-directed inspection on the PDMS photographs
(docs/pdms_inspect_preregistration.md).

Two arms, the same loop, budget and items; only the tool differs:
  C1   the photograph; report_inspection only (control)
  C1I  the photograph; inspect_region (up to 3 magnified views) and report_inspection

  ./.venv/bin/python scripts/run_pdms_inspect.py run --backend flash --arm C1 C1I [--limit 3 --out results/pdms_inspect_smoke]
  ./.venv/bin/python scripts/run_pdms_inspect.py score --model gemini-3.8-flash
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
from livelab.inspect_tool import inspect_item  # noqa: E402
from livelab.standard_api import _headers, _post  # noqa: E402
from scripts.run_core import PRICE  # noqa: E402
from scripts.run_pdms_pilot import INSTRUCTION, PILOT, REPORT, prompt_for  # noqa: E402
from scripts.run_probes import MODELS, PROVIDER  # noqa: E402

OUT = ROOT / "results/pdms_inspect"
TOOL_SENTENCE = ("\nBefore reporting, you may call inspect_region up to 3 times to see any rectangle of the "
                 "photograph magnified.")
ARMS = {"C1": False, "C1I": True}
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def items_for(which):
    items = json.load(open(PILOT / "items.json"))["items"]
    return items if which == "all" else [i for i in items if i["set"] == which]


def instruction_for(arm):
    return INSTRUCTION + (TOOL_SENTENCE if ARMS[arm] else "")


def spent(model, out):
    if model not in PRICE:
        return None
    pin, pout = PRICE[model]
    total = 0.0
    for f in Path(out).glob(f"{model}/*/*.json"):
        for u in json.loads(f.read_text()).get("usage_messages", []):
            total += (u["usage"].get("prompt_token_count") or 0) * pin / 1e6
            total += (u["usage"].get("response_token_count") or 0) * pout / 1e6
    return total


async def run(args):
    model = MODELS[args.backend]
    provider = PROVIDER[model]
    load_dotenv()
    key = os.environ.get(KEYS.get(provider, "")) or (os.environ.get("GOOGLE_API_KEY") if provider == "gemini" else None)
    if not key:
        sys.exit(f"Set {KEYS.get(provider)} in livelab/.env (never commit it).")
    headers = _headers(provider, key)
    items = items_for(args.set)[: args.limit or None]
    for arm in args.arm:
        for it in items:
            dest = Path(args.out) / model / arm / f"{it['item_id']}.json"
            if dest.exists():
                continue
            cost = spent(model, args.out)
            if cost is not None and cost > args.cap:
                sys.exit(f"spend for {model} in {args.out} is US${cost:.2f}, past the US${args.cap:.2f} cap. Stopped.")
            photo = PILOT / "images" / Path(it["image"]).name
            text = prompt_for(it, "C1")
            rec, attempts = None, []
            for attempt in range(3):
                try:
                    rec = await inspect_item(provider, model, instruction_for(arm), REPORT, text, photo,
                                             post=_post, headers=headers, inspect=ARMS[arm])
                    break
                except Exception as exc:  # noqa: BLE001 - transport error before any record
                    attempts.append(f"{type(exc).__name__}: {str(exc)[:300]}")
                    await asyncio.sleep(20 * (attempt + 1))
            rec = rec or {"status": "transport_error", "answer": None, "regions": [], "usage_messages": []}
            rec.update({"arm": arm, "item_id": it["item_id"], "set": it["set"], "group": it["group"],
                        "truth": it["truth"], "prompt": text, "instruction": instruction_for(arm),
                        "image": str(photo.relative_to(ROOT)), "attempts": attempts})
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            v = (rec["answer"] or {}).get("verdict")
            print(f"[{arm}] {it['item_id']:12} truth {it['truth']:8} -> {v} ({rec['status']}; "
                  f"{len(rec['regions'])} region(s))", flush=True)
    cost = spent(model, args.out)
    print("done" + (f"; spend so far US${cost:.2f}" if cost is not None else ""))


def score(model, out=OUT, which="flip"):
    items = items_for(which)
    rows = {}
    for arm in ARMS:
        recs = {f.stem: json.loads(f.read_text()) for f in (Path(out) / model / arm).glob("*.json")}
        right = unknown = none = used = 0
        groups = {}
        for it in items:
            r = recs.get(it["item_id"])
            v = ((r or {}).get("answer") or {}).get("verdict")
            none += v is None
            unknown += v == "UNKNOWN"
            ok = v == it["truth"]
            right += ok
            used += len((r or {}).get("regions") or []) > 0
            groups.setdefault(it["group"], []).append(ok)
        rows[arm] = {"items": len(items), "records": len(recs), "right": right, "unknown": unknown,
                     "no_answer": none, "used_inspection": used,
                     "both_steps_right": sum(len(g) == 2 and all(g) for g in groups.values()),
                     "images": len(groups), "spend_usd": round(sum(
                         (u["usage"].get("prompt_token_count") or 0) * PRICE[model][0] / 1e6
                         + (u["usage"].get("response_token_count") or 0) * PRICE[model][1] / 1e6
                         for r in recs.values() for u in r.get("usage_messages", [])), 3)}
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--backend", required=True, choices=sorted(MODELS))
    r.add_argument("--arm", nargs="+", default=list(ARMS), choices=list(ARMS))
    r.add_argument("--set", default="flip", choices=["flip", "pair", "all"])
    r.add_argument("--limit", type=int)
    r.add_argument("--cap", type=float, default=3.0, help="stop once spend in --out passes this many USD")
    r.add_argument("--out", default=str(OUT))
    s = sub.add_parser("score")
    s.add_argument("--model", required=True)
    s.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    if args.cmd == "run":
        asyncio.run(run(args))
    else:
        print(json.dumps(score(args.model, args.out), indent=1))


if __name__ == "__main__":
    main()
