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

## Second survey, outside the lab (2026-09-21)

The first survey looked for camera-only failures in laboratory work and found none public. The
second looked where cameras monitor physical processes as a matter of course: additive
manufacturing, welding, assembly cells, lab automation. **No public dataset has everything at
once:** real video, synchronised telemetry, anomalies labelled by time window, and failures
documented as visible only to the camera. Several come close.

Rows marked † were read by a survey agent from each landing page and not re-checked here. CAXTON
was checked directly, below.

| Source | Licence | Footage and telemetry | Camera-only failures? | Fit |
| --- | --- | --- | --- | --- |
| **[CAXTON](https://doi.org/10.17863/CAM.84082)**, extrusion 3D printing | **CC BY 4.0**; code MIT | 1,272,273 nozzle-camera images, 1280×720, 2.5 Hz, 192 prints. Every image carries a timestamp, flow rate, speed, Z offset, target and measured hotend temperature, bed temperature | **Yes, by construction.** The printer has no sensor for extrusion or Z offset. With those setpoints withheld, only the camera shows them | **Best available** |
| [NIST AMMT Overhang](https://pmc.ncbi.nlm.nih.gov/articles/PMC10871811/)†, laser powder bed | Public domain | Melt-pool camera up to 10 kHz; commanded laser path at 100 kHz | Yes by design; no labels yet | Partial: timescale studies |
| [ORNL DED](https://www.osti.gov/dataexplorer/biblio/dataset/2446626)†, metal deposition | Open (no rights asserted) | Melt-pool video 60 Hz; position 100 Hz | Melt-pool flaws, located by CT | Partial |
| [AEGIS](https://arxiv.org/html/2607.15620)†, OT-2 liquid handler | MIT (stated) | 64 real trajectories, 38 deliberate failures; command timestamps aligned to ±1 frame | **Yes, every one**: the robot has no liquid sensing | **Ideal lab fit, not yet released** |
| [Intel robotic welding](https://huggingface.co/datasets/amr-lopezjos/Intel_Robotic_Welding_Multimodal_Dataset)† | Research use only, **no commercial use**; login and contact-sharing agreement | 30 fps video, audio, current/voltage/gas/speed | Plausibly (spatter, porosity), unconfirmed; one label per weld | Excluded: derived frames likely cannot be published |
| [Future Factories v2](https://arxiv.org/abs/2502.05020)† | CC BY-SA 4.0 (per paper) | Two cameras, PLC, robot and load-cell data | Missing parts visible on camera | Partial: a factory cell |

### CAXTON, checked

From the repository record, the paper (Brion & Pattinson, *Nat. Commun.* 2022) and the code
repository's dataset README:

- **Images are released**, as one ZIP per print (print0.zip is 156 MB, print1.zip 223 MB; 198
  files in all). A first reading of the repository page saw only its five CSVs because the file
  list is paginated.
- **How the "faults" arise.** During each print, flow rate (20–200%), lateral speed (20–200%),
  Z offset (−0.08 to 0.32 mm) and hotend temperature were resampled at random every 150 images,
  about once a minute. Truth is therefore the setpoint, known exactly, not an annotator's
  judgement.
- **A built-in timescale.** The authors drop 15 images, about 6 s, after each change, "due to a
  combination of software and mechanical delays" before the change is visible. That is a measured
  lag between a command and its appearance on camera.
- **What the telemetry can and cannot show.** Hotend temperature is measured by a thermistor,
  so a hotend fault is visible in telemetry. Flow rate and Z offset are commanded values with no
  sensor behind them. Withhold them and the camera is the only witness. That gives all four cells
  of the information-structure design: telemetry-only, camera-only, both, and neither.
- **Caveats stated by the authors.** Z offset is the noisiest label, and values below 0.08 mm
  include mislabels. Prints 183–191 contain large-scale failures or poor lighting and were excluded
  from their training. Those may be the closest thing here to real, unplanned failures.
- **No trained model is released.** The repository has code but no weights and no releases, so a
  specialist CV baseline would have to be trained here.

What it cannot stand in for: these are deliberate parameter perturbations on a printer, not
failures in a scientific experiment. The benchmark can use it to answer *when a camera carries
information telemetry does not*, and *whether a model uses it*. The lab-specific claim still
needs lab footage, and AEGIS is the one to watch for that.

### CAXTON, one print downloaded and looked at (2026-09-21)

`print0.zip` (163.84 MB) and `caxton_dataset_filtered_no_outliers.csv` (116.12 MB), both
matching the repository's MD5 checksums, kept under the gitignored `data/external/caxton/`.

- **3,086 images in print0, 24 minutes of printing.** The measured capture interval is **0.46 s**
  (about 2.2 Hz; the paper states 2.5 Hz) and very steady. Parameters change about every 150
  images, roughly 69 s.
- **The raw log carries glitches.** Z offset reads −2.32 or −2.54 mm for one to four images at a
  time, far outside the stated range. These are the "incorrectly stored" values the filtered files
  remove, so any use of this data has to filter the same way.
- **Whether the picture carries the answer to a human eye: weakly, in single frames.** On a
  contact sheet cropped around the nozzle, the way the authors crop, a speed change is obvious
  (motion blur). A flow change is not obvious, even 36% against 100% at steady state. Frames are
  dark, often blurred, and sometimes catch the nozzle between features. The information is there,
  since the authors' network reaches 84% average accuracy, but that network needed about a
  million training images. That judgement is the author's, who is not an expert in extrusion
  printing, and it is exactly what an independent description of each frame, without the answer,
  should test before any model is scored.

**What this means for the camera-only design.** The cell exists, but its signal may be too
subtle in a single frame for a general model. A study built on this data should use the
**extreme settings** (flow near 20% or near 200%, Z offset near its top), **sequences** rather
than single frames, and a first check that a person can tell the conditions apart. Otherwise a
null result would say more about the footage than about the model.
