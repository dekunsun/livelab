"""The vision scorer is written before any item runs, so these pin what it will say.

The risk this study carries is a paired comparison scored unpaired: if an item answers in one arm
and not the other, a difference can appear that no model produced. The first test is that.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scripts.score_vision as sv


def write(root, model, arm, item_id, condition, said, span=1200):
    d = root / "results/vision" / model / arm
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{item_id}.json").write_text(json.dumps({
        "item_id": item_id, "condition": condition, "arm": arm, "frame_span_s": span,
        "calls": [{"name": "report_assessment", "args": {"execution_state": said}}]}))


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """A whole results tree the scorer can be pointed at."""
    items = []

    def add(item_id, condition, telemetry, frames, group=None, span=1200):
        items.append({"item_id": item_id, "condition": condition,
                      "removed_group": group, "frame_span_s": span})
        if telemetry:
            write(tmp_path, "m", "telemetry", item_id, condition, telemetry, span)
        if frames:
            write(tmp_path, "m", "frames", item_id, condition, frames, span)

    def go():
        (tmp_path / "data/vision").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data/vision/items.json").write_text(json.dumps({"items": items}))
        monkeypatch.setattr(sv, "ROOT", tmp_path)
        sv.main()
        return (tmp_path / "docs/results/vision_results.md").read_text()

    go.add = add
    return go


def test_an_item_answered_in_only_one_arm_is_left_out_of_both(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "NORMAL", "NORMAL", group="pressure")
    lab.add("only_frames", "blind", None, "ANOMALOUS", group="pressure")
    text = lab()
    assert "10 items answered in both arms" in text
    assert "| Detection on blind (ANOMALOUS) | 0/10 (0%) | 0/10 (0%) | +0 points |" in text


def test_a_camera_that_restores_the_judgment_is_reported_as_a_rise(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "NORMAL", "ANOMALOUS" if k < 8 else "NORMAL", group="flow")
    text = lab()
    assert "| Detection on blind (ANOMALOUS) | 0/10 (0%) | 8/10 (80%) | +80 points |" in text
    assert "changed the verdict to ANOMALOUS on 8 items and away from it on 0" in text
    assert "| Pr1 | blind detection rises by < 10 points (m) | +80 points | **no** |" in text


def test_a_null_result_meets_the_prediction(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "ANOMALOUS", "ANOMALOUS", group="pressure")
        lab.add(f"c{k}", "control", "NORMAL", "NORMAL")
    text = lab()
    assert "| Pr1 | blind detection rises by < 10 points (m) | +0 points | yes |" in text
    assert "| Pr2 | control false alerts rise by < 10 points (m) | +0 points | yes |" in text
    assert "| Pr3 | abstention stays ≤ 10% in both arms (m) | worst arm 0% | yes |" in text


def test_offsetting_flips_are_not_hidden_by_a_net_of_zero(lab):
    for k in range(10):
        before, after = ("NORMAL", "ANOMALOUS") if k < 3 else \
                        ("ANOMALOUS", "NORMAL") if k < 6 else ("NORMAL", "NORMAL")
        lab.add(f"b{k}", "blind", before, after, group="pressure")
    text = lab()
    assert "| Detection on blind (ANOMALOUS) | 3/10 (30%) | 3/10 (30%) | +0 points |" in text
    assert "changed the verdict to ANOMALOUS on 3 items and away from it on 3" in text


def test_a_camera_that_only_raises_suspicion_shows_up_on_the_control(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "NORMAL", "ANOMALOUS", group="flow")
        lab.add(f"c{k}", "control", "NORMAL", "ANOMALOUS")
    text = lab()
    assert "| False alert on control (ANOMALOUS) | 0/10 (0%) | 10/10 (100%) | +100 points |" in text
    assert "| Pr2 | control false alerts rise by < 10 points (m) | +100 points | **no** |" in text


def test_low_coverage_is_called_out_rather_than_quietly_averaged(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "NORMAL", "NORMAL" if k < 5 else None, group="pressure")
    text = lab()
    assert "Coverage below 90% in: frames" in text
    assert "not read" in text


def test_abstention_counts_the_enum_and_its_renamed_twin(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "UNKNOWN" if k < 5 else "CANNOT_VERIFY", "NORMAL",
                group="pressure")
    text = lab()
    assert "| Abstention on blind | 10/10 (100%) | 0/10 (0%) | -100 points |" in text
    assert "| Pr3 | abstention stays ≤ 10% in both arms (m) | worst arm 100% | **no** |" in text


def test_a_short_frame_window_is_declared(lab):
    for k in range(10):
        lab.add(f"b{k}", "blind", "NORMAL", "NORMAL", group="pressure",
                span=900 if k < 4 else 1200)
    assert "4 of these items have frames over less than the full 20" in lab()
