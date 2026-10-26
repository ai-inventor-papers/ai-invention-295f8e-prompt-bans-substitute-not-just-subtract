"""NOV-T pre-registered analysis (frozen in COMMIT #1; amendments only as new commits before the data they govern).

Primary unit: behaviour clusters = complete-linkage clusters (scipy linkage 'complete', fcluster t = 0.05,
criterion 'distance') of the probe-valid programs' 2,000 next-city decisions under Hamming distance (ERR = -1 only
matches -1), so every cluster has minimum within-cluster agreement >= 0.95. Identical decision vectors are collapsed
first (their multiplicity is kept for the Shannon index and rarefaction).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

CORE_ARMS = ["T1.0", "T1.6", "DTB", "RPB"]
TEMP_ARMS = ["T1.0", "T1.6"]
SEEDS = [0, 1]
THRESH = 0.05


# ------------------------------------------------------------------ clustering
def unique_vectors(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(unique rows U, inverse index per row, multiplicity per unique row)."""
    if len(X) == 0:
        return X.reshape(0, X.shape[1] if X.ndim == 2 else 0), np.zeros(0, int), np.zeros(0, int)
    U, inv, cnt = np.unique(X, axis=0, return_inverse=True, return_counts=True)
    return U, inv.reshape(-1), cnt


def cluster_labels_unique(U: np.ndarray, t: float = THRESH) -> np.ndarray:
    """Complete-linkage flat clusters of unique decision vectors (labels 1..K)."""
    if len(U) == 0:
        return np.zeros(0, int)
    if len(U) == 1:
        return np.ones(1, int)
    Z = linkage(pdist(U, "hamming"), method="complete")
    return fcluster(Z, t=t, criterion="distance")


def cluster_programs(X: np.ndarray, t: float = THRESH) -> dict:
    """Cluster the rows of X (one decision vector per program). Returns per-program labels and the count."""
    U, inv, cnt = unique_vectors(X)
    lab_u = cluster_labels_unique(U, t)
    labels = lab_u[inv] if len(inv) else np.zeros(0, int)
    return {"n_programs": int(len(X)), "n_unique": int(len(U)), "n_clusters": int(len(set(lab_u.tolist()))),
            "labels": labels, "labels_unique": lab_u, "U": U, "mult": cnt}


def min_within_agreement(U: np.ndarray, lab: np.ndarray) -> float:
    """Exact property check: the minimum pairwise agreement inside every cluster (1.0 if all singletons)."""
    worst = 1.0
    for c in set(lab.tolist()):
        idx = np.where(lab == c)[0]
        if len(idx) < 2:
            continue
        d = pdist(U[idx], "hamming")
        worst = min(worst, 1.0 - float(d.max()))
    return worst


def shannon(labels: np.ndarray) -> float:
    if len(labels) == 0:
        return 0.0
    c = np.array(list(Counter(labels.tolist()).values()), dtype=float)
    p = c / c.sum()
    return float(-(p * np.log(p)).sum())


def rarefy(labels: np.ndarray, m: int, n_sub: int = 1000, seed: int = 0) -> dict:
    """Distinct clusters in random subsamples of m programs (labels from the arm-seed partition)."""
    n = len(labels)
    if m <= 0 or n == 0:
        return {"m": m, "mean": 0.0, "lo": 0.0, "hi": 0.0, "exact_mean": 0.0}
    m = min(m, n)
    rng = np.random.default_rng(seed)
    vals = np.array([len(set(labels[rng.choice(n, m, replace=False)].tolist())) for _ in range(n_sub)])
    cnt = Counter(labels.tolist())
    # exact expectation: sum over clusters of 1 - C(n - n_c, m)/C(n, m)
    lc = math.lgamma
    ex = 0.0
    for nc in cnt.values():
        if n - nc < m:
            ex += 1.0
        else:
            ex += 1.0 - math.exp(lc(n - nc + 1) - lc(n - nc - m + 1) - lc(n + 1) + lc(n - m + 1))
    return {"m": int(m), "mean": float(vals.mean()), "lo": float(np.percentile(vals, 2.5)),
            "hi": float(np.percentile(vals, 97.5)), "exact_mean": float(ex)}


def discovery_curve(call_idx: np.ndarray, labels: np.ndarray, n_calls: int) -> list[int]:
    """Distinct clusters among probe-valid programs with call index <= c, for c = 0..n_calls-1."""
    order = np.argsort(call_idx, kind="stable")
    seen, out, k = set(), [], 0
    ci = call_idx[order]
    lab = labels[order]
    for c in range(n_calls):
        while k < len(ci) and ci[k] <= c:
            seen.add(int(lab[k]))
            k += 1
        out.append(len(seen))
    return out


# ------------------------------------------------------------------ ratios and bootstrap
def pooled_ratio(c: dict, N: dict, a: str, b: str, seeds=SEEDS) -> float:
    num = sum(c[(a, s)] for s in seeds) / max(1, sum(N[(a, s)] for s in seeds))
    den = sum(c[(b, s)] for s in seeds) / max(1, sum(N[(b, s)] for s in seeds))
    return float(num / den) if den > 0 else float("inf")


def per_seed_ratio(c: dict, N: dict, a: str, b: str, s: int) -> float:
    den = c[(b, s)] / max(1, N[(b, s)])
    return float((c[(a, s)] / max(1, N[(a, s)])) / den) if den > 0 else float("inf")


