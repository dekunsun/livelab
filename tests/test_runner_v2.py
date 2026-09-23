"""Runner v2's rules (docs/core_runner_v2.md), checked against scripted server behaviour."""
import asyncio
import json
from types import SimpleNamespace as NS

from livelab.core import setup_for
from livelab.runner_v2 import check_call, dump, live_item, rest_item, sha256

INSTRUCTION, TOOLS, REQUIRED = setup_for("V1")
B1_INSTRUCTION, B1_TOOLS, B1_REQUIRED = setup_for("B1")
VALID = {"execution_state": "ANOMALOUS", "scientific_evidence": "INCONCLUSIVE", "attribution": "instrument_process",
         "specific_cause": "seal_leak", "evidence": [{"channel": "pressure", "observation": "rising"}],
         "proposed_action": "call_human"}
REVISED = dict(VALID, execution_state="NORMAL")
VERIFY = {"atmosphere": "cannot_verify", "temperature": "verified", "gas_flow": "verified"}
TEXT = '{"t_sim_s": 0, "pressure_torr": 2.0}'
STANDARD, EXTENDED = "gemini-3.8-live", "gemini-3.8-live-extended-thinking"
IN_PROGRESS, COMPLETED = "InteractionStatus.IN_PROGRESS", "InteractionStatus.COMPLETED"


def m(calls=None, done=False, status=None, usage=None, said=None, interrupted=None, reason=None, audio=None):
    fcs = [NS(id=i, name=n, args=a) for i, n, a in calls] if calls else None
    turn = NS(parts=[NS(inline_data=NS(data=audio, mime_type="audio/pcm"))]) if audio else None
    return NS(tool_call=NS(function_calls=fcs) if fcs else None,
              usage_metadata=NS(**usage) if usage else None,
              server_content=NS(turn_complete=done, interaction_status=status, interrupted=interrupted,
                                turn_complete_reason=reason, model_turn=turn,
                                output_transcription=NS(text=said) if said else None))


class Session:
    """Each receive() yields the next scripted turn; with none left, the server is silent."""

    def __init__(self, turns):
        self.turns, self.sent, self.tool_responses = list(turns), [], []

    async def send_client_content(self, turns, turn_complete):
        self.sent.append((turns, turn_complete))

    async def send_tool_response(self, function_responses):
        self.tool_responses += list(function_responses)

    def receive(self):
        async def gen():
            if not self.turns:
                await asyncio.Event().wait()
            for msg in self.turns.pop(0):
                yield msg
        return gen()


class Connect:
    def __init__(self, session):
        self.session, self.configs = session, []

    def __call__(self, cfg):
        self.configs.append(cfg)
        session = self.session

        class CM:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *a):
                return False
        return CM()


def live(turns, model=STANDARD, setup=(INSTRUCTION, TOOLS, REQUIRED), **kw):
    session = Session(turns)
    kw.setdefault("submit_deadline", 0.3)
    kw.setdefault("collect_grace", 0.2)
    rec = asyncio.run(live_item(Connect(session), model, *setup, TEXT, **kw))
    json.dumps(rec)                                   # every record must serialise
    return rec, session


def test_one_message_with_a_call_usage_and_status_keeps_all_three():
    rec, _ = live([[m(calls=[("c1", "report_assessment", VALID)], usage={"prompt_token_count": 900},
                      status=COMPLETED, done=True)]])
    assert rec["calls"] == [{"name": "report_assessment", "args": VALID}]
    assert rec["usage_messages"][0]["usage"] == {"prompt_token_count": 900}
    assert rec["collection"]["last_interaction_status"] == COMPLETED
    assert rec["collection"]["status"] == "complete" and rec["outcome"] == "submitted_unprompted"


def test_a_revision_after_the_submission_is_kept_but_not_scored():
    rec, _ = live([[m(calls=[("c1", "report_assessment", VALID)]),
                    m(calls=[("c2", "report_assessment", REVISED)]), m(done=True)]])
    assert rec["calls"][0]["args"]["execution_state"] == "ANOMALOUS"
    assert [c["args"]["execution_state"] for c in rec["later_calls"]] == ["NORMAL"]
    assert rec["collection"]["status"] == "complete"


