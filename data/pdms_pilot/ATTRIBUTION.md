# Attribution: PDMS self-driving-lab inspection photographs

The 80 photographs in `images/` and the item list `items.json` are **derived from a published
dataset under CC BY 4.0**. Redistribution is permitted with attribution, which is what this file is.

## Source

> Lin et al., *Sci. Data* 2025 — self-driving-lab anomaly detection dataset (PDMS workflow).
> figshare: [10.6084/m9.figshare.29234663.v2](https://doi.org/10.6084/m9.figshare.29234663.v2)
> Licence: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/); the paper itself is CC BY-NC-ND
> and nothing from the paper is reproduced here.

## What was derived

- `images/`: 80 of the dataset's 1,671 photographs, unmodified, chosen by
  `scripts/make_pdms_items.py` from the annotation text alone (registered design:
  `docs/pilots_preregistration.md`; the chosen ids are also in `results/pilot1/items.json`).
- `items.json`: 100 inspection items on those 80 photographs (20 photographs appear under two
  workflow steps), with the context a model is allowed to see and the supported answer taken from
  the dataset's own annotations.

Counts and licence notes for the whole dataset: `docs/image_sources.md`.
