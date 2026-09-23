"""Runner v2 (docs/core_runner_v2.md): the same items, instructions, tools and scoring as v1, with
every exchange recorded and the reminder and scoring rules fixed in advance.

One item is one call to `live_item` (a Gemini Live session) or `rest_item` (a request/response
provider). Both return a record whose `calls` holds the first submission, so `livelab.core.score`
reads it exactly as it reads a v1 record, and whose other fields say how that submission came about.
"""
import asyncio
import hashlib
import json
from types import SimpleNamespace

from .prompting import async_only, tools_for
from .standard_api import _acknowledge, _assistant_turn, build_request, parse, url_for, user_turn

RUNNER_VERSION = "v2"
REMINDER = "Call {} now."
MAX_REMINDERS = 2


def sha256(obj):
    """Hash of exactly what was handed over: bytes as they are, text as UTF-8, anything else as
    canonical JSON."""
    if isinstance(obj, bytes):
        data = obj
    elif isinstance(obj, str):
        data = obj.encode()
    else:
        data = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(data).hexdigest()


def dump(obj):
    """A server message as plain JSON: every field kept, audio bytes replaced by length and hash."""
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(exclude_none=True)
    if isinstance(obj, SimpleNamespace):
        obj = vars(obj)
    if isinstance(obj, dict):
        return {str(k): dump(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, (list, tuple)):
        return [dump(v) for v in obj]
    if isinstance(obj, bytes):
        return {"bytes": len(obj), "sha256": sha256(obj)}
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _check(value, schema, path):
    problems, kind = [], schema.get("type")
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}={value!r} not allowed"]
    if kind == "string" and not isinstance(value, str):
        problems.append(f"{path} is not a string")
    elif kind in ("number", "integer") and (isinstance(value, bool) or not isinstance(value, (int, float))):
        problems.append(f"{path} is not a number")
    elif kind == "array":
        if not isinstance(value, list):
            return [f"{path} is not an array"]
        for i, v in enumerate(value):
            problems += _check(v, schema.get("items") or {}, f"{path}[{i}]")
    elif kind == "object":
        if not isinstance(value, dict):
            return [f"{path} is not an object"]
        props = schema.get("properties") or {}
        problems += [f"{path}.{k} missing".lstrip(".") for k in schema.get("required", []) if k not in value]
        for k, v in value.items():
            if k in props:
                problems += _check(v, props[k], f"{path}.{k}".lstrip("."))
    return problems


def check_call(name, args, tools):
    """Protocol problems with one call: the tool must exist and its arguments must fit its schema.
    Whether the answer is right never enters here."""
    spec = {t["name"]: t for t in tools}.get(name)
    if spec is None:
        return [f"unknown tool {name!r}"]
    if not isinstance(args, dict) or "__unparsed__" in args:
        return ["arguments could not be parsed"]
    return _check(args, dict(spec.get("parameters") or {}, type="object"), "")


class Submission:
    """Tracks calls in arrival order. The first valid call of each required tool is the submission."""

    def __init__(self, required, tools):
        self.required, self.tools = list(required), tools
        self.first, self.ids = {}, set()
        self.malformed, self.later, self.duplicates, self.extra = [], [], [], []
        self.t = self.reminders_before = None

    @property
    def complete(self):
        return all(r in self.first for r in self.required)

    def add(self, call_id, name, args, t, reminders):
        """Returns True if this call id is new (and so needs a response)."""
        entry = {"id": call_id, "name": name, "args": args, "t": t}
        if call_id is not None and call_id in self.ids:
            self.duplicates.append(entry)
            return False
        if call_id is not None:
            self.ids.add(call_id)
        if self.complete:
            self.later.append(entry)
            return True
        problems = check_call(name, args, self.tools)
        if problems:
            self.malformed.append(dict(entry, problems=problems))
        elif name in self.required and name not in self.first:
            self.first[name] = entry
            if self.complete:
                self.t, self.reminders_before = t, reminders
        else:
            self.extra.append(entry)          # a repeat before the submission was complete
        return True

    def calls(self):
        return [{"name": r, "args": self.first[r]["args"]} for r in self.required if r in self.first]


def _outcome(sub, deadline_passed):
    if sub.complete:
        return "submitted_unprompted" if sub.reminders_before == 0 else "submitted_after_reminder"
    return "timeout" if deadline_passed else "protocol_incomplete"


