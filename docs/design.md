# LiveLab design

**LiveLab: Multimodal Lab Observer.** A controlled benchmark for whether scientific agents can
distinguish what is wrong, what the current sensors actually support, and what remains unknowable
during a physical experiment.

> More modalities do not always mean more observability. In some stages of a physical experiment,
> the scientifically relevant state is simply not observable yet.

At every observation event the agent answers four questions, in this order:

1. **Did something go wrong?**
2. **What kind of thing went wrong?**
3. **Do I actually have enough evidence to know?**
4. **What should I do next?**

The claim is **multimodal failure assessment in simulated live lab episodes**. It is *not* real-time
failure detection in a real lab. Telemetry is author-constructed, images are real but taken from
published sources, and their pairing is constructed (§8).

This document is the Phase 1 specification. It fixes the output contract, the ground-truth rules
and the metrics **before** any model is run, so that results cannot shape the definitions. Items
marked **TBD** are listed in §13.

---

## 0. Two parts that never mix

| | **Research benchmark** | **Active Live demo** |
| --- | --- | --- |
| Goal | Fairness and reproducibility | Show what an AI-native lab workstation feels like |
| Evidence | **Frozen replay**: every condition receives the identical evidence stream at identical times | Closed loop: the agent's actions change what happens next |
| Agent can | Call `report_assessment()`, which includes a *proposed* action. Nothing it does changes later evidence | Call `pause_run()`, `request_diagnostic()`, `ask_human()`; talk by voice; see images and telemetry |
| Voice | Not an input; spoken output is logged but not scored | The main interface |
| Output | The metrics in §5 | A recorded demo; **no metrics are reported from it** |

The separation matters. If arm A chose to retry and arm C chose to measure O₂, the two would
receive different evidence from that point on, and they could no longer be compared. The demo
reuses the benchmark's simulator and episodes, but its runs are never mixed into the results.

In both parts, Gemini 3.8 Live's role is the same: an **observability-aware scientific agent**.

## 1. Two testbeds, two jobs

| Testbed | Its job | Why it suits that job |
| --- | --- | --- |
| **2D-materials CVD** | **Observability and abstention** | The sample cannot be seen during growth. Telemetry reports process health, not morphology. The visual evidence arrives only at post-growth characterization |
| **Liquid handling** | **Raw physical vision** | Anomalies are visible in the frame while the workflow runs |

CVD is not expected to show that vision helps most. Its value is that it makes the unobservable
explicit. Liquid handling asks one question only: when a physical anomaly is actually visible, does
native multimodal input help? It will not be expanded.

## 2. Output contract

Execution and scientific evidence are separate questions. An experiment that did not support its
hypothesis is not a malfunctioning experiment system.

| Field | Values | Answers |
| --- | --- | --- |
| `execution_state` | `NORMAL` · `ANOMALOUS` · `UNKNOWN` | Is the instrument / process executing as the protocol expects? |
| `scientific_evidence` | `SUPPORTING` · `NEGATIVE` · `INCONCLUSIVE` · `NOT_YET_AVAILABLE` | What does the current evidence mean for the scientific question? |
| `attribution` | `instrument_process` · `sample_handling` · `software` · `undetermined` · `none` | If execution is anomalous, which layer is at fault? |
| `specific_cause` | a fault from the library (`seal_leak`, `exhaust_blockage`, `thermocouple_drift`, `mfc_stuck`, `stale_status`) · `other` · `undetermined` · `none` | Which specific fault? A layer can be known while the specific cause is not |

The meaning of each `scientific_evidence` value depends on execution:

- **SUPPORTING**: characterization shows the target outcome.
- **NEGATIVE**: execution was `NORMAL`, and characterization shows the target was not achieved.
  This is evidence about the recipe or hypothesis, and it is the project's most important negative
  control. Calling it a malfunction counts as a false alert.
- **INCONCLUSIVE**: characterization exists but cannot count as evidence about the recipe, because
  execution was `ANOMALOUS` or the image is ambiguous. The real case is DeepMind's MXene
  reproductions: 3/26 succeeded before a seal / oxygen leak was fixed and 17/25 after, so the early
  failures were not evidence against the recipe.
