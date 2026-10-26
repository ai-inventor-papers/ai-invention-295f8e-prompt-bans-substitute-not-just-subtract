"""Statistics helpers: Hill numbers, paraphrase-cluster bootstrap, permutation chi-square, JS divergence, kappa."""
from __future__ import annotations

import math

import numpy as np

from common import wilson  # noqa: F401  (re-exported)


def norm_label(lab: str | None, cats: list[str]) -> str | None:
    if lab is None:
        return None
    return lab if lab in cats else "other"


def hill(counts: np.ndarray) -> float:
    n = counts.sum()
    if n <= 0:
        return float("nan")
    p = counts[counts > 0] / n
    return float(math.exp(-(p * np.log(p)).sum()))


def js(p_counts: np.ndarray, q_counts: np.ndarray, smooth: float = 0.5) -> float:
    """Jensen-Shannon divergence (nats). smooth=0 gives the unsmoothed JS (finite: zero cells contribute 0)."""
    p = (p_counts + smooth) / (p_counts + smooth).sum()
    q = (q_counts + smooth) / (q_counts + smooth).sum()
    m = 0.5 * (p + q)

    def kl(a: np.ndarray) -> float:
        nz = a > 0
        return float((a[nz] * np.log(a[nz] / m[nz])).sum())
    return 0.5 * kl(p) + 0.5 * kl(q)


class ArmData:
    """Per-arm arrays: paraphrase id, sample id, label index (-1 = unparseable), correct flag."""

    def __init__(self, rows: list[dict], cats: list[str], label_key: str = "label"):
        self.cats = cats + ["other"]
        self.K = len(self.cats)
        idx = {c: i for i, c in enumerate(self.cats)}
        self.pid = np.array([r["paraphrase_id"] for r in rows], dtype=int)
        self.sid = np.array([r["sample_id"] for r in rows], dtype=int)
        labs = []
        for r in rows:
            lab = r.get(label_key)
            if not r.get("parse_ok") or lab is None:
                labs.append(-1)
            else:
                labs.append(idx[norm_label(lab, cats)])
        self.lab = np.array(labs, dtype=int)
        self.cor = np.array([bool(r.get("passed")) for r in rows], dtype=bool)
        self.n = len(rows)
        self.groups = {p: np.where(self.pid == p)[0] for p in np.unique(self.pid)} if self.n else {}

    def counts(self, idx: np.ndarray | None = None, correct_only: bool = True) -> np.ndarray:
        lab = self.lab if idx is None else self.lab[idx]
        cor = self.cor if idx is None else self.cor[idx]
        m = (lab >= 0) & (cor if correct_only else True)
        return np.bincount(lab[m], minlength=self.K)

    def resample_idx(self, rng: np.random.Generator, pids: np.ndarray) -> np.ndarray:
        parts = []
        for p in pids:
            g = self.groups.get(p)
            if g is None or len(g) == 0:
                continue
            parts.append(rng.choice(g, size=len(g), replace=True))
        return np.concatenate(parts) if parts else np.array([], dtype=int)


def boot_stat(arms: list[ArmData], fn, B: int = 2000, seed: int = 0, min_correct: int = 5) -> dict:
    """Paraphrase-cluster bootstrap; paraphrase ids are resampled JOINTLY across the given arms.
    fn(list of index arrays) -> float (nan allowed). Resamples where any arm has < min_correct correct samples are skipped."""
    rng = np.random.default_rng(seed)
    all_p = np.unique(np.concatenate([np.array(list(a.groups.keys())) for a in arms if a.n])) if arms else np.array([])
    vals, skipped = [], 0
    for _ in range(B):
        pids = rng.choice(all_p, size=len(all_p), replace=True)
        idxs = [a.resample_idx(rng, pids) for a in arms]
        if any(int((a.cor[ix] & (a.lab[ix] >= 0)).sum()) < min_correct for a, ix in zip(arms, idxs)):
            skipped += 1
            continue
        v = fn(idxs)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            skipped += 1
            continue
        vals.append(v)
    full = fn([np.arange(a.n) for a in arms])
    if not vals:
        return {"est": full, "lo": None, "hi": None, "n_boot": 0, "skipped": skipped}
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"est": full, "lo": float(lo), "hi": float(hi), "n_boot": len(vals), "skipped": skipped}


def perm_chi2(a_labels: np.ndarray, b_labels: np.ndarray, K: int, n_perm: int = 10000, seed: int = 0) -> dict:
    a_labels = a_labels[a_labels >= 0]
    b_labels = b_labels[b_labels >= 0]
    if len(a_labels) == 0 or len(b_labels) == 0:
        return {"chi2": None, "p": None, "n_a": int(len(a_labels)), "n_b": int(len(b_labels))}
    pooled = np.concatenate([a_labels, b_labels])
    na = len(a_labels)

    def chi2(arr: np.ndarray) -> float:
        ca = np.bincount(arr[:na], minlength=K).astype(float)
        cb = np.bincount(arr[na:], minlength=K).astype(float)
        tot = ca + cb
        keep = tot > 0
        ca, cb, tot = ca[keep], cb[keep], tot[keep]
        ea = tot * na / len(arr)
        eb = tot * (len(arr) - na) / len(arr)
        return float(((ca - ea) ** 2 / ea).sum() + ((cb - eb) ** 2 / eb).sum())

    obs = chi2(pooled)
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        if chi2(rng.permutation(pooled)) >= obs - 1e-12:
            ge += 1
    return {"chi2": obs, "p": (ge + 1) / (n_perm + 1), "n_a": int(na), "n_b": int(len(b_labels))}


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    cats = sorted(set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    M = np.zeros((len(cats), len(cats)))
    for x, y in zip(a, b):
        M[idx[x], idx[y]] += 1
    n = M.sum()
    po = np.trace(M) / n
    pe = (M.sum(0) * M.sum(1)).sum() / (n * n)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0
