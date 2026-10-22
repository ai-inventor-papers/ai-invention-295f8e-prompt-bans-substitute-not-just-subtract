#!/usr/bin/env python3
"""Shared statistics and row access for the iteration-4 analyses (committed before the first population sample).

Shares: off-default share = #(catalogue label != default) / #valid, with 'invalid' and 'disputed' excluded from the
denominator and 'other' counted as NOT off-default (catalogue-only). Pass = passed the hidden tests (all attempts).
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src_base", ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

EXCLUDE = ("invalid", "disputed")


# ------------------------------------------------------------------------------------------------ rows
def join_rows(raw: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lab = {l["key"]: l for l in labels}
    out = []
    for r in raw:
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        if k in lab:
            l = lab[k]
            out.append({**{x: r.get(x) for x in ("task", "arm", "template", "sample_id", "family", "alpha",
                                                 "direction_seed", "s_dose", "axis", "stage", "n_tokens",
                                                 "finish_reason")},
                        "label": l["label"], "passed": bool(l.get("passed")), "valid": bool(l.get("valid")),
                        "labeller_source": l.get("labeller_source"), "code_sha256": l.get("code_sha256")})
    return out


def share(rows: Iterable[dict[str, Any]], cat: set[str], default: str) -> dict[str, Any]:
    rows = list(rows)
    valid = [r for r in rows if r["label"] not in EXCLUDE]
    off = sum(1 for r in valid if r["label"] in cat and r["label"] != default)
    n = len(valid)
    npass = sum(1 for r in rows if r["passed"])
    return {"n": len(rows), "n_valid": n, "k_off": off, "share": off / n if n else float("nan"),
            "pass": npass / len(rows) if rows else float("nan"), "k_pass": npass,
            "n_other": sum(1 for r in rows if r["label"] == "other"),
            "n_invalid": sum(1 for r in rows if r["label"] == "invalid"),
            "n_disputed": sum(1 for r in rows if r["label"] == "disputed")}


def by_key(rows: Iterable[dict[str, Any]], *keys: str) -> dict[tuple, list[dict[str, Any]]]:
    out: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        out[tuple(r[k] for k in keys)].append(r)
    return out


# ------------------------------------------------------------------------------------------------ stats
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.all(x == x[0]) or np.all(y == y[0]):
        return 0.0
    return float(stats.spearmanr(x, y)[0])


def perm_spearman(x: np.ndarray, y: np.ndarray, n_perm: int = 10000, seed: int = 0) -> dict[str, float]:
    """One-sided (greater) permutation p of Spearman rho, shuffling y; ties get average ranks; p = (1+#{rho*>=rho})/(1+n)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = spearman(x, y)
    rx = stats.rankdata(x)
    ry = stats.rankdata(y)
    rng = np.random.default_rng(seed)
    if np.all(ry == ry[0]):
        return {"rho": 0.0, "p": 1.0, "n": len(x)}
    rxc = (rx - rx.mean()) / max(rx.std(), 1e-12)
    P = np.stack([rng.permutation(ry) for _ in range(n_perm)])
    Pc = (P - P.mean(1, keepdims=True)) / np.maximum(P.std(1, keepdims=True), 1e-12)
    null = (Pc @ rxc) / len(x)
    p = (1 + int(np.sum(null >= rho - 1e-12))) / (1 + n_perm)
    return {"rho": rho, "p": float(p), "n": len(x), "null_q95": float(np.quantile(null, 0.95)),
            "null_q99": float(np.quantile(null, 0.99))}


def kendall(x: np.ndarray, y: np.ndarray) -> float:
    if np.all(np.asarray(y) == y[0]):
        return 0.0
    return float(stats.kendalltau(x, y, variant="b")[0])


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))

    def resid(a, b):
        b1 = np.c_[np.ones_like(b), b]
        coef, *_ = np.linalg.lstsq(b1, a, rcond=None)
        return a - b1 @ coef
    ex, ey = resid(rx, rz), resid(ry, rz)
    if np.std(ex) < 1e-12 or np.std(ey) < 1e-12:
        return 0.0
    return float(np.corrcoef(ex, ey)[0, 1])


def binom_greater_p(k: int, n: int, p0: float) -> float:
    return float(stats.binomtest(k, n, p0, alternative="greater").pvalue) if n > 0 else 1.0


def hill1(labels: list[str]) -> float:
    c = Counter(labels)
    n = sum(c.values())
    if n == 0:
        return float("nan")
    return math.exp(-sum((v / n) * math.log(v / n) for v in c.values()))


def hill1_rarefied(labels: list[str], depth: int = 25, n_sub: int = 1000, seed: int = 0) -> dict[str, Any]:
    if len(labels) < depth:
        return {"hill1": hill1(labels), "rarefied": float("nan"), "n": len(labels), "flag_below_depth": True}
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    vals = [hill1(list(rng.choice(arr, depth, replace=False))) for _ in range(n_sub)]
    return {"hill1": hill1(labels), "rarefied": float(np.mean(vals)), "n": len(labels), "flag_below_depth": False}


def js(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    m = {k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0)) for k in keys}

    def kl(a):
        return sum(a[k] * math.log2(a[k] / m[k]) for k in keys if a.get(k, 0.0) > 0)
    return 0.5 * kl(p) + 0.5 * kl(q)


def dist(labels: list[str]) -> dict[str, float]:
    c = Counter(labels)
    n = sum(c.values())
    return {k: v / n for k, v in c.items()} if n else {}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def auc(score: np.ndarray, lab: np.ndarray) -> float:
    pos, neg = score[lab == 1], score[lab == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))
