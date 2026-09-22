# Pre-registration: the remedy arm, and how stable Core's counts are

Status: **registered 2026-09-22, before any V1R or repetition item ran.** The Core suite itself ran
earlier ([results](results/core_leaderboard.md)); this follow-up is registered before its own runs.
Changes after this date are logged at the end.

## Why

Two loose ends from Core.

1. The project's revised recommendation has two halves: *state what cannot be verified*, and *keep
   anomaly rules running on what can*. The first half was tested and over-reached: told the gap,
   no model kept more than 20 of 30 faults the remaining sensors showed. The untested question is
   whether **wording alone can close that gap**: if the same sentence also names the sensors that
   remain installed, does the model keep the fault it can see?
2. Every Core number is **one run**. Nothing yet says how much these counts move when the same arm
   is rerun unchanged. The project's standing rule (differences under 3 items are not interpreted)
   was chosen a priori, not measured.

## The questions

**Q1.** With the remedy sentence, do models keep the visible faults they dropped under V1, without
losing hidden-twin abstention?

**Q2.** Across three identical runs of V1, how far do the headline counts spread?

## Arms and items

- **V1R**: Core's 80 items, with V1's sentence extended by one clause naming the required sensors
  that remain installed: *"… so the atmosphere cannot be verified with the installed sensors. The
  control thermocouple and the tube pressure gauge are installed and reporting."* Built by
  `livelab.core.remedy_sentence`; on the 20 guard items nothing is missing and the text is
  identical to V1. One run per item.
- **Repetitions**: the V1 arm rerun twice more per model (`--rep 1`, `--rep 2`), same script and
  inputs; provider-side sampling is the only source of variation. With the original run, three
  runs per model.

## Models

`claude-opus-5` and `gpt-6-astra`: the two models that follow a stated gap, which is what the
remedy clause modifies. Gemini's answers moved in every direction under the added sentence, so a
V1R change there could not be attributed to the clause; it is excluded from Q1 and may be run later
as exploratory only.

## Measures

For V1R and for each repetition: hidden abstains (of 30), visible faults kept (of 30), pairs both
right (of 30), needless abstention (of 20). V1R is read against each model's original V1 run.
Coverage per arm, not read below 90%.

## Predictions (registered)

| # | Prediction | Basis |
| --- | --- | --- |
| **Pm1** | Under V1R, each model keeps **at least 5 more** visible faults than under V1 (Opus 5 ≥ 25/30, Astra ≥ 17/30) | every dropped answer already described the fault; the clause removes the stated reason for withholding |
| **Pm2** | Under V1R, hidden abstention stays **within 5 items** of V1 (Opus 5 ≥ 21/30, Astra ≥ 25/30) | the gap is still stated |
| **Pm3** | Under V1R, needless abstention ≤ 2/20 | guard text is identical to V1, which gave 0/20 |
| **Pm4** | Across the three V1 runs, every headline count's spread (max − min) is **≤ 3 items**, both models | the standing no-interpret band |

## How results will be read

| Outcome | Reading |
| --- | --- |
| Pm1 and Pm2 hold | Naming the working channels recovers detection without losing abstention. The recommendation is refined: state the gap **and the working channels**. One wording, simulated; independent anomaly rules remain the default for a real system |
| Pm1 fails | Wording is not enough even at its most explicit. The system must keep detection itself; principle 2 stands, now with direct evidence |
| Pm2 fails | The clause over-reassures: models rule on hidden faults too. The clause is withdrawn |
| Pm3 fails | The sentence family itself causes abstention on healthy runs |
| Pm4 holds | Single-run counts move within the band the project already refuses to interpret; existing readings stand |
| Pm4 fails | The affected counts are reported as ranges everywhere they appear, and any conclusion resting on a difference smaller than the observed spread is withdrawn |

Differences under 3 items are not interpreted.

## Budget

Per model: V1R 80 calls + repetitions 160 calls = 240. Both models ≈ **US$8 (Opus 5) + US$12
(Astra) ≈ US$20**, estimated from the Core runs. The runner's meter counts each model's
**cumulative** Core spend, including the first suite (US$8.01 and US$11.88), so the caps are set
at US$30 (Opus 5) and US$40 (Astra).

## What this cannot show

- **One remedy wording**; a structured-field version is untested.
- **Repetitions measure sampling noise on the same items**, not a population rate. That would need
  a new item draw.
- **Gemini is not read** for Q1.

## Deviations log

1. **2026-09-22, Astra.** The OpenAI account ran out of credit during rep 1 (72 of 80 saved);
   after a top-up the same script filled the rest. Separately, an interrupted run chain and its
   resume briefly ran in parallel: 20 rep-2 items failed on rate limits and were filled by a later
   single run, and one result file (`V1.rep2/core_leak_ap_10__hidden.json`) was written twice —
   repaired by keeping its first complete record. No answer was altered.
2. **2026-09-22, Opus 5.** rep 2 was collected in two pieces around the same account's earlier
   credit interruption pattern; same script, same inputs throughout.
