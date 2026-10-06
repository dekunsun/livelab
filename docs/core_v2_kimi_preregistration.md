# Pre-registration: Kimi K3 (open weights) on Core under runner v2, V1 and V1S

Status: **registered 2026-10-05, before any scored call.** It follows
[core_v2_rules_preregistration.md](core_v2_rules_preregistration.md).

## Why

Every Core result so far comes from a closed model. Kimi K3 (Moonshot AI, weights released
2026-07-27 under the Kimi K3 License) adds two things:
- **reproducibility**: anyone can run the same check without a vendor account;
- **a test of whether the V1S result holds beyond the two closed models it was seen on** (Opus 5.5
  and Gemini 3.1 Pro). V1S stated the scoring rules, and both models met every cause and action
  target in one run.

## Runs

Only what the comparison needs: one run of each arm on all 80 public items, under runner v2. V1 is
the same-condition control and V1S the intervention.

| Arm | Output |
| --- | --- |
| V1 | `results/core_v2/moonshotai/kimi-k3/V1.auto/` |
| V1S | `results/core_v2/moonshotai/kimi-k3/V1S.auto/` |

**Call settings, same for both arms:**
- **Route:** `moonshotai/kimi-k3` through OpenRouter's OpenAI-compatible chat endpoint, with
  `provider.require_parameters` set so that only endpoints supporting tools and tool_choice serve
  it. The endpoint that answered is in each saved response.
- **Function calling:** unforced (`tool_choice: "auto"`), as for Opus 5.5 and Pro.
- **Reasoning:** the model's default.
- **Output cap:** none set.
- **Reminders:** by runner v2's fixed rule.

**Smoke:** three items on V1S, written to `results/core_v2_smoke/`, never scored. Pipeline checks
only.

**Scoring:** `scripts/score_core_rules.py`, on the same fixed denominators.

## Predictions

| # | Prediction |
| --- | --- |
| **Pk1** | V1S does not regress the state against V1: hidden abstentions and visible faults kept each within 2 items of V1 |
| **Pk2** | V1S, determinable cause right ≥ 18/20 and undeterminable cause `undetermined` ≥ 18/20 |
| **Pk3** | V1S, `continue` on non-NORMAL items 0/70, and action in the allowed set ≥ 68/70 |
| **Pk4** | V1S, valid submissions without a reminder ≥ 76/80 (an open model through a router may follow the function protocol less reliably) |

No prediction is made for V1. It is the control, and nothing is known of this model on Core.

**How the result is read, fixed in advance:**

| Result | Reading |
| --- | --- |
| Pk2 and Pk3 hold | The specification account extends to an open-weight model, in one run |
| They fail, with the V1S state no worse than V1 | Stating the rules is not enough for this configuration; reported as found, with the failure breakdown |
| Pk4 fails | The cause and action rows are read on fixed denominators, missing submissions count as wrong, and the protocol failures are listed |

One run per arm: no pass^3 and no qualification. Differences under 3 items are not interpreted (this
study's reading rule, not significance).

## Budget

- **Price:** OpenRouter lists US$0.95 per million input tokens and US$14 per million output tokens,
  with reasoning counted as output.
- **Estimate:** at about 3,000 input and up to 3,000 output tokens an item, about US$3–8 for 160
  items.
- **Cap:** `--cap 10`, counting this model's runner-v2 spend, which is US$0 before this run.
- **If the cap stops a run:** it is reported as incomplete, and no prediction is read from it.

## Deviations log

(none yet)
