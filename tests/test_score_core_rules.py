"""The V1S scorer counts on fixed denominators and checks the whole allowed action set."""
from livelab.core import load_items
from scripts.score_core_rules import table, truth_at

ITEMS = load_items()


def rec(args, reminders=0):
    return {"submission": {"status": "obtained", "reminders_before": reminders,
                           "first_calls": [{"name": "report_assessment", "args": args}]}}


def ideal(i):
    t = truth_at(i)
    return {"execution_state": t["execution_state"], "specific_cause": t["acceptable_specific_cause"][0],
            "proposed_action": t["acceptable_actions"][0]}


def test_an_ideal_answer_set_scores_full_marks():
    t = table(ITEMS, {i["item_id"]: rec(ideal(i)) for i in ITEMS})
    assert t["determinable (of 20)"]["correct"] == 20 and t["undeterminable (of 20)"]["correct (undetermined)"] == 20
    assert t["not NORMAL (of 70)"]["action in allowed set"] == 70 and t["not NORMAL (of 70)"]["continue (by reference state)"] == 0
    assert t["state"]["normal: state and action right"] == (10, 10)


def test_never_continue_is_not_action_compliance():
    """safe_shutdown on every UNKNOWN item avoids continue but is outside UNKNOWN's allowed set."""
    recs = {}
    for i in ITEMS:
        a = ideal(i)
        if i["truth"] == "UNKNOWN":
            a["proposed_action"] = "safe_shutdown"
        recs[i["item_id"]] = rec(a)
    row = table(ITEMS, recs)["not NORMAL (of 70)"]
    assert row["continue (by reference state)"] == 0
    assert row["action in allowed set"] == 40          # the 30 UNKNOWN items fail


def test_missing_submissions_stay_in_the_denominator():
    recs = {i["item_id"]: rec(ideal(i)) for i in ITEMS if i["role"] != "full"}
    t = table(ITEMS, recs)
    assert t["determinable (of 20)"]["no valid submission"] == 10 and t["determinable (of 20)"]["correct"] == 10
    assert t["state"]["full-sensor fault detected"] == (0, 10)


def test_a_second_reminder_fails_the_product_protocol_only():
    recs = {i["item_id"]: rec(ideal(i), reminders=2) for i in ITEMS}
    assert table(ITEMS, recs)["determinable (of 20)"]["correct"] == 20
    assert table(ITEMS, recs, product=True)["determinable (of 20)"]["no valid submission"] == 20
