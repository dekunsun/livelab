# Single-image inspection test: results

Registered in [pdms_inspect_preregistration.md](../pdms_inspect_preregistration.md). Gemini 3.8 Flash,
one run per arm, the 40 flip items (20 photographs, two workflow steps each). Scored with
`scripts/run_pdms_inspect.py score --model gemini-3.8-flash`; records in `results/pdms_inspect/`.

## Counts

| | C1 (control) | C1I (inspection tool) |
| --- | --- | --- |
| Items right, of 40 | 35 | 36 |
| Photographs with both steps right, of 20 | 15 | 18 |
| UNKNOWN answers | 0 | 1 |
| Items with no valid answer | 0 | 0 |
| Items on which the tool was used | — | 40 (1 view: 17, 2 views: 14, 3 views: 9) |
| Spend | US$0.12 | US$0.37 |

For reference, on the same 20 photographs: Gemini 3.8 Live, seeing the photograph, both steps right
on 14; a trained specialist on 6 ([pilot1_results.md](pilot1_results.md),
[specialist_results.md](specialist_results.md)).

## Predictions

| # | Prediction | Result | Held |
| --- | --- | --- | --- |
| Pi1 | C1I uses the tool on at least 20 of 40 items | 40 | yes |
| Pi2 | C1I at least 3 more items right than C1 | +1 | **no** |
| Pi3 | C1I at least 2 more photographs with both steps right | +3 | yes |
| Pi4 | C1I raises UNKNOWN by no more than 2 | +1 | yes |

**Reading, by the registered rule:** the item difference is within 2, so this is **no evidence that
magnification helps on these photographs**. Pi3 holding does not change that; the rule needs Pi2 and
Pi3 together.

## Where the arms differ

The net +1 item is three items fixed and two broken:

| Item | Truth | C1 | C1I |
| --- | --- | --- | --- |
| flip04_abn | ABNORMAL | NORMAL | ABNORMAL |
| flip09_abn | ABNORMAL | NORMAL | ABNORMAL |
| flip11_nor | NORMAL | ABNORMAL | NORMAL |
| flip02_nor | NORMAL | NORMAL | ABNORMAL |
| flip13_abn | ABNORMAL | ABNORMAL | UNKNOWN |

Both broken items are on photographs C1 already got wrong at the other step, which is why the
photograph count moved more than the item count. flip02_abn and flip13_nor are wrong in both arms.

## Limits

- **Little room.** The control already had 35 of 40 right, so a gain of 3 items needed 3 of the 5
  remaining. VISTA's single-image gain (41.0% to 63.2% on BabyVision) started from a much lower base.
- **Resolution.** Every photograph is 640 × 480; a magnified view adds pixels by interpolation, not
  detail. The "within one image" half of evidence on demand is better tested on high-resolution frames.
- One model, one run per arm, 40 items: a screening test, not a product claim. The tool tripled spend.
