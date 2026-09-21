# Real-plant replication: the finding holds, and the simulator was flattering the models

Registered before any item was built: [realdata_preregistration.md](../realdata_preregistration.md).
Collected 2026-09-20 on [Zenodo 17395543](https://doi.org/10.5281/zenodo.17395543) — 119
experiments on a real batch distillation plant, CC BY 4.0, 18 channels at 1 Hz. **Truth is the
dataset's expert annotations**, not this project's rules. 99 items per model, one run each, 0
without an answer.

| Condition | n | What is delivered | Supported answer |
| --- | --- | --- | --- |
| **Full** | 31 | every channel | `ANOMALOUS` — the experts saw it here |
| **Blind** | 31 | the instrument group that observed it removed | `UNKNOWN` |
| **Control** | 37 | a fault-free run, every channel | `NORMAL` |

## Results

| | Gemini 3.8 Live | Claude Opus 5 |
| --- | --- | --- |
| Detection on Full | 20/31 (65%) | 22/31 (71%) |
| **Abstention on Blind** | **0/31 (0%)** | **4/31 (13%)** |
| Over-abstention on Control | 0/37 | 0/37 |
| **Called a fault-free run ANOMALOUS** | **8/37 (22%)** | **12/37 (32%)** |
| Detection gap, Full − Blind | 6 points | 13 points |

## The registered predictions

| # | Prediction | Observed | Met |
| --- | --- | --- | --- |
| **Pr1** | Blind abstention ≤ 10% | 0% and 13% (4 of 31) | **yes / marginal** |
| **Pr2** | Detection on Full ≥ 60% | 65% and 71% | **yes** |
| **Pr3** | Over-abstention on Control ≤ 20% | 0% and 0% | **yes** |
| **Pr4** | Detection gap ≥ 30 points | 6 and 13 points | **no** |

Opus 5's 13% is four items against a bar of three, and the registration does not interpret
differences under about three items. It is a margin, not a counterexample.

## What this establishes

**The central finding is not an artefact of the simulator.** Real sensors, real noise, real
operators' annotations, a different process in a different lab — and where the instrument group
that carried the evidence is not delivered, the models abstain 0% and 13% of the time. They answer
`NORMAL` or `ANOMALOUS` instead.

**Pr4's failure says the same thing from the other side, and more sharply.** Removing the whole
instrument group moved the verdict by 6 and 13 points. In the blind condition the models still said
`ANOMALOUS` on 18 of 31 items. **The answer barely depends on whether the evidence is there.**

One caveat governs that reading and is registered, not added afterwards: a distillation column
couples its instrument groups, so a temperature excursion may leave a trace in pressure. A model
answering `ANOMALOUS` in the blind condition is **not necessarily wrong**, and abstention here is a
lower bound rather than a proof. What survives the caveat is the movement, not the level: the
verdict changed very little when a quarter to two-thirds of the instruments went away.

## What this costs the benchmark

**On the simulator, false alerts in the full-evidence arm were 0.00. On the real plant, the same
models call a fault-free run anomalous 22% and 32% of the time.**

That is a criticism of this project's own testbed, and it belongs here rather than in a footnote.
The simulator's reference bands are built from 100 normal runs of an identical process; a real
plant's fault-free runs differ from each other in ways a calibrated band does not capture. **The
benchmark's false-alert numbers are optimistic, and its detection numbers (0.90) are too** — on
real data the same models reach 0.65 and 0.71.

What does *not* change between the two is the abstention result, which is the finding the project
reports.

## What this does not show

- **Distillation is not CVD.** This says the behaviour is not an artefact of *this* simulator; it
  does not make the two processes equivalent.
- **Telemetry only.** The record's video and audio are unused: no annotation names an anomaly that
  a camera saw and a sensor did not ([survey](../material_survey.md)).
- **The blind condition is structural, not proven** — see the caveat above and deviations 1 and 2
  of the registration.
- **One run per item**, 31 items per anomalous condition.
- Token usage was not aggregated for the Live backend, so only the Opus 5 spend is measured:
  **$3.88** for 99 items.