def _record(sub, text, client, server, reminders, outcome, collection, **rest):
    return dict({
        "runner": RUNNER_VERSION,
        "item_text_sha256": sha256(text),
        "first_turn_matches_item": rest.pop("first_turn_text") == text,
        "calls": sub.calls(),
        "submission": {"status": "obtained" if sub.complete else "none", "t": sub.t,
                       "reminders_before": sub.reminders_before,
                       "first_calls": [sub.first[r] for r in sub.required if r in sub.first]},
        "outcome": outcome,
        "collection": collection,
        "reminders": reminders,
        "malformed_calls": sub.malformed, "later_calls": sub.later,
        "extra_calls_before_submission": sub.extra, "duplicate_call_ids": sub.duplicates,
        "client_events": client, "server_events": server,
    }, **rest)


def _is_busy(status):
    return status is not None and str(status).endswith("IN_PROGRESS")


def confirmed_idle(model_id, status):
    """Has the model finished, as far as the server has said? Extended Thinking's turnComplete does
    not mean its background work is done, so only an explicit status that is not IN_PROGRESS counts;
    for other models a completed turn counts unless the status says IN_PROGRESS."""
    if async_only(model_id):
        return status is not None and not _is_busy(status)
    return not _is_busy(status)


async def live_item(connect, model_id, instruction, tools, required, text, *, seed=0, thinking_level=None,
                    remedy="fixed", submit_deadline=300.0, collect_grace=30.0, clock=None):
    """One Live session for one item, recorded end to end."""
    from google.genai import types
    loop = asyncio.get_running_loop()
    clock = clock or loop.time
    start = clock()
    now = lambda: round(clock() - start, 3)  # noqa: E731
    client, server, reminders, usage, spoken = [], [], [], [], ""
    sub = Submission(required, tools)
    declared = tools_for(model_id, tools)
    setup = {"model": model_id, "response_modalities": ["AUDIO"], "system_instruction": instruction,
             "tools": declared, "output_audio_transcription": True, "seed": seed,
             "thinking_level": thinking_level}
    client.append({"t": now(), "kind": "setup", "content": setup, "sha256": sha256(setup)})
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"], system_instruction=instruction,
        tools=[{"function_declarations": declared}], output_audio_transcription={}, seed=seed,
        **({"thinking_config": types.ThinkingConfig(thinking_level=thinking_level)} if thinking_level else {}))
    status = seen_status = None
    interrupted, reasons, spoken_before = False, [], None
    collection, deadline_passed, sub_at = None, False, None

    async def send_user(kind, words, extra=None):
        turn = {"role": "user", "parts": [{"text": words}]}
        client.append(dict({"t": now(), "kind": kind, "content": turn, "sha256": sha256(turn)}, **(extra or {})))
        await session.send_client_content(turns=turn, turn_complete=True)

    cm = connect(config)
    session = await cm.__aenter__()
    try:
        await send_user("user_turn", text)
        empty_streams = 0
        while collection is None:
            stream, got_any = session.receive().__aiter__(), False
            while True:
                limit = (start + submit_deadline) if not sub.complete else (sub_at + collect_grace)
                left = limit - clock()
                if left <= 0:
                    deadline_passed = not sub.complete
                    collection = "timeout_after_submission" if sub.complete else "timeout_before_submission"
                    break
                try:
                    msg = await asyncio.wait_for(stream.__anext__(), left)
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    continue                  # the loop re-checks the deadline
                got_any = True
                server.append({"t": now(), "message": dump(msg)})
                # Every field of the message is read: one message can carry a call, usage and status.
                if getattr(msg, "usage_metadata", None) is not None:
                    usage.append({"t": now(), "usage": dump(msg.usage_metadata)})
                sc = getattr(msg, "server_content", None)
                if sc is not None:
                    if getattr(sc, "interaction_status", None) is not None:
                        status = seen_status = sc.interaction_status
                    if getattr(sc, "interrupted", None):
                        interrupted = True
                    if getattr(sc, "turn_complete_reason", None) is not None:
                        reasons.append(str(sc.turn_complete_reason))
                    tr = getattr(sc, "output_transcription", None)
                    if tr is not None and getattr(tr, "text", None):
                        spoken += tr.text
                tc = getattr(msg, "tool_call", None)
                if tc is not None and getattr(tc, "function_calls", None):
                    responses = []
                    was_complete = sub.complete
                    for fc in tc.function_calls:
                        if sub.add(fc.id, fc.name, dict(fc.args or {}), now(), len(reminders)):
                            responses.append(types.FunctionResponse(
                                id=fc.id, name=fc.name, response={"result": "recorded"},
                                **({} if async_only(model_id) else {"scheduling": "SILENT"})))
                    if not was_complete and sub.complete:
                        sub_at, spoken_before = clock(), spoken
                    if responses:
                        content = [{"id": r.id, "name": r.name, "response": r.response,
                                    "scheduling": str(r.scheduling) if r.scheduling else None} for r in responses]
                        client.append({"t": now(), "kind": "tool_response", "content": content,
                                       "sha256": sha256(content)})
                        await session.send_tool_response(function_responses=responses)
                if sc is not None and getattr(sc, "turn_complete", False):
                    idle = confirmed_idle(model_id, status)
                    if sub.complete and idle:
                        collection = "complete"
                        break
                    if not sub.complete and idle:
                        missing = [r for r in required if r not in sub.first]
                        if remedy == "fixed" and len(reminders) < MAX_REMINDERS:
                            words = REMINDER.format(missing[0])
                            reminders.append({"t": now(), "text": words, "missing": missing})
                            await send_user("reminder", words)
                            status = None     # a new turn: its status is not yet known
                        else:
                            collection = "ended_without_submission"
                        break
                    # not confirmed idle: keep listening, never infer idleness from waiting
            if collection is None and not got_any:
                empty_streams += 1
                if empty_streams >= 3:
                    collection = "closed_by_server"
            elif got_any:
                empty_streams = 0
    except Exception as exc:  # noqa: BLE001 - kept, and reported beside whatever was obtained
        collection = f"error: {type(exc).__name__}: {str(exc)[:200]}"
    finally:
        await cm.__aexit__(None, None, None)
    return _record(sub, text, client, server, reminders, _outcome(sub, deadline_passed),
                   {"status": collection, "last_interaction_status": str(seen_status) if seen_status else None,
                    "interaction_status_seen": seen_status is not None, "interrupted_seen": interrupted,
                    "turn_complete_reasons": reasons},
                   first_turn_text=client[1]["content"]["parts"][0]["text"],
                   provider="gemini_live", model=model_id, spoken=spoken, spoken_before_submission=spoken_before,
                   usage_messages=usage)