- **NOT_YET_AVAILABLE**: no characterization exists yet. In CVD this is the only correct value
  during growth.

Gemini 3.8 Live has no structured output, so every judgment is a function call. Every condition
gets the same declaration.

```json
{
  "name": "report_assessment",
  "description": "Report your current judgment of the run. Call exactly once after every observation event.",
  "parameters": {
    "type": "object",
    "properties": {
      "execution_state":     {"type": "string", "enum": ["NORMAL", "ANOMALOUS", "UNKNOWN"]},
      "scientific_evidence": {"type": "string", "enum": ["SUPPORTING", "NEGATIVE", "INCONCLUSIVE", "NOT_YET_AVAILABLE"]},
      "attribution":         {"type": "string", "enum": ["instrument_process", "sample_handling", "software", "undetermined", "none"]},
      "specific_cause":      {"type": "string", "enum": ["seal_leak", "exhaust_blockage", "thermocouple_drift", "mfc_stuck", "stale_status", "other", "undetermined", "none"]},
      "evidence": {
        "type": "array",
        "items": {"type": "object", "properties": {
          "channel": {"type": "string"},
          "t_sim_s": {"type": "number"},
          "observation": {"type": "string"}
        }, "required": ["channel", "observation"]}
      },
      "missing_evidence": {"type": "string", "description": "For any UNKNOWN / NOT_YET_AVAILABLE / INCONCLUSIVE: what observation would resolve it, and when it becomes available."},
      "proposed_action": {"type": "string", "enum": ["continue", "discriminating_test", "pause", "safe_shutdown", "call_human"]}
    },
    "required": ["execution_state", "scientific_evidence", "attribution", "specific_cause", "evidence", "proposed_action"]
  }
}
```

In the benchmark, `proposed_action` is recorded but never executed.

## 3. Frozen evidence replay

An **episode** is a fixed, pre-rendered stream of **observation events**. Each event contains:

- a telemetry update;
- the device manifest (§3.2);
- protocol state: the current step and the expected value of every channel;
- any image that becomes available at that time.

**Every observation event is followed by a mandatory `report_assessment()`.** The harness does not
send the next event until that report has arrived.

- **`t_alarm`** is the simulated time of the observation event after which the model first reported
  `execution_state=ANOMALOUS`.
- **Wall-clock time is ignored.** Network and audio latency cannot contaminate any metric.
- **Silence is never read as a judgment.** "The model didn't speak" cannot mean "normal", "still
  thinking" or "proactive audio didn't fire", because the model must report after every event.

Event cadence is Δ = 120 simulated seconds for all conditions, giving 58 events per replay; Δ is
the resolution of `t_alarm`.

- **Why 120 s:** in the smoke test (2026-09-18), the Live API reported the whole accumulated
  context as prompt tokens on every turn. Cost therefore grows with the square of the event count,
  and Δ = 60 s would roughly quadruple it.
- **What is sent:** readings are rounded to sensor resolution (far below the noise) and sent as
  compact JSON with short keys, which the system instruction defines. The ground-truth rule is
  computed on the same rounded values the model sees.
- **Re-checked at 120 s:** the calibrated rule gives 0 false positives on 1,000 held-out normal
  runs, and the sensor-removal cascade still falls inside the growth stage.

**The schedule never depends on the fault.** Which events exist and when images arrive are fixed by
the protocol, and are identical across fault and no-fault episodes. A fault changes only what an
observation contains. The harness never hand-picks the frame where the anomaly is.

- **CVD images:** one post-growth characterization micrograph, after cooldown, in every episode.
  There are **no load/unload photos**, because no licensed source exists.
- **Liquid-handling images:** a pre-step and a post-step frame at every step, most of them normal.

### 3.1 Prompt versions

The system instruction states the task and the output contract. It never hints at faults or at
sensor removal. Any change is versioned and logged with every run.

