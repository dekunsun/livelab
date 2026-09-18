import glob

import pytest

from livelab.episode import load, render
from livelab.observability import event_times, first_observable, reference_band
from livelab.protocol import TMD_MOS2_V0
from livelab.simulator import SENSOR_OF, simulate

PILOTS = sorted(glob.glob("scenarios/pilot/*.yaml"))
TRUTH_KEYS = {"execution_state", "scientific_evidence", "acceptable_attribution",
              "acceptable_specific_cause", "deviating_channels", "missing_required_sensors"}


def cases():
    for path in PILOTS:
        ep = load(path)
        for cond in ep["sensor_conditions"]:
            yield pytest.param(ep, cond, id=f"{ep['episode_id']}-{cond}")


@pytest.mark.parametrize("ep,cond", list(cases()))
def test_computed_truth_matches_declared_expectation(ep, cond):
    _, truth = render(ep, cond)
    want = ep["expected"][cond]
    growth = [r for r in truth if r["stage"] == "growth"]
    if "growth_after_fault" in want:
        last = growth[-1]
        assert last["execution_state"] == want["growth_after_fault"]["execution_state"]
        assert last["acceptable_specific_cause"] == [want["growth_after_fault"]["specific_cause"]]
    if "growth" in want:
        assert {r["execution_state"] for r in growth} == {want["growth"]["execution_state"]}
    assert truth[-1]["scientific_evidence"] == want["final_scientific_evidence"]


@pytest.mark.parametrize("ep,cond", list(cases()))
def test_replay_never_contains_ground_truth(ep, cond):
    events, _ = render(ep, cond)
    for e in events:
        assert not TRUTH_KEYS & set(e), e["event"]
        text = str(e).lower()
        for word in ("fault", "leak", "blockage", "drift", "success", "negative", ep["episode_id"]):
            assert word not in text, word


def test_same_evidence_gives_same_answer():
    """With O2 and pressure removed, a leak and a clean run deliver identical evidence during growth."""
    leak = render(load("scenarios/pilot/cvd_seal_leak_lpcvd.yaml"), "no_o2_no_pressure")
    clean = render(load("scenarios/pilot/cvd_nofault_lpcvd_success.yaml"), "no_o2_no_pressure")
    for (e1, t1), (e2, t2) in zip(zip(*leak), zip(*clean)):
        if e1["images"] or e2["images"]:
            break                      # characterization images differ by design
        assert e1["telemetry"] == e2["telemetry"]
        assert (t1["execution_state"], t1["acceptable_specific_cause"]) == \
               (t2["execution_state"], t2["acceptable_specific_cause"])


def test_cascade_certainty_follows_sensors():
    ep = load("scenarios/pilot/cvd_seal_leak_lpcvd.yaml")
    final_growth = {c: [r for r in render(ep, c)[1] if r["stage"] == "growth"][-1] for c in ep["sensor_conditions"]}
    assert final_growth["base"]["acceptable_specific_cause"] == ["seal_leak"]
    assert final_growth["no_o2"]["execution_state"] == "ANOMALOUS"
    assert final_growth["no_o2"]["acceptable_specific_cause"] == ["undetermined"]
    assert final_growth["no_o2"]["acceptable_attribution"] == ["instrument_process"]  # layer is known
    assert final_growth["no_o2_no_pressure"]["execution_state"] == "UNKNOWN"


def test_nofault_pilots_are_quiet_under_the_rule():
    for path in PILOTS:
        ep = load(path)
        if ep["fault"] is None:
            _, truth = render(ep, "base")
            assert all(r["execution_state"] == "NORMAL" for r in truth), ep["episode_id"]


def test_rule_false_positive_rate_on_normal_runs():
    times = event_times(TMD_MOS2_V0, 120)
    band = reference_band(TMD_MOS2_V0, "lpcvd", 120)
    sensors = set(SENSOR_OF.values())
    hits = sum(first_observable({c: simulate(TMD_MOS2_V0, "lpcvd", s)[c][times] for c in band}, band, sensors)
               is not None for s in range(200))
    assert hits / 200 <= 0.03
