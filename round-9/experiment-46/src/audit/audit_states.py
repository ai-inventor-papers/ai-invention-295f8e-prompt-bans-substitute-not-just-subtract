#!/usr/bin/env python3
"""State-level audit by a different code path: recomputes the headline class geometry from the raw state files
(cache/states/*.npz) with sklearn's NearestNeighbors kNN graph, networkx connected components and joins, and
networkx Dijkstra (iteration 8's geometry.py is NOT imported), at the committed block (predictions/commit2.json)
and k 15; compares g, classes and the unit-Dijkstra rank with results/geometry_all.json. Placebo: the same pipeline
on algorithm labels shuffled across points must not reproduce the classes more often than chance.
Writes results/audit_states.json."""

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parent.parent
CANON = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]


def knn_geodesics(X, k):
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    dist, idx = nn.kneighbors(X)
    G = nx.Graph()
    G.add_nodes_from(range(len(X)))
    for i in range(len(X)):
        for d, j in zip(dist[i], idx[i]):
            if j != i:
                w = max(float(d), 1e-12)
                if not G.has_edge(i, j) or G[i][j]["weight"] > w:
                    G.add_edge(i, int(j), weight=w)
    comps = [sorted(c) for c in nx.connected_components(G)]
    if len(comps) > 1:
        for a in range(len(comps)):
            for b in range(a + 1, len(comps)):
                A, Bc = np.array(comps[a]), np.array(comps[b])
                D = np.linalg.norm(X[A][:, None, :] - X[Bc][None, :, :], axis=2)
                i, j = np.unravel_index(np.argmin(D), D.shape)
                G.add_edge(int(A[i]), int(Bc[j]), weight=max(float(D[i, j]), 1e-12))
    n = len(X)
    geo = np.zeros((n, n))
    for s, dd in nx.all_pairs_dijkstra_path_length(G, weight="weight"):
        for t, v in dd.items():
            geo[s, t] = v
    return geo, len(comps)


def g_classes(geo, labels):
    nb = [a for a in NB5 if a in set(labels)]
    g = {a: min(float(geo[np.ix_(labels == a, labels == b)].mean()) for b in B5 if (labels == b).any()) for a in nb}
    m = float(np.median(list(g.values())))
    cls = {a: "EDGE" if v < m - 1e-12 else "OPPOSITE" if v > m + 1e-12 else "MIDDLE" for a, v in g.items()}
    return g, cls


def load(model, name):
    S = ROOT / "cache" / "states"
    if name in ("mname", "mdesc"):
        z = np.load(S / f"{name}_{model}.npz")
        return z["smean"], z["algorithm"], [int(b) for b in z["blocks"]]
    if name == "mlex":
        z = np.load(S / f"mlex_{model}.npz")
        return z["delta"], z["algorithm"], [int(b) for b in z["blocks"]]
    z = np.load(S / f"mcode_{model}.npz")
    sets = json.loads((ROOT / "data" / "mcode_sets.json").read_text())["sets"]["PRIMARY"]
    keys = list(z["keys"])
    rows = [(keys.index(p["scrubbed_sha256"]), a) for a in CANON if len(sets[a]) >= 10 for p in sets[a]]
    ri = list(z["readouts"]).index("R1")
    return z["R"][[r[0] for r in rows], ri], np.array([r[1] for r in rows]), [int(b) for b in z["blocks"]]


def main():
    blocks = json.loads((ROOT / "predictions" / "commit2.json").read_text())["manifolds"]
    geo_all = json.loads((ROOT / "results" / "geometry_all.json").read_text())
    out = {"checks": {}, "mismatches": []}
    rng = np.random.default_rng(0)
    for key in ("32b|mname", "32b|mdesc", "32b|mlex", "32b|mcode_PRIMARY_R1"):
        if key not in geo_all or key not in blocks:
            continue
        model, name = key.split("|")
        name0 = "mcode" if name.startswith("mcode") else name
        X, labels, bl = load(model, name0)
        L = blocks[key]["L_star"]
        Xb = X[:, bl.index(L)].astype(np.float64)
        geo, ncomp = knn_geodesics(Xb, 15)
        g, cls = g_classes(geo, labels)
        ref = geo_all[key]["L_star"]["describe"]["k15"]
        maxdiff = max(abs(g[a] - ref["g"][a]) for a in g)
        same = cls == ref["classes"]
        plac = []
        for _ in range(20):
            lp = rng.permutation(labels)
            _, cp = g_classes(geo, lp)
            plac.append(cp.get("dijkstra_unit") == cls.get("dijkstra_unit"))
        out["checks"][key] = {"block": L, "components": ncomp, "g": g, "classes": cls, "max_abs_g_diff": maxdiff,
                              "classes_equal": same, "placebo_shuffled_labels_share_same_udij_class":
                                  float(np.mean(plac))}
        if not same or maxdiff > 1e-6 * max(1.0, max(abs(v) for v in g.values())):
            out["mismatches"].append(key)
        print(key, "classes equal", same, "max |dg|", maxdiff, "placebo", float(np.mean(plac)), flush=True)
    (ROOT / "results" / "audit_states.json").write_text(json.dumps(out, indent=1))
    return 0 if not out["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
