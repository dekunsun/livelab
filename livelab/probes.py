"""The UNKNOWN probe study (docs/probe_preregistration.md): prompts, tools, a single-turn runner
and scoring. The main benchmark's frozen v4 wording is reused, never modified."""
import copy
import json
import os
from pathlib import Path

from .prompting import REPORT_ASSESSMENT, SYSTEM_INSTRUCTION, async_only, event_message, tools_for

ROOT = Path(__file__).resolve().parent.parent
PROBE_VERSION = "p1"

# The benchmark replays events one at a time; here events 0..k arrive in one turn.
SINGLE_TURN = ("\nIn this session the events so far arrive together in one message, one JSON object per line. "
               "Report your judgment as of the LAST event: call report_assessment exactly once.")
B2_DEFINITION = ("\nNORMAL means the installed sensors positively show that the process is executing as expected. "
                 "If something that matters for the current stage cannot be checked with the installed sensors, "
                 "report UNKNOWN.")
B1_ORDER = ("\nBefore report_assessment, call report_verifiability once, then call report_assessment.")

REPORT_VERIFIABILITY = {
    "name": "report_verifiability",
    "description": "For the current stage, say whether each condition can be verified with the installed sensors.",
    "behavior": "BLOCKING",
    "parameters": {"type": "object", "properties": {
        c: {"type": "string", "enum": ["verified", "cannot_verify", "anomalous"]}
        for c in ("atmosphere", "temperature", "gas_flow")},
        "required": ["atmosphere", "temperature", "gas_flow"]},
}
ANSWER_DETECTABILITY = {
    "name": "answer_detectability", "behavior": "BLOCKING",
    "description": "Answer whether the installed sensors could show the fault.",
    "parameters": {"type": "object", "properties": {
        "detectable": {"type": "string", "enum": ["yes", "no"]},
        "channels": {"type": "array", "items": {"type": "string"}}}, "required": ["detectable"]},
}
ANSWER_DISTINGUISHABILITY = {
    "name": "answer_distinguishability", "behavior": "BLOCKING",
    "description": "Answer whether the installed sensors could tell the two faults apart.",
    "parameters": {"type": "object", "properties": {
        "distinguishable": {"type": "string", "enum": ["yes", "no"]}}, "required": ["distinguishable"]},
}
SENSOR_WORDS = {"thermocouple": "control thermocouple", "heater_power": "heater power meter",
                "mfc_ar": "argon mass-flow controller (reports actual flow)",
                "pressure_gauge": "tube pressure gauge", "o2_exhaust": "exhaust O2 sensor"}
FAULT_WORDS = {"seal_leak": "a seal (O-ring) air leak", "exhaust_blockage": "a partial blockage of the exhaust line",
               "thermocouple_drift": "a drifting control thermocouple",
               "mfc_stuck": "an argon mass-flow controller stuck at a fixed flow"}
REGIME_WORDS = {"lpcvd": "a low-pressure CVD run (a few Torr, pumped)",
                "apcvd": "an atmospheric-pressure CVD run (about 760 Torr, flow-through)"}
P1_INSTRUCTION = ("You are an expert in monitoring chemical vapor deposition (CVD) runs in a single-zone tube furnace "
                  "growing MoS2 on SiO2/Si. Answer the question by calling the function provided.")

# On 2026-09-19 the Extended Thinking model's function-call path degraded over a run: no call was
# emitted, the server told the client nothing, and the model said "a system error occurred". That
# is indistinguishable, from the client, from a model declining to answer.
#
# A trivial canary does not catch it: a one-enum call still succeeded at the same minute as a real
# item failed three times, because the failure depends on the request (a 5k-token prefix and the
# full report_assessment schema), not on a global switch. The control therefore replays the SAME
# request against the standard Live model, which is what separated the two by hand
# (pre-registration, deviation 7).
CONTROL_MODEL = "gemini-3.8-live"
CANARY_TOOL = {
    "name": "canary", "behavior": "BLOCKING",
    "description": "Acknowledge this message.",
    "parameters": {"type": "object", "properties": {"ok": {"type": "string", "enum": ["yes"]}}, "required": ["ok"]},
}
CANARY_INSTRUCTION = "Call the canary function with ok=yes. Say nothing else."


async def calls_come_back(connect, instruction, tools, required, text, model_id=CONTROL_MODEL,
                          thinking_level=None, patience=240):
    """Does this model emit the required calls for this request? Only whether, never what."""
    import asyncio
    try:
        res = await asyncio.wait_for(
            run_single_turn(connect, instruction, tools, required, text, max_reminders=1,
                            model_id=model_id, thinking_level=thinking_level, patience=patience),
            patience + 120)
    except Exception:       # noqa: BLE001 - any failure here means the path cannot be shown to work
        return False
    return not [r for r in required if r not in {c["name"] for c in res["calls"]}]


