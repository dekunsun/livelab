# Core runner v1: what its records can and cannot show

Every result under `results/core/` — all models, all arms, the repetitions, the tool-choice control
and the Gemini hand-off — was collected by **runner v1**: `scripts/run_core.py`,
`scripts/run_core_handoff.py`, `livelab/standard_api.py` and `livelab/probes.py` as of commit
56fe25f. The saved answers and their scores stay as they are. This note lists what those records
cannot support, found by an audit of the runner on 2026-09-22, before any rerun.

## What the records leave out

1. **The request actually sent.** Each answer keeps only the last 400 characters of the user text
   (`text_tail`). The system instruction, tool definitions, configuration and full message are not
   saved per call. The items are frozen and `text_for` is deterministic, so the *intended* input
   can be regenerated; that is not a record of what the client handed the SDK.
2. **Reminders.** When a turn ends without the required call, the Gemini REST path
   (`StandardAsker`) and the Live path (`run_single_turn`) send up to two user turns reading
   *"Call <tool> now."*. The count is returned but `run_core.py` does not save it, so it is unknown
   for every Gemini result: Live, Flash, Pro and the hand-off judge. A reminder changes the model's
   context, so two models capped at the same number of reminders may still have received different
   interventions. The Anthropic and OpenAI paths send no reminders.
3. **Retries.** `run_core.py` asks again, up to three times, when a call raises or returns no
   answer. Only console output records this. The console logs kept from these runs show no retry
   after a missing answer; the retries they show followed transport errors (credit exhausted, rate
   limits). The logs are not committed and do not cover every item.
4. **How a Live session ended.** The session is closed as soon as the required calls arrive. Any
   later revision, speech after the call, the final usage report and the session's
   `interaction_status`, `interrupted` and `turn_complete_reason` are not collected.
5. **Usage.** The REST paths sum usage over every request of an item; the Live path keeps the last
   usage message it saw, and for V0 and V1 it saw none (183 of 240 Live files have no usage). Input
   length cannot prove the evidence arrived intact, and reasoning compute cannot be compared between
   Live and the REST models from these records.
6. **The Extended Thinking path** (earlier probe studies, not Core). If no `interaction_status`
   arrives, the runner sends a reminder after 240 s even though background reasoning may still be
   running, and a user turn with `turn_complete=true` can interrupt it. It also closes the session as
   soon as the required calls arrive.

7. **An output cap that cut answers off.** Anthropic requests were capped at 1,024 output tokens
   and the stop reason was not saved. Every Claude answer that later failed a schema check used
   exactly 1,024 (Opus 5.5: 102; unforced Opus 5: 26), and no complete answer did. The execution state, written first,
   survived in every case; later fields (the proposed action, sometimes the evidence) did not.
   Opus 5.5's reasoning cannot be switched off, so it wrote the longest answers.

## What this means for the readings

- **All counts stand as observations of the configurations that were run.** Nothing is rescored.
- **Anthropic and OpenAI results** received no reminders; forced and unforced calls are recorded
  per answer (`tool_choice`). Their readings are unchanged.
- **Gemini 3.8 Flash against Gemini 3.8 Live (22 against 10 pairs)** is kept as an observation of
  two configurations that differ in model, interface (a Live API audio session against REST),
  reasoning configuration and compute, and possibly in reminders. **No mechanism is attributed**;
  in particular the result does not show that the live mode costs judgment, and Core has no
  real-time interaction in which Live's own strengths would be used.
- **The hand-off (13 against 22)** is kept as an observation under runner v1: Flash judging from the
  readings did better than Flash judging from this Live narration. The design preference it
  supports — give the diagnosing model direct access to the evidence — is a design choice, not a
  general finding that summaries cannot work. The hand-off was not rerun under runner v2: the
  narrations it rests on are saved, and runner v1's faults concern how Live's own answers were
  collected, not what its narrations said.
- **"Gemini moved by nothing, at any thinking level"** (the cross-model and system-state probe
  studies) is **suspended** until the Extended Thinking call path is reviewed.

## Runner v2

A separate version with its own results directory (`results/core_v2/`), so no v1 record is
overwritten. Its rules, and the fake-event tests that check them, are in
[core_runner_v2.md](core_runner_v2.md). A small real smoke run checks that the SDK and server behave
as the runner assumes; it does not judge models. Only after it passes are any reruns made.
