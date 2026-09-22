# Pre-registration: is Opus 5.5's Core result the model, or the unforced call?

Status: **registered 2026-09-22, before any item below ran.**

## Why

Opus 5.5 is the first model to score 30/30 on Core's V1 headline counts (three runs, zero spread).
It is also the only model run with `tool_choice: auto`: its API refuses forced calls
([Core deviation 1](core_preregistration.md)). Every other model was forced to call the function
directly, which on this API leaves no room to write before answering. Opus 5.5 was free to, and its
median output was about twice Opus 5's (913 against 474 tokens), consistent with reasoning written
before the call. So the improvement may be the model, or it may be the freedom to think first.

The reverse control (Opus 5.5 forced) is impossible. The available one is **Opus 5 unforced**.

## Arm

Core's V1 arm, all 80 items, `claude-opus-5`, `tool_choice: auto` (`scripts/run_core.py
--tool-choice auto`). Everything else identical to the forced V1 runs. Text written before the call
is now saved with each answer. One run; an unanswered item (text but no call) is retried like any
other and counts against coverage.

## Predictions (registered)

| # | Prediction | Basis |
| --- | --- | --- |
| **Pt1** | Opus 5 unforced keeps **at most 23 of 30** visible faults (inside its forced range 19–23) | Opus 5.5 also stays at 0/30 when left to infer the gap (V0), so its gain is not general reasoning headroom |
| **Pt2** | Hidden abstention stays **at least 21 of 30** | the gap is still stated |
| **Pt3** | Needless abstention ≤ 2 of 20 | as V1 |

## How results will be read

| Visible faults kept | Reading |
| --- | --- |
| **≤ 23** (Pt1 holds) | The unforced call does not explain the gain: Opus 5.5's result is the model |
| **≥ 27** | The unforced call explains most of it. Headline changes to "letting the model write before it calls fixes this"; Opus 5.5's row is reported as confounded |
| **24–26** | Ambiguous against Opus 5's own spread: two more unforced runs, same rule on the three-run range |

Hidden abstention below 21 would mean the unforced call trades abstention for detection; reported
as such. Coverage below 90% is not read.

## Budget

80 calls, about US$3 (forced V1 cost US$2.65; unforced output may be longer). The runner's cap is
cumulative across Opus 5's Core runs (~US$16 so far), so it is set at US$25.

## Deviations log

None yet.
