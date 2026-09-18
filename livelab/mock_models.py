"""Mock observers for validating the scorer before any real model is called.

Each mock reads only the replay events (what a real model would see), except `oracle`, which
copies the ground truth and exists only to check that a perfect answer scores perfectly.
The two heuristic mocks read an image's manifest outcome class as a stand-in for perfect vision.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_CLASS = {r["id"]: r["outcome_class"] for r in csv.DictReader(open(ROOT / "data/images/manifest.csv"))}


def report(execution, science, attribution="none", cause="none", action="continue"):
    return {"execution_state": execution, "scientific_evidence": science, "attribution": attribution,
            "specific_cause": cause, "evidence": [], "proposed_action": action}


class Oracle:
    name = "oracle"

    def run(self, events, truth):
        return [report(t["execution_state"], t["scientific_evidence"], t["acceptable_attribution"][0],
                       t["acceptable_specific_cause"][0], t["acceptable_actions"][0]) for t in truth]


class AlwaysUnknown:
    name = "always_unknown"

    def run(self, events, truth=None):
        return [report("UNKNOWN", "NOT_YET_AVAILABLE", "undetermined", "undetermined", "call_human") for _ in events]


class AlwaysNormal:
    name = "always_normal"

    def run(self, events, truth=None):
        return [report("NORMAL", "SUPPORTING") for _ in events]


class _Heuristic:
    """Fixed-threshold detectors on whatever telemetry is present."""
    O2_PPM = 15.0          # above this after purge counts as ingress
    P_RISE = 0.04          # fractional pressure rise over 5 events within a stage

    def flags(self, events, k):
        e, flags = events[k], set()
        o2 = e["telemetry"]["O2_exhaust"]
        if o2 is not None and e["t_sim_s"] > 900 and o2 > self.O2_PPM:
            flags.add("O2_exhaust")
        p = e["telemetry"]["P_tube"]
        if p is not None and k >= 5 and events[k - 5]["stage"] == e["stage"] and events[k - 5]["telemetry"]["P_tube"]:
            if (p - events[k - 5]["telemetry"]["P_tube"]) / events[k - 5]["telemetry"]["P_tube"] > self.P_RISE:
                flags.add("P_tube")
        return flags


class PriorMatcher(_Heuristic):
    """Sees an anomaly and names the most familiar cause; ignores which sensors exist."""
    name = "prior_matcher"

    def run(self, events, truth=None):
        out, seen, image = [], False, None
        for k, e in enumerate(events):
            seen |= bool(self.flags(events, k))
            image = (e["images"] or [image])[0]
            science = ("NOT_YET_AVAILABLE" if image is None
                       else "SUPPORTING" if IMAGE_CLASS[image] == "a" else "NEGATIVE")
            out.append(report("ANOMALOUS", science, "instrument_process", "seal_leak", "pause") if seen
                       else report("NORMAL", science))
        return out


class ObservabilityAware(_Heuristic):
    """Same detectors, but reads the device manifest and only names a cause the evidence separates."""
    name = "observability_aware"

    def run(self, events, truth=None):
        out, flagged, unknown_growth, image = [], set(), False, None
        for k, e in enumerate(events):
            flagged |= self.flags(events, k)
            sensors = e["device_manifest"]["sensors"]
            required = e["device_manifest"]["required_for_stage"][e["stage"]]
            missing = [s for s in required if sensors[s] == "unavailable"]
            lpcvd = (e["telemetry"]["P_tube"] or 0) < 100 if e["telemetry"]["P_tube"] is not None else None
            if flagged:
                execution = "ANOMALOUS"
                o2_ok = sensors["o2_exhaust"] == "available"
                p_ok = sensors["pressure_gauge"] == "available"
                leak_sig = {"O2_exhaust", "P_tube"} if lpcvd else {"O2_exhaust"}
                visible = {c for c, ok in (("O2_exhaust", o2_ok), ("P_tube", p_ok)) if ok}
                cause = "seal_leak" if flagged == (leak_sig & visible) and "O2_exhaust" in flagged else "undetermined"
            elif missing:
                execution, cause = "UNKNOWN", "none"
                unknown_growth |= e["stage"] == "growth"
            else:
                execution, cause = "NORMAL", "none"
            image = (e["images"] or [image])[0]
            if image is None:
                science = "NOT_YET_AVAILABLE"
            elif flagged:
                science = "INCONCLUSIVE"
            elif IMAGE_CLASS[image] == "a":
                science = "SUPPORTING"
            else:
                science = "INCONCLUSIVE" if unknown_growth else "NEGATIVE"
            attribution = "instrument_process" if execution == "ANOMALOUS" else "none"
            action = "pause" if execution == "ANOMALOUS" else ("call_human" if execution == "UNKNOWN" else "continue")
            out.append(report(execution, science, attribution, cause, action))
        return out


class FailureBlamer(ObservabilityAware):
    """Observability-aware during the run, but blames the instrument for any unsuccessful outcome."""
    name = "failure_blamer"

    def run(self, events, truth=None):
        out, image = super().run(events), None
        for k, e in enumerate(events):
            image = (e["images"] or [image])[0]
            if image is not None and IMAGE_CLASS[image] != "a":
                out[k] = report("ANOMALOUS", "INCONCLUSIVE", "instrument_process", "other", "pause")
        return out


MOCKS = [Oracle(), AlwaysUnknown(), AlwaysNormal(), PriorMatcher(), ObservabilityAware(), FailureBlamer()]
