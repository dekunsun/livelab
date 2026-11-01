"""Write docs/eval_settings.md: how every LiveLab Core run was configured, from the run records.

Runner v2 records carry provider, call mode, output cap and runner. Runner v1 records carry only the model, so
their settings are the runner's documented defaults (docs/core.md, scripts/run_core.py): forced function call
unless the folder ends in .auto, a 1,024-token output cap on Anthropic requests, provider from
scripts/run_probes.PROVIDER. Temperature was never set, so each provider's default applies throughout.
Spend is estimated from the saved token counts at the list prices in scripts/run_core.PRICE.

  ./.venv/bin/python scripts/make_eval_settings.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.run_core import PRICE  # noqa: E402
from scripts.run_probes import PROVIDER  # noqa: E402

V1, V2 = ROOT / "results/core", ROOT / "results/core_v2"
SKIP = {"handoff", "logs"}


def folders(base):
    out = []
    for model_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name not in SKIP):
        subs = [model_dir] if any(model_dir.glob("*/*.json")) else [p for p in model_dir.iterdir() if p.is_dir()]
        for m in subs:
            for run in sorted(p for p in m.iterdir() if p.is_dir() and any(p.glob("*.json"))):
                if "quota_failed" not in run.name:
                    out.append(run)
    return out


def tokens(recs, v2):
    tin = tout = 0
    for r in recs:
        uses = [u["usage"] for u in r.get("usage_messages") or []] if v2 else [r.get("usage") or {}]
        for u in uses:
            tin += u.get("prompt_token_count") or 0
            tout += u.get("response_token_count") or 0
    return tin, tout


def row(run, v2):
    recs = [json.loads(p.read_text()) for p in sorted(run.glob("*.json"))]
    model = recs[0]["model"]
    arm = run.name
    if v2:
        provider = recs[0].get("provider", "?")
        call = recs[0].get("tool_choice", "?")
        cap = f"{recs[0].get('max_tokens'):,}" if provider == "anthropic" and recs[0].get("max_tokens") else "provider default"
        if provider == "gemini_live":
            call = "session"
        valid = sum(r["submission"]["status"] == "obtained" for r in recs)
        reminded = sum(bool(r["submission"].get("reminders_before")) for r in recs)
    else:
        provider = PROVIDER.get(model, "gemini live session" if "live" in model else "?")
        call = "auto" if arm.endswith(".auto") else ("session" if "live" in model else "forced")
        cap = "1,024" if provider == "anthropic" else "provider default"
        valid = sum(any(c["name"] == "report_assessment" for c in r.get("calls", [])) for r in recs)
        reminded = None
    tin, tout = tokens(recs, v2)
    price = PRICE.get(model)
    saved = tin or tout
    spend = "free tier" if not price else (f"{(tin * price[0] + tout * price[1]) / 1e6:.2f}" if saved else "—")
    return [model, arm, "v2" if v2 else "v1", provider, call, cap, f"{len(recs)}", f"{valid}",
            "—" if reminded is None else f"{reminded}", f"{tin:,}" if saved else "not saved",
            f"{tout:,}" if saved else "not saved", spend]


def main():
    head = ["Model", "Run", "Runner", "Provider / endpoint", "Call", "Output cap", "Records", "Assessments returned",
            "Items needing a reminder", "Input tokens", "Output tokens", "Est. spend (US$)"]
    lines = ["# LiveLab Core: evaluation settings", "",
             "Every Core run, one row per run folder, generated from the run records by "
             "`scripts/make_eval_settings.py`; never edited by hand. Results: "
             "[leaderboard](results/core_leaderboard.md). Registrations: one per study in `docs/`.", "",
             "**Common to every run.** 80 frozen public items (30 hidden twins, 30 visible twins, 10 normal runs, "
             "10 full-sensor faults); one run per item per folder (`.repN` = repeat N); temperature never set, so each "
             "provider's default applies; every request and response saved. The private hold-out is not listed and "
             "has not been run for any reported result.", "",
             "**Runner v1** (`scripts/run_core.py`): records keep only the model and the final usage, so the call "
             "mode, cap and provider below are the runner's documented defaults, not read from each record: forced "
             "function call unless the run ends in `.auto`; 1,024-token output cap on Anthropic requests, which cut "
             "128 Claude answers ([limitations](core_runner_v1_limitations.md)); Gemini 3.8 Live through a Live API "
             "session. **Runner v2** (`scripts/run_core_v2.py`): every field below is read from the records; up to "
             "two reminders for a missing submission; a missing submission is scored as wrong. The 8,192 output cap "
             "applies to Anthropic requests only; other providers use their default.", "",
             "**Arms.** V0 nothing stated; V1 the gap stated; V1R remedy wording; B1 verifiability probe first; "
             "V1S the scoring rules stated.", "",
             "**Spend** is estimated from saved token counts at the list prices in `scripts/run_core.py` (output "
             "includes reasoning tokens); billed amounts are in each registration's deviation log.", "",
             "| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    for v2, base in ((False, V1), (True, V2)):
        for run in folders(base):
            lines.append("| " + " | ".join(row(run, v2)) + " |")
    out = ROOT / "docs/eval_settings.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out.relative_to(ROOT)} ({len(lines) - 14} rows)")


if __name__ == "__main__":
    main()
