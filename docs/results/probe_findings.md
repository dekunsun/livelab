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

## Extended Thinking, stage 1 (partial)

Gemini 3.8 Live Extended Thinking at `thinkingLevel: HIGH`, same U items, same frozen wording,
2026-09-19. Only **B0 is readable**: an API-side failure took B1 to 8 of 14 answered and B2 to 3 of
14, so neither is scored (pre-registration, deviation 7, which also records how the failure was
identified).

| Measure | Standard | Extended Thinking (B0) |
| --- | --- | --- |
| Answered `UNKNOWN` where only `UNKNOWN` is supported | 0/14 | **0/13** |
| What it answered instead | 14 `NORMAL` | 11 `NORMAL`, 2 `ANOMALOUS` |
| Named the evidence it was missing | — | **13 of 13** |

More thinking did not produce a single abstention. What it did change is the quality of
`missing_evidence`: every answered item named something specific, and in the blockage episodes it
named the test that would settle the question, *"exhaust O2 concentration measurement or
rate-of-rise test to distinguish between a seal leak and an exhaust blockage"*, and then reported
the run as `NORMAL` anyway.

That is the same split the standard model showed in B1, reached from the other side: the model
knows what it cannot see, says so in a field that is not the verdict, and leaves the verdict
unchanged. Thinking longer improved the description of the gap without changing what was concluded
from it.

**Not claimed:** any comparison of abstention *rates* between the two models (13 items, one run
each), and anything at all about B1, B2, B3 or P1 under Extended Thinking.
