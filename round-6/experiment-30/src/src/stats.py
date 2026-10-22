#!/usr/bin/env python3
"""Statistics used by the committed decision rules (pure numpy/scipy; tested in tests/test_cpu.py).

exact McNemar (two-sided: min(1, 2 P(X <= min(b, c))), X ~ Bin(b + c, 1/2); one-sided: P(X >= b)), Holm step-down,
Mantel-Haenszel odds ratio with the Robins-Breslow-Greenland variance, Wilson intervals, first-divergence index.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
from scipy.stats import binom

from cfg import wilson_ci  # noqa: F401  (re-exported)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2.0 * binom.cdf(min(b, c), n, 0.5)))


def mcnemar_one_sided(b: int, c: int) -> float:
    """P(X >= b), X ~ Bin(b + c, 1/2): evidence that the b side exceeds the c side."""
    n = b + c
    if n == 0:
        return 1.0
    return float(binom.sf(b - 1, n, 0.5))


def holm(p: Sequence[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * p[i]))
        adj[i] = run
    return adj.tolist()


def mantel_haenszel(tables: Sequence[Sequence[float]], z: float = 1.959963984540054) -> dict[str, Any]:
    """tables: [(a, b, c, d)] per stratum with a = exposed & y1, b = exposed & y0, c = unexposed & y1,
    d = unexposed & y0. Strata with n < 2 or without both exposure groups contribute nothing."""
    R = S = 0.0
    sPR = sPS_QR = sQS = 0.0
    used = 0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n < 2 or (a + b) == 0 or (c + d) == 0:
            continue
        used += 1
        r, s = a * d / n, b * c / n
        p, q = (a + d) / n, (b + c) / n
        R += r
        S += s
        sPR += p * r
        sPS_QR += p * s + q * r
        sQS += q * s
    if R == 0 or S == 0:
        return {"or": float("inf") if S == 0 and R > 0 else (0.0 if R == 0 and S > 0 else float("nan")),
                "ci": [float("nan"), float("nan")], "n_strata_used": used, "R": R, "S": S}
    lor = math.log(R / S)
    var = sPR / (2 * R * R) + sPS_QR / (2 * R * S) + sQS / (2 * S * S)
    se = math.sqrt(var)
    return {"or": math.exp(lor), "ci": [math.exp(lor - z * se), math.exp(lor + z * se)], "log_or": lor, "se": se,
            "n_strata_used": used, "R": R, "S": S}


def first_divergence(a: Sequence[int], b: Sequence[int]) -> int:
    """First index where two token sequences differ (len of the shorter if one is a prefix of the other)."""
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def code_start(tok_texts: Sequence[str]) -> int | None:
    """Index of the first token after the opening fence LINE (the token after the first '\\n' that follows the first
    token containing ```). tok_texts = decoded text per token."""
    seen = False
    for i, s in enumerate(tok_texts):
        if not seen:
            if "```" in s:
                seen = True
                j = s.find("```")
                if "\n" in s[j:]:
                    return i + 1
            continue
        if "\n" in s:
            return i + 1
    return None
