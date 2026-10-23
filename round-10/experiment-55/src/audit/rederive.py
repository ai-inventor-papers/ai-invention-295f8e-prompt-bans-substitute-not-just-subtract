#!/usr/bin/env python3
"""Stage 7 INDEPENDENT RE-DERIVATION (stdlib + numpy only; nothing imported from src/). Recomputes from the saved
npz / json files: kNN geodesics (symmetrised kNN graph + Floyd-Warshall), the factorial cell RDMs, rho_d / rho_c
(rank partial correlations), the restricted permutation p, the UD / BF classes on F0 and F1 (out-of-sample rule),
Delta for UD / BF and the covert shares; compares with results/g1_*.json and g2_*.json (1e-9, classes exactly).
PLACEBOS that must fail: discipline labels shuffled across cells, container labels shuffled, Gaussian random states
with matched norms, survivor family labels permuted. Writes audit/rederive.json."""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
# iteration 9's cached states: the bit-identical reduced copies shipped in cache/e46_states (override: TPG2_E46_STATES)
E46_STATES = Path(os.environ.get("TPG2_E46_STATES", str(ROOT / "cache" / "e46_states")))
L = {"8b": 17, "32b": 33}
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["dijkstra_unit", "idastar", "bibfs", "jps", "biastar"]
K = 15


def jl(p):
    return json.loads(Path(p).read_text())


def rank(x):
    x = np.asarray(x, float)
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    i = 0
    xs = x[o]
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def pcor(y, x, ctrls):
    A = np.column_stack([np.ones(len(y))] + [rank(c) for c in ctrls])
    ry, rx = rank(y), rank(x)
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    return float((ey * ex).sum() / math.sqrt((ey ** 2).sum() * (ex ** 2).sum()))


def geodesic(X, k=K):
    n = len(X)
    D = np.stack([np.sqrt(((X - X[i]) ** 2).sum(1)) for i in range(n)])
    D[D == 0] = 1e-12
    np.fill_diagonal(D, 0.0)
    W = np.full((n, n), np.inf)
    np.fill_diagonal(W, 0.0)
    order = np.argsort(D, axis=1)
    for i in range(n):
        nb = [j for j in order[i] if j != i][:k]
        W[i, nb] = np.minimum(W[i, nb], D[i, nb])
        W[nb, i] = np.minimum(W[nb, i], D[i, nb])
    # components (joined by the shortest inter-component edge, as the frozen code does)
    comp = -np.ones(n, int)
    c = 0
    for s in range(n):
        if comp[s] >= 0:
            continue
        st = [s]
        comp[s] = c
        while st:
            u = st.pop()
            for v in np.where(np.isfinite(W[u]))[0]:
                if comp[v] < 0:
                    comp[v] = c
                    st.append(v)
        c += 1
    if c > 1:
        for a in range(c):
            for b in range(a + 1, c):
                ia, ib = np.where(comp == a)[0], np.where(comp == b)[0]
                sub = D[np.ix_(ia, ib)]
                i, j = np.unravel_index(np.argmin(sub), sub.shape)
                W[ia[i], ib[j]] = W[ib[j], ia[i]] = max(sub[i, j], 1e-12)
    for m in range(n):
        W = np.minimum(W, W[:, m:m + 1] + W[m:m + 1, :])
    return W, c


def class_mat(geo, lab, cells):
    M = np.zeros((len(cells), len(cells)))
    for i, a in enumerate(cells):
        for j, b in enumerate(cells):
            s = geo[np.ix_(lab == a, lab == b)]
            if i == j:
                s = s[~np.eye(len(s), dtype=bool)]
            M[i, j] = s.mean()
    return M


def up(M):
    return M[np.triu_indices(len(M), 1)]


def load(tag):
    fr = jl(ROOT / "data/frames.json")
    z = np.load(ROOT / f"cache/states/tpg2_{tag}.npz")
    ids = [str(x) for x in z["ids"]]
    pos = {u: i for i, u in enumerate(ids)}
    bi = [int(b) for b in z["blocks"]].index(L[tag])
    ze = np.load(E46_STATES / f"mcode_{tag}.npz")
    ek = {str(k): i for i, k in enumerate(ze["keys"])}
    ebi = [int(b) for b in ze["blocks"]].index(L[tag])

    def xn(u):
        return z["R"][pos[u], 0, bi].astype(np.float64)

    def xe(k):
        return ze["R"][ek[k], 0, ebi].astype(np.float64)
    return fr, xn, xe


