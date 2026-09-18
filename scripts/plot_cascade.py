"""Figure: the LPCVD seal-leak cascade. Telemetry against the reference band, and the
evidence-supported answer under each sensor condition. Telemetry is author-constructed."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.episode import load, render  # noqa: E402
from livelab.observability import event_times, reference_band  # noqa: E402
from livelab.protocol import PROTOCOLS  # noqa: E402

COLORS = {"NORMAL": "#9bc59d", "ANOMALOUS": "#d9534f", "UNKNOWN": "#c8c8c8"}


def main():
    ep = load(ROOT / "scenarios/pilot/cvd_seal_leak_lpcvd.yaml")
    protocol = PROTOCOLS[ep["protocol"]]
    times = event_times(protocol, 60) / 60
    band = reference_band(protocol, ep["regime"], 60)
    events, _ = render(ep, "base")
    conds = list(ep["sensor_conditions"])
    truths = {c: render(ep, c)[1] for c in conds}

    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [2, 2, 1.4]})
    for ax, ch, unit in ((axes[0], "O2_exhaust", "ppm"), (axes[1], "P_tube", "Torr")):
        m, s = band[ch]
        ax.fill_between(times, m - 4 * s, m + 4 * s, color="#dbe7f3", label="reference ±4σ (100 normal runs)")
        ax.plot(times, [e["telemetry"][ch] for e in events], color="#1f4e79", lw=1.2, label="this run")
        ax.set_ylabel(f"{ch} ({unit})")
        ax.axvline(ep["fault"]["t_fault_s"] / 60, color="#d9534f", ls="--", lw=1)
        ax.legend(loc="upper left", fontsize=8, frameon=False)
    axes[0].set_ylim(0, 60)
    axes[1].set_ylim(2.8, 4.3)
    axes[0].set_title("LPCVD seal leak: the evidence-supported answer depends on which sensors exist", fontsize=11)

    labels = {"base": "pressure + O₂", "no_o2": "pressure only", "no_o2_no_pressure": "neither"}
    for i, c in enumerate(conds):
        for r in truths[c]:
            cause = r["acceptable_specific_cause"][0]
            axes[2].barh(i, 1, left=times[r["event"]] - 1, color=COLORS[r["execution_state"]],
                         hatch="///" if cause == "undetermined" else None, edgecolor="white", lw=0)
    axes[2].set_yticks(range(len(conds)), [labels[c] for c in conds])
    axes[2].invert_yaxis()
    axes[2].set_xlabel("simulated time (min)")
    for name, col in COLORS.items():
        axes[2].barh(0, 0, color=col, label=name)
    axes[2].barh(0, 0, color=COLORS["ANOMALOUS"], hatch="///", edgecolor="white", label="ANOMALOUS, cause undetermined")
    axes[2].legend(loc="upper center", bbox_to_anchor=(0.5, -0.45), fontsize=7, ncol=4, frameon=False)
    for ax in axes:
        ax.set_xlim(35, 70)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    fig.text(0.01, 0.005, "Telemetry is author-constructed (LiveLab simulator); the fault type follows DeepMind arXiv 2608.26701.",
             fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ROOT / "docs/figures/cascade_lpcvd.png", dpi=160)


if __name__ == "__main__":
    main()
