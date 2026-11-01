"""Page-one figure: the two guardrail errors across task statements, for the four models run with the rules stated.

Left: missed escalations (hidden twins not abstained on, of 30). Right: missed faults (visible twins not reported,
of 30). x: V0 (nothing stated), V1 (the gap stated), V1S (the scoring rules stated). Scored from the run records with
the same function as scripts/plot_tradeoff.py; repeated runs enter at their median. GLM 5.3 Flash has no V0 run.

  ./.venv/bin/python scripts/plot_hero.py docs/figures/hero.png
  ./.venv/bin/python scripts/plot_hero.py docs/figures/hero_zh.png zh
"""
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import load_items  # noqa: E402
from scripts.plot_tradeoff import MODELS, point  # noqa: E402

KEEP = ["GPT-6 Astra", "Gemini 3.1 Pro", "Claude Opus 5.5", "GLM 5.3 Flash (open weights)"]
SHORT = {"GPT-6 Astra": "GPT-6 Astra", "Gemini 3.1 Pro": "Gemini 3.1 Pro", "Claude Opus 5.5": "Claude Opus 5.5",
         "GLM 5.3 Flash (open weights)": "GLM 5.3 Flash"}
COLOR = {"GPT-6 Astra": "#1baf7a", "Gemini 3.1 Pro": "#2a78d6", "Claude Opus 5.5": "#eb6834",
         "GLM 5.3 Flash (open weights)": "#eda100"}           # reference palette slots, validated
STAGES = ["V0", "V1", "V1S"]
INK, MUTED, GRID, SURFACE, GATE = "#1f2328", "#5b6470", "#e6e8eb", "#ffffff", "#e5f4e4"
TEXT = {
    "en": {"esc": "Missed escalations (of 30)", "fault": "Missed faults (of 30)",
           "esc_sub": "ruled on a hidden twin instead of abstaining", "fault_sub": "a fault the remaining sensors showed, not reported",
           "stages": ["V0\nnothing stated", "V1\ngap stated", "V1S\nrules stated"], "gate": "gate: at most 2",
           "font": "DejaVu Sans"},
    "zh": {"esc": "漏送审（共 30）", "fault": "漏报（共 30）",
           "esc_sub": "隐藏孪生题上照样下结论", "fault_sub": "剩下的传感器看得见的故障没报",
           "stages": ["V0\n不告知", "V1\n告知缺口", "V1S\n写明规则"], "gate": "门槛：最多 2",
           "font": "PingFang SC"},
}


def main(out, lang="en"):
    t = TEXT[lang]
    plt.rcParams.update({"font.family": t["font"], "font.size": 10, "axes.unicode_minus": False})
    items = load_items()
    series = {}
    for name, stages in MODELS:
        if name not in KEEP:
            continue
        esc, fault = {}, {}
        for s in STAGES:
            if s in stages:
                pts = [point(f, items) for f in stages[s]]
                esc[s] = 30 - statistics.median(p[0] for p in pts)
                fault[s] = 30 - statistics.median(p[1] for p in pts)
        series[name] = (esc, fault)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), dpi=200, facecolor=SURFACE)
    fig.subplots_adjust(left=0.05, right=0.84, top=0.82, bottom=0.2, wspace=0.5)
    offsets = dict(zip(KEEP, [-0.6, -0.2, 0.2, 0.6]))
    for ax, key, title, sub in ((axes[0], 0, t["esc"], t["esc_sub"]), (axes[1], 1, t["fault"], t["fault_sub"])):
        ax.set_facecolor(SURFACE)
        ax.axhspan(-1, 2.5, color=GATE, zorder=0)
        ax.text(-0.2, 3.0, t["gate"], ha="left", va="bottom", fontsize=8, color="#3d7a3c")
        ax.set_xlim(-0.25, 2.15)
        ax.set_ylim(-1, 31.5)
        ax.set_xticks(range(3))
        ax.set_xticklabels(t["stages"], fontsize=9, color=INK)
        ax.set_yticks([0, 10, 20, 30])
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, length=0)
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=18)
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=8.6, color=MUTED, va="bottom")
        ends = []
        for name in KEEP:
            vals = series[name][key]
            xs = [STAGES.index(s) for s in STAGES if s in vals]
            ys = [vals[s] + offsets[name] for s in STAGES if s in vals]
            ax.plot(xs, ys, color=COLOR[name], lw=2, marker="o", markersize=6.5, markeredgecolor=SURFACE,
                    markeredgewidth=1.2, zorder=3)
            ends.append([ys[-1], name, vals["V1S"]])
        ends.sort(key=lambda e: e[0])                     # spread end labels so they never overlap
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 2.4)
        for y, name, v in ends:
            ax.plot([2.2, 2.32], [y, y], color=COLOR[name], lw=2.6, clip_on=False, solid_capstyle="butt")
            ax.text(2.37, y, f"{SHORT[name]}  {v:g}", va="center", fontsize=8.6, color=INK, clip_on=False)
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")
    for k, v in series.items():
        print(k, v)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/figures/hero.png", sys.argv[2] if len(sys.argv) > 2 else "en")
