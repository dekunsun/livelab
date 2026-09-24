"""LiveLab Core: the frozen items are what the registration says, and scoring counts the right things."""
import json

from livelab.core import ARMS, REMEDY_ARM, build, load_items, remedy_sentence, score, text_for


ITEMS = load_items()
BY = {i["item_id"]: i for i in ITEMS}
TWINS = [i for i in ITEMS if i["kind"] == "twin"]


def test_frozen_items_regenerate_from_the_seed():
    assert build(write=False) == ITEMS


def test_counts_and_truth_are_as_registered():
    roles = {}
    for i in ITEMS:
        roles.setdefault((i["role"], i["truth"]), 0)
        roles[(i["role"], i["truth"])] += 1
    assert roles == {("visible", "ANOMALOUS"): 30, ("hidden", "UNKNOWN"): 30,
                     ("normal", "NORMAL"): 10, ("full", "ANOMALOUS"): 10}


def test_twins_differ_only_in_the_removed_sensor():
    pairs = {}
    for i in TWINS:
        pairs.setdefault(i["pair"], {})[i["role"]] = i
    assert len(pairs) == 30
    for p in pairs.values():
        v, h = p["visible"], p["hidden"]
        for key in ("seed", "onset_s", "params", "k", "family"):
            assert v[key] == h[key], key
        assert v["removed"] != h["removed"]
        assert v["missing_required"] and h["missing_required"]     # the system reports a gap in both
        assert v["deviating_channels"] and not h["deviating_channels"]


def test_every_item_is_in_growth_and_carries_no_answer():
    for i in ITEMS:
        lines = text_for(i, "V0").splitlines()
        assert len(lines) == i["k"] + 1
        last = json.loads(lines[-1])
        assert last["stage"] == "growth"
        text = "\n".join(lines).lower()
        for word in ("leak", "blockage", "fault", "unknown", "anomalous", "visible", "hidden", "core_"):
            assert word not in text, (i["item_id"], word)


def test_arms_add_only_the_system_sentence():
    for i in ITEMS[:6] + ITEMS[-4:]:
        v0, v1, b1 = (text_for(i, a) for a in ARMS)
        assert b1 == v0 and v1.startswith(v0 + "\n")
        added = v1[len(v0) + 1:]
        assert added.startswith("System check for this event:")
        assert ("cannot be verified" in added) == bool(i["missing_required"])


def test_remedy_sentence_names_only_the_remaining_required_sensors():
    from scripts.run_system_state import sentence
    s = remedy_sentence(["o2_exhaust"])
    assert s.startswith(sentence(["o2_exhaust"]))
    assert s.endswith("The control thermocouple and the tube pressure gauge are installed and reporting.")
    s2 = remedy_sentence(["pressure_gauge", "o2_exhaust"])
    assert s2.endswith("The control thermocouple is installed and reporting.")
    s3 = remedy_sentence(["pressure_gauge"])
    assert "exhaust O2 sensor are installed and reporting." in s3        # casing preserved mid-sentence
    assert remedy_sentence([]) == sentence([])


def test_v1r_appends_only_the_remedy_sentence():
    for i in ITEMS[:4] + ITEMS[-2:]:
        v0, v1r = text_for(i, "V0"), text_for(i, REMEDY_ARM)
        assert v1r.startswith(v0 + "\n")
        added = v1r[len(v0) + 1:]
        assert added.startswith("System check for this event:")
        if i["missing_required"]:
            assert added.endswith("installed and reporting.")
        else:
            assert v1r == text_for(i, "V1")     # nothing missing: identical to V1


def rec(state, atmosphere=None):
    calls = []
    if atmosphere:
        calls.append({"name": "report_verifiability", "args": {"atmosphere": atmosphere}})
    calls.append({"name": "report_assessment", "args": {"execution_state": state}})
    return {"calls": calls}


def test_a_model_that_abstains_whenever_told_gets_no_pair_right():
    told = {i["item_id"]: rec("UNKNOWN" if i["missing_required"] else ("NORMAL" if i["truth"] == "NORMAL" else "ANOMALOUS"))
            for i in ITEMS}
    s = score(ITEMS, {"V1": told})
    assert s["V1"]["hidden_abstains"] == (30, 30)
    assert s["V1"]["visible_detected"] == (0, 30) and s["V1"]["visible_dropped"] == (30, 30)
    assert s["V1"]["pairs_both_right"] == (0, 30)
    assert s["V1"]["guard_abstains"] == (0, 20)


def test_a_right_model_gets_every_pair_and_perceived_but_ignored_counts_commitments():
    right = {i["item_id"]: rec(i["truth"]) for i in ITEMS}
    s = score(ITEMS, {"V1": right, "V0": right})
    assert s["V1"]["pairs_both_right"] == (30, 30) and s["V0"]["normal_false_alarm"] == (0, 10)
    b1 = {i["item_id"]: rec("NORMAL" if n % 3 else "UNKNOWN", "cannot_verify") for n, i in enumerate(TWINS)
          if i["role"] == "hidden"}
    s = score(ITEMS, {"B1": b1})
    assert s["perceives_gap"] == (30, 30)
    assert s["perceived_but_ignored"] == (20, 30)
    assert s["coverage"]["B1"] == (30, 80)


def test_v1s_adds_only_the_rules_block_to_the_instruction():
    from livelab.core import RULES_ARM, rules_block, setup_for
    for i in ITEMS:                                   # every item's message is V1's, byte for byte
        assert text_for(i, RULES_ARM) == text_for(i, "V1")
    ins, tools, req = setup_for(RULES_ARM)
    ins1, tools1, req1 = setup_for("V1")
    assert ins == ins1 + rules_block() and ins.startswith(ins1)
    assert tools == tools1 and req == req1


def test_rules_block_states_the_scoring_library_exactly():
    import re
    from livelab.core import READING_WORDS, REGIME_RULE_WORDS, rules_block
    from livelab.observability import SIGNATURES
    block = rules_block()
    word_to_ch = {w: c for c, w in READING_WORDS.items()}
    for regime, sigs in SIGNATURES.items():
        line = next(l for l in block.splitlines() if l.startswith("- " + REGIME_RULE_WORDS[regime]))
        stated = {}
        for fault, moved in re.findall(r"(\w+) moves ([^;.]+)", line):
            stated[fault] = {word_to_ch[w.strip()] for w in re.split(r",| and ", moved) if w.strip()}
        assert stated == {f: set(ch) for f, ch in sigs.items()}
