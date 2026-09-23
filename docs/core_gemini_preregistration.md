# Pre-registration: should a lab assistant's conversation and diagnosis be one Live model, or two?

Status: **registered 2026-09-22, before any Core item below ran.**

## Why

On LiveLab Core, `gemini-3.8-live` is the weakest judge: 10 of 30 pairs both right under V1, and 17
of 30 visible faults caught with nothing added, where Opus 5, Astra and Opus 5.5 caught all 30. A
lab assistant built on Gemini has to choose an architecture: **one Live model that both talks and
diagnoses**, or **Live for the conversation and another model for the diagnosis**. That choice turns
on a question the leaderboard cannot answer: is the weakness the Live mode, or the model generation?
And if the work is split, does the hand-off between the two lose what the judge needs?

## Arms

All on Core's 80 frozen items, same item text, same system instruction, same function schema, same
scorer as every Core row.

| Arm | Model | What it answers |
| --- | --- | --- |
| **A** | `gemini-3.8-live` (existing row) | baseline |
| **B** | `gemini-3.8-flash`, request/response, V0 / V1 / B1 (240 calls) | the cost of the Live mode: same generation, standard product |
| **C** | `gemini-3.1-pro-preview`, same (240 calls) | the best Gemini judge available |
| **D** | Live narrates, Flash judges (80 items × 2 calls, V1 only) | the cost of the hand-off: Live sees the telemetry and describes it in at most 80 words without a verdict; Flash sees **only that description plus the system's V1 sentence** |

**Parity with the Live row.** B and C run with function calling **unforced** (`mode: AUTO`), as Live
does: the instruction asks for the call, and a turn that ends without it gets up to two "Call
<tool> now." reminders, as `run_single_turn` gives Live. Opus and Astra ran forced; B and C are read
against Live, not against them (the forced-vs-unforced question is its own
[registration](core_toolchoice_preregistration.md)). Each model at its default reasoning setting.
What cannot be equalised: Live answers in an audio session with a transcript, B and C in text; the
scorer reads only the function call in both.

**Caveat on "same generation".** Whether `gemini-3.8-live` and `gemini-3.8-flash` share weights is
not public. B measures the Live product against the standard product of the same generation, which
is the choice a builder actually has.

## Predictions (registered)

| # | Prediction | Basis |
| --- | --- | --- |
| **Pg1** | Flash (B) gets **at least 5 more** pairs both right under V1 than Live (≥ 15/30) | Live is optimised for conversation latency; the standard models tested hold far more pairs |
| **Pg2** | Flash (B) catches **at least 25 of 30** visible faults under V0 (Live: 17) | as Pg1 |
| **Pg3** | Pro (C) gets **at least as many** pairs both right under V1 as Flash (B) | larger model |
| **Pg4** | V0 hidden abstention ≤ 3/30 for B and C | 0/30 for every model so far |
| **Pg5** | The hand-off (D) keeps **at least 5 fewer** visible faults than Flash on raw telemetry (B, V1) | the specialist study lost accuracy when a verdict crossed a hand-off; a summary is lossier than the readings |

## How results will be read

| Outcome | Reading for the architecture |
| --- | --- |
| Pg1 holds | The Live mode costs judgment. **Split**: Live talks, a standard model judges |
| Pg1 fails, Pg3 holds with C ≥ 15 | The generation's Flash is weak here, Pro is not: split, with Pro as the judge |
| Pg1 and Pg3 fail (B, C ≈ Live) | The weakness is the family on this task, not the mode; splitting within Gemini does not fix it |
| Pg5 holds | Split, but **route the telemetry to the judge directly**; never let the voice layer's summary be the judge's evidence |
| Pg5 fails (D ≈ B) | Live's summaries preserve what the judge needs; a summary hand-off is acceptable |

Differences under 3 items are not interpreted; if Pg1 or Pg5 is decided by a margin inside Opus 5's
observed spread (4–5 items), the arm is rerun twice under the stability protocol before it is read.
Coverage below 90% is not read.

## Budget

Gemini paid tier, read from the vendor's pricing page (2026-09): Flash $0.75 / $3.75 and Pro $2 / $12 per
million input / output tokens, output including thinking. Estimated B ≈ US$1.5, C ≈ US$5–8,
D ≈ US$1–2 (Live's own usage is not reported). Billed to the owner's Google account. Caps in the
runner: US$5 (Flash), US$12 (Pro).

## Deviations log

1. **Arm C was collected over two days (2026-09-22 and 2026-09-23).** The paid tier caps
   `gemini-3.1-pro-preview` at 250 requests a day. The run stopped at about 64 of 80 items; 47 calls
   failed on the cap and were not saved. The rest was collected after the reset, skipping every item
   already saved, so no answer was asked twice. Coverage is 80 of 80 in every arm.
