"""Statistics: Wilson intervals, Hill numbers (order 1) with rarefaction and bootstrap, Cohen's kappa with
PABAK, raw agreement and bootstrap CI, Kish ESS, log-sum-exp helpers, Kendall tau."""

from __future__ import annotations

import math
import random
from collections import Counter

import numpy as np


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def hill1(labels: list[str]) -> float:
    if not labels:
        return float("nan")
    c = Counter(labels)
    n = len(labels)
    return math.exp(-sum((v / n) * math.log(v / n) for v in c.values()))


def rarefied_hill1(labels: list[str], depth: int = 25, reps: int = 1000, seed: int = 0) -> float | None:
    if len(labels) < depth:
        return None
    rng = random.Random(seed)
    return float(np.mean([hill1(rng.sample(labels, depth)) for _ in range(reps)]))


def bootstrap_ci(labels: list[str], stat, reps: int = 1000, alpha: float = 0.10, seed: int = 0):
    if not labels:
        return (None, None)
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        s = [labels[rng.randrange(len(labels))] for _ in range(len(labels))]
        v = stat(s)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            vals.append(v)
    if not vals:
        return (None, None)
    return (float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2)))


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def pabak(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    k = max(len(set(a) | set(b)), 2)
    po = sum(x == y for x, y in zip(a, b)) / n
    return (k * po - 1) / (k - 1)


def raw_agreement(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a) if a else float("nan")


def kappa_bootstrap(a, b, reps: int = 1000, alpha: float = 0.05, seed: int = 0):
    rng = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(cohen_kappa([a[i] for i in idx], [b[i] for i in idx]))
    vals = [v for v in vals if not math.isnan(v)]
    return (float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))) if vals else (None, None)


def logsumexp(x) -> float:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return float("-inf")
    m = np.max(x)
    return float(m + np.log(np.sum(np.exp(x - m))))


def logmeanexp(x) -> float:
    return logsumexp(x) - math.log(len(x))


def kish_ess_log(w) -> float:
    w = np.asarray(w, dtype=float)
    return float(math.exp(2 * logsumexp(w) - logsumexp(2 * w)))


def kendall_tau(order_a: list[str], order_b: list[str]) -> float:
    pos_b = {t: i for i, t in enumerate(order_b)}
    items = [t for t in order_a if t in pos_b]
    n = len(items)
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (pos_b[items[i]] - pos_b[items[j]])
            if s < 0:
                conc += 1
            elif s > 0:
                disc += 1
    return (conc - disc) / max(conc + disc, 1)


def self_test() -> dict:
    """Gate arithmetic check on a synthetic confusion matrix with a known answer.
    2x2 table [[20, 5], [10, 15]]: po = 0.70, pe = 0.5, kappa = 0.40, PABAK = 0.40."""
    a = ["x"] * 25 + ["y"] * 25
    b = ["x"] * 20 + ["y"] * 5 + ["x"] * 10 + ["y"] * 15
    k = cohen_kappa(a, b)
    pk = pabak(a, b)
    lo, hi = wilson(48, 50)
    return {"kappa": k, "kappa_ok": abs(k - 0.40) < 1e-9, "pabak": pk, "pabak_ok": abs(pk - 0.40) < 1e-9,
            "wilson_48_50": [lo, hi], "wilson_ok": abs(lo - 0.865) < 0.002 and abs(hi - 0.989) < 0.002,
            "hill1_uniform4": hill1(list("abcd")), "hill1_ok": abs(hill1(list("abcd")) - 4) < 1e-9,
            "ess_equal_weights": kish_ess_log([0.0] * 10), "ess_ok": abs(kish_ess_log([0.0] * 10) - 10) < 1e-9}
