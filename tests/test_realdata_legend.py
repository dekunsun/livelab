"""The plant description the model reads must say what each instrument actually measures.

LEGEND_V1, used by every real-plant run published before 2026-09-21, was wrong in four places, and
the models' false alerts on fault-free runs cite exactly the channel it got most wrong. These tests
hold LEGEND_V2 to the dataset's own annotations (data/realdata/tags.csv), and keep V1 byte-exact so
published runs stay reproducible.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab import realdata_prompt as rp

TAGS = {r["tag"]: r for r in csv.DictReader(open(ROOT / "data/realdata/tags.csv"))}


def flat(text):
    return re.sub(r"\s+", " ", text)


def test_the_two_versions_differ_only_in_the_legend():
    """The first attempt at this fix produced a V2 identical to V1 and nothing noticed."""
    assert rp.SYSTEM_INSTRUCTION_V1 != rp.SYSTEM_INSTRUCTION_V2
    assert rp.SYSTEM_INSTRUCTION_V1.replace(rp.LEGEND_V1, "") == \
        rp.SYSTEM_INSTRUCTION_V2.replace(rp.LEGEND_V2, "")


def test_runners_still_use_what_the_published_runs_used():
    assert rp.SYSTEM_INSTRUCTION == rp.SYSTEM_INSTRUCTION_V1


def test_every_heater_temperature_is_called_a_heater():
    legend = flat(rp.LEGEND_V2)
    for tag, row in TAGS.items():
        if row["role"] == "heater temperature":
            heater = "H" + tag[1:]
            assert tag in legend and heater in legend, tag


def test_reflux_and_distillate_are_the_right_way_round():
    legend = flat(rp.LEGEND_V2)
    assert TAGS["FT703"]["feature_of_interest"] == "Distillate stream"
    assert "FT703 distillate flow" in legend and "FT704 reflux flow" in legend


def test_cooling_water_is_not_called_a_ratio():
    legend = flat(rp.LEGEND_V2)
    assert "FYI702 cooling-water flow" in legend and "ratio" not in legend


def test_every_instrument_in_the_items_is_described():
    legend = flat(rp.LEGEND_V2)
    for tag in TAGS:
        assert tag in legend, tag


def test_the_old_legend_is_the_one_that_was_published():
    assert "along the column, reboiler to condenser" in rp.LEGEND_V1
    assert "FT703 reflux flow" in flat(rp.LEGEND_V1)


def test_the_heater_pattern_does_not_match_the_reflux_flow():
    """A first count matched FT704 (a flow) as T704 (a heater), and was published for an hour."""
    from scripts.score_realdata import HEATER
    for tag in ("T701", "T702", "T704", "T706", "T708"):
        assert HEATER.search(f'"channel": "{tag}"'), tag
    for tag in ("FT704", "T703", "T705", "T709", "T711", "T712", "FT703"):
        assert not HEATER.search(f'"channel": "{tag}"'), tag
