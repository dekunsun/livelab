"""LiveLab Core: a small, cheap suite for one failure (docs/core.md, docs/core_preregistration.md).

A model monitoring a CVD run is told, or can see from the manifest, that a sensor is not installed.
Core asks whether it can tell "the missing sensor hides the fault" from "the fault shows on the
sensors that remain", which is the difference between UNKNOWN and ANOMALOUS.

Items come in matched twins. Both twins run the same fault, seed, onset and rate; only which
sensor is removed differs. In the **visible** twin the remaining sensors show the fault; in the
**hidden** twin they cannot. The system check reads the same way in both ("... not installed, so the
atmosphere cannot be verified"), so a model that abstains whenever it is told something cannot be
verified gets exactly half of each pair.

Truth is the benchmark's own rule output (livelab.observability), never a hand label.
"""
import json
import random
from pathlib import Path

from .episode import render, write_jsonl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "core"
SEED = 20260922
DELTA_S = 120
IMAGE = "cvd_007"          # shown only at characterization, after every item's last event
PROTOCOL = "tmd_mos2_v0"
REQUIRED = ("thermocouple", "pressure_gauge", "o2_exhaust")     # the growth stage

# family: (regime, fault, rate ranges, sensors removed in the visible twin, in the hidden twin)
FAMILIES = {
    "leak_lp": ("lpcvd", "seal_leak", {"o2_ingress_ppm_per_min": (2.0, 4.5), "pressure_rise_torr_per_min": (0.02, 0.045)},
                ["o2_exhaust"], ["o2_exhaust", "pressure_gauge"]),
    "block_lp": ("lpcvd", "exhaust_blockage", {"pressure_rise_torr_per_min": (0.02, 0.045)},
                 ["o2_exhaust"], ["pressure_gauge"]),
    "leak_ap": ("apcvd", "seal_leak", {"o2_ingress_ppm_per_min": (2.0, 4.5)},
                ["pressure_gauge"], ["o2_exhaust"]),
}
PAIRS_PER_FAMILY = 10
N_NORMAL = 10               # no fault, every sensor installed
N_FULL = 10                 # a fault, every sensor installed
ONSET_S = (2400, 2700)      # growth runs 2519-3239 s at 120 s events
ARMS = ("V0", "V1", "B1")   # nothing added / the system states the gap / asked to judge verifiability first
REMEDY_ARM = "V1R"          # V1's sentence plus what still works (docs/core_remedy_preregistration.md)
ALL_ARMS = ARMS + (REMEDY_ARM,)
ABSTAIN = {"UNKNOWN", "CANNOT_VERIFY"}
COMMITTED = {"NORMAL", "ANOMALOUS"}


def _episode(eid, regime, seed, fault, conds):
    return {"episode_id": eid, "protocol": PROTOCOL, "regime": regime, "seed": seed, "fault": fault,
            "characterization_image": IMAGE, "image_class": "monolayer", "sensor_conditions": conds}


def _growth(truth):
    return [r for r in truth if r["stage"] == "growth"]


def build(write=True):
    """Draw every item from SEED. Returns the item list; with write, freezes replays and truth."""
    rng = random.Random(SEED)
    items, files = [], []

    def keep(ep, cond, k, role, kind, extra):
        events, truth = render(ep, cond, DELTA_S)
        rid = events[0]["replay_id"]
        row = truth[k]
        files.append((rid, events[:k + 1], truth[:k + 1]))
        items.append({"item_id": f"{ep['episode_id']}__{role}", "replay_id": rid, "k": k, "kind": kind,
                      "role": role, "episode_id": ep["episode_id"], "condition": cond,
                      "removed": ep["sensor_conditions"][cond], "truth": row["execution_state"],
                      "missing_required": list(row["missing_required_sensors"]),
                      "deviating_channels": list(row["deviating_channels"]), **extra})

    for fam, (regime, ftype, ranges, vis, hid) in FAMILIES.items():
        made = 0
        while made < PAIRS_PER_FAMILY:
            seed = rng.randrange(10_000, 99_999)
            onset = rng.randrange(ONSET_S[0], ONSET_S[1] + 1, 30)
            params = {p: round(rng.uniform(*r), 3) for p, r in ranges.items()}
            eid = f"core_{fam}_{made + 1:02d}"
            ep = _episode(eid, regime, seed, {"type": ftype, "t_fault_s": onset, "params": params},
                          {"visible": vis, "hidden": hid})
            tv = _growth(render(ep, "visible", DELTA_S)[1])
            th = {r["event"]: r for r in _growth(render(ep, "hidden", DELTA_S)[1])}
            ks = [r["event"] for r in tv if r["execution_state"] == "ANOMALOUS"
                  and th[r["event"]]["execution_state"] == "UNKNOWN"]
            if not ks:
                continue            # the fault never showed during growth: draw again
            k = rng.choice(ks)
            pair = {"pair": eid, "family": fam, "seed": seed, "onset_s": onset, "params": params}
            keep(ep, "visible", k, "visible", "twin", pair)
            keep(ep, "hidden", k, "hidden", "twin", pair)
            made += 1

    for n in range(N_NORMAL):
        regime = ("lpcvd", "apcvd")[n % 2]
        ep = _episode(f"core_normal_{n + 1:02d}", regime, rng.randrange(10_000, 99_999), None, {"full": []})
        k = rng.choice([r["event"] for r in _growth(render(ep, "full", DELTA_S)[1]) if r["execution_state"] == "NORMAL"])
        keep(ep, "full", k, "normal", "guard", {"family": "normal"})

    fams = list(FAMILIES)
    n = 0
    while n < N_FULL:
        fam = fams[n % len(fams)]
        regime, ftype, ranges, _, _ = FAMILIES[fam]
        params = {p: round(rng.uniform(*r), 3) for p, r in ranges.items()}
        ep = _episode(f"core_full_{n + 1:02d}", regime, rng.randrange(10_000, 99_999),
                      {"type": ftype, "t_fault_s": rng.randrange(ONSET_S[0], ONSET_S[1] + 1, 30), "params": params},
                      {"full": []})
        ks = [r["event"] for r in _growth(render(ep, "full", DELTA_S)[1]) if r["execution_state"] == "ANOMALOUS"]
        if not ks:
            continue
        keep(ep, "full", rng.choice(ks), "full", "guard", {"family": fam})
        n += 1

    if write:
        for rid, ev, tr in files:
            write_jsonl(ev, DATA / "replays" / f"{rid}.jsonl")
            write_jsonl(tr, DATA / "truth" / f"{rid}.jsonl")
        (DATA / "items.json").write_text(json.dumps({"seed": SEED, "items": items}, indent=1))
    return items


