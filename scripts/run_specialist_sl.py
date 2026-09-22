"""Arm S+L of docs/specialist_preregistration.md: the language models decide from S's verdict.

Pilot 1's instruction and task context, with the photograph replaced by one sentence reporting
what the specialist concluded. The language model never sees the picture.

  ./.venv/bin/python scripts/run_specialist_sl.py --backend opus-5
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.run_pdms_pilot import INSTRUCTION, REPORT, asker_for, call  # noqa: E402
from scripts.run_probes import MODELS  # noqa: E402

OUT = ROOT / "results/specialist"
PHRASE = {"NORMAL": "satisfied", "ABNORMAL": "not satisfied"}


def evidence(s):
    if s["verdict"] == "UNKNOWN":
        # The registered template has no agreement count to give here (deviation 1).
        return ("An inspection classifier trained on this laboratory's past photographs could not "
                "judge this check: it had too few similar past photographs.")
    return ("An inspection classifier trained on this laboratory's past photographs judged this "
            f"check: {PHRASE[s['verdict']]}, with {s['agreeing']} of 5 similar past photographs "
            "agreeing.")


async def run(backend):
    items = json.load(open(ROOT / "data/pdms_pilot/items.json"))["items"]
    S = json.load(open(OUT / "S_primary.json"))
    model, ask, _ = asker_for(backend)
    dest_dir = OUT / "SL" / model
    dest_dir.mkdir(parents=True, exist_ok=True)
    for n, it in enumerate(items, 1):
        dest = dest_dir / f"{it['item_id']}.json"
        if dest.exists():
            continue
        c = it["context"]
        text = "\n".join([f"Workflow step: {c['Stage_Description']}",
                          f"Inspection timing: {'before' if c['phase'] == 'pre' else 'after'} this step",
                          f"Inspection location: {c['Detection_Location']}",
                          f"What the inspection checks: {c['Detection_Content']}", "",
                          evidence(S[it["item_id"]])])
        res = await call(ask, INSTRUCTION, [REPORT], ["report_inspection"], text)
        if res is None:
            print(f"  {it['item_id']}: no answer", flush=True)
            continue
        a = res["calls"][-1]["args"]
        dest.write_text(json.dumps({"model": model, "item_id": it["item_id"], "set": it["set"],
                                    "group": it["group"], "truth": it["truth"], "prompt": text,
                                    "S": S[it["item_id"]], "verdict": a.get("verdict"),
                                    "observations": a.get("observations"),
                                    "usage": res.get("usage")}, indent=1))
        print(f"[{n:3}/100] {it['item_id']:12} truth {it['truth']:8} S {S[it['item_id']]['verdict']:8}"
              f" -> {a.get('verdict')}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=sorted(MODELS))
    asyncio.run(run(ap.parse_args().backend))
