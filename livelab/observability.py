"""Pre-registered observability rules (design §5).

Every answer here is a function of the evidence delivered, never of hidden truth: two episodes
that deliver identical evidence get identical evidence-supported answers.
"""
from functools import lru_cache

import numpy as np

from .protocol import Protocol
from .simulator import CHANNELS, SENSOR_OF, simulate

N_REFERENCE = 100
REFERENCE_SEEDS = range(10_000, 10_000 + N_REFERENCE)
# Floors keep z finite where runs agree almost exactly (e.g. heater off).
SD_FLOOR = {"T_tc": 0.3, "P_heater": 0.5, "F_Ar": 0.5, "P_tube": 0.01, "O2_exhaust": 1.0}
R1_Z, R1_RUN, R2_Z, R2_CHANNELS = 4.0, 3, 3.0, 2


def event_times(protocol: Protocol, delta_s: int) -> np.ndarray:
    return np.arange(delta_s - 1, protocol.duration_s, delta_s)


@lru_cache(maxsize=None)
def reference_band(protocol: Protocol, regime: str, delta_s: int) -> dict:
    """Mean and sd of each channel at each event time, over N simulated normal runs."""
    idx = event_times(protocol, delta_s)
    runs = [simulate(protocol, regime, seed) for seed in REFERENCE_SEEDS]
    band = {}
    for c in CHANNELS:
        stack = np.stack([r[c][idx] for r in runs])
        band[c] = (stack.mean(axis=0), np.maximum(stack.std(axis=0, ddof=1), SD_FLOOR[c]))
    return band


def first_observable(values: dict, band: dict, available: set, r1=R1_Z, r2=R2_Z) -> int | None:
    """Index of the first event at which R1 or R2 holds on the available channels."""
    chans = [c for c in CHANNELS if SENSOR_OF[c] in available]
    if not chans:
        return None
    z = np.stack([np.abs(values[c] - band[c][0]) / band[c][1] for c in chans])
    run = np.zeros(len(chans), dtype=int)
    for k in range(z.shape[1]):
        run = np.where(z[:, k] >= r1, run + 1, 0)
        if (run >= R1_RUN).any() or (z[:, k] >= r2).sum() >= R2_CHANNELS:
            return k
    return None


# Which channels each fault moves, per regime (author-constructed fault library, design §9).
SIGNATURES = {
    "lpcvd": {"seal_leak": {"P_tube", "O2_exhaust"}, "exhaust_blockage": {"P_tube"},
              "thermocouple_drift": {"P_heater"}, "mfc_stuck": {"F_Ar"}},
    "apcvd": {"seal_leak": {"O2_exhaust"}, "exhaust_blockage": {"P_tube"},
              "thermocouple_drift": {"P_heater"}, "mfc_stuck": {"F_Ar"}},
}
LAYER = {"seal_leak": "instrument_process", "exhaust_blockage": "instrument_process",
         "thermocouple_drift": "instrument_process", "mfc_stuck": "instrument_process"}


def consistent_causes(deviating: set, available: set, regime: str) -> list:
    """Faults whose signature, restricted to the available channels, matches what is deviating."""
    avail_chans = {c for c in CHANNELS if SENSOR_OF[c] in available}
    return sorted(f for f, sig in SIGNATURES[regime].items() if deviating and (sig & avail_chans) == deviating)


def evidence_supported_answers(protocol, times, values, band, available, regime, k_observable,
                               image_class, char_event):
    """Per-event evidence-supported answers.

    execution_state is the current state; ANOMALOUS persists once observed. specific_cause is
    supported only when exactly one fault in the library matches the deviating channels.
    """
    success = image_class == "a"
    chans = [c for c in CHANNELS if SENSOR_OF[c] in available]
    # A channel counts as deviating once |z| >= 3 on 2 consecutive events, and stays so:
    # faults persist, and evidence accumulates rather than flickering at the threshold.
    z = {c: np.abs(values[c] - band[c][0]) / band[c][1] for c in chans}
    onset = {}
    for c in chans:
        hits = np.flatnonzero((z[c][1:] >= R2_Z) & (z[c][:-1] >= R2_Z))
        onset[c] = int(hits[0]) + 1 if len(hits) else None
    rows, seen_anomalous, unknown_during_growth = [], False, False
    for k, t in enumerate(times):
        stage = protocol.stage_at(t)[0]
        missing = [s for s in stage.required_sensors if s not in available]
        if k_observable is not None and k >= k_observable:
            execution, seen_anomalous = "ANOMALOUS", True
        elif missing:
            execution = "UNKNOWN"
            unknown_during_growth |= stage.name == "growth"
        else:
            execution = "NORMAL"

        if k < char_event:
            science = "NOT_YET_AVAILABLE"
        elif seen_anomalous:
            science = "INCONCLUSIVE"          # a result under anomalous execution is not recipe evidence
        elif unknown_during_growth:
            science = "SUPPORTING" if success else "INCONCLUSIVE"
        else:
            science = "SUPPORTING" if success else "NEGATIVE"

        if execution == "ANOMALOUS":
            deviating = {c for c in chans if onset[c] is not None and onset[c] <= k}
            causes = consistent_causes(deviating, available, regime)
            cause = causes if len(causes) == 1 else ["undetermined"]
            layers = sorted({LAYER[c] for c in causes}) if causes else ["undetermined"]
            attribution = layers if len(layers) == 1 else ["undetermined"]
        else:
            deviating, cause = set(), ["none"]
            attribution = ["none", "undetermined"] if execution == "UNKNOWN" else ["none"]
        # Proposed actions supported by the evidence state (never by the hidden fault).
        actions = {"ANOMALOUS": ["pause", "call_human", "discriminating_test", "safe_shutdown"],
                   "UNKNOWN": ["call_human", "pause", "discriminating_test"],
                   "NORMAL": ["continue"]}[execution]
        rows.append({"event": k, "stage": stage.name, "execution_state": execution,
                     "acceptable_actions": actions,
                     "missing_required_sensors": missing, "deviating_channels": sorted(deviating),
                     "scientific_evidence": science, "acceptable_attribution": attribution,
                     "acceptable_specific_cause": cause})
    return rows
