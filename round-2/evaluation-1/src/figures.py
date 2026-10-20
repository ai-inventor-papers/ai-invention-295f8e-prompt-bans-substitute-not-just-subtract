#!/usr/bin/env python3
"""Figures (PDF + PNG) from results/*.json via the aii-data-fig-gen chart generator; the geometry heatmap with
per-cell rank annotations is hand-written with the same house style."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from common import FIG, RES, TAB, setup_logging

# chart generator of the aii-data-fig-gen skill: CHART_GEN env var, else the skills tree above the runs volume
G = Path(os.environ.get("CHART_GEN", Path(__file__).resolve().parents[7] / ".claude" / "skills" / "aii-data-fig-gen"
                        / "scripts" / "chart_gen.py"))
POS_ORDER = ["R", "k_pre", "k_post", "k_fork", "k8", "k16", "k32", "k64"]


def render(spec: dict, name: str) -> str:
    sp = FIG / f"{name}.json"
    sp.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([sys.executable, str(G), "--spec", str(sp), "--out", str(FIG / name)], capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f"{name}: {r.stderr[-800:]}")
        return f"FAILED: {r.stderr[-300:]}"
    logger.info(f"rendered figures/{name}.pdf/.png")
    return f"figures/{name}.pdf"


def main() -> None:
    setup_logging("figures")
    out = {}
    loc = json.loads((RES / "locus.json").read_text())
    # 1. locus curves: BA by layer per position (contrast W), one panel per task
    panels = []
    for t in ("T1", "T2"):
        W = loc["tasks"][t]["contrasts"]["W"]["positions"]
        series = []
        for p in POS_ORDER:
            if p in W:
                series.append({"label": p, "x": W[p]["layers"], "values": [round(v, 4) for v in W[p]["BA"]]})
        out[f"locus_curves_{t}"] = render({"type": "line", "title": f"{t}: within-ban probe (W), balanced accuracy by layer",
                                           "xlabel": "Layer", "ylabel": "Balanced accuracy (LOPO)", "aspect": "16:9",
                                           "series": series}, f"fig_locus_curves_{t}")
    # 1b. null bands: observed layer-max vs layer-max null 95th percentiles per position
    panels = []
    for t in ("T1", "T2"):
        W = loc["tasks"][t]["contrasts"]["W"]["positions"]
        ps = [p for p in POS_ORDER if p in W and p != "R"]
        panels.append({"type": "bar", "title": f"{t}: layer-max BA vs nulls", "xlabel": "Position", "ylabel": "Balanced accuracy",
                       "categories": ps,
                       "series": [{"label": "observed layer-max", "values": [round(W[p]["layer_max_BA"], 4) for p in ps]},
                                  {"label": "global null p95", "values": [round(W[p]["layer_max_null_global_p95"], 4) for p in ps]},
                                  {"label": "within-paraphrase null p95", "values": [round(W[p]["layer_max_null_within_p95"], 4) for p in ps]}]})
    out["locus_nulls"] = render({"type": "panel", "ncols": 2, "aspect": "2:1", "panels": panels}, "fig_locus_nulls")
    # 2. text-locus curve
    series = []
    for t in ("T1", "T2"):
        cv = loc["tasks"][t]["text"]["curve"]
        ks = sorted(int(k) for k in cv)
        series.append({"label": t, "x": ks, "values": [round(cv[str(k)]["BA_text"], 4) for k in ks]})
    out["text_locus"] = render({"type": "line", "title": "Written-prefix classifier: where the text reveals the algorithm",
                                "xlabel": "Prefix length k (generated tokens)", "ylabel": "BA of text-only probe",
                                "aspect": "16:9", "series": series}, "fig_text_locus")
    # 3. commit-aligned curve
    panels = []
    for t in ("T1", "T2"):
        cv = [c for c in loc["tasks"][t]["commit_aligned_curve"] if c["n"] > 0]
        panels.append({"type": "bar", "title": f"{t}", "xlabel": "Offset from commit index (bins)",
                       "ylabel": "OOF accuracy at L*", "categories": [c["bin"] for c in cv],
                       "series": [{"values": [round(c["acc"], 4) for c in cv],
                                   "errors": [round((c["ci"][1] - c["ci"][0]) / 2, 4) for c in cv]}]})
    out["commit_curve"] = render({"type": "panel", "ncols": 2, "aspect": "2:1", "panels": panels}, "fig_commit_curve")
    # 4. PCA views at k_pre (L*) per task
    panels = []
    for t in ("T1", "T2"):
        V = loc["tasks"][t]["pca_views"]
        key = next(k for k in V if k.startswith("k_pre|"))
        v = V[key]
        tags = sorted(set(v["tag"]))
        series = []
        for tg in tags:
            ii = [i for i, x in enumerate(v["tag"]) if x == tg]
            series.append({"label": tg, "x": [v["x"][i] for i in ii], "values": [v["y"][i] for i in ii]})
        out[f"pca_views_{t}"] = render({"type": "scatter", "title": f"{t} k_pre {key.split('|')[1]}: PCA of 300 states (PC1 {v['explained'][0]:.2f})",
                                        "xlabel": "PC1", "ylabel": "PC2", "aspect": "4:3", "series": series}, f"fig_pca_kpre_{t}")
    # 5. geometry heatmap (hand-written: cell = P(realised substitute nearest), annotated with full-data rank)
    out["geometry_heatmap"] = geometry_heatmap()
    # 6. perturbation composition (selected rows)
    pt = pd.read_csv(TAB / "perturbation_table.csv")
    sel = {"T2": [("exp4", "steer:dc:c=0:L=18", "e4 c=0"), ("exp4", "steer:dc:c=0.25:L=18", "e4 dc .25"),
                  ("exp4", "steer:rand1:c=0.25:L=18", "e4 rand1 .25"), ("exp4", "steer:rand2:c=0.25:L=18", "e4 rand2 .25"),
                  ("exp4", "steer:placebo:c=0.25:L=18", "e4 placebo"), ("exp5", "steer:random2", "e5 rand2 .5"),
                  ("exp5", "steer:random1", "e5 rand1 .5"), ("exp6", "A2|seed_semantic", "e6 sem seed"),
                  ("exp6", "A3|instr_fully_novel", "e6 novel"), ("exp6", "A3|instr_enumerate", "e6 enumerate"),
                  ("exp1", "ban:dijkstra", "e1 ban"), ("exp3", "G2:ban", "e3 ban")],
           "T1": [("exp4", "steer:dc:c=0:L=18", "e4 c=0"), ("exp4", "steer:dc:c=0.25:L=18", "e4 dc .25"),
                  ("exp4", "steer:rand1:c=0.1:L=18", "e4 rand1 .1"), ("exp5", "steer:random2", "e5 rand2 .5"),
                  ("exp6", "A2|seed_semantic", "e6 sem seed"), ("exp6", "A3|instr_fully_novel", "e6 novel"),
                  ("exp1", "mention:astar_gbfs", "e1 mention A*"), ("exp1", "ban:bfs", "e1 ban"),
                  ("exp3", "G2:ban", "e3 ban"), ("exp1", "succession:2", "e1 BFS+DFS ban")]}
    panels = []
    for t in ("T1", "T2"):
        rows = []
        for e, c, nm in sel[t]:
            r = pt[(pt.experiment == e) & (pt.task == t) & (pt.condition == c)]
            if len(r) and sum(json.loads(r.composition_correct.iloc[0]).values()) > 0:
                rows.append((nm, json.loads(r.composition_correct.iloc[0])))
        labs = sorted({k for _, d in rows for k in d}, key=lambda k: (k != ("BFS" if t == "T1" else "DIJKSTRA"), k))
        out[f"perturbation_composition_{t}"] = render(
            {"type": "stacked_pct", "title": f"{t}: label composition of correct programs", "xlabel": "Condition",
             "aspect": "21:9", "categories": [nm for nm, _ in rows],
             "series": [{"label": l, "values": [d.get(l, 0) for _, d in rows]} for l in labs]},
            f"fig_perturbation_composition_{t}")
    # 7. knob table: Hill vs pass points
    kt = pd.read_csv(TAB / "knob_table.csv")
    kt = kt[kt.hill1_rarefied.notna() & kt.pass_points.notna()]
    series = []
    for t in ("T1", "T2"):
        k = kt[kt.task == t]
        series.append({"label": t, "x": [round(v, 3) for v in k.pass_points], "values": [round(v, 4) for v in k.hill1_rarefied]})
    out["knob_table"] = render({"type": "scatter", "title": "Knobs: compliant-only rarefied Hill-1 (depth 25) vs pass cost",
                                "xlabel": "Pass points lost vs own reference", "ylabel": "Rarefied Hill-1",
                                "aspect": "16:9", "series": series}, "fig_knob_table")
    (RES / "figures.json").write_text(json.dumps(out, indent=1))


def geometry_heatmap() -> str:
    sys.path.insert(0, str(G.parent))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    try:
        from chart_style import apply_house_style
        apply_house_style()
    except ImportError:
        pass
    g = json.loads((RES / "geometry.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4), layout="constrained")
    for ax, t, key, lab in ((axes[0], "t1", "P_DFS_nearest", "DFS"), (axes[1], "t2", "P_BF_SPFA_nearest", "BF_SPFA")):
        cells = [c for c in g["grid"] if c["task"] == t and c["kind"] == "forced"]
        Ls = sorted({c["layer"] for c in cells})
        Ks = sorted({c["k"] for c in cells})
        M = np.zeros((len(Ls), len(Ks)))
        R = np.zeros((len(Ls), len(Ks)), dtype=int)
        for c in cells:
            M[Ls.index(c["layer"]), Ks.index(c["k"])] = c[key]
            R[Ls.index(c["layer"]), Ks.index(c["k"])] = c["realised_substitute_rank_full"]
        im = ax.imshow(M, vmin=0, vmax=1, cmap="cividis", aspect="auto")
        for i in range(len(Ls)):
            for j in range(len(Ks)):
                ax.text(j, i, f"{M[i, j]:.2f}\nrank {R[i, j]}", ha="center", va="center", fontsize=7,
                        color="black" if M[i, j] > 0.5 else "white")
        ax.set_xticks(range(len(Ks)), [str(k) for k in Ks])
        ax.set_yticks(range(len(Ls)), [str(l) for l in Ls])
        ax.set_xlabel("k (kNN graph)")
        ax.set_ylabel("Layer")
        ax.set_title(f"{t.upper()}: P({lab} nearest)", fontsize=10)
    fig.colorbar(im, ax=axes, shrink=0.8, label="share of 1000 draws")
    fig.savefig(FIG / "fig_geometry_heatmap.pdf")
    fig.savefig(FIG / "fig_geometry_heatmap.png", dpi=200)
    plt.close(fig)
    return "figures/fig_geometry_heatmap.pdf"


if __name__ == "__main__":
    main()
