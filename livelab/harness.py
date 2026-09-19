"""Frozen-replay harness: one observation event in, exactly one report_assessment out.

Writes an append-only audit log per run (design §4) with only visible behavior: what was
delivered, the report, what the model said, tool calls, and usage.
"""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from .prompting import PROMPT_VERSION, async_only, event_message, load_reference

ROOT = Path(__file__).resolve().parent.parent
MISSING = {"execution_state": "MISSING", "scientific_evidence": "MISSING", "attribution": "MISSING",
           "specific_cause": "MISSING", "evidence": [], "proposed_action": "MISSING"}


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


async def run_replay(backend, replay_id, arm, seed, out_dir, image_override=None, max_events=None):
    index = json.load(open(ROOT / "data/replays/INDEX.json"))[replay_id]
    replay_path = ROOT / f"data/replays/{replay_id}.jsonl"
    text = replay_path.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == index["sha256"], "replay file changed since rendering"
    events = [json.loads(line) for line in text.splitlines()][:max_events]
    ep = next(p for p in ROOT.glob("scenarios/**/*.yaml") if p.stem == index["episode_id"])
    meta_ep = yaml.safe_load(open(ep))
    reference = load_reference(meta_ep["protocol"], meta_ep["regime"])

    out = Path(out_dir) / f"{replay_id}__{arm}__s{seed}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {"model": backend.model_id, "prompt_version": PROMPT_VERSION, "arm": arm, "seed": seed, "replay_id": replay_id,
            "function_calling": "non_blocking" if async_only(backend.model_id) else "blocking+silent",
            "thinking_level": getattr(backend, "thinking_level", None),
            "replay_sha256": index["sha256"], "harness_commit": git_commit(),
            "image_override": image_override, "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    reports = []
    partial = out.with_suffix(".partial")      # renamed only when every event has been answered
    with open(partial, "w") as log:
        log.write(json.dumps({"event": "meta", **meta}) + "\n")
        await backend.start(seed)
        try:
            previous = None
            for e in events:
                msg, images = event_message(e, arm, reference, ROOT / "data/images/cvd", image_override, previous)
                previous = e
                t0 = dt.datetime.now(dt.timezone.utc)
                res = await backend.observe(msg, images)
                report = res["report"] or MISSING
                reports.append(report)
                log.write(json.dumps({
                    "event": "report", "k": e["event"], "t_sim_s": e["t_sim_s"],
                    "t_wall": t0.isoformat(), "latency_s": (dt.datetime.now(dt.timezone.utc) - t0).total_seconds(),
                    "delivered": msg, "images_delivered": len(images),
                    "report_assessment": report, "spoken_response": res["spoken"],
                    "tool_calls": res["tool_calls"], "reminders": res["reminders"],
                    "problems": res["problems"], "usage": res["usage"]}) + "\n")
                log.flush()
        finally:
            await backend.close()
    partial.replace(out)
    return reports, out


def completed_reports(out_dir, replay_id, arm, seed, n_events):
    """Reports from a finished log with the current prompt version, or None."""
    path = Path(out_dir) / f"{replay_id}__{arm}__s{seed}.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(line) for line in open(path)]
    if rows[0].get("prompt_version") != PROMPT_VERSION:
        return None
    reports = [r["report_assessment"] for r in rows[1:] if r["event"] == "report"]
    return reports if len(reports) == n_events else None
