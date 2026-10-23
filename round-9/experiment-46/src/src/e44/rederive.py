#!/usr/bin/env python3
"""T11 independent re-derivation (stdlib + numpy only; no sklearn/scipy, no project modules).

Recomputes from the raw labelled rows and the cached states: per-configuration correct-survivor shares and Wilson
bounds, the selection, L* (re-applying the committed tie rule to the saved CV curve), the geodesic g values (own kNN
graph + Floyd-Warshall), the landing statistic S and every null p value, the verdicts, a label-shuffle placebo, and
the commitments chain (each commit precedes the first row it governs). Writes results/rederive.json.
Run: .venv/bin/python src/rederive.py
"""

import collections
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
D = ROOT / "data"
CANON = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]


def rj(p):
    return json.loads(Path(p).read_text())


def rl(p):
    p = Path(p)
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def is_cs(r, banned):
    if not r.get("passed"):
        return False
    lab = r.get("adj_label")
    if lab in banned or lab in ("invalid", "no_code", None):
        return False
    if lab in CANON:
        return True
    return lab == "other" and bool(r.get("adj_other_name"))


def knn_geodesics(X, k):
    n = len(X)
    sq = (X * X).sum(1)
    Dm = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0))
    Dm[Dm == 0] = 1e-12
    np.fill_diagonal(Dm, 0)
    W = np.full((n, n), np.inf)
    order = np.argsort(Dm, axis=1)
    for i in range(n):
        nb = [j for j in order[i] if j != i][:k]
        W[i, nb] = Dm[i, nb]
    W = np.minimum(W, W.T)
    np.fill_diagonal(W, 0)
    # components (BFS over the finite-weight adjacency) and shortest inter-component joins
    adj = np.isfinite(W)
    comp = -np.ones(n, int)
    c = 0
    for s in range(n):
        if comp[s] >= 0:
            continue
        stack = [s]
        comp[s] = c
        while stack:
            u = stack.pop()
            for v in np.where(adj[u] & (comp < 0))[0]:
                comp[v] = c
                stack.append(v)
        c += 1
    ncomp = c
    for a in range(ncomp):
        for b in range(a + 1, ncomp):
            ia, ib = np.where(comp == a)[0], np.where(comp == b)[0]
            sub = Dm[np.ix_(ia, ib)]
            i, j = np.unravel_index(np.argmin(sub), sub.shape)
            W[ia[i], ib[j]] = W[ib[j], ia[i]] = max(sub[i, j], 1e-12)
    G = W.copy()
    for m in range(n):                      # Floyd-Warshall, vectorised
        G = np.minimum(G, G[:, m:m + 1] + G[m:m + 1, :])
    return G, ncomp


def g_vals(G, labels, banned, nonb):
    g = {}
    for a in nonb:
        g[a] = min(float(G[np.ix_(labels == a, labels == b)].mean()) for b in banned)
    return g


def classes(g):
    med = float(np.median(list(g.values())))
    return {a: ("EDGE" if v < med - 1e-12 else "OPPOSITE" if v > med + 1e-12 else "MIDDLE") for a, v in g.items()}


def nulls(g, surv, base_counts, rates, draws=10000, seed=0):
    algs = list(g)
    vals = np.array([g[a] for a in algs])
    n = len(surv)
    S = float(np.mean([g[a] for a in surv]))
    out = {"S": S}
    for key, probs, sd in (("U", {a: 1.0 for a in algs}, seed), ("F", {a: base_counts.get(a, 0) + 0.5 for a in algs},
                                                                     seed + 1),
                           ("C", {a: rates.get(a, 0.0) + 0.5 / 40 for a in algs}, seed + 2)):
        p = np.array([probs[a] for a in algs], float)
        p /= p.sum()
        rng = np.random.default_rng(sd)
        nl = vals[rng.choice(len(algs), size=(draws, n), p=p)].mean(1)
        out[key] = {"p_edge": float(np.mean(nl <= S + 1e-12)), "p_opp": float(np.mean(nl >= S - 1e-12))}
    cnt = collections.Counter(surv)
    counts = np.array([cnt[a] for a in algs], float)
    P = np.array([(counts * vals[list(pm)]).sum() / counts.sum() for pm in itertools.permutations(range(len(algs)))])
    out["P"] = {"p_edge": float(np.mean(P <= S + 1e-12)), "p_opp": float(np.mean(P >= S - 1e-12))}
    return out


