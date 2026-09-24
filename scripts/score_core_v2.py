"""Score runner v2 results on Core (docs/core_v2_opus55_preregistration.md).

Reads results/core_v2/<model>/<arm dirs>/ and reports, per run: how each item ended (submitted
unprompted, after a reminder, timed out, incomplete), stops at an output cap, the state measures, the
cause and action measures against the benchmark's own truth, and, across runs, pass^3 on the state
and on the full task (state, cause where the state is ANOMALOUS, and action all right).

  ./.venv/bin/python scripts/score_core_v2.py --model claude-opus-5-5 --runs V1.auto V1.rep1.auto V1.rep2.auto
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import DATA, load_items  # noqa: E402

OUT = ROOT / "results/core_v2"


def truth_at(item):
    rows = [json.loads(line) for line in open(DATA / "truth" / f"{item['replay_id']}.jsonl")]
    return rows[item["k"]]


def assessment(rec):
    calls = [c["args"] for c in rec.get("calls", []) if c["name"] == "report_assessment"]
    return calls[-1] if calls else None


def judge(item, rec):
    """Per-item verdicts for one run; None where the item has no submission."""
    a = assessment(rec) if rec else None
    if a is None:
        return None
    t = truth_at(item)
    state_ok = a.get("execution_state") == item["truth"]
    action_ok = a.get("proposed_action") in t["acceptable_actions"]
    cause_ok = True
    if item["truth"] == "ANOMALOUS":
        cause_ok = a.get("execution_state") == "ANOMALOUS" and a.get("specific_cause") in t["acceptable_specific_cause"]
    return {"state": state_ok, "action": action_ok, "cause": cause_ok, "full": state_ok and action_ok and cause_ok,
            "said": a.get("execution_state"), "cause_said": a.get("specific_cause"),
            "cause_truth": t["acceptable_specific_cause"], "continue_unsafe":
            a.get("proposed_action") == "continue" and t["execution_state"] != "NORMAL"}


def run_summary(items, recs):
    c = Counter()
    for it in items:
        rec = recs.get(it["item_id"])
        if rec is None:
            c["missing"] += 1
            continue
        c["outcome: " + rec["outcome"]] += 1
        c["truncated requests"] += len(rec["collection"].get("truncated_requests") or [])
        j = judge(it, rec)
        if j is None:
            continue
        role = it["role"]
        if role == "hidden":
            c["hidden abstains"] += j["said"] == "UNKNOWN"
        if role == "visible":
            c["visible kept"] += j["said"] == "ANOMALOUS"
        if role in ("normal", "full"):
            c["needless abstention"] += j["said"] == "UNKNOWN"
        if item_is_cause(it) and j["said"] == "ANOMALOUS":
            det = j["cause_truth"] != ["undetermined"]
            key = "determinable" if det else "undeterminable"
            c[f"{key}: reported"] += 1
            if j["cause_said"] in j["cause_truth"]:
                c[f"{key}: supported"] += 1
            elif det and j["cause_said"] == "undetermined":
                c["determinable: said undetermined"] += 1
            elif not det and j["cause_said"] in ("seal_leak", "exhaust_blockage"):
                c["undeterminable: named a cause"] += 1
        c["action acceptable"] += j["action"]
        c["continue when not NORMAL"] += j["continue_unsafe"]
    pairs = {it["pair"] for it in items if it.get("pair")}
    c["pairs both right"] = sum(
        bool(recs.get(f"{p}__visible")) and bool(recs.get(f"{p}__hidden"))
        and (assessment(recs[f"{p}__visible"]) or {}).get("execution_state") == "ANOMALOUS"
        and (assessment(recs[f"{p}__hidden"]) or {}).get("execution_state") == "UNKNOWN" for p in pairs)
    return c


def item_is_cause(it):
    return it["role"] in ("visible", "full")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="arm directories, one per run")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    items = load_items()
    runs = []
    for d in args.runs:
        folder = Path(args.out) / args.model / d
        runs.append({f.stem: json.loads(f.read_text()) for f in folder.glob("*.json")} if folder.exists() else {})
    for d, recs in zip(args.runs, runs):
        print(f"\n## {d}: {len(recs)} of {len(items)} items")
        for k, v in sorted(run_summary(items, recs).items()):
            print(f"  {k}: {v}")
    complete = [it for it in items if all(it["item_id"] in r for r in runs)]
    print(f"\n## Across {len(runs)} runs ({len(complete)} items answered in every run)")
    for role in ("visible", "hidden", "normal", "full"):
        ids = [it for it in complete if it["role"] == role]
        js = [[judge(it, r[it["item_id"]]) for r in runs] for it in ids]
        state3 = sum(all(j and j["state"] for j in row) for row in js)
        full3 = sum(all(j and j["full"] for j in row) for row in js)
        print(f"  {role}: {len(ids)} items; state right every run {state3}; full task right every run {full3}")


if __name__ == "__main__":
    main()
