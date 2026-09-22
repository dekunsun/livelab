# Pre-registration: does a model abstain when the system tells it the evidence cannot settle it?

Status: **registered 2026-09-21, before any item below was run.** Changes after this date are
logged at the end.

## Why

This project's standing recommendation is that "cannot verify" should be **a system state**,
computed from which sensors are installed and what each stage needs, not left to the model's
verdict. The recommendation has never been tested.

Phase two sharpened what it rests on. When the evidence itself was said to be absent or weak
("no photograph is available", a 3-to-2 classifier vote), the models abstained
([pilot 1](results/pilot1_results.md), [specialist](results/specialist_results.md)). In phase
one the missing instrument was stated as well, since the manifest said *not installed*. What the
models failed at was the **inference** from it: that the instruments they did have could not answer
the question. If that is the failure, doing the inference for them should fix it.

## The question

**Q: If the system states, per event, that a condition the current stage requires cannot be
verified with the installed sensors, do models answer UNKNOWN where only UNKNOWN is supported,
without abstaining where the evidence does support an answer?**

## Items

The probe's 38 in-context items ([probe registration](probe_preregistration.md)), unchanged: the
same replays, the same event, and the same prompt v4 wording under variant B0. The system state
comes from the truth file's own field `missing_required_sensors`, which the benchmark's rules
compute from the manifest and the stage's requirements, never from the hidden fault.

| Set | Items | What the system reports | Supported answer |
| --- | --- | --- | --- |
| **U** | 14 | a required sensor is missing (oxygen 6, pressure 2, both 6) | UNKNOWN |
| **A-missing** | 2 | the oxygen sensor is missing, **and** pressure already shows the fault | ANOMALOUS |
| **A** | 7 | every required sensor is installed | ANOMALOUS |
| **N** | 15 | every required sensor is installed | NORMAL |

The two **A-missing** items are the control that matters most. There the system says the
atmosphere cannot be verified, and the right answer is still ANOMALOUS. A model that abstains
whenever it is told something cannot be verified fails them. **Two items are too few to read on
their own**, and they are reported together with A.

## Arms

Each item is asked under all three. The only difference is what is added after the events.

| Arm | Added |
| --- | --- |
| **V0** | nothing: the probe's B0 as it was |
| **V1** | one sentence from the system. For a missing sensor: *"System check for this event: the growth stage requires the control thermocouple, the tube pressure gauge and the exhaust O2 sensor; the <missing sensors> is not installed, so the atmosphere cannot be verified with the installed sensors."* When nothing is missing: *"System check for this event: every sensor the growth stage requires is installed."* |
| **V2** | the same fact as a field in the last event: `"system_check": {"stage": "growth", "required_not_installed": [...], "verifiable": false}` (or `[]` and `true`) |

V0 is rerun alongside V1 and V2 rather than reused, so that all three are collected in the same
hours. This project once read a time trend as a variant effect (probe deviation 7).

All 38 items fall in the growth stage, which requires the thermocouple, the pressure gauge and
the exhaust oxygen sensor. In the benchmark's own table, both the pressure gauge and the oxygen
sensor serve the **atmosphere** condition, so that is the condition V1 names whenever either is
missing. Sensor names are the probe's own wording, so nothing new is introduced.

## Models

`gemini-3.8-live`, `claude-opus-5` and `gpt-6-astra`: the three characterised on these items.
One run per item and arm.

## Measures

For each model and arm: the share of **U** answered UNKNOWN; **A and A-missing** detection
(ANOMALOUS) and their UNKNOWN rate; **N** answered NORMAL and its UNKNOWN rate; and coverage, not
read below 90%.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pp1** | Under **V1**, U abstention is **at least 50%** for at least two of the three models (under V0 it has been close to 0) |
| **Pp2** | Under V1, detection on A and A-missing falls by **fewer than 3 of the 9 items**, and N's UNKNOWN rate rises by fewer than 3 of 15, for every model that meets Pp1 |
| **Pp3** | **V2 is at least as effective as V1**: U abstention within 2 items of V1's, or higher |
| **Pp4** | **Gemini's** U abstention under V1 stays **below 50%** |

The reasoning. Pp1 follows from phase two: a stated absence is respected, and V1 states it per
event, with the inference already done. Pp4 is the counterweight from phase one. There, an
explicit definition of when to answer UNKNOWN moved Opus and Astra and left Gemini at 0 of 14,
at every thinking level. If Gemini also ignores a per-event statement, stating it is not enough
for every model, and the system has to decide rather than inform.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Pp1 and Pp2 hold | **The recommendation holds**: compute "cannot verify" in the system and state it per event, and models abstain where they should without abstaining where they should not |
| Pp1 holds, Pp2 fails | Models abstain whenever told something cannot be verified, including where the evidence settles it. The system must decide, not just inform |
| Pp1 fails | Stating it is not enough. The recommendation is rewritten: the system overrides the verdict |
| Pp4 fails the other way (Gemini abstains) | The phase-one Gemini result was about the inference, not about Gemini |
| Coverage below 90% | Not read |

Differences under three items are not interpreted.

## Budget

38 items × 3 arms × 3 models = 342 calls, text only. **Cap: US$8.**

## What this cannot show

- **Simulated items**, one event each, 38 in all, of which only 2 are the key control.
- **The system state is correct by construction.** It is computed from the same rules that
  make the truth. A real system's state could be wrong, and this does not test what models do
  with a wrong one.
- **One wording** of V1 and one shape of V2.

## Deviations log

None yet.
