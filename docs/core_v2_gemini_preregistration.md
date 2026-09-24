# Pre-registration: Gemini 3.8 Live, 3.8 Flash and 3.1 Pro on Core under runner v2

Status: **registered 2026-09-23, before any call below is made.** It follows
[core_runner_v2.md](core_runner_v2.md) ("each rerun registered first").

## Why

The Gemini comparison on Core ([leaderboard](results/core_leaderboard.md), "one Live model, or Live
plus a judge") was collected by runner v1, which did not save reminders or full requests and closed a
Live session at the first function call ([limitations](core_runner_v1_limitations.md)). Its counts
stand, but they cannot show whether the gap between Live (10 pairs both right) and Flash (22) or Pro
(27) is partly the harness. Runner v2 records every server message, how each session ended and every
reminder, and scores the first protocol-valid submission. One V1 run per model, the first run of
each under v2, also gives the first cause and action measures for Gemini.

## Runs

All 80 items, arm V1, one run each, function calling unforced (`--tool-choice auto`; the Live API has
no forced mode, and B and C ran unforced under v1 for parity), reminders under runner v2's fixed
rule, output under v2's default settings, to `results/core_v2/<model>/V1.auto/`:

| Arm | Model | Path |
| --- | --- | --- |
| A | `gemini-3.8-live` | Live API session (`live_item`) |
| B | `gemini-3.8-flash` | REST (`rest_item`) |
| C | `gemini-3.1-pro-preview` | REST (`rest_item`) |

Scored with `scripts/score_core_v2.py`.

## Predictions

| # | Prediction | Basis |
| --- | --- | --- |
| **Pgv1** | Every item ends with a recorded collection status; any timeout or incomplete submission is reported as such and none is scored UNKNOWN | the runner rule, not a model property |
| **Pgv2** | Flash and Pro each reproduce their v1 hidden abstentions, visible faults kept and pairs both right within 2 items (v1: Flash 30 · 22 · 22; Pro 30 · 27 · 27) | same REST path; v2 changes the record, not the request |
| **Pgv3** | Pro gets at least as many pairs both right as Flash | v1: 27 against 22 |
| **Pgv4** | No Gemini model proposes `continue` on an item whose evidence is not NORMAL | observation for Opus 5.5 under v2 was 0 · 1 · 5; stated before seeing Gemini |

No direction is predicted for Live. Its v1 counts (hidden 20, visible kept 12, pairs 10) were
collected with the session closed at the first call and reminders unrecorded.

| Outcome for Live | Reading |
| --- | --- |
| Within 2 items of v1 on all three counts | The v1 gap to Flash is not an artefact of runner v1's Live handling; it remains an observation of two configurations |
| 3 or more items better on pairs | Part of the v1 gap was the harness; the v1 Live row is reported beside the v2 row, not replaced |
| 3 or more items worse | Reported as found; one run, so not read as a trend |
| Reminders on more than 10 items, or incomplete submissions on more than 8 (coverage below 90%) | The Live row is not read |

Differences under 3 items are not interpreted. One run per model: the counts are not pass^k.
Cause and action are reported as observations, with the same definitions as for Opus 5.5.

## Budget

Flash: estimated US$1.50, capped at **US$3** (`--cap 3`). Pro: estimated US$3, capped at **US$6**
(`--cap 6`); two requests per item keep it within the paid tier's 250 requests a day for that model.
The Live API reports usage per turn under v2 but has no price in the repository; its spend falls on
the owner's Google account and is reported as tokens, not dollars.

## Deviations log

None yet.
