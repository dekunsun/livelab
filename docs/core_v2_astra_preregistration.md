# Pre-registration: GPT-6 Astra on Core under runner v2, V1 and V1S

Status: **registered 2026-10-05, before any call below is made.** It follows
[core_runner_v2.md](core_runner_v2.md) and the V1S design in
[core_v2_rules_preregistration.md](core_v2_rules_preregistration.md).

## Why

GPT-6 Astra has been measured only under runner v1. There, across three runs, it:
- abstained on every hidden twin (30 · 30 · 30);
- kept only 12 · 14 · 14 of 30 visible faults;
- never ruled after saying it could not verify (0 of 20).

Under runner v2, only Claude Opus 5.5 and Gemini 3.1 Pro have been run with the scoring rules stated
(V1S). Both met every cause and action target in one run. That result does not cover Astra.

Astra's main V1 failure is in the state: it drops visible faults. That is not what V1S addresses,
because V1S states the cause and action rules. This run therefore asks two things:
- whether stating the rules also helps Astra's cause and action answers;
- whether it leaves the state failure where it was.

**The second is the more informative result.** If the state failure stays, the claim that V1S fixes
specification gaps for cause and action, and not model behaviour on the state, holds across a third
vendor.

## Runs

Only what the comparison needs: one run of each arm, on all 80 public items, under runner v2.
- **V1** is the same-condition control. Its runner-v1 records differ in runner and so are not used
  for this comparison.
- **V1S** is the intervention.

| Arm | Output |
| --- | --- |
| V1 | `results/core_v2/gpt-6-astra/V1/` |
| V1S | `results/core_v2/gpt-6-astra/V1S/` |

**Call settings, same for both arms:**
- The OpenAI Responses endpoint with `tool_choice: "required"`. The runner's `--tool-choice` flag
  does not change this for that endpoint, and runner v1 used the same setting.
- With one tool in V1 and V1S, this is a forced call. It differs from the unforced Opus 5.5 and Pro
  runs, so cross-model comparisons are reported as configurations.
- Reasoning at the model's default.
- No output cap is set: the cap flag applies to Anthropic.
- Reminders by runner v2's fixed rule.

**Smoke:** three items on V1S, written to `results/core_v2_smoke/`, never scored. Pipeline checks only.

**Scoring:** `scripts/score_core_rules.py`, with the same fixed denominators as the V1S registration.

## Predictions

| # | Prediction | Basis |
| --- | --- | --- |
| **Pa1** | V1: hidden abstentions ≥ 28/30; visible faults kept between 10 and 16 of 30 | runner v1: 30 · 30 · 30 and 12 · 14 · 14 |
| **Pa2** | V1S: visible faults kept within 4 of the V1 count; V1S does not fix the state failure | V1S states cause and action rules, not when to abstain |
| **Pa3** | V1S: `continue` on non-NORMAL items 0/70 and action in the allowed set ≥ 68/70 | the action rule is stated |
| **Pa4** | V1S: among determinable items Astra calls ANOMALOUS, the cause is right on all but at most 2 | the cause rule is stated; the fixed-denominator count is capped by the state failure and is reported as well |
| **Pa5** | V1S: undeterminable items with a named cause ≤ 2/20 | the cause rule is stated |

**Readings, fixed in advance:**
- **Pa2 and Pa3–Pa5 all hold:** stating the rules fixes the specification gaps but not the state
  failure, for a third vendor.
- **Pa2 fails because visible retention rises by more than 4:** the rules also changed the state
  behaviour. This is reported as found: one run, not a mechanism.
- **Pa3–Pa5 fail:** the specification account does not extend to this configuration.

One run per arm, so no pass^3 and no qualification. Differences under 3 items are not interpreted
(this study's reading rule, not significance).

## Budget

- **Runner v1 cost:** US$11.88 for 240 calls, about US$0.05 a call.
- **Runner v2 cost so far:** Opus 5.5 cost about 1.8 times more per call under runner v2 (an extra
  closing request and longer answers).
- **Estimate for this run:** 160 calls, US$12–14.
- **Cap:** `--cap 18`, counting this model's runner-v2 spend, which is US$0 before this run.
- **If the cap stops a run:** the run is reported as "stopped at budget, incomplete", and no
  prediction is read from it.

## Deviations log

- 2026-10-06: **stopped at budget, incomplete.** The cap stopped the run at US$18.04 after 155 of 160
  items (about US$0.12 a call, above the US$0.08–0.09 the estimate assumed). Not run: V1
  `core_full_09`, `core_full_10`; V1S `core_full_08`, `core_full_09`, `core_full_10`. Every record
  written is a valid submission. By the budget rule above, no prediction is read from this run.
  The 60 twin items and the 20 undeterminable items are complete in both arms; the missing
  full-sensor items fall in the determinable, non-NORMAL, full-detection and submission rows.
  Descriptive counts only (`scripts/score_core_rules.py --model gpt-6-astra --runs V1 V1S`):

  | Row | V1 | V1S |
  | --- | --- | --- |
  | Hidden abstains, of 30 | 30 | 30 |
  | Visible faults kept, of 30 | 14 | 30 |
  | Undeterminable: `undetermined`, of 20 | 11 | 20 |
  | Undeterminable: named a cause, of 20 | 0 | 0 |
  | Determinable: cause right, of 20 (items run) | 1 (18) | 17 (17) |
  | `continue` on non-NORMAL, of 70 (items run) | 0 (68) | 0 (67) |
  | Normal controls right, of 10 | 10 | 10 |

  Finishing the five items needs about US$0.60 beyond the cap and the owner's approval; if it is
  run, it is logged here as a second deviation before any prediction is read.
