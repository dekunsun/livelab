"""Load an episode file and render its frozen evidence replay and its (separate) ground truth."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from .observability import evidence_supported_answers, event_times, first_observable, reference_band
from .protocol import PROTOCOLS
from .simulator import CHANNELS, SENSOR_OF, Fault, simulate

ROOT = Path(__file__).resolve().parent.parent
ALL_SENSORS = sorted(set(SENSOR_OF.values()))
DECIMALS = {"T_tc": 1, "P_heater": 1, "F_Ar": 1, "O2_exhaust": 1}   # P_tube: 4 significant figures


def to_resolution(channel, x):
    """Round readings to sensor resolution, far below the noise, so they cost fewer tokens."""
    if channel in DECIMALS:
        return np.round(x, DECIMALS[channel])
    return np.array([float(f"{v:.4g}") for v in x])


def load(path) -> dict:
    ep = yaml.safe_load(open(path))
    manifest = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/images/manifest.csv"))}
    ep["image_class"] = manifest[ep["characterization_image"]]["outcome_class"]
    return ep


def render(ep: dict, condition: str, delta_s: int = 120) -> tuple[list, list]:
    """Return (replay events shown to the model, ground-truth rows kept apart)."""
    protocol = PROTOCOLS[ep["protocol"]]
    removed = set(ep["sensor_conditions"][condition])
    available = set(ALL_SENSORS) - removed
    f = ep.get("fault")
    fault = Fault(f["type"], f["t_fault_s"], f.get("params") or {}) if f else None
    trace = simulate(protocol, ep["regime"], ep["seed"], fault)
    times = event_times(protocol, delta_s)
    values = {c: to_resolution(c, trace[c][times]) for c in CHANNELS}
    band = reference_band(protocol, ep["regime"], delta_s)
    k_obs = first_observable(values, band, available)
    char_event = next(k for k, t in enumerate(times) if protocol.stage_at(t)[0].name == "characterization")

    required = {s.name: list(s.required_sensors) for s in protocol.stages}
    manifest = {"sensors": {s: ("not_installed" if s in removed else "installed") for s in ALL_SENSORS},
                "required_for_stage": required}
    # The model sees only an opaque id: episode and condition names would give the answer away.
    replay_id = hashlib.sha256(f"{ep['episode_id']}/{condition}".encode()).hexdigest()[:12]
    events = []
    for k, t in enumerate(times):
        stage = protocol.stage_at(t)[0].name
        telemetry = {c: (None if SENSOR_OF[c] in removed else float(values[c][k])) for c in CHANNELS}
        telemetry["status"] = str(trace["status"][t])
        t_set = trace["T_set"][t]
        events.append({
            "replay_id": replay_id, "event": k, "t_sim_s": int(t) + 1,
            "stage": stage,
            "setpoints": {"T_set": None if np.isnan(t_set) else round(float(t_set), 1),
                          "F_Ar_set": float(trace["F_Ar_set"][t])},
            "telemetry": telemetry, "device_manifest": manifest,
            "images": [ep["characterization_image"]] if k == char_event else [],
        })
    truth = evidence_supported_answers(protocol, times, values, band, available, ep["regime"], k_obs,
                                       ep["image_class"], char_event)
    for row in truth:
        row.update(replay_id=replay_id, episode_id=ep["episode_id"], condition=condition,
                   t_sim_s=int(times[row["event"]]) + 1)
    return events, truth


def write_jsonl(rows, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows)
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()