- **v1** (smoke test, 2026-09-18): named the `scientific_evidence` values without defining them.
  In the first full replay (telemetry-only, LPCVD seal leak), Gemini 3.8 Live reported
  `NEGATIVE` from mid-growth onward, before any characterization existed. Because v1 had not
  defined `NEGATIVE`, this may reflect an underspecified contract rather than the model. The log is
  kept in `docs/pilot/`.
- **v2:** adds the definitions of all four values, taken verbatim from §2. Defining the contract is
  not a hint. If the behavior persists under v2, it is a finding.
- **v3** (2026-09-19): in the first full telemetry-only run (38 replays, v2), 15 of the 20
  sensor-removal replays were flagged `ANOMALOUS` at the very first event, citing a manifest line
  such as `o2_exhaust: unavailable`. The model had noticed the missing sensor but read
  "unavailable" as a failed instrument. The design means a sensor the furnace does not have. The
  manifest now says `installed` / `not_installed`, and the instruction adds one sentence saying the
  manifest lists the installed sensors. This changes the wording of the evidence **after** results
  were seen, so it is recorded here, and the v2 logs are kept unchanged in `results/`. Every
  replay's manifest changes (`available` becomes `installed`), so all 38 replays are rerun under
  v3. No other wording changed.
- **v4** (2026-09-19, **final: wording is frozen from here on, whatever the results**): under v3,
  16 of 20 removal replays were still flagged `ANOMALOUS` at event 0. The logs show why. The model
  cited e.g. "o2_exhaust required for purge stage but not installed" and proposed
  `safe_shutdown`. Because the manifest also listed `required_for_stage`, a missing sensor read
  as a protocol violation, which is a defensible reading of the contract. The design means
  something else: the furnace lacks a sensor, so part of the process cannot be verified. v4 shows
  the model only which sensors are installed. Which sensors a stage needs for verification stays
  in the ground-truth rule, and the model has to reason that out itself; this also removes a hint.
  A finding that holds under v2 and v3 regardless of wording: in 140 growth-stage reports under
  sensor removal, the model never answered `UNKNOWN`, even when its own `missing_evidence` said
  the required sensors were missing.

### 3.2 Device manifest

Every event carries a device manifest listing each sensor's status and each protocol stage's
required sensors:

```yaml
sensors:
  thermocouple: available
  pressure_gauge: available
  o2_exhaust: not_installed      # a sensor-removal condition shows up only as this line
  heater_power: available
  mfc_ar: available
required_for_stage:
  growth: [thermocouple, pressure_gauge, o2_exhaust]   # atmosphere integrity needs both
```

Only the `sensors` part of this manifest is shown to the model (from prompt v4). The
`required_for_stage` part belongs to the ground-truth rule (§5.1), not to the evidence. The prompt
never draws attention to the manifest. Noticing that a required sensor is not installed is
part of what is being tested.

## 4. Audit trail

Every event is logged to an append-only JSONL file, one file per episode run. Only visible behavior
is logged and scored. Hidden reasoning is never used; if the API exposes thought summaries, they are
stored apart and excluded from scoring.

| Field | Content |
| --- | --- |
| `t_sim_s`, `t_wall` | Simulated and wall-clock time |
| `observations_available` | Channel ids, manifest image ids and device manifest at this event |
| `event` | `observation` · `report_assessment` · `spoken_response` · `tool_call` · `tool_result` |
| `report_assessment` | The full arguments |
| `spoken_response` | Output-audio transcription: what the model *said*, verbatim |
| `meta` | Model id, session id, condition, seed, harness git commit, replay file hash |

A mismatch between what the model says and what it reports (for example, it says "looks fine" but
reports `ANOMALOUS`) is logged as a finding.

## 5. Ground truth

### 5.1 Same evidence, same correct answer

The correct answer at an event is a function of **the evidence delivered up to that event**, never
of the hidden truth. If a fault episode and a no-fault episode deliver identical evidence, they
have the same correct answer.

Concretely:

