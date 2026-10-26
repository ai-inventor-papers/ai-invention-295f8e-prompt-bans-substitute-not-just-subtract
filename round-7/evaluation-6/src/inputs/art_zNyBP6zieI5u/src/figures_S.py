#!/usr/bin/env python3
"""Figures and the S11 geometry (actual activation coordinates, never summary bars only):
- geometry_<space>_L<l>.png/pdf: PCA (PC1/PC2 with variance explained), Isomap (k=10) and classical MDS (stress-1)
  of SPEC-mean states (raw residual with the 5 massive channels removed, or SAE codes) of the forced prompts of the
  6 T1 modes, the 120 neutral variants coloured by y_v, ban-BFS / ban-DFS, TOP5 and its twin; mode centroids sized and
  coloured by the implemented count in the T1 N=200 natural split.
- generated_panel_L22.png: natural BFS and DFS sample states at read positions fork+1..fork+8 (PCA fitted on them).
- fork_trajectories.png: per-base-path P(BFS | prefix) over the coarse scan, with detected change points.
- clamp_cells.png, dose_response.png: S8 cell outcomes with Wilson intervals; logit-level dy vs realised ox-norm.
The landing test (TOP5 centroid vs banned / surviving mode centroids, geodesic) is written to results/geometry.json.
"""

from __future__ import annotations

import itertools
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from cfg import FIG_DIR, RESULTS_DIR, STATES_DIR, T1_MODES, TOP5_BANNED, read_json, read_jsonl, wilson_ci, write_json  # noqa: E402

MODE_COL = {"bfs": "#1f77b4", "dfs": "#d62728", "bibfs": "#2ca02c", "iddfs": "#9467bd", "astar_gbfs": "#ff7f0e",
            "dijkstra": "#8c564b"}


