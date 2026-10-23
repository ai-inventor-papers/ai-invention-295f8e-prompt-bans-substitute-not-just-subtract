#!/usr/bin/env python3
"""Committed prediction functions and statistics (pure numpy/scipy; no GPU).

Token-map composition (plan DEFINITIONS). For a node n with fp32 logits z_n (teacher-forced, per template):
  pi_T(t | n)   = softmax(z_n[top20] / T) restricted to the 20 highest-logit tokens (T = 1 everywhere else)
  G(A | n, t)   = Phat(A | n, t) if t is committal (max_A Phat >= 0.8) or n has no second decision;
                  else sum_{t' in top20(n + t)} pi_T(t' | n + t) Phat(A | n + t, t')        (two-token composition)
  F_T(A | n)    = sum_{t in top20(n)} pi_T(t | n) G(A | n, t)
  P_T(A)        = sum_c w_c F_T(A | n_c) + (1 - sum_c w_c) q_rest(A)
with w_c the T = 1 probability of staying on opening O_c and q_rest the twin's off-opening label distribution.
The same composition with Pfail gives the predicted pass cost, and with Prev the predicted reversion.
Per-slot replay: the dosed decision token of slot s is the inverse CDF (token-id order) of pi_T(. | n) at the slot's
own uniform U[s, i_n]; a slot whose token does not change keeps the twin's label (identity property).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats

from cfg8 import COMMITTAL, PSEUDO


# ------------------------------------------------------------------------------------------------ distributions
def dist_topk(z: Any, T: float, k: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """(token ids, probabilities) of softmax(z[topk] / T) over the k highest logits (k = 0: full vocabulary).
    z is a full logit vector, or a (ids, logits) pair of saved top logits sorted descending."""
    if isinstance(z, tuple):
        return dist_top_from_saved(z[0], z[1], T, k)
    z = np.asarray(z, dtype=np.float64)
    if k and k > 0:
        ids = np.argpartition(-z, k - 1)[:k]
    else:
        ids = np.arange(len(z))
    x = z[ids] / float(T)
    x = x - x.max()
    p = np.exp(x)
    p /= p.sum()
    return ids, p


def dist_top_from_saved(ids: list[int], z: list[float], T: float, k: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Same from saved top-64 (ids sorted by logit, descending)."""
    ids_a = np.asarray(ids[:k], dtype=np.int64)
    x = np.asarray(z[:k], dtype=np.float64) / float(T)
    x = x - x.max()
    p = np.exp(x)
    return ids_a, p / p.sum()


def phat_vec(labels: list[str], classes: list[str]) -> np.ndarray:
    """Phat over classes (catalogue + 'other' + 'invalid') with pseudo-count PSEUDO per class."""
    c = np.full(len(classes), PSEUDO, dtype=np.float64)
    for l in labels:
        c[classes.index(l) if l in classes else classes.index("other")] += 1.0
    return c / c.sum()


def committal(ph: np.ndarray, classes: list[str]) -> str | None:
    """class(t) if max_A Phat(A | n, t) >= 0.8 over the catalogue algorithms (not 'other'/'invalid'), else None."""
    j = int(np.argmax(ph))
    if ph[j] >= COMMITTAL and classes[j] not in ("other", "invalid"):
        return classes[j]
    return None


def compose_node(z: np.ndarray, T: float, tmap: dict[int, dict[str, Any]], resid: dict[str, np.ndarray],
                 second: dict[int, dict[str, Any]] | None = None, k: int = 20) -> dict[str, np.ndarray]:
    """F_T(. | n) for algorithm shares, Pfail and Prev at one node and one template.
    tmap[t] = {'phat': [C], 'pfail': float, 'prev': float} for the mapped tokens; tokens of top20 without a map use
    `resid` ({'phat','pfail','prev'}). second[t] = {'z': z_{n+t}, 'tmap': ..., 'resid': ...} for non-committal t."""
    ids, p = dist_topk(z, T, k)
    C = len(resid["phat"])
    F = np.zeros(C)
    fail = 0.0
    rev = 0.0
    off_mass = 0.0
    for t, pt in zip(ids.tolist(), p.tolist()):
        if second is not None and t in second:
            sub = compose_node(second[t]["z"], T, second[t]["tmap"], second[t]["resid"], None, k)
            F += pt * sub["F"]
            fail += pt * sub["fail"]
            rev += pt * sub["rev_mass"]
            off_mass += pt * sub["off_mass"]
            continue
        m = tmap.get(t)
        if m is None:
            F += pt * resid["phat"]
            fail += pt * resid["pfail"]
            continue
        F += pt * m["phat"]
        fail += pt * m["pfail"]
        if m.get("off_default"):
            off_mass += pt
            rev += pt * m["prev"]
    return {"F": F, "fail": fail, "rev_mass": rev, "off_mass": off_mass}


