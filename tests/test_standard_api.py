"""The cross-model backend: the same question reaches every provider, byte for byte."""
import asyncio
import json

import pytest

from livelab.probes import SINGLE_TURN, prefix_message, variant_setup
from livelab.prompting import SYSTEM_INSTRUCTION
from livelab.standard_api import ApiError, StandardAsker, build_request, parse

ITEMS = json.load(open("data/probes/items.json"))


def a_reply(calls=(), text=""):
    content = [{"type": "text", "text": text}] if text else []
    content += [{"type": "tool_use", "id": f"tu{i}", "name": n, "input": a}
                for i, (n, a) in enumerate(calls)]
    return {"content": content, "usage": {"input_tokens": 100, "output_tokens": 7}}


def o_reply(calls=(), text=""):
    tc = [{"id": f"c{i}", "type": "function",
           "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(calls)]
    msg = {"role": "assistant", "content": text or None}
    if tc:
        msg["tool_calls"] = tc
    return {"choices": [{"message": msg}], "usage": {"prompt_tokens": 100, "completion_tokens": 7}}


def test_the_answer_schema_survives_translation_to_both_providers():
    """Parity is field names and enum values, so assert them rather than trusting the mapping."""
    _, tools, _ = variant_setup("B0")
    want = tools[0]["parameters"]
    ant = build_request("anthropic", "m", "sys", tools, [])["tools"][0]
    opn = build_request("openai", "m", "sys", tools, [])["tools"][0]["function"]
    assert ant["input_schema"] == want and opn["parameters"] == want
    for schema in (ant["input_schema"], opn["parameters"]):
        assert schema["properties"]["execution_state"]["enum"] == ["NORMAL", "ANOMALOUS", "UNKNOWN"]
    assert "behavior" not in json.dumps(ant) and "behavior" not in json.dumps(opn)


def test_both_providers_get_the_same_instruction_and_item_text():
    item = ITEMS["in_context"][0]
    instruction, tools, _ = variant_setup("B0")
    text = prefix_message(item["replay_id"], item["k"])
    ant = build_request("anthropic", "m", instruction, tools, [{"role": "user", "content": text}])
    opn = build_request("openai", "m", instruction, tools, [{"role": "user", "content": text}])
    assert ant["system"] == instruction == SYSTEM_INSTRUCTION + SINGLE_TURN
    assert opn["messages"][0] == {"role": "system", "content": instruction}
    assert ant["messages"][-1]["content"] == text == opn["messages"][-1]["content"]


def test_a_single_call_item_is_read_the_same_from_either_provider():
    args = {"execution_state": "UNKNOWN", "scientific_evidence": "NOT_YET_AVAILABLE"}
    for provider, reply in (("anthropic", a_reply), ("openai", o_reply)):
        calls, spoken, usage = parse(provider, reply([("report_assessment", args)], "thinking"))
        assert [(c["name"], c["args"]) for c in calls] == [("report_assessment", args)]
        assert spoken == "thinking" and usage["prompt_token_count"] == 100


def test_two_calls_take_two_turns_and_the_first_is_acknowledged():
    _, tools, required = variant_setup("B1")
    seen = []

    def post(url, headers, body):
        seen.append(body)
        if len(seen) == 1:
            return a_reply([("report_verifiability", {"atmosphere": "cannot_verify",
                                                      "temperature": "verified",
                                                      "gas_flow": "verified"})])
        return a_reply([("report_assessment", {"execution_state": "NORMAL"})])

    res = asyncio.run(StandardAsker("anthropic", "m", key="k", post=post)("sys", tools, required, "events"))
    assert [c["name"] for c in res["calls"]] == ["report_verifiability", "report_assessment"]
    assert len(seen) == 2
    # the second request carries the model's own turn and a neutral result for its call
    roles = [m["role"] for m in seen[1]["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert seen[1]["messages"][-1]["content"][0]["type"] == "tool_result"
    assert seen[1]["tool_choice"] == {"type": "tool", "name": "report_assessment"}
    assert res["usage"]["prompt_token_count"] == 200        # summed across both turns


def test_silence_is_returned_as_silence_and_never_invented():
    _, tools, required = variant_setup("B0")
    res = asyncio.run(StandardAsker("openai", "m", key="k",
                                    post=lambda *a: o_reply(text="I cannot do that"))(
        "sys", tools, required, "events"))
    assert res["calls"] == [] and res["spoken"] == "I cannot do that"


def test_a_provider_error_carries_its_status_so_the_runner_can_tell_them_apart():
    _, tools, required = variant_setup("B0")

    def post(*a):
        raise ApiError(429, "rate limited")
    with pytest.raises(ApiError) as e:
        asyncio.run(StandardAsker("anthropic", "m", key="k", post=post)("s", tools, required, "t"))
    assert e.value.status == 429


def test_the_request_actually_sent_is_kept_for_the_record():
    _, tools, required = variant_setup("B0")
    asker = StandardAsker("openai", "gpt-x", key="k",
                          post=lambda *a: o_reply([("report_assessment", {"execution_state": "NORMAL"})]))
    asyncio.run(asker("sys", tools, required, "events"))
    assert asker.last_request["model"] == "gpt-x"
    assert asker.last_request["messages"][-1]["content"] == "events"


def r_reply(calls=(), text="", reasoning=0):
    out = [{"id": f"fc{i}", "type": "function_call", "call_id": f"call_{i}", "name": n,
            "arguments": json.dumps(a)} for i, (n, a) in enumerate(calls)]
    if text:
        out.append({"type": "message", "content": [{"type": "output_text", "text": text}]})
    return {"output": out, "usage": {"input_tokens": 100, "output_tokens": 7,
                                     "output_tokens_details": {"reasoning_tokens": reasoning}}}


def test_the_responses_endpoint_gets_the_same_schema_and_instruction():
    """gpt-6-astra needs /v1/responses for function tools; parity must survive the move."""
    instruction, tools, _ = variant_setup("B0")
    body = build_request("openai_responses", "gpt-6-astra", instruction, tools,
                         [{"role": "user", "content": "events"}])
    assert body["instructions"] == instruction
    assert body["input"][-1]["content"] == "events"
    assert body["tools"][0]["parameters"] == tools[0]["parameters"]
    assert body["tools"][0]["parameters"]["properties"]["execution_state"]["enum"] == \
        ["NORMAL", "ANOMALOUS", "UNKNOWN"]
    assert "reasoning_effort" not in body          # the model's own default is what is measured


def test_a_responses_answer_and_its_reasoning_tokens_are_read():
    args = {"execution_state": "UNKNOWN"}
    calls, spoken, usage = parse("openai_responses", r_reply([("report_assessment", args)],
                                                             "thinking out loud", reasoning=512))
    assert [(c["name"], c["args"]) for c in calls] == [("report_assessment", args)]
    assert spoken == "thinking out loud" and usage["thoughts_token_count"] == 512


def test_responses_two_calls_echo_the_call_and_its_output():
    _, tools, required = variant_setup("B1")
    seen = []

    def post(url, headers, body):
        seen.append(body)
        if len(seen) == 1:
            return r_reply([("report_verifiability", {"atmosphere": "cannot_verify",
                                                      "temperature": "verified",
                                                      "gas_flow": "verified"})])
        return r_reply([("report_assessment", {"execution_state": "NORMAL"})])

    res = asyncio.run(StandardAsker("openai_responses", "gpt-6-astra", key="k", post=post)(
        "sys", tools, required, "events"))
    assert [c["name"] for c in res["calls"]] == ["report_verifiability", "report_assessment"]
    kinds = [i.get("type") or i.get("role") for i in seen[1]["input"]]
    assert kinds == ["user", "function_call", "function_call_output"]
    # the whole output is echoed, reasoning items included, or the API rejects the call
    assert seen[1]["input"][1] is not None
    assert seen[1]["tool_choice"] == {"type": "function", "name": "report_assessment"}


def test_responses_echoes_reasoning_items_too():
    """A function_call echoed without the reasoning item that produced it is rejected by the API."""
    _, tools, required = variant_setup("B1")
    seen = []

    def post(url, headers, body):
        seen.append(body)
        if len(seen) == 1:
            r = r_reply([("report_verifiability", {"atmosphere": "cannot_verify",
                                                   "temperature": "verified", "gas_flow": "verified"})])
            r["output"].insert(0, {"id": "rs_1", "type": "reasoning", "summary": []})
            return r
        return r_reply([("report_assessment", {"execution_state": "NORMAL"})])

    asyncio.run(StandardAsker("openai_responses", "gpt-6-astra", key="k", post=post)(
        "sys", tools, required, "events"))
    assert [i.get("type") or i.get("role") for i in seen[1]["input"]] == \
        ["user", "reasoning", "function_call", "function_call_output"]


def test_the_distillation_port_changes_nouns_and_not_the_contract():
    """docs/realdata_preregistration.md: the port may rename the process, never the contract."""
    from livelab.prompting import SYSTEM_INSTRUCTION as v4
    from livelab.realdata_prompt import SYSTEM_INSTRUCTION as ported
    for sentence in [
        "or UNKNOWN if the available evidence does not let you tell.",
        "- attribution: if execution is anomalous, which layer: instrument_process, sample_handling,",
        "  software, undetermined, or none.",
        "- proposed_action: continue, discriminating_test, pause, safe_shutdown, or call_human.",
        "- missing_evidence: what observation would resolve anything you cannot yet determine.",
    ]:
        assert sentence in v4 and sentence in ported, sentence
    assert "furnace" not in ported and "column" in ported


def test_frames_reach_every_provider_with_the_same_text_beside_them():
    """docs/vision_preregistration.md: the frames may be spelled differently, the evidence may not."""
    from livelab.standard_api import user_turn
    import base64, tempfile, os
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"\xff\xd8\xff\xe0jpegbytes")
    os.close(fd)
    want = base64.b64encode(b"\xff\xd8\xff\xe0jpegbytes").decode()
    turns = {p: user_turn(p, "the question", [path, path])
             for p in ("anthropic", "openai_responses", "openai")}
    for provider, turn in turns.items():
        blob = json.dumps(turn)
        assert blob.count(want) == 2, provider            # both frames, once each
        assert turn["content"][-1].get("text") == "the question", provider
        assert len(turn["content"]) == 3, provider        # frames first, then the question
    assert user_turn("anthropic", "just text") == {"role": "user", "content": "just text"}
    os.unlink(path)


def test_models_without_forced_tool_choice_get_auto():
    from livelab.standard_api import build_request
    body = build_request("anthropic", "claude-opus-5-5", "sys", 
                         [{"name": "t", "description": "d", "parameters": {"type": "object", "properties": {}}}],
                         [{"role": "user", "content": "x"}], force_tool="t")
    assert body["tool_choice"] == {"type": "auto"}
