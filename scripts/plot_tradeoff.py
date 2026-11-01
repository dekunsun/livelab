"""The error trade-off plane: hidden twins abstained on against visible faults kept, per model and task statement.

x = hidden twins where the model said UNKNOWN (of 30; the rest are missed escalations).
y = visible twins where the model said ANOMALOUS (of 30; the rest are missed faults).
The gate (docs/product.md, model qualification) is at most 2 of each, so the passing box is 28-30 on both axes.

Every point is scored from the saved records with the judge of scripts/score_core_v2.py; nothing is typed in.
Runs with missing records (Opus 5's third forced V1 run answered 73 of 80) are left out, as in the corrected
readings. V0, V1 and the remedy wording V1R are runner v1; V1S is runner v2; GLM ran only under runner v2.

  ./.venv/bin/python scripts/plot_tradeoff.py docs/figures/tradeoff.png
  ./.venv/bin/python scripts/plot_tradeoff.py docs/figures/tradeoff_zh.png zh
"""
import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import load_items  # noqa: E402
from scripts.score_core_v2 import judge  # noqa: E402

C, C2 = "results/core", "results/core_v2"
# (panel title, {stage: [run folders]}) in reading order; a stage absent from a model was not run.
MODELS = [
    ("Claude Opus 5", {"V0": [f"{C}/claude-opus-5/V0"], "V1": [f"{C}/claude-opus-5/V1", f"{C}/claude-opus-5/V1.rep1"],
                       "V1R": [f"{C}/claude-opus-5/V1R"]}),
    ("GPT-6 Astra", {"V0": [f"{C}/gpt-6-astra/V0"],
                     "V1": [f"{C}/gpt-6-astra/V1", f"{C}/gpt-6-astra/V1.rep1", f"{C}/gpt-6-astra/V1.rep2"],
                     "V1R": [f"{C}/gpt-6-astra/V1R"], "V1S": [f"{C2}/gpt-6-astra/V1S"]}),
    ("Gemini 3.8 Live", {"V0": [f"{C}/gemini-3.8-live/V0"], "V1": [f"{C}/gemini-3.8-live/V1"]}),
    ("Gemini 3.8 Flash", {"V0": [f"{C}/gemini-3.8-flash/V0"], "V1": [f"{C}/gemini-3.8-flash/V1"]}),
    ("Gemini 3.1 Pro", {"V0": [f"{C}/gemini-3.1-pro-preview/V0"], "V1": [f"{C}/gemini-3.1-pro-preview/V1"],
                        "V1S": [f"{C2}/gemini-3.1-pro-preview/V1S.auto"]}),
    ("Claude Opus 5.5", {"V0": [f"{C}/claude-opus-5-5/V0"],
                         "V1": [f"{C}/claude-opus-5-5/V1", f"{C}/claude-opus-5-5/V1.rep1", f"{C}/claude-opus-5-5/V1.rep2"],
                         "V1S": [f"{C2}/claude-opus-5-5/V1S.auto"]}),
    ("GLM 5.3 Flash (open weights)", {"V1": [f"{C2}/z-ai/glm-5.3-flash/V1.auto"],
                                      "V1S": [f"{C2}/z-ai/glm-5.3-flash/V1S.auto"]}),
]
ORDER = ["V0", "V1", "V1S"]
TEXT = {
    "en": {"title": "Telling the model the gap trades one error for the other; stating the rules moves it to the corner",
           "x": "Hidden twins: abstained (of 30)", "y": "Visible faults kept (of 30)",
           "stage": {"V0": "V0 nothing stated", "V1": "V1 gap stated", "V1S": "V1S rules stated", "V1R": "V1R remedy wording"},
           "gate": "gate", "block": "      abst · kept", "rules": "rules anyway:\nmissed escalations", "drops": "abstains and\ndrops visible faults",
           "key_title": "How to read a panel",
           "key": ["One model per panel, on Core's 30 matched",
                   "pairs. Top right is right on both; the green",
                   "box is the gate (at most 2 misses of each).",
                   "Arrows follow the task statement. Small dots",
                   "are repeated runs; the marker is their median.",
                   "V0, V1, V1R: runner v1. V1S: runner v2.",
                   "Public set: candidates, not qualifications."],
           "font": "DejaVu Sans"},
    "zh": {"title": "告诉模型缺口，一种错误换成另一种；写明评分规则，才走到右上角",
           "x": "隐藏孪生题：弃权数（共 30）", "y": "可见故障：保住数（共 30）",
           "stage": {"V0": "V0 不告知", "V1": "V1 告知缺口", "V1S": "V1S 写明规则", "V1R": "V1R 补救措辞"},
           "gate": "门槛", "block": "      弃权 · 保住", "rules": "照样下结论：\n漏送审", "drops": "弃权，同时\n丢掉可见故障",
           "key_title": "怎么读",
           "key": ["每个小图是一个模型在 LiveLab Core",
                   "30 对孪生题上的表现。右上角两边都对；",
                   "绿色方框是上线门槛（每类最多错 2 题）。",
                   "",
                   "箭头按任务说法：V0 → V1 → V1S。",
                   "小点是重复运行，标记在中位数。",
                   "",
                   "V0、V1、V1R：运行器 v1；V1S：运行器 v2。",
                   "除有多个小点外，每个模型只跑一次。",
                   "公开集；是候选结果，不是资格通过。"],
           "font": "PingFang SC"},
}
STAGE_COLOR = {"V0": "#9db8dc", "V1": "#3f73b8", "V1S": "#011F5B"}     # one hue, light -> dark
REMEDY = "#8a8f99"
INK, MUTED, GRID, SURFACE, GATE = "#1f2328", "#5b6470", "#e6e8eb", "#ffffff", "#e5f4e4"


