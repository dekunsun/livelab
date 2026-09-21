# Pre-registration: the real-plant study, rerun with the plant described correctly

Status: **registered 2026-09-21, before any item ran under the corrected description.** Changes
after this date are logged at the end.

## Why

The [real-plant study](realdata_preregistration.md) gave every model a legend of the plant's
instruments that I had written from tag names. It was wrong in four places. Five heater
temperatures were described as column temperatures, reflux and distillate were swapped, the
cooling-water flow was called a ratio, and one pressure difference was put on the wrong vessel
([deviation 5](realdata_preregistration.md)). Among the answers calling a fault-free run
anomalous, 11 of 12 (Opus 5), 37 of 37 (GPT-6 Astra) and 0 of 8 (Gemini) cite a heater
temperature.

So the study's numbers were measured on a plant the models were told something false about.
This rerun asks the same question with the description corrected.

## What changes, and what does not

**Only the legend.** `LEGEND_V2` in `livelab/realdata_prompt.py` replaces `LEGEND_V1`. Every other
sentence of the instruction is identical, and a test enforces it. Items, truth, conditions, tools,
models and one run per item are all unchanged: the same 99 items in `data/realdata/items.json`,
byte-for-byte.

The V1 results stay where they are (`results/realdata/`), and V2 writes to
`results/realdata_v2/`. Both are reported side by side, and nothing is overwritten.

## Models

`gemini-3.8-live`, `claude-opus-5` and `gpt-6-astra`: all three from the original study, now all
registered from the start.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Pv1** | Abstention on Blind stays **≤ 10%** for every model: the replication survives the corrected description |
| **Pv2** | False alerts on Control fall by **at least 5 items** (of 37) for Opus 5 and for GPT-6 Astra |
| **Pv3** | Gemini's false alerts on Control change by **fewer than 3 items** |
| **Pv4** | Among the Control false alerts that remain, **fewer than half** cite a heater temperature, for Opus 5 and GPT-6 Astra |

Why: Opus's and Astra's false alerts cited the misdescribed heaters almost without exception, so
correcting the description should remove most of them (Pv2, Pv4). Gemini's cited none, so its
false alerts should barely move (Pv3). Pv1 is the one that matters. The finding
this project reports is that models answer when nothing supports an answer. If a wrong
description was what made the blind items look anomalous, abstention should rise and Pv1 fails.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Pv1 holds | The real-plant replication survives its own harness error. The README's real-plant row is restated with V2 numbers |
| Pv1 fails | The wrong description was suppressing abstention. **The real-plant replication is withdrawn as support** for the headline, which narrows to the simulated benchmark and the probes, in the sentence that reports it |
| Pv2 fails | The heater temperatures draw alerts even when described correctly. The false-alert rate then says something about the models on real data, and is reported as such |
| Coverage below 90% for a model | That model is not read, as everywhere else |

Differences under three items are not interpreted.

## Budget

Measured on the original run: Opus 5 US$3.88 and Astra US$5.08 for 99 items each. Gemini's Live
backend reports no usage. **Cap: US$14.**

## What this cannot show

- Whether V2 is the *best* description of the plant, as opposed to a correct one. It follows the
  dataset's annotations, cross-checked where a second source exists (`data/realdata/tags.csv`).
- Anything about the camera studies. Those used V1 in every arm, and rerunning them was not chosen.

## Deviations log

None yet.
