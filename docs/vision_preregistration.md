# Pre-registration: when an instrument is missing, does a camera put it back?

Status: **registered 2026-09-20, before any frame was extracted or any model was asked.** One video
was fetched beforehand to prove the pipeline decodes; nothing was looked at except a single frame
to confirm the camera view. Changes after this date are logged at the end.

## Why this, and not the question the survey killed

The [material survey](material_survey.md) settled that no public, licensed dataset contains lab
failures that a camera can see and telemetry cannot. That blocks the project's strongest claim, and
the README says so.

It does not block the question a plant engineer actually has. **Instruments fail, are not fitted, or
are taken out for service.** The real-plant study measured what models do when the instrument group
that carried the evidence is gone: they keep ruling — abstention 0, 4 and 3 of 31
([results](results/realdata_results.md)). The next question is whether a camera watching the same
run compensates.

This is also the question worth asking about multimodality in a lab. The field's default assumption
is that adding vision helps. This benchmark has already measured one case where it did not: in the
simulated arm, reference curves plus micrographs did no better than reference curves alone, both at
0.90 detection.

## The question

**Q: With the instrument group that carried the evidence removed, do frames from the plant's own
camera restore the judgment that the missing instruments supported?**

## Data

The same real-plant items as the [real-data study](realdata_preregistration.md), restricted to
experiments whose Operation phase has video (Zenodo 17395543, CC BY 4.0):

| | Items | Notes |
| --- | --- | --- |
| **Blind** (observing instrument group removed) | **20** of 31 | pressure 12, temperature 5, flow 3 |
| **Control** (fault-free run) | **30** of 37 | |

Video is `Cam0`, 1920×1080, **one frame every two seconds**, with wall-clock timestamps in a `.txt`
beside each file, so a decision time maps to a frame exactly. The camera views the column top: the
condenser coil, the glass, the reflux and distillate lines.

## Conditions

Each item is run **twice**, and is its own control:

| Arm | Delivered |
| --- | --- |
| **telemetry** | the window's telemetry with the instrument group removed — already collected |
| **telemetry + frames** | the same text, plus **6 frames** evenly spaced across the same 20-minute window, downscaled to 640×480 |

Six frames at 640×480 cost about 2.5k extra tokens per item, measured
([frame cost](results/frame_token_cost.md)). Control items get frames in the same way, so the
presence of video never signals which condition an item is.

Truth is unchanged and still the dataset's expert annotations: `ANOMALOUS` is supported for blind
items, `NORMAL` for controls. **Abstention is not scored as correct here** — the question is
whether the camera restores a judgment, not whether the model hedges.

## Measures

- **Detection on blind, with frames minus without** — the headline, paired per item.
- **False alerts on control, with frames minus without** — the guard: a camera that makes every run
  look wrong is not compensating for anything.
- **Abstention**, reported for completeness.
- **By removed group** — pressure / temperature / flow. **Exploratory only:** with 12, 5 and 3
  items, no comparison between groups is interpreted, and none is predicted.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pr1** | Detection on blind rises by **fewer than 10 points** with frames — the camera does not compensate |
| **Pr2** | False alerts on control rise by fewer than 10 points — the camera does not manufacture alarms either |
| **Pr3** | Abstention stays ≤ 10% in both arms: another modality does not make a model say it cannot tell |

**Pr1 predicts a null, and the reason is stated so it can be wrong for a reason.** The camera sees
the column top; most annotated anomalies are setpoint and actuator manipulations whose visible
consequence is a change in boiling or reflux rate, against no baseline of what that run should look
like. If detection does rise, the interesting follow-up is whether it rises where the camera can
plausibly see the missing quantity — flow — and that is the exploratory split above.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Detection rises materially, controls flat | A camera compensates for missing instruments. The strongest multimodal result this project could produce, and the one that would justify the word in its title |
| Detection flat | Adding vision does not substitute for an instrument. Together with the simulated arm, that is two measured cases against the field's default assumption |
| Detection rises and control false alerts rise as much | The camera raises suspicion, not accuracy. Reported as such, never as detection |
| Coverage below 90% | Not read, as everywhere else |

## Models

