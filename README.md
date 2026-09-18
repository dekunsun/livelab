# LiveLab: Multimodal Lab Observer

A controlled benchmark for whether scientific agents can distinguish what is wrong, what the
current sensors actually support, and what remains unknowable during a physical experiment.

1. Did something go wrong?
2. What kind of thing went wrong?
3. Do I actually have enough evidence to know?
4. What should I do next?

> A self-driving lab should not only choose the next experiment. It should recognize when the
> current experiment is going wrong, distinguish physical failure from scientific evidence, and
> know when the available sensors are insufficient to tell.

> More modalities do not always mean more observability. In some stages of a physical
> experiment, the scientifically relevant state is simply not observable yet.

## Two parts

- **Research benchmark.** A frozen evidence replay: every condition receives the identical evidence
  stream at identical times, and after each event the model must call `report_assessment()`, which
  returns an execution state, the state of the scientific evidence, an attribution, what evidence
  is missing, and a proposed action. The goal is fairness and reproducibility.
- **Active Live demo.** Gemini 3.8 Live in a closed loop with voice, images, telemetry and tools
  (`pause_run`, `request_diagnostic`, `ask_human`). It shows what an observability-aware lab
  workstation feels like. No results are reported from it.

## Two testbeds

- **2D-materials CVD** tests observability and abstention. The sample is invisible during growth,
  and the visual evidence arrives only at post-growth characterization.
- **Liquid handling** tests raw physical vision. There, anomalies are visible while the workflow
  runs.

**Status:** Phase 1, design. No model has been run yet. See [docs/design.md](docs/design.md).

## What this project cannot show

- **This is not real-time failure detection in a real lab.** It is multimodal failure assessment
  in simulated live lab episodes.
- **No recipe is shown to work.** There is no real reactor. The simulator models the instrument,
  never the material.
- **No safety claim.** An LLM is not a safety system; hard interlocks are. LiveLab does not race
  them.
- **Telemetry dynamics are author-constructed.** Fault *types* cite published incidents, but the
  curve shapes are the author's.
- **Images are real, their pairing is not.** Every image comes from a published paper or public
  dataset (see `data/images/manifest.csv`) and is inserted into a constructed timeline.
- **"Scenario-unseen", not open-set.** A model's pretraining may well include these failures.
