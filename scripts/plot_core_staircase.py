"""What moved Core's full-task score: measurement fixes, then the task statement.

One measure throughout: items fully right of 80 (state right, action in the allowed set, and the
cause right where the state is ANOMALOUS; a missing or invalid submission counts as wrong), scored
from the saved records with the same judge as scripts/score_core_v2.py. Public set, V1 / V1S arms,
unforced calls.

  ./.venv/bin/python scripts/plot_core_staircase.py docs/figures/core_staircase.png
  ./.venv/bin/python scripts/plot_core_staircase.py docs/figures/core_staircase_zh.png zh
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import load_items  # noqa: E402
from scripts.score_core_v2 import judge  # noqa: E402

TEXT = {
    "en": {"stages": [("Runner v1", "output cap 1,024"), ("Runner v2", "cap 8,192, full records"),
                      ("V1S", "scoring rules stated")],
           "title": "What moved Core's full-task score", "ylabel": "Items fully right, of 80",
           "note": "Full task: state right, action allowed, and the cause right where the state is ANOMALOUS; no valid "
                   "submission counts as wrong.\nDots: each of three runs (bar at the median). V1S: one run per model, a "
                   "candidate, not a qualification. Public set, unforced calls.",
           "font": "DejaVu Sans"},
    "zh": {"stages": [("运行器 v1", "输出上限 1,024"), ("运行器 v2", "上限 8,192，完整记录"), ("V1S", "写明评分规则")],
           "title": "是什么推动了 Core 的全任务得分", "ylabel": "全任务正确的题数（共 80）",
           "note": "全任务：状态正确、动作在允许范围内，状态为 ANOMALOUS 时原因也正确；没有有效提交算错。\n"
                   "圆点：三次运行各一次（柱高为中位数）。V1S 每个模型只跑一次，是候选配置，不是资格通过。公开集，不强制调用。",
           "font": "PingFang SC"},
}
RUNS = {
    "Claude Opus 5.5": [["results/core/claude-opus-5-5/V1", "results/core/claude-opus-5-5/V1.rep1",
                         "results/core/claude-opus-5-5/V1.rep2"],
                        ["results/core_v2/claude-opus-5-5/V1.auto", "results/core_v2/claude-opus-5-5/V1.rep1.auto",
                         "results/core_v2/claude-opus-5-5/V1.rep2.auto"],
                        ["results/core_v2/claude-opus-5-5/V1S.auto"]],
    "Gemini 3.1 Pro": [["results/core/gemini-3.1-pro-preview/V1"],
                       ["results/core_v2/gemini-3.1-pro-preview/V1.auto"],
                       ["results/core_v2/gemini-3.1-pro-preview/V1S.auto"]],
}
RAMP = ["#86b6ef", "#3987e5", "#184f95"]          # ordinal blue, validated light->dark
INK, MUTED, GRID, SURFACE = "#1f2328", "#5b6470", "#e6e8eb", "#fcfcfb"


def full_task(folder, items):
    recs = {p.stem: json.loads(p.read_text()) for p in (ROOT / folder).glob("*.json")}
    total = 0
    for it in items:
        r = recs.get(it["item_id"])
        j = judge(it, r) if r else None
        total += bool(j and j["full"])
    return total


def main(out, lang="en"):
    T = TEXT[lang]
    items = load_items()
    data = {m: [[full_task(f, items) for f in stage] for stage in stages] for m, stages in RUNS.items()}
    plt.rcParams.update({"font.family": T["font"], "font.size": 10})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True, facecolor=SURFACE)
    for ax, (model, stages) in zip(axes, data.items()):
        ax.set_facecolor(SURFACE)
        for x, runs in enumerate(stages):
            mid = sorted(runs)[len(runs) // 2]
            ax.bar(x, mid, width=0.56, color=RAMP[x], zorder=2)
            if len(runs) > 1:
                ax.scatter([x] * len(runs), runs, s=22, color=INK, zorder=3)
                label = f"{min(runs)}–{max(runs)}"
            else:
                label = f"{runs[0]}"
            ax.text(x, max(runs) + 2, label, ha="center", va="bottom", color=INK, fontsize=11, fontweight="bold")
        ax.set_title(model, loc="left", color=INK, fontsize=12, fontweight="bold")
        ax.set_xticks(range(3), [f"{a}\n{b}" for a, b in T["stages"]], color=MUTED, fontsize=9)
        ax.set_ylim(0, 92)
        ax.set_yticks([0, 20, 40, 60, 80])
        ax.tick_params(axis="y", colors=MUTED, length=0)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", color=GRID, zorder=0)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
    axes[0].set_ylabel(T["ylabel"], color=MUTED)
    fig.suptitle(T["title"], x=0.06, y=0.975, ha="left", color=INK, fontsize=14, fontweight="bold")
    fig.text(0.06, 0.005, T["note"], color=MUTED, fontsize=8, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.08, 1, 0.97))
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(json.dumps(data))


if __name__ == "__main__":
    main(*sys.argv[1:3])
