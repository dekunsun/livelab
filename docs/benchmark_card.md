# Benchmark card

The hardest part of LiveLab is not calling the Gemini API. It is building an evaluation
environment that a skeptical reader is willing to believe. Every episode therefore carries a card
that states where each piece of evidence came from, what the ground truth is, and what was
constructed.

The episode YAML in `scenarios/` is the source of truth. The human-readable cards are generated
from it, so the two cannot drift apart.

## Fields

| Field | Meaning |
| --- | --- |
| `episode_id` | Unique id |
| `scientific_setting` | Domain, material or workflow, process regime, protocol id |
| `failure_mechanism` | The injected fault type, or `none` |
| `source_citation` | Where this *type* of failure is documented. Required unless `failure_mechanism: none` |
| `telemetry_provenance` | Always `author_constructed`. Curve shapes are never attributed to a real run |
| `visual_provenance` | Per image: `real`, manifest id, source DOI + figure/panel, license |
| `pairing` | Always `constructed`. Images and timeline do not come from the same run |
| `device_manifest` | Sensor availability per condition, and `required_for_stage` per protocol stage |
| `ground_truth.execution_state` | `NORMAL` / `ANOMALOUS` over time |
| `ground_truth.evidence_supported_answers` | The evidence-supported answer per stage and per sensor condition (same evidence → same answer) |
| `ground_truth.scientific_evidence` | `SUPPORTING` / `NEGATIVE` / `INCONCLUSIVE` once characterization arrives |
| `t_fault` | Fault onset (s), or `null` |
| `t_observable_process` | From the design §5.3 rule, computed by script. May be `never` for some sensor sets |
| `t_evidence_available` | When characterization arrives |
| `t_terminal` | When the lab would find out without an observer |
| `acceptable_attribution` | A list, because cross-layer faults may have several valid layers |
| `determinable_from` | When attribution becomes scoreable |
| `correct_actions` | Proposed actions that are right at detection (never executed in the benchmark) |
| `acceptable_actions` | Defensible but not preferred |
| `incorrect_or_unsafe_actions` | e.g. `continue` through an oxygen leak; retrying without a discriminating test |
| `labels` | Who labeled what, and the rule output vs the hand label where they differ |

## Rules

- **`source_citation` and `telemetry_provenance` are separate fields.** A citation supports the
  failure *type* only, never the dynamics.
- **An episode cannot be run until its card validates.** Every field must be present, every image
  must have a manifest row with a license, and `t_observable_*` must be computed by script.
- **Changes after the first model run are logged in the episode's `changelog`**, and the
  affected results are re-run.
