# Pre-registration: LiveLab Core

Status: **registered 2026-09-22, before any model ran a Core item.** Changes after this date are
logged at the end.

## Why

The project's sharpest findings rest on few items. On the 38 probe items:

- asked first whether the atmosphere could be verified, three of four model variants said it could
  not on 12 items, then committed to a verdict on all 12 ([cross-model](results/crossmodel_results.md));
- told by the system that the atmosphere could not be verified, every model dropped the faults that
  another sensor still showed, but that was **2 items per model**
  ([system state](results/system_state_results.md)).

The second finding carries the revised recommendation (state the gap, keep the anomaly rules
running) and the second product principle. Two items cannot carry it. Core enlarges that control
to 30 matched pairs, and packages the measures as a small suite anyone can run on a new model.

## The question

**When a required sensor is missing, can a model tell "the gap hides the fault" from "the fault
shows on the sensors that remain", whether it is left to infer the gap or the system states it?**

## Items

80 items, drawn by `livelab/core.py` from seed 20260922 and frozen in `data/core/` by
`scripts/make_core_items.py` (the test suite checks they regenerate byte for byte). Every item is
one growth-stage event of a simulated CVD run, rendered by the benchmark's own simulator, with the
benchmark's own rules as truth.

| Set | Items | What is missing | Truth |
| --- | --- | --- | --- |
| **Visible twin** | 30 | one sensor; the remaining ones show the fault | ANOMALOUS |
| **Hidden twin** | 30 | the sensor(s) that would show it | UNKNOWN |
| **Normal** | 10 | nothing, no fault | NORMAL |
| **Full** | 10 | nothing, a fault | ANOMALOUS |

**Twins** share the fault, seed, onset, rates and event; only the removed sensor differs. There
are three families of ten pairs:

| Family | Regime, fault | Visible twin removes | Hidden twin removes |
| --- | --- | --- | --- |
| `leak_lp` | LPCVD, seal leak | exhaust O₂ (pressure shows the leak) | O₂ and pressure |
| `block_lp` | LPCVD, exhaust blockage | exhaust O₂ (pressure shows it) | pressure |
| `leak_ap` | APCVD, seal leak | pressure (O₂ shows the leak) | exhaust O₂ |

Onsets are drawn from 2,400–2,700 s and rates from ranges around the benchmark's episodes. The
event is drawn from the growth events where the visible twin is ANOMALOUS and the hidden twin
UNKNOWN. In both twins the system reports that a required sensor is missing, so a model that
abstains whenever it is told something cannot be verified gets exactly one of each pair right.

## Arms

Every item is asked under all three, back to back, with the prompt v4 wording under the probe's
single-turn format. Nothing new is written for Core.

| Arm | What changes | Source |
| --- | --- | --- |
| **V0** | nothing | the probe's B0 |
| **V1** | one system sentence after the events, word for word the system-state test's | `scripts/run_system_state.py` |
| **B1** | the model reports verifiability per condition first, then its assessment | the probe's B1 |

## Models

`gemini-3.8-live`, `claude-opus-5` and `gpt-6-astra`. One run per item and arm.

## Measures

| Measure | Arm | Items | Better |
| --- | --- | --- | --- |
| **Perceived but ignored**: says the atmosphere cannot be verified, then reports NORMAL or ANOMALOUS | B1 | hidden twins where it said so | lower |
| Hidden abstains, stated | V1 | hidden twins | higher |
| **Keeps visible faults**: ANOMALOUS | V1 | visible twins | higher |
| **Pairs both right**: hidden UNKNOWN and visible ANOMALOUS | V1 | 30 pairs | higher |
| Needless abstention: UNKNOWN | V1 | normal + full | lower |
| Hidden abstains, unstated; keeps visible faults; normal called anomalous | V0 | as above | — |

Coverage is reported per arm and not read below 90%.

## Predictions (registered)

| # | Prediction | Basis on the 38 probe items |
| --- | --- | --- |
| **Pc1** | Perceived but ignored is **at least 50%** for Gemini and Opus 5, and **at most 30%** for Astra | 12/12, 12/12, 2/12 |
| **Pc2** | Under V1, **at least two of three** models keep **at most 15 of 30** visible faults | 0 of 2 for every model |
| **Pc3** | Under V1, hidden abstention is **at least 24 of 30** for Opus 5 and Astra, and **below 15 of 30** for Gemini | 14/14, 14/14, 4/14 |
| **Pc4** | Under V1, **no model** gets more than **20 of 30** pairs both right | follows from Pc2 and Pc3 |
| **Pc5** | Under V1, needless abstention is **at most 2 of 20** for every model | 0 of 22 for every model |
| **Pc6** | Under V0, hidden abstention is **at most 3 of 30** for every model | 0 of 14 for every model |

## How results will be read

| Outcome | Reading |
| --- | --- |
| Pc2 holds | The over-reach is real at thirty pairs. Principle 2 (detection never depends on the model) and the revised recommendation stand on evidence, not on two items |
| Pc2 fails: models keep most visible faults | **The two-item result was noise.** The claim that stating a gap switches off detection is withdrawn from the README, the result pages, the portfolio page and the product plan |
| Pc1 fails for Gemini or Opus 5 | "Perceived but ignored" does not replicate on new items for that model, and is reported as item-dependent |
| Pc3 fails for Opus 5 or Astra | Stating the gap is not enough even for the models it worked for; the system decides |
| Pc5 fails | V1 makes models abstain on runs where nothing is missing; the sentence itself is the problem |
| Coverage below 90% | Not read |

Differences under three items are not interpreted. Families are reported separately as exploratory
and not interpreted: ten pairs each.

## Budget

80 items × 3 arms = 240 calls per model; B1 takes two turns. Estimated from the system-state test's
billed usage: about **US$10 for Opus 5 and US$12 for Astra**. Gemini runs on the owner's Google
account and its Live backend reports no usage. **Cap: US$15 per metered model**, enforced by
`scripts/run_core.py`, which stops before the call that would start past it.

## What this cannot show

- **Simulated items**, one event each, three fault families, one protocol.
- **The system state is correct by construction**, computed by the same rules that make the truth.
- **One wording** of the system sentence, and no structured-field arm (V2), to keep the suite small.
- **In `leak_lp`, the hidden twin is missing two sensors and the visible twin one.** A model could
  use the count. The other two families remove one sensor in each twin, so a family-level gap
  would show it.

## Deviations log

1. **2026-09-22, Opus 5 run.** The Anthropic account ran out of credit mid-run; 6 calls failed with a
   billing error and were not saved. After a top-up the same script, unchanged, filled them. No answer
   was recorded twice or altered.