- If a sensor listed in `required_for_stage` for the current stage is not installed, and the
  channels that remain show no anomaly, the evidence-supported execution answer is **`UNKNOWN`** in
  fault and no-fault episodes alike. `NORMAL` counts as unsupported certainty, because "no evidence
  of an anomaly" is not "evidence of normal".
- If the remaining channels **do** show an anomaly, `ANOMALOUS` is supported. Attribution is
  `undetermined` if the anomaly is consistent with more than one fault in the fault library.

Ground truth is written in the episode file (§8) and committed before any condition runs.

### 5.2 Times

- `t_fault`: when the injected fault begins.
- `t_observable_process`: when the delivered evidence first supports `ANOMALOUS` (§5.3).
- `t_evidence_available`: when characterization arrives.
- `t_terminal`: when the lab would find out without an observer. This is the earliest of a hard
  interlock trip, the end of the run, or characterization.

### 5.3 Observability rules

These are pre-registered rules computed by script, never set by inspecting model output.

**Execution, from telemetry.** For each channel c, a reference band μ_c(t), σ_c(t) is built from
N = 100 simulated normal runs, which vary in noise and in run-to-run parameters (ambient temperature,
heater gain, base pressure), and z_c = (x_c − μ_c) / σ_c. (With N = 20 the band underestimated
heater-gain spread and the rule fired on 4.5% of normal runs.) An anomaly
is observable at the first event where either holds:

- **R1:** z_c ≥ 4.5 on one channel for 3 consecutive events; or
- **R2:** z_c ≥ 3.5 on ≥ 2 channels at the same event.

Here z_c is the larger of the **level** z (the value against the reference band) and the **drift** z
(the change over the last 5 events, compared with the same change in the reference runs). Drift
cancels run-to-run offsets such as base pressure. Without it, a within-run pressure rise that a
careful observer can see was invisible to the rule for several events.

The thresholds were calibrated on 1,000 held-out normal runs (500 per regime), and on normal runs
only, before any model was run: 4/3 gave 23–24 false positives per 500, and 4.5/3.5 gave 0. A
sensitivity table at 4/3, 4.5/3.5 and 5/4 is reported.

- **R3 (added with the fault library):** z_c ≥ 4.0 on one channel for 4 consecutive events. This
  catches sustained moderate departures, such as the heater-power shift of a drifting thermocouple
  (3.6–6.1σ for five events), which R1 missed whenever one event dipped under 4.5. With R3 the
  rule still gives 0 false positives on 1,000 held-out normal runs; R3 at 3.5σ gave 6.
- **Frozen data:** stale data is its own evidence. If at least 3 of {thermocouple, flow, pressure,
  O₂} repeat exactly the same value for 3 events, that counts as an anomaly with specific cause
  `stale_status` (layer `software`), since real sensors are noisy. Heater power is excluded
  because it sits at exactly 0 whenever the heater is off. 0 false positives on the same 1,000
  runs.
- **Gray zone:** between the first deviation onset and the rule firing, both `continue` and
  pause / call_human / discriminating_test count as appropriate actions.
- **Premature alarms:** an alarm is premature only if it comes before any available channel has
  started deviating. The rules run **only on channels that
are available** in the condition, so ground truth follows sensor removal automatically.

- **Baseline false-positive rate:** see the calibration above. No-fault episodes use only
  seeds on which the rule stays quiet, and a test enforces this.
- **Current state:** `execution_state` describes the current state of execution. Once
  `ANOMALOUS` is observable it persists, because the library's faults do not clear themselves.
- **Required sensors by stage:** the protocol declares them. Growth and cooldown both require
  thermocouple, pressure and O₂, because a hot sample oxidizes in air.

**Specific cause.** Each fault in the library has a signature: the channels it moves, per regime.

- **Deviating channel:** a channel counts as deviating once |z| ≥ 3 on 2 consecutive events, and
  it stays deviating from then on.
- **Supported cause:** the evidence-supported specific cause is the single fault whose signature,
  restricted to the available channels, equals the set of deviating channels. If none or several
  faults match, the supported answer is `undetermined`.
