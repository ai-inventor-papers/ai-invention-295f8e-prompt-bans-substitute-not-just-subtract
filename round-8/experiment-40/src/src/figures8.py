#!/usr/bin/env python3
"""S11 geometry + figures (actual activation coordinates; PDF + PNG in figures/).

F1 scan profile per unit: rank-1 CV recovery and full-state mean Delta by block (L* marked).
F2 held-out TF recovery by rank (seed 0) against the random-subspace median / 95th percentile (c1).
F3 decision-site geometry per unit: every prompt's coordinates in the fitted R_8 subspace at (L*, d) (centred on the
   twin mean), embedded in 2-D by metric MDS (Kruskal stress-1 printed) and Isomap (k = 8); class centroids sized by
   implemented counts (BASE + SRC generation rows); companion PCA of the raw block-L* states. Title says 'causal
   manifold' only if the site is CERTIFIED, else 'handle coordinates (not certified)'.
F4 generation: correct target programs by arm and class (Wilson 95% intervals).
F5 mediation: committed predictor pi_u against the escape share (retrospective 40 + prospective 24).

Usage: python src/figures8.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.manifold import MDS, Isomap

from cfg8 import CACHE, FIGS, MAPS, PROMPTS_DIR, RESULTS, read_json, read_jsonl, setup_logging, write_json

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
COL = {"bfs": "#1f77b4", "dfs": "#d62728", "union_find": "#2ca02c", "astar_gbfs": "#9467bd", "iddfs": "#8c564b",
       "twin": "#7f7f7f", "padtwin": "#bcbd22", "ban": "#ff7f0e", "top5": "#e377c2", "seed": "#17becf",
       "instr": "#000000", "p0": "#aaaaaa"}


def save(fig: Any, name: str) -> None:
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def group_of(r: dict[str, Any]) -> str:
    k = r["kind"]
    if k == "forced":
        return r["Y"]
    if k in ("seed_rand1", "seed_rand2"):
        return "seed"
    if k in ("instr_new", "instr_novel"):
        return "instr"
    return k


def f1_scan() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.0))
    fig.subplots_adjust(wspace=0.45)
    for ax, unit in zip(axes, ("T10", "GRID")):
        p = RESULTS / f"scan_{unit}.json"
        if not p.exists():
            ax.set_title(f"{unit}: scan not run")
            continue
        sc = {int(k): v for k, v in read_json(p).items()}
        L = sorted(sc)
        rec = [float(sc[l]["cv_median_recovery"]) if sc[l]["cv_median_recovery"] is not None else np.nan for l in L]
        full = [sc[l]["full_state_mean_delta_held96"] for l in L]
        ax.plot(L, rec, "o-", color="#d62728", label="rank-1 DAS CV recovery")
        ax.axhline(1.0, color="#d62728", lw=0.6, ls=":")
        ax.axhline(1.5, color="#d62728", lw=0.6, ls="--")
        ax.set_xlabel("block L (edit of the block output at the decision position d)")
        ax.set_ylabel("rank-1 DAS recovery (DAS / full-state)")
        ax2 = ax.twinx()
        ax2.plot(L, full, "s--", color="#555555", label="full-state mean Delta (nats)")
        ax2.set_ylabel("full-state mean Delta (nats)")
        d = RESULTS / f"dec_{unit}.json"
        if d.exists():
            Ls = read_json(d)["L_star"]
            ax.axvline(Ls, color="k", lw=0.8)
            ax.text(Ls, ax.get_ylim()[1] * 0.95, f" L*={Ls}", fontsize=8)
        ax.set_title(f"{unit} ({'Qwen3-8B' if unit == 'T10' else 'gemma-3-4b-it'}): block scan; dotted = 1, "
                     f"dashed = OFF-MANIFOLD 1.5", fontsize=9)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    save(fig, "F1_scan_profile")


def f2_rank() -> None:
    sites = [("T10", "dec", RESULTS / "dec_T10.json"), ("T10", "band", RESULTS / "band_T10.json"),
             ("GRID", "dec", RESULTS / "dec_GRID.json"), ("T10", "dec L24 (post hoc)", RESULTS / "dec_T10_L24.json")]
    sites = [s for s in sites if s[2].exists()]
    if not sites:
        return
    fig, axes = plt.subplots(1, len(sites), figsize=(3.6 * len(sites), 3.2), squeeze=False)
    for ax, (unit, site, p) in zip(axes[0], sites):
        d = read_json(p)
        ks = [1, 2, 4, 8]
        rr = [d["recovery_by_rank"][str(k)]["recovery"] for k in ks]
        lo = [d["recovery_by_rank"][str(k)]["ci95"][0] for k in ks]
        hi = [d["recovery_by_rank"][str(k)]["ci95"][1] for k in ks]
        ax.errorbar(ks, rr, yerr=[np.array(rr) - np.array(lo), np.array(hi) - np.array(rr)], fmt="o-",
                    color="#d62728", capsize=3, label="DAS (seed 0), held-out")
        med = [d["c1"][str(k)]["median"] for k in ks]
        p95 = [d["c1"][str(k)]["p95"] for k in ks]
        ax.plot(ks, med, "x--", color="#555555", label="random subspaces: median")
        ax.plot(ks, p95, "+:", color="#555555", label="random: 95th pct")
        ax.axhline(1.0, color="k", lw=0.5)
        ax.set_xscale("log", base=2)
        ax.set_xticks(ks)
        ax.set_xticklabels(ks)
        ax.set_xlabel("rank k")
        ax.set_ylabel("normalised recovery")
        ax.set_title(f"{unit} {site}: k*={d['k_star']}", fontsize=9)
        ax.legend(fontsize=6)
    save(fig, "F2_recovery_by_rank")


def implemented_counts(unit: str) -> dict[str, int]:
    labs = read_jsonl(Path(RESULTS.parent / "data" / f"labels_{unit}.jsonl"))
    cnt: dict[str, int] = {}
    for r in labs:
        if r.get("arm") in ("BASE", "SRC") and r.get("passed"):
            cnt[r["label"]] = cnt.get(r["label"], 0) + 1
    return cnt


def f3_geometry(unit: str, verdict: str | None) -> dict[str, Any] | None:
    d = RESULTS / f"dec_{unit}.json"
    st = CACHE / f"states_{unit}_dec_trained.pt"
    if not d.exists() or not st.exists():
        return None
    dd = read_json(d)
    L = dd["L_star"]
    R = torch.load(MAPS / f"{unit}_dec_L{L}_seed0.pt").float()           # [D, 8]
    H = torch.load(st)
    P = {r["key"]: r for r in read_jsonl(PROMPTS_DIR / ("t10_prompts.jsonl" if unit == "T10" else "grid_prompts.jsonl"))}
    keys = [k for k in P if k in H]
    X = torch.stack([H[k][L].float() for k in keys])                     # [n, D]
    tw = [i for i, k in enumerate(keys) if P[k]["kind"] == "twin"]
    mu = X[tw].mean(0)
    Z = ((X - mu) @ R).numpy()                                           # [n, 8] handle coordinates
    groups = [group_of(P[k]) for k in keys]
    D = np.linalg.norm(Z[:, None] - Z[None], axis=-1)
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, n_init=4, normalized_stress="auto")
    E = mds.fit_transform(D)
    dE = np.linalg.norm(E[:, None] - E[None], axis=-1)
    stress1 = float(np.sqrt(((D - dE) ** 2).sum() / (D ** 2).sum()))
    iso = Isomap(n_neighbors=8, n_components=2)
    Ei = iso.fit_transform(Z)
    geo = iso.dist_matrix_
    cnt = implemented_counts(unit)
    certified = verdict == "CERTIFIED VARIABLE"
    title = "causal manifold" if certified else "handle coordinates (not certified)"
    ug = sorted(set(groups))
    cents = {g: E[[i for i, x in enumerate(groups) if x == g]].mean(0) for g in ug}
    cls_names = [g for g in ug if g in ("bfs", "dfs", "union_find", "astar_gbfs", "iddfs")]
    gd = {}
    for a in ug:
        for b in ug:
            if a < b:
                ia = [i for i, x in enumerate(groups) if x == a]
                ib = [i for i, x in enumerate(groups) if x == b]
                gd[f"{a}|{b}"] = float(np.mean(geo[np.ix_(ia, ib)]))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, emb, name in ((axes[0], E, f"metric MDS of R_8 coordinates (stress-1 {stress1:.2f})"),
                          (axes[1], Ei, "Isomap (k = 8) of R_8 coordinates")):
        for g in ug:
            ix = [i for i, x in enumerate(groups) if x == g]
            ax.scatter(emb[ix, 0], emb[ix, 1], s=10, alpha=0.6, color=COL.get(g, "#333333"), label=f"{g} (n={len(ix)})")
        for g in cls_names:
            ix = [i for i, x in enumerate(groups) if x == g]
            c = emb[ix].mean(0)
            ax.scatter([c[0]], [c[1]], s=40 + 6 * cnt.get(g, 0), marker="*", color=COL.get(g), edgecolor="k",
                       zorder=5)
            ax.annotate(f"{g}: {cnt.get(g, 0)} impl.", c, fontsize=7)
        for g in ("ban", "top5", "seed", "instr"):
            ix = [i for i, x in enumerate(groups) if x == g]
            if ix:
                c = emb[ix].mean(0)
                ax.annotate(g, c, fontsize=7, color=COL.get(g))
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("embedding axis 1 (a.u.)")
        ax.set_ylabel("embedding axis 2 (a.u.)")
    axes[0].legend(fontsize=6, loc="best")
    pca = PCA(n_components=2).fit(X.numpy())
    Ep = pca.transform(X.numpy())
    for g in ug:
        ix = [i for i, x in enumerate(groups) if x == g]
        axes[2].scatter(Ep[ix, 0], Ep[ix, 1], s=10, alpha=0.6, color=COL.get(g, "#333333"), label=g)
    axes[2].set_title(f"PCA of raw block-{L} states at d (var {pca.explained_variance_ratio_.sum():.2f})", fontsize=9)
    axes[2].set_xlabel("PC1 of raw residual states")
    axes[2].set_ylabel("PC2 of raw residual states")
    fig.suptitle(f"{unit} decision site, block {L}: {title}. Stars = class centroids, size ~ implemented "
                 f"(passing BASE + SRC programs)", fontsize=10)
    save(fig, f"F3_geometry_{unit}")
    # handle coordinate 1 against class: a 1-D view of the actual coordinates
    fig, ax = plt.subplots(figsize=(6, 3))
    for j, g in enumerate(ug):
        ix = [i for i, x in enumerate(groups) if x == g]
        ax.scatter(Z[ix, 0], np.full(len(ix), j) + np.random.default_rng(j).uniform(-0.2, 0.2, len(ix)), s=8,
                   color=COL.get(g, "#333333"))
    ax.set_yticks(range(len(ug)))
    ax.set_yticklabels(ug, fontsize=7)
    ax.set_xlabel(f"coordinate on R_1 at block {L} (projection of h - mean(twins); activation units)")
    ax.set_title(f"{unit}: first handle coordinate per prompt group ({title})", fontsize=9)
    save(fig, f"F3b_handle_axis_{unit}")
    return {"unit": unit, "L": L, "mds_stress1": stress1, "isomap_mean_geodesic_between_groups": gd,
            "implemented_counts": cnt, "title": title, "n_prompts": len(keys),
            "group_centroids_mds": {g: cents[g].tolist() for g in ug}}


def f4_generation(an: dict[str, Any]) -> None:
    items = [(k, v) for k, v in an.items() if k.startswith("gen_")]
    if not items:
        return
    fig, axes = plt.subplots(1, len(items), figsize=(5 * len(items), 3.6), squeeze=False)
    for ax, (k, g) in zip(axes[0], items):
        arms = ["BASE", "FULL", "DAS", "RAND", "PERM"]
        x = np.arange(len(arms))
        w = 0.8 / max(1, len(g["classes"]))
        for j, (c, v) in enumerate(g["classes"].items()):
            sh = [(v["arms"].get(a) or {}).get("share") or 0 for a in arms]
            ci = [(v["arms"].get(a) or {}).get("wilson95") or [0, 0] for a in arms]
            lo = [s - (c_[0] or 0) for s, c_ in zip(sh, ci)]
            hi = [(c_[1] or 0) - s for s, c_ in zip(sh, ci)]
            ax.bar(x + j * w, sh, w, yerr=[lo, hi], capsize=2, color=COL.get(c, "#888"), label=f"target {c}")
        ax.set_xticks(x + w * (len(g["classes"]) - 1) / 2)
        ax.set_xticklabels(arms)
        ax.set_ylabel("share of correct target-class programs")
        ax.set_title(k.replace("gen_", ""), fontsize=9)
        ax.legend(fontsize=7)
    save(fig, "F4_generation")


def f5_mediation() -> None:
    p = RESULTS / "mediation_T10.json"
    if not p.exists():
        return
    m = read_json(p)
    an = read_json(RESULTS / "analysis.json") if (RESULTS / "analysis.json").exists() else {}
    fig, ax = plt.subplots(figsize=(5, 3.6))
    xs = [v["pi"] for v in m["directions"].values() if v.get("escape_pooled") is not None]
    ys = [v["escape_pooled"] for v in m["directions"].values() if v.get("escape_pooled") is not None]
    ax.scatter(xs, ys, s=16, color="#d62728", label="40 iteration-4 directions (retrospective)")
    rho = (m.get("spearman_escape_pooled") or {}).get("rho")
    ax.set_xlabel("committed predictor pi_u (projection of the realised push on the band subspace)")
    ax.set_ylabel("escape share (correct off-default programs)")
    ax.set_title(f"Mediation: Spearman rho = {rho:.2f}" if rho is not None else "Mediation", fontsize=9)
    ax.legend(fontsize=7)
    save(fig, "F5_mediation")


def main() -> None:
    setup_logging("figures8")
    FIGS.mkdir(exist_ok=True)
    an = read_json(RESULTS / "analysis.json") if (RESULTS / "analysis.json").exists() else {}
    f1_scan()
    f2_rank()
    geo = {}
    for unit in ("T10", "GRID"):
        try:
            v = an.get("verdicts", {}).get(f"{unit}-dec", {}).get("verdict")
            g = f3_geometry(unit, v)
            if g:
                geo[unit] = g
        except (RuntimeError, ValueError, KeyError, FileNotFoundError) as e:
            logger.error(f"geometry {unit} failed: {e}")
    write_json(RESULTS / "geometry.json", geo)
    f4_generation(an)
    f5_mediation()
    logger.info(f"figures written: {sorted(p.name for p in FIGS.glob('*.png'))}")


if __name__ == "__main__":
    main()
