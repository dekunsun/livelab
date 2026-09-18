"""The scorer must separate each degenerate observer by the metric built to catch it."""
import math

import pytest

from scripts.score_mocks import run_all


@pytest.fixture(scope="module")
def card():
    return {name: {k: (v[0] if isinstance(v, tuple) else v) for k, v in m.items()} for name, m in run_all().items()}


def test_oracle_scores_perfectly(card):
    o = card["oracle"]
    assert o["Detection"] == 1 and o["Attribution"] == 1 and o["Appropriate abstention"] == 1
    assert o["False alert"] == 0 and o["Over-abstention"] == 0 and o["Unsupported certainty"] == 0
    assert o["Obs. sensitivity"] == 1 and o["Obs. invariance"] == 1
    assert o["Action appropriate"] == 1 and o["First action quality"] == 1


def test_always_unknown_is_caught_by_over_abstention(card):
    u = card["always_unknown"]
    assert u["Over-abstention"] == 1 and u["Detection"] == 0
    assert math.isnan(u["Unsupported certainty"])       # it never commits to anything


def test_always_normal_is_caught_by_unsupported_certainty(card):
    assert card["always_normal"]["Unsupported certainty"] > 0.5
    assert card["always_normal"]["Detection"] == 0


def test_prior_matcher_is_caught_by_observability_sensitivity(card):
    p, a = card["prior_matcher"], card["observability_aware"]
    assert p["Detection"] == 1                            # it does see the anomalies...
    assert p["Obs. sensitivity"] < 0.5 < a["Obs. sensitivity"]   # ...but ignores which sensors exist
    assert p["Unsupported certainty"] > a["Unsupported certainty"]


def test_failure_blamer_is_caught_by_the_negative_control(card):
    assert card["failure_blamer"]["Negative called fault"] == 1
    assert card["failure_blamer"]["False alert"] > card["observability_aware"]["False alert"]
