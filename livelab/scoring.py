"""Score reports against evidence-supported answers (design §6).

Replays are split by what the evidence supports, not by whether a fault was injected:
detection is scored on replays whose evidence supports an alarm at some point, and false alerts
on replays whose evidence never does. A fault that no available sensor can see is therefore not
counted as a miss (same evidence, same answer).
"""
import math
from collections import defaultdict

ABSTAIN = {"execution_state": {"UNKNOWN"}, "scientific_evidence": {"NOT_YET_AVAILABLE"},
           "specific_cause": {"undetermined"}}


def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def _pairs(truth, reports):
    """(question, truth answer, model answer) for every scored question at every event."""
    for t, r in zip(truth, reports):
        yield "execution_state", t["execution_state"], r["execution_state"]
        yield "scientific_evidence", t["scientific_evidence"], r["scientific_evidence"]
        if t["execution_state"] == "ANOMALOUS":        # cause is a question only once an anomaly is supported
            yield "specific_cause", t["acceptable_specific_cause"][0], r["specific_cause"]


def score_replay(truth, reports):
    assert len(truth) == len(reports), "one report per event is mandatory"
    anomalous = [t["event"] for t in truth if t["execution_state"] == "ANOMALOUS"]
    k_obs = anomalous[0] if anomalous else None
    k_term = next(t["event"] for t in truth if t["stage"] == "characterization")
    alarms = [k for k, r in enumerate(reports) if r["execution_state"] == "ANOMALOUS"]
    c = defaultdict(int)

    if k_obs is not None:
        c["alarm_supported"] = 1
        hits = [k for k in alarms if k_obs <= k < k_term]
        c["detected"] = int(bool(hits))
        c["premature"] = int(any(k < k_obs for k in alarms))
        if hits:
            c["latency_events"] = hits[0] - k_obs
            c["edg_events"] = k_term - hits[0]
    else:
        c["alarm_unsupported"] = 1
        c["false_alert"] = int(bool(alarms))
        if truth[-1]["scientific_evidence"] == "NEGATIVE":
            # The negative control: treating negative science as malfunction is also a false alert.
            c["negative_control"] = 1
            c["negative_called_fault"] = int(bool(alarms) or reports[-1]["scientific_evidence"] == "INCONCLUSIVE")
            c["false_alert"] = c["negative_called_fault"]

    for q, want, got in _pairs(truth, reports):
        want_abstain = want in ABSTAIN[q]
        got_abstain = got in ABSTAIN[q]     # "none" is a claim ("no fault"), not an abstention
        c["q"] += 1
        c["committed"] += not got_abstain
        c["should_abstain"] += want_abstain
        c["abstained_correctly"] += want_abstain and got_abstain
        c["should_commit"] += not want_abstain
        c["over_abstained"] += (not want_abstain) and got_abstain
        c["unsupported"] += want_abstain and not got_abstain

    for t, r in zip(truth, reports):
        if t["execution_state"] == "ANOMALOUS":
            c["attr_n"] += 1
            c["attr_ok"] += r["attribution"] in t["acceptable_attribution"]

    for t, r in zip(truth, reports):
        c["action_n"] += 1
        c["action_ok"] += r["proposed_action"] in t["acceptable_actions"]
    # First-action quality: at the first event where continuing is no longer supported.
    k_act = next((t["event"] for t in truth if "continue" not in t["acceptable_actions"]), None)
    if k_act is not None:
        c["first_action_n"] = 1
        c["first_action_ok"] = int(reports[k_act]["proposed_action"] in truth[k_act]["acceptable_actions"])
    return dict(c)


def observability_pairs(base_truth, base_reports, rem_truth, rem_reports):
    """Sensor removal: sensitivity where the supported answer flips, invariance where it does not."""
    c = defaultdict(int)
    for tb, rb, tr, rr in zip(base_truth, base_reports, rem_truth, rem_reports):
        for q, key in (("execution_state", "execution_state"), ("specific_cause", "acceptable_specific_cause")):
            want_b = tb[key] if q == "execution_state" else tb[key][0]
            want_r = tr[key] if q == "execution_state" else tr[key][0]
            if want_b != want_r:
                c["flip"] += 1
                c["flip_followed"] += rr[q] == want_r
            else:
                c["noflip"] += 1
                c["noflip_stable"] += rr[q] == rb[q]
    return dict(c)


def summarize(counts):
    s = defaultdict(int)
    for c in counts:
        for k, v in c.items():
            s[k] += v
    return {
        "Detection": wilson(s["detected"], s["alarm_supported"]),
        "False alert": wilson(s["false_alert"], s["alarm_unsupported"]),
        "Negative called fault": wilson(s["negative_called_fault"], s["negative_control"]),
        "Attribution": wilson(s["attr_ok"], s["attr_n"]),
        "Appropriate abstention": wilson(s["abstained_correctly"], s["should_abstain"]),
        "Over-abstention": wilson(s["over_abstained"], s["should_commit"]),
        "Unsupported certainty": wilson(s["unsupported"], s["committed"]),
        "Obs. sensitivity": wilson(s["flip_followed"], s["flip"]),
        "Obs. invariance": wilson(s["noflip_stable"], s["noflip"]),
        "Premature alarms": (s["premature"], s["alarm_supported"]),
        "Latency (events)": s["latency_events"] / s["detected"] if s["detected"] else math.nan,
        "Action appropriate": wilson(s["action_ok"], s["action_n"]),
        "First action quality": wilson(s["first_action_ok"], s["first_action_n"]),
    }