def test_repeated_ids_count_once_and_several_calls_in_one_message_keep_their_order():
    rec, session = live([[m(calls=[("c1", "report_verifiability", VERIFY), ("c1", "report_verifiability", VERIFY),
                                   ("c2", "report_assessment", VALID)], done=True)]],
                        setup=(B1_INSTRUCTION, B1_TOOLS, B1_REQUIRED))
    assert [c["name"] for c in rec["calls"]] == ["report_verifiability", "report_assessment"]
    assert len(rec["duplicate_call_ids"]) == 1 and len(session.tool_responses) == 2


def test_a_malformed_call_is_logged_and_the_next_valid_one_is_the_submission():
    rec, _ = live([[m(calls=[("c1", "report_assessment", dict(VALID, execution_state="MAYBE"))]),
                    m(calls=[("c2", "report_assessment", VALID)]), m(done=True)]])
    assert rec["calls"][0]["args"] == VALID
    assert rec["malformed_calls"][0]["problems"] == ["execution_state='MAYBE' not allowed"]


def test_validity_is_about_the_protocol_not_the_answer():
    assert check_call("report_assessment", REVISED, TOOLS) == []
    assert check_call("report_assessment", {k: v for k, v in VALID.items() if k != "evidence"}, TOOLS) == ["evidence missing"]
    assert check_call("report_assessment", dict(VALID, evidence=[{"channel": "p"}]), TOOLS) == ["evidence[0].observation missing"]
    assert check_call("no_such_tool", {}, TOOLS) == ["unknown tool 'no_such_tool'"]


def test_extended_thinking_still_in_progress_gets_no_reminder():
    rec, session = live([[m(done=True, status=IN_PROGRESS)],
                         [m(calls=[("c1", "report_assessment", VALID)], status=COMPLETED, done=True)]], model=EXTENDED)
    assert rec["outcome"] == "submitted_unprompted" and rec["reminders"] == [] and len(session.sent) == 1


def test_extended_thinking_with_no_status_is_never_presumed_idle():
    rec, session = live([[m(done=True)]], model=EXTENDED)
    assert rec["reminders"] == [] and len(session.sent) == 1
    assert rec["outcome"] == "timeout" and rec["collection"]["status"] == "timeout_before_submission"
    assert rec["collection"]["interaction_status_seen"] is False


def test_extended_thinking_calls_are_async_and_carry_no_scheduling():
    rec, session = live([[m(calls=[("c1", "report_assessment", VALID)], status=COMPLETED, done=True)]], model=EXTENDED)
    assert all(str(t["behavior"]).endswith("NON_BLOCKING") for t in rec["client_events"][0]["content"]["tools"])
    assert session.tool_responses[0].scheduling is None


def test_a_standard_model_that_ends_its_turn_without_the_call_gets_one_recorded_reminder():
    rec, session = live([[m(said="Pressure is rising.", done=True)],
                         [m(calls=[("c1", "report_assessment", VALID)]), m(done=True)]])
    assert rec["outcome"] == "submitted_after_reminder" and rec["submission"]["reminders_before"] == 1
    assert rec["reminders"][0]["text"] == "Call report_assessment now."
    sent = [e for e in rec["client_events"] if e["kind"] == "reminder"]
    assert len(sent) == 1 and sent[0]["sha256"] == sha256(sent[0]["content"])
    assert rec["spoken_before_submission"] == "Pressure is rising."


def test_with_remedy_off_no_reminder_is_sent_and_no_submission_is_not_unknown():
    rec, session = live([[m(done=True)]], remedy="none")
    assert len(session.sent) == 1 and rec["outcome"] == "protocol_incomplete"
    assert rec["collection"]["status"] == "ended_without_submission" and rec["calls"] == []


def test_a_submission_with_no_end_is_still_a_submission():
    rec, _ = live([[m(calls=[("c1", "report_assessment", VALID)])]])
    assert rec["outcome"] == "submitted_unprompted"
    assert rec["collection"]["status"] == "timeout_after_submission"


