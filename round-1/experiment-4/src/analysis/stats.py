#!/usr/bin/env python3
"""Statistics: Wilson intervals, Hill numbers (plug-in and rarefied), TV / JS divergence, sample and
paraphrase-cluster bootstraps (paired when arms share paraphrases), flip rates, Fisher / Monte-Carlo
exact tests, and logistic dose-response with paraphrase-clustered standard errors.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def hill(labels, q: float) -> float:
    c = np.array(list(Counter(labels).values()), dtype=float)
    if c.sum() == 0:
        return float("nan")
    p = c / c.sum()
    if q == 0:
        return float((p > 0).sum())
    if q == 1:
        return float(np.exp(-(p * np.log(p)).sum()))
    return float((p ** q).sum() ** (1 / (1 - q)))


def rarefied_hill1(labels, m: int, n_rep: int = 1000, seed: int = 0) -> float:
    labels = list(labels)
    n = len(labels)
    if n == 0 or m <= 0:
        return float("nan")
    if m >= n:
        return hill(labels, 1)
    codes = {x: i for i, x in enumerate(sorted(set(labels)))}
    y = np.array([codes[x] for x in labels])
    rng = np.random.default_rng(seed)
    vals = np.empty(n_rep)
    for r in range(n_rep):
        sub = y[rng.permutation(n)[:m]]
        c = np.bincount(sub).astype(float)
        c = c[c > 0] / m
        vals[r] = np.exp(-(c * np.log(c)).sum())
    return float(vals.mean())


def dist(labels) -> dict:
    c = Counter(labels)
    n = sum(c.values())
    return {k: v / n for k, v in c.items()} if n else {}


def tv(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def js(p: dict, q: dict, keys: list[str], pseudo: float = 0.5, counts_q: dict | None = None) -> float:
    """Jensen-Shannon divergence (nats) between forecast p and realised counts (add-0.5 smoothed)."""
    P = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    P = P / P.sum()
    if counts_q is not None:
        Q = np.array([counts_q.get(k, 0) + pseudo for k in keys], dtype=float)
    else:
        Q = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    Q = Q / Q.sum()
    M = 0.5 * (P + Q)

    def kl(a, b):
        mask = a > 0
        return float((a[mask] * np.log(a[mask] / b[mask])).sum())
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def correct_labels(rows: list[dict]) -> list[str]:
    return [r["label"] for r in rows if r["passed"]]


def boot_stat(rows: list[dict], stat, n_boot: int = 2000, seed: int = 0, cluster: bool = True) -> list[float]:
    """90% bootstrap interval of stat(rows); cluster=True resamples paraphrases, then samples within them."""
    rng = np.random.default_rng(seed)
    by = {}
    for r in rows:
        by.setdefault(r["paraphrase_id"], []).append(r)
    keys = sorted(by)
    vals = []
    for _ in range(n_boot):
        if cluster:
            pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
            res = []
            for k in pick:
                g = by[k]
                res.extend(g[i] for i in rng.integers(0, len(g), len(g)))
        else:
            res = [rows[i] for i in rng.integers(0, len(rows), len(rows))]
        v = stat(res)
        if v == v:
            vals.append(v)
    if not vals:
        return [float("nan"), float("nan")]
    return [float(np.percentile(vals, 5)), float(np.percentile(vals, 95))]


def boot_diff(rows_a: list[dict], rows_b: list[dict], stat, n_boot: int = 2000, seed: int = 0, cluster: bool = True,
              paired: bool = True) -> dict:
    """90% interval of stat(a) - stat(b). Cluster mode resamples paraphrase ids jointly (paired) or separately."""
    rng = np.random.default_rng(seed)

    def group(rows):
        by = {}
        for r in rows:
            by.setdefault(r["paraphrase_id"], []).append(r)
        return by
    A, B = group(rows_a), group(rows_b)
    ka, kb = sorted(A), sorted(B)
    common = sorted(set(ka) & set(kb))
    vals = []
    for _ in range(n_boot):
        if cluster:
            if paired and common:
                pick = [common[i] for i in rng.integers(0, len(common), len(common))]
                pa = pb = pick
            else:
                pa = [ka[i] for i in rng.integers(0, len(ka), len(ka))]
                pb = [kb[i] for i in rng.integers(0, len(kb), len(kb))]
            ra, rb = [], []
            for k in pa:
                g = A[k]
                ra.extend(g[i] for i in rng.integers(0, len(g), len(g)))
            for k in pb:
                g = B[k]
                rb.extend(g[i] for i in rng.integers(0, len(g), len(g)))
        else:
            ra = [rows_a[i] for i in rng.integers(0, len(rows_a), len(rows_a))]
            rb = [rows_b[i] for i in rng.integers(0, len(rows_b), len(rows_b))]
        va, vb = stat(ra), stat(rb)
        if va == va and vb == vb:
            vals.append(va - vb)
    if not vals:
        return {"ci90": [float("nan"), float("nan")], "n_boot": 0}
    return {"ci90": [float(np.percentile(vals, 5)), float(np.percentile(vals, 95))], "n_boot": len(vals),
            "p_le_0": float(np.mean(np.array(vals) <= 0))}


def hill1_cc(rows: list[dict]) -> float:
    lab = correct_labels(rows)
    return hill(lab, 1) if lab else float("nan")


def make_rarefied(m: int, n_rep: int = 30, seed: int = 0):
    def f(rows):
        lab = correct_labels(rows)
        if len(lab) < m:
            return float("nan")
        return rarefied_hill1(lab, m, n_rep=n_rep, seed=seed)
    return f


def pass_rate(rows: list[dict]) -> float:
    return float(np.mean([r["passed"] for r in rows])) if rows else float("nan")


def flips(rows: list[dict], ref_rows: list[dict], ref_mode: str) -> dict:
    ref = {(r["paraphrase_id"], r["sample_id"]): r for r in ref_rows}
    n = fl = away = into_nc = 0
    for r in rows:
        k = (r["paraphrase_id"], r["sample_id"])
        if k not in ref:
            continue
        n += 1
        a, b = ref[k]["label"], r["label"]
        if a != b:
            fl += 1
            if a == ref_mode:
                away += 1
            if b == "no_code":
                into_nc += 1
    return {"n_matched": n, "flip_rate": fl / n if n else float("nan"),
            "flip_away_from_mode_rate": away / n if n else float("nan"),
            "flip_into_no_code_rate": into_nc / n if n else float("nan"),
            "flip_ci95": wilson(fl, n)}


def fisher_or_mc(table: np.ndarray, n_mc: int = 20000, seed: int = 0) -> dict:
    """Exact test for a 2 x K table: Fisher for 2x2, otherwise a Monte-Carlo permutation test of chi^2."""
    from scipy.stats import fisher_exact
    table = np.asarray(table, dtype=int)
    table = table[:, table.sum(0) > 0]
    if table.shape[1] <= 1:
        return {"test": "degenerate", "p": 1.0}
    if table.shape == (2, 2):
        return {"test": "fisher_exact", "p": float(fisher_exact(table)[1])}
    rng = np.random.default_rng(seed)
    labels = np.repeat(np.arange(table.shape[1]), table.sum(0))
    n0 = int(table[0].sum())

    def chi2(t):
        e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
        return float(((t - e) ** 2 / np.where(e > 0, e, 1)).sum())
    obs = chi2(table)
    cnt = 0
    for _ in range(n_mc):
        perm = rng.permutation(labels)
        a = np.bincount(perm[:n0], minlength=table.shape[1])
        b = np.bincount(perm[n0:], minlength=table.shape[1])
        if chi2(np.vstack([a, b])) >= obs - 1e-12:
            cnt += 1
    return {"test": "monte_carlo_chi2", "p": (cnt + 1) / (n_mc + 1), "chi2": obs}


def logit_cluster(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict:
    import statsmodels.api as sm
    if len(set(y.tolist())) < 2:
        return {"slope": None, "se": None, "p": None, "note": "outcome constant"}
    X = sm.add_constant(x.astype(float))
    try:
        m = sm.GLM(y.astype(float), X, family=sm.families.Binomial()).fit(cov_type="cluster",
                                                                          cov_kwds={"groups": groups})
        return {"intercept": float(m.params[0]), "slope": float(m.params[1]), "se": float(m.bse[1]),
                "p": float(m.pvalues[1]), "ci95": [float(v) for v in m.conf_int()[1]]}
    except (ValueError, np.linalg.LinAlgError) as e:
        return {"slope": None, "se": None, "p": None, "note": f"fit failed: {e!r}"[:200]}


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def kappa_ci(a: list[str], b: list[str], n_boot: int = 2000, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    n = len(a)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        v = cohen_kappa([a[i] for i in idx], [b[i] for i in idx])
        if v == v:
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [float("nan")] * 2


def self_test() -> None:
    assert abs(hill(list("abcd"), 1) - 4) < 1e-9 and abs(hill(list("aaaa"), 1) - 1) < 1e-9
    assert abs(hill(list("abcd"), 2) - 4) < 1e-9
    skew = list("a" * 90 + "b" * 7 + "c" * 2 + "d")
    assert rarefied_hill1(skew, 20, n_rep=500) <= hill(skew, 1) + 1e-9
    a = boot_stat([{"paraphrase_id": i % 10, "sample_id": i, "label": "x" if i % 3 else "y", "passed": True}
                   for i in range(100)], hill1_cc, n_boot=200, seed=1)
    b = boot_stat([{"paraphrase_id": i % 10, "sample_id": i, "label": "x" if i % 3 else "y", "passed": True}
                   for i in range(100)], hill1_cc, n_boot=200, seed=1)
    assert a == b
    assert math.isfinite(math.log(0.02))


if __name__ == "__main__":
    self_test()
    print("stats self-test ok")
