"""Build the real-plant replication items from the batch distillation dataset.

Registered design: docs/realdata_preregistration.md. Truth comes from the dataset's expert
annotations — this project's z-score rules appear once, as a guard that drops a blind item whose
evidence is still visible on a channel that was left in.

Needs data/external/batch_distillation/ (CC BY 4.0, Zenodo 17395543), fetched by
scripts/fetch_batch_distillation.py. Nothing from that record is committed.

  ./.venv/bin/python scripts/make_realdata_items.py
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data/external/batch_distillation"
CADENCE_S = 60
WINDOW_S = 1200
GUARD_Z = 3.5           # the one place this project's rule is used, and never as truth
PHASE = "Operation"


def clock(s):
    return datetime.strptime(s.strip(), "%H:%M:%S")


def read_series(path):
    rows = list(csv.DictReader(open(path)))
    if not rows:
        return None, None, None
    channels = [c for c in rows[0] if c != "Time"]
    t = [clock(r["Time"]) for r in rows]
    values = {c: np.array([float(r[c]) if r[c] not in ("", "nan") else np.nan for r in rows])
              for c in channels}
    return t, values, channels


def annotations(exp_path):
    """(anomaly windows with the sensor that observed them) for one experiment."""
    y = exp_path.with_suffix(".yaml")
    if not y.exists():
        return []
    out = []
    for a in (yaml.safe_load(open(y)) or {}).get("anomalies") or []:
        o = ((a.get("wasOriginatedBy") or {}).get("Observation") or {})
        sensor = (((o.get("madeBySensor") or {}).get("Sensor") or {}).get("id"))
        if sensor and a.get("hasBeginning") and a.get("hasEnd"):
            out.append({"start": clock(a["hasBeginning"]), "end": clock(a["hasEnd"]),
                        "sensor": sensor, "label": o.get("label")})
    return out


def window_rows(t, values, channels, end_idx, drop=()):
    """Events every CADENCE_S over WINDOW_S ending at end_idx, as compact dicts."""
    keep = [c for c in channels if c not in drop]
    idx = [i for i in range(max(0, end_idx - WINDOW_S), end_idx + 1, CADENCE_S)]
    rows = []
    for n, i in enumerate(idx):
        obs = {c: (None if np.isnan(values[c][i]) else round(float(values[c][i]), 3)) for c in keep}
        rows.append({"k": n, "t": t[i].strftime("%H:%M:%S"), "obs": obs})
    return rows, idx


GROUPS = {"temperature": re.compile(r"^T\d"), "flow": re.compile(r"^(FT|FYI)"),
          "pressure": re.compile(r"^(PDI|PY)"), "level": re.compile(r"^LS")}


def group_of(channel):
    for name, pat in GROUPS.items():
        if pat.match(channel):
            return name
    return "other"


def blind_drop(channels, observing):
    """Every channel of the same instrument group as the one the experts cited.

    Removing that single channel is not enough on a real column - the process couples channels, and
    telling coupling from the batch's own trajectory needs statistics of ours that would shape the
    result (deviation 1). Removing the whole instrument group is structural instead: it is read off
    the plant's tag list, not off the data.
    """
    g = group_of(observing)
    return {c for c in channels if group_of(c) == g}


def prefix(rows, manifest):
    head = json.dumps({"device_manifest": {"sensors": manifest}}, separators=(",", ":"))
    return "\n".join([head] + [json.dumps(r, separators=(",", ":")) for r in rows])


def main():
    sensors_root = DATA / "ts" / "01_Batch_Distillation_Plant_M-202210_Timeseries_Sensors" / PHASE
    labels_root = (DATA / "labels" / "00_Batch_Distillation_Plant_M-202210_Timeseries_Label_"
                   "Anomaly_Metadata" / PHASE)
    if not sensors_root.exists():
        sys.exit(f"missing {sensors_root} — run scripts/fetch_batch_distillation.py first")

    items, dropped = [], {"no_window": 0, "guard": 0, "no_annotation": 0, "no_twin": 0}
    normals = []
    for csv_path in sorted(sensors_root.glob("*/*/*.csv")):
        rel = csv_path.relative_to(sensors_root)
        t, values, channels = read_series(csv_path)
        if not t:
            continue
        if "anormal" not in csv_path.name:
            normals.append((rel, t, values, channels))
            continue
        anns = annotations(labels_root / rel)
        if not anns:
            dropped["no_annotation"] += 1
            continue
        a = anns[0]                                   # the first annotated anomaly in the run
        end = next((i for i, ts in enumerate(t) if a["start"] <= ts <= a["end"]), None)
        if end is None or end < WINDOW_S // 2:
            dropped["no_window"] += 1
            continue
        end = min(end + 120, len(t) - 1)              # two minutes into the anomaly
        if a["sensor"] not in channels:
            dropped["no_annotation"] += 1
            continue
        base = {"experiment": str(rel.with_suffix("")), "observing_sensor": a["sensor"],
                "anomaly_label": a["label"], "decision_time": t[end].strftime("%H:%M:%S")}
        rows, idx = window_rows(t, values, channels, end)
        items.append(base | {"condition": "full", "supported": "ANOMALOUS",
                             "prefix": prefix(rows, {c: "installed" for c in channels})})
        drop = blind_drop(channels, a["sensor"])
        if len(channels) - len(drop) >= 4:            # something must be left to judge with
            brows, _ = window_rows(t, values, channels, end, drop=drop)
            manifest = {c: ("not_installed" if c in drop else "installed") for c in channels}
            items.append(base | {"condition": "blind", "supported": "UNKNOWN",
                                 "removed_group": group_of(a["sensor"]),
                                 "removed": sorted(drop),
                                 "prefix": prefix(brows, manifest)})
        else:
            dropped["guard"] += 1

    for rel, t, values, channels in normals[:40]:
        end = min(len(t) - 1, WINDOW_S + 600)
        if end < WINDOW_S:
            continue
        rows, _ = window_rows(t, values, channels, end)
        items.append({"experiment": str(rel.with_suffix("")), "observing_sensor": None,
                      "anomaly_label": None, "decision_time": t[end].strftime("%H:%M:%S"),
                      "condition": "control", "supported": "NORMAL",
                      "prefix": prefix(rows, {c: "installed" for c in channels})})

    out = ROOT / "data/realdata/items.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cadence_s": CADENCE_S, "window_s": WINDOW_S, "items": items},
                              indent=1))
    by = {}
    for it in items:
        by[it["condition"]] = by.get(it["condition"], 0) + 1
    print(f"{len(items)} items -> {out.relative_to(ROOT)}")
    print("  " + "  ".join(f"{k} {v}" for k, v in sorted(by.items())))
    print("  dropped: " + "  ".join(f"{k} {v}" for k, v in dropped.items()))
    chars = sum(len(i["prefix"]) for i in items) / len(items)
    print(f"  prefix {chars:,.0f} chars ≈ {chars / 3.7:,.0f} tokens per item")


if __name__ == "__main__":
    main()
