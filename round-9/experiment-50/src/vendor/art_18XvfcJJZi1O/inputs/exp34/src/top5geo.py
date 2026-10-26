#!/usr/bin/env python3
"""G.5 geometry of the T1 grid-path catalogue in actual activation coordinates (no summary bars).

Points: S-mean block outputs (mean over the task-spec positions) of the exp9 forced 'Implement X' prompts, 10
algorithms x 10 paraphrases, at L_geo (exp30's F5 geometry blocks were 12-23; we use block 18, the middle of the
iteration-4 GEO_BLOCKS (18, 23)) and at L_ax(T1) = median of the three P2 tasks' L_ax.
  - Isomap with k in {5, 10, 15} (raw coordinates, no whitening) and classical MDS with Kruskal stress-1
  - g(X) = mean geodesic distance (Isomap k = 10 graph) between survivor X's points and the nearest banned
    algorithm's points; 'edge' survivors = g <= median, 'opposite' = the rest
  - out-of-sample placement (Isomap.transform) of the twins, the BFS ban, the top-five ban, the realised pushed
    twin states of every push arm and s, and exp30's old u_top5 push (alpha 1-8) -> figures/F6_top5_geometry
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import c7 as common  # noqa: E402
from c7 import FIGS, IN30, PRED, RESULTS, STATES, read_json, write_json  # noqa: E402

T1_SURV = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
T1_TOP5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]


def stress1(D: np.ndarray, Y: np.ndarray) -> float:
    from scipy.spatial.distance import pdist, squareform
    d = squareform(pdist(Y))
    iu = np.triu_indices(len(D), 1)
    return float(np.sqrt(((D[iu] - d[iu]) ** 2).sum() / (D[iu] ** 2).sum()))


def classical_mds(D: np.ndarray, k: int = 2) -> np.ndarray:
    n = len(D)
    J = np.eye(n) - 1 / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    i = np.argsort(w)[::-1][:k]
    return V[:, i] * np.sqrt(np.maximum(w[i], 0))


def geometry(layer: int) -> dict[str, Any]:
    from scipy.sparse.csgraph import shortest_path
    from scipy.spatial.distance import pdist, squareform
    from sklearn.decomposition import PCA
    from sklearn.manifold import Isomap
    from sklearn.neighbors import kneighbors_graph
    z = np.load(STATES / "top5_T1_states.npz", allow_pickle=True)
    blocks = list(z["blocks"])
    li = blocks.index(layer)
    X = z["smean"][:, li].astype(np.float64)
    labels = list(z["labels"])
    out: dict[str, Any] = {"layer": layer, "n_points": len(X)}
    D = squareform(pdist(X))
    emb = {}
    for k in (5, 10, 15):
        iso = Isomap(n_neighbors=k, n_components=2)
        Y = iso.fit_transform(X)
        G = kneighbors_graph(X, k, mode="distance")
        geo = shortest_path(G, directed=False)
        finite = np.isfinite(geo)
        out[f"isomap_k{k}"] = {"connected": bool(finite.all()), "stress1_vs_geodesic":
                               stress1(np.where(finite, geo, np.nanmax(geo[finite])), Y)}
        emb[k] = (iso, Y, geo)
    Ym = classical_mds(D)
    out["mds_stress1"] = stress1(D, Ym)
    pca = PCA(n_components=2).fit(X)
    out["pca_explained_variance_ratio"] = pca.explained_variance_ratio_.tolist()
    k_g = next((k for k in (5, 10, 15) if out[f"isomap_k{k}"]["connected"]), 15)
    out["k_for_geodesic_g"] = k_g     # smallest k whose kNN graph is connected (decided before any T1 landing)
    iso, Y, geo = emb[k_g]
    lab = np.array(labels)
    g = {}
    for Xs in T1_SURV:
        dmin = []
        for b in T1_TOP5:
            dd = geo[np.ix_(lab == Xs, lab == b)]
            dd = dd[np.isfinite(dd)]
            dmin.append(float(dd.mean()) if dd.size else np.inf)
        g[Xs] = float(min(dmin))
        out.setdefault("nearest_banned", {})[Xs] = T1_TOP5[int(np.argmin(dmin))]
    med = float(np.median(list(g.values())))
    out["g_geodesic"] = g
    out["edge_survivors"] = [x for x in T1_SURV if g[x] <= med]
    order = sorted(T1_SURV, key=lambda x: g[x])
    out["g_rank_norm"] = {x: i / (len(order) - 1) for i, x in enumerate(order)}
    cent = {c: X[lab == c].mean(0) for c in sorted(set(labels))}
    out["centroid_distances_to_banned_centroid"] = {c: float(np.linalg.norm(v - np.mean([cent[b] for b in T1_TOP5],
                                                                                         0)))
                                                    for c, v in cent.items()}
    return out | {"_emb": emb, "_X": X, "_labels": labels, "_pca": pca, "_Ym": Ym}


def placed_points(layer: int) -> dict[str, np.ndarray]:
    """S-mean states of twins, BFS ban, top-five ban (this run), realised pushed twin states (recomputed from the
    raw rows' realised records is not possible -> from cache/states/top5_push_states.npz if present) and exp30's
    old u_top5 push states (geometry_T1_states.npz, blocks 12-23)."""
    z = np.load(STATES / "top5_T1_states.npz", allow_pickle=True)
    blocks = list(z["blocks"])
    li = blocks.index(layer)
    pts = {}
    for k in z.files:
        if "__" in k:
            pts[k] = z[k][li]
    p = STATES / "top5_push_states.npz"
    if p.exists():
        zp = np.load(p)
        for k in zp.files:
            pts[k] = zp[k][blocks.index(layer)] if zp[k].ndim == 2 else zp[k]
    g30 = np.load(IN30 / "geometry_T1_states.npz")
    b30 = list(g30["blocks"])
    if layer in b30:
        for k in g30.files:
            if k.startswith("push"):
                pts[f"old_u_top5_{k}"] = g30[k][b30.index(layer)]
    return pts


def figure(res: dict[str, Any], layer: int, tag: str) -> None:
    """Row 1: Isomap / PC1-PC2 with the old u_top5 overshoot (full extent) and classical MDS of the forced points;
    row 2: the same Isomap / PCA zoomed on the catalogue (old overshoot omitted) with every placed state."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    k_g = res.get("k_for_geodesic_g", 10)
    iso, Y, _ = res["_emb"][k_g]
    lab = np.array(res["_labels"])
    pca = res["_pca"]
    X = res["_X"]
    P2 = pca.transform(X)
    pts = placed_points(layer)
    fig, axes = plt.subplots(2, 3, figsize=(19, 12))
    cmap = plt.get_cmap("tab10")
    cats = T1_TOP5 + T1_SURV
    ev = pca.explained_variance_ratio_
    panels = [(axes[0, 0], f"Isomap k={k_g}: forced-prompt states + old u_top5 push (alpha 1-8)", Y, iso.transform, True),
              (axes[0, 1], "PC1-PC2 of forced-prompt states + old u_top5 push", P2, pca.transform, True),
              (axes[0, 2], "classical MDS (Euclidean) of forced-prompt states", res["_Ym"], None, False),
              (axes[1, 0], f"Isomap k={k_g}, zoom: in-manifold pushes, bans, twins", Y, iso.transform, False),
              (axes[1, 1], "PC1-PC2, zoom: in-manifold pushes, bans, twins", P2, pca.transform, False)]
    for ax, name, coords, tf, with_old in panels:
        for i, c in enumerate(cats):
            m = lab == c
            ax.scatter(coords[m, 0], coords[m, 1], s=22, color=cmap(i), marker="o" if c in T1_TOP5 else "^",
                       label=f"{c} ({'banned' if c in T1_TOP5 else 'survivor'})", alpha=0.75)
            cx, cy = coords[m].mean(0)
            ax.annotate(c, (cx, cy), fontsize=8, weight="bold")
        if tf is not None:
            for gname, col in (("twin", "k"), ("ban", "red"), ("top5ban", "purple")):
                q = np.array([v for k, v in pts.items() if k.startswith(f"{gname}__")])
                if len(q):
                    qq = tf(q.astype(np.float64))
                    ax.scatter(qq[:, 0], qq[:, 1], s=90, marker="X", color=col, edgecolor="w",
                               label={"twin": "neutral twin W1-W5", "ban": "BFS ban W1-W5",
                                      "top5ban": "prompt top-five ban W1-W5"}[gname])
            for arm, col in (("SURV", "tab:green"), ("RSURV", "tab:olive"), ("AWAY", "tab:brown")):
                for sv, mk in (("0.25", "s"), ("0.5", "D"), ("1", "P")):
                    q = np.array([v for k, v in pts.items() if k.startswith(f"{arm}_s{sv}__")])
                    if len(q):
                        qq = tf(q.astype(np.float64))
                        ax.scatter(qq[:, 0], qq[:, 1], s=60, marker=mk, color=col, edgecolor="k", lw=0.5,
                                   label=f"{arm} push s={sv}")
            if with_old:
                for a in ("1", "2", "4", "8"):
                    q = np.array([v for k, v in pts.items() if k.startswith(f"old_u_top5_push{a}__")])
                    if len(q):
                        qq = tf(q.astype(np.float64))
                        ax.scatter(qq[:, 0], qq[:, 1], s=50, marker="*", color="gray")
                        ax.annotate(f"old a={a}", qq.mean(0), fontsize=7, color="gray")
        ax.set_title(name, fontsize=10)
        if "PC1" in name:
            ax.set_xlabel(f"PC1 ({ev[0]:.1%} of forced-state variance)")
            ax.set_ylabel(f"PC2 ({ev[1]:.1%})")
        else:
            ax.set_xlabel("component 1")
            ax.set_ylabel("component 2")
        if not with_old and tf is not None:
            cx = coords[:, 0]
            cy = coords[:, 1]
            padx, pady = 0.25 * np.ptp(cx), 0.25 * np.ptp(cy)
            ax.set_xlim(cx.min() - padx, cx.max() + padx)
            ax.set_ylim(cy.min() - pady, cy.max() + pady)
    h, l = axes[1, 0].get_legend_handles_labels()
    axes[1, 2].axis("off")
    axes[1, 2].legend(h, l, loc="center", ncol=2, fontsize=8)
    fig.suptitle(f"T1 grid-path catalogue at block {layer} (actual activation coordinates: S-mean block outputs of "
                 f"10 forced paraphrases per algorithm); geodesic edge survivors {res['edge_survivors']}", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"F6_top5_geometry_{tag}.{ext}", dpi=140)
    plt.close(fig)


def main() -> None:
    ax = read_json(PRED / "commit2_axis.json")
    L_ax_T1 = int(np.median([ax[t]["L_ax"] for t in ("T10", "T2", "T03")]))
    out = {}
    for layer, tag in ((18, "Lgeo18"), (L_ax_T1, f"Lax{L_ax_T1}")):
        r = geometry(layer)
        figure(r, layer, tag)
        out[tag] = {k: v for k, v in r.items() if not k.startswith("_")}
    prim = out["Lgeo18"]
    res = {"L_geo": 18, "L_ax_T1": L_ax_T1, "per_layer": out, "edge_survivors": prim["edge_survivors"],
           "g_rank_norm": prim["g_rank_norm"], "g_geodesic": prim["g_geodesic"]}
    write_json(RESULTS / "top5_geometry.json", res)
    print(res["edge_survivors"])


if __name__ == "__main__":
    main()
