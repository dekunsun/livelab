"""The frame window is where a fabricated observation would enter this study.

A frame is an assertion about what the column looked like at a moment. Pick the wrong index and
the model is shown a minute that has nothing to do with the decision, which is worse than showing
it nothing. These tests pin the rules the registration and its deviation 1 state.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.make_vision_items import FRAMES, MIN_SPAN_S, TOL_S, WINDOW_S, pick_indices


def recording(first, n, cadence=2):
    """n frame times at a fixed cadence, the way the plant's sidecar lists them."""
    t0 = datetime.strptime(first, "%H:%M:%S")
    return [t0 + timedelta(seconds=cadence * i) for i in range(n)]


def test_frames_end_at_the_decision_and_cover_the_whole_window_when_the_camera_was_on():
    times = recording("10:00:00", 1800)                      # 10:00:00 - 10:59:58
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    idx, span = pick_indices(times, decision)
    assert len(idx) == FRAMES and span == WINDOW_S
    picked = [times[i] for i in idx]
    assert picked[0] == decision - timedelta(seconds=WINDOW_S)
    assert picked[-1] == decision
    gaps = {(picked[i + 1] - picked[i]).total_seconds() for i in range(FRAMES - 1)}
    assert gaps == {WINDOW_S / (FRAMES - 1)}


def test_a_late_starting_camera_gives_six_frames_over_the_part_it_recorded():
    """Deviation 1: the span shrinks to the intersection, the last frame stays at the decision."""
    times = recording("10:25:00", 900)                       # starts 5 min into the window
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    idx, span = pick_indices(times, decision)
    assert len(idx) == FRAMES
    assert span == 900                                       # 15 of the 20 minutes
    assert times[idx[0]] == times[0] and times[idx[-1]] == decision


def test_too_little_recording_drops_the_item_rather_than_shrinking_further():
    times = recording("10:32:00", 240)
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    idx, span = pick_indices(times, decision)
    assert idx == [] and span < MIN_SPAN_S


def test_a_decision_after_the_recording_stops_is_refused():
    times = recording("10:00:00", 600)                       # ends 10:19:58
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    assert pick_indices(times, decision)[0] == []


def test_a_gap_in_the_recording_refuses_the_frame_instead_of_substituting_a_far_one():
    times = recording("10:20:00", 300) + recording("10:35:00", 150)
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    idx, _ = pick_indices(times, decision)
    assert len(idx) < FRAMES                                 # the item is then dropped by main()


def test_every_frame_lands_within_the_stated_tolerance_of_its_target():
    times = recording("10:00:00", 1800)
    decision = datetime.strptime("10:40:00", "%H:%M:%S")
    idx, span = pick_indices(times, decision)
    start = decision - timedelta(seconds=span)
    for k, i in enumerate(idx):
        target = start + timedelta(seconds=span * k / (FRAMES - 1))
        assert abs((times[i] - target).total_seconds()) <= TOL_S


def test_no_frame_is_sent_twice():
    """Six copies of one still are not six looks at the column."""
    times = recording("10:00:00", 1800, cadence=400)
    decision = times[-1]
    idx, _ = pick_indices(times, decision)
    assert len(set(idx)) == len(idx)


@pytest.mark.parametrize("offset", [0, 61, 599])
def test_the_last_frame_is_the_decision_moment_wherever_the_recording_starts(offset):
    """Within one cadence step: at 2 s between frames an odd-second decision has no exact frame."""
    times = recording("10:00:00", 2000)
    decision = times[0] + timedelta(seconds=WINDOW_S + offset)
    idx, _ = pick_indices(times, decision)
    assert abs((times[idx[-1]] - decision).total_seconds()) <= 2
