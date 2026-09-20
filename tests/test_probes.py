"""The probe study: each variant changes only what the pre-registration says, and scoring works."""
import asyncio
import json
from types import SimpleNamespace as NS

import pytest

from livelab.probes import (B2_DEFINITION, SINGLE_TURN, p1_message, prefix_message, run_single_turn, score,
                            variant_setup)
from livelab.prompting import SYSTEM_INSTRUCTION

ITEMS = json.load(open("data/probes/items.json"))


def test_variants_change_only_what_is_registered():
    i0, t0, r0 = variant_setup("B0")
    assert i0 == SYSTEM_INSTRUCTION + SINGLE_TURN and [t["name"] for t in t0] == ["report_assessment"]
    i1, t1, r1 = variant_setup("B1")
    assert [t["name"] for t in t1] == ["report_verifiability", "report_assessment"] and r1[0] == "report_verifiability"
    i2, t2, _ = variant_setup("B2")
    assert i2 == i0 + B2_DEFINITION and t2 == t0
    i3, t3, _ = variant_setup("B3")
    assert t3[0]["parameters"]["properties"]["execution_state"]["enum"] == ["CANNOT_VERIFY", "ANOMALOUS", "NORMAL"]
    assert "CANNOT_VERIFY" in i3 and "or UNKNOWN if the available evidence" not in i3
    assert t0[0]["parameters"]["properties"]["execution_state"]["enum"] == ["NORMAL", "ANOMALOUS", "UNKNOWN"]


def test_prefix_is_the_benchmark_evidence_without_truth():
    item = ITEMS["in_context"][0]
    lines = prefix_message(item["replay_id"], item["k"]).splitlines()
    assert len(lines) == item["k"] + 1
    rows = [json.loads(line) for line in lines]
    assert "device_manifest" in rows[0] and all("device_manifest" not in r for r in rows[1:])
    text = "\n".join(lines).lower()
    for word in ("leak", "blockage", "drift", "fault", "unknown", "anomalous", "required_for_stage"):
        assert word not in text, word


def test_p1_question_names_regime_sensors_and_fault():
    q = p1_message(next(i for i in ITEMS["p1"] if i["kind"] == "detectable"))
    assert "Installed sensors" in q and "any point in the run" in q


def msg(tool=None, done=False):
    fcs = [NS(id=f"c{n}", name=name, args=args) for n, (name, args) in enumerate(tool or [])]
    return NS(tool_call=NS(function_calls=fcs) if fcs else None, usage_metadata=None,
              server_content=NS(turn_complete=done, output_transcription=None))


class FakeSession:
    def __init__(self, turns):
        self.turns, self.sent, self.responses = list(turns), [], []

    async def send_client_content(self, turns, turn_complete):
        self.sent.append(turns)

    async def send_tool_response(self, function_responses):
        self.responses += function_responses

    async def receive(self):
        for m in self.turns.pop(0):
            yield m


class Mute(FakeSession):
    """A model that never answers and never stops the turn, like the broken call path."""
    async def receive(self):
        yield msg(done=True)


def connect_to(session):
    class CM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *a):
            return False
    return lambda cfg: CM()


def test_single_turn_collects_both_b1_calls_and_reminds_for_a_missing_one():
    ver = {"atmosphere": "cannot_verify", "temperature": "verified", "gas_flow": "verified"}
    rep = {"execution_state": "NORMAL"}
    s = FakeSession([[msg([("report_verifiability", ver)]), msg(done=True)], [msg([("report_assessment", rep)]), msg(done=True)]])
    _, tools, required = variant_setup("B1")
    res = asyncio.run(run_single_turn(connect_to(s), "x", tools, required, "events"))
    assert [c["name"] for c in res["calls"]] == ["report_verifiability", "report_assessment"]
    assert res["reminders"] == 1 and "report_assessment" in s.sent[-1]["parts"][0]["text"]


def fake(calls):
    return {"calls": [{"name": n, "args": a} for n, a in calls]}


def test_scoring_matches_registered_measures():
    ctx = ITEMS["in_context"]
    # A model that is right on U/N/A under B2 and conflates under B1.
    b2 = {i["item_id"]: fake([("report_assessment", {"execution_state": {"U": "UNKNOWN", "N": "NORMAL", "A": "ANOMALOUS"}[i["set"]]})]) for i in ctx}
    b1 = {i["item_id"]: fake([("report_verifiability", {"atmosphere": "cannot_verify" if i["set"] == "U" else "verified",
                                                         "temperature": "verified", "gas_flow": "verified"}),
                              ("report_assessment", {"execution_state": "NORMAL"})]) for i in ctx}
    always_yes = {i["item_id"]: fake([("answer_detectability", {"detectable": "yes"}), ("answer_distinguishability", {"distinguishable": "yes"})])
                  for i in ITEMS["p1"]}
    s = score(ITEMS, {"B2": b2, "B1": b1, "P1": always_yes})
    n_u = sum(i["set"] == "U" for i in ctx)
    assert s["B2"]["abstention_on_U"] == (n_u, n_u) and s["B2"]["over_abstention_on_N"][0] == 0
    assert s["B2"]["detection_on_A"][0] == s["B2"]["detection_on_A"][1]
    assert s["B1"]["conflation_rate_on_U"] == (n_u, n_u)
    assert s["P1"]["detectable"]["balanced_accuracy"] == 0.5          # always-"yes" cannot pass Pr1


