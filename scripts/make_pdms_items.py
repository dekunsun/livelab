"""Choose pilot 1's items from the PDMS annotations, without looking at any image.

Registered design: docs/pilots_preregistration.md. Reads annotation.json only. Writes the chosen
items, and the fields a model is allowed to see, to data/pdms_pilot/items.json (gitignored with
the rest of data/) and a copy of the ids to results/pilot1/items.json, which is committed so the
selection can be checked against the registration.

  ./.venv/bin/python scripts/make_pdms_items.py
"""
import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/external/pdms/data/annotation/annotation.json"
OUT = ROOT / "data/pdms_pilot/items.json"
RECORD = ROOT / "results/pilot1/items.json"
SEED = 20260921
N_PAIRS = 30
N_FLIP = 20

# What a model may see: the step it is inspecting and what the check asks. Nothing that carries the
# answer: not Anomaly_Label, Anomaly_Type, Anomaly_Label_Description, Caption, Grounding or the
# dataset's own question-and-answer conversations.
SHOWN = ("Stage_Description", "phase", "Detection_Location", "Detection_Content")
PAIR_KEY = ("step", "phase", "Detection_Content", "Views", "Distance")
CONTEXT = ("step", "phase", "Detection_Content")


def context_of(r):
    return {k: r[k] for k in SHOWN}


def main():
    A = json.load(open(SRC))
    rng = random.Random(SEED)

    by_image = collections.defaultdict(list)
    for r in A:
        by_image[r["Image_Id"]].append(r)
    flip_images = sorted(i for i, rs in by_image.items()
                         if {r["Anomaly_Label"] for r in rs} == {True, False})

    # Context-flip items: one normal and one abnormal annotation of the same image, whose contexts
    # differ. If they did not differ, the two labels would contradict each other, not depend on
    # the step, and the image is set aside and counted.
    flips, contradictory = [], 0
    for img in rng.sample(flip_images, len(flip_images)):
        rs = by_image[img]
        normal = [r for r in rs if not r["Anomaly_Label"]]
        abnormal = [r for r in rs if r["Anomaly_Label"]]
        options = [(a, b) for a in normal for b in abnormal
                   if tuple(a[k] for k in CONTEXT) != tuple(b[k] for k in CONTEXT)]
        if not options:
            contradictory += 1
            continue
        a, b = rng.choice(options)
        flips.append((img, a, b))
        if len(flips) == N_FLIP:
            break
    flip_set = {img for img, _, _ in flips}

    # Matched pairs: same step, phase, check, view and distance; one normal and one abnormal
    # annotation on two different images, neither of them a context-flip image.
    groups = collections.defaultdict(list)
    for r in A:
        if r["Image_Id"] not in flip_set:
            groups[tuple(r[k] for k in PAIR_KEY)].append(r)
    eligible = []
    for key, rs in sorted(groups.items()):
        normal = [r for r in rs if not r["Anomaly_Label"]]
        abnormal = [r for r in rs if r["Anomaly_Label"]]
        if any(a["Image_Id"] != b["Image_Id"] for a in normal for b in abnormal):
            eligible.append((key, normal, abnormal))
    pairs, used = [], set()
    for key, normal, abnormal in rng.sample(eligible, len(eligible)):
        options = [(a, b) for a in normal for b in abnormal
                   if a["Image_Id"] != b["Image_Id"]
                   and a["Image_Id"] not in used and b["Image_Id"] not in used]
        if not options:
            continue
        a, b = rng.choice(options)
        used |= {a["Image_Id"], b["Image_Id"]}
        pairs.append((key, a, b))
        if len(pairs) == N_PAIRS:
            break

    items = []
    for n, (key, a, b) in enumerate(pairs):
        for r in (a, b):
            items.append({"item_id": f"pair{n:02d}_{'abn' if r['Anomaly_Label'] else 'nor'}",
                          "set": "pair", "group": f"pair{n:02d}", "image": r["Image_Id"],
                          "context": context_of(r),
                          "truth": "ABNORMAL" if r["Anomaly_Label"] else "NORMAL"})
    for n, (img, a, b) in enumerate(flips):
        for r in (a, b):
            items.append({"item_id": f"flip{n:02d}_{'abn' if r['Anomaly_Label'] else 'nor'}",
                          "set": "flip", "group": f"flip{n:02d}", "image": img,
                          "context": context_of(r),
                          "truth": "ABNORMAL" if r["Anomaly_Label"] else "NORMAL"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "shown_fields": SHOWN, "items": items}, indent=1,
                              ensure_ascii=False))
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({"seed": SEED, "items": [
        {k: it[k] for k in ("item_id", "set", "group", "image", "truth")} for it in items]}, indent=1))

    audit = {"0008", "0024", "0032", "0080", "0089", "0116", "0379", "0389"}
    drawn = sorted({Path(it["image"]).stem for it in items} & audit)
    print(f"{len(A)} annotations, {len(by_image)} images; {len(flip_images)} images carry both labels")
    print(f"flip items: {len(flips)} images, {contradictory} set aside as contradictory "
          f"(same step, phase and check, opposite labels)")
    print(f"matched pairs: {len(pairs)} of {len(eligible)} eligible groups")
    print(f"{len(items)} items, {len({it['image'] for it in items})} distinct images")
    print(f"images named in the independent audit that were drawn: {drawn or 'none'}")


if __name__ == "__main__":
    main()
