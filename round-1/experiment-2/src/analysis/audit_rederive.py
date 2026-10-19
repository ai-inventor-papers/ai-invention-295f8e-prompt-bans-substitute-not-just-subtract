#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (audit).

Reads the RAW files (data/samples_*.jsonl, cache/hR_*.npy, predictions/predictions_v1.json, labeller/gold_set.json)
and recomputes each headline number through a different code path than analysis/analyze.py / hf/phase_b.py
(no imports from the pipeline modules; networkx instead of scipy.csgraph, eigendecomposition PCA instead of SVD,
sklearn's cohen_kappa_score and NearestNeighbors), then compares with the reported values. Placebo / shuffled-input
versions of the comparisons that act as tests must FAIL. Writes results/audit_rederive.json.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(99)


def rows(name):
    return [json.loads(l) for l in (ROOT / "data" / name).read_text().splitlines() if l.strip()]


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def main() -> None:
    out = {"checks": []}

    def check(name, derived, reported, tol=1e-6, note=""):
        ok = close(float(derived), float(reported), tol) if reported is not None else None
        out["checks"].append({"name": name, "derived": derived, "reported": reported, "match": ok, "note": note})
        print(f"{'OK ' if ok else ('-- ' if ok is None else 'BAD')} {name}: derived={derived} reported={reported} {note}")

    A, C, D = rows("samples_phaseA.jsonl"), rows("samples_phaseC.jsonl"), rows("samples_phaseD.jsonl")
    summ = json.loads((ROOT / "results" / "summaries.json").read_text())
    # ---------------------------------------------------------------- behaviour (raw counts)
    for t, m in (("t1", "bfs"), ("t2", "dijkstra")):
        b = [r for r in A if r["task"] == t and r["condition"] == "baseline"]
        check(f"{t} baseline modal count ({m})", sum(r["label"] == m for r in b), summ[t]["baseline"]["label_counts"].get(m))
        check(f"{t} baseline n", len(b), summ[t]["baseline"]["n"])
        check(f"{t} baseline pass rate", sum(bool(r["passed"]) for r in b) / len(b), summ[t]["baseline"]["pass_rate"], 1e-9)
        ban = [r for r in C if r["task"] == t and r["condition"] == f"ban:{m}"]
        comp = sum(bool(r["passed"]) and r["label"] not in (m, "no_code") for r in ban)
        check(f"{t} ban:{m} compliance", comp / len(ban), summ[t][f"ban:{m}"]["compliance"], 1e-9, f"({comp}/{len(ban)})")
        check(f"{t} ban:{m} still-{m} count", sum(r["label"] == m for r in ban), summ[t][f"ban:{m}"]["label_counts"].get(m))
        # Hill number of correct labels, computed with an explicit formula
        cc = Counter(r["label"] for r in ban if r["passed"])
        n = sum(cc.values())
        H = -sum(c / n * math.log(c / n) for c in cc.values())
        check(f"{t} ban:{m} hill_cc", math.exp(H), summ[t][f"ban:{m}"]["hill_cc"], 1e-9)
    # removal: pre-declared arms move nothing; byte-identical outputs vs alpha=0 under CRN
    c2 = json.loads((ROOT / "results" / "c2_removal.json").read_text())
    for t, m in (("t1", "bfs"), ("t2", "dijkstra")):
        a0 = {r["sample_id"]: r for r in D if r["task"] == t and r["arm"] == "hooked_alpha0"}
        for arm in sorted({r["arm"] for r in D if r["task"] == t}):
            ra = [r for r in D if r["task"] == t and r["arm"] == arm]
            moved = sum(r["label"] not in (m, "no_code") for r in ra) / len(ra)
            check(f"{t} {arm} moved_frac", moved, c2[t]["arms"][arm]["moved_frac"], 1e-9)
            same = np.mean([r["raw_text"] == a0[r["sample_id"]]["raw_text"] for r in ra])
            check(f"{t} {arm} identical-text vs alpha0", float(same), c2[t]["arms"][arm]["identical_text_vs_alpha0_frac"], 1e-9)
    # ---------------------------------------------------------------- contest log scores (fresh implementation)
    preds = json.loads((ROOT / "predictions" / "predictions_v1.json").read_text())
    contest = json.loads((ROOT / "results" / "contest.json").read_text())
    for eid, e in contest["events"].items():
        ev = preds["events"][eid]
        S = ev["survivors"]
        cond = "ban:" + "+".join(ev["banset"])
        rr = [r for r in C if r["task"] == ev["task"] and r["condition"] == cond]
        for p in ("association", "frequency", "geodesic", "decoder"):
            dist = ev["distributions"][p]
            vals = []
            for r in rr:
                if r["label"] in S:
                    vals.append(math.log(0.98 * (0.95 * dist[r["label"]] + 0.05 / len(S))))
                elif r["label"] == "other":
                    vals.append(math.log(0.02))
            check(f"{eid} {p} mean log score", float(np.mean(vals)), e["predictors"][p]["log_score_mean"], 1e-9)
    # ---------------------------------------------------------------- geometry: geodesic distances with networkx
    index = [json.loads(l) for l in (ROOT / "cache" / "hR_index.jsonl").read_text().splitlines() if l.strip()]
    geo_b = json.loads((ROOT / "results" / "geometry_b.json").read_text())
    cats = {"t1": ["bfs", "dfs", "bidir_bfs", "iddfs", "astar", "dijkstra_unit"],
            "t2": ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]}

    def geodesics(X, labels, cat, k=10):
        mu = X.mean(0)
        Xc = X - mu
        w, V = np.linalg.eigh(Xc.T @ Xc if Xc.shape[1] <= Xc.shape[0] else Xc @ Xc.T)
        # dual trick for n << d: eigenvectors of the Gram matrix map to principal axes
        order = np.argsort(w)[::-1]
        w, V = w[order], V[:, order]
        ev = w / w.sum()
        kk = int(np.searchsorted(np.cumsum(ev), 0.95) + 1)
        kk = max(2, min(kk, 50))
        axes = (Xc.T @ V[:, :kk]) / np.sqrt(np.maximum(w[:kk], 1e-12))
        P = Xc @ axes
        C = np.stack([X[[i for i, l in enumerate(labels) if l == m]].mean(0) for m in cat])
        Cp = (C - mu) @ axes
        G = nx.Graph()
        nn = NearestNeighbors(n_neighbors=k + 1).fit(P)
        dist, idx = nn.kneighbors(P)
        for i in range(len(P)):
            for d, j in zip(dist[i, 1:], idx[i, 1:]):
                G.add_edge(i, int(j), weight=float(d))
        nnc = NearestNeighbors(n_neighbors=k).fit(P)
        dc, ic = nnc.kneighbors(Cp)
        for a in range(len(cat)):
            for d, j in zip(dc[a], ic[a]):
                G.add_edge(("c", a), int(j), weight=float(d))
        D = np.zeros((len(cat), len(cat)))
        for a in range(len(cat)):
            sp = nx.single_source_dijkstra_path_length(G, ("c", a), weight="weight")
            for b in range(len(cat)):
                D[a, b] = sp[("c", b)]
        return D, kk

    for t, l in (("t1", 27), ("t2", 24)):
        H = np.load(ROOT / "cache" / f"hR_layer{l}.npy").astype(np.float64)
        sel = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("forced:")]
        labels = [index[i]["condition"].split(":")[1] for i in sel]
        X = H[sel]
        D, kk = geodesics(X, labels, cats[t])
        rep = np.array(geo_b[t]["centroid_geodesic"])
        for b in range(1, len(cats[t])):
            check(f"{t} geodesic {cats[t][0]}->{cats[t][b]} (L{l})", round(float(D[0, b]), 3), round(float(rep[0, b]), 3), 0.05)
        check(f"{t} PCA dims for 95% variance", kk, geo_b[t]["pca_dims"])
        # placebo: shuffle the mode labels of the points -> centroid geodesics collapse towards each other
        Dp, _ = geodesics(X, list(RNG.permutation(labels)), cats[t])
        off = D[np.triu_indices(len(cats[t]), 1)]
        offp = Dp[np.triu_indices(len(cats[t]), 1)]
        out["checks"].append({"name": f"{t} placebo (shuffled mode labels) mean centroid geodesic", "derived": float(offp.mean()),
                              "reported_real": float(off.mean()), "placebo_much_smaller": bool(offp.mean() < 0.5 * off.mean())})
        print(f"PLACEBO {t}: real mean centroid geodesic {off.mean():.1f} vs shuffled-label {offp.mean():.1f}")
        # ------------------------------------------------------------ probe transfer accuracy (named -> masked) + placebo
        selm = [i for i, r in enumerate(index) if r["task"] == t and r["condition"].startswith("masked:")]
        ym = np.array([cats[t].index(index[i]["condition"].split(":")[1]) for i in selm])
        yn = np.array([cats[t].index(m) for m in labels])
        Xm = H[selm]
        mu = X.mean(0)
        U, S, Vt = np.linalg.svd(X - mu, full_matrices=False)
        nc = min(50, len(X) - 12)
        Zn, Zm = (X - mu) @ Vt[:nc].T, (Xm - mu) @ Vt[:nc].T
        acc = float((LogisticRegression(C=1.0, max_iter=5000).fit(Zn, yn).predict(Zm) == ym).mean())
        gate = json.loads((ROOT / "results" / "gate.json").read_text())
        rep_acc = next(p["transfer_acc"] for p in gate[t]["per_layer"] if p["layer"] == l)
        null95 = next(p["null_transfer_p95"] for p in gate[t]["per_layer"] if p["layer"] == l)
        check(f"{t} named->masked transfer accuracy (L{l})", round(acc, 4), round(rep_acc, 4), 0.034,
              "(tolerance = one masked sample; randomized-PCA vs exact-SVD solver)")
        plac = [float((LogisticRegression(C=1.0, max_iter=5000).fit(Zn, RNG.permutation(yn)).predict(Zm) == ym).mean())
                for _ in range(10)]
        passes_real = acc >= null95 + 0.20
        passes_plac = float(np.mean(plac)) >= null95 + 0.20
        out["checks"].append({"name": f"{t} transfer test on shuffled labels (placebo)", "placebo_mean_acc": float(np.mean(plac)),
                              "chance": 1 / len(cats[t]), "real_passes_test": bool(passes_real),
                              "placebo_passes_test": bool(passes_plac)})
        print(f"PLACEBO {t}: transfer real {acc:.3f} (passes test {passes_real}); shuffled-label mean {np.mean(plac):.3f} "
              f"(passes test {passes_plac}; chance {1 / len(cats[t]):.2f})")
        # ------------------------------------------------------------ TwoNN intrinsic dimension + placebo
        P = (X - mu) @ Vt[:geo_b[t]["pca_dims"]].T
        d2, _ = NearestNeighbors(n_neighbors=3).fit(P).kneighbors(P)
        mu_r = d2[:, 2] / d2[:, 1]
        mu_r = mu_r[np.isfinite(mu_r) & (mu_r > 1)]
        idim = len(mu_r) / np.sum(np.log(mu_r))
        man = json.loads((ROOT / "results" / "manifold.json").read_text())
        check(f"{t} TwoNN intrinsic dimension", round(float(idim), 3), round(man[t]["twonn_id"], 3), 0.05)
        Ps = P.copy()
        for c in range(Ps.shape[1]):
            Ps[:, c] = RNG.permutation(Ps[:, c])
        d2s, _ = NearestNeighbors(n_neighbors=3).fit(Ps).kneighbors(Ps)
        ms = d2s[:, 2] / d2s[:, 1]
        ms = ms[np.isfinite(ms) & (ms > 1)]
        out["checks"].append({"name": f"{t} TwoNN on column-shuffled placebo", "placebo_id": float(len(ms) / np.sum(np.log(ms))),
                              "real_id": float(idim)})
        print(f"PLACEBO {t}: TwoNN real {idim:.2f} vs column-shuffled {len(ms) / np.sum(np.log(ms)):.2f}")
    # ---------------------------------------------------------------- labeller gate kappa (sklearn)
    gold = json.loads((ROOT / "labeller" / "gold_set.json").read_text())
    lg = json.loads((ROOT / "results" / "labeller_gate.json").read_text())
    for t in ("t1", "t2"):
        g = [x for x in gold if x["task"] == t]
        k = cohen_kappa_score([str(x["rt"]) for x in g], [str(x["ast"]) for x in g])
        check(f"{t} kappa(runtime, AST) on gold set", round(float(k), 4), round(lg["gate"][t]["kappa_runtime_ast"], 4), 1e-3)
        agree = np.mean([x["rt"] == x["adjudicated"] for x in g])
        check(f"{t} runtime vs adjudicated", float(agree), lg["gate"][t]["runtime_vs_adjudicated"], 1e-9)
        shuf = [str(x["ast"]) for x in g]
        RNG.shuffle(shuf)
        kp = cohen_kappa_score([str(x["rt"]) for x in g], shuf)
        out["checks"].append({"name": f"{t} kappa placebo (AST labels shuffled)", "placebo_kappa": float(kp),
                              "passes_0.8_threshold": bool(kp >= 0.8)})
        print(f"PLACEBO {t}: kappa with shuffled AST labels {kp:.3f} (passes >=0.8: {kp >= 0.8})")
    n_bad = sum(1 for c in out["checks"] if c.get("match") is False)
    out["n_mismatches"] = n_bad
    (ROOT / "results" / "audit_rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"mismatches: {n_bad} of {sum(1 for c in out['checks'] if 'match' in c)} compared numbers")


if __name__ == "__main__":
    main()