def compose_unit(node_data: list[dict[str, Any]], q_rest: np.ndarray, q_rest_fail: float, T: float,
                 k: int = 20) -> dict[str, Any]:
    """P_T(A) for one template: node_data = [{'w': w_c, 'z', 'tmap', 'resid', 'second'}]."""
    C = len(q_rest)
    P = np.zeros(C)
    fail = 0.0
    rev = 0.0
    off = 0.0
    wsum = 0.0
    for nd in node_data:
        r = compose_node(nd["z"], T, nd["tmap"], nd["resid"], nd.get("second"), k)
        P += nd["w"] * r["F"]
        fail += nd["w"] * r["fail"]
        rev += nd["w"] * r["rev_mass"]
        off += nd["w"] * r["off_mass"]
        wsum += nd["w"]
    wsum = min(wsum, 1.0)
    P += (1.0 - wsum) * q_rest
    fail += (1.0 - wsum) * q_rest_fail
    return {"P": P, "fail": fail, "reversion": (rev / off) if off > 1e-12 else 0.0, "off_token_mass": off,
            "on_opening": wsum}


# ------------------------------------------------------------------------------------------------ replay
def replay_token(top_ids: list[int], top_z: list[float], u: float, T: float, k: int = 20) -> int:
    """Inverse CDF in TOKEN-ID order over the top-k at temperature T (engine order), searchsorted(left)."""
    ids = np.asarray(top_ids[:k], dtype=np.int64)
    z = np.asarray(top_z[:k], dtype=np.float64)
    o = np.argsort(ids)
    ids, z = ids[o], z[o]
    x = z / float(T)
    x = x - x.max()
    p = np.exp(x)
    cdf = np.cumsum(p)
    cdf /= cdf[-1]
    j = int(np.searchsorted(cdf, u, side="left"))
    return int(ids[min(j, len(ids) - 1)])


# ------------------------------------------------------------------------------------------------ statistics
def wilson(x: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_paired(a: int, b: int, c: int, d: int, z: float = 1.96) -> dict[str, float]:
    """Newcombe (1998) method 10 hybrid-score CI for p1 - p2 of paired binary outcomes.
    a = both 1, b = 1 then 0, c = 0 then 1, d = both 0; p1 = (a + b) / n, p2 = (a + c) / n."""
    n = a + b + c + d
    if n == 0:
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan")}
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, z)
    l2, u2 = wilson(a + c, n, z)
    diff = p1 - p2
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        if num > n / 2:
            num -= n / 2
        elif num >= 0:
            num = 0.0
        phi = num / math.sqrt(denom)
    dl2 = (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2
    du2 = (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2
    return {"diff": diff, "lo": diff - math.sqrt(max(dl2, 0.0)), "hi": diff + math.sqrt(max(du2, 0.0))}


def mcnemar_exact(b: int, c: int, alternative: str = "two-sided") -> float:
    n = b + c
    if n == 0:
        return 1.0
    if alternative == "greater":          # H1: b > c
        return float(stats.binom.sf(b - 1, n, 0.5))
    if alternative == "less":
        return float(stats.binom.cdf(b, n, 0.5))
    return float(min(1.0, 2 * min(stats.binom.cdf(min(b, c), n, 0.5), 1.0)))


def hill1_rarefied(labels: list[str], depth: int = 25) -> float | None:
    """exp(E[H]) with E[H] the exact hypergeometric expectation of the Shannon entropy (nats) of a random
    depth-subset (without replacement) of the given labels; None if fewer than depth labels."""
    N = len(labels)
    if N < depth:
        return None
    from collections import Counter
    EH = 0.0
    for _, n_i in Counter(labels).items():
        xs = np.arange(1, min(n_i, depth) + 1)
        pm = stats.hypergeom.pmf(xs, N, n_i, depth)
        q = xs / depth
        EH -= float(np.sum(pm * q * np.log(q)))
    return float(math.exp(EH))


def hill1_bruteforce(labels: list[str], depth: int) -> float:
    """Brute-force check of hill1_rarefied on small inputs (all subsets)."""
    from collections import Counter
    from itertools import combinations
    Hs = []
    for sub in combinations(range(len(labels)), depth):
        cnt = Counter(labels[i] for i in sub)
        q = np.array(list(cnt.values()), dtype=float) / depth
        Hs.append(-float(np.sum(q * np.log(q))))
    return float(math.exp(np.mean(Hs)))


def mae_noise_ceiling(pred: list[np.ndarray], n: int = 50, draws: int = 10_000, thr: float = 0.10,
                      seed: int = 20261023) -> float:
    """P(MAE <= thr | prediction exactly true): draw each cell's counts ~ Multinomial(n, pred_cell), MAE over all
    (cell, class) entries; pred = list of share vectors (one per cell)."""
    rng = np.random.default_rng(seed)
    ok = 0
    P = [np.clip(np.asarray(p, dtype=float), 0, None) for p in pred]
    P = [p / p.sum() for p in P]
    for _ in range(draws):
        errs = []
        for p in P:
            x = rng.multinomial(n, p) / n
            errs.extend(np.abs(x - p).tolist())
        ok += float(np.mean(errs)) <= thr
    return ok / draws


def pick_dose(curve: dict[float, float], target: float, attainable_frac: float | None = None) -> float | None:
    """Smallest grid T whose predicted value reaches target (curve: T -> value, increasing T)."""
    for T in sorted(curve):
        if curve[T] >= target - 1e-12:
            return T
    return None
