"""The undersampling study: what a transient supports depends on how often you look.

Registered design: docs/undersampling_preregistration.md. A transient fault lasts `duration_s` and
then leaves no trace, so the same episode is missed, glimpsed or resolved depending only on the
delivery cadence.

This module is deliberately separate from `observability`. The glimpsed rule below - a single
deviating sample with no second one to confirm it supports UNKNOWN - is new, and the benchmark's
ground truth must not change under it (deviation 1). Nothing here is imported by the benchmark.
"""
import numpy as np

from .observability import CHANNELS, R2_Z, SENSOR_OF, event_times, zscore

CADENCES = (120, 30, 5)     # seconds between delivered observations
WINDOW_S = 1200             # the comparison window around the excursion, identical at every cadence
MISSED, GLIMPSED, RESOLVED = "missed", "glimpsed", "resolved"
SUPPORTED = {MISSED: "NORMAL", GLIMPSED: "UNKNOWN", RESOLVED: "ANOMALOUS"}


def inside(times: np.ndarray, fault) -> np.ndarray:
    """Indices of delivered samples that fall inside the excursion."""
    end = fault.t_fault_s + (fault.duration_s or 0)
    return np.flatnonzero((times >= fault.t_fault_s) & (times < end))


def deviating(values: dict, band: dict, available: set, z_min: float = R2_Z) -> np.ndarray:
    """Per-event: does any available channel depart by at least z_min?"""
    chans = [c for c in CHANNELS if SENSOR_OF[c] in available]
    if not chans:
        return np.zeros(len(next(iter(values.values()))), dtype=bool)
    return (np.stack([zscore(values, band, c) for c in chans]) >= z_min).any(axis=0)


def classify(times: np.ndarray, values: dict, band: dict, fault, available: set) -> tuple[str, str]:
    """(class, supported execution_state at the end of the window) for one episode at one cadence.

    The excursion has to be *seen* to count: a sample inside it that does not depart by z_min is
    not evidence of anything, so a class is decided on deviating samples, never on the hidden
    fault's timing. That keeps "same evidence, same answer" intact - the answer follows what was
    delivered, not what happened.
    """
    dev = deviating(values, band, available)
    seen = [k for k in inside(times, fault) if dev[k]]
    if len(seen) >= 2 and any(b - a == 1 for a, b in zip(seen, seen[1:])):
        return RESOLVED, SUPPORTED[RESOLVED]
    if len(seen) == 1:
        return GLIMPSED, SUPPORTED[GLIMPSED]
    return MISSED, SUPPORTED[MISSED]


def window_slice(times: np.ndarray, fault, window_s: int = WINDOW_S) -> np.ndarray:
    """The delivered events inside the comparison window, which is the same at every cadence."""
    mid = fault.t_fault_s + (fault.duration_s or 0) / 2
    lo, hi = mid - window_s / 2, mid + window_s / 2
    return np.flatnonzero((times >= lo) & (times < hi))


def cadence_events(protocol, cadence_s: int, fault, window_s: int = WINDOW_S):
    """(event indices in the window, their simulated times) for one cadence."""
    times = event_times(protocol, cadence_s)
    keep = window_slice(times, fault, window_s)
    return keep, times[keep]
