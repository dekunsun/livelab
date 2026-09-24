"""Build the data for the LiveLab Monitor demo: every Core item, what the rules computed on it, and
what each model answered under runner v2.

Nothing here is new: telemetry comes from the frozen replays, rule outputs from the frozen truth
files (livelab.observability, a function of the delivered evidence only), answers from
results/core_v2/. The one addition is the reading a removed sensor would have shown, recomputed from
the episode's seed with the same simulator, so a viewer can see what the hidden twin hid.

  ./.venv/bin/python scripts/build_monitor_demo.py OUT.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import DATA, DELTA_S, FAMILIES, PROTOCOL, load_items  # noqa: E402
from livelab.episode import to_resolution  # noqa: E402
import numpy as np  # noqa: E402
from livelab.observability import R2_Z, consistent_causes, drift, event_times, reference_band  # noqa: E402
from livelab.protocol import PROTOCOLS  # noqa: E402
from livelab.simulator import CHANNELS, SENSOR_OF, Fault, simulate  # noqa: E402

RUNS = [("claude-opus-5-5", "V1.auto", "Claude Opus 5.5", 1), ("claude-opus-5-5", "V1.rep1.auto", "Claude Opus 5.5", 2),
        ("claude-opus-5-5", "V1.rep2.auto", "Claude Opus 5.5", 3), ("gemini-3.1-pro-preview", "V1.auto", "Gemini 3.1 Pro", 1),
        ("gemini-3.8-flash", "V1.auto", "Gemini 3.8 Flash", 1), ("gemini-3.8-live", "V1.auto", "Gemini 3.8 Live", 1)]


def regime_and_fault(it):
    fam = it["family"]
    if fam == "normal":
        n = int(it["episode_id"].rsplit("_", 1)[1]) - 1
        return ("lpcvd", "apcvd")[n % 2], None
    return FAMILIES[fam][0], FAMILIES[fam][1]


def answer(model, run, item_id):
    f = ROOT / "results/core_v2" / model / run / f"{item_id}.json"
    rec = json.loads(f.read_text())
    a = rec["calls"][-1]["args"] if rec["calls"] else None
    out = {"outcome": rec["outcome"], "reminders": len(rec.get("reminders") or [])}
    if a:
        out.update(state=a.get("execution_state"), cause=a.get("specific_cause"), action=a.get("proposed_action"),
                   missing=a.get("missing_evidence"),
                   evidence=[{"t": e.get("t_sim_s"), "ch": e.get("channel"), "obs": e.get("observation")}
                             for e in (a.get("evidence") or [])[:4]])
    else:
        spoken = rec.get("spoken") or ""
        out["spoken"] = (spoken if isinstance(spoken, str) else " ".join(spoken))[:420]
    return out


def main(out_path):
    protocol = PROTOCOLS[PROTOCOL]
    times = event_times(protocol, DELTA_S)
    items = []
    for it in load_items():
        regime, fault_type = regime_and_fault(it)
        events = [json.loads(line) for line in open(DATA / "replays" / f"{it['replay_id']}.jsonl")]
        truth = [json.loads(line) for line in open(DATA / "truth" / f"{it['replay_id']}.jsonl")]
        k = it["k"]
        band = reference_band(protocol, regime, DELTA_S)
        removed = set(it["removed"])
        available = {s for s in SENSOR_OF.values()} - removed
        shown = {c: [e["telemetry"][c] for e in events] for c in CHANNELS}
        hidden = {}
        if removed and "seed" in it:              # twins carry their seed: recompute what was removed
            f = Fault(fault_type, it["onset_s"], it["params"], None)
            trace = simulate(protocol, regime, it["seed"], f)
            for c in CHANNELS:
                if SENSOR_OF[c] in removed:
                    hidden[c] = [float(v) for v in to_resolution(c, trace[c][times])[:k + 1]]
        z = {}
        for c in CHANNELS:
            vals = shown[c] if shown[c][0] is not None else hidden.get(c)
            if vals is not None:          # as livelab.observability.zscore, on the delivered events
                x, (m, s, dm, ds) = np.array(vals[:k + 1]), band[c]
                zz = np.maximum(np.abs(x - m[:k + 1]) / s[:k + 1], np.abs(drift(x) - dm[:k + 1]) / ds[:k + 1])
                z[c] = [round(float(v), 1) for v in zz]
        row = truth[k]
        causes = (consistent_causes(set(row["deviating_channels"]), available, regime)
                  if row["execution_state"] == "ANOMALOUS" else [])
        items.append({
            "id": it["item_id"], "family": it["family"], "role": it["role"], "regime": regime,
            "fault": fault_type, "onset": it.get("onset_s"), "removed": sorted(removed), "k": k,
            "t": [e["t_sim_s"] for e in events], "stage": [e["stage"] for e in events],
            "values": {c: v for c, v in shown.items()}, "hidden": hidden, "z": z,
            "band": {c: {"mean": [round(float(x), 4) for x in band[c][0][:k + 1]],
                         "sd": [round(float(x), 4) for x in band[c][1][:k + 1]]} for c in CHANNELS},
            "required": events[0]["device_manifest"]["required_for_stage"],
            "rules": [{"state": r["execution_state"], "dev": r["deviating_channels"],
                       "missing": r["missing_required_sensors"]} for r in truth[:k + 1]],
            "causes": causes, "allowed": row["acceptable_actions"],
            "answers": [dict(answer(m, run, it["item_id"]), model=name, run=n) for m, run, name, n in RUNS],
        })
    Path(out_path).write_text(json.dumps({"z_flag": R2_Z, "items": items}, separators=(",", ":")))
    print(f"{len(items)} items -> {out_path} ({Path(out_path).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
