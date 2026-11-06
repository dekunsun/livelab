"""Poster charts drawn at their printed size, so every label is the poster's body size (26 px = 19.5 pt).

Each chart is saved at the width it occupies on the poster (CSS px at 96 per inch), in Helvetica Neue, with no title
inside the image (the poster heading above each chart names it). Values are read from the run records through the
same functions the full-size figures use:
  rules_poster.png     Results B: missed escalations and missed faults by task statement (scripts/plot_tradeoff.point)
  realplant_poster.png Results C: detection against false alerts on the real plant (scripts/plot_realdata_ci.counts)
  cascade_poster.png   Methodology: the evidence-supported answer over time for three sensor sets (livelab.episode)
  arms_poster.png      LiveLab 2.0: onsets located within 120 s per arm (records in ../livelab2/results)

  ./.venv/bin/python scripts/plot_poster_charts.py            # widths below; change them if the poster columns change
"""
import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "poster/fig"
WIDTH = {"rules": 902, "realplant": 958, "cascade": 671, "arms": 524}   # CSS px on the poster
PT = 19.5                                                              # 26 px at 96 per inch
INK, SOFT, GRID, NAVY = "#15201c", "#4d5a55", "#e3e6ea", "#011F5B"
plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": PT, "axes.titlesize": PT, "axes.labelsize": PT,
                     "xtick.labelsize": PT, "ytick.labelsize": PT, "legend.fontsize": PT, "axes.unicode_minus": False,
                     "axes.edgecolor": GRID, "axes.labelcolor": SOFT, "xtick.color": SOFT, "ytick.color": SOFT,
                     "xtick.major.size": 0, "ytick.major.size": 0, "axes.spines.top": False, "axes.spines.right": False})


def figure(key, height_in, **kw):
    return plt.subplots(figsize=(WIDTH[key] / 96, height_in), dpi=300, facecolor="white", **kw)


def save(fig, key):
    path = OUT / f"{key}_poster.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print("wrote", path.relative_to(ROOT))


def rules():
    from livelab.core import load_items
    from scripts.plot_tradeoff import MODELS, point
    keep = [("Claude Opus 5.5", "Opus 5.5", "#eb6834"), ("GPT-6 Astra", "Astra", "#1baf7a"),
            ("Gemini 3.1 Pro", "3.1 Pro", "#2a78d6"), ("GLM 5.3 Flash (open weights)", "GLM", "#eda100")]
    stages = ["V0", "V1", "V1S"]
    items = load_items()
    runs = dict(MODELS)
    fig, axes = figure("rules", 4.0, ncols=2)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.76, bottom=0.15, wspace=0.22)
    for ax, k, title in ((axes[0], 0, "Missed escalations"), (axes[1], 1, "Missed faults")):
        ax.axhspan(-1, 2.5, color="#e5f4e4", zorder=0)
        if k == 0:
            ax.text(0.5, 3.4, "gate", ha="center", va="bottom", color="#3d7a3c")
        for j, (name, short, col) in enumerate(keep):
            xs, ys = [], []
            for i, s in enumerate(stages):
                if s in runs[name]:
                    pts = [point(f, items) for f in runs[name][s]]
                    xs.append(i)
                    ys.append(30 - statistics.median(p[k] for p in pts) + (j - 1.5) * 0.3)
            ax.plot(xs, ys, color=col, lw=3, marker="o", markersize=9, markeredgecolor="white", markeredgewidth=1.5, zorder=3)
        ax.set_title(title, loc="left", color=INK, fontweight="bold", pad=10)
        ax.set_xticks(range(3), ["none", "gap", "rules"])
        ax.set_xlim(-0.2, 2.2)
        ax.set_ylim(-1.5, 31.5)
        ax.set_yticks([0, 15, 30])
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], color=c, lw=3, marker="o", markersize=9, label=s) for _, s, c in keep]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.53, 1.0),
               handlelength=1.4, columnspacing=1.2)
    save(fig, "rules")


