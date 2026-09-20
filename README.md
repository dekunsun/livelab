# LiveLab: Multimodal Lab Observer

A controlled benchmark for whether scientific agents can distinguish what is wrong, what the
current sensors actually support, and what remains unknowable during a physical experiment.

> A self-driving lab should not only choose the next experiment. It should recognize when the
> current experiment is going wrong, distinguish physical failure from scientific evidence, and
> know when the available sensors are insufficient to tell.

## Headline result

Gemini 3.8 Live watched 38 simulated CVD growth runs (MoS₂ on SiO₂/Si, following the TMD workflow
in DeepMind's Gemini paper) and reported its judgment every two simulated minutes.

1. **Context fixes detection.** Adding normal-run reference curves raised detection from
   **0.50 to 0.90** and cut false alerts from **0.83 to 0.00–0.11**. Reference curves alone
   (C-context) did as well as reference curves plus micrographs (C-full). In-run detection comes
   from context, not from images.
2. **Nothing fixes calibration.** At the **1,986** events (662 per arm) where the evidence could
   not support a judgment, because a sensor needed to verify the stage was not installed, the model
   answered `UNKNOWN` **0 times**. Unsupported certainty stayed at **0.37** in every arm.
3. **It knows, but its verdict does not change.** A
   [pre-registered probe](docs/probe_preregistration.md) ruled out three explanations:
   - **Knowledge:** the model mostly knows which sensors can see which faults (81% balanced
     accuracy).
   - **Convention:** an explicit instruction to answer `UNKNOWN` in exactly this situation moved it
     0 of 14.
   - **Option bias:** renaming and reordering the enum moved it 0 of 14.

   What remains: asked separately, it said *"atmosphere cannot be verified"* on 12 of 14 such items,
   then reported the run as **NORMAL on all 12**.
   - **Thinking longer:** Gemini 3.8 Live Extended Thinking, at HIGH, abstained **0 of 41** times
     under three of the same framings. It named the missing evidence more precisely, including the
     test that would settle the question, and then committed anyway.

   Across both models, **97 answers** on items where only `UNKNOWN` is supported, **0 abstentions**.

**Implication:** "cannot verify" has to be a system state, computed from which sensors are
installed and what each stage needs, or asked as its own question. It cannot be left to the
model's verdict.

![Detection, false alert and unsupported certainty per arm](docs/figures/arms.png)
![Answers at events where only UNKNOWN is supported](docs/figures/unknown.png)
![Pre-registered probe](docs/figures/probe.png)

Full tables: [arm comparison](docs/results/arm_comparison.md) ·
[probe results](docs/results/probe_results.md) · [probe findings](docs/results/probe_findings.md) ·
[mock scorecard](docs/results/mock_scorecard.md).

## What the benchmark asks

After every observation event the agent calls `report_assessment()` and answers four questions:

1. Did something go wrong? (`execution_state`: NORMAL / ANOMALOUS / UNKNOWN)
2. What kind of thing went wrong? (`attribution`, `specific_cause`)
3. Do I actually have enough evidence to know? (abstention, and `scientific_evidence`:
   SUPPORTING / NEGATIVE / INCONCLUSIVE / NOT_YET_AVAILABLE)
4. What should I do next? (`proposed_action`, which is recorded but never executed)

Execution and scientific evidence are kept separate. A run that executed normally and grew nothing
is a **negative result**, not a malfunction. A result from a run with anomalous execution is
**inconclusive**. It is not evidence about the recipe.

## How it works

| Stage | What it does | Where |
| --- | --- | --- |
| Episodes | Instrument simulator (a PID-controlled tube furnace, MFC, pressure, exhaust O₂) with five fault types: seal leak, exhaust blockage, thermocouple drift, stuck MFC, stale status. Each run ends with a real, license-checked micrograph from a published paper | `livelab/simulator.py`, `scenarios/` |
| Ground truth | Pre-registered rules decide what the delivered evidence supports at each event. **Same evidence, same answer:** truth never depends on hidden state | `livelab/observability.py`, `data/truth/` |
| Frozen replay | Every condition receives identical evidence at identical times, with an opaque id and no truth | `data/replays/`, `livelab/harness.py` |
| Scoring | Five primary metrics, plus operational metrics, validated first against mock observers (oracle, always-normal, always-unknown, prior-matcher and others) | `livelab/scoring.py`, `livelab/mock_models.py` |
| Model | Gemini 3.8 Live on the free tier, one Live session per replay, and an append-only audit log of visible behavior only | `livelab/backends.py`, `results/` |

The benchmark has **18 CVD episodes**, which render to **38 replays** once sensor-removal
conditions are included. The arms are: **A** (telemetry only), **C-context** (+ normal-run
reference curves) and **C-full** (+ micrographs).

![The sensor-removal cascade: the supported answer depends on which sensors exist](docs/figures/cascade_lpcvd.png)

## What this project cannot show

- **Not real-time failure detection in a real lab.** It is multimodal failure assessment in
  simulated live lab episodes.
- **No recipe is shown to work.** The simulator models the instrument, never the material.
- **No safety claim.** An LLM is not a safety system; hard interlocks are.
- **Telemetry dynamics are author-constructed.** Fault *types* cite published incidents
  (DeepMind arXiv 2608.26701; Anthropic MHS), but the curve shapes are the author's.
- **Images are real; their pairing with a run is not.** See `data/images/manifest.csv` and
  `data/images/ATTRIBUTION.md`. Image outcome labels await human review.
- **One model, one run per replay.** Different seeds gave near-identical outputs (57 of 58 events),
  so variance comes from episode variants. Other models are untested.
- **Scientific-evidence judgments from images are confounded.** The prompt never defined the
  target as a *monolayer*, and the micrographs include several TMDs. These judgments are therefore
  not claimed as results.
- **"Scenario-unseen", not open-set.** Pretraining may include these failures.

## How the wording was frozen

This benchmark changed its prompt wording three times after seeing results. Each change is recorded
with its reason in [docs/design.md §3.1](docs/design.md), and every version's logs are kept in
`results/`:

- **v1 → v2:** defined the `scientific_evidence` values.
- **v2 → v3:** changed "unavailable" to "not installed".
- **v3 → v4:** stopped showing per-stage sensor requirements, which the model read as a protocol
  violation.

Wording has been **frozen at v4**. The `UNKNOWN` result held under every version.

What went wrong along the way, and what it taught (evaluation design, contract ambiguity,
pre-registration, porting the harness between models, cost structure):
[docs/lessons_learned.md](docs/lessons_learned.md).

## Running it

```bash
python3 -m venv .venv && ./.venv/bin/pip install numpy pyyaml pytest matplotlib pillow google-genai
./.venv/bin/python -m pytest -q                       # everything below works without an API key
./.venv/bin/python scripts/render_replays.py          # frozen replays + separate truth files
./.venv/bin/python scripts/score_mocks.py             # validates the metrics on mock observers
./.venv/bin/python scripts/compare_arms.py            # scores archived runs -> docs/results/
./.venv/bin/python scripts/plot_results.py            # figures -> docs/figures/
```

To run Gemini 3.8 Live, copy `.env.example` to `.env` and put your key there. `.env` is gitignored;
never paste the key anywhere else.

```bash
./.venv/bin/python scripts/run_benchmark.py --backend gemini --arm C-full --resume
./.venv/bin/python scripts/run_probes.py && ./.venv/bin/python scripts/score_probes.py
```

On the free tier, one replay takes about a minute and roughly 0.4M cumulative prompt tokens. The
Live API counts the whole accumulated context on every turn, so events are 120 s apart and sent as
compact JSON.

## Licensing

- **Code and documentation:** MIT (see `LICENSE`).
- **Images in `data/images/cvd/`:** panels cropped from CC BY 4.0 articles. Each image's source,
  figure, panel and licence are in `data/images/manifest.csv`, with per-source attribution in
  `data/images/ATTRIBUTION.md`. Reuse them under CC BY 4.0, citing the original papers.
- **Telemetry and episodes:** author-constructed simulation, covered by the MIT licence above, and
  not data from any real run.

## Status

**Done:**
- the benchmark design;
- 18 CVD episodes;
- the scorer and its mock validation;
- arms A, C-context and C-full, each under frozen prompt v4;
- the pre-registered UNKNOWN probe.

- **the Extended Thinking comparison** (stage 1: B0, B1 and B2 on the 14 U items). Collecting it
  took a night and produced nothing on the free tier, where the model's function-call path fails
  silently for hours, and about twenty minutes once billing was enabled. What that failure looked
  like, how it was caught, and what now prevents a harness from scoring it as the model declining
  to answer, is in [deviation 7](docs/probe_preregistration.md) and
  [lessons_learned.md](docs/lessons_learned.md).

**Not yet built:**
- the liquid-handling control;
- arm B (specialist detectors);
- C-vision and C-shuffled-image;
- a cross-model comparison;
- the Active Live demo.
