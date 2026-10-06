# Pre-registration: does model-directed magnification help on single inspection photographs?

Status: **registered 2026-10-05, before any scored call** (approved by the owner).

## Why

The product plan's evidence-on-demand requirement (PRD FR14) bundles two abilities:
- revisiting earlier evidence across time;
- looking closer at part of one image.

VISTA (arXiv 2610.02200) separated the second with a single-image test (BabyVision, maze and
line-tracing items), where its inspection tools raised accuracy from 41.0% to 63.2%. This study does
the same for LiveLab's laboratory photographs. It isolates **looking closer within one image**,
with nothing to revisit, at the lowest cost that can answer the question.

## Items and arms

- **Items.** The 40 "flip" items of the PDMS inspection set (`data/pdms_pilot/items.json`, Lin et al.
  2025, CC BY 4.0):
  - 20 photographs, each judged at two workflow steps whose correct answer differs;
  - every photograph is 640 × 480.
  - On these items Gemini 3.8 Live, seeing the photograph, got both steps right on 14 of 20, and a
    trained specialist on 6 of 20.
- **Model.** Gemini 3.8 Flash (REST, the paid tier). It is chosen for cost; there is no earlier Flash
  run on these items, so the control arm is the baseline.
- **Arms.** Both arms use the same loop (`livelab/inspect_tool.py`), up to 8 requests, the fixed
  reminder rule, and the same item text and photograph. They differ only in the inspection tool and
  the one sentence that offers it.

| Arm | Tools | Instruction |
| --- | --- | --- |
| C1 (control) | `report_inspection` | the pilot's inspection instruction |
| C1I | `inspect_region` (up to 3 magnified views, long side 1,024 px) and `report_inspection` | the same, plus one sentence offering the tool |

- **Runs.** One run per arm. Smoke first: 3 items per arm, sent to `results/pdms_inspect_smoke/`,
  pipeline checks only and never scored.

## What is counted

On fixed denominators, for each arm:
- items right, of 40;
- photographs with both steps right, of 20;
- UNKNOWN answers;
- items with no valid answer, which count as wrong;
- items on which the tool was used (C1I only);
- spend.

Scored with `scripts/run_pdms_inspect.py score`.

## Predictions

| # | Prediction |
| --- | --- |
| **Pi1** | C1I uses the tool on at least 20 of 40 items |
| **Pi2** | C1I gets at least 3 more items right than C1, of 40 |
| **Pi3** | C1I gets at least 2 more photographs with both steps right than C1, of 20 |
| **Pi4** | C1I does not raise UNKNOWN answers by more than 2 |

**How the result is read, fixed in advance:**

| Result | Reading |
| --- | --- |
| Pi2 and Pi3 hold | Looking closer helps on these photographs; evidence on demand keeps its "within one image" half, to be confirmed on a stronger model before it is relied on |
| Within 2 items either way | No evidence that magnification helps here. At 640 × 480 the whole image may already carry what the model can use; the "across time" half is tested separately |
| C1I worse by 3 or more | Reported as found: the tool can distract. One run, so not a mechanism |

Differences under 3 items are not interpreted; this is the study's reading rule, not significance.
One run per arm, one model, 40 items: a screening test, not a product claim.

## Budget

- **Estimate:** under US$1. Flash is priced at US$0.75 and US$3.75 per million input and output
  tokens; there are about 80 items plus magnified views.
- **Cap:** `--cap 3`.

## Deviations log

(none yet)
