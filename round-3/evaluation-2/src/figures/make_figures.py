#!/usr/bin/env python3
"""figures/argmax_vs_landing.{pdf,png}: hit rate of each likelihood argmax on the realised landing, with Wilson 95%
intervals (asymmetric, so hand-written with the aii-data-fig-gen house style rather than the symmetric-error forest
type). Reads results/c1_diagnostics.json only."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
# house-style helpers of the aii-data-fig-gen skill, when available (set AII_DATA_FIG_GEN_SCRIPTS to its scripts/ dir)
SKILL = Path(os.environ.get("AII_DATA_FIG_GEN_SCRIPTS", "__missing__"))
if SKILL.is_dir():
    sys.path.insert(0, str(SKILL))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    from chart_style import apply_house_style, place_legend, fit_legends, clear_legends_of_data, fit_tick_labels, fit_titles  # noqa: E402
    from chart_geometry import assert_text_is_legible  # noqa: E402
    HOUSE = True
except ImportError:
    HOUSE = False


def main() -> None:
    d = json.loads((WS / "results" / "c1_diagnostics.json").read_text())
    met = d["event_table"]["metrics"]
    preds = [("Gbar_neutral", "full gain argmax"), ("s_neutral", "residual argmax"), ("mass", "implied-mass argmax")]
    models = [("Qwen", "Qwen3-8B"), ("meta-llama", "Llama-3.1-8B")]
    if HOUSE:
        apply_house_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
    colors = ["#0173B2", "#DE8F05"]
    y = 0
    yt, yl = [], []
    for pi, (pk, pname) in enumerate(preds):
        for mi, (mk, mname) in enumerate(models):
            b = met.get(f"{mk}|{pk}|all_events")
            if not b:
                continue
            lo, hi = b["wilson"]
            ax.plot([lo, hi], [y, y], color=colors[mi], lw=2)
            ax.plot([b["rate"]], [y], "o", color=colors[mi], ms=6, label=mname if pi == 0 else None)
            ax.text(min(hi + 0.02, 0.98), y - 0.28, f"{b['hits']}/{b['n']}", va="center", fontsize=8)
            yt.append(y)
            yl.append(pname)
            y += 1
        y += 0.6
    chance = met["Qwen|s_neutral|all_events"]["chance_rate"]
    ax.axvline(chance, color="grey", ls="--", lw=1)
    ax.text(chance + 0.01, 1.8, f"chance {chance:.2f}", color="grey", fontsize=8, va="center")
    ax.set_yticks(yt)
    ax.set_yticklabels(yl)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Hit rate on the realised landing (Wilson 95%)")
    ax.set_title("Does the likelihood argmax point where the model writes?")
    ax.invert_yaxis()
    if HOUSE:
        place_legend(ax, loc="center right")
        fit_legends(fig)
        clear_legends_of_data(fig)
        fit_tick_labels(fig)
        fit_titles(fig)
        clear_legends_of_data(fig)
        assert_text_is_legible(fig)
    else:
        ax.legend(loc="center right")
    for ext in ("pdf", "png"):
        fig.savefig(WS / "figures" / f"argmax_vs_landing.{ext}", dpi=200)
    print("wrote figures/argmax_vs_landing.{pdf,png}")


if __name__ == "__main__":
    main()
