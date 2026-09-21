"""Run pilot 1 (docs/pilots_preregistration.md): does a model join what it sees to the task step?

  ./.venv/bin/python scripts/run_pdms_pilot.py describe
  ./.venv/bin/python scripts/run_pdms_pilot.py run --backend opus-5 --condition C0 C1 C2

`describe` writes one visual-fact description per image, from the image alone. `run` asks each
item under the chosen conditions. Everything is written under results/pilot1/ and skipped if it
already exists, so a run can be resumed.
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import run_single_turn  # noqa: E402
from livelab.standard_api import StandardAsker  # noqa: E402
from scripts.run_probes import MODELS, PATIENCE_S, PROVIDER, real_connect  # noqa: E402

PILOT = ROOT / "data/pdms_pilot"
OUT = ROOT / "results/pilot1"
DESCRIBER = "opus-5"

INSTRUCTION = (
    "You are the inspection step of an automated chemistry laboratory. You are told which workflow "
    "step is being inspected and what the inspection checks. Decide whether the check is "
    "satisfied, and call report_inspection exactly once.\n"
    "- NORMAL: what you were given shows the check is satisfied.\n"
    "- ABNORMAL: what you were given shows the check is not satisfied.\n"
    "- UNKNOWN: what you were given does not let you tell.")
EVIDENCE = {
    "C0": "No photograph is available for this inspection.",
    "C1": "The inspection camera's photograph is attached.",
    "C2": ("A description of the inspection camera's photograph follows, written by someone who "
           "was not told what is being checked."),
}
REPORT = {
    "name": "report_inspection",
    "description": "Report the result of this inspection.",
    "parameters": {"type": "object", "properties": {
        "verdict": {"type": "string", "enum": ["NORMAL", "ABNORMAL", "UNKNOWN"]},
        "observations": {"type": "string",
                         "description": "What the verdict rests on, in one or two sentences."}},
        "required": ["verdict", "observations"]},
}

DESCRIBE_INSTRUCTION = (
    "Describe what is visible in this photograph of laboratory equipment. List the objects, where "
    "they are, and their visible states: for example open or closed, capped or uncapped, upright "
    "or on its side, empty or holding liquid, and the liquid's colour. Report only what you can "
    "see. Do not judge whether anything is correct, expected, missing or wrong. Call "
    "write_description exactly once.")
DESCRIBE = {
    "name": "write_description",
    "description": "Submit the description of the photograph.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
                   "required": ["text"]},
}
# Registered: a description using any of these is sent back once, then dropped.
# Matched anywhere in a word, so "unexpected" and "incorrect" are caught as well.
BANNED = re.compile(r"\w*(abnormal|anomal|error|wrong|missing|should|fail|correct|normal|expected)\w*",
                    re.I)


def asker_for(backend):
    model = MODELS[backend]
    if model in PROVIDER:
        load_dotenv()
        provider = PROVIDER[model]
        env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(env):
            sys.exit(f"Set {env} in livelab/.env (never commit it).")
        asker = StandardAsker(provider, model)

        async def ask(system, tools, required, text, images=()):
            return await asker(system, tools, required, text, images=list(images))
        return model, ask, asker
    connect = real_connect(model)

    async def ask(system, tools, required, text, images=()):
        blobs = [("image/jpeg", Path(f).read_bytes()) for f in images]
        return await run_single_turn(connect, system, tools, required, text, model_id=model,
                                     patience=PATIENCE_S, images=blobs)
    return model, ask, None


async def call(ask, *a, **kw):
    for attempt in range(3):
        try:
            res = await asyncio.wait_for(ask(*a, **kw), 300)
        except Exception as exc:  # noqa: BLE001
            print(f"    attempt {attempt + 1} failed: {type(exc).__name__}: {str(exc)[:90]}",
                  flush=True)
            await asyncio.sleep(15 * (attempt + 1))
            continue
        if res["calls"]:
            return res
        print(f"    attempt {attempt + 1}: no tool call", flush=True)
    return None


async def describe():
    items = json.load(open(PILOT / "items.json"))["items"]
    model, ask, _ = asker_for(DESCRIBER)
    out = OUT / "descriptions"
    out.mkdir(parents=True, exist_ok=True)
    dropped = 0
    for img in sorted({it["image"] for it in items}):
        stem = Path(img).stem
        dest = out / f"{stem}.json"
        if dest.exists():
            continue
        path = PILOT / "images" / Path(img).name
        text, tries, banned = None, [], []
        prompt = "Describe the attached photograph."
        for attempt in range(2):
            res = await call(ask, DESCRIBE_INSTRUCTION, [DESCRIBE], ["write_description"], prompt,
                             images=[path])
            if res is None:
                break
            t = [c["args"] for c in res["calls"] if c["name"] == "write_description"][-1]["text"]
            tries.append(t)
            banned = sorted({m.group(0).lower() for m in BANNED.finditer(t)})
            if not banned:
                text = t
                break
            prompt = ("Describe the attached photograph again, listing only what is visible. Do "
                      f"not use these words: {', '.join(banned)}.")
        dropped += text is None
        dest.write_text(json.dumps({"image": img, "describer": model, "text": text,
                                    "attempts": tries, "banned_found": banned}, indent=1))
        print(f"  {stem}: {'ok' if text else 'DROPPED'} ({len(tries)} attempt(s))", flush=True)
    print(f"done; {dropped} descriptions dropped for banned words")


def prompt_for(item, condition):
    c = item["context"]
    lines = [f"Workflow step: {c['Stage_Description']}",
             f"Inspection timing: {'before' if c['phase'] == 'pre' else 'after'} this step",
             f"Inspection location: {c['Detection_Location']}",
             f"What the inspection checks: {c['Detection_Content']}", "", EVIDENCE[condition]]
    if condition == "C2":
        d = json.loads((OUT / "descriptions" / f"{Path(item['image']).stem}.json").read_text())
        if not d["text"]:
            return None
        lines += ["", f"Description: {d['text']}"]
    return "\n".join(lines)


async def run(backend, conditions):
    items = json.load(open(PILOT / "items.json"))["items"]
    model, ask, asker = asker_for(backend)
    done = failed = skipped = 0
    for cond in conditions:
        for n, it in enumerate(items, 1):
            dest = OUT / model / cond / f"{it['item_id']}.json"
            if dest.exists():
                continue
            text = prompt_for(it, cond)
            if text is None:
                skipped += 1
                continue
            images = [PILOT / "images" / Path(it["image"]).name] if cond == "C1" else []
            res = await call(ask, INSTRUCTION, [REPORT], ["report_inspection"], text, images=images)
            if res is None:
                failed += 1
                continue
            a = [c["args"] for c in res["calls"] if c["name"] == "report_inspection"][-1]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps({"model": model, "condition": cond, **{
                k: it[k] for k in ("item_id", "set", "group", "image", "truth")},
                "prompt": text, "images": [str(p.relative_to(ROOT)) for p in images],
                "verdict": a.get("verdict"), "observations": a.get("observations"),
                "calls": res["calls"], "usage": res.get("usage")}, indent=1, ensure_ascii=False))
            sample = OUT / model / f"request_sample_{cond}.json"
            if asker is not None and not sample.exists() and getattr(asker, "last_request", None):
                body = json.dumps(asker.last_request)
                for blob in re.findall(r'"[A-Za-z0-9+/]{200,}={0,2}"', body):
                    body = body.replace(blob, f'"<{len(blob) - 2} base64 chars elided>"')
                sample.write_text(json.dumps({"condition": cond, "request": json.loads(body)},
                                             indent=1))
            done += 1
            print(f"[{cond} {n:3}/{len(items)}] {it['item_id']:12} truth {it['truth']:8} -> "
                  f"{a.get('verdict')}", flush=True)
    print(f"done; {done} answered, {failed} without an answer, {skipped} skipped (no description)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    r = sub.add_parser("run")
    r.add_argument("--backend", required=True, choices=sorted(MODELS))
    r.add_argument("--condition", nargs="+", default=["C0", "C1", "C2"], choices=["C0", "C1", "C2"])
    args = ap.parse_args()
    asyncio.run(describe() if args.cmd == "describe" else run(args.backend, args.condition))


if __name__ == "__main__":
    main()