def point(folder, items):
    recs = {p.stem: json.loads(p.read_text()) for p in (ROOT / folder).glob("*.json")}
    if len(recs) < len(items):
        raise SystemExit(f"{folder}: {len(recs)} records of {len(items)}; incomplete runs are not plotted")
    hidden = visible = 0
    for it in items:
        j = judge(it, recs.get(it["item_id"]))
        if j is None:
            continue
        hidden += it["role"] == "hidden" and j["said"] == "UNKNOWN"
        visible += it["role"] == "visible" and j["said"] == "ANOMALOUS"
    return hidden, visible


def main(out, lang="en"):
    t = TEXT[lang]
    plt.rcParams.update({"font.family": t["font"], "font.size": 10, "axes.unicode_minus": False})
    items = load_items()
    fig, axes = plt.subplots(2, 4, figsize=(14, 7.6), dpi=150, facecolor=SURFACE)
    fig.subplots_adjust(left=0.06, right=0.985, top=0.86, bottom=0.09, wspace=0.28, hspace=0.42)
    data = {}
    for ax, (name, stages) in zip(axes.flat, MODELS):
        pts = {s: [point(f, items) for f in fs] for s, fs in stages.items()}
        data[name] = pts
        med = {s: (statistics.median(p[0] for p in v), statistics.median(p[1] for p in v)) for s, v in pts.items()}
        ax.set_facecolor(SURFACE)
        ax.add_patch(Rectangle((27.5, 27.5), 3.3, 3.3, facecolor=GATE, edgecolor="#7fb77e", lw=1, zorder=0))
        ax.text(29.15, 31.4, t["gate"], ha="center", va="bottom", fontsize=8, color="#3d7a3c")
        ax.set_xlim(-1.5, 34.5)
        ax.set_ylim(-1.5, 33.5)
        ax.set_xticks([0, 10, 20, 30])
        ax.set_yticks([0, 10, 20, 30])
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
        ax.set_title(name, loc="left", fontsize=11, fontweight="bold", color=INK, pad=6)
        seq = [s for s in ORDER if s in med]
        for a, b in zip(seq, seq[1:]):
            if med[a] != med[b]:
                ax.add_patch(FancyArrowPatch(med[a], med[b], arrowstyle="-|>", mutation_scale=12, lw=1.6,
                                             color=STAGE_COLOR[b], shrinkA=6, shrinkB=7, zorder=2))
        if "V1R" in med:
            ax.add_patch(FancyArrowPatch(med["V1"], med["V1R"], arrowstyle="-|>", mutation_scale=10, lw=1.1,
                                         color=REMEDY, ls=(0, (3, 2)), shrinkA=6, shrinkB=6, zorder=2))
        for s, runs in pts.items():
            col = REMEDY if s == "V1R" else STAGE_COLOR[s]
            if len(runs) > 1:
                ax.scatter([p[0] for p in runs], [p[1] for p in runs], s=10, color=col, alpha=0.55, zorder=3, lw=0)
            mk = "s" if s == "V1R" else "o"
            face = SURFACE if s == "V1R" else col
            ax.scatter(*med[s], s=58, marker=mk, facecolor=face, edgecolor=col, lw=1.6, zorder=4)
        # short stage tags beside the points; exact counts (with run ranges) in the empty lower-left corner
        groups = {}
        for s in ["V0", "V1", "V1R", "V1S"]:
            if s in med:
                groups.setdefault(med[s], []).append(s)
        for (x, y), ss in groups.items():
            tag = " = ".join(ss)
            col = REMEDY if ss == ["V1R"] else INK
            if x >= 26:
                ax.text(x + 1.2, y, tag, ha="left", va="center", fontsize=8.5, color=col, fontweight="bold")
            elif y >= 27 or (x < 5):
                ax.text(x - 0.4, y + 2.1, tag, ha="left", va="center", fontsize=8.5, color=col, fontweight="bold")
            else:
                ax.text(x, y - 2.3, tag, ha="center", va="center", fontsize=8.5, color=col, fontweight="bold")

        def rng(vals):
            lo, hi = min(vals), max(vals)
            return f"{lo}" if lo == hi else f"{lo}–{hi}"

        rows = [f"{s:<4} {rng([p[0] for p in pts[s]]):>5} · {rng([p[1] for p in pts[s]])}"
                for s in ["V0", "V1", "V1R", "V1S"] if s in pts]
        ax.text(0.03, 0.03, t["block"] + "\n" + "\n".join(rows), transform=ax.transAxes, ha="left", va="bottom",
                fontsize=7.6, color=MUTED, family="monospace" if lang == "en" else t["font"], linespacing=1.35)
        ax.set_xlabel(t["x"], fontsize=8.5, color=MUTED)
        ax.set_ylabel(t["y"], fontsize=8.5, color=MUTED)
    # the eighth cell: how to read
    key = axes.flat[7]
    key.axis("off")
    key.text(0.0, 1.0, t["key_title"], fontsize=11, fontweight="bold", color=INK, va="top", transform=key.transAxes)
    handles = [plt.Line2D([], [], marker="o", ls="", markersize=7, color=STAGE_COLOR[s], label=t["stage"][s]) for s in ORDER]
    handles.append(plt.Line2D([], [], marker="s", ls="", markersize=7, markerfacecolor=SURFACE, markeredgecolor=REMEDY,
                              color=REMEDY, label=t["stage"]["V1R"]))
    key.legend(handles=handles, loc="upper left", bbox_to_anchor=(-0.02, 0.9), frameon=False, fontsize=8.6,
               handletextpad=0.3, borderaxespad=0)
    key.text(0.0, 0.5, "\n".join(t["key"]), fontsize=8.3, color=INK, va="top", linespacing=1.4,
             transform=key.transAxes)
    fig.suptitle(t["title"], x=0.06, ha="left", fontsize=13.5, fontweight="bold", color=INK, y=0.965)
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")
    for name, pts in data.items():
        print(name, {s: v for s, v in pts.items()})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/figures/tradeoff.png", sys.argv[2] if len(sys.argv) > 2 else "en")
