# Lessons learned

What went wrong while building and running LiveLab, what it taught, and where the record is.
Every item below was found either by a test, a smoke test or a pre-registration check, or by
reading a model's own stated evidence before drawing a conclusion. Each fix and its reason is
recorded in the design doc, the pre-registration's deviation log, or the commit history, and the
results from before each fix are kept in `results/` and `docs/pilot/`.

## A. Evaluation design fails quietly

| What happened | How it was found | Lesson |
| --- | --- | --- |
| Replay files carried the episode name (e.g. `cvd_seal_leak_lpcvd`), which gives the answer away | A test that scans replays for revealing words | The most dangerous evaluation bug is a leak, and nothing crashes. Test for it explicitly |
| With every relevant sensor removed, a leak run and a clean run delivered identical evidence but had different "correct" answers | Designing the sensor-removal cascade | **Same evidence, same answer.** Truth must depend only on what the model was shown. Several later fixes (splitting detection and false alerts by evidence, deriving correct actions per event) follow from this |
| The truth rule itself was wrong three times: too few reference runs (4.5% false positives), blind to within-run drift, and missing sustained moderate departures | Mock observers raising "premature" alarms that were actually justified; declared expectations failing | The ground-truth rule is a model too. Calibrate it on normal runs only, before any model runs, and test it |
| Scorer bugs: first-action quality mixed timing with quality; `none` was counted as an abstention; arms that never see the image were asked to judge it | Some by mock observers, some only by real model data | Validating metrics on mock observers catches a lot, but not everything. Real data exposes cases you did not imagine |
| Different seeds gave identical reports on 57 of 58 events | Comparing two pilot runs | Repeating a replay mostly re-samples the same answer. Variance has to come from the evidence (episode variants), which also saved free-tier quota |

## B. Contract ambiguity vs real model behaviour

Four times, what looked like a model failure was an ambiguity in the task:

| Version | Apparent failure | Actual cause |
| --- | --- | --- |
| v1 | Declared the scientific result `NEGATIVE` mid-growth | `NEGATIVE` was never defined |
| v2 | Flagged a missing sensor as `ANOMALOUS` | "unavailable" reads as "broken" |
| v3 | Still `ANOMALOUS` + shutdown | The manifest said the sensor was "required", so its absence is a protocol violation |
| (open) | Called multilayer and oxide micrographs "supporting" | The target (a monolayer) was never stated; recorded as a limitation |

Lessons:

1. **Read the model's cited evidence before judging.** Each time, its reading was defensible under
   the contract we had written.
2. **Do not tune until the model looks good.** Wording was frozen at v4. Every change is recorded
   with its reason, and every version's logs are kept.
3. **When ambiguity is suspected, test for it instead of guessing.** Probe B2 stated the definition
   explicitly and still got 0 of 14 abstentions. That separates "the task was unclear" from "the
   model will not do it".
4. **A result that holds under every wording is the most credible one.** "Never answers `UNKNOWN`"
   held under v2, v3 and v4.

## C. Pre-registration

- **Registering first removes the temptation to explain results afterwards.** The probe's reading
  rules said in advance that if the explicit definition did not help, that would be the strongest
  evidence of a model-level tendency. That is what happened, and no after-the-fact story was
  needed.
- **Generating the items exposed two design flaws before anything ran.** The detectability items
  were 40 "yes" and 8 "no", so an always-"yes" model would have passed an 80% bar; the fix was
  balanced accuracy. The question wording ("during growth") also did not match the scope of the
  truth. Both were logged as deviations before any probe ran.
- **Changing the plan mid-study is fine if it happens before results and is written down.** The
  staged Extended Thinking run is an example.

## D. A harness is not portable between models

Adding Gemini 3.8 Live Extended Thinking broke four assumptions that held for the standard Live
model:

| Symptom | Cause | Fix |
| --- | --- | --- |
| Calls rejected | Only NON_BLOCKING function calls are supported, and a thinking level is required | Model-specific tool declarations; HIGH thinking, recorded per run |
| A report landed on the next event | Reasoning continues in the background; `turn_complete` does not mean idle | Send the next event only after this event's own report |
| 10-minute stalls | Sometimes no `turn_complete` follows a report | Wait at most 30 s after a report |
| Reasoning never finished; no answer | **The harness's reminders interrupted it.** The docs say a new client message interrupts generation; the consequence was missed | No reminder for 240 s; never save a harness-caused non-answer |

Lessons:

1. **Each model family needs its own adapter and its own tests.** Fake sessions reproduce each
   failure mode (late reports, silence after answering, background reasoning), so the harness can
   be shown not to hang or misattribute.
2. **Smoke tests pay for themselves.** All four problems surfaced in 5-event smoke tests, before
   any full run was wasted.
3. **Measure before planning.** The smoke test measured about 14 s per event and about 1.7k tokens
   of context growth per event at HIGH thinking. That showed a full benchmark run would take 9+
   hours and approach the context limit, so the plan changed to a staged probe first.

## E. Cost structure shapes the design

- **The Live API counts the whole accumulated context on every turn,** so cost grows with the
  square of the event count. The response was 120 s cadence and compact event JSON. The cost
  estimate was wrong twice: once by missing the square law, and once by missing that the model's
  own outputs also accumulate.
- **Cumulative input was about 0.5M tokens per replay, but the final context only about 16k.** On
  standard APIs the repeated history can be served from a prompt cache at 5–10% of the input
  price, which makes a cross-model comparison affordable.
- **Consumer subscriptions are not API access.** Evaluation runs need developer API accounts with
  spending caps.

## F. What the model taught us

1. **Context fixes detection.** Normal-run reference curves took detection from 0.50 to 0.90 and
   false alerts from 0.83 to 0.00–0.11.
2. **Nothing tried fixes calibration.** `UNKNOWN` was answered 0 times in 1,986 events. More
   information made the model more confidently `NORMAL` (556 → 656 → 661 of 662).
3. **It knows it cannot see, but the verdict does not change.** It says "cannot verify", then
   reports `NORMAL` (12 of 12), even under an explicit instruction.
4. **Given reference curves, it compares with the mean and ignores the spread.** Both C-context
   false alerts were readings less than 2 σ from the mean.
5. **Recognising is not acting.** Action latency ran 11–19 events after an anomaly was detectable.

Product implications:

- Instrument baselines are cheap, high-value context.
- "Cannot verify" must be a system state beside the model's verdict, never left to the verdict
  itself.
- Asked as its own question, verifiability was answered correctly 91% of the time. The information
  exists, but it has to be asked for separately.
