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
MIN_SPAN_S = 600        # half the telemetry window; deviation 1 of the registration
TOL_S = 30              # a frame further than this from its target is refused, not used
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
    """Frame indices ending at the decision time, spread over as much of the window as the
    recording covers.

    Returns (indices, span_s). Four of the nineteen recordings start after the window does —
    the camera was switched on a couple of minutes into it — so the frames span the intersection
    of the two rather than the full 20 minutes, and the span is carried into the item so a reader
    can see which items saw less. Under MIN_SPAN_S the item is dropped instead.
    """
    if not times:
        return [], 0.0
    start = max(decision - timedelta(seconds=WINDOW_S), times[0])
    span = (decision - start).total_seconds()
    if span < MIN_SPAN_S or decision > times[-1] + timedelta(seconds=TOL_S):
        return [], span
    wanted = [start + timedelta(seconds=span * k / (FRAMES - 1)) for k in range(FRAMES)]
    idx = []
    for w in wanted:
        j = min(range(len(times)), key=lambda i: abs((times[i] - w).total_seconds()))
        if abs((times[j] - w).total_seconds()) <= TOL_S:
            idx.append(j)
    if len(set(idx)) != len(idx):      # never send the same frame twice as if it were two looks
        return [], span
    return idx, span


def extract(video, indices, dest):
    """One decode pass for all six frames, rather than one pass each.

    Old frames are deleted first: ffmpeg overwrites f01 onwards, so a re-run that produced fewer
    frames would leave the previous run's stills sitting beside the new ones, and they would go to
    the model as if this run had taken them.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for stale in dest.glob("f*.jpg"):
        stale.unlink()
    expr = "+".join(f"eq(n\\,{i})" for i in indices)
    cmd = [ffmpeg(), "-v", "error", "-y", "-i", str(video), "-vf",
           f"select='{expr}',scale={SIZE[0]}:{SIZE[1]}", "-vsync", "0",
           str(dest / "f%02d.jpg")]
    subprocess.run(cmd, check=True)
    return sorted(dest.glob("f*.jpg"))


def main():
    items = json.load(open(ROOT / "data/realdata/items.json"))["items"]
    made, skipped = [], {"no_video": 0, "no_window": 0, "wrong_count": 0, "unreadable": 0}
    for it in items:
        if it["condition"] not in ("blind", "control"):
            continue
        folder = MEDIA / it["experiment"]
        video, txt = folder / "Cam0.mp4", folder / "Cam0.txt"
        if not (video.exists() and txt.exists()):
            skipped["no_video"] += 1
            continue
        times = frame_times(txt)
        idx, span = pick_indices(times, datetime.strptime(it["decision_time"], "%H:%M:%S"))
        if len(idx) < FRAMES:
            skipped["no_window"] += 1
            continue
        key = f"{it['experiment'].replace('/', '__')}__{it['condition']}"
        try:
            files = extract(video, idx, OUT / "frames" / key)
        except subprocess.CalledProcessError:
            print(f"  UNREADABLE {key[:60]}", flush=True)
            skipped["unreadable"] += 1
            continue
        if len(files) != FRAMES:
            skipped["wrong_count"] += 1
            continue
        made.append(it | {"item_id": key,
                          "frames": [str(f.relative_to(OUT)) for f in files],
                          "frame_times": [times[i].strftime("%H:%M:%S") for i in idx],
                          "frame_span_s": round(span)})
        print(f"  {key[:56]:58} {len(files)} frames over {round(span):4}s", flush=True)

    (OUT / "items.json").write_text(json.dumps({"frames_per_item": FRAMES, "size": list(SIZE),
                                                "window_s": WINDOW_S, "items": made}, indent=1))
    by = {}
    for m in made:
        by[m["condition"]] = by.get(m["condition"], 0) + 1
    print(f"\n{len(made)} items with frames -> data/vision/items.json")
    print("  " + "  ".join(f"{k} {v}" for k, v in sorted(by.items())))
    print("  skipped: " + "  ".join(f"{k} {v}" for k, v in skipped.items()))
    if skipped["unreadable"]:
        # A short item set that nobody noticed is how a study quietly changes its own design.
        sys.exit(f"{skipped['unreadable']} video(s) would not decode — still downloading, or "
                 f"truncated. Fix those before running the study.")


if __name__ == "__main__":
    main()