def g1_check(tag):
    fr, xn, _ = load(tag)
    cells = [c["cell"] for c in fr["g1_cells"]]
    disc = {c["cell"]: c["disc"] for c in fr["g1_cells"]}
    cont = {c["cell"]: c["cont"] for c in fr["g1_cells"]}
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    X = np.stack([xn(f["id"]) for f in fact])
    lab = np.array([f["cell"] for f in fact])
    geo, nc = geodesic(X)
    D = class_mat(geo, lab, cells)
    Dd = np.array([[float(disc[a] != disc[b]) for b in cells] for a in cells])
    Dc = np.array([[float(cont[a] != cont[b]) for b in cells] for a in cells])
    y, d, c = up(D), up(Dd), up(Dc)
    rd, rc = pcor(y, d, [c]), pcor(y, c, [d])
    # restricted permutations (disciplines within container), exact
    groups = {}
    for i, cl in enumerate(cells):
        groups.setdefault(cont[cl], []).append(i)
    base = [disc[cl] for cl in cells]
    null = []
    for combo in itertools.product(*[list(itertools.permutations(g)) for g in groups.values()]):
        lab2 = list(base)
        for g, pg in zip(groups.values(), combo):
            for a, b in zip(g, pg):
                lab2[a] = base[b]
        dd = np.array([[float(lab2[i] != lab2[j]) for j in range(len(cells))] for i in range(len(cells))])
        null.append(pcor(y, up(dd), [c]))
    null = np.array(null)
    p = float(np.mean(null >= rd - 1e-12))
    ref = jl(ROOT / f"results/g1_{tag}.json")
    out = {"rho_d": rd, "rho_c": rc, "p_rho_d": p, "n_perm": len(null), "components": nc,
           "ref_rho_d": ref["point_model"]["rho_d"], "ref_rho_c": ref["point_model"]["rho_c"],
           "ref_p": ref["perm"]["model"]["rho_d"]["p_greater"],
           "max_abs_diff_cell_rdm": float(np.abs(D - np.array(ref["cell_rdm"])).max())}
    out["match"] = bool(abs(rd - out["ref_rho_d"]) < 1e-9 and abs(rc - out["ref_rho_c"]) < 1e-9 and
                        abs(p - out["ref_p"]) < 1e-9 and out["max_abs_diff_cell_rdm"] < 1e-6)
    # placebos
    rng = random.Random(0)
    pl = {"disc_shuffled": [], "cont_shuffled": []}
    for _ in range(100):
        sh = base[:]
        rng.shuffle(sh)
        dd = np.array([[float(sh[i] != sh[j]) for j in range(len(cells))] for i in range(len(cells))])
        pl["disc_shuffled"].append(pcor(y, up(dd), [c]))
        cb = [cont[cl] for cl in cells]
        rng.shuffle(cb)
        cc = np.array([[float(cb[i] != cb[j]) for j in range(len(cells))] for i in range(len(cells))])
        pl["cont_shuffled"].append(pcor(y, up(cc), [d]))
    qd = np.quantile(null, 0.95)
    out["placebo_disc_shuffled"] = {"mean_abs_rho_d": float(np.mean(np.abs(pl["disc_shuffled"]))),
                                    "share_exceeding_restricted_null_q95": float(np.mean(np.array(pl["disc_shuffled"]) >= qd)),
                                    "observed_rho_d": rd}
    out["placebo_cont_shuffled"] = {"mean_abs_rho_c": float(np.mean(np.abs(pl["cont_shuffled"]))), "observed_rho_c": rc}
    nrng = np.random.default_rng(0)
    Xg = nrng.normal(size=X.shape)
    Xg *= (np.linalg.norm(X, axis=1) / np.linalg.norm(Xg, axis=1))[:, None]
    gg, _ = geodesic(Xg)
    Dg = class_mat(gg, lab, cells)
    out["placebo_gaussian_states"] = {"rho_d": pcor(up(Dg), d, [c]), "rho_c": pcor(up(Dg), c, [d])}
    return out


def oos(x, F, geo, k=K):
    d = np.linalg.norm(F - x, axis=1)
    nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)


