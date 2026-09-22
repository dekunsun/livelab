"""The hand-off arm (docs/core_gemini_preregistration.md, arm D): Live talks, another model judges.

Stage 1: gemini-3.8-live, as the voice interface, is asked what the instruments show and told not to
give a verdict. It sees the telemetry only. Its spoken answer (the transcript) is saved.
Stage 2: gemini-3.8-flash, as the judge, sees only that transcript plus the system's own V1
sentence, and reports through the same report_assessment call as every Core arm. It never sees the
telemetry. Compared against gemini-3.8-flash on the raw telemetry (its V1 arm), the difference is what
the hand-off costs.

  ./.venv/bin/python scripts/run_core_handoff.py --limit 2
  ./.venv/bin/python scripts/run_core_handoff.py
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.core import load_items, setup_for, system_sentence, text_for  # noqa: E402
from livelab.probes import run_single_turn  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import PATIENCE_S, real_connect  # noqa: E402

OUT = ROOT / "results/core/handoff"
LIVE, JUDGE = "gemini-3.8-live", "gemini-3.8-flash"
NARRATE = ("You are the voice interface of a lab run monitor for a CVD tube furnace. The events so far arrive "
           "together, one JSON object per line. The scientist asks: \"What are the instruments showing right "
           "now?\" In at most 80 words, describe what the readings show, including any trends and any sensors "
           "that are not installed. Do not say whether the run is normal or anomalous; another system decides that.")
HANDOFF = "Summary of the current run, from the monitoring assistant that watched the instruments:\n\n{}\n"


async def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    load_dotenv()
    connect = real_connect(LIVE)
    judge = StandardAsker("gemini", JUDGE)
    instruction, tools, required = setup_for("V1")
    items = load_items()[:args.limit] if args.limit else load_items()
    for it in items:
        dest = OUT / f"{it['item_id']}.json"
        if dest.exists():
            continue
        telemetry = text_for(it, "V0")
        narration = None
        for attempt in range(3):
            try:
                r = await asyncio.wait_for(run_single_turn(connect, NARRATE, [], [], telemetry, model_id=LIVE,
                                                           patience=PATIENCE_S), 600)
            except Exception as exc:  # noqa: BLE001
                print(f"  live {it['item_id']} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:90]}", flush=True)
                await asyncio.sleep(20 * (attempt + 1))
                continue
            if r["spoken"].strip():
                narration = r
                break
        if narration is None:
            continue
        judged = None
        text = HANDOFF.format(narration["spoken"].strip()) + "\n" + system_sentence(it["missing_required"])
        for attempt in range(3):
            try:
                got = await asyncio.wait_for(judge(instruction, tools, required, text), 600)
            except Exception as exc:  # noqa: BLE001
                print(f"  judge {it['item_id']} attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:90]}", flush=True)
                await asyncio.sleep(20 * (attempt + 1))
                continue
            if all(q in {c["name"] for c in got["calls"]} for q in required):
                judged = got
                break
        if judged is None:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({"item_id": it["item_id"], "role": it["role"], "truth": it["truth"],
                                    "narration": narration["spoken"], "narration_usage": narration.get("usage") and
                                    {k: v for k, v in narration["usage"].items() if isinstance(v, int)},
                                    "judge_text": text, "calls": judged["calls"], "usage": judged["usage"]}, indent=1))
        said = [c["args"] for c in judged["calls"] if c["name"] == "report_assessment"][-1].get("execution_state")
        print(f"[handoff] {it['item_id']:32} {it['role']:7} truth {it['truth']:9} -> {said}", flush=True)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
