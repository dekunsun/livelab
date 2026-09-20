# Pre-registration: is observability set by the model, or by the sampling interval?

Status: **registered 2026-09-20, before any transient episode is written or any run is made.**
Changes after this date are logged at the end, with reasons, and never made after results are seen
unless recorded as deviations.

## Why

The project's original claim is that **physical observability exceeds software observability** —
that a lab agent needs eyes because telemetry misses things. The benchmark as built cannot test it:
every replay delivers one image, after the run ends, and all five fault types leave a telemetry
signature ([README](../README.md)).

But the part of that claim that matters is not about cameras. It is about **evidence that exists
only briefly**. An arc, a droplet detaching, a boat slipping, an overflow: seconds. The benchmark
delivers an observation every 120 simulated seconds, so an event shorter than that interval is not
hard to judge — it is **absent from the evidence**. That can be tested today, with the simulator
already written and no imagery at all.

It also reframes the finding this project already has. Where the sensor-removal cascade varies
**which channels exist**, this varies **how often they are read**. Both produce the same thing: a
supported answer that is weaker than the model's confidence.

## The question

**Q: When a fault is shorter than the sampling interval, what is the supported answer, and what
does the model say instead?**

The registered position, which the study can refute: at 120 s a model that reports `NORMAL`
through a 20-second excursion **is not wrong**. The delivered evidence supports `NORMAL`. The
failure belongs to the architecture, and no prompt can repair it.

## Episodes

New **transient** fault types, added to the existing simulator, each with an excursion of duration
`d` and no lasting trace: a brief exhaust restriction that clears itself, a momentary MFC dropout,
a short pressure spike from a valve actuation. Their shapes are author-constructed, as the existing
faults' are, and the episode cards say so.

`d` is chosen per episode from **{20 s, 60 s, 240 s}**, so that the same fault falls into a
different observability class at each cadence.

## Cadences

