"""Ask a request/response model one probe item, over plain HTTP.

The cross-model study (docs/crossmodel_preregistration.md) requires that every model receive the
same item text, the same instruction and the same answer schema, and that the exact request sent to
each one be committable so the parity claim can be checked rather than trusted. So the request body
is built here as a dict and posted as JSON: no provider SDK sits between the registration and the
bytes.

Only what the study needs: one system instruction, one user turn, tool/function schemas with a
fixed enum, and up to a few turns so a variant that wants two calls can make them.
"""
import asyncio
import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_TOKENS = 1024
TIMEOUT_S = 120
# Models whose API dropped forced tool calls: tool_choice "tool" and "any" are refused
# (measured 2026-09-22 on claude-opus-5-5), so these get "auto" and rely on the instruction.
NO_FORCED_TOOL_CHOICE = {"claude-opus-5-5"}


def _ssl_context():
    """python.org builds on macOS ship no CA bundle, so urllib cannot verify anything by default.

    certifi comes with the HTTP stack the Gemini client already uses, which is why those calls
    worked and these did not. Verification is never disabled - an unverified request to a provider
    carrying an API key is not a trade worth making.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_CTX = _ssl_context()


class ApiError(RuntimeError):
    """A provider error, carrying the HTTP status so the runner can tell retryable from not."""

    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {str(body)[:200]}")
        self.status = status
        self.body = body


def schema_of(tool):
    """The tool's JSON Schema, exactly as the Gemini declaration carries it.

    `behavior` is Live-only scheduling and is dropped; every field name, type and enum value is
    passed through untouched, because that is what parity means here.
    """
    return json.loads(json.dumps(tool["parameters"]))


def user_turn(provider, text, images=()):
    """One user turn carrying text and, when the study calls for them, frames.

    Each provider spells an image differently; what must not differ is the text beside it or the
    order (frames first, then the question), so the same evidence reaches every model.
    """
    if not images:
        return {"role": "user", "content": text}
    b64 = [base64.b64encode(Path(p).read_bytes()).decode() for p in images]
    if provider == "anthropic":
        parts = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                              "data": d}} for d in b64]
        return {"role": "user", "content": parts + [{"type": "text", "text": text}]}
    if provider == "openai_responses":
        parts = [{"type": "input_image", "image_url": f"data:image/jpeg;base64,{d}"} for d in b64]
        return {"role": "user", "content": parts + [{"type": "input_text", "text": text}]}
    parts = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{d}"}}
             for d in b64]
    return {"role": "user", "content": parts + [{"type": "text", "text": text}]}


def build_request(provider, model, instruction, tools, messages, force_tool=None, tool_choice=None, **extra):
    """The literal request body. Pure, so a test and a committed artifact can both check it."""
    if provider == "anthropic":
        body = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": instruction,
            "messages": messages,
            "tools": [{"name": t["name"], "description": t["description"],
                       "input_schema": schema_of(t)} for t in tools],
        }
        if model in NO_FORCED_TOOL_CHOICE or tool_choice == "auto":
            body["tool_choice"] = {"type": "auto"}
        else:
            body["tool_choice"] = ({"type": "tool", "name": force_tool} if force_tool
                                   else {"type": "any"})
    elif provider == "openai_responses":
        # gpt-6-astra refuses function tools on /v1/chat/completions unless reasoning_effort is
        # "none". That is an intervention, not a default, and the registration keeps each model at
        # its own default reasoning - so this endpoint is used instead. The shape below was read
        # from one real call, not guessed.
        body = {
            "model": model,
            "instructions": instruction,
            "input": messages,
            "tools": [{"type": "function", "name": t["name"], "description": t["description"],
                       "parameters": schema_of(t)} for t in tools],
        }
        body["tool_choice"] = ({"type": "function", "name": force_tool} if force_tool
                               else "required")
    elif provider == "openai":
        body = {
            "model": model,
            "messages": [{"role": "system", "content": instruction}] + messages,
            "tools": [{"type": "function",
                       "function": {"name": t["name"], "description": t["description"],
                                    "parameters": schema_of(t)}} for t in tools],
        }
        body["tool_choice"] = ({"type": "function", "function": {"name": force_tool}} if force_tool
                               else "required")
    else:
        raise ValueError(provider)
    body.update(extra)
    return body


def url_for(provider):
    return {"anthropic": ANTHROPIC_URL, "openai": OPENAI_URL,
            "openai_responses": OPENAI_RESPONSES_URL}[provider]


def _headers(provider, key):
    if provider == "anthropic":
        return {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json"}
    return {"authorization": f"Bearer {key}", "content-type": "application/json"}


def _post(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise ApiError(e.code, e.read().decode(errors="replace")) from None
    except urllib.error.URLError as e:
        raise ApiError(0, str(e.reason)) from None


def parse(provider, response):
    """(calls, spoken text, usage) from one response. Malformed arguments are kept as raw text."""
    calls, spoken = [], ""
    if provider == "anthropic":
        for block in response.get("content") or []:
            if block.get("type") == "text":
                spoken += block["text"]
            elif block.get("type") == "tool_use":
                calls.append({"id": block.get("id"), "name": block["name"],
                              "args": block.get("input") or {}})
        u = response.get("usage") or {}
        usage = {"prompt_token_count": u.get("input_tokens"),
                 "response_token_count": u.get("output_tokens")}
    elif provider == "openai_responses":
        for item in response.get("output") or []:
            if item.get("type") == "function_call":
                raw = item.get("arguments") or "{}"
                try:
                    args = json.loads(raw)
                except json.JSONDecodeError:
                    args = {"__unparsed__": raw}
                calls.append({"id": item.get("call_id"), "name": item.get("name"), "args": args,
                              "raw": item})
            elif item.get("type") == "message":
                for part in item.get("content") or []:
                    spoken += part.get("text") or ""
        u = response.get("usage") or {}
        usage = {"prompt_token_count": u.get("input_tokens"),
                 "response_token_count": u.get("output_tokens"),
                 "thoughts_token_count": (u.get("output_tokens_details") or {}).get("reasoning_tokens")}
    else:
        msg = ((response.get("choices") or [{}])[0].get("message")) or {}
        spoken = msg.get("content") or ""
        for c in msg.get("tool_calls") or []:
            fn = c.get("function") or {}
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = {"__unparsed__": raw}
            calls.append({"id": c.get("id"), "name": fn.get("name"), "args": args})
        u = response.get("usage") or {}
        usage = {"prompt_token_count": u.get("prompt_tokens"),
                 "response_token_count": u.get("completion_tokens")}
    return calls, spoken, {k: v for k, v in usage.items() if v is not None}


def _acknowledge(provider, calls):
    """The turn that hands each call a neutral result, so a second call can follow."""
    if provider == "anthropic":
        return [{"role": "user",
                 "content": [{"type": "tool_result", "tool_use_id": c["id"], "content": "recorded"}
                             for c in calls]}]
    if provider == "openai_responses":
        return [{"type": "function_call_output", "call_id": c["id"], "output": "recorded"}
                for c in calls]
    return [{"role": "tool", "tool_call_id": c["id"], "content": "recorded"} for c in calls]


def _assistant_turn(provider, response, calls):
    """What the model said, in the shape its own API wants echoed back."""
    if provider == "anthropic":
        return [{"role": "assistant", "content": response.get("content") or []}]
    if provider == "openai_responses":
        # Every item, in order: a function_call echoed without the reasoning item that produced it
        # is rejected, and picking items apart is how that happened once already.
        return list(response.get("output") or [])
    return [(response.get("choices") or [{}])[0].get("message") or {}]


class StandardAsker:
    """One provider, one model, one item per call. The Live backends' counterpart."""

    def __init__(self, provider, model, key=None, post=_post, max_turns=3, tool_choice=None):
        self.provider, self.model, self.max_turns = provider, model, max_turns
        self.tool_choice = tool_choice    # "auto" lifts forced calls (Anthropic only)
        self.key = key or os.environ.get(
            "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY", "")
        self._post = post
        self.last_request = None          # committed verbatim as the parity evidence

    async def __call__(self, instruction, tools, required, text, images=()):
        calls, spoken, usage = [], "", {}
        messages = [user_turn(self.provider, text, images)]
        for _ in range(self.max_turns):
            missing = [r for r in required if r not in {c["name"] for c in calls}]
            if not missing:
                break
            body = build_request(self.provider, self.model, instruction, tools, messages,
                                 force_tool=missing[0] if len(required) > 1 else None,
                                 tool_choice=self.tool_choice)
            self.last_request = body
            response = await asyncio.to_thread(self._post, url_for(self.provider),
                                               _headers(self.provider, self.key), body)
            new, said, u = parse(self.provider, response)
            calls += new
            spoken += said
            for k, v in u.items():
                usage[k] = usage.get(k, 0) + v
            if not new:                    # nothing to acknowledge, and nothing would change
                break
            messages = messages + _assistant_turn(self.provider, response, new) + \
                _acknowledge(self.provider, new)
        return {"calls": [{"name": c["name"], "args": c["args"]} for c in calls],
                "spoken": spoken, "usage": usage, "reminders": 0}
