#!/usr/bin/env python3
"""Figures 1-6 (PNG + PDF) from results/analysis.json and the saved states."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import FIGURES, MODES, STATES  # noqa: E402

plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
COL = {"topk10": "#1f77b4", "topp095": "#d62728", "pure": "#444444"}
TEMPS = [0.3, 0.7, 1.0, 1.3]


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", dpi=180)
    fig.savefig(FIGURES / f"{name}.pdf")
    plt.close(fig)


def fig1_shares(A):
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharey=True)
    for i, task in enumerate(("T1", "T2")):
        for j, think in enumerate((False, True)):
            ax = axes[i, j]
            for sampler in ("topk10", "topp095"):
                rows = sorted([r for r in A["bfs_dijkstra_table"] if r["task"] == task and r["thinking"] == think
                               and r["sampler"] == sampler], key=lambda r: r["T"])
                if not rows:
                    continue
                x = [r["T"] for r in rows]
                y = [r["share_classified"]["share"] for r in rows]
                lo = [r["share_classified"]["share"] - r["share_classified"]["cluster_boot95"][0] for r in rows]
                hi = [r["share_classified"]["cluster_boot95"][1] - r["share_classified"]["share"] for r in rows]
                ax.errorbar(x, y, yerr=[lo, hi], marker="o", capsize=3, color=COL[sampler],
                            label="top-k=10" if sampler == "topk10" else "top-p=0.95")
            a0 = [r for r in A["bfs_dijkstra_table"] if r["task"] == task and r["arm"] == "A0"]
            if a0 and not think:
                ax.plot([1.0], [a0[0]["share_classified"]["share"]], "k*", ms=10, label="A0 (pure, T=1.0)")
            ax.set_ylim(0, 1.05)
            ax.set_xticks(TEMPS)
            mode = "BFS" if task == "T1" else "Dijkstra"
            ax.set_title(f"{task}: {mode} share, thinking {'on' if think else 'off'}")
            ax.set_xlabel("temperature T")
            if j == 0:
                ax.set_ylabel(f"{mode} share (classified)")
            ax.legend(loc="lower left", fontsize=7)
    _save(fig, "fig1_bfs_dijkstra_share")


def fig2_phrasing(A):
    sl = A["ideas_by_phrasings"]["table"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, task in zip(axes, ("T1", "T2")):
        for sampler in ("topk10", "topp095"):
            for think, ls in ((False, "-"), (True, "--")):
                rows = sorted([r for r in sl if r["task"] == task and r["sampler"] == sampler and
                               r["thinking"] == think and r["arm"] in ("A1", "A6a", "A6b", "A6c", "A6d")],
                              key=lambda r: r["T"])
                if not rows:
                    continue
                x = [r["T"] for r in rows]
                yp = [r["theta0.8_single"]["DA_phr_25"] or np.nan for r in rows]
                yi = [r["theta0.8_single"]["DA_idea_25"] or np.nan for r in rows]
                ax.plot(x, yp, ls, marker="o", color=COL[sampler],
                        label=f"phrasings {sampler}{' think' if think else ''}")
                ax.plot(x, yi, ls, marker="s", color=COL[sampler], alpha=0.4,
                        label=f"ideas {sampler}{' think' if think else ''}")
        ax.set_yscale("log")
        ax.set_xticks(TEMPS)
        ax.set_xlabel("temperature T")
        ax.set_ylabel("DA@25 (expected distinct in 25 draws)")
        ax.set_title(f"{task}: ideas vs phrasings (theta=0.8, single)")
        ax.legend(fontsize=6, ncol=2)
    _save(fig, "fig2_ideas_vs_phrasings")


def fig3_ratios(A):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for ax, task in zip(axes, ("T1", "T2")):
        c = A["subspace_test"][task]["l_star"]["conditions"]
        names = list(c)
        y = [c[n]["ratio"] for n in names]
        lo = [c[n]["ratio"] - c[n]["ratio_ci90"][0] for n in names]
        hi = [c[n]["ratio_ci90"][1] - c[n]["ratio"] for n in names]
        colors = ["#2ca02c" if n.startswith("seed_semantic") else "#1f77b4" if n.startswith("seed") else
                  "#7f7f7f" if n == "neutral_insert" else "#ff7f0e" for n in names]
        ax.barh(range(len(names)), y, xerr=[lo, hi], color=colors, capsize=3)
        ax.axvline(1.0, color="k", lw=0.8)
        ax.axvline(1.5, color="r", lw=0.8, ls="--", label="1.5x equivalence bound")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.set_xlabel("median displacement / baseline-pair null")
        ax.set_title(f"{task}, layer l*={A['subspace_test'][task]['l_star']['layer']}")
        ax.legend(fontsize=7)
    _save(fig, "fig3_displacement_ratios")


def fig4_variance(A):
    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    for i, task in enumerate(("T1", "T2")):
        vs = A["variance_split"][task]
        for name, col in (("S_gen", "#9467bd"), ("S_R", "#8c564b"), ("S_nat", "#17becf")):
            if name not in vs["per_T"]:
                continue
            per = vs["per_T"][name]
            x = [float(t) for t in per]
            axes[i, 0].plot(x, [per[t]["excess_share_dm"] for t in per], marker="o", color=col,
                            label=f"{name} excess share (data-matched null)")
            axes[i, 0].plot(x, [per[t]["share"] for t in per], marker=".", ls=":", color=col, label=f"{name} raw share")
            axes[i, 1].plot(x, [per[t]["mode_var"] for t in per], marker="o", color=col, label=f"{name} mode var")
            if name == "S_gen" or (name == "S_R" and "S_gen" not in vs["per_T"]):
                axes[i, 1].plot(x, [per[t]["comp_var"] for t in per], marker="s", color="k", label="complement var")
        axes[i, 0].axhline(0, color="k", lw=0.6)
        axes[i, 0].set_title(f"{task}: mode-subspace share of trajectory variance (layer {vs['layer']})")
        axes[i, 1].set_yscale("log")
        axes[i, 1].set_title(f"{task}: variance in mode subspace vs complement")
        for ax in axes[i]:
            ax.set_xlabel("temperature T")
            ax.set_xticks(TEMPS)
            ax.legend(fontsize=6)
    _save(fig, "fig4_variance_split")


def fig5_mds(A, samples):
    from sklearn.manifold import MDS
    meta = json.loads((STATES / "meta.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    stress = {}
    for ax, task in zip(axes, ("T1", "T2")):
        l = meta["l_star"][task]
        Hn = np.load(STATES / f"R_named_{task}.npy", mmap_mode="r")[:, l].astype(np.float64)
        Hc = np.load(STATES / f"R_conditions_{task}.npy", mmap_mode="r")[:, l].astype(np.float64)
        yn = np.array([r["condition"].split(":")[1] for r in meta[f"R_named_{task}"]])
        rows = meta[f"R_conditions_{task}"]
        modes = sorted(set(yn.tolist()))
        conds = sorted({r["condition"] for r in rows})
        pts = [Hn[yn == m].mean(0) for m in modes] + [Hc[[i for i, r in enumerate(rows) if r["condition"] == c]].mean(0)
                                                      for c in conds]
        P = np.array(pts)
        D = np.linalg.norm(P[:, None] - P[None], axis=2)
        mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, normalized_stress="auto")
        Y = mds.fit_transform(D)
        stress[task] = float(mds.stress_)
        nat = Counter(s["label"] for s in samples if s["task"] == task and s["arm"] in ("A0", "A1", "A2", "A3")
                      or (s["task"] == task and s["arm"].startswith("A6")))
        sizes = [30 + 3 * np.sqrt(nat.get(m, 0)) * 10 for m in modes]
        sc = ax.scatter(Y[:len(modes), 0], Y[:len(modes), 1], s=sizes, c=[np.log1p(nat.get(m, 0)) for m in modes],
                        cmap="viridis", edgecolor="k", zorder=3)
        for k, m in enumerate(modes):
            ax.annotate(f"{m} (n={nat.get(m, 0)})", Y[k], fontsize=7, xytext=(4, 4), textcoords="offset points")
        ax.scatter(Y[len(modes):, 0], Y[len(modes):, 1], marker="x", color="r", zorder=4)
        for k, c in enumerate(conds):
            ax.annotate(c, Y[len(modes) + k], fontsize=6, color="r", xytext=(3, -8), textcoords="offset points")
        ax.set_title(f"{task}: MDS of R-state centroids (layer {l}), stress={stress[task]:.3g}")
        plt.colorbar(sc, ax=ax, label="log(1+implemented count, natural arms)")
    _save(fig, "fig5_mds_centroids")
    return stress


def fig6_conditions(A):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, task in zip(axes, ("T1", "T2")):
        rows = [r for r in A["seeds_instructions"] if r["task"] == task]
        names = ["A0"] + [r["condition"] for r in rows]
        dists = [rows[0]["base_label_dist_correct"]] + [r["label_dist_correct"] for r in rows]
        modes = MODES[task] + ["other"]
        bottom = np.zeros(len(names))
        cmap = plt.get_cmap("tab10")
        for k, m in enumerate(modes):
            v = np.array([d.get(m, 0) / max(sum(d.values()), 1) for d in dists])
            ax.bar(range(len(names)), v, bottom=bottom, color=cmap(k), label=m)
            bottom += v
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("share of correct programs")
        ax.set_title(f"{task}: algorithm mix by condition (A0 decoding)")
        ax.legend(fontsize=6, loc="lower right")
    _save(fig, "fig6_condition_label_mix")


def make_all(A: dict, samples: list[dict]) -> dict:
    fig1_shares(A)
    fig2_phrasing(A)
    fig3_ratios(A)
    fig4_variance(A)
    stress = fig5_mds(A, samples)
    fig6_conditions(A)
    return dict(mds_stress=stress, files=sorted(p.name for p in FIGURES.glob("*.png")))
