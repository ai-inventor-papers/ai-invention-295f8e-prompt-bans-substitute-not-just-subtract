#!/usr/bin/env python3
"""Stage 6 figures in ACTUAL activation coordinates (R1 at the frozen block; projection, block, readout and N in every
caption/title). Usage: python src/figures.py <8b|32b|both>"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.manifold import Isomap  # noqa: E402

import geometry  # noqa: E402
import run_analysis as RA  # noqa: E402
from common import read_json, read_jsonl  # noqa: E402
from tpg2 import DATA, FIGS, IN44, K_PRIMARY, K_SECOND, RESULTS, ROOT, cell_dc  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
DCOL = {"LEV": "#1f77b4", "DFS": "#d62728", "HEU": "#2ca02c", "RLX": "#9467bd", "RND": "#ff7f0e", "CRD": "#8c564b",
        "OTHER": "#7f7f7f", "NONE": "#7f7f7f"}
CMARK = {"DEQ": "o", "STK": "s", "HEAP": "^", "ARR": "D", "SET": "P", "SLIST": "X", "LIST": "v", "DICT": "<",
         "CALL": "*", "NONE": ".", "OTHER": "."}
FAMCOL = {"UD-LEV": "#00bcd4", "BF-RLX": "#e91e63", "CK-CRD": "#795548", "RP-RND": "#ffc107", "FL-RLX": "#9c27b0",
          "RC-RND": "#ff5722", "SP-OTHER": "#607d8b", "MX-OTHER": "#3f51b5", "MX-DFS": "#3f51b5"}


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def scatter_frame(ax: plt.Axes, Y: np.ndarray, F: dict, title: str, cent: bool = True) -> None:
    f0 = F["cell"] == "__f0__"
    ax.scatter(Y[f0, 0], Y[f0, 1], s=8, c="#bbbbbb", marker=".", label="F0 catalogue programs", zorder=1)
    for a in sorted(set(F["alg"][f0].tolist())):
        m = f0 & (F["alg"] == a)
        c = Y[m].mean(0)
        ax.annotate(a, c, fontsize=7, color="#444444", ha="center", zorder=5)
    for c in sorted(set(F["cell"].tolist()) - {"__f0__"}):
        m = F["cell"] == c
        d, k = cell_dc(c)
        ax.scatter(Y[m, 0], Y[m, 1], s=14, c=DCOL[d], marker=CMARK[k], alpha=0.55, zorder=2, linewidths=0)
        if cent:
            ax.scatter(*Y[m].mean(0), s=140, c=DCOL[d], marker=CMARK[k], edgecolors="k", linewidths=0.8, zorder=4)
    ax.set_title(title, fontsize=9)


def legend_disc_cont(ax: plt.Axes) -> None:
    from matplotlib.lines import Line2D

    h = [Line2D([], [], color=DCOL[d], marker="o", ls="", label=d) for d in ("LEV", "DFS", "HEU", "RLX", "RND", "CRD")]
    h += [Line2D([], [], color="k", marker=CMARK[c], ls="", label=c, markerfacecolor="none") for c in
          ("DEQ", "STK", "HEAP", "ARR", "SET", "SLIST")]
    h += [Line2D([], [], color="#bbbbbb", marker=".", ls="", label="F0 catalogue")]
    ax.legend(handles=h, fontsize=6, ncol=2, loc="best", framealpha=0.7)


def per_model(tag: str) -> None:
    D = RA.load_all(tag)
    Fs = RA.build_frames(D)
    F0, F1 = Fs["F0"], Fs["F1"]
    L = D["L"]
    n1 = len(F1["X"])
    # (a) PCA of F1
    pca = PCA(n_components=2, random_state=0).fit(F1["X"])
    Y = pca.transform(F1["X"])
    fig, ax = plt.subplots(figsize=(7.2, 6))
    ev = pca.explained_variance_ratio_
    scatter_frame(ax, Y, F1, f"Qwen3-{tag.upper()} block {L}, readout R1: PCA of frame F1 (N={n1}; factorial cells "
                             f"coloured by measured discipline, marker = container; large = cell centroid)")
    ax.set_xlabel(f"PC1 ({ev[0]:.1%} var)")
    ax.set_ylabel(f"PC2 ({ev[1]:.1%} var)")
    legend_disc_cont(ax)
    save(fig, f"pca_F1_{tag}")
    # (b) Isomap k15 / k10
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.4))
    for ax, k in zip(axs, (K_PRIMARY, K_SECOND)):
        Yi = Isomap(n_neighbors=k, n_components=2).fit_transform(F1["X"])
        scatter_frame(ax, Yi, F1, f"Isomap k={k} of F1 (Qwen3-{tag.upper()}, block {L}, R1, N={n1})")
        ax.set_xlabel("Isomap 1")
        ax.set_ylabel("Isomap 2")
    legend_disc_cont(axs[0])
    save(fig, f"isomap_F1_{tag}")
    # (c) classical MDS of the geodesic matrix
    geo, _ = geometry.geodesics(F1["X"], K_PRIMARY)
    Ym = geometry.classical_mds(geo)
    s1 = geometry.stress1(geo, Ym)
    fig, ax = plt.subplots(figsize=(7.2, 6))
    scatter_frame(ax, Ym, F1, f"Classical MDS of kNN-geodesic distances (k={K_PRIMARY}), F1, Qwen3-{tag.upper()} "
                              f"block {L}, R1, N={n1}; Kruskal stress-1 = {s1:.3f}")
    ax.set_xlabel("MDS 1")
    ax.set_ylabel("MDS 2")
    legend_disc_cont(ax)
    save(fig, f"mds_F1_{tag}")
    # (d) F0 with catalogue centroids sized by implemented count (baseline vs ban), survivors / covert overlaid
    if tag == "32b":
        base = Counter(r["adj_label"] for r in read_jsonl(IN44 / "data" / "labelled_C6_baseline.jsonl"))
        ban = Counter(r["adj_label"] for r in read_jsonl(IN44 / "data" / "labelled_C6_ban.jsonl"))
        cond = ("iteration-8 C6 baseline (Qwen3-32B, 100 samples)", "iteration-8 C6 top-5 ban (50 samples)")
    else:
        base = None
        ban = Counter(r["label"] for r in read_jsonl(ROOT / "inputs" / "exp9" / "data" / "top5_labelled_rows.jsonl"))
        cond = ("baseline counts not available for Qwen3-8B", "iteration-2 TOP5 ban (Qwen3-8B, 100 samples)")
    pca0 = PCA(n_components=2, random_state=0).fit(F0["X"])
    Y0 = pca0.transform(F0["X"])
    surv = D["fr"]["survivors"]
    Xs = RA.X_new(D, [s["id"] for s in surv])
    Ys = pca0.transform(Xs)
    cov = D["fr"]["covert"]
    Yc = pca0.transform(RA.X_new(D, [c["id"] for c in cov])) if cov else np.zeros((0, 2))
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, cnt, ttl in zip(axs, (base, ban), cond):
        ax.scatter(Y0[:, 0], Y0[:, 1], s=6, c="#cccccc", zorder=1)
        algs = sorted(set(F0["alg"].tolist()))
        for a in algs:
            c = Y0[F0["alg"] == a].mean(0)
            n = (cnt or {}).get(a, 0)
            ax.scatter(*c, s=60 + 25 * n, c=[[0.1, 0.3, 0.8, min(1.0, 0.25 + n / 60)]], edgecolors="k", zorder=3)
            ax.annotate(f"{a} ({n})", c, fontsize=7, xytext=(4, 4), textcoords="offset points", zorder=6)
        for fam in sorted(set(s["family_split"] for s in surv)):
            m = np.array([s["family_split"] == fam for s in surv])
            ax.scatter(Ys[m, 0], Ys[m, 1], s=16, c=FAMCOL.get(fam, "k"), marker="x", label=f"survivor {fam} ({m.sum()})", zorder=4)
        if len(Yc):
            ax.scatter(Yc[:, 0], Yc[:, 1], s=14, facecolors="none", edgecolors="k", marker="o",
                       label=f"covert BFS/DFS ({len(Yc)})", zorder=4)
        ax.set_title(f"F0 (Qwen3-{tag.upper()}, block {L}, R1, PCA fit on F0, N={len(F0['X'])})\ncentroid size = "
                     f"implemented count:\n{ttl}", fontsize=8)
        ax.set_xlabel(f"PC1 ({pca0.explained_variance_ratio_[0]:.1%})")
        ax.set_ylabel(f"PC2 ({pca0.explained_variance_ratio_[1]:.1%})")
    axs[1].legend(fontsize=6, loc="best")
    save(fig, f"F0_counts_placed_{tag}")
    # (e) S_disc and S_cont panels for UD and BF
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    for row, fam in enumerate(("UD-LEV", "BF-RLX")):
        m = np.array([s["family_split"] == fam for s in surv])
        if not m.any():
            continue
        c_f = surv[int(np.where(m)[0][0])]["cont"]
        for col, kind in enumerate(("S_disc", "S_cont")):
            mask = (F1["cont"] != c_f) if kind == "S_disc" else (F1["cont"] == c_f)
            F = RA.subframe(F1, mask)
            p = PCA(n_components=2, random_state=0).fit(F["X"])
            Yf = p.transform(F["X"])
            scatter_frame(axs[row, col], Yf, F, f"{kind}({fam}): F1 {'without' if kind == 'S_disc' else 'only'} "
                                                 f"container {c_f} (N={len(F['X'])}); Qwen3-{tag.upper()} block {L}, R1",
                          cent=True)
            Yp = p.transform(Xs[m])
            axs[row, col].scatter(Yp[:, 0], Yp[:, 1], s=30, c=FAMCOL.get(fam, "k"), marker="x", zorder=6,
                                  label=f"{fam} survivors (projected)")
            axs[row, col].legend(fontsize=6)
            axs[row, col].set_xlabel(f"PC1 ({p.explained_variance_ratio_[0]:.1%})")
            axs[row, col].set_ylabel(f"PC2 ({p.explained_variance_ratio_[1]:.1%})")
    save(fig, f"subframes_UD_BF_{tag}")
    # (g) RDM heatmaps
    g1 = read_json(RESULTS / f"g1_{tag}.json")
    cells = g1["cells"]
    mats = [("cell RDM (mean geodesic)", np.array(g1["cell_rdm"])), ("D_disc", np.array(g1["model_rdms"]["D_disc"])),
            ("D_cont", np.array(g1["model_rdms"]["D_cont"])), ("D_surf (AST 4-gram)", np.array(g1["model_rdms"]["D_surf"]))]
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.2))
    for ax, (nm, M) in zip(axs, mats):
        im = ax.imshow(M, cmap="viridis")
        ax.set_xticks(range(len(cells)), cells, rotation=90, fontsize=6)
        ax.set_yticks(range(len(cells)), cells, fontsize=6)
        ax.set_title(f"{nm}" + (f"\nQwen3-{tag.upper()} block {L}, R1, k={K_PRIMARY}" if nm.startswith("cell") else ""),
                     fontsize=8)
        plt.colorbar(im, ax=ax, fraction=0.046)
    save(fig, f"rdm_heatmaps_{tag}")


def forest() -> None:
    rows = []
    for tag in ("8b", "32b"):
        p = RESULTS / f"g1_{tag}.json"
        if p.exists():
            rows.append((tag, read_json(p)))
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(8, 1.2 + 1.3 * len(rows) * 2))
    y = 0
    yt, yl = [], []
    for tag, g in rows:
        nc = g["noise_ceiling"]
        for stat in ("rho_d", "rho_c"):
            pt = g["point_model"][stat]
            ci = g["bootstrap"]["model"][stat]["ci95"]
            nq = g["perm"]["model"][stat]["null_q"]
            ax.plot([nq[0], nq[3]], [y, y], color="#dddddd", lw=8, solid_capstyle="butt", zorder=1)
            ax.errorbar(pt, y, xerr=[[pt - ci[0]], [ci[1] - pt]], fmt="o", color="k" if stat == "rho_d" else "#d62728",
                        capsize=3, zorder=3)
            yt.append(y)
            yl.append(f"{tag} {stat} (model, block {g['block']})")
            y += 1
        for b, colr in (("block0", "#1f77b4"), ("tfidf", "#2ca02c"), ("astngram", "#9467bd")):
            pt = g["point_" + b]["rho_d"]
            ci = g["bootstrap"][b]["rho_d"]["ci95"]
            ax.errorbar(pt, y, xerr=[[pt - ci[0]], [ci[1] - pt]], fmt="s", color=colr, capsize=3, zorder=3)
            yt.append(y)
            yl.append(f"{tag} rho_d baseline: {b}")
            y += 1
        ax.axvline(nc["ceiling_sqrt"], color="#ff7f0e", ls=":", lw=1)
        ax.text(nc["ceiling_sqrt"], y - 0.5, f"{tag} noise ceiling sqrt(r_SB)={nc['ceiling_sqrt']:.2f}", fontsize=6,
                color="#ff7f0e")
        y += 0.6
    ax.axvline(0.3, color="k", ls="--", lw=0.8)
    ax.axvline(0.1, color="k", ls=":", lw=0.8)
    ax.set_yticks(yt, yl, fontsize=7)
    ax.set_xlabel("partial Spearman (95% bootstrap CI; grey band = 2.5-97.5% of the restricted permutation null)")
    ax.set_title("G1: discipline (rho_d | container) vs container (rho_c | discipline) on the factorial cell RDM", fontsize=9)
    save(fig, "g1_forest")


if __name__ == "__main__":
    which = sys.argv[1]
    for t in (("8b", "32b") if which == "both" else (which,)):
        if (RESULTS / f"g1_{t}.json").exists():
            per_model(t)
    forest()
    print(json.dumps(sorted(p.name for p in FIGS.glob("*.png"))))
