"""Render every episode into frozen replay files.

data/replays/<replay_id>.jsonl       what the model sees (opaque id; no truth)
data/truth/<replay_id>.jsonl          evidence-supported answers, kept apart
data/replays/reference_<...>.json     reference curves for arms that get context (C-context, C-full)
data/replays/INDEX.json               replay_id -> episode, condition, sha256
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from livelab.episode import load, render, write_jsonl  # noqa: E402
from livelab.observability import N_REFERENCE, reference_band  # noqa: E402
from livelab.protocol import PROTOCOLS  # noqa: E402

DELTA_S = 60


def main():
    index = {}
    regimes = set()
    for path in sorted(glob.glob(str(ROOT / "scenarios" / "**" / "*.yaml"), recursive=True)):
        ep = load(path)
        regimes.add((ep["protocol"], ep["regime"]))
        for cond in ep["sensor_conditions"]:
            events, truth = render(ep, cond, DELTA_S)
            rid = events[0]["replay_id"]
            digest = write_jsonl(events, ROOT / "data" / "replays" / f"{rid}.jsonl")
            write_jsonl(truth, ROOT / "data" / "truth" / f"{rid}.jsonl")
            index[rid] = {"episode_id": ep["episode_id"], "condition": cond, "events": len(events),
                          "delta_s": DELTA_S, "sha256": digest}
            print(f"{rid}  {ep['episode_id']:28} {cond:18} {digest[:12]}")
    for protocol_id, regime in sorted(regimes):
        band = reference_band(PROTOCOLS[protocol_id], regime, DELTA_S)
        ref = {"protocol": protocol_id, "regime": regime, "delta_s": DELTA_S, "n_runs": N_REFERENCE,
               "provenance": "author-constructed simulator, normal runs",
               "channels": {c: {"mean": [round(float(x), 3) for x in m], "sd": [round(float(x), 3) for x in s]}
                            for c, (m, s) in band.items()}}
        (ROOT / "data" / "replays" / f"reference_{protocol_id}_{regime}.json").write_text(json.dumps(ref))
    (ROOT / "data" / "replays" / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
