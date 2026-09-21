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
    """What each model answered on a real plant, by condition, under both instrument legends.

    V1 is the original run, whose legend described the instruments wrongly; V2 is the registered
    rerun with it corrected (docs/realdata_v2_preregistration.md). Faded bars are V1, solid V2.
    """
    rows = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for legend, folder in (("v1", "realdata"), ("v2", "realdata_v2")):
        for model, _ in REAL_MODELS:
            for f in (ROOT / "results" / folder / model).glob("*.json"):
                d = json.loads(f.read_text())
                said = [c["args"] for c in d["calls"] if c["name"] == "report_assessment"][-1]
                rows[(model, legend)][d["condition"]][said.get("execution_state")] += 1
    if not rows:
        return

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4), sharey=True)
    order = ["ANOMALOUS", "NORMAL", "UNKNOWN"]
    width = 0.34
    for ax, (cond, correct, title) in zip(axes, CONDITIONS):
        for i, (model, label) in enumerate(REAL_MODELS):
            for legend, dx, alpha in (("v1", -0.19, 0.38), ("v2", 0.19, 1.0)):
                counts = rows[(model, legend)][cond]
                total = sum(counts.values()) or 1
                bottom = 0
                for verdict in order:
                    v = counts.get(verdict, 0)
                    if not v:
                        continue
                    share = v / total * 100
                    ax.bar(i + dx, share, bottom=bottom, color=VERDICT_COLORS[verdict], alpha=alpha,
                           width=width, edgecolor="white", linewidth=0.8)
                    if share >= 12 and legend == "v2":
                        ax.text(i + dx, bottom + share / 2, f"{v}", ha="center", va="center",
                                color="white", fontsize=8, weight="bold")
                    bottom += share
                ax.text(i + dx, 102, f"{counts.get(correct, 0)}", ha="center", fontsize=8,
                        color=VERDICT_COLORS[correct], alpha=1.0 if legend == "v2" else 0.6)
                ax.text(i + dx, -7, legend, ha="center", fontsize=7, color="#777")
        ax.set_xticks(range(len(REAL_MODELS)),
                      [lab.replace(" 3.8", "\n3.8").replace("Claude ", "").replace("GPT-6 ", "GPT-6\n")
                       for _, lab in REAL_MODELS], fontsize=8.5)
        ax.tick_params(axis="x", pad=14)
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 50, 100], ["0", "50", "100%"])
        ax.set_title(f"{title}\nshould answer {correct}", fontsize=10,
                     color=VERDICT_COLORS[correct])
        style(ax)
    axes[0].set_ylabel("share of items", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=VERDICT_COLORS[v]) for v in order]
    handles += [plt.Rectangle((0, 0), 1, 1, color="#999", alpha=0.38),
                plt.Rectangle((0, 0), 1, 1, color="#999")]
    fig.legend(handles, order + ["v1: instruments described wrongly", "v2: corrected, rerun"],
               loc="lower center", ncol=5, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.05))
    fig.suptitle("On a real distillation plant: correcting the instrument description moved the "
                 "verdicts, not the abstention", fontsize=11)
    fig.text(0.01, 0.005, "119 runs of a real batch distillation column (Zenodo 17395543, CC BY) \u00b7 "
             "truth from the plant's expert annotations \u00b7 31/31/37 items per condition \u00b7 "
             "one run per item per legend \u00b7 number above a bar = answers matching the supported one",
             fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.14, 1, 0.95))
    fig.savefig(ROOT / "docs/figures/realdata.png", dpi=160)


FRAME_TOKENS = {"claude-opus-5": 417, "gpt-6-astra": 361}      # measured, 640x480
INPUT_PRICE = {"claude-opus-5": 5.0, "gpt-6-astra": 10.0}      # USD per 1M input tokens
LIVE_VIDEO_PER_HOUR = 0.12                                     # $0.002/min, flat in frame rate


def fig_crossover():
    """Where seeing a transient starts to cost less by streaming than by sending frames.

    Both halves are measured in this project: what each cadence can resolve comes from the
    undersampling ground truth, and tokens per frame from one request with and without a frame.
    """
    items = json.load(open(ROOT / "data/transients/items.json"))["items"]
    resolvable = {}
    for it in items:
        c = it["cadence_s"]
        n, r = resolvable.get(c, (0, 0))
        resolvable[c] = (n + 1, r + (it["class"] == "resolved"))
    cadences = sorted(resolvable, reverse=True)

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax2 = ax.twinx()
    x = [1 / c for c in cadences]                              # frames per second
    share = [resolvable[c][1] / resolvable[c][0] * 100 for c in cadences]
    ax.plot(x, share, "-o", color="#2ca02c", lw=2.4, ms=7, zorder=3,
            label="transients the evidence can support a judgment on")
    for xi, yi, c in zip(x, share, cadences):
        ax.annotate(f"{resolvable[c][1]}/{resolvable[c][0]}", (xi, yi), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, color="#2ca02c")

    fine = [1 / c for c in (120, 30, 5, 1)]
    for model, tok in FRAME_TOKENS.items():
        cost = [3600 * f * tok / 1e6 * INPUT_PRICE[model] for f in fine]
        ax2.plot(fine, cost, "--", lw=1.8, label=f"send frames to {model}",
                 color="#4c78a8" if "opus" in model else "#d9534f")
    ax2.axhline(LIVE_VIDEO_PER_HOUR, color="#15191b", lw=1.8, ls=":",
                label="stream video to Gemini Live ($0.002/min)")
    # where per-frame stops being the cheaper option, solved from the measured token counts
    cross = sorted(LIVE_VIDEO_PER_HOUR / (3600 * FRAME_TOKENS[m] / 1e6 * INPUT_PRICE[m])
                   for m in FRAME_TOKENS)
    ax2.axvspan(cross[0], cross[1], color="#15191b", alpha=0.07, zorder=0)
    ax2.annotate(f"streaming becomes\ncheaper here\n(every {1 / cross[1]:.0f}\u2013{1 / cross[0]:.0f} s)",
                 ((cross[0] * cross[1]) ** 0.5, 12), ha="center", fontsize=8.5, color="#15191b")

    ax.set_xscale("log")
    ax2.set_yscale("log")
    ax.set_xticks(fine, ["every\n120 s", "every\n30 s", "every\n5 s", "every\n1 s"], fontsize=9)
    ax.set_ylim(0, 118)
    ax.set_ylabel("% of transients resolvable", color="#2ca02c", fontsize=9)
    ax2.set_ylabel("cost of one hour of watching (log)", fontsize=9)
    ax2.set_ylim(0.03, 30)
    ax2.set_yticks([0.1, 1, 10], ["$0.10", "$1", "$10"])
    style(ax)
    for spine in ("top",):
        ax2.spines[spine].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="lower right",
              bbox_to_anchor=(0.99, 0.02))
    fig.suptitle("The rate that sees a transient is the rate where streaming starts paying",
                 fontsize=11)
    fig.text(0.01, 0.01, "Left: this project's undersampling ground truth, 12 transient faults. Right: "
             "measured tokens per 640\u00d7480 frame \u00d7 list price, image only.\n"
             "See docs/results/undersampling_results.md and frame_token_cost.md",
             fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(ROOT / "docs/figures/crossover.png", dpi=160)


def main():
    arms, n, cards, unknown = arms_data()
    fig_arms(arms, n, cards)
    fig_unknown(arms, unknown)
    fig_probe()
    fig_realdata()
    fig_crossover()
    print("wrote arms.png, unknown.png, probe.png, realdata.png, crossover.png")


if __name__ == "__main__":
    main()
