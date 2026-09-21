# Pre-registration: does the finding hold on a real plant?

Status: **registered 2026-09-20, before any item is built or any model is asked.** Changes after
this date are logged at the end, with reasons.

## Why

Everything this project has measured runs on a simulator. The instrument dynamics are
author-constructed, and the README says so. The central finding — that a model commits to a verdict
where the delivered evidence cannot support one — has held across four models, seven framings and
two mechanisms (a missing sensor, and a sampling interval too coarse to see a transient). It has
never been asked of real data.

[Zenodo 17395543](https://doi.org/10.5281/zenodo.17395543) makes that possible: **119 experiments
on a real batch distillation plant**, CC BY 4.0, with 1 Hz telemetry from 18 sensor channels,
actuator logs, and **expert annotations that name both each anomaly's time window and the sensor
that observed it** ([survey](material_survey.md)).

That last detail is what makes a replication possible rather than an analogy. The sensor-removal
cascade — this project's core device — can be built from the experts' own account of which channel
carried the evidence, instead of from a rule of ours.

## The question

**Q: On real plant data, with truth taken from the plant's own experts, does a model abstain when
the channel that carried the evidence is not delivered?**

## Data

| | |
| --- | --- |
| Experiments | 119 (81 with injected anomalies, 38 fault-free) |
| Channels | 18 at 1 Hz: `LS701/702`, `T701`–`T712`, `FT703/704`, `PDI701/702`, `PY23`, `FYI702` |
| Annotations | 506 anomalies; **147 of them, in 43 experiments, name the observing sensor** |
| Licence | CC BY 4.0. Telemetry only — no audio or video is used here |

## Truth comes from the dataset, not from this project's rule

**This is the point of the study, so it is stated first.** The supported answer is read from the
expert annotation: an anomaly's `hasBeginning`/`hasEnd` and its `wasOriginatedBy.Observation`. This
project's z-score rules (`observability.py`) are **not** used to decide truth here. Re-deriving
truth with our own rule and then scoring a model against it would replicate the rule, not the
finding.

The rules are used for exactly one thing, as a **guard, never as truth**: in the blind condition
below, an item is dropped if any *remaining* channel still departs by |z| ≥ 3.5, because then the
evidence has not actually been removed. That check makes the blind condition honest and is not
allowed to create or relabel any item.

## Conditions

Per anomalous experiment, over the same window ending at a decision point inside the anomaly:

| Condition | What is delivered | Supported answer |
| --- | --- | --- |
| **Full** | all 18 channels | `ANOMALOUS` — the experts saw it here |
| **Blind** | the observing channel removed, and the guard above satisfied | `UNKNOWN` |
| **Control** | a fault-free experiment, all channels | `NORMAL` |

Blind is the replication of the 1,986-event finding. Control is what stops a model that abstains
everywhere from looking calibrated.

## Items

Each item is one window of real telemetry as a single turn, in the same compact format the probes
use, ending at a decision point. **Cadence 60 s over a 20-minute window** (20 events), so an item
is comparable in size to the probe items already run. The window ends inside the annotated anomaly
for Full and Blind, and at a matched time for Control.

Target: **43 experiments × 3 conditions ≈ 129 items per model**, subject to the guard and to
windows that fit inside the Operation phase.

## The instruction has to be ported, and the port is frozen here

Prompt v4 names a tube furnace and its stages. A distillation column is not one, so the wording
must change, and this is the one place where "frozen" cannot be taken literally.

**The port changes process nouns only** — furnace → column, stage names, channel names — and
changes **nothing** about the contract: the same fields, the same enum
(`NORMAL`/`ANOMALOUS`/`UNKNOWN`), the same definition of when to abstain, the same single-turn
sentence. The ported text is committed **before any model is run**, and a diff against v4 goes in
the results so a reader can check what moved. No wording is revised after seeing output.

## Measures

- **Abstention on Blind** — the share answered `UNKNOWN`. The headline.
- **Detection on Full** — the share answered `ANOMALOUS`.
- **Over-abstention on Control** — the guard.
- **Coverage** — answered / registered, beside every rate, as in every study here.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pr1** | Abstention on Blind is ≤ 10%, replicating the simulated result on real data |
| **Pr2** | Detection on Full is ≥ 60% — lower than the simulator's 0.90, because real noise is not a calibrated band |
| **Pr3** | Over-abstention on Control is ≤ 20% |
| **Pr4** | The gap between Full and Blind detection is at least 30 points: the model's verdict does follow the evidence when the evidence is there |

Pr1 is the replication. **If it fails — if models abstain on real data — the simulator's clean
reference bands are implicated, and that is a finding about this benchmark**, not a relief.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Blind abstention ≤ 10% | The finding is not an artefact of the simulator. The product conclusion carries to real plants |
| Blind abstention high | The simulated evidence made abstention unnatural in a way real data does not. The benchmark's headline narrows to simulated telemetry, in the sentence that reports it |
| Detection on Full low, Blind also low | The model is not tracking this plant at all, and no abstention conclusion can be drawn from it. Reported as a failed replication, not as support |
| Coverage below 90% | Not read, as everywhere else |

## Models

`gemini-3.8-live` and `claude-opus-5` — the two already characterised on the simulator, so a
difference is about the data rather than about a new adapter.

## Budget

About 129 items × 2 models ≈ 258 calls at roughly 3k tokens each. **Cap: US$10.**

## What this cannot show

- **A different process.** Distillation is not CVD. A replication here says the behaviour is not an
  artefact of *this* simulator; it does not say the two processes are equivalent.
- **Telemetry only.** The dataset's video and audio are not used: its annotations name no anomaly
  that a camera saw and a sensor did not ([survey](material_survey.md)).
- **The blind condition is approximate.** Removing the channel the experts named removes the
  evidence they cited; another channel may still carry a trace, which is what the guard is for, and
  the guard is a rule of ours applied to real data.
- **One run per item**, as everywhere in this project.

## Deviations log

1. **The guard could not be built on this data, and the blind condition is structural instead
   (2026-09-20, before any model ran).** Two attempts failed for reasons worth recording:

   - A **within-run baseline** marks 15 of 18 channels as departing. This is a *batch*
     distillation: temperatures climb through the whole run as the light component leaves, so a
     global baseline reads the normal trajectory as an anomaly.
   - A **paired-twin baseline**, using the dataset's own fault-free run at the same operating
     point, fails on alignment. Paired runs differ in length — 3,526 against 4,879 samples in one
     case, 8,414 against 4,110 in another — so an index-aligned difference measures the
     misalignment: one temperature channel read z = 122 from that alone. Resampling both runs onto
     a common progress axis would work, and would be a rule of ours shaping the very thing the
     study is meant to take from the experts.

   So the blind condition removes **the whole instrument group** the observing sensor belongs to —
   temperature, flow, pressure or level — read off the plant's tag list rather than off the data.

2. **What that costs the claim.** "Only `UNKNOWN` is supported" is now an argument from the
   instrument list, not a proof: the column couples groups, and a temperature anomaly may leave a
   trace in pressure. A model that answers `ANOMALOUS` in the blind condition is therefore not
   necessarily wrong, and **abstention on blind is a lower bound**. This is weaker than the
   simulated study, where the cascade could be proven, and it is reported as such.

3. **A third model was added after the first two were scored (2026-09-20).** The registration
   names `gemini-3.8-live` and `claude-opus-5`. `gpt-6-astra` was added **after** their results were
   read, which is exactly the move pre-registration exists to discipline, so the reason and the
   limits are recorded here:

   - The decision is about **generality, not about a better number**. The measures, items, truth
     and prompt are unchanged and were fixed before any model ran; nothing is re-scored.
   - What prompted it: the finding that these models call a fault-free real run anomalous 22% and
     32% of the time rests on **two** models. A third either shows it is general or shows it is not.
   - Predictions Pr1–Pr4 are **not** restated for it. They were registered against the two named
     models and stand as scored; astra is reported beside them and its numbers are labelled as an
     unregistered extension.

4. **The ported instruction is committed** at `livelab/realdata_prompt.py`, before any run;
   `python -m livelab.realdata_prompt --diff` prints what changed against v4. A test asserts the
   contract sentences are byte-identical.

5. **The plant description the models read was wrong (found 2026-09-21, after every real-plant
   result was published).** The ported instruction's tag legend (deviation 4) was written by me,
   not taken from the dataset, and it was wrong in four places:

   | Tag | The legend said | The dataset's annotations say |
   | --- | --- | --- |
   | T701–T712 | temperatures along the column, reboiler to condenser | T701, T702, T704, T706 and T708 are **heater** temperatures, which run at 300–500 °C. T703 is the reboiler vessel. The rest are column sections, not in order |
   | FT703 / FT704 | reflux / distillate | **distillate / reflux**, swapped |
   | FYI702 | flow ratio | **cooling-water** flow |
   | PDI702 | a column pressure difference | the **buffer vessel's** pressure difference |

   Each correction was checked against a second source before being accepted. The five heater
   temperatures carry the same numbers as the five heaters in the plant's actuator log (H701,
   H702, H704, H706, H708). The flows fit the physics only one way round: under the dataset's
   labelling, reflux is about twice distillate and exceeds it in 78% of events, as it should in a
   batch column. Under the legend's labelling, the column would be running at a reflux ratio of
   0.5. The table with sources is `data/realdata/tags.csv`.

   **How it was found.** In the camera study, every false alert on a fault-free run cited T701 as
   an implausible "reboiler" temperature. Opus's reasoning was correct *given the legend*: a
   reboiler at 330 °C under a column at 60–90 °C would be broken. A heater at 330 °C is ordinary.

   **What it affects.** Across the three models, the answers calling a fault-free run anomalous
   cite a heater temperature in 11 of 12 (Opus 5), 37 of 37 (GPT-6 Astra) and 0 of 8 (Gemini).
   (Corrected the same day. The first count, published briefly as 12, 37 and 3, matched `FT704`,
   the reflux flow, as the heater `T704`; the pattern now requires a word boundary.)
   Evidence lists name several channels, so citing is not proof of cause. But the false-alert
   rates reported for this study (22%, 32%, 100%) cannot be read as the difficulty of real data;
   they are at least partly the cost of a wrong description. The same holds for detection on Full,
   and for the `ANOMALOUS` answers on Blind that abstention is measured against.

   **What it does not affect.** Every arm and condition in every real-plant study received the same
   legend, so paired comparisons within a study hold as comparisons: the camera's effect, and the
   follow-up's decomposition of it. The simulated benchmark and the probes used a different
   instruction and are untouched.

   **What happens next.** The corrected legend is `LEGEND_V2` in `livelab/realdata_prompt.py`. The
   old one is kept byte-exact as `LEGEND_V1`, and runners still use it, so the two can never mix in
   one results directory. A rerun under V2 is a new registered study, with both versions reported;
   nothing is overwritten.
