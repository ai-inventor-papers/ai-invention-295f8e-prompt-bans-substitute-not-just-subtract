#!/usr/bin/env python3
"""Independent re-derivation (standard library only; no project code, no numpy/scipy).

Reads the JSON exports (results/geometry_all.json class geodesic matrices, results/lexical_regression.json alias
rows, results/lexical.json, inputs/e44/results/landing.json null inputs) and recomputes, by its own code:
  * g(a) = min over banned b of the class-matrix entry M[a][b], the EDGE/MIDDLE/OPPOSITE classes, rank of unit Dijkstra
  * the landing verdict with the EXACT uniform null (convolution over the 15 survivor draws) and the F null
  * Spearman of g_alias against L1 (own ranking with ties averaged)
Placebos that must fail: random survivor labels (verdict NEITHER in about 90-95% of draws), permuted L1 (rho near 0),
shuffled algorithm labels on the M-name class matrix (unit Dijkstra keeps OPPOSITE only at chance).
Writes results/rederive.json.
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
CANON = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]
UD = "dijkstra_unit"


def load(p):
    return json.loads(Path(p).read_text())


def median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def classes(g):
    m = median(list(g.values()))
    return {a: ("EDGE" if x < m - 1e-12 else "OPPOSITE" if x > m + 1e-12 else "MIDDLE") for a, x in g.items()}, m


def g_from_matrix(M, present):
    g = {}
    for a in NB5:
        if a not in present:
            continue
        i = CANON.index(a)
        vals = [M[i][CANON.index(b)] for b in B5 if b in present and M[i][CANON.index(b)] == M[i][CANON.index(b)]]
        g[a] = min(vals)
    return g


def exact_null(g, probs, n):
    """Distribution of the mean of n iid draws (values g, probabilities probs): dict value -> probability."""
    algs = list(g)
    tot = sum(probs[a] for a in algs)
    dist = {0.0: 1.0}
    for _ in range(n):
        nd = {}
        for s, p in dist.items():
            for a in algs:
                key = round(s + g[a], 9)
                nd[key] = nd.get(key, 0.0) + p * probs[a] / tot
        dist = nd
    return {round(k / n, 9): v for k, v in dist.items()}


def landing_exact(g, cls, surv, fprobs):
    n = len(surv)
    S = sum(g[a] for a in surv) / n
    out = {"S": S}
    for nm, pr in (("U", {a: 1.0 for a in g}), ("F", fprobs)):
        d = exact_null(g, pr, n)
        out[nm] = {"p_edge": sum(p for v, p in d.items() if v <= S + 1e-9),
                   "p_opp": sum(p for v, p in d.items() if v >= S - 1e-9)}
    share_e = sum(cls[a] == "EDGE" for a in surv) / n
    share_o = sum(cls[a] == "OPPOSITE" for a in surv) / n
    if out["U"]["p_edge"] < 0.05 and out["F"]["p_edge"] < 0.05 and share_e > 0.5:
        v = "EDGE"
    elif out["U"]["p_opp"] < 0.05 and out["F"]["p_opp"] < 0.05 and share_o > 0.5:
        v = "OPPOSITE"
    else:
        v = "NEITHER"
    out["verdict"] = v
    return out


def ranks(x):
    idx = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[idx[j + 1]] == x[idx[i]]:
            j += 1
        for t in range(i, j + 1):
            r[idx[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def main():
    geo = load(R / "geometry_all.json")
    land_e44 = load(ROOT / "inputs" / "e44" / "results" / "landing.json")
    fprobs = land_e44["primary"]["null_F_probs"]
    surv = [UD] * 15
    out = {"manifolds": {}, "mismatches": []}
    for key, r in geo.items():
        if not r:
            continue
        d = r["L_star"]["describe"]
        rec = {}
        for k in ("k10", "k15"):
            M = d[k]["class_geodesic_matrix"]
            g = g_from_matrix(M, d["present"])
            cls, med = classes(g)
            rank = sorted(g, key=g.get).index(UD) + 1 if UD in g else None
            rec[k] = {"g": g, "classes": cls, "udij_rank": rank}
            if cls != d[k]["classes"]:
                out["mismatches"].append(f"{key} {k} classes {cls} vs {d[k]['classes']}")
            if max(abs(g[a] - d[k]["g"][a]) for a in g) > 1e-6:
                out["mismatches"].append(f"{key} {k} g differs")
            if rank != d[k]["udij_rank"]:
                out["mismatches"].append(f"{key} {k} rank {rank} vs {d[k]['udij_rank']}")
            if UD in g:
                fp = {a: fprobs.get(a, 0.5) for a in g}
                le = landing_exact(g, cls, surv, fp)
                rec[k]["landing_exact"] = le
                proj = r["L_star"]["landing"].get(k, {}).get("pooled", {}).get("verdict")
                if proj is not None and proj != le["verdict"]:
                    out["mismatches"].append(f"{key} {k} verdict {le['verdict']} vs {proj}")
        out["manifolds"][key] = rec
    lr = load(R / "lexical_regression.json")
    lexr = {}
    for key in ("32b|mname", "8b|mname", "32b|mlex", "8b|mlex"):
        if key not in lr or not lr[key]:
            continue
        lexr[key] = {}
        for k in ("k10", "k15"):
            rows = lr[key][k]["rows"]
            rho = spearman([x["g_alias"] for x in rows], [x["L1"] for x in rows])
            lexr[key][k] = rho
            if abs(rho - lr[key][k]["spearman_L1"]) > 1e-9:
                out["mismatches"].append(f"lexical {key} {k}: {rho} vs {lr[key][k]['spearman_L1']}")
    out["lexical_rho"] = lexr
    # placebos
    rnd = random.Random(0)
    plac = {}
    ref = out["manifolds"].get("32b|mname", {}).get("k15")
    if ref:
        g, cls = ref["g"], ref["classes"]
        fp = {a: fprobs.get(a, 0.5) for a in g}
        verdicts = []
        for _ in range(300):
            sv = [rnd.choice(list(g)) for _ in range(15)]
            verdicts.append(landing_exact(g, cls, sv, fp)["verdict"])
        plac["random_survivor_labels_share_NEITHER"] = verdicts.count("NEITHER") / len(verdicts)
        M = geo["32b|mname"]["L_star"]["describe"]["k15"]["class_geodesic_matrix"]
        same = 0
        for _ in range(500):
            perm = CANON[:]
            rnd.shuffle(perm)
            Mp = [[M[CANON.index(perm[i])][CANON.index(perm[j])] for j in range(10)] for i in range(10)]
            gp = g_from_matrix(Mp, CANON)
            cp, _ = classes(gp)
            same += cp[UD] == "OPPOSITE"
        plac["shuffled_labels_share_udij_OPPOSITE"] = same / 500
    if "32b|mname" in lr and lr["32b|mname"]:
        rows = lr["32b|mname"]["k15"]["rows"]
        gs = [x["g_alias"] for x in rows]
        L1 = [x["L1"] for x in rows]
        rhos = []
        for _ in range(2000):
            p = L1[:]
            rnd.shuffle(p)
            rhos.append(spearman(gs, p))
        plac["permuted_L1_mean_rho"] = sum(rhos) / len(rhos)
        obs = spearman(gs, L1)
        plac["permuted_L1_share_as_extreme_as_observed"] = sum(1 for x in rhos if x <= obs + 1e-12) / len(rhos)
    out["placebos"] = plac
    out["n_mismatches"] = len(out["mismatches"])
    (R / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"rederive: {len(out['mismatches'])} mismatches; placebos {plac}")
    return 0 if not out["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
