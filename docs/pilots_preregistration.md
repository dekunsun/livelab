# Pre-registration: two data-usability pilots

Status: **registered 2026-09-21, before either dataset was opened to choose items.** Changes after
this date are logged at the end.

These are pilots. Their job is to decide whether two public datasets can carry the next study, and
to find where a model fails when they can. They make no capability claim about any model.

## Where this sits

The first phase of this project measured what models do when the evidence cannot support a
verdict. It has not answered the question it started from:

> **Under what conditions of observability, time and interaction can a native multimodal observer
> support an experimental decision earlier, more accurately or more cheaply than telemetry alone,
> or than a specialist vision model feeding a language model?**

Three things have to be kept apart, because this project has already confused them once:

| Question | What truth it needs |
| --- | --- |
| Can the setting be read back from the picture? | The parameter log |
| Is the physical state visibly wrong? | An annotation of the state itself |
| Was that state caused by the setting? | Evidence that rules out the other causes |

Both pilots are about the **second** question: is a state visible, and does a model use it
together with what the protocol requires?

## What has already been seen

Registration has to say what was looked at before it was written.

- **CAXTON print 0**: its whole log, and contact sheets of frames 21–22, 340–385, 503–634,
  805–936, 1264–1286, 1416–1547 and 1568–1699, seen by the author and sent to the project owner.
  None of these frames is eligible for pilot 2.
- **CAXTON print 190**: frame 1 and its log line, seen by both.
- **PDMS**: an independent audit's report names eight images it checked by eye (0008, 0024,
  0032, 0080, 0089, 0116, 0379, 0389). The author has read the report but not opened the images.
  They stay eligible, and are reported separately if drawn.
- **Prints 183–189 and 191**: not opened.

---

## Pilot 1: PDMS, is the picture used together with the task?