def realplant():
    from scripts.plot_realdata_ci import COLOR, MODELS, counts, wilson
    short = {"gemini-3.8-live": "Gemini 3.8 Live", "claude-opus-5": "Opus 5", "gpt-6-astra": "Astra"}
    s = counts()
    fig, ax = figure("realplant", 4.2)
    fig.subplots_adjust(left=0.10, right=0.985, top=0.86, bottom=0.17)
    ax.scatter([0], [31], marker="*", s=260, color=INK, zorder=5)
    ax.text(1.0, 31.3, "ideal", color=INK, va="center")
    for m in MODELS:
        for lg in ("v1", "v2"):
            c = s[(m, lg)]
            x, y = c["fa"], c["det"]
            xl, xh = wilson(c["fa"], c["nc"])
            yl, yh = wilson(c["det"], c["nf"])
            a = 0.35 if lg == "v1" else 1.0
            ax.plot([xl, xh], [y, y], color=COLOR[m], lw=2, alpha=a, zorder=2)
            ax.plot([x, x], [yl, yh], color=COLOR[m], lw=2, alpha=a, zorder=2)
            ax.scatter([x], [y], s=110, facecolor="white" if lg == "v1" else COLOR[m], edgecolor=COLOR[m], lw=2, zorder=4)
        c = s[(m, "v2")]
        right = c["fa"] > 25
        ax.text(c["fa"] + (-1.2 if right else 1.4), c["det"] - 2.4, f"{short[m]}  {c['det']}/31 · {c['fa']}/37",
                ha="right" if right else "left", va="top", color=INK, fontweight="bold")
    ax.set_xlim(-1.5, 38.5)
    ax.set_ylim(-1.5, 33.5)
    ax.set_xticks([0, 10, 20, 30, 37])
    ax.set_yticks([0, 10, 20, 31])
    ax.grid(color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("Fault-free runs called anomalous, of 37")
    ax.set_ylabel("Faults detected, of 31")
    handles = [plt.Line2D([], [], marker="o", ls="", markersize=11, markerfacecolor="white", markeredgecolor=SOFT, label="first run"),
               plt.Line2D([], [], marker="o", ls="", markersize=11, color=SOFT, label="corrected rerun")]
    fig.legend(handles=handles, loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(0.99, 1.0))
    save(fig, "realplant")


def cascade():
    from livelab.episode import load, render
    from livelab.observability import event_times
    from livelab.protocol import PROTOCOLS
    colors = {"NORMAL": "#9bc59d", "ANOMALOUS": "#d9534f", "UNKNOWN": "#c8c8c8"}
    labels = {"base": "pressure + O₂", "no_o2": "pressure only", "no_o2_no_pressure": "neither"}
    ep = load(ROOT / "scenarios/pilot/cvd_seal_leak_lpcvd.yaml")
    times = event_times(PROTOCOLS[ep["protocol"]], 120) / 60
    conds = list(ep["sensor_conditions"])
    fig, ax = figure("cascade", 3.9)
    fig.subplots_adjust(left=0.30, right=0.90, top=0.87, bottom=0.42)
    for i, c in enumerate(conds):
        for r in render(ep, c)[1]:
            und = r["acceptable_specific_cause"][0] == "undetermined"
            ax.barh(i, 1, left=times[r["event"]] - 1, height=0.72, color=colors[r["execution_state"]],
                    hatch="///" if und else None, edgecolor="white", lw=0)
    t0 = ep["fault"]["t_fault_s"] / 60
    ax.axvline(t0, color=INK, ls="--", lw=1.5)
    ax.text(t0, -0.62, "leak starts", ha="center", va="bottom", color=INK)
    ax.set_yticks(range(len(conds)), [labels[c] for c in conds], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(35, 70)
    ax.set_xticks([40, 50, 60, 70], ["40", "50", "60", "70 min"])
    ax.spines["left"].set_visible(False)
    handles = [Patch(color=colors["NORMAL"], label="normal"), Patch(color=colors["ANOMALOUS"], label="anomalous"),
               Patch(color=colors["UNKNOWN"], label="unknown"),
               Patch(facecolor=colors["ANOMALOUS"], hatch="///", edgecolor="white", label="cause unknown")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.55, 0.0),
               handlelength=1.2, columnspacing=1.0)
    save(fig, "cascade")


def arms():
    base = ROOT.parent / "livelab2" / "results"
    def hits(agent, cell):
        d = base / agent / "main_public" / cell
        return sum(json.load(open(p))["metrics"]["exact"]["120"] == "hit" for p in d.glob("*.json")) if d.exists() else None
    arms_ = [("F2_t2", True, "Classical"), ("E_K1800_t2", False, "Fixed"), ("D_K1800_t2", False, "Agent"), ("B_K1800_t2", False, "Oracle")]
    models = [("opus-5.5", "Opus 5.5", NAVY), ("gemini-3.1-pro", "3.1 Pro", "#8a98b8")]
    fig, ax = figure("arms", 3.5)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.80, bottom=0.14)
    w = 0.38
    for i, (cell, classical, _) in enumerate(arms_):
        if classical:
            v = hits("baselines", cell)
            ax.bar(i, v, w, color="#b8c0cc")
            ax.text(i, v + 0.6, str(v), ha="center", va="bottom", color=INK, fontweight="bold")
            continue
        for j, (agent, _, col) in enumerate(models):
            v = hits(agent, cell)
            x = i + (j - 0.5) * w
            ax.bar(x, v, w, color=col)
            ax.text(x, v + 0.6, str(v), ha="center", va="bottom", color=INK, fontweight="bold")
    ax.set_xticks(range(len(arms_)), [a[2] for a in arms_], color=INK)
    ax.set_ylim(0, 25)
    ax.set_yticks([])
    ax.set_ylabel("onsets found, of 25")
    ax.spines["left"].set_visible(False)
    handles = [Patch(color=c, label=l) for _, l, c in models]
    fig.legend(handles=handles, loc="upper left", ncol=2, frameon=False, bbox_to_anchor=(0.06, 1.0), handlelength=1.2)
    save(fig, "arms")


if __name__ == "__main__":
    for f in (rules, realplant, cascade, arms):
        f()
