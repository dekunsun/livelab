# Cross-model results: who says "I cannot tell"?

Design, predictions and reading rules registered before any of this ran:
[crossmodel_preregistration.md](../crossmodel_preregistration.md). Collected 2026-09-20. One run
per item; 38 items per variant (U = 14, N = 15, A = 9); the same item text, instruction and answer
schema for every model, with the request each one received committed at
`results/probes/<model>/request_sample.json`.

## Abstention on U — the items where only `UNKNOWN` is supported

| Model | B0 frozen wording | B1 verify first | B2 explicit definition | B3 renamed enum |
| --- | --- | --- | --- | --- |
| Gemini 3.8 Live | **0/14** | 0/14 | 0/14 | 0/14 |
| Gemini 3.8 Live Extended Thinking | **0/13** | 0/14 | 0/14 | not run |
| Claude Opus 5 | **0/14** | 0/14 | **13/14** | not run |
| GPT-6 Astra | **0/14** | **10/14** | **14/14** | not run |

**Under the benchmark's own contract, every model answers 0 of 55.** That is the finding the
benchmark reports, and it now holds across three families.

**What differs is whether it can be fixed by asking differently.** One added sentence — *"NORMAL
means the installed sensors positively show that the process is executing as expected. If something
that matters for the current stage cannot be checked with the installed sensors, report UNKNOWN."*
— takes Opus 5 to 93% and Astra to 100%, and moves Gemini by nothing, in either model, at any
thinking level.

## The guards

| Model | Variant | Over-abstention on N | Detection on A |
| --- | --- | --- | --- |
| Gemini 3.8 Live | B0 | 0/15 | 4/9 |
| Claude Opus 5 | B0 | 0/15 | 8/9 |
| Claude Opus 5 | B2 | 2/15 | 6/9 |
| GPT-6 Astra | B0 | 0/15 | 8/9 |
| GPT-6 Astra | B1 | 2/15 | 8/9 |
| GPT-6 Astra | B2 | **4/15** | 8/9 |

Abstention is only worth having if it is selective. Astra under B2 abstains on every U item and on
4 of 15 N items, which is past the registered 20% guard: it reads as a model that has become more
willing to abstain, not one that has become calibrated. Opus 5 under B2 stays inside the guard
(2/15) but loses two of nine detections. **The sentence is not free in either model** — and with
these sample sizes a two-item difference is at the edge of what the registration allows to be
interpreted.

## What B1 shows, and it is the sharpest thing here

B1 asks for verifiability in its own function call, then for the verdict.

| Model | Said atmosphere `cannot_verify` | Of those, committed to a verdict anyway |
| --- | --- | --- |
| Gemini 3.8 Live | 12/14 | **12/12** |
| Gemini 3.8 Live Extended Thinking | 12/14 | **12/12** |
| Claude Opus 5 | 12/14 | **12/12** |
| GPT-6 Astra | 12/14 | **2/12** |

**All four models perceive the same thing, on exactly the same 12 items.** What separates them is
whether that perception reaches the verdict. Three carry it nowhere; one carries it through ten
times out of twelve.

This is the project's central claim stated as a measurement: the gap is not in what the model
notices, it is in what the model's answer is allowed to depend on.

## The registered predictions

| # | Prediction | Observed | Met |
| --- | --- | --- | --- |
| **Pr1** | every model's B0 abstention on U ≤ 10% | 0% in all four | **yes** |
| **Pr2** | some non-Gemini model > 50% on U under B2, with N ≤ 20% | Opus 5: 93% U, 13% N | **yes** |
| **Pr3** | every model that runs B1 conflates on ≥ 40% of U | Astra: 2/12 = 17% | **no** |
| **Pr4** | no model's over-abstention on N exceeds 20% under B0 | 0/15 in all | **yes** |

Pr2 was registered as the prediction I expected to lose, with the note that registering it was the
cheapest way to be shown wrong. It was met. Pr3, which I expected to hold everywhere, is the one
that broke. **Both mistakes point the same way: I assumed the Gemini behaviour was a fact about
models, and it is a fact about Gemini.**

## What this does not show

- **Not a capability ranking.** Astra abstains more; that is not the same as judging better. On A
  items Astra and Opus 5 both detect 8 of 9 while Gemini detects 4, but the probes were never
  designed to measure detection.
- **One run per item, 14 items per cell.** Differences under three items are not interpreted.
- **The wording was tuned against Gemini** over four versions. A model that reads it differently is
  partly a finding about the wording.
- **Modality differs by construction.** Gemini answered in audio-output Live sessions, the others
  as text through request/response APIs. The evidence text was identical.

## Cost

| Model | Calls | Input | Output | Spend |
| --- | --- | --- | --- | --- |
| `claude-opus-5` | 114 | 480,444 | 53,314 | **$3.74** |
| `gpt-6-astra` | 114 | 378,014 | 33,571 (2,851 reasoning) | **$5.46** |

**$9.20 against the registered $20 cap.** The Gemini arms were collected on the free tier.
