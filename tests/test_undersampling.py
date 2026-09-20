"""The undersampling study: the same fault is missed, glimpsed or resolved by cadence alone."""
import numpy as np

from livelab.observability import CHANNELS, SENSOR_OF, event_times, reference_band
from livelab.protocol import PROTOCOLS
from livelab.simulator import Fault, simulate
from livelab.undersampling import (CADENCES, GLIMPSED, MISSED, RESOLVED, classify, inside,
                                   window_slice)

PROTO = list(PROTOCOLS.values())[0]
ALL = set(SENSOR_OF.values())
BANDS = {c: reference_band(PROTO, "lpcvd", c) for c in CADENCES}


def run(duration_s, t_fault, amp=0.25, seed=7):
    f = Fault("transient_blockage", t_fault, {"pressure_offset_torr": amp}, duration_s)
    return f, simulate(PROTO, "lpcvd", seed, f)


def classes(duration_s, t_fault):
    f, trace = run(duration_s, t_fault)
    out = {}
    for cad in CADENCES:
        times = event_times(PROTO, cad)
        out[cad] = classify(times, {c: trace[c][times] for c in CHANNELS}, BANDS[cad], f, ALL)[0]
    return out


def test_a_transient_leaves_no_trace_once_it_clears():
    f, trace = run(60, 3000)
    after = trace["P_tube"][f.t_fault_s + f.duration_s + 30]
    before = trace["P_tube"][f.t_fault_s - 30]
    assert abs(after - before) < 0.1, "the excursion must not persist, or it is not a transient"


def test_cadence_alone_decides_what_is_supported():
    """The registered claim, as a test: same fault, same seed, different answer."""
    c = classes(20, 3000)
    assert c[120] == MISSED and c[5] == RESOLVED


def test_all_three_classes_are_reachable():
    assert classes(20, 3075)[30] == GLIMPSED        # one sample lands inside, nothing confirms it
    assert classes(60, 3060)[120] == GLIMPSED
    assert classes(240, 3000)[120] == RESOLVED      # long enough to be seen even at 120 s


def test_a_sample_inside_the_excursion_only_counts_if_it_deviates():
    """Class follows the delivered evidence, never the hidden fault's timing."""
    f, trace = run(60, 3000, amp=0.001)             # inside the noise: nothing is seen
    times = event_times(PROTO, 5)
    assert len(inside(times, f)) > 2                 # samples do fall inside
    assert classify(times, {c: trace[c][times] for c in CHANNELS}, BANDS[5], f, ALL)[0] == MISSED


def test_the_window_is_the_same_wall_clock_span_at_every_cadence():
    f, _ = run(60, 3000)
    spans = []
    for cad in CADENCES:
        times = event_times(PROTO, cad)
        keep = window_slice(times, f)
        spans.append((times[keep][0], times[keep][-1]))
    for lo, hi in spans:
        assert abs((hi - lo) - 1200) <= 2 * max(CADENCES)
    assert all(lo <= f.t_fault_s and hi >= f.t_fault_s + f.duration_s for lo, hi in spans)


def test_the_benchmark_truth_is_not_touched_by_this_module():
    """Deviation 1: the glimpsed rule is new and must not rewrite published ground truth."""
    import livelab.observability as obs
    src = open(obs.__file__).read()
    assert "undersampling" not in src and "GLIMPSED" not in src
