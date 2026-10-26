#!/usr/bin/env python3
"""Optional data figure: the eight frozen rivals against the pooled escape fraction E_pool (15 Qwen3-8B tasks).

Builds a JSON spec from rivals.json + results/rival_scores.json (figures/fig_rivals_spec.json; the plotted points are
exactly the stored values).  The published figure was rendered with the aii-data-fig-gen skill's chart_gen.py; set
AII_CHART_GEN to that script's path to use it.  Without it, the same spec is drawn with plain matplotlib.
Output: figures/fig_rivals.{pdf,png}.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
SHORT = {"R1": "opening margin", "R2": "forced can rate", "R3": "assoc. clarity", "R4": "novelty excess",
         "R5": "human Hill-1", "R6": "runtime ratio", "R7": "twin modal share", "R8": "ban-free/ban unit"}


def build_spec() -> dict:
    riv = json.loads((WS / "rivals.json").read_text())
    sc = json.loads((WS / "results" / "rival_scores.json").read_text())
    E = sc["targets"]["E_pool"]
    mv = sc["movable_E_pool_gt_0"]
    panels = []
    for rv in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"):
        vals = riv["values"][rv]
        s = sc["scores"][rv]["E_pool"]
        series = []
        for lab, flag in (("movable (E_pool > 0)", 1), ("immovable", 0)):
            tk = [t for t in riv["tasks"] if vals.get(t) is not None and mv[t] == flag]
            if tk:
                series.append({"label": lab, "x": [vals[t] for t in tk], "values": [E[t] for t in tk]})
        panels.append({"type": "scatter", "title": f"{rv} rho {s['rho']:+.2f} (n {s['n']})",
                       "xlabel": SHORT[rv], "ylabel": "E_pool", "series": series})
    return {"type": "panel", "panel_labels": True, "ncols": 2, "aspect": "3:4", "width_in": 7.0,
            "title": "Frozen rivals vs pooled escape fraction (screen, descriptive)", "panels": panels}


def draw_matplotlib(spec: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, 2, figsize=(7.0, 9.3), constrained_layout=True)
    colors = {"movable (E_pool > 0)": "#3b8bc2", "immovable": "#e0a33a"}
    for i, (ax, pn) in enumerate(zip(axes.ravel(), spec["panels"])):
        for se in pn["series"]:
            ax.scatter(se["x"], se["values"], s=22, color=colors.get(se["label"]), label=se["label"])
        ax.set_title(f"({'abcdefgh'[i]}) {pn['title']}", fontsize=9)
        ax.set_xlabel(pn["xlabel"], fontsize=8)
        ax.set_ylabel(pn["ylabel"], fontsize=8)
        ax.tick_params(labelsize=7)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(spec["title"], fontsize=10)
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=200, bbox_inches="tight")


def main() -> None:
    spec = build_spec()
    spec_path = WS / "figures" / "fig_rivals_spec.json"
    spec_path.write_text(json.dumps(spec, indent=1))
    out = WS / "figures" / "fig_rivals"
    chart = os.environ.get("AII_CHART_GEN")
    if chart and Path(chart).exists():
        p = subprocess.run([sys.executable, chart, "--spec", str(spec_path), "--out", str(out)], capture_output=True,
                           text=True, timeout=300)
        if p.returncode != 0:
            raise SystemExit(f"chart_gen failed: {p.stderr[-1500:]}")
        print("rendered figures/fig_rivals.{pdf,png} with aii-data-fig-gen")
    else:
        draw_matplotlib(spec, out)
        print("rendered figures/fig_rivals.{pdf,png} with plain matplotlib (AII_CHART_GEN not set)")


if __name__ == "__main__":
    main()
