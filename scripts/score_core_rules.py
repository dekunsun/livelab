"""Score the task-rule clarification run (docs/core_v2_rules_preregistration.md): V1S against the
runner v2 V1 records of the same model, on fixed denominators.

Every row counts the whole predefined set; an item with no valid submission counts as not done, and
is also listed on its own. Research protocol: up to two reminders. Product protocol: a submission that
needed a second reminder does not count.

  ./.venv/bin/python scripts/score_core_rules.py --model claude-opus-5-5 --runs V1.auto V1.rep1.auto V1.rep2.auto V1S.auto
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import DATA, load_items  # noqa: E402

OUT = ROOT / "results/core_v2"


def truth_at(item):
    rows = [json.loads(line) for line in open(DATA / "truth" / f"{item['replay_id']}.jsonl")]
    return rows[item["k"]]


def submitted(rec, product=False):
    """The scored assessment: the first protocol-valid submission, or None."""
    if not rec or rec["submission"]["status"] != "obtained":
        return None
    if product and (rec["submission"]["reminders_before"] or 0) > 1:
        return None
    return next(c["args"] for c in rec["submission"]["first_calls"] if c["name"] == "report_assessment")


def cause_sets(items):
    det = [i for i in items if i["truth"] == "ANOMALOUS" and truth_at(i)["acceptable_specific_cause"] != ["undetermined"]]
    und = [i for i in items if i["truth"] == "ANOMALOUS" and truth_at(i)["acceptable_specific_cause"] == ["undetermined"]]
    return det, und


def table(items, recs, product=False):
    det, und = cause_sets(items)
    t = {}

    def a(i):
        return submitted(recs.get(i["item_id"]), product)

    # determinable causes: 20
    c = {"correct": 0, "wrong cause": 0, "needless undetermined": 0, "state not ANOMALOUS": 0, "no valid submission": 0}
    for i in det:
        x = a(i)
        if x is None:
            c["no valid submission"] += 1
        elif x.get("execution_state") != "ANOMALOUS":
            c["state not ANOMALOUS"] += 1
        elif x.get("specific_cause") in truth_at(i)["acceptable_specific_cause"]:
            c["correct"] += 1
        elif x.get("specific_cause") == "undetermined":
            c["needless undetermined"] += 1
        else:
            c["wrong cause"] += 1
    t["determinable (of %d)" % len(det)] = c
    # undeterminable causes: 20
    c = {"correct (undetermined)": 0, "named a cause": 0, "state not ANOMALOUS": 0, "no valid submission": 0}
    for i in und:
        x = a(i)
        if x is None:
            c["no valid submission"] += 1
        elif x.get("execution_state") != "ANOMALOUS":
            c["state not ANOMALOUS"] += 1
        elif x.get("specific_cause") == "undetermined":
            c["correct (undetermined)"] += 1
        else:
            c["named a cause"] += 1
    t["undeterminable (of %d)" % len(und)] = c
    # actions on the 70 items whose reference state is not NORMAL
    notnorm = [i for i in items if i["truth"] != "NORMAL"]
    c = {"continue (by reference state)": 0, "action in allowed set": 0, "no valid submission": 0,
         "said UNKNOWN/ANOMALOUS, then continue (self-consistency)": 0}
    for i in notnorm:
        x = a(i)
        if x is None:
            c["no valid submission"] += 1
            continue
        c["continue (by reference state)"] += x.get("proposed_action") == "continue"
        c["action in allowed set"] += x.get("proposed_action") in truth_at(i)["acceptable_actions"]
    for i in items:
        x = a(i)
        if x is not None and x.get("execution_state") in ("UNKNOWN", "ANOMALOUS") and x.get("proposed_action") == "continue":
            c["said UNKNOWN/ANOMALOUS, then continue (self-consistency)"] += 1
    t["not NORMAL (of %d)" % len(notnorm)] = c
    # state, fixed denominators
    def count(role, ok):
        ids = [i for i in items if i["role"] == role]
        return sum(1 for i in ids if (x := a(i)) is not None and ok(i, x)), len(ids)
    t["state"] = {
        "hidden abstains": count("hidden", lambda i, x: x.get("execution_state") == "UNKNOWN"),
        "visible kept": count("visible", lambda i, x: x.get("execution_state") == "ANOMALOUS"),
        "full-sensor fault detected": count("full", lambda i, x: x.get("execution_state") == "ANOMALOUS"),
        "normal: state NORMAL": count("normal", lambda i, x: x.get("execution_state") == "NORMAL"),
        "normal: state and action right": count("normal", lambda i, x: x.get("execution_state") == "NORMAL"
                                                and x.get("proposed_action") in truth_at(i)["acceptable_actions"]),
    }
    # submission
    s = {"first valid, unprompted": 0, "after 1 reminder": 0, "after 2 reminders": 0, "no valid submission": 0}
    for i in items:
        r = recs.get(i["item_id"])
        if not r or r["submission"]["status"] != "obtained":
            s["no valid submission"] += 1
        else:
            s[{0: "first valid, unprompted", 1: "after 1 reminder"}.get(r["submission"]["reminders_before"] or 0,
                                                                       "after 2 reminders")] += 1
    t["submission (of %d)" % len(items)] = s
    return t


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--product", action="store_true", help="product protocol: at most one reminder")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    items = load_items()
    for d in args.runs:
        folder = Path(args.out) / args.model / d
        recs = {f.stem: json.loads(f.read_text()) for f in folder.glob("*.json")} if folder.exists() else {}
        print(f"\n## {args.model} {d}: {len(recs)} of {len(items)} records"
              + (" (product protocol)" if args.product else " (research protocol)"))
        for group, rows in table(items, recs, args.product).items():
            print(f"  {group}")
            for k, v in rows.items():
                print(f"    {k}: {'%d/%d' % v if isinstance(v, tuple) else v}")


if __name__ == "__main__":
    main()