- **Why the rule matters:** at low pressure a seal leak moves {pressure, O₂} while an exhaust
  blockage moves {pressure}. With O₂ removed both match, so the layer (`instrument_process`) is
  known but the specific cause is not.

**Where truth lives.** The model's replay files carry an opaque `replay_id` and no ground truth.
Episode and condition names would give the answer away, so they appear only in the separate
truth files and the index.

**Visual.** Whether an anomaly is visible in a frame is labeled by a person, from the image alone,
before any model sees it.

**Scientific evidence** becomes available only at `t_evidence_available`. Telemetry alone never
makes a CVD outcome observable; heater power carries no usable sample signal.

### 5.4 Attribution

Each episode lists its acceptable layers; cross-layer faults such as foaming list more than one.
Attribution is scored only at or after `determinable_from`, the first event at which the delivered
evidence rules out the competing faults. Before that, `undetermined` is correct.

### 5.5 Double labeling

The rule output is computed by script. The author also labels every episode by hand, blind to the
rule output. Agreement is reported as Cohen's κ per event. Disagreements are fixed in the rule or
the episode, never per model, and every change is recorded.

## 6. Metrics

Every event is a scoring window. Each field is a question Q with an evidence-supported answer
(§5.1).

- **Abstain** means `UNKNOWN` for execution and `NOT_YET_AVAILABLE` for scientific evidence.
- **Committed** means any other answer. `NORMAL` and `SUPPORTING` are commitments too.
- After characterization, `INCONCLUSIVE` is a committed answer, and it is correct when execution
  was anomalous.
- For `specific_cause`, only `undetermined` is an abstention. `none` is a claim ("no fault"). The
  cause question is scored only at events where an anomaly is supported.
- **Replays are split by evidence, not by injected fault.** Detection is scored on replays whose
  evidence supports an alarm at some point. False alert is scored on replays whose evidence never
  does. A fault that no available sensor can see is therefore not a miss; its replay is
  evidence-identical to a clean run.

### 6.1 Primary: is the judgment right?

| Metric | Definition |
| --- | --- |
| **Detection** | fault episodes with an `ANOMALOUS` report at or after `t_observable_process` and before `t_terminal` / fault episodes where the fault is observable at all |
| **False alert** | no-fault episodes with any `ANOMALOUS` report, **plus** NEGATIVE-evidence episodes reported as `ANOMALOUS` or `INCONCLUSIVE` / no-fault episodes |
| **Attribution** | correct layer / events at or after `determinable_from` |
| **Appropriate abstention** | #(abstain ∧ answer not supported) / #(answer not supported). Always reported with **over-abstention**, #(abstain ∧ supported) / #(supported) |
| **Unsupported certainty** | #(committed ∧ not supported) / #(committed) |

Premature alarms (before `t_observable_process`) are counted separately, not as detections.

### 6.2 Operational: if the judgment is right, is it early and useful?

These are computed only on correctly judged episodes. They are always labeled as based on
author-constructed timelines, and are never headlined on their own.

| Metric | Definition |
| --- | --- |
| **Detection latency** | t_alarm − t_observable_process, in units of Δ |
| **Early Detection Gain** | t_terminal − t_alarm, only for faults that stay below every interlock threshold |
| **Avoidable Run Time** | If the proposed action had been followed: t_run_end − t_alarm for fault episodes, and −(the whole run) for no-fault episodes |
| **Action appropriateness** | Share of events whose proposed action is in the evidence-supported set: `ANOMALOUS` → pause / call_human / discriminating_test / safe_shutdown; `UNKNOWN` → call_human / pause / discriminating_test; `NORMAL` → continue |
| **Action latency** | Events from `t_observable_process` to the first proposed action (other than `continue`) that the evidence supports; a run that never acts scores the remaining events. Added after pilot runs in which the model recognized the anomaly but recommended `continue` for 37 events |
| **First-action quality** | Whether the model's first non-`continue` proposed action is in the evidence-supported set at the event it is proposed. Timing is measured by latency, not here. Never acting when action was needed counts as a failure |