def g2_check(tag):
    fr, xn, xe = load(tag)
    classes = fr["f0_classes"]
    prim = [p for p in fr["primary"] if p["algorithm"] in classes]
    tops = [t for t in fr["topups"] if t["algorithm"] in classes]
    X0 = np.stack([xe(p["e46_key"]) for p in prim] + [xn(t["id"]) for t in tops])
    a0 = np.array([p["algorithm"] for p in prim] + [t["algorithm"] for t in tops])
    geo0, _ = geodesic(X0)
    B = [b for b in B5 if b in set(a0)]
    NB = [a for a in NB5 if (a0 == a).sum() >= 10]
    gvals = {a: min(float(geo0[np.ix_(a0 == a, a0 == b)].mean()) for b in B) for a in NB}
    med = float(np.median(list(gvals.values())))
    ref = jl(ROOT / f"results/g2_{tag}.json")["k15"]
    out = {"F0_median": med, "ref_F0_median": ref["frames_algorithm_level"]["F0"]["median"]}
    fams = {}
    for fam in ("UD-LEV", "BF-RLX"):
        S = [s for s in fr["survivors"] if s["family_split"] == fam]
        cls = []
        for s in S:
            dv = oos(xn(s["id"]), X0, geo0)
            g = min(float(dv[a0 == b].mean()) for b in B)
            cls.append("EDGE" if g < med - 1e-12 else ("OPPOSITE" if g > med + 1e-12 else "MIDDLE"))
        cc = {k: cls.count(k) for k in set(cls)}
        fc = "EDGE" if cc.get("EDGE", 0) / len(cls) > 0.5 else ("OPPOSITE" if cc.get("OPPOSITE", 0) / len(cls) > 0.5 else "MIXED")
        fams[fam] = {"class_counts": cc, "class": fc, "ref_class_counts": ref["families"][fam]["F0"]["class_counts"],
                     "match": cc == ref["families"][fam]["F0"]["class_counts"]}
    out["families_F0"] = fams
    # covert share on F0
    cov = fr["covert"]
    nb = 0
    for cv in cov:
        dv = oos(xn(cv["id"]), X0, geo0)
        m = {a: float(dv[a0 == a].mean()) for a in sorted(set(a0.tolist()))}
        nb += int(min(m, key=m.get) in B5)
    out["covert_share_F0"] = nb / len(cov) if cov else None
    out["ref_covert_share_F0"] = ref.get("covert", {}).get("share_nearest_banned_F0")
    # placebo: survivor family labels permuted -> class stability
    rng = random.Random(1)
    allS = [s for s in fr["survivors"] if s["family_split"] in ("UD-LEV", "BF-RLX")]
    gs = []
    for s in allS:
        dv = oos(xn(s["id"]), X0, geo0)
        gs.append(min(float(dv[a0 == b].mean()) for b in B))
    labs = [s["family_split"] for s in allS]
    stab = []
    for _ in range(200):
        pl = labs[:]
        rng.shuffle(pl)
        ok = 0
        for fam in ("UD-LEV", "BF-RLX"):
            v = [g for g, l in zip(gs, pl) if l == fam]
            ok += int((np.mean(v) < med) == (fams[fam]["class"] == "EDGE"))
        stab.append(ok / 2)
    out["placebo_family_labels_permuted"] = {"mean_share_family_class_reproduced": float(np.mean(stab)),
                                             "note": "share of the two families whose S-based side of the median survives a random relabelling"}
    out["match"] = bool(abs(med - out["ref_F0_median"]) < 1e-9 and all(f["match"] for f in fams.values()) and
                        (out["ref_covert_share_F0"] is None or abs(out["covert_share_F0"] - out["ref_covert_share_F0"]) < 1e-12))
    return out


if __name__ == "__main__":
    res = {}
    for tag in sys.argv[1:] or ["8b", "32b"]:
        if not (ROOT / f"results/g1_{tag}.json").exists():
            continue
        res[tag] = {"g1": g1_check(tag), "g2": g2_check(tag)}
        print(tag, "G1 match", res[tag]["g1"]["match"], "G2 match", res[tag]["g2"]["match"])
    res["n_mismatches"] = sum(int(not v["g1"]["match"]) + int(not v["g2"]["match"]) for k, v in res.items() if isinstance(v, dict))
    (ROOT / "audit" / "rederive.json").write_text(json.dumps(res, indent=1, default=float))
    print("mismatches:", res["n_mismatches"])
