"""System instruction, tool declaration and per-event messages for each arm.

The prompt describes the task and the output contract only. It never mentions faults, sensor
removal or what to look for, so noticing an unavailable sensor is left to the model.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT_VERSION = "v2"   # v2 (2026-09-18): defines the scientific_evidence values; see docs/design.md §3.2

SYSTEM_INSTRUCTION = """You are the observer for a chemical vapor deposition (CVD) run in a single-zone tube furnace.
The run is being replayed to you one observation event at a time, at fixed intervals of simulated time.

After EVERY observation event, call report_assessment exactly once with your current judgment:
- execution_state: is the instrument/process executing as the protocol expects? NORMAL, ANOMALOUS,
  or UNKNOWN if the available evidence does not let you tell.
- scientific_evidence: what the evidence so far means for the scientific question (did the target
  material grow?):
    SUPPORTING: characterization shows the target outcome.
    NEGATIVE: execution was normal and characterization shows the target was not achieved;
      this is evidence about the recipe.
    INCONCLUSIVE: characterization exists but cannot count as evidence about the recipe
      (for example because execution was anomalous, or the result is ambiguous).
    NOT_YET_AVAILABLE: no characterization of the sample exists yet.
- attribution: if execution is anomalous, which layer: instrument_process, sample_handling,
  software, undetermined, or none.
- specific_cause: the specific fault if the evidence identifies one; otherwise undetermined or none.
- evidence: the channels and times your judgment rests on.
- missing_evidence: what observation would resolve anything you cannot yet determine.
- proposed_action: continue, discriminating_test, pause, safe_shutdown, or call_human.
  Your proposed action is recorded but not executed; the run continues regardless.

Each event is compact JSON: k = event index; t = simulated seconds; stage = protocol stage;
set = setpoints (T in °C, Ar in sccm); obs = readings: T thermocouple °C, Pheat heater power %,
Ar argon flow sccm, P tube pressure Torr, O2 exhaust oxygen ppm, status = controller status.
When present, ref gives [mean, sd] of each reading at this time across normal runs. A device manifest listing sensor
status and the sensors each stage requires is sent with the first event and again whenever it
changes. Telemetry values are null when a sensor is unavailable.
Speak at most one short sentence per event, and only if your judgment changed."""

REPORT_ASSESSMENT = {
    "name": "report_assessment",
    "description": "Report your current judgment of the run. Call exactly once after every observation event.",
    "behavior": "BLOCKING",
    "parameters": {
        "type": "object",
        "properties": {
            "execution_state": {"type": "string", "enum": ["NORMAL", "ANOMALOUS", "UNKNOWN"]},
            "scientific_evidence": {"type": "string", "enum": ["SUPPORTING", "NEGATIVE", "INCONCLUSIVE", "NOT_YET_AVAILABLE"]},
            "attribution": {"type": "string", "enum": ["instrument_process", "sample_handling", "software", "undetermined", "none"]},
            "specific_cause": {"type": "string", "enum": ["seal_leak", "exhaust_blockage", "thermocouple_drift", "mfc_stuck",
                                                          "stale_status", "other", "undetermined", "none"]},
            "evidence": {"type": "array", "items": {"type": "object", "properties": {
                "channel": {"type": "string"}, "t_sim_s": {"type": "number"}, "observation": {"type": "string"}},
                "required": ["channel", "observation"]}},
            "missing_evidence": {"type": "string"},
            "proposed_action": {"type": "string", "enum": ["continue", "discriminating_test", "pause", "safe_shutdown", "call_human"]},
        },
        "required": ["execution_state", "scientific_evidence", "attribution", "specific_cause", "evidence", "proposed_action"],
    },
}
ENUMS = {k: set(v["enum"]) for k, v in REPORT_ASSESSMENT["parameters"]["properties"].items() if "enum" in v}

# Which inputs each arm receives (design §7.1). Arm B needs the detector bank and is not built yet.
ARMS = {
    "A": {"reference": False, "images": False},
    "C-context": {"reference": True, "images": False},
    "C-vision": {"reference": False, "images": True},
    "C-full": {"reference": True, "images": True},
}


SHORT = {"T_tc": "T", "P_heater": "Pheat", "F_Ar": "Ar", "P_tube": "P", "O2_exhaust": "O2"}


def _sig(x):
    return float(f"{x:.3g}")


def validate(report: dict) -> list:
    """Return the problems with a report_assessment call (empty if valid)."""
    problems = [f"missing {k}" for k in REPORT_ASSESSMENT["parameters"]["required"] if k not in report]
    problems += [f"{k}={report[k]!r} not allowed" for k, allowed in ENUMS.items() if k in report and report[k] not in allowed]
    return problems


def load_reference(protocol_id: str, regime: str) -> dict:
    return json.load(open(ROOT / f"data/replays/reference_{protocol_id}_{regime}.json"))


def event_message(event: dict, arm: str, reference: dict | None, image_dir: Path,
                  image_override: dict | None = None, previous: dict | None = None):
    """Return (text, [(mime, bytes)]) for one observation event under an arm.

    The device manifest is sent on the first event and whenever it changes; repeating an identical
    manifest every event would only spend context.
    """
    cfg = ARMS[arm]
    tel = event["telemetry"]
    payload = {"k": event["event"], "t": event["t_sim_s"], "stage": event["stage"],
               "set": {"T": event["setpoints"]["T_set"], "Ar": event["setpoints"]["F_Ar_set"]},
               "obs": {SHORT[c]: tel[c] for c in SHORT} | {"status": tel["status"]}}
    if previous is None or previous["device_manifest"] != event["device_manifest"]:
        payload["device_manifest"] = event["device_manifest"]
    if cfg["reference"] and reference is not None:
        k = event["event"]
        payload["ref"] = {SHORT[c]: [_sig(v["mean"][k]), _sig(v["sd"][k])] for c, v in reference["channels"].items()}
    images = []
    if cfg["images"]:
        for img in event["images"]:
            img = (image_override or {}).get(img, img)
            images.append(("image/png", (image_dir / f"{img}.png").read_bytes()))
        if images:
            payload["images"] = [f"post-growth optical micrograph ({len(images)} attached)"]
    elif event["images"]:
        payload["images"] = ["characterization image taken (not shown in this configuration)"]
    return json.dumps(payload, separators=(",", ":")), images
