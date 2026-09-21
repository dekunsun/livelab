"""Headline figures from the archived logs in results/ (never from hand-copied numbers).

docs/figures/arms.png     detection, false alert and unsupported certainty per arm
docs/figures/unknown.png  what the model answered where only UNKNOWN is supported, per arm
docs/figures/probe.png    the pre-registered probe: knowledge, conflation, abstention per variant
"""
import collections
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.probes import score as probe_score  # noqa: E402
from livelab.prompting import ARMS  # noqa: E402
from livelab.scoring import score_runs  # noqa: E402
from scripts.compare_arms import MODEL, VERSION, load_jsonl, reports  # noqa: E402
from scripts.score_probes import load as load_probes  # noqa: E402

PROBE_MODELS = [("gemini-3.8-live", "Gemini 3.8 Live", "#4c78a8"),
                ("gemini-3.8-live-extended-thinking", "+ Extended Thinking (HIGH)", "#1f3a5f")]
VERDICT_COLORS = {"NORMAL": "#9aa5b1", "ANOMALOUS": "#d9534f", "UNKNOWN": "#2ca02c"}

COLORS = {"A": "#9aa5b1", "C-context": "#4c78a8", "C-full": "#1f3a5f"}
FOOT = "LiveLab · Gemini 3.8 Live · simulated CVD episodes (author-constructed telemetry) · one run per replay"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def arms_data():
    index = json.load(open(ROOT / "data/replays/INDEX.json"))
    arms = [a for a in ("A", "C-context", "C-full") if (ROOT / "results" / MODEL / a / VERSION).exists()]
    common = [r for r in index if all(reports(a, r) for a in arms)]
    truth = lambda r: load_jsonl(ROOT / f"data/truth/{r}.jsonl")
    cards, unknown = {}, {}
    for a in arms:
        reps = {r: reports(a, r) for r in common}
        cards[a] = score_runs(reps, index, truth, sees_images=ARMS[a]["images"])
        c = collections.Counter()
        for r in common:
            for t, x in zip(truth(r), reps[r]):
                if t["execution_state"] == "UNKNOWN":
                    c[x["execution_state"]] += 1
        unknown[a] = c
    return arms, len(common), cards, unknown