async def call_path_healthy(connect, model_id=CONTROL_MODEL, thinking_level=None, patience=60):
    """Can this model make any function call at all? Catches a total outage, not a per-request one."""
    return await calls_come_back(connect, CANARY_INSTRUCTION, [CANARY_TOOL], ["canary"], "Call canary now.",
                                 model_id, thinking_level, patience)


def variant_setup(variant):
    """(system instruction, tools, required tool names) for an in-context variant."""
    report = copy.deepcopy(REPORT_ASSESSMENT)
    instruction = SYSTEM_INSTRUCTION + SINGLE_TURN
    tools, required = [report], ["report_assessment"]
    if variant == "B1":
        tools, required = [REPORT_VERIFIABILITY, report], ["report_verifiability", "report_assessment"]
        instruction += B1_ORDER
    elif variant == "B2":
        instruction += B2_DEFINITION
    elif variant == "B3":
        report["parameters"]["properties"]["execution_state"]["enum"] = ["CANNOT_VERIFY", "ANOMALOUS", "NORMAL"]
        instruction = instruction.replace("or UNKNOWN if the available evidence", "or CANNOT_VERIFY if the available evidence")
    elif variant != "B0":
        raise ValueError(variant)
    return instruction, tools, required


def prefix_message(replay_id, k, replay_dir=None):
    """Events 0..k in the benchmark's compact arm-A format, one per line."""
    replay_dir = Path(replay_dir) if replay_dir else ROOT / "data/replays"
    events = [json.loads(line) for line in open(replay_dir / f"{replay_id}.jsonl")][:k + 1]
    lines, previous = [], None
    for e in events:
        text, _ = event_message(e, "A", None, ROOT / "data/images/cvd", None, previous)
        lines.append(text)
        previous = e
    return "\n".join(lines)


def p1_message(item):
    sensors = ", ".join(SENSOR_WORDS[s] for s in item["installed"])
    base = f"Setting: {REGIME_WORDS[item['regime']]}. Installed sensors: {sensors}. No other sensors or cameras."
    if item["kind"] == "detectable":
        return (base + f" Question: if {FAULT_WORDS[item['fault']]} developed during growth, could these sensors show "
                "it at any point in the run (growth or cooldown)? Call answer_detectability.")
    return (base + f" Question: if the readings showed an anomaly, could these sensors tell {FAULT_WORDS['seal_leak']} "
            f"apart from {FAULT_WORDS['exhaust_blockage']}? Call answer_distinguishability.")


def p1_setup(item):
    tool = ANSWER_DETECTABILITY if item["kind"] == "detectable" else ANSWER_DISTINGUISHABILITY
    return P1_INSTRUCTION, [tool], [tool["name"]]


async def run_single_turn(connect, instruction, tools, required, text, seed=0, max_reminders=2, model_id="gemini-3.8-live",
                          thinking_level=None, patience=240, images=()):
    """One Live session, one user turn; returns every function call made, what was said, and usage."""
    from google.genai import types
    config = types.LiveConnectConfig(response_modalities=["AUDIO"], system_instruction=instruction,
                                     tools=[{"function_declarations": tools_for(model_id, tools)}],
                                     output_audio_transcription={}, seed=seed,
                                     **({"thinking_config": types.ThinkingConfig(thinking_level=thinking_level)}
                                        if thinking_level else {}))
    import asyncio
    calls, spoken, usage, reminders, busy = [], "", None, 0, False
    started = asyncio.get_running_loop().time()
    cm = connect(config)
    session = await cm.__aenter__()
    try:
        parts = [{"inline_data": {"mime_type": m, "data": b}} for m, b in images] + [{"text": text}]
        await session.send_client_content(turns={"role": "user", "parts": parts}, turn_complete=True)
        while True:
            stream = session.receive().__aiter__()
            while True:
                try:
                    left = started + patience - asyncio.get_running_loop().time()
                    wait = (left if left > 1 else 120.0) if async_only(model_id) else None
                    msg = await asyncio.wait_for(stream.__anext__(), wait)
                except (StopAsyncIteration, asyncio.TimeoutError):
                    break
                if getattr(msg, "usage_metadata", None) is not None:
                    usage = msg.usage_metadata.model_dump(exclude_none=True)
                sc = getattr(msg, "server_content", None)
                if sc is not None and getattr(sc, "interaction_status", None) is not None:
                    busy = str(sc.interaction_status).endswith("IN_PROGRESS")
                if sc is not None and getattr(sc, "output_transcription", None) and sc.output_transcription.text:
                    spoken += sc.output_transcription.text
                if getattr(msg, "tool_call", None):
                    responses = []
                    for fc in msg.tool_call.function_calls:
                        calls.append({"name": fc.name, "args": dict(fc.args or {})})
                        responses.append(types.FunctionResponse(
                            id=fc.id, name=fc.name, response={"result": "recorded"},
                            **({} if async_only(model_id) else {"scheduling": "SILENT"})))
                    await session.send_tool_response(function_responses=responses)
                    if not [r for r in required if r not in {c["name"] for c in calls}]:
                        break       # all required calls are in; the session ends, so nothing can leak
                if sc is not None and getattr(sc, "turn_complete", False):
                    break
            missing = [r for r in required if r not in {c["name"] for c in calls}]
            if not missing or reminders >= max_reminders:
                break
            if busy or (async_only(model_id) and asyncio.get_running_loop().time() - started < patience):
                continue            # async model may still be reasoning: keep listening, never interrupt
            reminders += 1
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": f"Call {missing[0]} now."}]}, turn_complete=True)
    finally:
        await cm.__aexit__(None, None, None)
    return {"calls": calls, "spoken": spoken, "usage": usage, "reminders": reminders}


