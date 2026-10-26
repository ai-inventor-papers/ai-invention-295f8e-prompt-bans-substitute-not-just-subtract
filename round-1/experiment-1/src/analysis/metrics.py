#!/usr/bin/env python3
"""Shared descriptive statistics: condition summaries, event outcomes, scoring primitives."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

from common import MODES, NO_CODE, OTHER, THRESHOLDS, wilson_ci


def hill_cc(labels: list[str]) -> float:
    if not labels:
        return float("nan")
    c = np.array(list(Counter(labels).values()), dtype=float)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    code = [r for r in rows if r["label"] != NO_CODE]
    lab = Counter(r["label"] for r in code)
    lab_c = Counter(r["label"] for r in code if r["passed"])
    k_pass = sum(1 for r in code if r["passed"])
    out = {
        "n": n, "n_code": len(code), "no_code_rate": (n - len(code)) / n if n else None,
        "label_counts": dict(lab), "label_counts_correct": dict(lab_c),
        "pass_rate": k_pass / len(code) if code else None,
        "pass_rate_wilson_ci": list(wilson_ci(k_pass, len(code))) if code else None,
        "hill_cc": hill_cc([r["label"] for r in code if r["passed"]]),
        "other_fraction": lab.get(OTHER, 0) / len(code) if code else None,
        "truncation_rate": sum(1 for r in rows if r.get("finish_reason") == "length") / n if n else None,
        "wilson_ci": {k: list(wilson_ci(v, len(code))) for k, v in lab.items()},
        "labeller_sources": dict(Counter(r.get("labeller_source") for r in rows)),
    }
    return out


def event_outcome(task: str, rows: list[dict[str, Any]], banned: list[str]) -> dict[str, Any]:
    S = [m for m in MODES[task] if m not in banned]
    code = [r for r in rows if r["label"] != NO_CODE]
    rec = sum(1 for r in code if r["label"] in banned)
    compliant = [r for r in code if r["passed"] and r["label"] not in banned]
    counts = Counter(r["label"] if r["label"] in S else OTHER for r in compliant)
    nc = len(compliant)
    shares = {y: counts.get(y, 0) / nc if nc else 0.0 for y in S + [OTHER]}
    order = sorted(S + [OTHER], key=lambda y: (-shares[y], y))
    top, second = order[0], order[1] if len(order) > 1 else None
    margin = shares[top] - (shares[second] if second else 0.0)
    realised = top if (nc > 0 and margin >= THRESHOLDS["realised_margin"]) else "no clear mode"
    cat_order = sorted(S, key=lambda y: (-counts.get(y, 0), y))
    return {
        "survivors": S, "n_rows": len(rows), "n_code": len(code), "recurrence": rec / len(code) if code else None,
        "compliance": 1 - rec / len(code) if code else None, "n_compliant": nc,
        "pass_rate": sum(1 for r in code if r["passed"]) / len(code) if code else None,
        "realised_counts": {y: counts.get(y, 0) for y in S + [OTHER]}, "realised_shares": shares,
        "realised_mode": realised, "realised_margin": margin, "plurality": top,
        "plurality_catalogue": cat_order[0] if cat_order and counts.get(cat_order[0], 0) > 0 else None,
        "hill_cc": hill_cc([r["label"] for r in compliant]),
        "label_counts_all": dict(Counter(r["label"] for r in code)),
    }


def is_informative(stratum: str, out: dict[str, Any]) -> bool:
    present = stratum in ("modal", "present", "succession")
    return bool(present and (out["compliance"] or 0) >= THRESHOLDS["compliance_informative"]
                and len(out["survivors"]) >= 2 and out["n_compliant"] >= THRESHOLDS["min_compliant"])


def js_bits(p: dict[str, float], q: dict[str, float]) -> float:
    keys = sorted(set(p) | set(q))
    a = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    b = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    a, b = a / a.sum(), b / b.sum()
    m = 0.5 * (a + b)

    def kl(x, y):
        mask = x > 0
        return float((x[mask] * np.log2(x[mask] / y[mask])).sum())

    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def smoothed(counts: dict[str, int], keys: list[str], add: float = 0.5) -> dict[str, float]:
    tot = sum(counts.get(k, 0) + add for k in keys)
    return {k: (counts.get(k, 0) + add) / tot for k in keys}


def log_score(q: dict[str, float], labels: list[str]) -> float:
    return float(np.mean([math.log(q[y]) for y in labels])) if labels else float("nan")


def spearman(a: list[float], b: list[float]) -> float | None:
    from scipy.stats import spearmanr

    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    r = spearmanr(a, b).statistic
    return None if r != r else float(r)


def top2_agree(q: dict[str, float], shares: dict[str, float], S: list[str]) -> bool | None:
    if len(S) < 3:
        return None
    tq = sorted(S, key=lambda y: (-q[y], y))[:2]
    tr = sorted(S, key=lambda y: (-shares[y], y))[:2]
    return tq == tr


def bootstrap_ci(vals: list[float], n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> list[float] | None:
    if not vals:
        return None
    rng = np.random.default_rng(seed)
    arr = np.array(vals, dtype=float)
    bs = arr[rng.integers(0, len(arr), (n_boot, len(arr)))].mean(axis=1)
    return [float(np.quantile(bs, alpha / 2)), float(np.quantile(bs, 1 - alpha / 2))]


def newcombe_diff_ci(k1: int, n1: int, k2: int, n2: int) -> list[float]:
    """Newcombe (1998) hybrid score interval for p1 - p2."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_ci(k1, n1)
    l2, u2 = wilson_ci(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return [lo, hi]


def binom_exact_ci(k: int, n: int, alpha: float = 0.05) -> list[float] | None:
    from scipy.stats import beta

    if n == 0:
        return None
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]
