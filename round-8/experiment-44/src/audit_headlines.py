#!/usr/bin/env python3
"""Short independent audit of the headline numbers (TODO 5). Reads raw rows and cached states directly and recomputes
through code paths the pipeline does not use: set logic for survivors, scipy binomtest for Wilson intervals, a sklearn
kNN graph + networkx Dijkstra for geodesics, exact enumeration (not Monte Carlo) for the uniform landing null, and
placebos (shuffled point labels, random survivor labels, shuffled screen labels) on which the test must not pass.
Run: .venv/bin/python audit_headlines.py   -> results/audit_headlines.json"""

import itertools
import json
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.stats import binomtest
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parent
BANNED = {"bfs", "dfs", "iddfs", "astar", "gbfs"}
NONB = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
CAT = BANNED | set(NONB)


def rows(cid, arm):
    p = ROOT / "data" / f"labelled_{cid}_{arm}.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def survivors(rs):
    ok = []
    for r in rs:
        lab = r.get("adj_label")
        if r.get("passed") is True and lab not in BANNED | {"invalid", None} and (
                lab in CAT or (lab == "other" and r.get("adj_other_name"))):
            ok.append(r)
    return ok


def geodesic_g(X, labels, k):
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    dist, idx = nn.kneighbors(X)
    G = nx.Graph()
    G.add_nodes_from(range(len(X)))
    for i in range(len(X)):
        for d, j in zip(dist[i][1:], idx[i][1:]):
            G.add_edge(i, int(j), weight=float(d))
    assert nx.is_connected(G), "kNN graph disconnected"
    D = dict(nx.all_pairs_dijkstra_path_length(G, weight="weight"))
    M = np.array([[D[i][j] for j in range(len(X))] for i in range(len(X))])
    return {a: min(M[np.ix_(labels == a, labels == b)].mean() for b in BANNED) for a in NONB}


def exact_p_opp(g, surv):
    """P(mean of len(surv) iid uniform draws over the 5 non-banned g values >= S), by full enumeration."""
    S = np.mean([g[a] for a in surv])
    vals = [g[a] for a in NONB]
    n = len(surv)
    hits = sum(1 for c in itertools.product(vals, repeat=n) if np.mean(c) >= S - 1e-12)
    return S, hits / 5 ** n


def main():
    out = {}
    screen = json.loads((ROOT / "results" / "screen.json").read_text())
    shares = {}
    for cid in [f"C{i}" for i in range(1, 9)]:
        rs = rows(cid, "ban")
        k, n = len(survivors(rs)), len(rs)
        ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
        shares[cid] = {"k": k, "n": n, "share": k / n, "wilson": [ci.low, ci.high],
                       "matches_screen_json": k == screen[cid]["n_correct_survivors"] and
                       abs(ci.low - screen[cid]["share_cs_wilson95"][0]) < 1e-6}
    out["screen_shares"] = shares
    out["Q"] = sorted(c for c, s in shares.items() if s["share"] >= 0.20)
    rc = rows("C6", "confirm")
    kc = len(survivors(rc))
    ci = binomtest(kc, len(rc)).proportion_ci(method="wilson")
    out["confirmation_share"] = {"k": kc, "n": len(rc), "share": kc / len(rc), "wilson": [ci.low, ci.high]}
    # geometry from raw S-mean states (block L* = 31, k = 15 = the committed primary k)
    z = np.load(ROOT / "cache" / "states" / "smean_C6_nf4.npz")
    F = z["kind"] == "forced"
    blocks = [int(b) for b in z["blocks"]]
    X = z["smean"][F][:, blocks.index(31)].astype(np.float64)
    labels = z["algorithm"][F]
    g = geodesic_g(X, labels, 15)
    landing = json.loads((ROOT / "results" / "landing.json").read_text())
    out["g_k15"] = g
    out["g_max_abs_diff_vs_pipeline"] = max(abs(g[a] - landing["primary"]["g"][a]) for a in NONB)
    surv = [r["adj_label"] for r in survivors(rows("C6", "ban")) if r["adj_label"] in NONB]
    S, p = exact_p_opp(g, surv)
    out["landing"] = {"survivors": surv, "S": S, "exact_p_opp_uniform": p, "pipeline_S": landing["primary"]["S"],
                      "pipeline_p_opp_U_montecarlo": landing["primary"]["nulls"]["U"]["p_opp"]}
    surv_c = [r["adj_label"] for r in survivors(rc) if r["adj_label"] in NONB]
    Sc, pc = exact_p_opp(g, surv_c)
    out["confirmation_landing"] = {"survivors": surv_c, "S": Sc, "exact_p_opp_uniform": pc}
    # placebo 1: shuffle the algorithm labels of the 300 forced points (geometry destroyed)
    rng = np.random.default_rng(0)
    sig = 0
    for _ in range(100):
        gp = geodesic_g(X, rng.permutation(labels), 15)
        sig += exact_p_opp(gp, surv)[1] < 0.05
    out["placebo_shuffled_points_sig_rate"] = sig / 100
    # placebo 2: random survivor labels on the real geometry
    sig2 = sum(exact_p_opp(g, list(rng.choice(NONB, size=len(surv))))[1] < 0.05 for _ in range(500))
    out["placebo_random_survivors_sig_rate"] = sig2 / 500
    # placebo 3: shuffle adj_label across C6 ban rows -> share of correct survivors
    r6 = rows("C6", "ban")
    labs = [r.get("adj_label") for r in r6]
    sh = []
    for _ in range(200):
        perm = rng.permutation(len(labs))
        sh.append(len(survivors([dict(r, adj_label=labs[j]) for r, j in zip(r6, perm)])) / len(r6))
    out["placebo_shuffled_labels_C6_share_mean"] = float(np.mean(sh))
    (ROOT / "results" / "audit_headlines.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("Q", "confirmation_share", "landing", "g_max_abs_diff_vs_pipeline",
                                          "placebo_shuffled_points_sig_rate", "placebo_random_survivors_sig_rate",
                                          "placebo_shuffled_labels_C6_share_mean")}, default=float))
    print({c: (s["k"], s["n"], s["matches_screen_json"]) for c, s in shares.items()})


if __name__ == "__main__":
    main()
