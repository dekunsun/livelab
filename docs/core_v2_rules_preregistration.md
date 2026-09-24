# Pre-registration: stating the task's cause and action rules (V1S) on Core under runner v2

Status: **registered 2026-09-24, before any V1S call is made.** Smoke calls described below are
outside the scored set and are made after this file is committed.

## Why

Under runner v2 no model passes the gate ([leaderboard](results/core_leaderboard.md)):
- **Claude Opus 5.5** leaves determinable causes undetermined: 9 · 9 · 10 of 20 across three runs.
- **Gemini 3.1 Pro** names a blockage on every undeterminable cause it answered: 19 of 19.
- Both propose `continue` on items whose state is not NORMAL: Opus 5.5 0 · 1 · 5, Pro 20 of 70.

The scorer judges cause and action by two rules that the model was never told:
1. a cause counts only if it is the one fault in the library that fits the deviating readings;
2. each state allows a fixed set of actions.

A check of the request actually sent (`livelab.probes.variant_setup("B0")`, the V1 instruction and
tool schema) found that neither the fault library's signatures nor the allowed action sets appear in
it. The model sees the cause names in the tool's enum, not what each fault does to the readings.

So the question is bounded:

> **Does telling the model the scoring rules for cause and action — and the fault library those rules
> depend on — improve the current configurations' cause and action answers, without breaking the state
> answers?**

It is a task-rule clarification test, not a prompt search. The rules are general. Nothing in the added
text depends on the item: no state, no candidate cause, no answer.

## The intervention (arm V1S)

- V1S is V1 with one block appended to the system instruction (`livelab.core.rules_block()`).
- The block is generated from `livelab.observability.SIGNATURES` and the frozen-status constants, so
  it states exactly what the scorer uses.
- Each item's message, the tool schema, the reminder rule and every request setting are V1's.
- `tests/test_core.py::test_v1s_adds_only_the_rules_block_to_the_instruction` checks this on all 80 items.
- `test_rules_block_states_the_scoring_library_exactly` checks the library text against the scorer.

The block, as sent:

```
Task rules for specific_cause and proposed_action. These are this benchmark's conventions and they decide how your answer is scored.
Fault library. Only these faults are considered, each with the readings it moves in this simulated furnace:
- Low-pressure runs (tube pressure a few Torr): seal_leak moves tube pressure P and exhaust oxygen O2; exhaust_blockage moves tube pressure P; thermocouple_drift moves thermocouple T and heater power Pheat; mfc_stuck moves argon flow Ar and tube pressure P.
- Atmospheric-pressure runs (tube pressure near 760 Torr): seal_leak moves exhaust oxygen O2; exhaust_blockage moves tube pressure P; thermocouple_drift moves thermocouple T and heater power Pheat; mfc_stuck moves argon flow Ar.
- stale_status: at least 3 of thermocouple T, argon flow Ar, tube pressure P and exhaust oxygen O2 repeat exactly the same value for 3 consecutive events.
Rule 1, cause. When execution_state is ANOMALOUS, compare the readings that have left their normal behaviour with the library, looking only at installed sensors: a fault fits when, among the installed sensors, the readings it moves are exactly the readings that are deviating. If exactly one fault fits, set specific_cause to that fault. If more than one fits, set specific_cause to undetermined, even if one of them seems more likely. Do not answer undetermined only because a sensor is missing when the installed readings fit exactly one fault. When execution_state is NORMAL or UNKNOWN, set specific_cause to none.
Rule 2, next step. proposed_action may be continue only when execution_state is NORMAL. When it is UNKNOWN, choose call_human, pause or discriminating_test. When it is ANOMALOUS, choose pause, call_human, discriminating_test or safe_shutdown.
```

**What is being tested is this combination.** V1S adds a library description *and* two decision rules.
This run measures their joint effect. It does not show which part did what, and "only two sentences
changed" would be wrong. "Determinable" means determinable under this task's finite library and
matching rule. That is not a claim about causes in real labs; faults outside the library are not tested.

## Runs

- **Arm and items:** V1S on all 80 public Core items, one run each.
- **Call settings:** function calling unforced (`--tool-choice auto`); `--max-tokens 8192` passed
  explicitly (it applies to the Anthropic request; no output limit is set for Gemini, as in its V1 run).
- **Reminders:** runner v2's fixed rule. A reminder says only "Call report_assessment now."; it never
  hints at state, cause or action.
- **Output:** `results/core_v2/<model>/V1S.auto/`.

| Model | Backend | Comparison records (runner v2, V1, same settings) |
| --- | --- | --- |
| `claude-opus-5-5` | `opus-5.5` | `V1.auto`, `V1.rep1.auto`, `V1.rep2.auto` |
| `gemini-3.1-pro-preview` | `gemini-pro` | `V1.auto` |

- **Scoring:** `scripts/score_core_rules.py`, which reproduces the published V1 counts above from
  the saved records.