**Data.** Lin et al., *Sci. Data* 2025 ([figshare](https://figshare.com/articles/dataset/sdls_anomaly_detect/29234663/2),
CC BY 4.0): 1,671 images and 2,788 annotations of a self-driving lab's PDMS synthesis. The
visible states include a missing container, one knocked over, an uncapped tube and a spill.

**Items**, chosen by a script with a fixed seed, before any image is looked at:

- **30 matched pairs.** Each pair is one normal and one abnormal annotation sharing `step`,
  `phase`, `Detection_Content`, `Views` and `Distance`, on two different images.
- **Up to 20 context-flip images.** These are images annotated normal under one task step and
  abnormal under another; the audit counted 63. Each is asked under both steps, and it counts as
  right only if both answers are right.

**What the model is given.** The task step, the stage description and what is being checked.
**Never given:** `Anomaly_Label`, `Anomaly_Type`, `Anomaly_Label_Description`, the answer-bearing
`conversations`, the `Grounding` field, or the dataset's `Caption`, which was written knowing the
answer.

**Conditions**, each item under all three:

| | Input |
| --- | --- |
| **C0** | Task context only |
| **C1** | Task context + the image |
| **C2** | Task context + a **visual-fact description** of the image |

**The descriptions in C2** are written by a separate model call that sees the image and nothing
else: no task, no step, no label. It is told to list objects, positions and states, such as
"two containers on the bench, both upright; the left tube has no cap". A fixed list of words
disqualifies a description and forces a rewrite: *abnormal, anomaly, error, wrong, missing,
should, fail, correct, normal, expected*. **C2 is not an expert oracle.** It is a text channel
produced by the vision of a model. If a model succeeds from C2 and fails from C1, the image was
seen but not used under the task framing. If it fails from both, the reasoning is at fault. The
project owner checks 15 descriptions, drawn at random, against their images for accuracy and
leakage.

**Truth** is the dataset's annotation. The project owner also checks 15 randomly drawn
annotations against their images. A label that is not visibly supported is reported and kept, not
silently dropped.

**Models.** `claude-opus-5` and `gemini-3.8-live`, both already characterised. One run per item
and condition.

**Predictions (registered)**

| # | Prediction |
| --- | --- |
| **Pa1** | C0 accuracy is **below 70%** for both models: the task cannot be solved from context alone. If this fails, pilot 1 is not a test of vision, and is reported as such |
| **Pa2** | C1 beats C0 by **at least 15 points** for both models |
| **Pa3** | C2 is **at least as accurate as C1** (within 5 points or better) |
| **Pa4** | On context-flip images, the rate of getting **both** steps right under C1 is **below 60%** |

Pa4 is the one this pilot exists for. The same pixels need different answers under different
steps, so a model that answers from the picture alone must fail one of them.

**Budget.** About 80 items × 3 conditions × 2 models, plus about 80 description calls. **Cap:
US$8.**

---

## Pilot 2: CAXTON, can a person see a state in the clip without the log?

This is a human check. No model is scored.

**Clips.** Ten consecutive logged frames each, about 4.6 s, shown with their original spacing.
Chosen by a script with a fixed seed, from the log alone:

- **8 clips from prints 183–191**, at most 2 per print. The authors excluded these prints for
  large-scale failures or poor lighting.
- **6 clips from print 0** where every logged setting is within 5% of nominal, drawn from frames
  not listed above.
- **2 repeats** of earlier clips, to check the reviewer's consistency.

**Reviewer.** The project owner, on a page that shows the clips shuffled, with no print number,
no parameters and no hint of which pool a clip came from. For each clip the reviewer records:

- what they see, in their own words;
- any of these states: *visible deposition*, *material built up round the nozzle*, *strings or
  loops*, *travel move, nothing being deposited*, *too dark or blurred to tell*;
- which frames the judgement rests on, and a confidence of low, medium or high.

A clip may be left undecided. Nothing forces a verdict.

**Second pass.** The logs are then revealed, and for each clip the reviewer says whether the
logged settings explain what they saw.

**Stop conditions (registered).** CAXTON stops being used as a line of **zero-shot fault
judgement** if any one of these holds:

1. **Fewer than 4** of the 8 flagged clips get a medium- or high-confidence tag of *material built
   up* or *strings*.
2. **No** nominal-log clip is tagged *visible deposition* at medium or high confidence, so there
   is no reasonable normal control.
3. **More than half** of the medium- and high-confidence judgements are revised once the log is
   shown, so the state could only be read with the parameters in hand.

If it stops, CAXTON is kept for what it answers well: whether a specialist vision model reads
process settings. It is **not** rescued by hunting for more extreme examples.

---

## How the pilots will be read

| Outcome | Reading |
| --- | --- |
| Pa1 holds, Pa2 holds | The picture carries task-relevant information and the models use it |
| Pa2 fails, Pa3 holds | The models do not use the picture, but can use a description of it. The bottleneck is visual extraction under task framing |
| Pa2 and Pa3 both fail | The models fail to join what is there to what the task requires, even from text |
| Pa4 holds | Models answer from the picture without regard to the step |
| Pilot 2 passes its stop conditions | CAXTON goes forward as the time-series line, with the flagged prints as camera-only candidates |
| Pilot 2 stops | CAXTON is reported as unsuitable for zero-shot fault judgement, with the reason |

Differences under three items are not interpreted.

## What this cannot show

- **PDMS is stills, without telemetry or time.** It says nothing about Live, streaming or early
  warning, and no claim of that kind is made from it.
- **Neither pilot has a specialist vision baseline yet.** That comes after, if the pilots pass.
- **One reviewer**, who is not an expert in either process.
- **Clips from the same print are not independent**, and none of the counts here are rates.

## Deviations log

1. **Pilot 1: 100 items, not about 80, and the details fixed before any model call
   (2026-09-21).** Items were chosen by `scripts/make_pdms_items.py` from the annotation text
   alone. The registered definition gives 30 pairs (60 items) plus 20 context-flip images asked
   under two steps each (40 items): **100 items on 80 distinct images**. None of the 20 flip images
   had to be set aside as contradictory, meaning the same step, phase and check with opposite
   labels. None of the eight images named by the audit was drawn. The ids are committed in
   `results/pilot1/items.json`.

   Fixed now, before any model is asked:

   - **Answer format.** One tool call, `report_inspection`, with `verdict` NORMAL, ABNORMAL or
     UNKNOWN and a sentence of `observations`. **Accuracy** counts a verdict equal to the truth;
     UNKNOWN is never correct, and the UNKNOWN rate is reported beside accuracy. In C0, UNKNOWN is
     the right answer in spirit, since no picture is given. Pa1 is read on accuracy as registered.
   - **Instruction.** It is the same in all three conditions except for one sentence about the
     evidence: "No photograph is available" (C0), "The inspection camera's photograph is attached"
     (C1), or "A description of the inspection camera's photograph follows, written by someone
     who was not told what is being checked" (C2).
   - **The describer** is `claude-opus-5`, given the image and a fixed instruction to list objects,
     positions and visible states. It is given no task and no step. A description containing a
     banned word is sent back once for a rewrite and then dropped, and drops are counted. Because
     Opus is also a model under test, its own C1-against-C2 difference compares its vision under
     task framing with its vision without it. Gemini's C2 uses Opus's eyes.
   - **Banned words match inside words.** The registered list is matched as word stems, so that
     *unexpected* and *incorrect* are caught along with *expected* and *correct*. A first version
     matched whole words only and let both through; this was caught in a test before any
     description was written.
   - **Two faults in the describer, found after 20 descriptions and before any model was
     scored.** The 20 were discarded, and all 80 were rewritten under the corrected rules. First,
     the instruction set no length, and Opus wrote about 400 words per image. Three calls hit the
     1,024-token output limit, and the tool call came back with its text cut off. The instruction
     now asks for at most 120 words, in keeping with the registration's own one-line example.
     Second, the stem matching above caught *shoulder*, the shoulder of a bottle, as *should*.
     *should* and *missing* are now matched as whole words only.
   - **Transport.** Opus through the standard API, and Gemini through the same single-turn path
     with images as the camera study, which passed the frames-arrive check.

2. **Pilot 2 has 4 nominal clips, not 6 (2026-09-21, before the review).** The rule "every
   logged setting within 5% of nominal, on frames not seen before registration" leaves print 0 with
   one stretch, frames 0–48 without 21–22. That has room for **4** non-overlapping 10-frame clips,
   all from the first minute of the first layer. Six would need either a looser rule or more
   downloads, and neither is registered, so the pool is 4. With the repeats, the review has **14
   clips**: 9 flagged (8 plus one repeat) and 5 nominal (4 plus one repeat). Z offset, nominally 0,
   is held within 0.02 mm, since a percentage of zero means nothing. Clips were chosen by
   `scripts/make_pilot2_clips.py` from the logs alone, with a fixed seed. The key mapping clips to
   prints stays out of the repository until the review is done.

3. **The owner's checks for pilot 1 are drawn now (2026-09-21).** Fifteen items and fifteen
   images were drawn at random with a fixed seed (`results/pilot1/audit_sample.json`). The label
   check is **blind**. The reviewer sees the image, the step and the check, but not the label, and
   says whether the check is met. Their answer is compared with the label afterwards.
