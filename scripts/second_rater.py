"""A blind second rater for pilot 1's owner checks (deviation 4 of docs/pilots_preregistration.md).

GPT-6 Astra, which took no part in pilot 1, answers the same questions the owner answered, from
the same images, without the labels. Run only after the owner had finished, so the owner never saw
its answers.

  ./.venv/bin/python scripts/second_rater.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_pdms_pilot import call  # noqa: E402

MODEL = "gpt-6-astra"
OUT = ROOT / "results/pilot1/second_rater"
PILOT = ROOT / "data/pdms_pilot"

LABEL_SYS = ("You are checking one inspection photograph from an automated chemistry laboratory. "
             "You are told the workflow step and what the inspection checks. Say whether, from the "
             "photograph, the check is met. If the photograph does not let you tell, say so. Call "
             "rate_check exactly once.")
RATE_CHECK = {"name": "rate_check", "description": "Your judgement of the check.",
              "parameters": {"type": "object", "properties": {
                  "verdict": {"type": "string", "enum": ["MET", "NOT_MET", "CANNOT_TELL"]},
                  "note": {"type": "string", "description": "What in the photograph you relied on."}},
                  "required": ["verdict", "note"]}}
DESC_SYS = ("You are checking a written description of a laboratory photograph against the "
            "photograph itself. Say how accurate it is, and whether it contains any judgement "
            "(saying something is wrong, missing, expected or should be otherwise) rather than "
            "only describing. Call rate_description exactly once.")
RATE_DESC = {"name": "rate_description", "description": "Your rating of the description.",
             "parameters": {"type": "object", "properties": {
                 "accuracy": {"type": "string",
                              "enum": ["ACCURATE", "MINOR_ERRORS", "ERRORS_THAT_WOULD_CHANGE_A_JUDGEMENT"]},
                 "judgement_present": {"type": "string", "enum": ["NO", "YES"]},
                 "note": {"type": "string", "description": "What is wrong, if anything."}},
                 "required": ["accuracy", "judgement_present", "note"]}}


async def main():
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY in livelab/.env (never commit it).")
    asker = StandardAsker("openai_responses", MODEL)
    ask = lambda s, t, r, x, images=(): asker(s, t, r, x, images=list(images))  # noqa: E731
    items = {it["item_id"]: it for it in json.load(open(PILOT / "items.json"))["items"]}
    audit = json.load(open(ROOT / "results/pilot1/audit_sample.json"))
    OUT.mkdir(parents=True, exist_ok=True)

    for iid in audit["labels"]:
        dest = OUT / f"label-{iid}.json"
        if dest.exists():
            continue
        it = items[iid]
        c = it["context"]
        text = (f"Workflow step: {c['Stage_Description']}\n"
                f"Inspection timing: {'before' if c['phase'] == 'pre' else 'after'} this step\n"
                f"Inspection location: {c['Detection_Location']}\n"
                f"What the inspection checks: {c['Detection_Content']}")
        res = await call(ask, LABEL_SYS, [RATE_CHECK], ["rate_check"], text,
                         images=[PILOT / "images" / Path(it["image"]).name])
        a = res["calls"][-1]["args"] if res else None
        dest.write_text(json.dumps({"item_id": iid, "rater": MODEL, "answer": a,
                                    "usage": res and res.get("usage")}, indent=1))
        print(f"  label {iid:14} -> {a and a['verdict']}", flush=True)

    for img in audit["descriptions"]:
        stem = Path(img).stem
        dest = OUT / f"desc-{stem}.json"
        if dest.exists():
            continue
        d = json.load(open(ROOT / f"results/pilot1/descriptions/{stem}.json"))
        res = await call(ask, DESC_SYS, [RATE_DESC], ["rate_description"],
                         f"Description:\n{d['text']}", images=[PILOT / "images" / Path(img).name])
        a = res["calls"][-1]["args"] if res else None
        dest.write_text(json.dumps({"image": img, "rater": MODEL, "answer": a,
                                    "usage": res and res.get("usage")}, indent=1))
        print(f"  desc {stem} -> {a and a['accuracy']}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