def verdict(nl, cls, surv):
    n = len(surv)
    sh = collections.Counter(cls[a] for a in surv)
    if nl["U"]["p_edge"] < 0.05 and nl["F"]["p_edge"] < 0.05 and sh["EDGE"] / n > 0.5:
        return "EDGE"
    if nl["U"]["p_opp"] < 0.05 and nl["F"]["p_opp"] < 0.05 and sh["OPPOSITE"] / n > 0.5:
        return "OPPOSITE"
    return "NEITHER"


def main():
    out = {"mismatches": []}
    c2 = rj(ROOT / "predictions" / "commit2.json")
    screen = rj(R / "screen.json")
    sel = rj(R / "selection.json")
    shares = {}
    rows_by = {}
    for cid, banned in c2["banned_sets"].items():
        rows = rl(D / f"labelled_{cid}_ban.jsonl")
        if not rows:
            continue
        rows_by[cid] = rows
        k = sum(is_cs(r, banned) for r in rows)
        shares[cid] = {"k": k, "n": len(rows), "share": k / len(rows), "wilson": wilson(k, len(rows))}
        if abs(shares[cid]["share"] - screen[cid]["share_cs"]) > 1e-12:
            out["mismatches"].append(f"share {cid}")
        if max(abs(a - b) for a, b in zip(shares[cid]["wilson"], screen[cid]["share_cs_wilson95"])) > 1e-9:
            out["mismatches"].append(f"wilson {cid}")
    out["shares"] = shares
    q = [c for c, s in shares.items() if s["share"] >= 0.20]
    out["Q"] = sorted(q)
    if sorted(q) != sel["Q"]:
        out["mismatches"].append("Q")
    # geometry and landing
    geo = rj(R / "geometry_M1.json")
    land = rj(R / "landing.json")
    curve = {int(k): v for k, v in geo["layer_curve"]["curve"].items()}
    nl_ = rj(R / f"states_{geo['tag']}.json")["n_layers"]
    best = max(curve.values())
    near = [b for b in sorted(curve) if best - curve[b] <= 0.01]
    Lr = min(near, key=lambda b: (abs((b + 1) / nl_ - 0.5), b))
    if all(v >= 0.9999 for v in curve.values()):
        Lr = min(curve, key=lambda b: (abs((b + 1) / nl_ - 0.5), b))
    out["L_star"] = Lr
    if Lr != geo["L_star"]:
        out["mismatches"].append("L_star")
    z = np.load(ROOT / "cache" / "states" / f"smean_{geo['tag']}.npz")
    F = z["kind"] == "forced"
    blocks = [int(b) for b in z["blocks"]]
    X = z["smean"][F][:, blocks.index(Lr)].astype(np.float64)
    labels = z["algorithm"][F]
    banned = geo["banned"]
    nonb = [a for a in CANON if a not in banned]
    kp = geo["M1"]["k_primary"]
    G, ncomp = knn_geodesics(X, kp)
    g = g_vals(G, labels, banned, nonb)
    out["g"] = g
    gm = geo["M1"][f"k{kp}"]["g"]
    out["g_max_abs_diff"] = max(abs(g[a] - gm[a]) for a in nonb)
    if out["g_max_abs_diff"] > 1e-6 * max(1.0, max(abs(v) for v in gm.values())):
        out["mismatches"].append("g")
    cls = classes(g)
    if cls != geo["M1"][f"k{kp}"]["classes"]:
        out["mismatches"].append("classes")
    surv = land["survivors"]
    ms = sel["m_star"]
    base = rl(D / f"labelled_{ms}_baseline.jsonl")
    bc = collections.Counter(r["adj_label"] for r in base)
    keep = rj(ROOT / "inputs" / "exp9" / "results" / "catalogue_keep.json")["tasks"]["t1"]
    rates = {a: keep[a]["passed_as_requested"] / keep[a]["n_forced"] for a in CANON}
    if surv:
        nl = nulls(g, surv, {a: bc.get(a, 0) for a in nonb}, rates)
        out["S"] = nl["S"]
        out["p"] = {k: v for k, v in nl.items() if k != "S"}
        v = verdict(nl, cls, surv)
        out["verdict"] = v
        lp = land["primary"]
        if abs(nl["S"] - lp["S"]) > 1e-6:
            out["mismatches"].append("S")
        for key in ("U", "F", "C", "P"):
            for side in ("p_edge", "p_opp"):
                if abs(nl[key][side] - lp["nulls"][key][side]) > 1e-9:
                    out["mismatches"].append(f"p_{key}_{side}")
        if v != lp["verdict"]:
            out["mismatches"].append("verdict")
        # placebo: random survivor labels (uniform over the non-banned) -> directional verdicts at ~nominal rate
        rng = np.random.default_rng(7)
        vs = []
        for _ in range(200):
            fake = list(rng.choice(nonb, size=len(surv)))
            vs.append(verdict(nulls(g, fake, {a: bc.get(a, 0) for a in nonb}, rates, draws=2000,
                                    seed=int(rng.integers(1e9))), cls, fake))
        out["placebo_verdicts"] = dict(collections.Counter(vs))
    # selection placebo: shuffle adj_label across rows within each configuration
    rng = np.random.default_rng(11)
    same = 0
    for _ in range(200):
        sh = {}
        for cid, rows in rows_by.items():
            labs = [r.get("adj_label") for r in rows]
            rng.shuffle(labs)
            fake = [dict(r, adj_label=l) for r, l in zip(rows, labs)]
            sh[cid] = sum(is_cs(r, c2["banned_sets"][cid]) for r in fake) / len(rows)
        qq = sorted(c for c, s in sh.items() if s >= 0.20)
        same += qq == out["Q"]
    out["selection_placebo_same_Q_rate"] = same / 200
    # commitments chain and commit-before-first-row
    lines = (ROOT / "commitments.log").read_text().splitlines()
    prev = "0" * 64
    chain_ok = True
    times = {}
    for ln in lines:
        e = json.loads(ln)
        chain_ok &= e["prev_line_sha256"] == prev
        chain_ok &= hashlib.sha256((ROOT / e["payload_path"]).read_bytes()).hexdigest() == e["payload_sha256"]
        prev = hashlib.sha256(ln.encode()).hexdigest()
        times[e["label"]] = e["utc"]
    out["chain_ok"] = chain_ok
    first = {}
    for p in sorted(D.glob("raw_*_*.jsonl")):
        arm = p.stem.split("_")[-1]
        ts = [r.get("utc") for r in rl(p) if r.get("utc")]
        if ts:
            first[p.stem] = min(ts)
    order_ok = {}
    for name, t in first.items():
        arm = name.split("_")[-1]
        need = {"baseline": "commit1", "ban": "commit2", "confirm": "commit4"}.get(arm)
        if need:
            order_ok[name] = need in times and times[need] < t
    out["commit_precedes_rows"] = order_ok
    if not all(order_ok.values()) or not chain_ok:
        out["mismatches"].append("commit order/chain")
    out["n_mismatches"] = len(out["mismatches"])
    (R / "rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("n_mismatches", "mismatches", "Q", "L_star", "chain_ok")}, default=float))


if __name__ == "__main__":
    main()