Each episode is delivered at **120 s** (the benchmark's own interval), **30 s** and **5 s**, over
the **same 20-minute window** around the excursion. The window is identical across cadences, so
what differs is only how often the instrument was read.

| Cadence | Events in the window |
| --- | --- |
| 120 s | 10 |
| 30 s | 40 |
| 5 s | 240 |

As in the probe study, each item is a single turn carrying every delivered event in the window and
asking for one `report_assessment`. That keeps cost linear in the number of events and reuses a
method already validated.

## Truth: one new rule, and it does not touch the benchmark

Most of this needs nothing new. Truth is computed by the pre-registered z-score rules over the
**delivered** samples, under "same evidence, same answer", so changing the cadence changes what is
supported by itself: an excursion no sample falls into is simply not there, and one that meets the
consecutive-sample threshold is `ANOMALOUS`.

**The glimpsed class is the exception, and this registration originally got it wrong.** The
benchmark's rule maps a single deviating sample to `NORMAL`, not to `UNKNOWN` — one point does not
meet the consecutive-sample threshold, so nothing is supported beyond "normal so far". Calling it
`UNKNOWN` is a **new rule**, stated here before any run:

> A delivered sample that deviates by |z| ≥ 3.5 with no second consecutive sample to confirm it
> supports `UNKNOWN`: the evidence contains something unexplained and nothing that can resolve it.

It applies **only to this study**, and the benchmark's own ground truth and published results are
untouched (see deviation 1). Three classes follow,
and each episode is assigned to its class by script, never by hand:

| Class | What the delivered samples contain | Supported answer |
| --- | --- | --- |
| **Missed** | no sample falls inside the excursion | `NORMAL` |
| **Glimpsed** | exactly one sample falls inside it | `UNKNOWN` — one point cannot separate a transient from noise |
| **Resolved** | the rule's consecutive-sample threshold is met | `ANOMALOUS` |

The **glimpsed** class is where this study meets the previous one. The evidence contains a single
odd reading and nothing that can explain it, so the only supported answer is "I cannot tell yet" —
reached this time through timing rather than through a missing sensor.

## Measures

- **Detection by cadence** — resolved events called `ANOMALOUS`.
- **False alert by cadence** — missed events called `ANOMALOUS`. Finer sampling delivers more
  noise, so this is the cost side of sampling faster.
- **Abstention on glimpsed events** — the share answered `UNKNOWN`.
- **Cost per run by cadence**, measured, for both architectures: repeated calls carrying the window
  versus a streaming Live session.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pr1** | Detection rises with sampling rate: at 120 s, detection of 20 s excursions is ≤ 10%; at 5 s it is ≥ 80% |
| **Pr2** | On glimpsed events, abstention is ≤ 10% — the models commit, as they have in every previous study |
| **Pr3** | False alerts at 5 s are no more than twice those at 120 s |
| **Pr4** | Token cost per window grows faster than linearly in the event count, because each item carries every event delivered so far |

Pr2 is the one that ties this study to the others. If it fails — if models abstain when the
evidence is a single unexplained point — then the refusal to abstain is specific to *missing
sensors* rather than *insufficient evidence*, which would be a more interesting result than the
one I expect.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Detection rises with cadence, as predicted | Observability is a property of the delivery architecture. "How often do you look" belongs beside "what sensors do you have" in any agent design |
| Detection does not rise | The excursions are visible in aggregate statistics even when unsampled, and the episode design is wrong — reported as such |
| Abstention low on glimpsed events | The finding generalizes from missing channels to insufficient sampling: the model's confidence tracks neither |
| False alerts rise sharply at 5 s | Sampling faster is not free, and the product recommendation must carry that cost |

## Models

Gemini 3.8 Live on the free tier, and **one** request/response model already characterized
(Claude Opus 5), to check that a cadence effect is not a quirk of one family. Both under the frozen
v4 wording. B2's added definition is **not** used: this study measures the default contract.

## Budget

12 episodes × 3 cadences × 2 models = **72 calls**. The 5 s items carry about 240 events, so
roughly 11k tokens each; the whole study is a few hundred thousand tokens. **Cap: US$10.**

## What this cannot show

- **Nothing about cameras.** It tests the consequence of sampling, not the value of vision. The
  optical version needs real in-run footage of camera-only faults, which the project does not have,
  and generated imagery is not allowed.
- **The excursion shapes are author-constructed**, as all telemetry in this project is. Real
  transients may be longer, shorter or differently shaped, and the fault *types* carry citations
  while the curves do not.
- **Not a claim about real-time systems.** Delivering every 5 s in a replay is not a streaming
  architecture; the cost comparison estimates what one would pay, it does not build one.
- **The Live API's video path is not measured by this**, and its pricing is per minute rather than
  per accumulated token, so a cost result for text events says nothing about continuous vision.

## Deviations log

1. **Results, for the record (2026-09-20).** Pr2 and Pr3 hold; **Pr1 and Pr4 do not**. Detection at
   5 s reached 67% (Gemini) and 50% (Opus 5) against a registered bar of 80%, and prompt tokens per
   event *fell* with event count (273 → 139 → 101) rather than rising. Pr4 was wrong by my own
   construction: the items are single turns precisely so that context does not accumulate, and I
   predicted the accumulating-context curve anyway. Both failures are in the same direction as the
   cross-model study's: I expected effects to be stronger than they are.
   [Results](results/undersampling_results.md).
2. **The glimpsed rule is new, and is scoped to this study (2026-09-20, found while implementing,
   before any episode was written).** The text above first claimed the existing truth already
   produced `UNKNOWN` for a single unconfirmed excursion. It does not: the benchmark's rule requires
   two consecutive deviating samples and otherwise reports `NORMAL`. The rule is therefore stated
   explicitly above and implemented in a separate module, so that
   `evidence_supported_answers` — and every result already published from it — is unchanged. Had
   the rule been applied globally it would have silently rewritten the ground truth of the
   1,986-event finding.