def test_usage_arriving_after_the_call_is_collected():
    rec, _ = live([[m(calls=[("c1", "report_assessment", VALID)]),
                    m(usage={"prompt_token_count": 900, "thoughts_token_count": 300}), m(done=True)]])
    assert rec["usage_messages"][0]["usage"]["thoughts_token_count"] == 300


def test_an_interruption_and_the_turn_complete_reason_are_recorded():
    rec, _ = live([[m(calls=[("c1", "report_assessment", VALID)]),
                    m(interrupted=True, reason="TurnCompleteReason.INTERRUPTED", done=True)]])
    assert rec["collection"]["interrupted_seen"] is True
    assert rec["collection"]["turn_complete_reasons"] == ["TurnCompleteReason.INTERRUPTED"]


def test_what_was_sent_is_hashed_where_it_was_sent():
    rec, session = live([[m(calls=[("c1", "report_assessment", VALID)], done=True)]])
    kinds = [e["kind"] for e in rec["client_events"]]
    assert kinds == ["setup", "user_turn", "tool_response"]
    assert all(e["sha256"] == sha256(e["content"]) for e in rec["client_events"])
    assert rec["client_events"][1]["content"] == session.sent[0][0]
    assert rec["first_turn_matches_item"] is True and rec["item_text_sha256"] == sha256(TEXT)


def test_audio_is_kept_as_length_and_hash_not_bytes():
    rec, _ = live([[m(audio=b"\x00" * 64), m(calls=[("c1", "report_assessment", VALID)], done=True)]])
    part = rec["server_events"][0]["message"]["server_content"]["model_turn"]["parts"][0]
    assert part["inline_data"]["data"] == {"bytes": 64, "sha256": sha256(b"\x00" * 64)}
    assert dump(NS(a=None, b=1)) == {"b": 1}


def gemini_response(calls=(), text=None, usage=10):
    parts = [{"functionCall": {"name": n, "args": a}} for n, a in calls] + ([{"text": text}] if text else [])
    return {"candidates": [{"content": {"role": "model", "parts": parts}}],
            "usageMetadata": {"promptTokenCount": usage, "candidatesTokenCount": 1}}


def rest(responses, provider="gemini", **kw):
    queue, bodies = list(responses), []

    def post(url, headers, body):
        bodies.append(json.loads(json.dumps(body)))
        return queue.pop(0)
    rec = asyncio.run(rest_item(provider, "gemini-3.8-flash", INSTRUCTION, TOOLS, REQUIRED, TEXT, post=post,
                                headers={"x-goog-api-key": "SECRET"}, **kw))
    assert "SECRET" not in json.dumps(rec)
    return rec, bodies


def test_rest_keeps_every_request_whole_and_records_its_reminder():
    rec, bodies = rest([gemini_response(text="Rising pressure."),
                        gemini_response([("report_assessment", VALID)]), gemini_response(text="Done.")])
    requests = [e for e in rec["client_events"] if e["kind"] == "request"]
    assert [e["content"] for e in requests] == bodies and all(e["sha256"] == sha256(e["content"]) for e in requests)
    assert rec["outcome"] == "submitted_after_reminder" and rec["reminders"][0]["text"] == "Call report_assessment now."
    assert bodies[1]["contents"][-1] == {"role": "user", "parts": [{"text": "Call report_assessment now."}]}
    assert len(rec["usage_messages"]) == 3 and rec["first_turn_matches_item"] is True
    assert rec["collection"]["status"] == "complete"


def test_rest_closing_turn_revision_is_a_later_call():
    rec, _ = rest([gemini_response([("report_assessment", VALID)]), gemini_response([("report_assessment", REVISED)])])
    assert rec["calls"][0]["args"] == VALID and rec["later_calls"][0]["args"] == REVISED


def test_rest_with_remedy_off_stops_at_the_first_turn_without_a_call():
    rec, bodies = rest([gemini_response(text="Rising pressure.")], remedy="none")
    assert len(bodies) == 1 and rec["outcome"] == "protocol_incomplete" and rec["reminders"] == []