def last_args(result, name):
    found = [c["args"] for c in result["calls"] if c["name"] == name]
    return found[-1] if found else None


def answered(results):
    """Drop items with no answer: silence is excluded from every rate, never counted as a choice.

    A missing answer can be the model declining or the API's function-call path failing, and the
    two are indistinguishable from the client (pre-registration, deviation 7). Coverage is reported
    beside each rate so that a measure computed on few items cannot be mistaken for a full one."""
    return {v: {i: d for i, d in items.items() if not (d.get("unanswered") or d.get("no_answer"))}
            for v, items in results.items()}


def score(items, results):
    """Registered measures. `results[variant][item_id]` is a run_single_turn result."""
    abstain = {"UNKNOWN", "CANNOT_VERIFY"}
    out = {}
    ctx = items["in_context"]
    saved, results = results, answered(results)
    for variant in ("B0", "B1", "B2", "B3"):
        res = results.get(variant, {})
        m = {"coverage": {}}
        for s, want in (("U", "abstain"), ("N", "abstain"), ("A", "ANOMALOUS")):
            got = [(last_args(res[i["item_id"]], "report_assessment") or {}).get("execution_state")
                   for i in ctx if i["set"] == s and i["item_id"] in res]
            hits = sum((g in abstain) if want == "abstain" else (g == "ANOMALOUS") for g in got)
            m[{"U": "abstention_on_U", "N": "over_abstention_on_N", "A": "detection_on_A"}[s]] = (hits, len(got))
            m["coverage"][s] = (len(got), sum(i["set"] == s for i in ctx))   # answered / registered
        if variant == "B1":
            u = [i for i in ctx if i["set"] == "U" and i["item_id"] in res]
            conflate = sum(((last_args(res[i["item_id"]], "report_verifiability") or {}).get("atmosphere") == "cannot_verify"
                            and (last_args(res[i["item_id"]], "report_assessment") or {}).get("execution_state") == "NORMAL")
                           for i in u)
            says_cannot = sum((last_args(res[i["item_id"]], "report_verifiability") or {}).get("atmosphere") == "cannot_verify"
                              for i in u)
            m["atmosphere_cannot_verify_on_U"] = (says_cannot, len(u))
            m["conflation_rate_on_U"] = (conflate, len(u))
            cells = [(i, c) for i in ctx if i["item_id"] in res for c in ("atmosphere", "temperature", "gas_flow")]
            m["verifiability_accuracy"] = (sum((last_args(res[i["item_id"]], "report_verifiability") or {}).get(c)
                                               == i["truth_verifiability"][c] for i, c in cells), len(cells))
        out[variant] = m
    res = results.get("P1", {})
    out.setdefault("P1", {})["coverage"] = (len(res), len(items["p1"]))       # answered / registered
    for kind, key in (("detectable", "detectable"), ("distinguishable", "distinguishable")):
        its = [i for i in items["p1"] if i["kind"] == kind and i["item_id"] in res]
        fn = "answer_detectability" if kind == "detectable" else "answer_distinguishability"
        correct = {"yes": [0, 0], "no": [0, 0]}
        for i in its:
            correct[i["truth"]][1] += 1
            correct[i["truth"]][0] += (last_args(res[i["item_id"]], fn) or {}).get(key) == i["truth"]
        rates = [c / n for c, n in correct.values() if n]
        out.setdefault("P1", {})[kind] = {
            "accuracy": (sum(c for c, _ in correct.values()), sum(n for _, n in correct.values())),
            "balanced_accuracy": sum(rates) / len(rates) if rates else float("nan"),
            "by_truth": {k: tuple(v) for k, v in correct.items()}}
    return out
