#!/usr/bin/env python3
"""replay.pick(z, u, T, k): an independent float64 numpy re-implementation of the engine's per-step transform
(engine5.step_probs5 + engine_v4._inverse_cdf):
    p = softmax(z / T)                          (float64; z = the bf16 logits widened to float64)
    top-k: p[p < k-th largest p] = 0             (ties at the k-th value kept, exactly as the engine)
    cdf = cumsum(p) in TOKEN-ID order; cdf /= cdf[-1]
    token = first index with cdf >= u            (torch.searchsorted, right=False), clamped to V - 1
The token-id order makes the coupling across temperatures exact in marginals but NOT monotone in T, so per-slot
predictions must use pick(), never a sorted CDF.
"""

from __future__ import annotations

import numpy as np


def probs(z: np.ndarray, T: float, k: int = 0) -> np.ndarray:
    x = np.asarray(z, dtype=np.float64) / float(T)
    x = x - x.max()
    p = np.exp(x)
    p /= p.sum()
    if k and k > 0:
        kth = np.partition(p, -k)[-k]
        p = np.where(p < kth, 0.0, p)
    return p


def pick(z: np.ndarray, u: float, T: float, k: int = 0) -> int:
    p = probs(z, T, k)
    cdf = np.cumsum(p)
    cdf = cdf / cdf[-1]
    t = int(np.searchsorted(cdf, u, side="left"))
    return min(t, len(p) - 1)


def dist(z: np.ndarray, T: float, k: int = 0) -> np.ndarray:
    """The normalised sampling distribution of one step (kept mass renormalised)."""
    p = probs(z, T, k)
    return p / p.sum()
