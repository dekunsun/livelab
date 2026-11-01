"""The real plant with its uncertainty drawn: detection against false alerts, and abstention, per model.

Counts are scored from the saved records exactly as scripts/score_realdata.py does (last report_assessment;
full -> ANOMALOUS is a detection, blind -> UNKNOWN/CANNOT_VERIFY is an abstention, control -> ANOMALOUS is a
false alert). Intervals are 95% Wilson score intervals for a count out of n. v1 = the wrong instrument
description, v2 = corrected and rerun (docs/realdata_v2_preregistration.md).

  (add a third argument "poster" for the poster size: smaller canvas, larger relative text, 300 dpi)
  ./.venv/bin/python scripts/plot_realdata_ci.py docs/figures/realdata_ci.png
  ./.venv/bin/python scripts/plot_realdata_ci.py docs/figures/realdata_ci_zh.png zh
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.score_realdata import ABSTAIN, LEGENDS, MODELS, load  # noqa: E402

NAMES = {"gemini-3.8-live": "Gemini 3.8 Live", "claude-opus-5": "Claude Opus 5", "gpt-6-astra": "GPT-6 Astra"}
COLOR = {"gemini-3.8-live": "#2a78d6", "claude-opus-5": "#eb6834", "gpt-6-astra": "#1baf7a"}  # validated slots 1-3
INK, MUTED, GRID, SURFACE = "#1f2328", "#5b6470", "#e6e8eb", "#ffffff"
TEXT = {
    "en": {"title": "On the real plant, the intervals are wide and the abstention result still holds",
           "a": "Detection against false alerts", "b": "Abstention with the observing instruments removed", "b_short": "Abstention, instruments removed",
           "x": "Fault-free runs called anomalous (of 37)", "y": "Anomalies detected with full evidence (of 31)",
           "bx": "Blind items answered UNKNOWN (of 31)", "ideal": "ideal", "target": "right answer on every item",
           "v1": "v1 description wrong", "v2": "v2 corrected",
           "note": "68 runs (31 anomalous, 37 fault-free) of a public 119-run batch distillation dataset (Zenodo 17395543, CC BY 4.0); "
                   "truth from the plant's expert annotations. One run per item.\n"
                   "Bars: 95% Wilson intervals. Arrows: v1 (instrument description wrong) to v2 (corrected and rerun).",
           "font": "DejaVu Sans"},
    "zh": {"title": "真实装置上，区间很宽，弃权的结论仍然成立",
           "a": "检出率与误报率", "b": "去掉观测仪表后的弃权", "b_short": "去掉观测仪表后的弃权",
           "x": "无故障运行被判异常（共 37）", "y": "证据齐全时检出的异常（共 31）",
           "bx": "盲测题回答 UNKNOWN（共 31）", "ideal": "理想", "target": "每题都答对",
           "v1": "v1 描述有误", "v2": "v2 已更正",
           "note": "公开间歇精馏数据集 119 次运行中的 68 次（31 次异常、37 次无故障；Zenodo 17395543，CC BY 4.0），以装置专家标注为真值。每题跑一次。\n"
                   "误差线：95% Wilson 区间。箭头：v1（仪器描述有误）到 v2（更正后重跑）。",
           "font": "PingFang SC"},
}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h) * n, min(1.0, c + h) * n


def counts():
    out = {}
    for m in MODELS:
        for lg, d in LEGENDS.items():
            r = load(d, m)
            by = {c: [x for x in r.values() if x["condition"] == c] for c in ("full", "blind", "control")}
            out[(m, lg)] = {"det": sum(x["said"] == "ANOMALOUS" for x in by["full"]), "nf": len(by["full"]),
                            "ab": sum(x["said"] in ABSTAIN for x in by["blind"]), "nb": len(by["blind"]),
                            "fa": sum(x["said"] == "ANOMALOUS" for x in by["control"]), "nc": len(by["control"])}
    return out


def main(out, lang="en"):
    t = TEXT[lang]
    plt.rcParams.update({"font.family": t["font"], "font.size": 9.5, "axes.unicode_minus": False})
    s = counts()
    k = 0.74 if POSTER else 1.0
    fig, (a, b) = plt.subplots(1, 2, figsize=(13 * k, 5.6 * k), dpi=300 if POSTER else 150, facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1.15, 1]})
    fig.subplots_adjust(left=0.065, right=0.975, top=0.86 if POSTER else 0.82, bottom=0.13 if POSTER else 0.2, wspace=0.34 if POSTER else 0.28)
    for ax in (a, b):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, length=0)
    # (a) detection against false alerts
    a.set_xlim(-1.5, 38.5)
    a.set_ylim(-1.5, 33)
    a.set_xticks([0, 10, 20, 30, 37])
    a.set_yticks([0, 10, 20, 31])
    a.scatter([0], [31], marker="*", s=140, color=INK, zorder=5)
    a.text(1.0, 31.6, t["ideal"], fontsize=8.5, color=INK, va="bottom")
    for m in MODELS:
        for lg in LEGENDS:
            c = s[(m, lg)]
            x, y = c["fa"], c["det"]
            xl, xh = wilson(c["fa"], c["nc"])
            yl, yh = wilson(c["det"], c["nf"])
            col = COLOR[m]
            alpha = 0.35 if lg == "v1" else 1.0
            a.plot([xl, xh], [y, y], color=col, lw=1.3, alpha=alpha, zorder=2)
            a.plot([x, x], [yl, yh], color=col, lw=1.3, alpha=alpha, zorder=2)
            a.scatter([x], [y], s=60, facecolor=SURFACE if lg == "v1" else col, edgecolor=col, lw=1.6, zorder=4,
                      alpha=0.8 if lg == "v1" else 1)
        p1, p2 = s[(m, "v1")], s[(m, "v2")]
        a.add_patch(FancyArrowPatch((p1["fa"], p1["det"]), (p2["fa"], p2["det"]), arrowstyle="-|>", mutation_scale=11,
                                    lw=1.2, color=COLOR[m], shrinkA=6, shrinkB=7, zorder=3))
        x, y = p2["fa"], p2["det"]
        ha, dx = ("right", -1.2) if x > 25 else ("left", 1.4)
        a.text(x + dx, y - 2.2, f"{NAMES[m]}  {p2['det']}/31 · {p2['fa']}/37", ha=ha, va="top", fontsize=8.6,
               color=INK, fontweight="bold")
    a.set_xlabel(t["x"], color=MUTED)
    a.set_ylabel(t["y"], color=MUTED)
    a.set_title(t["a"], loc="left", fontsize=11, fontweight="bold", color=INK)
    # (b) abstention on blind items
    b.set_xlim(-1, 33)
    b.set_xticks([0, 10, 20, 31])
    b.axvline(31, color=INK, lw=1, ls=(0, (3, 2)))
    b.text(30.6, 2.75, t["target"], ha="right", va="center", fontsize=8, color=INK)
    b.set_ylim(-0.6, 2.9)
    b.set_yticks(range(len(MODELS)))
    b.set_yticklabels([NAMES[m] for m in MODELS], color=INK)
    for i, m in enumerate(MODELS):
        for lg, off in (("v1", -0.16), ("v2", 0.16)):
            c = s[(m, lg)]
            lo, hi = wilson(c["ab"], c["nb"])
            col = COLOR[m]
            b.plot([lo, hi], [i + off, i + off], color=col, lw=1.6, alpha=0.4 if lg == "v1" else 1)
            b.scatter([c["ab"]], [i + off], s=55, facecolor=SURFACE if lg == "v1" else col, edgecolor=col, lw=1.6, zorder=3)
            b.text(hi + 0.7, i + off, f"{c['ab']}/31  {lg}", va="center", fontsize=8.2, color=INK)
    b.invert_yaxis()
    b.set_xlabel(t["bx"], color=MUTED)
    b.set_title(t["b_short"] if POSTER else t["b"], loc="left", fontsize=11, fontweight="bold", color=INK)
    handles = [plt.Line2D([], [], marker="o", ls="", markersize=7, markerfacecolor=SURFACE, markeredgecolor=MUTED,
                          label=t["v1"]),
               plt.Line2D([], [], marker="o", ls="", markersize=7, color=MUTED, label=t["v2"])]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.975, 0.995 if POSTER else 0.93), ncol=2, frameon=False, fontsize=8.8)
    if not POSTER:
        fig.suptitle(t["title"], x=0.065, ha="left", y=0.965, fontsize=13.5, fontweight="bold", color=INK)
    if not POSTER:
        fig.text(0.065, 0.025, t["note"], fontsize=7.9, color=MUTED, linespacing=1.4)
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")
    for k, v in s.items():
        print(k, v)


POSTER = "poster" in sys.argv[3:]

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/figures/realdata_ci.png", sys.argv[2] if len(sys.argv) > 2 else "en")
