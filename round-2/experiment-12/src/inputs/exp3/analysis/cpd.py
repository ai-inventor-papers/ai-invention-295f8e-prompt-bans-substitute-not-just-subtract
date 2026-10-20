"""S8 change points + S9 tests.

Binary segmentation on G(i) = 2 * N_seg * JS_w(P_left, P_right) (nats) -- the multinomial likelihood-ratio statistic --
with a permutation null (continuation labels permuted across the segment's positions, sizes kept). PELT with a custom
multinomial cost (ruptures) is the Forking-Fast-aligned sensitivity analysis.
"""

from __future__ import annotations

import numpy as np


def _xlogx(c: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(c > 0, c * np.log(np.where(c > 0, c, 1.0)), 0.0)


def seg_loglik(counts: np.ndarray) -> np.ndarray:
    """Max multinomial log-likelihood of pooled counts (..., K): sum c log(c/N)."""
    n = counts.sum(-1)
    return _xlogx(counts).sum(-1) - _xlogx(n)


def split_stats(C: np.ndarray) -> np.ndarray:
    """G for every split of the (npos, K) matrix into [:i] and [i:], i = 1..npos-1. Shape (..., npos-1)."""
    cum = np.cumsum(C, axis=-2)
    left = cum[..., :-1, :]
    total = cum[..., -1:, :]
    right = total - left
    return 2.0 * (seg_loglik(left) + seg_loglik(right) - seg_loglik(total))


def perm_max_g(C: np.ndarray, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    """Null distribution of max_i G(i): permute individual labels across positions, keeping per-position sizes."""
    npos, K = C.shape
    sizes = C.sum(1).astype(int)
    labels = np.repeat(np.arange(K), C.sum(0).astype(int))
    N = labels.size
    if N == 0 or npos < 2:
        return np.zeros(n_perm)
    perms = np.argsort(rng.random((n_perm, N)), axis=1)
    pl = labels[perms]  # (n_perm, N)
    onehot = np.zeros((n_perm, N, K), dtype=np.float64)
    np.put_along_axis(onehot, pl[..., None], 1.0, axis=2)
    bounds = np.cumsum(sizes)[:-1]
    cum = np.cumsum(onehot, axis=1)  # (n_perm, N, K)
    left = cum[:, bounds - 1, :]  # (n_perm, npos-1, K)
    total = cum[:, -1:, :]
    right = total - left
    g = 2.0 * (seg_loglik(left) + seg_loglik(right) - seg_loglik(total))
    # splits at positions with zero size are ill-defined; sizes > 0 here by construction
    return g.max(1)


def binseg(C: np.ndarray, n_perm: int = 1000, alpha: float = 0.05, max_cp: int = 3,
           seed: int = 0) -> list[dict]:
    """Permutation-calibrated binary segmentation. Returns change points as indices i (split between i-1 and i)."""
    rng = np.random.default_rng(seed)
    found: list[dict] = []
    stack = [(0, C.shape[0])]
    while stack and len(found) < max_cp:
        a, b = stack.pop(0)
        if b - a < 2:
            continue
        sub = C[a:b]
        if sub.sum() == 0:
            continue
        g = split_stats(sub)
        i = int(np.argmax(g))
        gmax = float(g[i])
        null = perm_max_g(sub, n_perm, rng)
        thr = float(np.quantile(null, 1 - alpha))
        p = float((1 + (null >= gmax).sum()) / (1 + n_perm))
        if gmax > thr and gmax > 1e-9:
            cp = a + i + 1
            found.append({"index": cp, "G": gmax, "threshold": thr, "p_perm": p, "segment": [a, b]})
            stack.append((a, cp))
            stack.append((cp, b))
    return sorted(found, key=lambda d: d["index"])


def perm_chi2(c1, c2, n_perm: int = 2000, seed: int = 0) -> float:
    """Monte-Carlo permutation p-value of the chi-square statistic for two count vectors."""
    c1 = np.asarray(c1, float)
    c2 = np.asarray(c2, float)
    K = len(c1)
    keep = (c1 + c2) > 0
    c1, c2 = c1[keep], c2[keep]
    if len(c1) < 2 or c1.sum() == 0 or c2.sum() == 0:
        return 1.0

    def chi(a, b):
        tot = a + b
        n1, n2 = a.sum(-1, keepdims=True), b.sum(-1, keepdims=True)
        N = n1 + n2
        e1 = tot * n1 / N
        e2 = tot * n2 / N
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.nansum((a - e1) ** 2 / np.where(e1 > 0, e1, 1) + (b - e2) ** 2 / np.where(e2 > 0, e2, 1), -1)

    obs = float(chi(c1[None], c2[None])[0])
    rng = np.random.default_rng(seed)
    labels = np.repeat(np.arange(len(c1)), (c1 + c2).astype(int))
    n1 = int(c1.sum())
    perms = np.argsort(rng.random((n_perm, labels.size)), axis=1)
    pl = labels[perms]
    a = np.stack([(pl[:, :n1] == k).sum(1) for k in range(len(c1))], 1).astype(float)
    b = np.stack([(pl[:, n1:] == k).sum(1) for k in range(len(c1))], 1).astype(float)
    null = chi(a, b)
    del K
    return float((1 + (null >= obs - 1e-12).sum()) / (1 + n_perm))


def pelt_cv(C: np.ndarray, label_lists: list[list[int]], K: int, seed: int = 0,
            pens: tuple = (1, 2, 4, 6, 8, 12, 16, 24, 32)) -> dict:
    """PELT with a custom multinomial cost; penalty chosen by 5-fold CV over continuations (held-out log-lik)."""
    import ruptures as rpt
    from ruptures.base import BaseCost

    class MultiCost(BaseCost):
        model = "multinomial"
        min_size = 1

        def fit(self, signal):
            self.cum = np.vstack([np.zeros((1, signal.shape[1])), np.cumsum(signal, 0)])
            return self

        def error(self, start, end):
            c = self.cum[end] - self.cum[start]
            return float(-2.0 * seg_loglik(c))

    rng = np.random.default_rng(seed)
    folds = [[rng.integers(0, 5, size=len(ll)) for ll in label_lists]]
    best_pen, best_ll = None, -np.inf
    npos = C.shape[0]
    for pen in pens:
        ll_tot = 0.0
        for f in range(5):
            tr = np.zeros((npos, K))
            te = []
            for j, ll in enumerate(label_lists):
                fo = folds[0][j]
                for lab, ff in zip(ll, fo):
                    if ff == f:
                        te.append((j, lab))
                    else:
                        tr[j, lab] += 1
            if tr.sum() == 0:
                continue
            algo = rpt.Pelt(custom_cost=MultiCost(), min_size=1, jump=1).fit(tr)
            bks = algo.predict(pen=pen)
            seg_of = np.zeros(npos, int)
            start = 0
            for si, e in enumerate(bks):
                seg_of[start:e] = si
                start = e
            seg_counts = {}
            for si in set(seg_of):
                seg_counts[si] = tr[seg_of == si].sum(0) + 0.5
            for j, lab in te:
                pc = seg_counts[seg_of[j]]
                ll_tot += np.log(pc[lab] / pc.sum())
        if ll_tot > best_ll:
            best_ll, best_pen = ll_tot, pen
    algo = rpt.Pelt(custom_cost=MultiCost(), min_size=1, jump=1).fit(C)
    bks = algo.predict(pen=best_pen)
    return {"penalty": best_pen, "breakpoints": [int(b) for b in bks[:-1]], "cv_loglik": float(best_ll)}
