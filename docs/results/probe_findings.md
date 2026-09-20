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

## Extended Thinking, stage 1

Gemini 3.8 Live Extended Thinking at `thinkingLevel: HIGH`, the same 14 U items under B0, B1 and
B2, the same frozen wording. Collected 2026-09-19 (B0) and 2026-09-20 (B1, B2). One item of B0 has
no answer and is excluded; the rest is complete.

| Variant | Abstention on U | Standard model |
| --- | --- | --- |
| B0 baseline | **0 / 13** | 0 / 14 |
| B1 verify, then report | **0 / 14** | 0 / 14 |
| B2 explicit definition | **0 / 14** | 0 / 14 |

**Across both models: 97 answers on items where only `UNKNOWN` is supported, and 0 abstentions.**
The standard model answered `NORMAL` every time (56 of 56). Extended Thinking answered `NORMAL` 35
times and `ANOMALOUS` 6 times: thinking longer moved some verdicts from one certainty to another,
never to "I cannot tell".

B1 asks for verifiability first, in its own function call, and then for the verdict:

| It said atmosphere was | Its verdict | n |
| --- | --- | --- |
| **cannot_verify** | NORMAL | **10** |
| **cannot_verify** | ANOMALOUS | 2 |
| verified | NORMAL | 2 |

Its verifiability answers are good: 95% correct against the registered truth, and it marked
atmosphere `cannot_verify` on 12 of 14, the same as the standard model. **Twelve times it stated
that it could not verify the condition, and twelve times it then committed to a verdict anyway.**

Its `missing_evidence` is more specific than the standard model's, naming in every answered B0
item what it would need, including the test that would settle the question: *"exhaust O2
concentration measurement or rate-of-rise test to distinguish between a seal leak and an exhaust
blockage."* Then it reported the run as `NORMAL`.

**Stage 2 is not run.** The registration makes the N and A controls conditional on some abstention
appearing on U. None did, so there is nothing to check for reflexiveness.

**What this does not show.** One run per item, 14 items per variant, one thinking level (HIGH).
B3 and P1 were not run for Extended Thinking, as registered. Nothing here compares the two models'
*accuracy*; the comparison is only about whether either ever abstains.

## A note on where this data came from

B1 and B2 could not be collected on the free tier at all: the model's function-call path failed
silently for hours (pre-registration, deviation 7). They were collected in about twenty minutes
once billing was enabled, for roughly $0.20 of tokens. The free-tier attempt cost a night and
produced nothing, and the first version of the harness would have recorded that night as
**"the model declined to answer"** — which, scored the old way, would have read as evidence for
the very conclusion this study reports.