async def rest_item(provider, model, instruction, tools, required, text, *, post, headers, tool_choice=None,
                    remedy="fixed", max_requests=6, closing_turn=True, clock=None):
    """One item on a request/response API, every request body and response kept whole.

    `headers` is used to send and is never recorded. After the submission, one closing request hands
    back the call results so the model can finish its turn; anything it calls then is a later call."""
    loop = asyncio.get_running_loop()
    clock = clock or loop.time
    start = clock()
    now = lambda: round(clock() - start, 3)  # noqa: E731
    client, server, reminders, usage = [], [], [], []
    sub = Submission(required, tools)
    messages = [user_turn(provider, text)]
    spoken, spoken_before, collection, closing = "", None, None, False
    for n in range(max_requests):
        missing = [r for r in required if r not in sub.first]
        body = build_request(provider, model, instruction, tools, messages,
                             force_tool=(missing[0] if missing and len(required) > 1 else None),
                             tool_choice=tool_choice)
        client.append({"t": now(), "kind": "request", "content": body, "sha256": sha256(body)})
        response = await asyncio.to_thread(post, url_for(provider, model), headers, body)
        server.append({"t": now(), "message": response})
        new, said, u = parse(provider, response)
        usage.append({"t": now(), "request": n, "usage": u})
        spoken += said
        was_complete = sub.complete
        for i, c in enumerate(new):
            sub.add(c.get("id") or f"r{n}c{i}", c["name"], c["args"], now(), len(reminders))
        if not was_complete and sub.complete:
            spoken_before = spoken
        if closing:
            collection = "complete"
            break
        if sub.complete:
            if not closing_turn:
                collection = "complete"
                break
            closing = True
            messages = messages + _assistant_turn(provider, response, new) + _acknowledge(provider, new)
            continue
        if not new:                           # the model's turn ended without the call
            if remedy == "fixed" and len(reminders) < MAX_REMINDERS:
                words = REMINDER.format(missing[0])
                reminders.append({"t": now(), "text": words, "missing": missing})
                messages = messages + _assistant_turn(provider, response, new) + [reminder_turn(provider, words)]
                continue
            collection = "ended_without_submission"
            break
        messages = messages + _assistant_turn(provider, response, new) + _acknowledge(provider, new)
    else:
        collection = "request_limit"
    return _record(sub, text, client, server, reminders, _outcome(sub, False), {"status": collection},
                   first_turn_text=text if client and _first_text(provider, client[0]["content"]) == text else None,
                   provider=provider, model=model, spoken=spoken, spoken_before_submission=spoken_before,
                   usage_messages=usage)


def reminder_turn(provider, words):
    if provider == "gemini":
        return {"role": "user", "parts": [{"text": words}]}
    return {"role": "user", "content": words}


def _first_text(provider, body):
    """The first user turn's text as it stands in the request body that was sent."""
    if provider == "gemini":
        return body["contents"][0]["parts"][-1]["text"]
    turns = body.get("messages") or body.get("input") or [{}]
    first = turns[1] if provider == "openai" else turns[0]
    content = first.get("content")
    return content if isinstance(content, str) else (content or [{}])[-1].get("text")
