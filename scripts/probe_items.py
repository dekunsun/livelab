"""Generate the probe items (docs/probe_preregistration.md) from the truth files and the fault
library, and write data/probes/items.json. Committed before any probe runs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.observability import SIGNATURES  # noqa: E402
from livelab.simulator import SENSOR_OF  # noqa: E402

K = 24
ALL = sorted(set(SENSOR_OF.values()))
SENSOR_SETS = {"full": [], "no_o2": ["o2_exhaust"], "no_pressure": ["pressure_gauge"],
               "no_o2_no_pressure": ["o2_exhaust", "pressure_gauge"],
               "no_heater_power": ["heater_power"], "no_mfc": ["mfc_ar"]}
CONDITION_CHANNELS = {"atmosphere": {"P_tube", "O2_exhaust"}, "temperature": {"T_tc", "P_heater"},
                      "gas_flow": {"F_Ar"}}
CONDITION_SENSORS = {"atmosphere": {"pressure_gauge", "o2_exhaust"}, "temperature": {"thermocouple"},
                     "gas_flow": {"mfc_ar"}}


def load_jsonl(p):
    return [json.loads(line) for line in open(p)]


def in_context_items():
    index = json.load(open(ROOT / "data/replays/INDEX.json"))
    items = []
    for rid, m in sorted(index.items(), key=lambda x: (x[1]["episode_id"], x[1]["condition"])):
        t = load_jsonl(ROOT / f"data/truth/{rid}.jsonl")[K]
        manifest = load_jsonl(ROOT / f"data/replays/{rid}.jsonl")[K]["device_manifest"]["sensors"]
        installed = {s for s, v in manifest.items() if v == "installed"}
        verif = {}
        for cond, chans in CONDITION_CHANNELS.items():
            if chans & set(t["deviating_channels"]):
                verif[cond] = "anomalous"
            elif CONDITION_SENSORS[cond] <= installed:
                verif[cond] = "verified"
            else:
                verif[cond] = "cannot_verify"
        items.append({"item_id": f"{m['episode_id']}__{m['condition']}", "replay_id": rid, "k": K,
                      "set": {"UNKNOWN": "U", "NORMAL": "N", "ANOMALOUS": "A"}[t["execution_state"]],
                      "truth_execution_state": t["execution_state"], "truth_verifiability": verif})
    return items


def p1_items():
    items = []
    for regime in ("lpcvd", "apcvd"):
        sigs = SIGNATURES[regime]
        for set_name, removed in SENSOR_SETS.items():
            chans = {c for c, s in SENSOR_OF.items() if s not in removed}
            for fault in ("seal_leak", "exhaust_blockage", "thermocouple_drift", "mfc_stuck"):
                seen = sorted(sigs[fault] & chans)
                items.append({"item_id": f"P1det__{regime}__{set_name}__{fault}", "kind": "detectable",
                              "regime": regime, "installed": [s for s in ALL if s not in removed],
                              "fault": fault, "truth": "yes" if seen else "no", "truth_channels": seen})
            a, b = sigs["seal_leak"] & chans, sigs["exhaust_blockage"] & chans
            items.append({"item_id": f"P1dist__{regime}__{set_name}", "kind": "distinguishable",
                          "regime": regime, "installed": [s for s in ALL if s not in removed],
                          "truth": "yes" if (a and b and a != b) else "no"})
    return items


def main():
    ctx, p1 = in_context_items(), p1_items()
    out = ROOT / "data/probes/items.json"
    out.write_text(json.dumps({"k": K, "in_context": ctx, "p1": p1}, indent=1))
    from collections import Counter
    print("in-context:", Counter(i["set"] for i in ctx), "| P1:", Counter(i["kind"] for i in p1),
          "| P1 truth yes/no:", Counter((i["kind"], i["truth"]) for i in p1))


if __name__ == "__main__":
    main()
