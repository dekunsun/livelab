"""Generate the undersampling study's items: one window, delivered at three cadences.

Registered design: docs/undersampling_preregistration.md. Each episode is a transient fault that
clears itself; each item is that episode's comparison window rendered at one cadence, as a single
turn in the benchmark's own compact event format. The class (missed / glimpsed / resolved) and the
supported answer are computed from the delivered samples and written beside each item.

The script refuses to write if the classes do not come out as the design intends, so the item set
cannot drift away from the registration without someone noticing.

  ./.venv/bin/python scripts/make_transient_items.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.episode import ALL_SENSORS, to_resolution  # noqa: E402
from livelab.observability import CHANNELS, SENSOR_OF, event_times, reference_band  # noqa: E402
from livelab.protocol import PROTOCOLS  # noqa: E402
from livelab.prompting import event_message  # noqa: E402
from livelab.simulator import Fault, simulate  # noqa: E402
from livelab.undersampling import CADENCES, GLIMPSED, MISSED, RESOLVED, classify, window_slice  # noqa: E402

PROTO = PROTOCOLS["tmd_mos2_v0"]
REGIME = "lpcvd"
AMPLITUDE = {"transient_blockage": {"pressure_offset_torr": 0.25},
             "transient_pressure_spike": {"pressure_offset_torr": 0.25},
             "transient_mfc_dropout": {"dropout_fraction": 0.55}}

# duration and onset are chosen so that the three classes are all populated, and the intended class
# is asserted below rather than discovered afterwards.
SHAPES = [(20, 3000, {120: MISSED, 30: MISSED, 5: RESOLVED}),
          (20, 3075, {120: MISSED, 30: GLIMPSED, 5: RESOLVED}),
          (60, 3060, {120: GLIMPSED, 30: RESOLVED, 5: RESOLVED}),
          (240, 3000, {120: RESOLVED, 30: RESOLVED, 5: RESOLVED})]
SEEDS = {"transient_blockage": 7, "transient_pressure_spike": 11, "transient_mfc_dropout": 13}


def rows_for(trace, times, keep, fault_id):
    """Events in the benchmark's own shape, so the model reads exactly what it reads there."""
    manifest = {"sensors": {s: "installed" for s in ALL_SENSORS}}
    out = []
    for n, k in enumerate(keep):
        t = int(times[k])
        stage, _, _ = PROTO.stage_at(t)
        out.append({"replay_id": fault_id, "event": n, "t_sim_s": t + 1, "stage": stage.name,
                    "setpoints": {"T_set": None if PROTO.setpoint(t) is None else float(PROTO.setpoint(t)),
                                  "F_Ar_set": float(stage.f_ar_sccm)},
                    "telemetry": {c: float(to_resolution(c, trace[c][t:t + 1])[0]) for c in CHANNELS}
                    | {"status": "running"},
                    "device_manifest": manifest, "images": []})
    return out


def prefix(rows):
    lines, previous = [], None
    for r in rows:
        text, _ = event_message(r, "A", None, ROOT / "data/images/cvd", None, previous)
        lines.append(text)
        previous = r
    return "\n".join(lines)


def main():
    bands = {c: reference_band(PROTO, REGIME, c) for c in CADENCES}
    available = set(SENSOR_OF.values())
    items, problems = [], []
    for ftype, params in AMPLITUDE.items():
        for duration_s, t0, intended in SHAPES:
            fault = Fault(ftype, t0, params, duration_s)
            trace = simulate(PROTO, REGIME, SEEDS[ftype], fault)
            ep_id = f"{ftype}__d{duration_s}__t{t0}"
            for cad in CADENCES:
                times = event_times(PROTO, cad)
                values = {c: to_resolution(c, trace[c][times]) for c in CHANNELS}
                cls, answer = classify(times, values, bands[cad], fault, available)
                if cls != intended[cad]:
                    problems.append(f"{ep_id} @ {cad}s: designed {intended[cad]}, got {cls}")
                keep = window_slice(times, fault)
                rows = rows_for(trace, times, keep, f"{ep_id}__{cad}s")
                items.append({"item_id": f"{ep_id}__{cad}s", "episode": ep_id, "fault_type": ftype,
                              "duration_s": duration_s, "t_fault_s": t0, "cadence_s": cad,
                              "events": len(rows), "class": cls, "supported": answer,
                              "prefix": prefix(rows)})
    if problems:
        sys.exit("the item set no longer matches the registered design:\n  " + "\n  ".join(problems))

    out = ROOT / "data/transients/items.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cadences": list(CADENCES), "items": items}, indent=1))
    counts = {c: {k: 0 for k in (MISSED, GLIMPSED, RESOLVED)} for c in CADENCES}
    for it in items:
        counts[it["cadence_s"]][it["class"]] += 1
    print(f"{len(items)} items -> {out.relative_to(ROOT)}")
    for c in CADENCES:
        ev = next(i["events"] for i in items if i["cadence_s"] == c)
        print(f"  {c:3}s  {ev:3} events/item   " +
              "  ".join(f"{k} {v}" for k, v in counts[c].items()))


if __name__ == "__main__":
    main()