def test_runner_end_to_end_with_a_fake_model(tmp_path):
    import scripts.run_probes as rp
    rp.RETRY_WAIT_S = 0        # a broken fake must fail fast, not wait out free-tier retries

    class Echo:
        """Answers every prompt with the first required tool, always NORMAL / yes."""
        def __call__(self, cfg):
            names = [fd.name for fd in cfg.tools[0].function_declarations]
            args = {"report_assessment": {"execution_state": "NORMAL"}, "report_verifiability": {"atmosphere": "verified", "temperature": "verified", "gas_flow": "verified"},
                    "answer_detectability": {"detectable": "yes"}, "answer_distinguishability": {"distinguishable": "yes"}}
            s = FakeSession([[msg([(n, args[n]) for n in names]), msg(done=True)]])
            return connect_to(s)(cfg)
    asyncio.run(rp.main(connect=Echo(), out_root=tmp_path, argv=["--limit", "2"]))
    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.glob("*/*.json"))
    assert len(files) == 10 and {f.split("/")[0] for f in files} == {"P1", "B0", "B1", "B2", "B3"}


def test_single_turn_ends_once_required_calls_are_in():
    class Hanging(FakeSession):
        async def receive(self):
            yield msg([("answer_detectability", {"detectable": "yes"})])
            await asyncio.sleep(3600)          # no turn_complete
    res = asyncio.run(asyncio.wait_for(run_single_turn(connect_to(Hanging([])), "x", [], ["answer_detectability"], "q"), 5))
    assert [c["name"] for c in res["calls"]] == ["answer_detectability"]


def test_a_broken_call_path_aborts_instead_of_recording_a_non_answer(tmp_path):
    """Deviation 7: silence from a broken API must never be saved as the model declining."""
    import scripts.run_probes as rp
    rp.RETRY_WAIT_S = 0

    class SilentEverywhere:            # answers nothing, not even the canary
        def __call__(self, cfg):
            return connect_to(FakeSession([[msg(done=True)]] * 4))(cfg)
    with pytest.raises(SystemExit) as e:
        asyncio.run(rp.main(connect=SilentEverywhere(), out_root=tmp_path,
                            argv=["--only", "P1", "--limit", "1", "--cooldown", "0", "--max-cooldowns", "0"]))
    assert "still broken after 0 cooldowns" in str(e.value)
    assert list(tmp_path.glob("*/*.json")) == []


def test_silence_while_the_control_model_answers_waits_then_resumes(tmp_path):
    """Deviation 7: a broken call path makes the runner idle and retry, never record a non-answer."""
    import scripts.run_probes as rp
    rp.RETRY_WAIT_S = 0

    def answers(cfg):
        names = [fd.name for fd in cfg.tools[0].function_declarations]
        args = {"answer_detectability": {"detectable": "yes"}, "answer_distinguishability": {"distinguishable": "yes"}}
        return connect_to(FakeSession([[msg([(n, args[n]) for n in names]), msg(done=True)]]))(cfg)

    class BrokenThenFixed:
        """Silent until the cooldown has passed once, exactly like the API recovering while idle."""
        def __init__(self):
            self.calls_made = 0

        def __call__(self, cfg):
            self.calls_made += 1
            if self.calls_made <= 3:
                return connect_to(Mute([]))(cfg)
            return answers(cfg)
    rp.PATIENCE_S = 0
    under_test = BrokenThenFixed()
    asyncio.run(rp.main(connect=under_test, control_connect=answers, out_root=tmp_path,
                        argv=["--backend", "gemini-extended", "--only", "P1", "--limit", "1",
                              "--cooldown", "0", "--max-cooldowns", "1"]))     # waiting is opt-in now
    [f] = list(tmp_path.glob("P1/*.json"))
    d = json.loads(f.read_text())
    assert not d.get("unanswered") and d["calls"]         # it waited and got a real answer
    assert under_test.calls_made == 4                     # 3 silent attempts, one cooldown, then one more


def test_a_run_gives_up_after_the_cooldowns_are_spent(tmp_path):
    import scripts.run_probes as rp
    rp.RETRY_WAIT_S = 0
    rp.PATIENCE_S = 0

    def answers(cfg):
        names = [fd.name for fd in cfg.tools[0].function_declarations]
        args = {"answer_detectability": {"detectable": "yes"}, "answer_distinguishability": {"distinguishable": "yes"}}
        return connect_to(FakeSession([[msg([(n, args[n]) for n in names]), msg(done=True)]]))(cfg)
    with pytest.raises(SystemExit) as e:
        asyncio.run(rp.main(connect=lambda cfg: connect_to(Mute([]))(cfg), control_connect=answers, out_root=tmp_path,
                            argv=["--backend", "gemini-extended", "--only", "P1", "--limit", "1",
                                  "--cooldown", "0", "--max-cooldowns", "2"]))
    assert "still broken after 2 cooldowns" in str(e.value)
    assert list(tmp_path.glob("*/*.json")) == []


def test_a_working_call_path_records_the_non_answer_and_excludes_it(tmp_path):
    import scripts.run_probes as rp
    rp.RETRY_WAIT_S = 0

    class SilentButCanaryWorks:
        def __call__(self, cfg):
            names = [fd.name for fd in cfg.tools[0].function_declarations]
            if names == ["canary"]:
                return connect_to(FakeSession([[msg([("canary", {"ok": "yes"})]), msg(done=True)]]))(cfg)
            return connect_to(FakeSession([[msg(done=True)]] * 3))(cfg)
    asyncio.run(rp.main(connect=SilentButCanaryWorks(), out_root=tmp_path,
                        argv=["--only", "P1", "--limit", "1", "--cooldown", "0"]))
    [f] = list(tmp_path.glob("P1/*.json"))
    d = json.loads(f.read_text())
    assert d["unanswered"] is True and d["calls"] == []
    # and it is excluded from the rate, not counted as a wrong answer
    s = score(ITEMS, {"P1": {d["item_id"]: d}})
    assert s["P1"]["coverage"] == (0, len(ITEMS["p1"])) and s["P1"]["detectable"]["accuracy"] == (0, 0)
