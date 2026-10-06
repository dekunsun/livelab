# Pre-registration: GLM 5.3 Flash (open weights) on Core under runner v2, V1 and V1S

Status: **registered 2026-10-05, before any scored call.** It follows
[core_v2_rules_preregistration.md](core_v2_rules_preregistration.md) and replaces the unrun Kimi K3
registration ([core_v2_kimi_preregistration.md](core_v2_kimi_preregistration.md)).

## Why

Every Core result so far comes from a closed model. GLM 5.3 Flash is an open-weight model and the
one VISTA (arXiv 2610.02200) used to show its harness was reproducible. Running it here does two
things:
- it gives a check that anyone can repeat without a closed-vendor account;
- it asks whether the V1S result also holds for a smaller, open model. V1S stated the scoring rules,
  and Opus 5.5 and Gemini 3.1 Pro each met every cause and action target in one run.

A smaller model failing V1S would be harder to read than a frontier one doing so. Capability and
specification could both explain it. The predictions are set with that in mind.

## Runs

Only what the comparison needs: one run of each arm on all 80 public items, under runner v2. V1 is
the same-condition control and V1S the intervention.

| Arm | Output |
| --- | --- |
| V1 | `results/core_v2/z-ai/glm-5.3-flash/V1.auto/` |
| V1S | `results/core_v2/z-ai/glm-5.3-flash/V1S.auto/` |

**Call settings, same for both arms:**
- **Route:** `z-ai/glm-5.3-flash` through OpenRouter's OpenAI-compatible chat endpoint, pinned to
  one host, Z.AI (fp8), with no fallback and `require_parameters`.
  - Why pinned: an unscored Kimi K3 smoke showed that unpinned routing can send one item's requests
    to several hosts.
  - The host that served each response is in the saved record; any response not from Z.AI is a
    deviation.
- **Function calling:** unforced (`tool_choice: "auto"`), as for Opus 5.5 and Pro.
- **Reasoning:** the model's default.
- **Output cap:** none set.
- **Reminders:** by runner v2's fixed rule.

**Smoke:** three items on V1S, written to `results/core_v2_smoke/`, never scored. Pipeline checks,
including that every response came from Z.AI.

**Scoring:** `scripts/score_core_rules.py`, on the same fixed denominators.

## Predictions

| # | Prediction |
| --- | --- |
| **Pg1** | V1S does not regress the state against V1: hidden abstentions and visible faults kept each within 2 items of V1 |
| **Pg2** | V1S improves the cause rows over V1 by at least 3 items each, where V1 leaves room (below 18/20) |
| **Pg3** | V1S: `continue` on non-NORMAL items at most 2/70 |
| **Pg4** | V1S: valid submissions without a reminder ≥ 72/80 |

No absolute target is set for the cause rows. The 18/20 gate rows are reported, but a smaller model
missing them does not by itself separate capability from specification.

**How the result is read, fixed in advance:**

| Result | Reading |
| --- | --- |
| Pg2 and Pg3 hold | Stating the rules moved this open model in the same direction as the two closed ones |
| No movement, with the state no worse | For this configuration, stating the rules was not enough; the failure breakdown says where it stopped |
| Pg4 fails | Rows on fixed denominators; missing submissions count as wrong and are listed |

One run per arm: no pass^3 and no qualification. Differences under 3 items are not interpreted (this
study's reading rule, not significance).

## Budget

- **Price:** Z.AI through OpenRouter lists US$0.15 per million input tokens and US$0.50 per million
  output tokens.
- **Estimate:** under US$1 for 160 items.
- **Cap:** `--cap 2`.

## Deviations log

(none yet)