def _save(fig: Any, name: str) -> None:
    fig.savefig(FIG_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def classical_mds(D: np.ndarray, k: int = 2) -> tuple[np.ndarray, float]:
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(-w)[:k]
    X = V[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    Dh = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
    stress = float(np.sqrt(((D - Dh) ** 2).sum() / max((D ** 2).sum(), 1e-12)))
    return X, stress


def geometry(saes: dict, layers: list[int], implemented: dict[str, int]) -> dict[str, Any]:
    import torch
    from sklearn.decomposition import PCA
    from sklearn.manifold import Isomap

    V = torch.load(STATES_DIR / "variants.pt")
    C = torch.load(STATES_DIR / "contrast.pt")
    pts, kinds, modes, yv = [], [], [], []
    for c in C:
        g = c["group"]
        if g.startswith("forced_"):
            pts.append(c)
            kinds.append("forced")
            modes.append(g[len("forced_"):])
            yv.append(np.nan)
        elif g in ("ban_bfs", "ban_dfs", "top5", "top5_twin"):
            pts.append(c)
            kinds.append(g)
            modes.append(None)
            yv.append(np.nan)
    for v in V:
        pts.append(v)
        kinds.append("variant")
        modes.append(None)
        yv.append(v["y"])
    kinds_a, yv_a = np.array(kinds), np.array(yv, dtype=float)
    res: dict[str, Any] = {"n_points": len(pts), "layers": layers, "implemented_counts": implemented, "spaces": {}}
    for space in ("raw", "sae"):
        for l in layers:
            if space == "raw":
                X = np.stack([p["spec_mean"][l].float().numpy() for p in pts])
                massive = np.argsort(-np.abs(X).mean(0))[:5]
                X[:, massive] = 0.0
            else:
                X = np.log1p(np.stack([p["codes_spec_mean"][l].float().numpy() for p in pts]).clip(min=0))
            pca = PCA(n_components=10, random_state=0).fit(X)
            Z = pca.transform(X)
            iso = Isomap(n_neighbors=10, n_components=2)
            Zi = iso.fit_transform(X)
            G = iso.dist_matrix_
            finite = np.isfinite(G)
            Gm = np.where(finite, G, np.nanmax(G[finite]) * 2)
            D = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
            Zm, stress = classical_mds(D)
            # mode centroids and landing test (geodesic: mean pairwise geodesic distance between point sets)
            idx_mode = {m: [i for i, (k, mm) in enumerate(zip(kinds, modes)) if k == "forced" and mm == m] for m in T1_MODES}
            idx_top5 = [i for i, k in enumerate(kinds) if k == "top5"]
            dist_top5 = {m: float(Gm[np.ix_(idx_top5, ii)].mean()) for m, ii in idx_mode.items()}
            dist_eu = {m: float(D[np.ix_(idx_top5, ii)].mean()) for m, ii in idx_mode.items()}
            banned = [m for m in T1_MODES if m in TOP5_BANNED]
            surv = [m for m in T1_MODES if m not in TOP5_BANNED]
            stat = np.mean([dist_top5[m] for m in banned]) - np.mean([dist_top5[m] for m in surv])
            null = []
            for comb in itertools.combinations(T1_MODES, len(banned)):
                b = list(comb)
                s = [m for m in T1_MODES if m not in b]
                null.append(np.mean([dist_top5[m] for m in b]) - np.mean([dist_top5[m] for m in s]))
            rank = float(np.mean(np.array(null) <= stat))
            nearest = min(dist_top5, key=dist_top5.get)
            key = f"{space}|L{l}"
            res["spaces"][key] = {"pca_var_explained": pca.explained_variance_ratio_[:2].tolist(),
                                  "mds_stress1": stress, "geodesic_top5_to_mode": dist_top5,
                                  "euclid_top5_to_mode": dist_eu, "nearest_mode_geodesic": nearest,
                                  "banned_minus_survivor_geodesic": float(stat),
                                  "landing_rank_among_all_4of6_splits": rank,
                                  "landing_reading": ("TOP5 sits at the EDGE of / inside the banned region"
                                                      if stat < 0 else "TOP5 sits on the survivor (opposite) side")}
            # ---- figure
            fig, axs = plt.subplots(1, 3, figsize=(18, 5.6))
            for ax, ZZ, title in ((axs[0], Z[:, :2], f"PCA (PC1 {pca.explained_variance_ratio_[0]:.2f}, "
                                                     f"PC2 {pca.explained_variance_ratio_[1]:.2f})"),
                                  (axs[1], Zi, "Isomap k=10"), (axs[2], Zm, f"classical MDS (stress-1 {stress:.2f})")):
                vm = kinds_a == "variant"
                sc = ax.scatter(ZZ[vm, 0], ZZ[vm, 1], c=yv_a[vm], cmap="coolwarm", s=14, alpha=0.8, marker="o",
                                label="neutral variants (colour = y_v)")
                for m in T1_MODES:
                    ii = idx_mode[m]
                    ax.scatter(ZZ[ii, 0], ZZ[ii, 1], c=MODE_COL[m], s=18, marker="^", alpha=0.6)
                    cen = ZZ[ii].mean(0)
                    cnt = implemented.get(m, 0)
                    ax.scatter([cen[0]], [cen[1]], c=MODE_COL[m], s=80 + 3 * cnt, marker="*", edgecolor="k",
                               label=f"forced {m} centroid (implemented {cnt}/200)")
                for g, mk, col in (("ban_bfs", "x", "#1f77b4"), ("ban_dfs", "x", "#d62728"), ("top5", "P", "k"),
                                   ("top5_twin", "D", "#7f7f7f")):
                    ii = np.where(kinds_a == g)[0]
                    ax.scatter(ZZ[ii, 0], ZZ[ii, 1], c=col, marker=mk, s=60, label=g)
                ax.set_title(title, fontsize=10)
                ax.set_xlabel("dim 1 (activation coordinates)")
                ax.set_ylabel("dim 2")
            axs[0].legend(fontsize=6, loc="best")
            fig.colorbar(sc, ax=axs[2], label="y_v = fork logit readout (BFS vs DFS)")
            fig.suptitle(f"T1 SPEC-mean states, {'raw residual (5 massive channels removed)' if space == 'raw' else 'SAE codes log1p'}, "
                         f"block {l}; TOP5 nearest (geodesic): {nearest}", fontsize=11)
            _save(fig, f"geometry_{space}_L{l}")
    write_json(RESULTS_DIR / "geometry.json", res)
    return res


def generated_panel(fk: dict[str, Any], layer_idx: int = 2, layer: int = 22) -> dict[str, Any]:
    import torch
    from sklearn.decomposition import PCA

    S = torch.load(STATES_DIR / "s3_T1.pt")
    H, meta = S["H"], S["meta"]
    tf = fk["fork_token_index"]
    js = list(range(tf + 1, tf + 9))
    X, lab, sid = [], [], []
    for i, m in enumerate(meta):
        if m["label"] not in ("bfs", "dfs") or m["n_pos"] <= js[-1]:
            continue
        for j in js:
            X.append(H[i, j, layer_idx].float().numpy())
            lab.append(m["label"])
            sid.append(i)
    X = np.stack(X)
    X[:, np.argsort(-np.abs(X).mean(0))[:5]] = 0
    p = PCA(n_components=2, random_state=0).fit(X)
    Z = p.transform(X)
    fig, ax = plt.subplots(figsize=(7, 6))
    sid_a, lab_a = np.array(sid), np.array(lab)
    for s in sorted(set(sid)):
        ii = np.where(sid_a == s)[0]
        ax.plot(Z[ii, 0], Z[ii, 1], color=MODE_COL[lab_a[ii[0]]], alpha=0.25, lw=0.8)
    for c in ("bfs", "dfs"):
        ii = lab_a == c
        ax.scatter(Z[ii, 0], Z[ii, 1], c=MODE_COL[c], s=8, alpha=0.6, label=f"natural {c.upper()} samples")
    ax.set_xlabel(f"PC1 ({p.explained_variance_ratio_[0]:.2f})")
    ax.set_ylabel(f"PC2 ({p.explained_variance_ratio_[1]:.2f})")
    ax.set_title(f"Block {layer} states at read positions fork+1..fork+8 (fork token index {tf})")
    ax.legend()
    _save(fig, f"generated_panel_L{layer}")
    return {"n_samples": len(set(sid)), "pca_var": p.explained_variance_ratio_.tolist()}


def fork_figure(fk: dict[str, Any]) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    for p in fk["per_path"]:
        col = MODE_COL["bfs"] if p["label"] == "bfs" else MODE_COL["dfs"]
        axs[0].plot(p["t"], p["p_bfs"], color=col, alpha=0.5, marker=".")
        if p["fork_t"] is not None:
            axs[0].axvline(p["fork_t"], color=col, alpha=0.15)
    axs[0].axvline(fk["fork_token_index"], color="k", ls="--", label=f"fork token index {fk['fork_token_index']}")
    axs[0].set_xlabel("prefix length t (response tokens kept from the base path)")
    axs[0].set_ylabel("P(BFS) among 8 continuations")
    axs[0].set_title("Coarse prefix resampling (blue = BFS base paths, red = DFS base paths)")
    axs[0].legend()
    for r in fk.get("refined", []):
        ts = [s["t"] for s in r["series"]]
        ps = [s["p_bfs"] for s in r["series"]]
        axs[1].plot(ts, ps, marker="o", color=MODE_COL["bfs"] if r["label"] == "bfs" else MODE_COL["dfs"], alpha=0.7,
                    label=f"{r['row_id'].split('|')[2]} s{r['row_id'].split('|')[-1]}: '{r['fork_token']}'")
    axs[1].set_xlabel("prefix length t (single-token refinement, 16 continuations)")
    axs[1].set_ylabel("P(BFS)")
    axs[1].legend(fontsize=6)
    axs[1].set_title("Refinement around each path's change point")
    _save(fig, "fork_trajectories")


def clamp_figure(cl: dict[str, Any], ceiling: dict[str, Any]) -> None:
    cells = cl["cells"]
    names = ["twin_cstar"] + sorted(k for k in cells if k != "twin_cstar")
    fig, ax = plt.subplots(figsize=(12, 5))
    xs = np.arange(len(names) + 2)
    vals, los, his, labels = [], [], [], []
    for n in names:
        c = cells[n]
        tgt = (c["meta"].get("toward") or "bfs")
        k = c.get("target_correct", 0) if n != "twin_cstar" else c["correct"].get("bfs", 0)
        lo, hi = wilson_ci(k, c["n"])
        vals.append(k / max(c["n"], 1))
        los.append(k / max(c["n"], 1) - lo)
        his.append(hi - k / max(c["n"], 1))
        labels.append(n + ("" if tgt == "bfs" else " [target DFS]"))
    for arm in ("forced_bfs", "forced_dfs"):
        c = ceiling[arm]
        k = c["correct"].get(arm.split("_")[1], 0)
        lo, hi = wilson_ci(k, c["n"])
        vals.append(k / c["n"])
        los.append(k / c["n"] - lo)
        his.append(hi - k / c["n"])
        labels.append(f"prompt ceiling: {arm}")
    los = [max(0.0, x) for x in los]
    his = [max(0.0, x) for x in his]
    ax.bar(xs, vals, yerr=[los, his], color=["#7f7f7f"] + ["#1f77b4"] * (len(names) - 1) + ["#2ca02c", "#2ca02c"])
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("target-class correct share (Wilson 95% CI)")
    ax.set_title("S8 clamp cells (N=50 each, CRN-paired) vs canonical-prefix twin and prompting ceiling")
    _save(fig, "clamp_cells")


def dose_figure() -> None:
    rows = read_jsonl(RESULTS_DIR / "logit_sweep.jsonl")
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, site in zip(axs, ("FORK", "SPEC")):
        for kind, col in (("FEAT", "#1f77b4"), ("DiM", "#2ca02c"), ("RANDF", "#ff7f0e"), ("ISO", "#7f7f7f")):
            rr = [r for r in rows if r["site"] == site and r["kind"] == kind and r["src"] in ("input",)
                  and r["dy"] is not None]
            if not rr:
                continue
            groups: dict[tuple, list] = {}
            for r in rr:
                groups.setdefault((r["k"], r["lam"], r["layer"]), []).append(r)
            xs = [np.mean([x.get("ox_norm_mean", 0) for x in g]) for g in groups.values()]
            ys = [np.mean([x["dy"] for x in g]) for g in groups.values()]
            ax.scatter(xs, ys, c=col, label=kind, s=25)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xscale("symlog")
        ax.set_xlabel("realised edit norm, massive channels excluded (mean over site positions)")
        ax.set_ylabel("mean dy (fork logit readout), 120 variants")
        ax.set_title(f"{site} site: dose-response, toward BFS")
        ax.legend()
    _save(fig, "dose_response")


__all__ = ["geometry", "generated_panel", "fork_figure", "clamp_figure", "dose_figure"]
_ = read_json