`gemini-3.8-live` (native multimodal) and `claude-opus-5` (image input), both already characterised
on the telemetry-only arm, so a difference is about the frames. The standard-API backend does not
send images yet; that is the one piece of code this study needs, and it will carry the same parity
test as the text path.

## Budget

50 items × 2 arms × 2 models = 200 calls, about 4k tokens each with frames. **Cap: US$5.**

## What this cannot show

- **One camera view.** The plant records three; only `Cam0` is used, and it sees the column top.
  A negative result is about this view, not about cameras.
- **Six frames.** Sampling the window more finely might show more; six was chosen for cost before
  any result was seen.
- **Not the strong claim.** Nothing here tests whether a camera sees failures telemetry cannot —
  that needs footage of camera-only faults, which no public dataset has.
- **The blind condition is structural** — deviations 1 and 2 of the
  [real-data registration](realdata_preregistration.md) apply unchanged.

## Deviations log

1. **The frames span the recording, not always the full 20 minutes (2026-09-20, before any model
   ran).** Four of the nineteen blind recordings begin *after* the telemetry window does — the
   camera was switched on 2 to 7 minutes into it. Under the registered rule (six frames evenly
   across the whole window, each within 30 s of its target) those four items lose a frame or two
   and would be dropped, taking blind from 19 to 15.

   Instead the six frames now span the **intersection** of the telemetry window and the recording,
   still ending at the decision time, and an item is dropped if that intersection is shorter than
   **10 minutes** — none is. Each item records its `frame_span_s`, so which items saw less is
   visible rather than buried.

   What it costs: in those four items the frames cover 13 to 17 of the 20 minutes the telemetry
   covers, so the two arms are not looking at exactly the same stretch of time. The threshold was
   fixed before any model was asked anything, and the alternative — dropping a fifth of the items
   because a camera started late — throws away more.

2. **A guard was added: the frames are proven to arrive (2026-09-20, before the study ran).**
   Pr1 predicts a null, and an image path that silently dropped its attachments would produce that
   null perfectly. The Live backend reports no token counts, so the usual evidence — the prompt got
   bigger — is not available for one of the two models.

   `scripts/check_frames_arrive.py` therefore sends the same six frames through the same code path
   with a question only the frames can answer, and sends the same question with no frames. On
   `gemini-3.8-live`: **6 of 6 reported with frames, 0 without**, described as "a coiled condenser
   and a reservoir in a fume hood". The evidence is saved beside the results. A model that cannot
   pass this check is not run.

   This is the same move as deviation 7 of the [probe registration](probe_preregistration.md):
   before a silence is scored as model behaviour, the path is shown to be working.

3. **The timestamp sidecars had to be fetched separately (2026-09-20).** `fetch_zenodo_members.py`
   matched `.mp4` only, so the first pass pulled video with no clock beside it. Frames without the
   sidecar cannot be placed on the plant's clock at all, and the mapping the registration relies on
   — timestamp *i* is frame *i* — is now checked rather than assumed: in all six recordings tested
   the sidecar's line count equals the video's frame count exactly, at the stated 2 s cadence.

4. **The registered budget was computed on the wrong item size (2026-09-20, before the study
   ran).** The cap of US$5 assumed about 4k tokens per item with frames. The real-plant items
   measure **5,211 input tokens** on average before any frame is added, and the frames add about
   2,500 more. At the Opus 5 price implied by the real-data run's measured US$3.88 for 99 items,
   this study costs about **US$4.50 for Opus 5 alone**, plus the Gemini side.

   Nothing about the design changes; the estimate was wrong, not the plan. The cap is restated
   here as **US$12 for both models**, and the actual spend is reported with the results.

5. **One control recording is dropped because its clock and its frames disagree (2026-09-20,
   before its item ran).** Every video was checked the same way: the frames in the stream against
   the timestamps in the sidecar. 48 of 49 agree exactly. One control recording
   (`acetone+butan-1-ol+methanol/operating_point_006/train_normal_experiment_001`) has **1,261
   frames and 1,169 timestamps**. The file is complete — the surplus is in the source — but with 92
   frames unaccounted for there is no way to say which minute a given frame shows, so no frame
   from it can be placed at a decision time. The check is now a rule in `make_vision_items.py`,
   not a hand exclusion. Control goes from 30 to 29; blind is unchanged at 19. **48 items.**
