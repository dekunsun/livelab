"""Choose pilot 2's CAXTON clips from the logs alone, and cut their frames for the blind review.

Registered design: docs/pilots_preregistration.md. Clip choice reads only print_log_full.csv; no
image is looked at to choose. The key that maps each shuffled clip back to its print and frames
is written to data/pilot2/key.json, which is gitignored, and is committed only after the review,
so the reviewer cannot see where a clip came from. This script and its seed are committed before
the review, and they fix the selection.

  ./.venv/bin/python scripts/make_pilot2_clips.py
"""
import csv
import json
import random
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CAX = ROOT / "data/external/caxton"
OUT = ROOT / "data/pilot2"
SEED = 20260921
CLIP = 10
FLAGGED_PRINTS = list(range(183, 192))
N_FLAGGED = 8
N_REPEATS = 2
# Frames of print 0 already looked at before registration; never eligible.
SEEN_PRINT0 = {*range(21, 23), *range(340, 386), *range(503, 635), *range(805, 937),
               *range(1264, 1287), *range(1416, 1548), *range(1568, 1700)}
SIZE = (640, 360)


def log(print_id):
    path = CAX / f"print{print_id}/print_log_full.csv"
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        r["frame"] = int(r["img_path"].rsplit("-", 1)[1].split(".")[0])
    return rows


def nominal(r):
    """Every logged setting within 5% of nominal. Z offset is nominally 0, where a percentage means
    nothing, so it must be within 0.02 mm."""
    return (95 <= float(r["flow_rate"]) <= 105 and 95 <= float(r["feed_rate"]) <= 105
            and abs(float(r["z_offset"])) <= 0.02 and 195 <= float(r["target_hotend"]) <= 215)


def main():
    rng = random.Random(SEED)
    clips = []

    # Flagged pool: one clip from each of 8 of the 9 excluded prints, at a random point.
    for p in rng.sample(FLAGGED_PRINTS, N_FLAGGED):
        rows = log(p)
        start = rng.randrange(0, len(rows) - CLIP + 1)
        clips.append({"pool": "flagged", "print": p, "rows": rows[start:start + CLIP]})

    # Nominal pool: non-overlapping 10-frame windows of print 0 where every row is nominal and
    # no frame was seen before registration. Registered as 6; the log only has room for 4.
    rows0 = log(0)
    windows, i = [], 0
    while i + CLIP <= len(rows0):
        w = rows0[i:i + CLIP]
        if all(nominal(r) and r["frame"] not in SEEN_PRINT0 for r in w):
            windows.append(w)
            i += CLIP
        else:
            i += 1
    for w in rng.sample(windows, min(6, len(windows))):
        clips.append({"pool": "nominal", "print": 0, "rows": w})

    for n, c in enumerate(clips):
        c["source"] = f"s{n:02d}"
    # Repeats: one flagged, one nominal, shown again under a new id with the same source.
    for pool in ("flagged", "nominal"):
        src = rng.choice([c for c in clips if c["pool"] == pool])
        clips.append(src | {"repeat": True})

    rng.shuffle(clips)
    OUT.mkdir(parents=True, exist_ok=True)
    key = []
    for n, c in enumerate(clips, 1):
        cid = f"clip{n:02d}"
        dest = OUT / "clips" / cid
        dest.mkdir(parents=True, exist_ok=True)
        z = zipfile.ZipFile(CAX / f"print{c['print']}.zip")
        times = []
        for k, r in enumerate(c["rows"], 1):
            name = f"print{c['print']}/image-{r['frame']}.jpg"
            im = Image.open(BytesIO(z.read(name))).convert("RGB").resize(SIZE)
            im.save(dest / f"f{k:02d}.jpg", quality=82)
            times.append(r["timestamp"])
        key.append({"clip": cid, "pool": c["pool"], "print": c["print"],
                    "frames": [r["frame"] for r in c["rows"]], "timestamps": times,
                    "source": c["source"], "repeat": c.get("repeat", False),
                    "log": [{k: r[k] for k in ("flow_rate", "feed_rate", "z_offset",
                                               "target_hotend", "hotend")} for r in c["rows"]]})
    (OUT / "key.json").write_text(json.dumps({"seed": SEED, "clips": key}, indent=1))
    by = {}
    for k in key:
        by[k["pool"]] = by.get(k["pool"], 0) + 1
    print(f"{len(key)} clips: {by}; nominal windows available in print 0: {len(windows)}")


if __name__ == "__main__":
    main()
