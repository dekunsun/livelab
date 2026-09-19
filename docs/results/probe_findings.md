# UNKNOWN probe: findings

Interpretation of [probe_results.md](probe_results.md), which `scripts/score_probes.py` generates.
The design, predictions and reading rules were registered before any probe ran
([probe_preregistration.md](../probe_preregistration.md)). One run per item; 14 U items,
15 N items, 9 A items; Gemini 3.8 Live on the free tier, 2026-09-19.

## What was found

| Explanation | Registered test | Result | Reading |
| --- | --- | --- | --- |
| **K** knowledge | P1 detectability, balanced accuracy ≥ 80% | 81% (41/48); distinguishability 9/12 | The model mostly knows which sensors can see which faults. **K is not the main cause.** |
| **R** reporting | B1: says `cannot_verify` on ≥ half of U, conflation ≥ 40% | `cannot_verify` 12/14; of those, **12/12 then reported `NORMAL`** | **Supported.** It states that atmosphere integrity cannot be verified, then reports that execution is normal. |
| **C** convention | B2: explicit definition raises abstention to ≥ 50% | **0/14**; N 0/15, A 4/9 | **Not supported.** The behavior survives an explicit instruction to answer UNKNOWN in exactly this situation. |
| **O** option bias | B3: renamed/reordered enum changes abstention by ≥ 20 points | 0/14 vs 0/14 | **Not supported.** Neither position nor name matters. |

Per the registered reading rules, the pattern "B2 abstention still ≤ 10%" is **the strongest
evidence that this is a model-level tendency**. Combined with B1, the tendency is specific: the
model can recognize and state that it cannot verify something, but it does not let that
recognition change its verdict, even when told to.

## What this does not show

- **One model, one configuration.** Only Gemini 3.8 Live, telemetry-only content, single-turn
  prefixes (events 0–24 at once rather than streamed), and one run per item. Other models and the
  Extended Thinking variant are untested.
- **B2 tests one wording of the instruction.** A different placement or phrasing could behave
  differently; the claim is that the stated definition was not enough.
- **Detection on A was 4/9 in B0**, consistent with the telemetry-only arm of the benchmark: the
  probes were not designed to test detection.

## What it implies

- **Abstention cannot be delegated to the verdict field.** A separate verifiability check,
  computed by the system or asked as its own question, carries information that the model's own
  verdict drops. In B1 the separate question was answered correctly for 91% of conditions
  (104/114).
- **For a lab product:** show "cannot verify" as a system state beside the agent's verdict, and do
  not let a `NORMAL` verdict stand when a stage's required sensors are missing.
