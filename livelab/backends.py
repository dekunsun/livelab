"""Observer backends: a mock wrapper for testing the harness, and Gemini 3.8 Live.

A backend receives one observation event at a time and must return exactly one
report_assessment. It never sees ground truth.
"""
import json
import os
from pathlib import Path

from .prompting import REPORT_ASSESSMENT, SYSTEM_INSTRUCTION, validate

ROOT = Path(__file__).resolve().parent.parent
MAX_REMINDERS = 2
EVENT_TIMEOUT_S = 120   # a silently stalled connection raises instead of hanging


def load_dotenv(path=ROOT / ".env"):
    """Load KEY=VALUE lines into the environment without printing them. .env is gitignored."""
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class MockBackend:
    """Replays a mock observer through the same interface, so the harness can be tested offline."""

    def __init__(self, mock, events):
        self.model_id = f"mock:{mock.name}"
        self._reports = iter(mock.run(events))

    async def start(self, seed):
        pass

    async def observe(self, text, images):
        return {"report": next(self._reports), "spoken": "", "tool_calls": 1, "reminders": 0,
                "problems": [], "usage": None}

    async def close(self):
        pass


class GeminiLiveBackend:
    """One Live session per replay; a report_assessment is required after every event."""

    def __init__(self, model_id="gemini-3.8-live", temperature=None, connect=None):
        self.model_id = model_id
        self.temperature = temperature
        self._connect = connect          # injectable for tests; defaults to the real SDK
        self._session = self._cm = None
        self._handle = None
        self.seed = None

    def _config(self):
        from google.genai import types
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[{"function_declarations": [REPORT_ASSESSMENT]}],
            output_audio_transcription={},
            # No context window compression: it would silently drop earlier evidence.
            session_resumption=types.SessionResumptionConfig(handle=self._handle),
            seed=self.seed,
            temperature=self.temperature,
        )

    async def _open(self):
        if self._connect is None:
            from google import genai
            load_dotenv()
            if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
                raise RuntimeError("Set GEMINI_API_KEY in livelab/.env (never commit it).")
            client = genai.Client()
            self._connect = lambda cfg: client.aio.live.connect(model=self.model_id, config=cfg)
        self._cm = self._connect(self._config())
        self._session = await self._cm.__aenter__()

    async def start(self, seed):
        self.seed = seed
        await self._open()

    async def _reconnect(self):
        """Resume the same session (context intact) after the server's periodic connection reset."""
        await self._cm.__aexit__(None, None, None)
        await self._open()

    async def observe(self, text, images):
        import asyncio
        return await asyncio.wait_for(self._observe(text, images), EVENT_TIMEOUT_S)

    async def _observe(self, text, images):
        from google.genai import types
        parts = [{"text": text}] + [{"inline_data": {"mime_type": m, "data": b}} for m, b in images]
        await self._session.send_client_content(turns={"role": "user", "parts": parts}, turn_complete=True)
        result = {"report": None, "spoken": "", "tool_calls": 0, "reminders": 0, "problems": [], "usage": None}
        reconnect = False
        while True:
            async for msg in self._session.receive():
                if getattr(msg, "session_resumption_update", None) and msg.session_resumption_update.new_handle:
                    self._handle = msg.session_resumption_update.new_handle
                if getattr(msg, "go_away", None) is not None:
                    reconnect = True
                if getattr(msg, "usage_metadata", None) is not None:
                    result["usage"] = msg.usage_metadata.model_dump(exclude_none=True)
                sc = getattr(msg, "server_content", None)
                if sc is not None and getattr(sc, "output_transcription", None) and sc.output_transcription.text:
                    result["spoken"] += sc.output_transcription.text
                if getattr(msg, "tool_call", None):
                    responses = []
                    for fc in msg.tool_call.function_calls:
                        result["tool_calls"] += 1
                        args = dict(fc.args or {})
                        problems = validate(args) if fc.name == "report_assessment" else [f"unknown tool {fc.name}"]
                        if fc.name == "report_assessment" and not problems and result["report"] is None:
                            result["report"] = args
                        result["problems"] += problems
                        responses.append(types.FunctionResponse(
                            id=fc.id, name=fc.name, scheduling="SILENT",
                            response={"result": "recorded" if not problems else "rejected: " + "; ".join(problems)}))
                    await self._session.send_tool_response(function_responses=responses)
                if sc is not None and getattr(sc, "turn_complete", False):
                    break
            if result["report"] is not None or result["reminders"] >= MAX_REMINDERS:
                break
            result["reminders"] += 1
            await self._session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Call report_assessment for this event now."}]},
                turn_complete=True)
        if reconnect:
            await self._reconnect()
        return result

    async def close(self):
        if self._cm is not None:
            await self._cm.__aexit__(None, None, None)
