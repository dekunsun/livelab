# Attribution: batch distillation data

`items.json` in this directory is **derived from real plant data** published under
**CC BY 4.0**. Redistribution is permitted with attribution, which is what this file is.

## Source

> Arweiler, Justus; Jungjohann, Indra; Werner, Jennifer; Muraleedharan, Aparna; Schmid, Jochen; Leitte, Heike; Burger, Jakob; Münnemann, Kerstin; Bortz, Michael; Jirasek, Fabian; Hasse, Hans.
> *Batch Distillation Data for Developing Machine Learning Anomaly Detection Methods*.
> Zenodo, version 1.1.3, 2026-09-02.
> DOI: [10.5281/zenodo.22250958](https://doi.org/10.5281/zenodo.22250958)
> Licence: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/)

## What was derived, and what was not

- `items.json` carries **windows of the published 1 Hz sensor readings**, rounded to three
  decimals, re-serialised into this project's compact event format, plus the condition and the
  supported answer taken from the record's own expert annotations.
- Values are the authors' measurements. Nothing was simulated, interpolated or generated.
- The record's **audio, video, NMR and raw spectra are not used and not redistributed**. Only the
  small tabular parts were ever downloaded.
- The full record is **not** committed here: `data/external/` is gitignored, and
  `scripts/fetch_batch_distillation.py` fetches what is needed.

## What this project did with it

A pre-registered replication of its own central finding on real plant data — design in
[docs/realdata_preregistration.md](../../docs/realdata_preregistration.md), results in
[docs/results/realdata_results.md](../../docs/results/realdata_results.md). The dataset's expert
annotations are the ground truth; this project's own rules were deliberately kept out of it.

**The authors are not associated with this project and have not reviewed it.**
