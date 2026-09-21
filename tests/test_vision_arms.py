"""The follow-up arms (docs/vision_followup_preregistration.md) must each change one thing.

The camera study could not be read cleanly because its frames arm changed two things at once. These
tests pin that each follow-up arm differs from its neighbour in exactly the thing it is meant to
isolate, and that the donor footage is never the item's own.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_vision import ARMS, donor_map


def items():
    """Five experiments with a control run each, and two blind items from other experiments."""
    out = [{"item_id": f"c{k}", "experiment": f"exp{k}", "condition": "control"} for k in range(5)]
    out += [{"item_id": f"b{k}", "experiment": f"expb{k}", "condition": "blind"} for k in range(2)]
    return out


def test_each_follow_up_arm_changes_one_thing_from_the_frames_arm():
    announce, source = ARMS["frames"]
    assert ARMS["sentence"] == (announce, None)            # same sentence, nothing attached
    assert ARMS["other_frames"] == (announce, "donor")     # same sentence, someone else's frames
    assert ARMS["telemetry"] == (False, None)


def test_every_item_gets_a_control_donor_from_another_experiment():
    its = items()
    donors = donor_map(its)
    by_id = {i["item_id"]: i for i in its}
    assert set(donors) == set(by_id)
    for item_id, donor in donors.items():
        assert by_id[donor]["condition"] == "control"
        assert by_id[donor]["experiment"] != by_id[item_id]["experiment"]


def test_the_assignment_is_fixed_before_the_run():
    """Same items, same seed, same donors: nothing about it can be chosen after seeing answers."""
    assert donor_map(items()) == donor_map(list(reversed(items())))
    assert donor_map(items(), seed=1) != donor_map(items(), seed=0) or len(items()) < 3


def test_donors_are_spread_rather_than_one_run_for_everyone():
    donors = donor_map(items())
    assert len(set(donors.values())) >= 4
