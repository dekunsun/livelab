# Core runner v2: rules

Runner v2 asks the same frozen items, with the same instructions, tools and arms, as runner v1, and
its records score with the same `livelab.core.score`. What changes is what it records and three
rules it fixes in advance. It exists because v1's records could not separate a model from the way
it was asked ([v1 limitations](core_runner_v1_limitations.md)). Code: `livelab/runner_v2.py`,
`scripts/run_core_v2.py`; results: `results/core_v2/<model>/<arm>/<item_id>.json`, never mixed with
v1's.

## What every record keeps

- **Two hashes, two claims.** `item_text_sha256` is computed from the frozen item by the item
  generator. Every message the client hands the SDK (setup, first user turn, tool responses,
  reminders; for REST, every full request body) is kept in full with its own `sha256`, computed at
  the point of sending. `first_turn_matches_item` says whether the first user turn equals the frozen
  item text. This shows what the client submitted, not that the server processed all of it. No
  credentials are ever recorded.
- **Every server message**, time-stamped, with audio bytes replaced by their length and hash: tool
  calls with their ids, `usage_metadata`, `interaction_status`, `interrupted`, `turn_complete` and
  `turn_complete_reason`. Every field of a message is read; one message can carry a tool call,
  usage and a status at once.
- **Every attempt.** A transport error before any submission starts a fresh attempt; each attempt's
  error is kept.

## Scoring: the first submission

- A **submission** is complete when each required tool has a protocol-valid call: the tool exists and
  its arguments satisfy the tool's schema (required fields present, enum values allowed). Validity
  never depends on whether the answer is right. Malformed calls are logged and are not submissions.
- The **first valid call of each required tool** is scored (`calls` in the record). Calls are taken
  in arrival order, and in list order within one message; a repeated call id counts once, at its
  first arrival.
- After the submission the runner **keeps collecting** until the session ends normally or a fixed
  grace period passes. Later calls are kept as `later_calls`; a final-answer-after-revision measure,
  if ever used, is a separate metric defined before the run. Collecting the session and accepting a
  changed answer are different things.
- **Submission status and collection status are separate.** A submission followed by a collection
  timeout is recorded as *submitted; collection timed out, usage may be incomplete*. It is never
  reclassified as no submission.
- **No submission is `timeout` or `protocol_incomplete`**, never a semantic UNKNOWN.

## Reminders

- Two results come from each run: **unprompted** (a submission before any reminder, within the
  deadline) and **with remedy** (a submission after reminders sent under the fixed rule below). The
  mode `--remedy none` sends no reminders at all.
- The fixed rule: a reminder (*"Call <tool> now."*) is sent only after the model's turn has ended
  without a submission, **and** the model is confirmed idle. For the standard Live model and the REST
  models, a completed turn whose status is not `IN_PROGRESS` counts as idle. For Extended Thinking,
  whose `turnComplete` does not mean background work has finished, only an explicit status that is not
  `IN_PROGRESS` counts. At most two reminders; each is recorded with its time, text and what was
  missing.
- **A reminder is never triggered by waiting.** If the status is missing or still in progress, the
  runner records that, waits to the deadline, and ends the item as `timeout` with the status marked
  unconfirmed. It does not infer that the model is idle.
- The first user turn is sent with `turn_complete=true`, as the protocol requires to start the
  model's answer; this rule governs only what is sent after the interaction has begun.

## Extended Thinking

Tools are declared `NON_BLOCKING`; tool responses carry no `scheduling` field, because the model's
own documentation says it does not support scheduling configuration. What the server does when it
is omitted is not assumed; the events show it.

## Validation before any rerun

1. Fake-event tests (`tests/test_runner_v2.py`) script server behaviour and check each rule above:
   a call then a revision; `turnComplete` while `IN_PROGRESS`; no status ever; usage after the call;
   an interruption; no submission; one message carrying a call, usage and a status; repeated call ids
   and several calls in one message; a malformed call; a submission with no end.
2. A small real smoke run (a few items per backend) checks that the SDK and server behave as these
   rules assume, including where `interaction_status` actually appears. It does not judge models.
3. Only after both pass are any reruns made, each registered first.

## Observed in the smoke run (2026-09-22)

Three V1 items (`core_leak_lp_01__visible`, `core_leak_lp_01__hidden`, `core_normal_01__normal`) on
the standard Live model, Extended Thinking and Flash; records in `results/core_v2_smoke/`. It checks
the runner, not the models.

- Every item was submitted unprompted, with no reminder, no malformed call, no later call, and a
  first user turn equal to the frozen item text. Every session ended normally.
- **The standard Live model sends no `interaction_status` at all.** Its turn ends with
  `generation_complete` and `turn_complete`, and one usage message arrives after the call, in the same
  message as `turn_complete`, reporting 339–503 thinking tokens per item. Runner v1 closed the
  session at the call and lost that message; the model does reason.
- **Extended Thinking sends `interaction_status` inside `server_content`, beside `turn_complete`.** On
  the visible item: a first turn ended at 4 s with no call and status `IN_PROGRESS`; the call came at
  13 s; two more turns followed, the last with status `IDLE` at 23 s. Usage arrives once per turn
  (5,955 / 20,096 / 6,672 prompt tokens; 372 / 5,702 / 57 thinking tokens). The counts rise and fall,
  so they read as per-turn, not running totals; that is an inference, not documented. Runner v1 would
  have closed at 13 s, keeping only the first turn's usage (372 thinking tokens).
- Flash's usage arrives once per request; its first request carried 347–5,625 thinking tokens.
