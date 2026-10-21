"""Small statistics toolkit: Wilson and Newcombe intervals, Hill numbers (with rarefaction), template-cluster
bootstrap, Jensen-Shannon divergence with a pooled-bootstrap null, permutation chi-square of homogeneity, exact
one-sided upper bounds for zero/low counts, Cohen's kappa, log scores."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Callable, Iterable

Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def newcombe(k1: int, n1: int, k2: int, n2: int) -> dict[str, Any]:
    """Newcombe hybrid score interval for p1 - p2."""
    if n1 == 0 or n2 == 0:
        return {"diff": None, "ci": [None, None]}
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {"diff": d, "ci": [lo, hi]}


def exact_upper(k: int, n: int, alpha: float = 0.05) -> float | None:
    """Exact (Clopper-Pearson) one-sided upper bound; 0/N -> 1 - alpha^(1/N) (~3/N)."""
    if n == 0:
        return None
    if k >= n:
        return 1.0
    from scipy.stats import beta

    return float(beta.ppf(1 - alpha, k + 1, n - k))


def hill1(counts: Iterable[int]) -> float:
    c = [x for x in counts if x > 0]
    n = sum(c)
    if n == 0:
        return 0.0
    h = -sum((x / n) * math.log(x / n) for x in c)
    return math.exp(h)


def hill1_rarefied(labels: list[str], depth: int = 20, draws: int = 200, seed: int = 0) -> float | None:
    if len(labels) < depth:
        return None
    rng = random.Random(seed)
    vals = [hill1(Counter(rng.sample(labels, depth)).values()) for _ in range(draws)]
    return sum(vals) / len(vals)


def cluster_bootstrap(rows: list[dict[str, Any]], stat: Callable[[list[dict[str, Any]]], float | None],
                      cluster_key: str = "template", n_boot: int = 2000, seed: int = 0) -> list[float | None]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r.get(cluster_key), []).append(r)
    keys = list(groups)
    if len(keys) < 2:
        return [None, None]
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        samp = []
        for _k in keys:
            samp.extend(groups[rng.choice(keys)])
        v = stat(samp)
        if v is not None:
            vals.append(v)
    if not vals:
        return [None, None]
    vals.sort()
    return [vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]]


def js_divergence(c1: Counter, c2: Counter) -> float:
    keys = set(c1) | set(c2)
    n1, n2 = sum(c1.values()), sum(c2.values())
    if n1 == 0 or n2 == 0:
        return float("nan")
    js = 0.0
    for k in keys:
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        if p > 0:
            js += 0.5 * p * math.log2(p / m)
        if q > 0:
            js += 0.5 * q * math.log2(q / m)
    return js


def js_null(labels1: list[str], labels2: list[str], n_boot: int = 2000, seed: int = 0) -> dict[str, Any]:
    """Observed JS (bits) vs a pooled-bootstrap null (both samples redrawn from the pooled labels)."""
    obs = js_divergence(Counter(labels1), Counter(labels2))
    pooled = labels1 + labels2
    rng = random.Random(seed)
    null = []
    for _ in range(n_boot):
        a = [rng.choice(pooled) for _ in labels1]
        b = [rng.choice(pooled) for _ in labels2]
        null.append(js_divergence(Counter(a), Counter(b)))
    p = (1 + sum(v >= obs for v in null)) / (1 + len(null))
    null.sort()
    return {"js_bits": obs, "null_p95": null[int(0.95 * (len(null) - 1))], "p_value": p, "n_boot": n_boot}


def chi2_stat(table: list[list[int]]) -> float:
    rows = [sum(r) for r in table]
    cols = [sum(c) for c in zip(*table)]
    n = sum(rows)
    if n == 0:
        return 0.0
    s = 0.0
    for i, r in enumerate(table):
        for j, o in enumerate(r):
            e = rows[i] * cols[j] / n
            if e > 0:
                s += (o - e) ** 2 / e
    return s


def perm_chi2(groups: dict[str, list[str]], n_perm: int = 10000, seed: int = 0) -> dict[str, Any]:
    """Permutation chi-square of homogeneity of a binary/categorical label across groups."""
    cats = sorted({x for v in groups.values() for x in v})
    names = list(groups)

    def table(gs):
        return [[sum(1 for x in gs[g] if x == c) for c in cats] for g in names]

    obs = chi2_stat(table(groups))
    pooled = [x for g in names for x in groups[g]]
    sizes = [len(groups[g]) for g in names]
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        gs, i = {}, 0
        for g, s in zip(names, sizes):
            gs[g] = pooled[i:i + s]
            i += s
        ge += chi2_stat(table(gs)) >= obs - 1e-12
    return {"chi2": obs, "p_perm": (ge + 1) / (n_perm + 1), "n_perm": n_perm, "categories": cats,
            "counts": {g: dict(Counter(groups[g])) for g in names}}


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a or len(a) != len(b):
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def log_score(pred: dict[str, float], labels: list[str], survivors: list[str], uniform_mix: float = 0.05,
              other_floor: float = 0.02) -> dict[str, Any]:
    """Frozen C1 scoring: mix the forecast with 5% uniform over survivors and a 2% shared 'other' floor."""
    if not labels:
        return {"mean_log_score": None, "top1_hit": None}
    surv = list(survivors)
    q: dict[str, float] = {}
    tot = sum(pred.get(s, 0.0) for s in surv) or 0.0
    for s in surv:
        base = (pred.get(s, 0.0) / tot) if tot > 0 else 1.0 / len(surv)
        q[s] = (1 - uniform_mix - other_floor) * base + uniform_mix / len(surv)
    q["other"] = other_floor
    ls = [math.log(q.get(l, other_floor)) for l in labels]
    top = max(surv, key=lambda s: q[s]) if surv else None
    modal = Counter(labels).most_common(1)[0][0]
    return {"mean_log_score": sum(ls) / len(ls), "top1": top, "observed_modal": modal, "top1_hit": top == modal}
