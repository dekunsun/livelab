# Material survey: is there real footage of camera-only lab failures?

Done 2026-09-20, to decide whether the project's first claim — that physical observability exceeds
software observability — can be tested with real imagery rather than left open
([README](../README.md)). The rule that physical imagery must be real, never generated, is what
makes this a search problem rather than an engineering one.

Since the API moved to a paid tier, licence policy is two-tier: **CC BY / CC0 imagery may be
committed**; anything else may only be fetched locally by a script and sent to a paid endpoint,
never redistributed here. Bot protection is never bypassed — two PMC sources were unreachable
behind reCAPTCHA and are recorded as unreachable rather than worked around.

## What was found

| Source | Licence | What it has | Usable? |
| --- | --- | --- | --- |
| [Frontiers, liquid transfer videos](https://www.frontiersin.org/journals/molecular-biosciences/articles/10.3389/fmolb.2023.1147514/full) | CC BY (article) | 19 videos, 720×1280, 30 fps: **bottom-out** (11), **clogged tip** (3), normal (5) | **No — the videos are not released.** "The dataset is currently private since the data acquisition is still in progress" |
| [arXiv 2512.02018, pipette bubbles](https://arxiv.org/abs/2512.02018) | **none stated** | 3,202 real tip images, 1,701 with an air bubble | **No** — no LICENSE in the repo, data on a personal Drive link |
| [Zenodo 17395543, batch distillation](https://doi.org/10.5281/zenodo.17395543) | **CC BY 4.0** | **119 experiments** on a real plant: sensors, actuators, NMR, **audio (47%) and video (77%)**, expert anomaly annotations | **Yes**, but see below |

## The decisive check, and its answer

The batch-distillation record is the only one that is both released and licensed. Its anomaly
metadata (1.7 MB, downloaded) ties every observed anomaly to the sensor that observed it:

- 506 annotated anomalies across 119 experiments;
- every one with an originating observation names a **sensor** (`FT703`, `PY23`, `T709`, …);
- **zero** annotations describe an anomaly as seen on camera, heard, or noticed by a person;
- the injected perturbations are setpoint and actuator manipulations, plus one physical fault —
  **"improperly sealed sample valve", 59 times**.

So the answer to the question this survey was run to settle is **no**: there is no public, licensed
dataset of lab failures that are visible to a camera and absent from telemetry. The strong claim
stays untested, and the README continues to say so.

## What the distillation data does afford

Two things this project cannot get anywhere else, both on **real** data rather than simulation:

1. **A replication target.** Real sensors, real noise, 119 runs, and annotations that state both
   the anomaly and its cause. The benchmark's established finding — that a model commits to a
   verdict where the evidence cannot support one — can be asked again on a real plant.
2. **A weaker but honest version of the vision question.** Video is synchronised with telemetry for
   77% of experiments, so one can ask whether a video channel improves detection *latency* or
   attribution for faults that telemetry does show. That is not "the camera sees what telemetry
   cannot", and must not be reported as if it were.

Worth noting for the simulator's credibility: the most frequent physical perturbation on a real
plant, 59 of 506, is a seal leak — the fault type this project's own library leads with.

## What would answer the original question

Footage of a fault whose signature is optical and absent from the instrument's own channels: a
boat slipping, powder spilling, condensation on a tube wall, an arc, an overflow. Nothing public
and licensed was found. Three routes remain, in order of cost:

1. **Ask.** Both unusable datasets have named contacts, and both are ongoing projects. A licence
   grant costs an email.
2. **Look where the camera is the instrument.** In-situ optical monitoring papers exist
   ([one CC BY example](https://www.beilstein-journals.org/bjnano/articles/10/57)), but they image
   growth, not failure.
3. **Record it.** Out of scope here: no wet lab.
