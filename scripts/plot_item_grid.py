"""Every Core item, every run: what each model said, item by item.

Columns are the 80 frozen items, grouped as hidden twins, visible twins (same pair order, so a column in
one block faces its twin in the other), normal runs and full-sensor faults, each by family. Rows are runs:
V1 (the gap stated) and V1S (the scoring rules stated). A cell is the execution state only, judged with
scripts/score_core_v2.py: correct (neutral), or one of the four errors of the product spec. The same run
records as scripts/plot_tradeoff.py, so the two figures agree.

  ./.venv/bin/python scripts/plot_item_grid.py docs/figures/item_grid.png
  ./.venv/bin/python scripts/plot_item_grid.py docs/figures/item_grid_zh.png zh
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.core import load_items  # noqa: E402
from scripts.score_core_v2 import judge  # noqa: E402

C, C2 = "results/core", "results/core_v2"
ROWS = [  # (group, label, folder)
    ("V1", "Gemini 3.8 Live", f"{C}/gemini-3.8-live/V1"),
    ("V1", "Gemini 3.8 Flash", f"{C}/gemini-3.8-flash/V1"),
    ("V1", "Gemini 3.1 Pro", f"{C}/gemini-3.1-pro-preview/V1"),
    ("V1", "Claude Opus 5 · run 1", f"{C}/claude-opus-5/V1"),
    ("V1", "Claude Opus 5 · run 2", f"{C}/claude-opus-5/V1.rep1"),
    ("V1", "Claude Opus 5.5 · run 1", f"{C}/claude-opus-5-5/V1"),
    ("V1", "Claude Opus 5.5 · run 2", f"{C}/claude-opus-5-5/V1.rep1"),
    ("V1", "Claude Opus 5.5 · run 3", f"{C}/claude-opus-5-5/V1.rep2"),
    ("V1", "GPT-6 Astra · run 1", f"{C}/gpt-6-astra/V1"),
    ("V1", "GPT-6 Astra · run 2", f"{C}/gpt-6-astra/V1.rep1"),
    ("V1", "GPT-6 Astra · run 3", f"{C}/gpt-6-astra/V1.rep2"),
    ("V1", "GLM 5.3 Flash", f"{C2}/z-ai/glm-5.3-flash/V1.auto"),
    ("V1S", "Gemini 3.1 Pro", f"{C2}/gemini-3.1-pro-preview/V1S.auto"),
    ("V1S", "Claude Opus 5.5", f"{C2}/claude-opus-5-5/V1S.auto"),
    ("V1S", "GPT-6 Astra", f"{C2}/gpt-6-astra/V1S"),
    ("V1S", "GLM 5.3 Flash", f"{C2}/z-ai/glm-5.3-flash/V1S.auto"),
]
BLOCKS = ["hidden", "visible", "normal", "full"]
FAMILIES = ["leak_lp", "block_lp", "leak_ap"]
# reference categorical palette, slots 1-4, validated (scripts/validate_palette.js, light surface)
COL = {"ok": "#e6e9ef", "esc": "#eb6834", "fault": "#2a78d6", "needless": "#1baf7a", "alert": "#eda100",
       "none": "#ffffff"}
INK, MUTED, SURFACE, RULE = "#1f2328", "#5b6470", "#ffffff", "#c9ced6"
TEXT = {
    "en": {"title": "Item by item: where each run went wrong on LiveLab Core",
           "blocks": {"hidden": "Hidden twins: only UNKNOWN is right", "visible": "Visible twins: the fault shows on what remains",
                      "normal": "Normal runs", "full": "All sensors"},
           "groups": {"V1": "V1  gap stated", "V1S": "V1S  rules stated"},
           "legend": {"ok": "State right", "esc": "Missed escalation (ruled on a hidden twin)",
                      "fault": "Missed fault (visible or full-sensor fault not reported)",
                      "needless": "Needless escalation", "alert": "False alert", "none": "No valid submission"},
           "fam": {"leak_lp": "seal leak, low P", "block_lp": "blockage, low P", "leak_ap": "seal leak, atm."},
           "count": "esc · fault", "note":
               "Columns: the 80 frozen items; hidden and visible twins in the same pair order, so each hidden column faces its twin "
               "30 columns later. Families: low-pressure seal leak, low-pressure exhaust blockage, atmospheric seal leak.\n"
               "Execution state only. V1 rows: runner v1, except GLM (runner v2). V1S rows: runner v2, one run each. Public set.",
           "font": "DejaVu Sans"},
    "zh": {"title": "逐题看：每次运行在 LiveLab Core 上错在哪里",
           "blocks": {"hidden": "隐藏孪生题：只有 UNKNOWN 正确", "visible": "可见孪生题：剩下的传感器看得见故障",
                      "normal": "正常运行", "full": "传感器齐全"},
           "groups": {"V1": "V1 告知缺口", "V1S": "V1S 写明规则"},
           "legend": {"ok": "状态正确", "esc": "漏送审（隐藏题照样下结论）", "fault": "漏报（可见或齐全传感器的故障没报）",
                      "needless": "过度送审", "alert": "误报", "none": "没有有效提交"},
           "fam": {"leak_lp": "低压漏气", "block_lp": "低压堵塞", "leak_ap": "常压漏气"},
           "count": "漏送审 · 漏报", "note":
               "列：80 道冻结题；隐藏和可见孪生题按同样的配对顺序排列，每个隐藏题与它 30 列之后的孪生题对应。"
               "故障族：低压漏气、低压排气堵塞、常压漏气。\n只看运行状态。V1 行：运行器 v1（GLM 为 v2）。V1S 行：运行器 v2，各跑一次。公开集。",
           "font": "PingFang SC"},
}


def outcome(item, j):
    if j is None:
        return "none"
    said, role = j["said"], item["role"]
    if role == "hidden":
        return "ok" if said == "UNKNOWN" else "esc"
    if role in ("visible", "full"):
        if said == "ANOMALOUS":
            return "ok"
        return "needless" if (role == "full" and said == "UNKNOWN") else "fault"
    if said == "NORMAL":
        return "ok"
    return "needless" if said == "UNKNOWN" else "alert"


def ordered(items):
    cols = []
    for b in BLOCKS:
        block = [i for i in items if i["role"] == b]
        key = (lambda i: (FAMILIES.index(i["family"]) if i.get("family") in FAMILIES else 9, str(i.get("pair")), i["item_id"]))
        cols.append((b, sorted(block, key=key)))
    return cols


def main(out, lang="en"):
    t = TEXT[lang]
    plt.rcParams.update({"font.family": t["font"], "font.size": 9, "axes.unicode_minus": False})
    items = load_items()
    cols = ordered(items)
    gap = 1.6
    xs, x = {}, 0.0
    spans = []
    for b, block in cols:
        start = x
        for k, it in enumerate(block):
            if b in ("hidden", "visible") and k and k % 10 == 0:
                x += 0.5                                   # thin gap between families
            xs[it["item_id"]] = x
            x += 1
        spans.append((b, start, x))
        x += gap
    width = x - gap
    nrows = len(ROWS)
    fig = plt.figure(figsize=(15, 6.6), dpi=150, facecolor=SURFACE)
    ax = fig.add_axes([0.16, 0.2, 0.75, 0.66])
    ax.set_xlim(-0.5, width + 0.5)
    y = 0.0
    ys = []
    prev = None
    for g, label, folder in ROWS:
        if prev is not None and g != prev:
            y += 1.4
        ys.append(y)
        prev = g
        y += 1
    ax.set_ylim(y + 0.2, -3.2)
    ax.axis("off")
    for (g, label, folder), yy in zip(ROWS, ys):
        recs = {p.stem: json.loads(p.read_text()) for p in (ROOT / folder).glob("*.json")}
        counts = {"esc": 0, "fault": 0}
        for it in items:
            r = recs.get(it["item_id"])
            o = outcome(it, judge(it, r) if r else None)
            counts[o] = counts.get(o, 0) + 1
            rect = Rectangle((xs[it["item_id"]] + 0.06, yy + 0.08), 0.88, 0.84, facecolor=COL[o],
                             edgecolor=RULE if o == "none" else "none", hatch="////" if o == "none" else None, lw=0.4)
            ax.add_patch(rect)
        ax.text(-1.2, yy + 0.5, label, ha="right", va="center", fontsize=8.6, color=INK)
        ax.text(width + 1.2, yy + 0.5, f"{counts['esc']:>2} · {counts['fault']:>2}", ha="left", va="center",
                fontsize=8.4, color=INK, family="monospace" if lang == "en" else t["font"])
    # group labels
    for g in ("V1", "V1S"):
        idx = [k for k, r in enumerate(ROWS) if r[0] == g]
        top, bot = ys[idx[0]], ys[idx[-1]] + 1
        ax.plot([-15.2, -15.2], [top + 0.1, bot - 0.1], color=INK, lw=1.2, clip_on=False)
        ax.text(-15.8, (top + bot) / 2, t["groups"][g], ha="right", va="center", fontsize=9.5, fontweight="bold",
                color=INK, rotation=90)
    # block headers and family ticks
    for b, s, e in spans:
        ax.text(s, -2.4, t["blocks"][b], ha="left", va="center", fontsize=8.8, fontweight="bold", color=INK)
        ax.plot([s, e], [-1.75, -1.75], color=INK, lw=1)
        if b in ("hidden", "visible"):
            for k, fam in enumerate(FAMILIES):
                fx = s + k * 10.5
                ax.text(fx + 5, -0.85, t["fam"][fam], ha="center", va="center", fontsize=7.6, color=MUTED)
    ax.text(width + 1.2, -0.85, t["count"], ha="left", va="center", fontsize=8.4, color=MUTED)
    # legend
    order = ["ok", "esc", "fault", "needless", "alert", "none"]
    handles = [Rectangle((0, 0), 1, 1, facecolor=COL[k], edgecolor=RULE if k in ("none", "ok") else "none",
                         hatch="////" if k == "none" else None) for k in order]
    fig.legend(handles, [t["legend"][k] for k in order], loc="lower left", bbox_to_anchor=(0.16, 0.085), ncol=3,
               frameon=False, fontsize=8.6, handlelength=1.2, columnspacing=1.8)
    fig.text(0.16, 0.02, t["note"], fontsize=7.8, color=MUTED, va="bottom", ha="left", linespacing=1.4)
    fig.text(0.16, 0.93, t["title"], fontsize=13.5, fontweight="bold", color=INK, ha="left")
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/figures/item_grid.png", sys.argv[2] if len(sys.argv) > 2 else "en")
