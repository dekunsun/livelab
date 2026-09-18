# LiveLab design

**LiveLab: Multimodal Lab Observer.** A controlled benchmark for whether scientific agents can
distinguish what is wrong, what the current sensors actually support, and what remains unknowable
during a physical experiment.

At every point in an episode the agent is asked four things, in this order:

1. **Did something go wrong?**
2. **What kind of thing went wrong?**
3. **Do I actually have enough evidence to know?**
4. **What should I do next?**

The claim is **multimodal failure assessment in simulated live lab episodes**. It is *not*
real-time failure detection in a real lab. Telemetry is author-constructed, images are real but
come from published sources, and their pairing is constructed (§7).

This document is the Phase 1 specification. It fixes the output contract, the ground-truth rules
and the metrics **before** any model is run, so that results cannot shape the definitions. Items
marked **TBD** are listed in §11.

---

## 1. Output contract: two orthogonal fields

Execution and scientific outcome are separate questions. An experiment that did not support the
hypothesis is not a malfunctioning experiment system.

| Field | Values | Answers |
| --- | --- | --- |
| `execution_state` | `NORMAL` · `ANOMALOUS` · `UNKNOWN` | Is the instrument / process executing as the protocol expects? |
| `scientific_outcome` | `POSITIVE` · `NEGATIVE` · `INCONCLUSIVE` · `NOT_YET_OBSERVABLE` | What does the characterization say about the scientific question? |
| `attribution` | `instrument_process` · `sample_handling` · `software` · `undetermined` · `none` | If execution is anomalous, which layer is at fault? |

The outcome values are defined against execution:

- **POSITIVE**: characterization shows the target outcome.
- **NEGATIVE**: execution was `NORMAL` and characterization shows the target was **not**
  achieved. This is evidence about the recipe or hypothesis. It is the project's most important
  negative control, and calling it a malfunction is a false alert.
- **INCONCLUSIVE**: characterization exists but cannot be read as evidence about the recipe,
  because execution was `ANOMALOUS` (or the image is ambiguous). DeepMind's MXene reproductions
  are the real case: 3/26 succeeded before a seal and oxygen leak was fixed, and 17/25 after. The
  early failures were not evidence against the recipe.
- **NOT_YET_OBSERVABLE**: there is no characterization yet. In CVD this is the only correct value
  during growth.

The mid-growth leak case then needs no special pleading: `execution_state=ANOMALOUS`,
`scientific_outcome=NOT_YET_OBSERVABLE`, `attribution=instrument_process`.

Gemini 3.8 Live has no structured output, so every judgment is a function call. Every arm gets the
same declaration.

```json
{
  "name": "report_assessment",
  "description": "Report your current judgment of the run. Call on every checkpoint request, and at any other time your judgment changes.",
  "parameters": {
    "type": "object",
    "properties": {
      "execution_state":    {"type": "string", "enum": ["NORMAL", "ANOMALOUS", "UNKNOWN"]},
      "scientific_outcome": {"type": "string", "enum": ["POSITIVE", "NEGATIVE", "INCONCLUSIVE", "NOT_YET_OBSERVABLE"]},
      "attribution":        {"type": "string", "enum": ["instrument_process", "sample_handling", "software", "undetermined", "none"]},
      "evidence": {
        "type": "array",
        "items": {"type": "object", "properties": {
          "channel": {"type": "string"},
          "t_sim_s": {"type": "number"},
          "observation": {"type": "string"}
        }, "required": ["channel", "observation"]}
      },
      "missing_evidence": {"type": "string", "description": "For any UNKNOWN / NOT_YET_OBSERVABLE / INCONCLUSIVE: what observation would resolve it, and when it becomes available."},
      "action": {"type": "string", "enum": ["continue", "discriminating_test", "pause", "safe_shutdown", "call_human"]}
    },
    "required": ["execution_state", "scientific_outcome", "attribution", "evidence", "action"]
  }
}
```

No verbal confidence score is collected. Abstention is measured through the explicit
`UNKNOWN` / `NOT_YET_OBSERVABLE` values.

## 2. Episodes and delivery schedule

An **episode** replays one simulated run as a stream of observations: simulated telemetry,
protocol state (the current step and the expected value of each channel), and real images from the
manifest.

**The delivery schedule never depends on the fault.**

- **What is fixed by the protocol alone:** when an image arrives, how many arrive, and when the
  harness asks for an assessment. These are identical across fault and no-fault episodes of the
  same protocol.
- **What the fault changes:** only the *content* of an observation, never whether or when an
  observation happens. The harness never hand-picks the frame where the anomaly is.
- **Why:** choosing frames by where the anomaly is would hand the model part of the detection.

Concretely:

- **Telemetry:** an update every Δ = 60 simulated seconds throughout the run.
- **CVD images:**
  - a load image and an unload image in every episode;
  - a post-growth characterization image at the end of every episode, fault or not.
