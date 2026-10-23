#!/usr/bin/env python3
"""Second independent re-derivation (stdlib + numpy only; nothing imported from src/; own geodesics = Floyd-Warshall on
the symmetrised kNN graph, own placement rule, own rank statistics). Reads the raw state arrays and data/frames.json
and recomputes the headline numbers NOT covered by audit/rederive.py, then compares with results/*.json:
  leave-one-program-out nearest-cell accuracy (cell / discipline / container) and the surface-vs-mechanism error split,
  PROBE nearest-cell landing on F1, Delta for UD-LEV and BF-RLX on F1, covert share with a banned-discipline nearest cell,
  rho_d of the AST node-type 4-gram baseline.
Placebos that must FAIL: shuffled cell labels (LOO accuracy -> chance, surface-error excess -> none), Gaussian states with
matched norms (Delta / PROBE / covert structure disappears). Writes audit/rederive2.json."""

import ast
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
E46_STATES = Path(os.environ.get("TPG2_E46_STATES", str(ROOT / "cache" / "e46_states")))
L = {"8b": 17, "32b": 33}
K = 15
BANNED = {"LEV", "DFS", "HEU"}


def dc(cell):
    return tuple(cell.split("_"))


def geo_fw(X, k=K):
    n = len(X)
    D = np.stack([np.sqrt(((X - X[i]) ** 2).sum(1)) for i in range(n)])
    D[D == 0] = 1e-12
    np.fill_diagonal(D, 0.0)
    W = np.full((n, n), np.inf)
    np.fill_diagonal(W, 0.0)
    for i in range(n):
        nb = [j for j in np.argsort(D[i]) if j != i][:k]
        W[i, nb] = np.minimum(W[i, nb], D[i, nb])
        W[nb, i] = np.minimum(W[nb, i], D[i, nb])
    for m in range(n):
        W = np.minimum(W, W[:, m:m + 1] + W[m:m + 1, :])
    if not np.isfinite(W).all():
        raise RuntimeError("disconnected graph (the frozen code would join components)")
    return W


def place(x, F, geo, k=K):
    d = np.sqrt(((F - x) ** 2).sum(1))
    nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)