def round_block_bootstrap(rounds_a: np.ndarray, labels_a: np.ndarray, calls_per_round_a: dict,
                          rounds_b: np.ndarray, labels_b: np.ndarray, calls_per_round_b: dict,
                          n_boot: int = 1000, seed: int = 0) -> dict:
    """Paired round-block bootstrap of r = (c_a/N_a)/(c_b/N_b): round indices resampled with replacement, shared
    by both arms of a seed; c = distinct cluster labels among the probe-valid programs of the drawn rounds."""
    all_rounds = sorted(set(calls_per_round_a) | set(calls_per_round_b))
    rng = np.random.default_rng(seed)
    by_a = defaultdict(set)
    by_b = defaultdict(set)
    for r, l in zip(rounds_a.tolist(), labels_a.tolist()):
        by_a[r].add(l)
    for r, l in zip(rounds_b.tolist(), labels_b.tolist()):
        by_b[r].add(l)
    vals = []
    R = np.array(all_rounds)
    for _ in range(n_boot):
        draw = rng.choice(R, len(R), replace=True)
        sa, sb = set(), set()
        na = nb = 0
        for r in draw.tolist():
            sa |= by_a.get(r, set())
            sb |= by_b.get(r, set())
            na += calls_per_round_a.get(r, 0)
            nb += calls_per_round_b.get(r, 0)
        if len(sb) == 0 or nb == 0 or na == 0:
            continue
        vals.append((len(sa) / na) / (len(sb) / nb))
    vals = np.array(vals)
    if len(vals) == 0:
        return {"lo": None, "hi": None, "median": None, "n": 0}
    return {"lo": float(np.percentile(vals, 2.5)), "hi": float(np.percentile(vals, 97.5)),
            "median": float(np.median(vals)), "n": int(len(vals))}


def paired_bootstrap_diff(a: np.ndarray, b: np.ndarray, n_boot: int = 10000, seed: int = 0) -> dict:
    """Paired per-instance bootstrap of mean(a - b) (gap points)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (n_boot, len(d)))
    m = d[idx].mean(axis=1)
    return {"mean_diff": float(d.mean()), "lo": float(np.percentile(m, 2.5)), "hi": float(np.percentile(m, 97.5)),
            "n": int(len(d))}


# ------------------------------------------------------------------ verdicts
def verdict_v1(g200: dict, g200_nn: float, arms=CORE_ARMS, seeds=SEEDS) -> dict:
    """g200[(arm, seed)] = held-out n-200 mean gap of that arm-seed's selection-best program."""
    bar = 0.8 * g200_nn
    keys = [(a, s) for a in arms for s in seeds if (a, s) in g200 and g200[(a, s)] is not None]
    missing = [(a, s) for a in arms for s in seeds if (a, s) not in keys]
    failing = [f"{a}|{s}" for a, s in keys if not g200[(a, s)] <= bar]
    if not missing and not failing:
        v = "SUPPORTED"
    elif not any(g200[k] < g200_nn for k in keys):
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    return {"verdict": v, "bar_0.8xNN": bar, "G200_NN": g200_nn, "failing": failing,
            "missing": [f"{a}|{s}" for a, s in missing],
            "per_arm_seed": {f"{a}|{s}": g200[(a, s)] for a, s in keys}}


def verdict_v2(c: dict, N: dict, g200: dict, seeds=SEEDS) -> dict:
    """c[(arm, seed)] primary cluster counts, N[(arm, seed)] calls, g200[(arm, seed)] held-out best."""
    R = {x: pooled_ratio(c, N, "DTB", x, seeds) for x in ("T1.0", "T1.6", "RPB")}
    r = {f"{x}|{s}": per_seed_ratio(c, N, "DTB", x, s) for x in ("T1.0", "T1.6", "RPB") for s in seeds}

    def mean_g(arm):
        v = [g200.get((arm, s)) for s in seeds]
        return float(np.mean(v)) if all(x is not None for x in v) else None

    gd, gt = mean_g("DTB"), [mean_g(x) for x in TEMP_ARMS]
    heldout_ok = gd is not None and all(x is not None for x in gt) and gd <= min(gt)
    c1 = R["T1.0"] >= 1.5 and R["T1.6"] >= 1.5
    c2 = all(r[f"{x}|{s}"] > 1 for x in TEMP_ARMS for s in seeds)
    c3 = R["RPB"] >= 1.2
    if c1 and c2 and c3 and heldout_ok:
        v, branches = "SUPPORTED", []
    elif R["T1.0"] <= 1.0 or R["T1.6"] <= 1.0:
        v, branches = "DISCONFIRMED", []
    else:
        v, branches = "PARTIAL", []
        if not heldout_ok:
            branches.append("clusters but worse held-out best")
        if sum(R[x] >= 1.5 for x in TEMP_ARMS) == 1:
            branches.append("one comparator only")
        if not c2 and any(all(r[f"{x}|{s}"] > 1 for x in TEMP_ARMS) for s in seeds):
            branches.append("one seed only")
        if not c3:
            branches.append("not position-specific")
        if not branches:
            branches.append("ratios between 1.0 and 1.5")
    return {"verdict": v, "branches": branches, "R": R, "r": r, "criteria": {
        "R_temp_ge_1.5": c1, "per_seed_gt_1": c2, "R_RPB_ge_1.2": c3, "heldout_DTB_le_temp": heldout_ok},
        "mean_G200": {"DTB": gd, "T1.0": gt[0], "T1.6": gt[1]}}


def best_program(rows: list[dict]) -> dict | None:
    """Minimum F among PROBE-VALID programs (ties to the earliest call), chosen without held-out data."""
    pv = [r for r in rows if r.get("probe_valid") and r.get("F") is not None]
    if not pv:
        return None
    return min(pv, key=lambda r: (r["F"], r["call_idx"]))
