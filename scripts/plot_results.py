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


def fig_probe():
    items = json.load(open(ROOT / "data/probes/items.json"))
    s = probe_score(items, load_probes())
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), gridspec_kw={"width_ratios": [1, 1.2, 1.6]})
    p1 = s["P1"]["detectable"]
    axes[0].bar([0], [p1["balanced_accuracy"]], color="#4c78a8")
    axes[0].axhline(0.8, ls="--", color="#888", lw=1)
    axes[0].text(0, p1["balanced_accuracy"] + 0.03, f"{p1['balanced_accuracy']:.0%}", ha="center")
    axes[0].set_xticks([0], ["which sensors\nsee which fault"])
    axes[0].set_ylim(0, 1.1)
    axes[0].set_title("Knows? (P1, balanced acc.)", fontsize=10)
    b1 = s["B1"]
    said, conf = b1["atmosphere_cannot_verify_on_U"], b1["conflation_rate_on_U"]
    axes[1].bar([0, 1], [said[0], conf[0]], color=["#4c78a8", "#d9534f"])
    axes[1].text(0, said[0] + 0.3, f"{said[0]}/{said[1]}", ha="center")
    axes[1].text(1, conf[0] + 0.3, f"{conf[0]}/{said[0]}", ha="center")
    axes[1].set_xticks([0, 1], ["says atmosphere\n'cannot verify'", "of those, then\nreports NORMAL"])
    axes[1].set_ylim(0, said[1] + 2)
    axes[1].set_title("Says it, then ignores it (B1)", fontsize=10)
    names = {"B0": "benchmark\nwording", "B1": "verify\nfirst", "B2": "explicit\ndefinition", "B3": "renamed\nenum"}
    vals = [s[v]["abstention_on_U"] for v in ("B0", "B1", "B2", "B3")]
    axes[2].bar(range(4), [v[0] for v in vals], color="#2ca02c")
    for i, v in enumerate(vals):
        axes[2].text(i, v[0] + 0.3, f"{v[0]}/{v[1]}", ha="center")
    axes[2].set_xticks(range(4), [names[v] for v in ("B0", "B1", "B2", "B3")], fontsize=8)
    axes[2].set_ylim(0, vals[0][1] + 2)
    axes[2].set_title("Answers UNKNOWN when it should (U items)", fontsize=10)
    for ax in axes:
        style(ax)
    fig.suptitle("Pre-registered probe: the model knows it cannot see, but its verdict does not change", fontsize=11)
    fig.text(0.01, 0.01, "Gemini 3.8 Live · single-turn prefixes (events 0–24) · one run per item · "
             "see docs/probe_preregistration.md", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(ROOT / "docs/figures/probe.png", dpi=160)


def main():
    arms, n, cards, unknown = arms_data()
    fig_arms(arms, n, cards)
    fig_unknown(arms, unknown)
    fig_probe()
    print("wrote docs/figures/arms.png, unknown.png, probe.png")


if __name__ == "__main__":
    main()
