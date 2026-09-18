# Image sources

This is a source-level registry. Per-image rows go into `data/images/manifest.csv` only after the
figure has been viewed, its caption checked for "reproduced from" credits (third-party panels are
not covered by the article license), and its outcome class labeled by a person.

**License checked by** says where each license was confirmed.

- **EPMC**: Europe PMC `license` field, checked 2026-09-18.
- **Crossref**: Crossref license URL, checked 2026-09-18.
- **API**: repository API (figshare / Zenodo / GitHub), checked 2026-09-18.
- **agent**: reported by a research agent from the article page and not yet re-checked. Re-check
  before use.

Use rules:

- **Free tier**: only CC BY, CC0 or MIT. Free-tier inputs are used to improve Google products.
- **Paid tier**: NC and NC-ND sources may be sent here for non-commercial evaluation with
  attribution.
- **Repository**: image bytes are committed only for CC BY, CC0 or MIT. NC sources are listed
  by DOI and figure only.

## CVD growth of 2D TMDs: post-growth characterization

Outcome classes:

- a: monolayer success
- b: no or sparse nucleation
- c: multilayer / bulk
- d: small domains / dense nucleation
- e: oxide or residue
- f: parameter sweep

| # | Source | DOI | License | Checked by | Figures → classes | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MoS₂ via sulfurization of MoO₂ precursor, *Nanomaterials* 2021 | 10.3390/nano11102642 | CC BY | EPMC | Fig 2, 3 (MoO₂ mass), 4 (Ar flow, oxide stripes by Raman), 5, 7, 8 → a b d e f | Best single source |
| 2 | Carrier-gas flow rate, monolayer WSe₂, *Materials* 2024 | 10.3390/ma17102190 | CC BY | EPMC | Fig 2a–i → a c d e f; Fig 3 Raman/PL | Flow sweep on SiO₂/Si, from unreacted particles to decomposition |
| 3 | Monolayer/bilayer WSe₂ from liquid precursor, *Nanomaterials* 2024 | 10.3390/nano14242021 | CC BY | EPMC | Fig 1a–d → a b f; Fig 2a–c → c f | Concentration and temperature sweeps |
| 4 | Reverse-flow CVD MoSe₂, *Nanomaterials* 2020 | 10.3390/nano10010075 | CC BY | EPMC | Fig 2a–h → a b d f; Fig 3 | Includes nucleation-density statistics |
| 5 | Large-scale WS₂ monolayers, *RSC Adv.* 2019 | 10.1039/c9ra06219j | CC BY | EPMC | Figs 2–4 → a c | Monolayer to bulk in one image, with Raman/PL |
| 6 | Substrate placement for MoS₂, *Crystals* 2025 | 10.3390/cryst15010059 | CC BY 4.0 | Crossref | Fig 4c,d → f | Classes per position not yet checked |
| 7 | Multilayer MoSe₂ TFT, *Sci. Rep.* 2015 | 10.1038/srep15313 | CC BY 4.0 | Crossref | Fig 1b,c → c | |
| 8 | MoS₂/MoO₂ microflowers, *Sci. Rep.* 2022 | 10.1038/s41598-022-26185-z | CC BY 4.0 | Crossref | Fig 1c, 2, 5 → c e | Oxide-rich growth |
| 9 | Single-crystal WS₂ monolayer, *Micromachines* 2021 | 10.3390/mi12020137 | CC BY | EPMC | Fig 1a → a | Clean positive control |
| 10 | Submillimeter WSe₂ / MoSe₂, *Materials* 2023 | 10.3390/ma16134795 | CC BY 4.0 | agent | Fig 2 → a | Positive control |
| 11 | Barrier-assisted MoS₂, *Nanoscale Adv.* 2020 | 10.1039/d0na00524j | CC BY-NC | EPMC | Fig 2 → a c e; Fig 3 → f | Paid tier only; mostly on sapphire |
| 12 | Processing parameters, MoSe₂, *RSC Adv.* 2022 | 10.1039/d2ra00387b | CC BY-NC 3.0 | agent | Fig 1 → a f | Paid tier only; few failures |
| 13 | Precursor ratio and MoS₂ morphology, *Crystals* 2026 | 10.3390/cryst16080480 | CC BY | agent | Fig 3 → dendritic | |
| 14 | Metatungstate CVD WSe₂, *Crystals* 2024 | 10.3390/cryst14020184 | CC BY 4.0 | agent | Fig 2 → c, e? | Substrate corrosion |

**Labeled dataset.** *Identifying optical microscope images of CVD-grown 2D MoS₂ by CNNs*,
PeerJ CS 2024, 10.7717/peerj-cs.1885.

- License: CC BY, checked via EPMC.
- Real MoS₂-on-SiO₂/Si micrographs in the article's supplementary files, in four classes: normal;
  normal + overlapped; non-triangular monolayer; overlapped / non-triangular / multilayer.
- Candidate training data for arm B's CVD image classifier. The supplementary files have not
  been opened yet.

**DeepMind arXiv 2608.26701.**

- License: CC BY-NC-ND 4.0, checked on the arXiv abs page.
- Fig 3b/3d: successful MoS₂ / WS₂ / MoSe₂. Fig A5a: failed MXene substrate.
- Paid tier only; listed here but not redistributed.

**Excluded by license (NC-ND, although the science is a strong fit):** ACS Omega
10.1021/acsomega.2c07408, 10.1021/acsomega.2c03108, 10.1021/acsomega.4c10312. Also excluded:
arXiv papers under the non-exclusive license.

## Liquid handling and lab operations (cross-domain control)

| Source | Where | License | Checked by | Covers | Notes |
| --- | --- | --- | --- | --- | --- |
| Lin et al. SDL anomaly dataset, *Sci. Data* 2025 | figshare 10.6084/m9.figshare.29234663.v2 | CC BY 4.0 (dataset); paper CC BY-NC-ND | API | 1,671 images / 2,788 pairs: Missing 547, Inoperable Object 554, Transfer Failure 447, Unfulfilled Object 215, Environmental Disturbance 20, normal 1,005 | Counts recomputed from the GitHub copy of `annotation.json` and they match paper Table 2. 80 normal-labeled records mention a small spill, which makes them "odd-looking but normal" candidates. Single frames, not sequences. |
| LabPics 2 (Chemistry, Medical) | Zenodo 4736111 | MIT | API | Foam annotated as its own phase; liquids, solids, suspensions | Candidate foaming images. The scenario context is what makes the foam a failure. |
| Vector-LabPics V1 | Zenodo 3697452 | MIT | API | Vessel and material phases | Some photos credited to third parties; check copyright per image. |
| HeinSight4.0 | Zenodo 14630321, 15605098 | CC BY 4.0 | API | Frames from real experiment videos; classes Empty, Residue, Homogeneous, Heterogeneous, Solid | Liquid level shown by the air/liquid boundary; no foam or bubble class |

**No licensed source for tip bubbles yet.** The only real set (arXiv 2512.02018, 3,202 images
of an ABLE Labs NOTABLE) has no license on its repository, checked via the GitHub API. Using it
requires the authors' permission. Also rejected: the HeinSight 2.0 Drive data (no license
stated), foam-sensing data from SLAS Technology 2021 (not public), and the Frontiers 2023
liquid-transfer videos (private).
