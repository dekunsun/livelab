# Pre-registration: what moved Opus 5, the photographs or the sentence?

Status: **registered 2026-09-20, after the camera study was scored and before any arm below ran.**
Changes after this date are logged at the end.

## Why

In the [camera study](results/vision_results.md), adding six frames from the plant's camera moved
Opus 5 towards `ANOMALOUS` on every item where it changed its answer. That meant +21 points on blind
items and +38 on fault-free runs. Gemini did not move.

That study's frames arm changed two things at once: it attached the photographs, and it added one
sentence to the instruction saying they were attached. The results page says this cannot be
separated. This study separates it.

It matters for the product question. If the sentence alone does it, the model is reacting to being
told it is watched by a camera, and the cure is in the wording. If photographs of a *different*
run do it just as well, the model is reacting to photographs existing, not to what they show. In
that case a camera adds alarm without adding information, whatever the prompt says.

## The question

**Q: Is Opus 5's shift towards `ANOMALOUS` caused by the sentence announcing a camera, by the
presence of photographs, or by what the photographs show?**

## Items and model

The same 48 items as the camera study (19 blind, 29 control), the same instruction, the same
tools. **Opus 5 only**, because it is the model that moved. Gemini's null leaves nothing to
separate.

## Arms

The two existing arms are reused as collected. Two new arms are added:

| Arm | Instruction | Attached | Status |
| --- | --- | --- | --- |
| telemetry | base | nothing | collected |
| frames | base + sentence | this run's 6 frames | collected |
| **sentence** | base + sentence | **nothing** | new |
| **other_frames** | base + sentence | **6 frames from a different fault-free run** | new |

- **sentence** keeps the sentence byte-identical, so it now says six photographs are attached when
  none are. That is deliberate: any other wording would change two things again. The risk is that
  the model notices the missing images and reacts to the mismatch. Its free-text reasoning is read
  for that, and the count is reported (see Measures).
- **other_frames** gives every item, blind or control, the frames of a **different control run**,
  meaning footage of a column that was running normally. Donors are assigned once, by a seeded
  derangement over the control items, so no item receives its own experiment's footage. The
  assignment is written out before the run and committed with the results. The frames come from
  the same camera, the same resolution and the same six even positions across that donor's window.

## Measures

For each arm, the share answered `ANOMALOUS` on blind and on control items, and abstention. All
comparisons are paired per item against the telemetry arm, and only items answered in every arm
compared are counted.

- **Shift** of an arm = its `ANOMALOUS` rate minus the telemetry arm's, separately for blind and
  control.
- **Mismatch mentions** in the sentence arm = the number of answers whose text says the photographs
  are missing, not visible or not attached. It is counted by a fixed keyword list, written into
  the scorer before the run.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pf1** | The **sentence** arm reproduces **less than half** of the frames arm's shift on control (under +19 points) |
| **Pf2** | The **other_frames** arm reproduces the frames arm's shift on control to within **10 points** |
| **Pf3** | Abstention stays ≤ 10% in both new arms |

The reasoning, so that it can be wrong for a reason, from the camera study's records (checked
before registering, by `scripts/explain_vision_flips.py`):

- Opus changed 15 verdicts to `ANOMALOUS` when the frames were added. **14 of those 15 answers never
  mention the photographs.** All 15 cite the same telemetry channel, the reboiler temperature
  `T701`, as implausible or a faulty sensor.
- On 13 of those items, the telemetry-only answer had also cited `T701` and called it normal, for
  example "smooth monotonic heat-up, reboiler 321→330 °C".

So the photographs did not supply evidence. They changed how Opus read a number it already had.
If that is the mechanism, footage from a different normal run should work as well as this run's
(Pf2), because what the frames show is not being used. The sentence alone is predicted to do less
(Pf1), because the change shows up where images are attached. That second prediction is the
weaker one.

## How results will be read

| Outcome | Reading |
| --- | --- |
| sentence ≈ frames, other_frames ≈ frames | The cue is the announcement. Wording can fix it |
| sentence small, other_frames ≈ frames | **Photographs raise suspicion regardless of their content.** A camera adds alarm, not information |
| sentence small, other_frames small | Opus reads the *content* of this run's frames. The earlier shift is a response to what this camera showed, and the control false alerts need another explanation |
| Any other pattern | Reported as observed, with no mechanism claimed |
| Mismatch mentions in more than a quarter of sentence-arm answers | The sentence arm is not read as a clean test of the wording. It is reported and the reason is given |

Differences under three items are not interpreted, as everywhere in this project.

## Budget

48 items × 2 arms = 96 Opus 5 calls. The camera study measured US$4.40 for 96 calls with frames
in half of them. **Cap: US$6.**

## What this cannot show

- **One model.** Whether other models share Opus's shift is untested here, apart from Gemini
  showing none.
- **One sentence.** A differently worded announcement might act differently. This tests the
  sentence that was used.
- **Donor footage is from normal runs only.** It separates "any photograph" from "this run's
  photograph", not "normal footage" from "faulty footage".

## Deviations log

None yet.