- **Liquid-handling images:** a pre-step frame and a post-step frame at *every* step. Lin et al.
  already has this pre/post structure. Most frames are normal.
- **Checkpoint assessments:** requested at protocol-defined steps (end of purge, end of ramp,
  mid-growth, end of growth, mid-cooldown, after characterization; for liquid handling, after
  each step). These are the scoring windows.
- **Volunteered assessments:** any `report_assessment` the model makes on its own (on Live,
  proactive speech plus a function call). The first `ANOMALOUS` report sets `t_alarm`, with
  resolution Δ.

## 3. Audit trail

Every event is logged to an append-only JSONL file, one file per episode run. Only visible
behavior is logged and scored. Hidden reasoning is never used; if the API exposes thought
summaries, they are stored separately and excluded from scoring.

| Field | Content |
| --- | --- |
| `t_sim_s`, `t_wall` | Simulated and wall-clock time |
| `observations_available` | Channel ids and manifest image ids delivered so far, plus sensors marked offline |
| `event` | `observation` · `checkpoint_request` · `tool_call` · `tool_result` · `report_assessment` · `spoken_response` |
| `report_assessment` | The full arguments: execution_state, scientific_outcome, attribution, evidence, action |
| `spoken_response` | The output-audio transcription: what the model *said* to the scientist, verbatim |
| `tool_call` / `tool_result` | Name, arguments, returned value |
| `meta` | Model id, session id, arm, condition, seed, harness git commit |

