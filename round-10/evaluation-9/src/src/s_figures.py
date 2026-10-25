#!/usr/bin/env python3
"""S-10 figures (hand-written matplotlib in the aii-data-fig-gen house style; every number read from results/).

fig_s0_kcurves   k = 1..5 per model: lexical, runtime coarse, runtime fine, tracer coarse and tracer fine compliance
                 with Wilson 95% bands; hand reads as k = 5 points (committed and held-out templates).
fig_s0_placement every survivor's geodesic distance g by family and frame, with the two reference values
                 (unit-weight Dijkstra, IDA*) and the frame median that defines edge / opposite.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from io_util import A_GEO, A_REN, FIGURES, ROOT, load_stage, ref, save_stage, sha256_file, write_json

from io_util import env_value  # noqa: E402

SKILL = env_value("FIG_SKILL")          # aii-data-fig-gen scripts (house style); optional
if SKILL and SKILL not in sys.path:
    sys.path.insert(0, SKILL)


def _style() -> Any:
    import matplotlib
    matplotlib.use("Agg")
    try:
        import chart_style as CS
        CS.apply_house_style()
        return CS
    except Exception as e:  # the house style is optional; fall back to plain matplotlib
        logger.warning(f"house style unavailable ({e!r}); plain matplotlib")
        return None


def _finish(fig: Any, CS: Any) -> None:
    if CS is None:
        return
    try:
        from chart_geometry import assert_text_is_legible
        CS.fit_legends(fig)
        CS.clear_legends_of_data(fig)
        CS.fit_tick_labels(fig)
        CS.fit_titles(fig)
        CS.clear_legends_of_data(fig)
        assert_text_is_legible(fig)
    except Exception as e:
        logger.warning(f"layout pass: {e!r}")


def wilson(k: int, n: int) -> tuple[float, float]:
    from vend import S
    return S.wilson_ci(k, n)


def fig_kcurves(CS: Any) -> dict[str, Any]:
    import matplotlib.pyplot as plt
    a = load_stage("s0a")
    C = a["cells"]
    readings = [("runtime_coarse", "runtime label, coarse (primary)", "-"), ("runtime_fine", "runtime label, fine", "--"),
                ("tracer_coarse", "tracer, coarse", "-."), ("tracer_fine", "tracer, fine", ":")]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4), sharey=True, layout="constrained")
    ks = np.arange(1, 6)
    pal = (CS.PALETTE if CS is not None else plt.rcParams["axes.prop_cycle"].by_key()["color"])
    for ax, (mk, title) in zip(axes, (("q32", "Qwen3-32B, thinking on"), ("q14", "Qwen3-14B, thinking on"))):
        lex = [C[mk][str(k)]["runtime_coarse"]["lex"] for k in ks]
        lexk = [C[mk][str(k)]["runtime_coarse"]["lex_k"] for k in ks]
        lexn = [C[mk][str(k)]["runtime_coarse"]["n"] for k in ks]
        lo, hi = zip(*[wilson(k_, n_) for k_, n_ in zip(lexk, lexn)])
        ax.plot(ks, lex, color="black", lw=1.6, marker="o", ms=3.5, label="lexical (L1)")
        ax.fill_between(ks, lo, hi, color="black", alpha=0.08, lw=0)
        for i, (rd, lab, ls) in enumerate(readings):
            y = [C[mk][str(k)][rd]["mech"] for k in ks]
            kk = [C[mk][str(k)][rd]["mech_k"] for k in ks]
            nn = [C[mk][str(k)][rd]["n"] for k in ks]
            lo, hi = zip(*[wilson(k_, n_) for k_, n_ in zip(kk, nn)])
            ax.plot(ks + (i - 1.5) * 0.04, y, color=pal[i % len(pal)], ls=ls, lw=1.4, marker="o", ms=3, label=lab)
            ax.fill_between(ks + (i - 1.5) * 0.04, lo, hi, color=pal[i % len(pal)], alpha=0.10, lw=0)
        h5 = C[mk]["5"]["hand_reads"]
        hh = C[mk]["ho"]["hand_reads"]
        ax.errorbar([5.12], [h5["mech"]], yerr=[[h5["mech"] - h5["mech_wilson"][0]], [h5["mech_wilson"][1] - h5["mech"]]],
                    fmt="D", color=pal[4 % len(pal)], ms=5, capsize=2, label="hand reads, k = 5")
        ax.errorbar([5.28], [hh["mech"]], yerr=[[hh["mech"] - hh["mech_wilson"][0]], [hh["mech_wilson"][1] - hh["mech"]]],
                    fmt="s", mfc="white", color=pal[4 % len(pal)], ms=5, capsize=2, label="hand reads, k = 5 held out")
        ax.set_title(title)
        ax.set_xticks(list(ks))
        ax.set_xlim(0.8, 5.45)
        ax.set_ylim(-0.02, 1.05)
        ax.set_xlabel("k (names banned)")
    axes[0].set_ylabel("Compliance (share)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=3, fontsize=8, frameon=False)
    _finish(fig, CS)
    out = FIGURES / "fig_s0_kcurves"
    fig.savefig(str(out) + ".pdf", metadata={"CreationDate": None})  # no timestamp: byte-identical reruns
    fig.savefig(str(out) + ".png", dpi=200)
    plt.close(fig)
    return {"id": "fig_s0_kcurves", "file": "figures/fig_s0_kcurves.pdf",
            "sha256": sha256_file(str(out) + ".pdf"), "png": "figures/fig_s0_kcurves.png",
            "png_sha256": sha256_file(str(out) + ".png"),
            "what": "Compliance against the number of banned names k = 1..5 for Qwen3-32B and Qwen3-14B with thinking: "
                    "lexical (L1) compliance and mechanistic compliance under four readings (runtime label coarse and "
                    "fine, tracer coarse and fine), each with its Wilson 95% band; hand reads substituted shown as k = 5 "
                    "points with Wilson 95% intervals (diamond committed templates, open square held-out templates).",
            "data_source": [ref(A_REN, "data/labelled_v9_{A,E}_k{1..5}{,_ho}.jsonl"),
                            ref(A_REN, "data/manual_reads_v9.jsonl"), "results/s0a.json#cells"],
            "code": "src/s_figures.py#fig_kcurves", "insert_after": "Table 431b"}


def fig_placement(CS: Any) -> dict[str, Any]:
    import matplotlib.pyplot as plt
    from io_util import dep_path, read_json
    d = load_stage("s0d")
    pl = read_json(dep_path(A_GEO, "results/placement.json"))
    fmap = {}
    import csv
    with open(ROOT / "tables" / "placement_family_map.csv") as fh:
        for r in csv.DictReader(fh):
            fmap[r["uid"]] = r["family"]
    fams = ["unit-weight Dijkstra", "Bellman-Ford/SPFA", "BFS variants", "other known"]
    short = ["unit-weight\nDijkstra", "Bellman-Ford\n/SPFA", "BFS\nvariants", "other\nknown"]
    frames = [("32b|mcode_PRIMARY_R1", "Qwen3-32B primary (block 33)"), ("32b|mcode_PRIMARY_R2", "Qwen3-32B second (block 21; gate fails)"),
              ("32b|mcode_M32_R1", "Qwen3-32B programs only (block 31)"), ("8b|mcode_PRIMARY_R1", "Qwen3-8B primary (block 17)")]
    pal = (CS.PALETTE if CS is not None else plt.rcParams["axes.prop_cycle"].by_key()["color"])
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.6), layout="constrained")
    for ax, (fk, title) in zip(axes.ravel(), frames):
        fv = pl[fk]
        for j, fam in enumerate(fams):
            rs = sorted([r for r in fv["rows"] if r["set"] == "SURV" and fmap[r["uid"]] == fam], key=lambda r: r["uid"])
            n = len(rs)
            offs = (np.arange(n) - (n - 1) / 2) * (0.5 / max(n, 1))
            for r, o in zip(rs, offs):
                ax.plot(j + o, r["g_x"], marker="o" if r["class"] == "EDGE" else "^", ms=4,
                        color=pal[0] if r["class"] == "EDGE" else pal[1], alpha=0.85, ls="none")
        ax.axhline(fv["frame_median"], color="black", lw=1.0, ls="-")
        ax.axhline(fv["frame_g"]["dijkstra_unit"], color=pal[2], lw=1.0, ls="--")
        ax.axhline(fv["frame_g"]["idastar"], color=pal[3], lw=1.0, ls=":")
        ax.set_xticks(range(len(fams)))
        ax.set_xticklabels(short, fontsize=7.5)
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("g to the banned five", fontsize=8)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="none", color=pal[0], label="survivor classed edge"),
         Line2D([], [], marker="^", ls="none", color=pal[1], label="survivor classed opposite"),
         Line2D([], [], color="black", lw=1.0, label="frame median (edge/opposite cut)"),
         Line2D([], [], color=pal[2], lw=1.0, ls="--", label="unit-weight Dijkstra programs (reference)"),
         Line2D([], [], color=pal[3], lw=1.0, ls=":", label="IDA* programs (reference)")]
    fig.legend(handles=h, loc="outside lower center", ncols=2, fontsize=8, frameon=False)
    _finish(fig, CS)
    out = FIGURES / "fig_s0_placement"
    fig.savefig(str(out) + ".pdf", metadata={"CreationDate": None})  # no timestamp: byte-identical reruns
    fig.savefig(str(out) + ".png", dpi=200)
    plt.close(fig)
    return {"id": "fig_s0_placement", "file": "figures/fig_s0_placement.pdf",
            "sha256": sha256_file(str(out) + ".pdf"), "png": "figures/fig_s0_placement.png",
            "png_sha256": sha256_file(str(out) + ".png"),
            "what": "Every iteration-8 survivor's geodesic distance g to the banned five on each of the four program "
                    "frames (k 15), grouped by the frozen family map (15 unit-weight Dijkstra, 15 Bellman-Ford/SPFA, 3 "
                    "BFS variants, 5 other known); circles are classed edge and triangles opposite; the solid line is the "
                    "frame median of the two non-banned reference classes, the dashed and dotted lines are the frame g of "
                    "the unit-weight Dijkstra and IDA* programs. Not preregistered.",
            "data_source": [ref(A_GEO, "results/placement.json", "<frame>.rows (set SURV), frame_g, frame_median"),
                            "tables/placement_family_map.csv"],
            "code": "src/s_figures.py#fig_placement", "insert_after": "Table 438"}


def run() -> dict[str, Any]:
    CS = _style()
    with warnings.catch_warnings(record=True):
        f1 = fig_kcurves(CS)
        f2 = fig_placement(CS)
    write_json(ROOT / "figure_markers.json", [f1, f2])
    save_stage("s10_figures", {"status": "DONE", "figures": [f1, f2],
                               "metrics": {"n_figures": 2},
                               "examples": {"figures": [{"input": f"figure {f['id']}", "output": f["what"],
                                                         "metadata_file": f["file"], "metadata_sha256": f["sha256"],
                                                         "metadata_code": f["code"]} for f in (f1, f2)]}})
    return {"figures": [f1, f2]}