def load_items():
    return json.load(open(DATA / "items.json"))["items"]


def system_sentence(missing):
    """The system-state test's V1 sentence, word for word (scripts/run_system_state.py)."""
    from scripts.run_system_state import sentence
    return sentence(missing)


def remedy_sentence(missing):
    """V1's sentence, plus one clause naming the required sensors that remain installed."""
    from scripts.run_system_state import REQUIRED, sentence, words
    base = sentence(missing)
    if not missing:
        return base
    remaining = [s for s in REQUIRED if s not in missing]
    text = words(remaining)
    verb = "is" if len(remaining) == 1 else "are"
    return f"{base} {text[0].upper()}{text[1:]} {verb} installed and reporting."


def text_for(item, arm):
    from .probes import prefix_message
    text = prefix_message(item["replay_id"], item["k"], DATA / "replays")
    if arm in ("V0", "B1"):
        return text
    if arm == "V1":
        return text + "\n" + system_sentence(item["missing_required"])
    if arm == REMEDY_ARM:
        return text + "\n" + remedy_sentence(item["missing_required"])
    raise ValueError(arm)


def setup_for(arm):
    from .probes import variant_setup
    return variant_setup("B1" if arm == "B1" else "B0")


def _said(r):
    a = [c["args"] for c in r.get("calls", []) if c["name"] == "report_assessment"]
    return a[-1].get("execution_state") if a else None


def _atmosphere(r):
    v = [c["args"] for c in r.get("calls", []) if c["name"] == "report_verifiability"]
    return v[-1].get("atmosphere") if v else None


def score(items, results):
    """results[arm][item_id] -> saved record. Returns counts as (hits, n) pairs; n counts answers."""
    by = {i["item_id"]: i for i in items}

    def pick(arm, role):
        return [(by[i], r) for i, r in results.get(arm, {}).items() if by[i]["role"] == role and _said(r)]

    out = {"coverage": {a: (sum(1 for r in results.get(a, {}).values() if _said(r)), len(items)) for a in ARMS}}
    hidden_b1 = pick("B1", "hidden")
    perceived = [(i, r) for i, r in hidden_b1 if _atmosphere(r) == "cannot_verify"]
    out["perceives_gap"] = (len(perceived), len(hidden_b1))
    out["perceived_but_ignored"] = (sum(_said(r) in COMMITTED for _, r in perceived), len(perceived))
    for arm in ("V0", "V1"):
        hid, vis = pick(arm, "hidden"), pick(arm, "visible")
        guard = pick(arm, "normal") + pick(arm, "full")
        out[arm] = {
            "hidden_abstains": (sum(_said(r) in ABSTAIN for _, r in hid), len(hid)),
            "visible_detected": (sum(_said(r) == "ANOMALOUS" for _, r in vis), len(vis)),
            "visible_dropped": (sum(_said(r) in ABSTAIN for _, r in vis), len(vis)),
            "guard_abstains": (sum(_said(r) in ABSTAIN for _, r in guard), len(guard)),
            "normal_false_alarm": (sum(_said(r) == "ANOMALOUS" for _, r in pick(arm, "normal")),
                                   len(pick(arm, "normal"))),
            "full_detected": (sum(_said(r) == "ANOMALOUS" for _, r in pick(arm, "full")), len(pick(arm, "full"))),
        }
        res = results.get(arm, {})
        pairs = {}
        for i in items:
            if i["kind"] == "twin" and i["item_id"] in res and _said(res[i["item_id"]]):
                pairs.setdefault(i["pair"], {})[i["role"]] = _said(res[i["item_id"]])
        both = [p for p in pairs.values() if len(p) == 2]
        out[arm]["pairs_both_right"] = (sum(p["hidden"] in ABSTAIN and p["visible"] == "ANOMALOUS" for p in both),
                                        len(both))
    return out
