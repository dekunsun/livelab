# Attribution: CAXTON 3D-printing nozzle-camera frames

The frames in `clips/` and the answer key `key.json` are **derived from a published dataset under
CC BY 4.0**. Redistribution is permitted with attribution, which is what this file is.

## Source

> Brion, D. A. J. and Pattinson, S. W., *Generalisable 3D printing error detection and correction
> via multi-head neural networks*, Nature Communications 2022.
> Dataset (CAXTON): [10.17863/CAM.84082](https://doi.org/10.17863/CAM.84082)
> Licence: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/); code MIT.

## What was derived

- `clips/clipNN/`: 140 nozzle-camera frames, unmodified, cut from the dataset's prints by
  `scripts/make_pilot2_clips.py`, which chose the clips from the print logs alone (registered
  design: `docs/pilots_preregistration.md`, pilot 2). Frames of print 0, looked at before the
  registration, were never eligible.
- `key.json`: the seed and the map from each shuffled clip back to its print and frame range. It was
  kept out of the repository until the blind human review was finished
  (`docs/results/pilot2_results.md`), and committed on 2026-10-14.

Survey notes on the dataset: `docs/material_survey.md`.
