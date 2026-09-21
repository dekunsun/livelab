"""Cut six frames out of each run's video, at the same window the telemetry item covers.

Registered design: docs/vision_preregistration.md. The plant records one frame every two seconds
with a wall-clock timestamp per frame in a .txt beside the video, so a decision time maps to a
frame index exactly rather than approximately.

Needs the footage fetched by scripts/fetch_zenodo_members.py. Frames are written under
data/vision/, which is gitignored: they are CC BY 4.0 and attributed in
data/realdata/ATTRIBUTION.md, but 20 runs of stills do not belong in a git history.

  ./.venv/bin/python scripts/make_vision_items.py
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MEDIA = ROOT / "data/external/batch_distillation/media/image/Operation"
OUT = ROOT / "data/vision"
FRAMES = 6
WINDOW_S = 1200
SIZE = (640, 480)
CLOCK = re.compile(r"(\d{2})-(\d{2})-(\d{2})")


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def frame_times(txt_path):
    """Wall-clock time of every recorded frame, in order."""
    out = []
    for line in txt_path.read_text(errors="replace").splitlines():
        m = CLOCK.search(line)
        if m:
            out.append(datetime.strptime(":".join(m.groups()), "%H:%M:%S"))
    return out


def pick_indices(times, decision):
    """Frame indices evenly across the window that ends at the decision time."""
    if not times:
        return []
    start = decision - timedelta(seconds=WINDOW_S)
    wanted = [start + timedelta(seconds=WINDOW_S * k / (FRAMES - 1)) for k in range(FRAMES)]
    idx = []
    for w in wanted:
        j = min(range(len(times)), key=lambda i: abs((times[i] - w).total_seconds()))
        if abs((times[j] - w).total_seconds()) <= 30:      # the recording must actually cover it
            idx.append(j)
    return idx


def extract(video, indices, dest):
    """One decode pass for all six frames, rather than one pass each."""
    dest.mkdir(parents=True, exist_ok=True)
    expr = "+".join(f"eq(n\\,{i})" for i in indices)
    cmd = [ffmpeg(), "-v", "error", "-y", "-i", str(video), "-vf",
           f"select='{expr}',scale={SIZE[0]}:{SIZE[1]}", "-vsync", "0",
           str(dest / "f%02d.jpg")]
    subprocess.run(cmd, check=True)
    return sorted(dest.glob("f*.jpg"))


def main():
    items = json.load(open(ROOT / "data/realdata/items.json"))["items"]
    made, skipped = [], {"no_video": 0, "no_window": 0, "wrong_count": 0}
    for it in items:
        if it["condition"] not in ("blind", "control"):
            continue
        folder = MEDIA / it["experiment"]
        video, txt = folder / "Cam0.mp4", folder / "Cam0.txt"
        if not (video.exists() and txt.exists()):
            skipped["no_video"] += 1
            continue
        times = frame_times(txt)
        idx = pick_indices(times, datetime.strptime(it["decision_time"], "%H:%M:%S"))
        if len(idx) < FRAMES:
            skipped["no_window"] += 1
            continue
        key = f"{it['experiment'].replace('/', '__')}__{it['condition']}"
        files = extract(video, idx, OUT / "frames" / key)
        if len(files) != FRAMES:
            skipped["wrong_count"] += 1
            continue
        made.append(it | {"item_id": key,
                          "frames": [str(f.relative_to(OUT)) for f in files],
                          "frame_times": [times[i].strftime("%H:%M:%S") for i in idx]})
        print(f"  {key[:60]:62} {len(files)} frames", flush=True)

    (OUT / "items.json").write_text(json.dumps({"frames_per_item": FRAMES, "size": list(SIZE),
                                                "window_s": WINDOW_S, "items": made}, indent=1))
    by = {}
    for m in made:
        by[m["condition"]] = by.get(m["condition"], 0) + 1
    print(f"\n{len(made)} items with frames -> data/vision/items.json")
    print("  " + "  ".join(f"{k} {v}" for k, v in sorted(by.items())))
    print("  skipped: " + "  ".join(f"{k} {v}" for k, v in skipped.items()))


if __name__ == "__main__":
    main()