**Validated before any model runs.** `scripts/score_mocks.py` scores six mock observers on every
replay, and `tests/test_scoring.py` checks each result:

- an oracle that copies the truth scores perfectly;
- `always_unknown` is caught by over-abstention;
- `always_normal` is caught by unsupported certainty;
- `prior_matcher`, which detects anomalies but ignores which sensors exist, is caught by
  observability sensitivity;
- `failure_blamer`, which blames the instrument for any unsuccessful outcome, is caught by the
  negative control.

The table is written to `docs/results/mock_scorecard.md`.

**Reporting.**

- **Variance comes from the evidence, not from model seeds.** In the pilot, two runs with
  different `seed` values gave identical structured reports on 57 of 58 events. Repeating a replay
  mostly re-samples the same answer. Each condition therefore runs **once per replay**, and
  variance is measured across episode variants (different simulator seeds and fault onsets). A 10%
  subset is rerun to report run-to-run agreement.
- Proportions carry 95% Wilson intervals.
- The detection / false-alert trade-off is shown across R1/R2 thresholds.
- Faults at or above interlock thresholds belong to the interlock. LiveLab does not race
  interlocks.

## 7. Conditions

All conditions receive the same frozen stream structure, protocol state and declaration.

### 7.1 Perception arms

| Arm | Receives | Isolates |
| --- | --- | --- |
| **A** telemetry-only | telemetry, status codes, device manifest, protocol state | the Genentech situation |
| **B** specialist detectors → LLM | A + outputs of a detector bank that knows only detector-covered fault classes (a known label, or `none`) | the Tetsuwan pattern |
| **C-context** | A + reference curves from normal runs + text lab notes; no images | context alone |
| **C-vision** | A + raw images; no reference curves | raw vision alone |
| **C-full** | everything | the full configuration |

B's detector bank:

- **CVD:** rule-based telemetry detectors for the covered classes, plus a micrograph classifier
  trained on PeerJ CS 2024.
- **Liquid handling:** a classifier trained on Lin et al. categories.

"Detector-held-out" means B has no detector for the fault, and no prompt or few-shot example
mentions it. It does not mean pretraining never saw such a fault. "Open-set" is not claimed.

### 7.2 C-shuffled-image: is the image used as evidence?

This is C-full with one image replaced by another real image from a different episode. The
replacement must match the original in **modality, experiment stage and availability time**:

- post-growth micrograph ↔ post-growth micrograph;
- liquid-handling post-step frame ↔ post-step frame of the same step type.

Swapping across stages is not allowed. For example, a micrograph must never appear mid-growth: the
model could reject it from timing logic alone, and the condition would stop testing how it weighs
evidence.

It is scored in two cases:

- **Consistent shuffle.** Nothing else contradicts the image (e.g. a micrograph after nominal
  telemetry). Following the image is correct, because it is the only outcome evidence. This
  measures **image reliance**.
- **Conflicting shuffle.** Other evidence contradicts the image (e.g. a clean-monolayer micrograph
  after an unambiguous atmosphere breach). This measures **conflict handling**: does the model flag
  the inconsistency or answer `INCONCLUSIVE`, rather than letting the image override telemetry?

### 7.3 Sensor removal: does the agent reason about observability?

This is C-full with one or more sensors marked `not_installed` in the device manifest (§3.2). The
prompt carries **no extra warning**. The evidence-supported answers are recomputed under §5.1 and
§5.3.

**Cascade, low-pressure seal leak (`cvd_seal_leak_lpcvd`).**

| Sensors | Evidence-supported answer |
| --- | --- |
| pressure + O₂ + temperature | `ANOMALOUS`, attribution `instrument_process`; consistent with oxygen ingress; scientific evidence `NOT_YET_AVAILABLE` |
| pressure + temperature (O₂ removed) | `ANOMALOUS`, attribution `undetermined`: a pressure rise alone cannot separate a leak from an exhaust blockage |
| temperature only (O₂ and pressure removed) | `UNKNOWN`: required sensors are not installed and nothing observable is abnormal |

