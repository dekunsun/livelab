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


def _pairs(truth, reports, image_truth=True):
    """(question, truth answer, model answer) for every scored question at every event.

    `image_truth=False` drops every scientific-evidence question whose answer comes from the
    micrograph. Those labels were assigned by a model and cannot be verified here (the captions
    state growth parameters, not morphology), so the benchmark reports what it claims without
    them; scripts/check_image_label_exposure.py measures the difference.
    """
    for t, r in zip(truth, reports):
        yield "execution_state", t["execution_state"], r["execution_state"]
        if image_truth or t["scientific_evidence"] == "NOT_YET_AVAILABLE":
            yield "scientific_evidence", t["scientific_evidence"], r["scientific_evidence"]
        if t["execution_state"] == "ANOMALOUS":        # cause is a question only once an anomaly is supported
            yield "specific_cause", t["acceptable_specific_cause"][0], r["specific_cause"]


def blind_to_images(truth):
    """Truth for an observer that never sees the characterization image (arms A, C-context).

    Without the image the outcome itself is unknowable, so the supported scientific evidence is
    NOT_YET_AVAILABLE, except that anomalous execution already makes any result INCONCLUSIVE.
    """
    out, anomalous = [], False
    for t in truth:
        anomalous |= t["execution_state"] == "ANOMALOUS"
        if t["scientific_evidence"] != "NOT_YET_AVAILABLE":
            t = dict(t, scientific_evidence="INCONCLUSIVE" if anomalous else "NOT_YET_AVAILABLE")
        out.append(t)
    return out


def score_replay(truth, reports, image_truth=True):
    assert len(truth) == len(reports), "one report per event is mandatory"
    anomalous = [t["event"] for t in truth if t["execution_state"] == "ANOMALOUS"]
    k_obs = anomalous[0] if anomalous else None
    k_term = next(t["event"] for t in truth if t["stage"] == "characterization")
    alarms = [k for k, r in enumerate(reports) if r["execution_state"] == "ANOMALOUS"]
    c = defaultdict(int)

    if k_obs is not None:
        c["alarm_supported"] = 1
        # An alarm counts once any available channel has started deviating, even if that is earlier
        # than the pre-registered R1/R2 rule; latency is then negative. An alarm before any deviation
        # is premature: the evidence did not exist yet.
        hits = [k for k in alarms if truth[k]["deviation_onset_reached"] and k < k_term]
        c["detected"] = int(bool(hits))
        c["premature"] = int(any(not truth[k]["deviation_onset_reached"] for k in alarms))
        if hits:
            c["latency_events"] = hits[0] - k_obs
            c["edg_events"] = k_term - hits[0]
        # Action latency: from the rule firing to the first proposed action that the anomalous
        # evidence supports. Recognizing an anomaly while recommending "continue" does not count.
        acts = [k for k in range(k_obs, len(truth)) if reports[k]["proposed_action"] != "continue"
                and reports[k]["proposed_action"] in truth[k]["acceptable_actions"]]
        c["action_latency_n"] = 1
        c["action_latency_events"] = (acts[0] - k_obs) if acts else (len(truth) - k_obs)
    else:
        c["alarm_unsupported"] = 1
        c["false_alert"] = int(bool(alarms))
        if truth[-1]["scientific_evidence"] == "NEGATIVE":
            # The negative control: treating negative science as malfunction is also a false alert.
            c["negative_control"] = 1
            c["negative_called_fault"] = int(bool(alarms) or reports[-1]["scientific_evidence"] == "INCONCLUSIVE")
            c["false_alert"] = c["negative_called_fault"]

    for q, want, got in _pairs(truth, reports, image_truth):
        want_abstain = want in ABSTAIN[q]
        got_abstain = got in ABSTAIN[q]     # "none" is a claim ("no fault"), not an abstention
        c["q"] += 1
        if got == "MISSING":
            # A missing report can only hurt: it neither abstains where it should, nor commits where
            # it should, and it is not a claim, so it does not enter unsupported certainty.
            c["missing"] += 1
            c["should_abstain"] += want_abstain
            c["should_commit"] += not want_abstain
            c["over_abstained"] += not want_abstain
            continue
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
    # First-action quality, separate from timing (timing is latency): is the model's first
    # non-continue action appropriate at the moment it is proposed? Never acting when action
    # was needed counts as a failure; never acting when none was needed is not scored.
    k_first = next((k for k, r in enumerate(reports) if r["proposed_action"] != "continue"), None)
    needed = any("continue" not in t["acceptable_actions"] for t in truth)
    if k_first is not None or needed:
        c["first_action_n"] = 1
        c["first_action_ok"] = int(k_first is not None and
                                   reports[k_first]["proposed_action"] in truth[k_first]["acceptable_actions"])
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
        "Missing reports": wilson(s["missing"], s["q"]),
        "Latency (events)": s["latency_events"] / s["detected"] if s["detected"] else math.nan,
        "Action latency (events)": (s["action_latency_events"] / s["action_latency_n"]
                                    if s["action_latency_n"] else math.nan),
        "Action appropriate": wilson(s["action_ok"], s["action_n"]),
        "First action quality": wilson(s["first_action_ok"], s["first_action_n"]),
    }


def score_runs(reports_by_replay: dict, index: dict, load_truth, sees_images: bool = True,
               image_truth: bool = True) -> dict:
    """Score a set of runs, including sensor-removal pairs when base and removal replays are both present."""
    counts, by_ep = [], {}
    for rid, reports in reports_by_replay.items():
        truth = load_truth(rid) if sees_images else blind_to_images(load_truth(rid))
        counts.append(score_replay(truth, reports, image_truth))
        by_ep.setdefault(index[rid]["episode_id"], {})[index[rid]["condition"]] = (truth, reports)
    for conds in by_ep.values():
        for cond, (t, r) in conds.items():
            if cond != "base" and "base" in conds:
                counts.append(observability_pairs(*conds["base"], t, r))
    return summarize(counts)