def fig_arms(arms, n, cards):
    metrics = [("Detection", "higher is better"), ("False alert", "lower is better"),
               ("Unsupported certainty", "lower is better")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.6))
    for ax, (m, note) in zip(axes, metrics):
        vals = [cards[a][m] for a in arms]
        x = range(len(arms))
        ax.bar(x, [v[0] for v in vals], color=[COLORS[a] for a in arms],
               yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]], capsize=3, ecolor="#555")
        for i, v in enumerate(vals):
            ax.text(i, v[2] + 0.03, f"{v[0]:.2f}", ha="center", fontsize=9)
        ax.set_xticks(list(x), arms)
        ax.set_ylim(0, 1.15)
        ax.set_title(f"{m}\n({note})", fontsize=10)
        style(ax)
    fig.suptitle("Reference curves fix detection and false alerts; unsupported certainty does not move", fontsize=11)
    fig.text(0.01, 0.01, f"{FOOT} · {n} replays per arm · 95% Wilson intervals", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    fig.savefig(ROOT / "docs/figures/arms.png", dpi=160)


def fig_unknown(arms, unknown):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    labels = [("UNKNOWN", "#2ca02c"), ("NORMAL", "#9aa5b1"), ("ANOMALOUS", "#d9534f")]
    for i, a in enumerate(arms):
        left = 0
        total = sum(unknown[a].values())
        for lab, col in labels:
            v = unknown[a].get(lab, 0)
            ax.barh(i, v, left=left, color=col, label=lab if i == 0 else None)
            if v >= 40:
                ax.text(left + v / 2, i, str(v), ha="center", va="center", color="white", fontsize=9)
            left += v
        ax.text(total * 1.03, i, f"UNKNOWN: {unknown[a].get('UNKNOWN', 0)} of {total}", va="center", fontsize=9)
    ax.set_yticks(range(len(arms)), arms)
    ax.invert_yaxis()
    ax.set_xlabel("events where the evidence supports only UNKNOWN")
    ax.set_xlim(0, max(sum(c.values()) for c in unknown.values()) * 1.35)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=3, fontsize=8, frameon=False)
    ax.set_title("Where it cannot tell, the model never says so", fontsize=11)
    style(ax)
    fig.text(0.01, 0.01, FOOT, fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(ROOT / "docs/figures/unknown.png", dpi=160)


def b1_followup(model, items):
    """On U items where it said atmosphere cannot be verified, what verdict did it then give?"""
    sets = {i["item_id"]: i["set"] for i in items["in_context"]}
    got = load_probes(ROOT / "results" / "probes" / model).get("B1", {})
    out = collections.Counter()
    for iid, d in got.items():
        if sets.get(iid) != "U" or d.get("unanswered"):
            continue
        ver = [c["args"] for c in d["calls"] if c["name"] == "report_verifiability"]
        rep = [c["args"] for c in d["calls"] if c["name"] == "report_assessment"]
        if ver and rep and ver[-1].get("atmosphere") == "cannot_verify":
            out[rep[-1].get("execution_state")] += 1
    return out


def fig_probe():
    items = json.load(open(ROOT / "data/probes/items.json"))
    models = [(m, lab, col) for m, lab, col in PROBE_MODELS
              if (ROOT / "results" / "probes" / m).exists()]
    scores = {m: probe_score(items, load_probes(ROOT / "results" / "probes" / m)) for m, _, _ in models}
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), gridspec_kw={"width_ratios": [1, 1.25, 1.9]})

    p1 = scores["gemini-3.8-live"]["P1"]["detectable"]           # P1 was not run for the other model
    axes[0].bar([0], [p1["balanced_accuracy"]], color="#4c78a8", width=0.5)
    axes[0].axhline(0.8, ls="--", color="#888", lw=1)
    axes[0].text(0, p1["balanced_accuracy"] + 0.04, f"{p1['balanced_accuracy']:.0%}", ha="center")
    axes[0].set_xticks([0], ["which sensors\nsee which fault"])
    axes[0].set_ylim(0, 1.15)
    axes[0].set_title("It knows\n(P1, balanced accuracy)", fontsize=10)

    for i, (m, lab, _) in enumerate(models):                     # what followed "cannot verify"
        counts = b1_followup(m, items)
        bottom, total = 0, sum(counts.values())
        for verdict in ("NORMAL", "ANOMALOUS", "UNKNOWN"):
            v = counts.get(verdict, 0)
            axes[1].bar(i, v, bottom=bottom, color=VERDICT_COLORS[verdict],
                        label=verdict if i == 0 else None)
            if v:
                axes[1].text(i, bottom + v / 2, str(v), ha="center", va="center", color="white", fontsize=9)
            bottom += v
        axes[1].text(i, total + 0.5, f"{total} said 'cannot verify'", ha="center", fontsize=7.5, color="#444")
    axes[1].set_xticks(range(len(models)), [lab.replace("+ ", "+\n") for _, lab, _ in models], fontsize=8)
    axes[1].set_ylim(0, 19)
    axes[1].set_title("Then it ruled anyway\n(B1, verdict after 'cannot verify')", fontsize=10)
    axes[1].legend(fontsize=7, frameon=False, loc="upper center", ncol=3, columnspacing=0.8,
                   handlelength=1.2, bbox_to_anchor=(0.5, 1.0))

    names = {"B0": "benchmark\nwording", "B1": "verify\nfirst", "B2": "explicit\ndefinition", "B3": "renamed\nenum"}
    variants = ["B0", "B1", "B2", "B3"]
    width = 0.38
    for i, (m, lab, col) in enumerate(models):
        xs, heights, labels = [], [], []
        for j, v in enumerate(variants):
            cov = scores[m][v]["coverage"].get("U", (0, 0))
            xs.append(j + (i - 0.5) * width)
            heights.append(scores[m][v]["abstention_on_U"][0])
            labels.append(f"{scores[m][v]['abstention_on_U'][0]}/{cov[0]}" if cov[0] else "not run")
        axes[2].bar(xs, heights, width=width, color=col, label=lab)
        for x, h, t in zip(xs, heights, labels):
            axes[2].text(x, h + 0.25, t, ha="center", fontsize=7.5,
                         color="#999" if t == "not run" else "#333")
    axes[2].set_xticks(range(len(variants)), [names[v] for v in variants], fontsize=8)
    axes[2].set_ylim(0, 6)
    axes[2].set_yticks([0, 1, 2])
    axes[2].set_ylabel("items answered UNKNOWN", fontsize=8)
    axes[2].set_title("It never abstains\n(U items: only UNKNOWN is supported)", fontsize=10)
    axes[2].legend(fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.02))
    total = sum(scores[m][v]["coverage"].get("U", (0, 0))[0] for m, _, _ in models for v in variants)
    axes[2].text(1.5, 3.1, f"0 of {total} answers, across both models",
                 ha="center", fontsize=10, color="#d9534f", weight="bold")

    for ax in axes:
        style(ax)
    fig.suptitle("Pre-registered probe: it knows it cannot see, and rules anyway \u2014 more thinking does not change that",
                 fontsize=11)
    fig.text(0.01, 0.01, "Gemini 3.8 Live and Gemini 3.8 Live Extended Thinking (HIGH) \u00b7 single-turn prefixes "
             "(events 0\u201324) \u00b7 one run per item \u00b7 items with no answer excluded \u00b7 "
             "see docs/probe_preregistration.md", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.9))
    fig.savefig(ROOT / "docs/figures/probe.png", dpi=160)