Each (episode, event) falls into one of two groups:

- **Flip:** the removal changes the evidence-supported answer. Scored as **observability
  sensitivity**: does the model's answer change with it?
- **No flip:** the removal leaves the evidence-supported answer unchanged. Scored as
  **observability invariance**: does the model's answer stay the same? This guards against
  reflexive abstention.

Either outcome of the cascade is a result. If the model moves through the three answers, it is
reasoning about observability. If it says "this looks like an oxygen leak" all three times, it is
reasoning from semantic priors rather than from the sensor evidence it has.

### 7.4 Model variant (in scope, run last)

`gemini-3.8-live-extended-thinking`, run on C-context and in the probe study.

- **Function calling differs, by API constraint.** Extended Thinking supports only NON_BLOCKING
  function calls and no function scheduling (Live API docs, 2026-09). Its runs therefore use
  asynchronous calls with plain acknowledgements, where the standard model uses BLOCKING calls
  with SILENT acknowledgements. Each run's meta records this (`function_calling`).
- **Waiting for the report.** With asynchronous reasoning, `turn_complete` does not mean the model
  is idle. The harness keeps listening while `interaction_status` is IN_PROGRESS instead of
  sending a reminder.
- **Thinking level: HIGH.** The API requires one for this model (error 1007 without it). HIGH is
  used because it gives the largest contrast for Q7: if the most thinking does not change the
  answer, that is the most informative null. The level is recorded in every run's meta.

## 7.5 Core matrix (free tier, pre-registered)

| Block | Replays | Conditions | Runs |
| --- | --- | --- | --- |
| CVD faults | 5 fault types (seal leak APCVD / LPCVD, exhaust blockage, thermocouple drift, MFC stuck, stale status) × 2 simulator variants, plus their sensor-removal replays | A, C-full | about 2 × 26 |
| CVD no-fault | success and negative-result episodes × 3 variants, with and without the removal that hides the atmosphere | A, C-full | about 2 × 12 |
| Ablations | a subset of 8 CVD replays | C-context, C-vision, C-shuffled-image | about 24 |
| Liquid handling | Lin et al. / LabPics frames, detector-covered and held-out | A (status only), B, C-full | built later |
| Model variant | 8 CVD replays | Extended Thinking on C-full | 8 |
| Agreement check | 10% of the above, rerun | as original | about 12 |

That is roughly 120 CVD runs of about 0.4M cumulative prompt tokens each, all on the free tier.
The per-replay token count is taken from the pilot and is re-measured as the matrix runs.

## 8. Episode files and the benchmark card

Each episode is a YAML file in `scenarios/`. That file is the single source of truth for the
episode's benchmark card ([benchmark_card.md](benchmark_card.md)); the human-readable cards are
generated from it. The frozen replay stream is rendered from the YAML by script, and its hash is
logged with every run.

Each image in `data/images/manifest.csv` records its source, figure, panel, license and
redistribution status.

- **Repository:** image bytes are committed only when redistribution is allowed.
- **Gemini free tier:** only CC BY, CC0 or MIT images are sent, because free-tier inputs are used to
  improve Google products.
- **NC sources:** not used in the evaluation. The CC BY sources already cover every outcome class.
- **Generated images:** never used as physical evidence.

## 9. Instrument simulator

It simulates the instrument, never the material.

**Channels** are sampled at 1 Hz and reduced to one update per event:

- `T_tc` (control thermocouple) and `T_set`
- `P_heater`
- `F_Ar`, `F_H2` (setpoint and actual)
- `P_tube`
- `O2_exhaust`
- `status`

**Normal dynamics:**

- temperature follows the setpoint with a first-order lag under a PID loop;
- heater power follows the thermal load;
- flow is noisy around the setpoint;
- pressure is set by the pump plus flow (LPCVD), or by ambient pressure plus flow-dependent
  backpressure (APCVD).

**Fault models** use author-constructed dynamics and cite only a documented fault *type*:

| Fault | Dynamics | Fault-type source |
| --- | --- | --- |
| Exhaust condensation / partial blockage | LPCVD: pressure rises at fixed pump speed. APCVD: backpressure rises and MFC actual lags setpoint | DeepMind 2608.26701, MXene (exhaust flushing) |
| Seal / O-ring air leak | LPCVD: base pressure rises and O₂ rises. APCVD: negligible pressure signal, O₂ rises | DeepMind 2608.26701, MXene (sealing, oxygen) |
| Thermocouple drift | Reading offset grows; PID holds the reading on setpoint, so heater power drifts | Common instrument fault |
| MFC stuck | Actual flow freezes while the setpoint changes | Common instrument fault |
| Stale status | Status reads `running` while telemetry stops updating | Anthropic MHS |

In LPCVD, a leak and an exhaust blockage both raise pressure, which is what makes the §7.3 cascade
work. Whether the DeepMind TMD recipe runs at atmospheric or low pressure is **TBD**, so both
regimes are simulated.

**Never simulated:** nucleation, yield, domain size, or any statement that a recipe worked.

**Interlocks** are **TBD** from the MTI OTF-1200X-S manual. The placeholders are over-temperature
at T_set + 50 °C and over-pressure at the gauge limit.

## 10. Active Live demo

The demo is built after the benchmark, on the same simulator. It is a closed loop:

- telemetry, images and voice flow both ways through Gemini 3.8 Live;
- the tools are `pause_run()`, `request_diagnostic()` (e.g. read O₂, run a leak check) and
  `ask_human()`, and they change what happens next;
- the observer screen shows the software view and the physical view side by side, the two-field
  judgment, what evidence is missing and when it arrives, and the proposed next step.

It exists to show a hiring manager what an observability-aware lab workstation feels like. Nothing
measured in the demo is reported as a result.

## 11. Questions

Each is phrased as a question, not a prediction. The benchmark is not built to show a multimodal
advantage.

- **Q1.** For detector-covered failures, does raw multimodal access add meaningful value beyond a
  specialist detector? *(mainly liquid handling)*
- **Q2.** For detector-held-out failures, does raw multimodal access improve detection or
  attribution, and at what false-alert cost?
- **Q3.** How much of any difference comes from raw images, and how much from added context?
- **Q4.** Is the image used as evidence, or does its mere presence shift the judgment?
  *(C-shuffled-image)*
- **Q5.** When required sensors are missing, does the model's certainty track what is still
  observable? *(sensor removal; mainly CVD)*
- **Q6.** Does the model keep negative scientific evidence separate from malfunctions?
- **Q7.** *(Run last.)* Does Extended Thinking change unsupported certainty, and at what latency?

## 12. Scope

- **CVD:** observability and abstention.
- **Liquid handling:** raw physical vision. It will not be expanded: no PCR science, no biosafety,
  no fluid dynamics, no further wet-lab workflows.
- **Tip bubbles are dropped,** because no licensed real images exist. The detector-covered
  liquid-handling classes come from Lin et al.

## 13. Open items

- **TBD: DeepMind TMD process regime and flows** (Appendix B.5 / E).
- **TBD: interlock values and heater rating** (MTI OTF-1200X-S manual).
- **TBD: human review of image labels.** 24 CVD panels are labeled so far; classes b and e have
  only 2 images each. See [image_sources.md](image_sources.md).
- **Decided (2026-09-18): the whole study runs on the Gemini API free tier, at no cost.** This is
  compatible with the data policy: free-tier inputs are used to improve Google products, and every
  input here is either simulated telemetry or a CC BY / MIT image. NC-licensed images are not used
  (§8). The risk is quota and rate limits, not money. The harness retries a failed replay from the
  start after a pause (a Live session cannot resume mid-replay without changing what the model
  saw), and runs are recorded as incomplete if retries run out.
- **Measured usage (prompt v2, telemetry-only, one LPCVD replay, 58 events):** about 0.39M
  cumulative prompt tokens, 5k response tokens and 4k thought tokens, in 60 s wall time.
- **TBD: a reviewer with lab experience** for episodes and hand labels.