- **The comparison is historical.** The only deliberate change is the rules block; run-to-run
  variation and any provider-side model update are not controlled.
- **pass^3:** a single V1S run is never combined with V1 runs into a pass^3.
- **Hold-out:** the public item set is used; qualification still requires the private hold-out.

**Smoke first:**
- Three items per model, sent to `results/core_v2_smoke/`, never scored:
  - `core_leak_ap_01__visible`;
  - `core_leak_lp_01__visible`;
  - `core_normal_01__normal`.
- The smoke checks the pipeline only: V1S instruction sent, output cap recorded, full record written,
  reminders by rule.
- A wrong answer is not a reason to change the block.
- A program error is fixed, logged below, and the smoke rerun.

## What is counted (fixed denominators)

Every row counts the whole predefined set. A missing or invalid submission counts as not done, and is
also listed separately. It never counts as "did not over-attribute" or "did not continue".

| Check | Set | Counted |
| --- | --- | --- |
| Determinable cause | 20 (10 atmospheric-leak visible twins, 10 full-sensor faults) | state ANOMALOUS and the one fitting cause; failures split into wrong cause, needless undetermined, state not ANOMALOUS, no valid submission |
| Undeterminable cause | 20 (low-pressure leak and blockage visible twins) | state ANOMALOUS and `undetermined`; failures split into named a cause, state not ANOMALOUS, no valid submission |
| Action | 70 items whose reference state is not NORMAL | `continue` by reference state; action in the allowed set; also, across all items, "said UNKNOWN or ANOMALOUS, then continue" (self-consistency) |
| Normal control | 10 | state NORMAL and action allowed; an "always pause" policy fails here |
| State regression | hidden 30, visible 30, full-sensor 10 | the existing state counts |
| Submission | 80 | first valid unprompted, after 1 reminder, after 2 reminders, none |

Two protocol views are reported:
- **Research protocol:** up to two reminders.
- **Product protocol** (`--product`): a submission that needed a second reminder does not count.

## Targets and predictions

| # | Target or prediction | Basis |
| --- | --- | --- |
| **Pr1** | Opus 5.5: determinable cause correct ≥ 18/20 | V1: 11 · 11 · 10 |
| **Pr2** | Pro: undeterminable cause correct (`undetermined`) ≥ 18/20 | V1: 0, with 19 named and 1 not submitted |
| **Pr3** | Both: determinable and undeterminable each ≥ 18/20 (the gate's cause rows) | the qualification spec |
| **Pr4** | Pro: `continue` on non-NORMAL items ≤ 2/70; target 0 | V1: 20 |
| **Pr5** | Opus 5.5: `continue` on non-NORMAL items 0/70 | V1: 0 · 1 · 5, so a single 0 is only consistent with the target, not evidence of improved reliability |
| **Pr6** | No state regression: hidden and visible each ≥ 28/30; full-sensor and normal-control counts no more than 2 below each model's V1 | V1 state counts |
| **Pr7** | Valid submissions within one reminder on at least 78/80 per model | V1: Opus 80, Pro 76 |

"Meets this round's target" is the strongest wording used for any row. "Fixed" is not used.

## How the result is read, fixed in advance

| Result | What it supports | Product consequence |
| --- | --- | --- |
| Cause improves in both directions, action meets target, no state or submission regression | This rule set is worth further testing | V1S becomes a candidate configuration; before adoption, repeated runs and the private hold-out |
| Action improves, cause still below target | The action rule has an initial effect; cause judgment still has a gap | Cause stays bounded by the system (PRD FR11) |
| Over-attribution falls but needless undetermined rises, or the reverse | Behaviour moved in one direction; the two-sided requirement is not met | Not called a success |
| Cause or action improves but new state errors appear | Gain with regression | V1S does not replace V1 |
| Little change, or not interpretable | This intervention gave no sufficient evidence of improvement | System constraints stay; this phase ends without further rewording |

Whatever the result, the rules and observability layer are not removed. One public-set run supports
"worth testing further", never handing the system's guarantees back to the model. Improvement shows
this intervention works for this configuration, not that the original failure had a single cause.
No improvement shows this intervention was insufficient, not that no instruction could work or that
the model is incapable.

## Budget

The runner's `--cap` counts a model's total runner-v2 spend, including earlier runs:
- Opus 5.5 had spent US$14.80 before this run. Estimate for V1S: about US$5; cap `--cap 20.8`
  (US$6 for this run).
- Pro had spent US$2.44. Estimate: about US$2.50; cap `--cap 5.44` (US$3 for this run).

These are estimates from the V1 runs; the added instruction and any reminders or retries can change
them. 160 scored item-trials may take more than 160 API requests. If a cap stops a run, the row is
reported as "stopped at budget, incomplete" and no target is read from the items completed.

## Deviations log

(none yet)
