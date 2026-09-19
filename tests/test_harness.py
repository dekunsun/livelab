"""Harness and Gemini Live backend, tested offline against a fake Live session."""
import asyncio
import json
from types import SimpleNamespace as NS

from livelab.backends import MAX_REMINDERS, GeminiLiveBackend, MockBackend
from livelab.harness import run_replay
from livelab.mock_models import ObservabilityAware

VALID = {"execution_state": "NORMAL", "scientific_evidence": "NOT_YET_AVAILABLE", "attribution": "none",
         "specific_cause": "none", "evidence": [], "proposed_action": "continue"}


def msg(tool=None, said=None, done=False, go_away=False, handle=None):
    fc = [NS(id="c1", name="report_assessment", args=tool)] if tool is not None else None
    return NS(tool_call=NS(function_calls=fc) if fc else None,
              server_content=NS(turn_complete=done, output_transcription=NS(text=said) if said else None),
              go_away=NS(time_left="5s") if go_away else None,
              session_resumption_update=NS(new_handle=handle) if handle else None,
              usage_metadata=None)


class FakeSession:
    def __init__(self, turns):
        self.turns, self.sent, self.tool_responses = list(turns), [], []

    async def send_client_content(self, turns, turn_complete):
        self.sent.append(turns)

    async def send_tool_response(self, function_responses):
        self.tool_responses += function_responses

    async def receive(self):
        for m in self.turns.pop(0):
            yield m


class FakeConnect:
    def __init__(self, session):
        self.session, self.configs = session, []

    def __call__(self, cfg):
        self.configs.append(cfg)
        outer = self

        class CM:
            async def __aenter__(self):
                return outer.session

            async def __aexit__(self, *a):
                return False
        return CM()


def observe(turns):
    session = FakeSession(turns)
    connect = FakeConnect(session)
    backend = GeminiLiveBackend(connect=connect)

    async def go():
        await backend.start(seed=3)
        return await backend.observe("{}", [])
    return asyncio.run(go()), session, connect


def test_report_is_recorded_and_acknowledged_silently():
    res, session, connect = observe([[msg(tool=VALID), msg(said="Looks nominal."), msg(done=True)]])
    assert res["report"] == VALID and res["spoken"] == "Looks nominal." and res["reminders"] == 0
    assert session.tool_responses[0].scheduling == "SILENT"
    assert connect.configs[0].seed == 3
    assert connect.configs[0].context_window_compression is None     # never drop evidence


def test_missing_report_triggers_a_reminder():
    res, session, _ = observe([[msg(said="Hmm."), msg(done=True)], [msg(tool=VALID), msg(done=True)]])
    assert res["report"] == VALID and res["reminders"] == 1
    assert "report_assessment" in session.sent[-1]["parts"][0]["text"]


def test_invalid_report_is_rejected_and_ends_missing():
    bad = dict(VALID, execution_state="FINE")
    turns = [[msg(tool=bad), msg(done=True)] for _ in range(MAX_REMINDERS + 1)]
    res, session, _ = observe(turns)
    assert res["report"] is None and res["reminders"] == MAX_REMINDERS
    assert "rejected" in session.tool_responses[0].response["result"]


def test_go_away_resumes_the_same_session():
    res, _, connect = observe([[msg(handle="h-42"), msg(tool=VALID), msg(go_away=True), msg(done=True)]])
    assert res["report"] == VALID
    assert len(connect.configs) == 2 and connect.configs[1].session_resumption.handle == "h-42"


def test_harness_writes_a_complete_audit_log(tmp_path):
    index = json.load(open("data/replays/INDEX.json"))
    rid = next(r for r, m in index.items() if m["condition"] == "base")
    events = [json.loads(line) for line in open(f"data/replays/{rid}.jsonl")]
    reports, log = asyncio.run(run_replay(MockBackend(ObservabilityAware(), events), rid, "C-full", 0, tmp_path))
    rows = [json.loads(line) for line in open(log)]
    assert rows[0]["event"] == "meta" and rows[0]["replay_sha256"] == index[rid]["sha256"]
    assert len(rows) == 1 + len(events) == 1 + len(reports)
    delivered = [json.loads(r["delivered"]) for r in rows[1:]]
    assert "device_manifest" in delivered[0] and all("device_manifest" not in d for d in delivered[1:])
    assert set(delivered[0]["device_manifest"]) == {"sensors"}           # stage requirements stay hidden
    assert all("ref" in d for d in delivered)                            # C-full gets context
    assert sum(r["images_delivered"] for r in rows[1:]) == 1               # one micrograph, at the end