REAL_MODELS = [("gemini-3.8-live", "Gemini 3.8 Live"),
               ("claude-opus-5", "Claude Opus 5"),
               ("gpt-6-astra", "GPT-6 Astra")]
CONDITIONS = [("full", "ANOMALOUS", "Full evidence"),
              ("blind", "UNKNOWN", "Evidence removed"),
              ("control", "NORMAL", "Fault-free run")]


def fig_realdata():
    """What each model answered on a real plant, by condition. The control panel is the point."""
    rows = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for model, _ in REAL_MODELS:
        for f in (ROOT / "results/transients").parent.glob(f"realdata/{model}/*.json"):
            d = json.loads(f.read_text())
            said = [c["args"] for c in d["calls"] if c["name"] == "report_assessment"][-1]
            rows[model][d["condition"]][said.get("execution_state")] += 1
    if not rows:
        return

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.1), sharey=True)
    order = ["ANOMALOUS", "NORMAL", "UNKNOWN"]
    for ax, (cond, correct, title) in zip(axes, CONDITIONS):
        for i, (model, label) in enumerate(REAL_MODELS):
            counts = rows[model][cond]
            total = sum(counts.values()) or 1
            bottom = 0
            for verdict in order:
                v = counts.get(verdict, 0)
                if not v:
                    continue
                share = v / total * 100
                ax.bar(i, share, bottom=bottom, color=VERDICT_COLORS[verdict], width=0.62,
                       edgecolor="white", linewidth=0.8,
                       label=verdict if (ax is axes[0] and bottom == 0 or verdict not in
                                         [t.get_label() for t in ax.containers]) else None)
                if share >= 9:
                    ax.text(i, bottom + share / 2, f"{v}", ha="center", va="center",
                            color="white", fontsize=9, weight="bold")
                bottom += share
            ax.text(i, 103, f"{counts.get(correct, 0)}/{total}", ha="center", fontsize=8.5,
                    color=VERDICT_COLORS[correct])
        ax.set_xticks(range(len(REAL_MODELS)),
                      [lab.replace(" 3.8", "\n3.8").replace("Claude ", "").replace("GPT-6 ", "GPT-6\n")
                       for _, lab in REAL_MODELS], fontsize=8.5)
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 50, 100], ["0", "50", "100%"])
        ax.set_title(f"{title}\nshould answer {correct}", fontsize=10,
                     color=VERDICT_COLORS[correct])
        style(ax)
    axes[0].set_ylabel("share of items", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=VERDICT_COLORS[v]) for v in order]
    fig.legend(handles, order, loc="lower center", ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.055))
    fig.suptitle("On a real distillation plant: one model detects almost everything, "
                 "and alarms on everything too", fontsize=11)
    fig.text(0.01, 0.005, "119 runs of a real batch distillation column (Zenodo 17395543, CC BY) \u00b7 "
             "truth from the plant's expert annotations \u00b7 31/31/37 items per condition \u00b7 "
             "one run per item \u00b7 see docs/results/realdata_results.md", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.15, 1, 0.9))
    fig.savefig(ROOT / "docs/figures/realdata.png", dpi=160)


def main():
    arms, n, cards, unknown = arms_data()
    fig_arms(arms, n, cards)
    fig_unknown(arms, unknown)
    fig_probe()
    fig_realdata()
    print("wrote docs/figures/arms.png, unknown.png, probe.png, realdata.png")


if __name__ == "__main__":
    main()