The transcription is recorded as the model's visible statement to the user, not as its
reasoning. A mismatch between what the model *says* and what it *reports* (e.g. it says "looks
fine" but reports `ANOMALOUS`) is itself logged as a finding.

## 4. Ground truth

Ground truth belongs to the **episode**, never to model behavior. It is written in the scenario
file (§7) and committed before any arm runs.

### 4.1 Times

- `t_fault`: when the injected fault begins.
- `t_observable_process`: when the evidence first suffices to call execution `ANOMALOUS` (§4.2).
- `t_observable_sample`: when the scientific outcome first becomes observable, i.e. when the
  characterization image arrives.
- `t_terminal`: when the lab would find out without an observer: the earliest of a hard interlock
  trip, the end of the run, or characterization.

### 4.2 Observability rules

These are pre-registered rules computed by script, never set by inspecting model output.

**Execution (telemetry rule).**

- For each channel c, a reference band μ_c(t), σ_c(t) comes from N = 20 simulated normal runs of
  the same protocol with different noise seeds, and z_c = (x_c − μ_c) / σ_c.
- Execution anomaly is observable at the first update where either condition holds:
  - **R1:** |z_c| ≥ 4 on one channel for 3 consecutive updates, or
  - **R2:** |z_c| ≥ 3 on ≥ 2 channels at the same update.
- Headline results use 4/3. A sensitivity table at 3/4/5 is also reported.

The rules are applied **only to the channels present in the condition**. When a sensor is
removed (§6.3), observability is recomputed from the reduced channel set, so ground truth follows
the sensors automatically.

**Visual evidence.**

- **What is labeled:** whether an anomaly is visible in a frame.
- **Who labels it:** a person, from the image alone, before any model sees it.
- **Rule:** a visible anomaly makes execution observable when that frame arrives.

**Scientific outcome.** The outcome is observable only at `t_observable_sample`. Telemetry
alone never makes a CVD outcome observable; heater power carries no usable sample signal.

### 4.3 Attribution

- **Truth:** each episode lists its acceptable layers. Cross-layer faults such as foaming list
  more than one.
- **When it counts:** each episode declares a `determinable_from` time, the first time the
  evidence rules out the competing layers. Attribution is scored only at or after that time;
  before it, `undetermined` is correct.

### 4.4 Double labeling

- **Two passes:** the rule output (§4.2) is computed by script, and the author labels every
  episode independently, blind to that output.
- **Agreement:** reported as Cohen's κ on observability per checkpoint.
- **Disagreements:** fixed in the rule or the episode, never per model. Every change is recorded.

## 5. Metrics

At checkpoint k, each field is a question Q with truth value v(Q) and an observability flag
obs(Q, k).

- **Abstain** means `UNKNOWN` for execution, and `NOT_YET_OBSERVABLE` for outcome.
- **Committed** means any other answer. `NORMAL` and `POSITIVE` are commitments too, so "the
  sample is fine" is a claim like any other.
- After characterization, `INCONCLUSIVE` is a committed answer, and a correct one when execution
  was anomalous.

### 5.1 Primary: is the judgment right?

| Metric | Definition |
| --- | --- |
| **Detection** | fault episodes with an `ANOMALOUS` report at or after `t_observable_process` and before `t_terminal` / fault episodes |
| **False alert** | no-fault episodes with any `ANOMALOUS` report, **or** NEGATIVE-outcome episodes where the model reports `ANOMALOUS` or `INCONCLUSIVE` (treating negative science as malfunction) / no-fault episodes |
| **Attribution** | correct layer / checkpoints at or after `determinable_from` |
| **Appropriate abstention** | #(abstain ∧ ¬obs) / #(¬obs). Always reported together with **over-abstention** #(abstain ∧ obs) / #(obs), so that a model that always says "I don't know" cannot score well |
| **Unsupported certainty** | #(committed ∧ ¬obs) / #(committed) |

Premature alarms (before `t_observable_process`) are counted separately. They are not
detections.

### 5.2 Operational: if the judgment is right, is it early and useful?

These are reported only on correctly judged episodes, and always labeled as computed on
author-constructed timelines. They are never headlined on their own.

| Metric | Definition |
| --- | --- |
| **Detection latency** | t_alarm − t_observable_process |
| **Early Detection Gain** | t_terminal − t_alarm, only for faults that stay below every interlock threshold |
| **Avoidable Run Time** | For fault episodes the agent stops: t_run_end − t_stop. For no-fault episodes it stops: −(the whole run), because a good run was lost |
| **First-action quality** | The first non-`continue` action falls in the episode's correct / acceptable / incorrect-or-unsafe action sets (§7) |

Reporting:

- Each condition × episode runs at least 5 times with different seeds.
- Proportions carry 95% Wilson intervals.
- The detection / false-alert trade-off is shown across the R1/R2 thresholds rather than at a
  single operating point.
- Faults at or above interlock thresholds belong to the interlock. LiveLab does not race
  interlocks.

## 6. Conditions

Every condition receives the same protocol state and the same `report_assessment` declaration.

### 6.1 Perception arms

| Arm | Receives | Isolates |
| --- | --- | --- |
| **A** telemetry-only | telemetry, status codes, protocol state | the Genentech situation |
| **B** specialist detectors → LLM | A + a detector bank that knows only the detector-covered fault classes and outputs a known label or `none` | the Tetsuwan pattern |
| **C-context** | A + reference curves from normal runs + text lab notes; no images | context alone |
| **C-vision** | A + raw images; no reference curves | raw vision alone |
| **C-full** | everything | Gemini 3.8 Live, full configuration |

B's detector bank has two parts:

- **CVD:** rule-based telemetry detectors for the covered classes, plus a small micrograph
  classifier trained on the PeerJ CS 2024 dataset.
- **Liquid handling:** a small classifier trained on Lin et al. categories.

"Detector-held-out" means B has no detector for that fault and no prompt or few-shot example
mentions it. It does not mean pretraining never saw such a fault, so "open-set" is not claimed.

### 6.2 C-shuffled-image: is the image used as evidence?

This condition is C-full with the episode's image replaced by a real image of the same experiment
type from a *different* episode with a *different* outcome class. There are two cases, and they
must be scored differently:

- **Consistent shuffle.** Nothing else contradicts the image, e.g. a post-growth micrograph after
  nominal telemetry. Following the image is the *correct* behavior here, because the image is the
  only outcome evidence. This case measures **image reliance**: does the answer change when only
  the image changes?
- **Conflicting shuffle.** Other evidence contradicts the image. Examples: a clean-monolayer
  micrograph after an unambiguous oxygen leak; a liquid-handling frame whose objects do not match
  the protocol step. This case measures **conflict handling**: does the model flag the
  inconsistency, or return `INCONCLUSIVE` / `UNKNOWN`, rather than overriding the telemetry?

Metrics: image-following rate (consistent case), and conflict-flag rate plus unsupported
certainty (conflicting case).

### 6.3 Sensor removal: does the agent reason about observability?

This condition is C-full with exactly one input removed and the removal **announced** in the
status channel ("pressure gauge offline"). The inputs removed are: pressure · exhaust O₂ ·
images · reference history · characterization.

Ground-truth observability is recomputed from the reduced channel set (§4.2). Each (episode,
checkpoint) then falls into one of two groups:

- **Flip:** the removal makes a previously observable question unobservable. Score whether the
  answer moves to `UNKNOWN` / `NOT_YET_OBSERVABLE`. This is **observability sensitivity**.
- **No flip:** the removal leaves the question observable. Score whether the answer stays the
  same. This is **observability invariance**, which guards against reflexive abstention.

If the model gives the same confident answer after the only informative sensor is gone, it is
relying on priors and textual patterns rather than evidence. This condition tests the thesis most
directly.

Silent removal (channel missing, not announced) is a possible later variant. It is not in scope.

### 6.4 Model variant (in scope, run last)

`gemini-3.8-live-extended-thinking` on C-full. Voice is not an input variable in any condition.

## 7. Episode files and the benchmark card

Each episode is a YAML file in `scenarios/`, and that file is the source of truth for its
benchmark card. The card format is specified in [benchmark_card.md](benchmark_card.md), and the
human-readable cards are generated from the YAML, so the two can never disagree.

`data/images/manifest.csv` holds one row per image. Its fields are `id`, `source_doi_or_url`,
`figure`, `panel`, `license`, `redistribution_allowed`, `outcome_class`, `domain`,
`visible_anomaly_label`, `labeled_by` and `notes`. Rules:

- **Repository:** image bytes are committed only when `redistribution_allowed=yes`; otherwise
  the repo holds the manifest row and a fetch script.
- **Gemini free tier:** only CC BY, CC0 or MIT images, because free-tier inputs are used to
  improve Google products.
- **Gemini paid tier:** NC sources, with attribution.
- **Never:** a generated image or video used as physical evidence.

## 8. Instrument simulator

It simulates the instrument, never the material.

**Channels** are sampled at 1 Hz and downsampled to Δ for the model:

- `T_tc` (control thermocouple, °C) and `T_set`
- `P_heater` (% of maximum)
- `F_Ar`, `F_H2` (sccm; setpoint and actual)
- `P_tube`
- `O2_exhaust` (ppm)
- `status` / error codes

**Normal dynamics:**

- temperature follows the setpoint with a first-order lag under a PID loop;
- heater power follows the thermal load;
- flow is noisy around the setpoint;
- pressure is set by the regime: pump plus flow for LPCVD, ambient plus flow-dependent
  backpressure for APCVD.

**Fault models** use author-constructed dynamics and cite only a documented fault *type*:

| Fault | Dynamics | Fault-type source |
| --- | --- | --- |
| Outlet condensation / partial blockage | APCVD: backpressure rises toward a blocked asymptote and MFC actual lags setpoint late in the run. LPCVD: pressure rises at fixed pump speed | DeepMind 2608.26701, MXene (exhaust flushing) |
| Seal / O-ring air leak | LPCVD: base pressure rises with leak conductance. APCVD: negligible pressure signal, O₂ rises at the exhaust | DeepMind 2608.26701, MXene (sealing, oxygen) |
| Thermocouple drift | Reading offset grows linearly; the PID holds the reading on setpoint, so the true temperature and heater power drift | Common instrument fault; author-constructed |
| MFC stuck | Actual flow freezes while the setpoint changes | Common instrument fault; author-constructed |
| Stale status | Status reads `running` while telemetry stops updating | Anthropic MHS (device status, camera disconnect) |

The APCVD leak shows why sensor removal matters. With `O2_exhaust` the leak is observable; with it
removed, the correct execution answer is `UNKNOWN`. Whether the DeepMind TMD recipe runs at
atmospheric or low pressure is **TBD**, so both regimes are simulated.

**Never simulated:** nucleation, yield, domain size, or any statement that a recipe worked.

**Interlocks** are **TBD** from the MTI OTF-1200X-S manual. The placeholders are over-temperature
at T_set + 50 °C and over-pressure at the regime's gauge limit.

## 9. Questions

Every one is phrased as a question, not a prediction. The benchmark is not built to show a
multimodal advantage.

- **Q1.** For detector-covered failures, does raw multimodal access add meaningful value beyond a
  specialist detector?
- **Q2.** For detector-held-out failures, does raw multimodal access improve detection or
  attribution, and at what false-alert cost?
- **Q3.** How much of any difference comes from raw images, and how much from added context?
- **Q4.** Is the image used as evidence, or does its presence alone shift the judgment?
  (C-shuffled-image)
- **Q5.** When a sensor is removed, does the model's stated certainty track what is still
  observable? (sensor removal)
- **Q6.** Does the model keep negative scientific results separate from malfunctions?
- **Q7.** *(Run last.)* Does Extended Thinking change unsupported certainty, and at what latency?

## 10. Scope

- **Primary environment: CVD.** Here the outcome is unobservable during the run, which is where
  the question is sharpest.
- **Cross-domain control: liquid handling.** It answers one question only: when a physical anomaly
  is actually visible, does native multimodal input help? It will not be expanded, so there will be
  no PCR science, no biosafety, no fluid dynamics and no further wet-lab workflows.
- **Tip bubbles are dropped.** No licensed real images exist. Detector-covered liquid-handling
  classes come from Lin et al. instead.

## 11. Open items

- **TBD: the DeepMind TMD process regime** (atmospheric or low pressure) and flows, from
  Appendix B.5 / E.
- **TBD: interlock values and heater rating**, from the MTI OTF-1200X-S manual.
- **TBD: the per-image manifest.** Sources are registered in [image_sources.md](image_sources.md).
- **TBD: Live API context billing** across a long session. It is measured in the pilot before any
  study cost is stated.
- **TBD: a reviewer** with lab experience for the episodes and hand labels.
