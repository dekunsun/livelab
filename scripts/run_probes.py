"""Run the pre-registered UNKNOWN probes (docs/probe_preregistration.md) on Gemini 3.8 Live.

  ./.venv/bin/python scripts/run_probes.py             # all variants; resumes, skipping finished items
  ./.venv/bin/python scripts/run_probes.py --only B0 --limit 2    # a cheap smoke test

Each answer is saved to results/probes/<model>/<variant>/<item_id>.json as soon as it arrives.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import (CONTROL_MODEL, PROBE_VERSION, call_path_healthy, calls_come_back,  # noqa: E402
                            p1_message, p1_setup, prefix_message, run_single_turn, variant_setup)

MODELS = {"gemini": "gemini-3.8-live", "gemini-extended": "gemini-3.8-live-extended-thinking"}
VARIANTS = ["P1", "B0", "B1", "B2", "B3"]
RETRY_WAIT_S = 30
PATIENCE_S = 240        # how long an async model may reason before a reminder interrupts it


async def path_is_broken(model, thinking, connect, control_connect, request):
    """Did the API fail, or did the model decline? Only a control on the same request can say.

    The free-tier Extended Thinking model's call path degrades with use and recovers when idle, and
    the server reports the failure to the model, not to the client (deviation 7)."""
    if model != CONTROL_MODEL:
        return await calls_come_back(control_connect, *request, patience=PATIENCE_S)
    return not await call_path_healthy(connect, model, thinking)     # no second model to compare with


def real_connect(model):
    import os
    from google import genai
    load_dotenv()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("Set GEMINI_API_KEY in livelab/.env (never commit it).")
    client = genai.Client()
    return lambda cfg: client.aio.live.connect(model=model, config=cfg)


def jobs(items, only, sets=None):
    for v in VARIANTS:
        if only and v not in only:
            continue
        if v == "P1":
            for it in items["p1"]:
                yield v, it["item_id"], (*p1_setup(it), p1_message(it))
        else:
            for it in items["in_context"]:
                if sets and it["set"] not in sets:
                    continue
                yield v, it["item_id"], (*variant_setup(v), prefix_message(it["replay_id"], it["k"]))


async def main(connect=None, out_root=None, argv=None, control_connect=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=VARIANTS)
    ap.add_argument("--limit", type=int, help="at most this many items per variant (smoke test)")
    ap.add_argument("--backend", default="gemini", choices=sorted(MODELS))
    ap.add_argument("--sets", nargs="*", choices=["U", "N", "A"], help="in-context item sets to run (default: all)")
    ap.add_argument("--cooldown", type=int, default=1200,
                    help="seconds to idle when the API's call path breaks, before trying the item again")
    ap.add_argument("--max-cooldowns", type=int, default=0,
                    help="cooldown cycles before giving up. Default 0: stop at once. Measured on 2026-09-20, "
                         "every request while the path is broken appears to push recovery further out, so "
                         "polling it collected nothing in six hours")
    args = ap.parse_args(argv)
    model = MODELS[args.backend]
    thinking = "HIGH" if "extended" in model else None
    out_root = out_root or ROOT / "results" / "probes" / model
    items = json.load(open(ROOT / "data/probes/items.json"))
    if connect is None:
        connect = real_connect(model)
        control_connect = control_connect or real_connect(CONTROL_MODEL)
    per_variant, failures = {}, 0
    for v, item_id, (instruction, tools, required, text) in jobs(items, args.only, args.sets):
        if args.limit and per_variant.get(v, 0) >= args.limit:
            continue
        per_variant[v] = per_variant.get(v, 0) + 1
        out = Path(out_root) / v / f"{item_id}.json"
        if out.exists():
            continue
        res, unanswered, cooldowns = None, [], 0
        while res is None:
            for attempt in range(1 if cooldowns else 3):
                try:
                    got = await asyncio.wait_for(run_single_turn(connect, instruction, tools, required, text, model_id=model,
                                                                 thinking_level=thinking, patience=PATIENCE_S), 600)
                except Exception as exc:  # noqa: BLE001 - free-tier transient errors; retry the whole item
                    print(f"{v} {item_id} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
                    await asyncio.sleep(RETRY_WAIT_S * (attempt + 1))
                    continue
                if [r for r in required if r not in {c["name"] for c in got["calls"]}]:
                    unanswered.append(got)              # the model answered nothing this time
                    print(f"{v} {item_id} attempt {attempt + 1}: required call missing after reminders", flush=True)
                    continue
                res = got
                break
            if res is not None or not unanswered:
                break                                   # answered, or only transient errors: --resume picks it up
            # Silence means either the model declined or the API's call path is broken, and from here
            # those look identical (deviation 7). Ask the control model before recording anything.
            if not await path_is_broken(model, thinking, connect, control_connect, (instruction, tools, required, text)):
                res = dict(unanswered[-1], unanswered=True, control_answered=False,
                           attempts_spoken=[u["spoken"] for u in unanswered])
                break
            cooldowns += 1
            if cooldowns > args.max_cooldowns:
                sys.exit(f"{v} {item_id}: the call path was still broken after {args.max_cooldowns} cooldowns.\n"
                         "Nothing was saved for this item. Rerun when the API is healthy.")
            print(f"{time.strftime('%H:%M:%S')} {v} {item_id}: call path broken ({CONTROL_MODEL} answers the same "
                  f"request). Waiting {args.cooldown // 60} min, then one more attempt "
                  f"(cooldown {cooldowns}/{args.max_cooldowns}).", flush=True)
            await asyncio.sleep(args.cooldown)
        if res is None:
            failures += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"probe_version": PROBE_VERSION, "model": model,
                                   "thinking_level": thinking, "variant": v,
                                   "item_id": item_id, **res}, indent=1))
        names = [c["name"] for c in res["calls"]]
        print(f"{v} {item_id}: {names} reminders={res['reminders']}" + ("  (NO ANSWER on 3 attempts; excluded)" if res.get("unanswered") else ""))
    print(f"done; {failures} item(s) failed and can be retried by rerunning the same command")


if __name__ == "__main__":
    asyncio.run(main())