def rank(v):
    o = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    vs = np.asarray(v)[o]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and vs[j + 1] == vs[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pcor(y, x, c):
    A = np.column_stack([np.ones(len(y)), rank(c)])
    ry, rx = rank(y), rank(x)
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    return float((ey * ex).sum() / np.sqrt((ey ** 2).sum() * (ex ** 2).sum()))


def load(tag):
    fr = json.loads((ROOT / "data/frames.json").read_text())
    items = {it["id"]: it for it in json.loads((ROOT / "data/state_items.json").read_text())["items"]}
    z = np.load(ROOT / f"cache/states/tpg2_{tag}.npz")
    pos = {str(u): i for i, u in enumerate(z["ids"])}
    bi = [int(b) for b in z["blocks"]].index(L[tag])
    ze = np.load(E46_STATES / f"mcode_{tag}.npz")
    ek = {str(k): i for i, k in enumerate(ze["keys"])}
    ebi = [int(b) for b in ze["blocks"]].index(L[tag])
    xn = lambda u: z["R"][pos[u], 0, bi].astype(np.float64)  # noqa: E731
    xe = lambda k: ze["R"][ek[k], 0, ebi].astype(np.float64)  # noqa: E731
    return fr, items, xn, xe


def audit(tag, gaussian=False, shuffle=False):
    fr, items, xn, xe = load(tag)
    cells = [c["cell"] for c in fr["g1_cells"]]
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    X = np.stack([xn(f["id"]) for f in fact])
    lab = [f["cell"] for f in fact]
    rng = np.random.default_rng(7)
    if gaussian:
        G = rng.normal(size=X.shape)
        X = G * (np.linalg.norm(X, axis=1) / np.linalg.norm(G, axis=1))[:, None]
    if shuffle:
        lab = list(np.array(lab)[rng.permutation(len(lab))])
    lab = np.array(lab)
    # (1) leave-one-program-out nearest cell
    pred = []
    for i in range(len(X)):
        keep = np.arange(len(X)) != i
        g = geo_fw(X[keep])
        dv = place(X[i], X[keep], g)
        lk = lab[keep]
        m = {c: dv[lk == c].mean() for c in cells}
        pred.append(min(m, key=m.get))
    pred = np.array(pred)
    out = {"loo_cell": float(np.mean(pred == lab)),
           "loo_disc": float(np.mean([dc(a)[0] == dc(b)[0] for a, b in zip(pred, lab)])),
           "loo_cont": float(np.mean([dc(a)[1] == dc(b)[1] for a, b in zip(pred, lab)]))}
    err = [(t, p) for t, p in zip(lab, pred) if t != p]
    sc = sum(dc(p)[1] == dc(t)[1] for t, p in err)
    sd = sum(dc(p)[0] == dc(t)[0] and dc(p)[1] != dc(t)[1] for t, p in err)
    ch = np.mean([sum(dc(c)[1] == dc(t)[1] for c in cells if c != t) / (len(cells) - 1) for t, _ in err]) if err else 0
    out.update({"errors": len(err), "same_container_errors": int(sc), "same_discipline_errors": int(sd),
                "chance_same_container": float(ch), "excess_same_container": float(sc / max(1, len(err)) - ch)})
    if shuffle:
        return out
    # (2) F0 + F1 frames, PROBE landing, Delta, covert
    cls = set(fr["f0_classes"])
    prim = [p for p in fr["primary"] if p["algorithm"] in cls]
    tops = [t for t in fr["topups"] if t["algorithm"] in cls]
    F0 = np.stack([xe(p["e46_key"]) for p in prim] + [xn(t["id"]) for t in tops])
    if gaussian:
        G0 = rng.normal(size=F0.shape)
        F0 = G0 * (np.linalg.norm(F0, axis=1) / np.linalg.norm(G0, axis=1))[:, None]
    F1 = np.concatenate([F0, X])
    cell1 = np.array(["__f0__"] * len(F0) + list(lab))
    g1 = geo_fw(F1)

    def placed(uid):
        x = xn(uid)
        if gaussian:
            gx = rng.normal(size=x.shape)
            x = gx * np.linalg.norm(x) / np.linalg.norm(gx)
        return place(x, F1, g1)

    probe = [f for f in fr["factorial"] if f["cell"] == "PROBE"]
    pc = Counter()
    for f in probe:
        dv = placed(f["id"])
        m = {c: dv[cell1 == c].mean() for c in cells}
        pc[min(m, key=m.get)] += 1
    out["probe_nearest_cell"] = dict(pc)
    for fam in ("UD-LEV", "BF-RLX"):
        S = [s for s in fr["survivors"] if s["family_split"] == fam]
        d_f, c_f = S[0]["disc"], S[0]["cont"]
        own = f"{d_f}_{c_f}"
        same_c = [c for c in cells if dc(c)[1] == c_f and dc(c)[0] != d_f and c != own]
        same_d = [c for c in cells if dc(c)[0] == d_f and dc(c)[1] != c_f and c != own]
        vals = []
        for s in S:
            dv = placed(s["id"])
            a = np.mean([dv[cell1 == c].mean() for c in same_c])
            b = np.mean([dv[cell1 == c].mean() for c in same_d])
            vals.append(a - b)
        out[f"Delta_{fam}"] = float(np.mean(vals))
    nb = 0
    for c in fr["covert"]:
        dv = placed(c["id"])
        m = {cc: dv[cell1 == cc].mean() for cc in cells}
        nb += int(dc(min(m, key=m.get))[0] in BANNED)
    out["covert_share_banned_disc_F1"] = nb / len(fr["covert"])
    # (3) AST node-type 4-gram baseline rho_d (own feature builder; min_df 2; L2 rows)
    if not gaussian:
        grams = []
        for f in fact:
            seq = [type(n).__name__ for n in ast.walk(ast.parse(items[f["id"]]["scrubbed"]))]
            grams.append(Counter("_".join(seq[i:i + 4]) for i in range(len(seq) - 3)))
        df = Counter(g for c in grams for g in c)
        vocab = sorted(g for g, n in df.items() if n >= 2)
        vi = {g: i for i, g in enumerate(vocab)}
        A = np.zeros((len(fact), len(vocab)))
        for r, c in enumerate(grams):
            for g, n in c.items():
                if g in vi:
                    A[r, vi[g]] = n
        A /= np.linalg.norm(A, axis=1, keepdims=True)
        ga = geo_fw(A)
        M = np.zeros((len(cells), len(cells)))
        for i, a in enumerate(cells):
            for j, b in enumerate(cells):
                s = ga[np.ix_(lab == a, lab == b)]
                if i == j:
                    s = s[~np.eye(len(s), dtype=bool)]
                M[i, j] = s.mean()
        iu = np.triu_indices(len(cells), 1)
        Dd = np.array([[float(dc(a)[0] != dc(b)[0]) for b in cells] for a in cells])[iu]
        Dc = np.array([[float(dc(a)[1] != dc(b)[1]) for b in cells] for a in cells])[iu]
        out["astngram_rho_d"] = pcor(M[iu], Dd, Dc)
    return out


def reference(tag):
    t5 = json.loads((ROOT / "results/t5_placement.json").read_text())["loo_nearest_cell_accuracy"][tag]
    g2 = json.loads((ROOT / f"results/g2_{tag}.json").read_text())["k15"]
    g1 = json.loads((ROOT / f"results/g1_{tag}.json").read_text())
    cf = json.loads((ROOT / "results/explore_confusion.json").read_text())[f"predict_nearest_cell_{tag}"]
    return {"loo_cell": t5["cell"], "loo_disc": t5["discipline"], "loo_cont": t5["container"],
            "same_container_errors": cf["same_container_other_discipline"],
            "same_discipline_errors": cf["same_discipline_other_container"], "errors": cf["errors"],
            "probe_nearest_cell": g2["probe"]["nearest_cell_counts"],
            "Delta_UD-LEV": g2["families"]["UD-LEV"]["Delta"]["value"], "Delta_BF-RLX": g2["families"]["BF-RLX"]["Delta"]["value"],
            "covert_share_banned_disc_F1": g2["covert"]["share_nearest_banned_disc_F1"],
            "astngram_rho_d": g1["point_astngram"]["rho_d"]}


if __name__ == "__main__":
    res = {}
    for tag in sys.argv[1:] or ["8b", "32b"]:
        mine, ref = audit(tag), reference(tag)
        cmp = {}
        for k, v in ref.items():
            m = mine.get(k)
            cmp[k] = {"rederived": m, "reported": v,
                      "match": (m == v) if isinstance(v, (dict, int)) else (m is not None and abs(m - v) < 1e-9)}
        res[tag] = {"comparison": cmp, "n_mismatch": sum(not c["match"] for c in cmp.values()),
                    "placebo_shuffled_labels": audit(tag, shuffle=True),
                    "placebo_gaussian_states": audit(tag, gaussian=True)}
        print(tag, "mismatches:", res[tag]["n_mismatch"], {k: c["match"] for k, c in cmp.items()})
        print("  shuffled:", {k: round(v, 3) if isinstance(v, float) else v for k, v in res[tag]["placebo_shuffled_labels"].items()})
        print("  gaussian:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[tag]["placebo_gaussian_states"].items()})
    res["n_mismatches"] = sum(v["n_mismatch"] for v in res.values() if isinstance(v, dict))
    (ROOT / "audit" / "rederive2.json").write_text(json.dumps(res, indent=1, default=float))
    print("total mismatches:", res["n_mismatches"])
