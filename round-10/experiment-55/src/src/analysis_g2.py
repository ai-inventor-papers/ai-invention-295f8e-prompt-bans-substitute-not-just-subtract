#!/usr/bin/env python3
"""FROZEN analysis for TP-G2 (sha256 in COMMIT #1). G1: does the program map's cell geometry follow expansion
DISCIPLINE once frontier CONTAINER (code surface) is held fixed? G2: where do the survivor families and the covert
BFS/DFS programs land when placed alone on the frozen graph, judged by mechanism (measured discipline) vs surface?

Geometry primitives are iteration 9's geometry.py (knn_graph / geodesics / class_matrix / g_values / classify /
classical_mds / stress1) and landing.py, unchanged. Placement is E46's frozen out-of-sample rule
d(x, j) = min over x's k nearest frame points i of (||x - i|| + geo(i, j)).

G1 statistics (cells with >= 10 accepted factorial programs, PROBE excluded):
  D       cell RDM = mean geodesic between the programs of two cells (iteration 9's class_matrix), upper triangle
  D_disc  1[discipline differs]; D_cont 1[container differs]; D_surf mean pairwise AST 4-gram Jaccard distance;
  D_len   |difference of mean code-token count|; D_disp |difference of within-cell mean geodesic|
  rho_d = partial Spearman(D, D_disc | D_cont), rho_c = partial Spearman(D, D_cont | D_disc) (ranks, residualised);
  *_full additionally control D_surf, D_len, D_disp; Kendall tau-a zero-order fits.
  Inference: B bootstrap resamples of programs within cells (graph rebuilt each time); restricted permutations
  (discipline labels permuted among the cells WITHIN each container for rho_d; container labels within discipline
  for rho_c; exact enumeration when the count is <= 100,000, else 10,000 sampled, seed 0); Holm over the 2 models.
  Noise ceiling: 100 split-halves within cells, Spearman of the half RDMs, Spearman-Brown corrected.
VERDICT (per model): SUPPORTED if rho_d >= 0.3, Holm p < 0.05 and P_boot(rho_d > rho_c) >= 0.95; DISCONFIRMED if
rho_d <= 0.1 on BOTH models; INTERMEDIATE otherwise; FRAGILE if the full-control or cross-validated result flips it.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np
from scipy.stats import binomtest, rankdata, spearmanr

import geometry

THRESH_SUPPORT, THRESH_DISCONF = 0.3, 0.1
N_PERM_SAMPLE, PERM_EXACT_MAX = 10000, 100000


# ---------------------------------------------------------------------------------------------- RSA primitives
def upper(M: np.ndarray) -> np.ndarray:
    return M[np.triu_indices(len(M), 1)]


def _resid(y: np.ndarray, A: np.ndarray) -> np.ndarray:
    return y - A @ np.linalg.lstsq(A, y, rcond=None)[0]


def partial_spearman(y: np.ndarray, x: np.ndarray, controls: list[np.ndarray]) -> float:
    ry, rx = rankdata(y), rankdata(x)
    A = np.column_stack([np.ones(len(ry))] + [rankdata(c) for c in controls])
    ey, ex = _resid(ry, A), _resid(rx, A)
    den = math.sqrt(float((ey ** 2).sum() * (ex ** 2).sum()))
    return float((ey * ex).sum() / den) if den > 0 else float("nan")


def kendall_tau_a(x: np.ndarray, y: np.ndarray) -> float:
    n = len(x)
    s = 0.0
    for i in range(n - 1):
        s += float((np.sign(x[i + 1:] - x[i]) * np.sign(y[i + 1:] - y[i])).sum())
    return s / (n * (n - 1) / 2) if n > 1 else float("nan")


def cell_model_rdms(cells: list[str], disc: dict[str, str], cont: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    n = len(cells)
    Dd = np.array([[float(disc[cells[i]] != disc[cells[j]]) for j in range(n)] for i in range(n)])
    Dc = np.array([[float(cont[cells[i]] != cont[cells[j]]) for j in range(n)] for i in range(n)])
    return Dd, Dc


def surface_cell_rdm(J: np.ndarray, groups: list[np.ndarray]) -> np.ndarray:
    """J = program x program AST 4-gram Jaccard DISTANCE; groups = program indices per cell."""
    n = len(groups)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            M[i, j] = M[j, i] = float(J[np.ix_(groups[i], groups[j])].mean())
    return M


def len_cell_rdm(lens: np.ndarray, groups: list[np.ndarray]) -> np.ndarray:
    m = np.array([lens[g].mean() for g in groups])
    return np.abs(m[:, None] - m[None, :])


def cell_rdm_from_geo(geo: np.ndarray, labels: np.ndarray, cells: list[str]) -> tuple[np.ndarray, np.ndarray]:
    M = geometry.class_matrix(geo, labels, cells)
    diag = np.diag(M).copy()
    return M, diag


def stats_from(D: np.ndarray, Dd: np.ndarray, Dc: np.ndarray, Ds: np.ndarray, Dl: np.ndarray, Dp: np.ndarray
               ) -> dict[str, float]:
    y, d, c, s, ln, p = upper(D), upper(Dd), upper(Dc), upper(Ds), upper(Dl), upper(Dp)
    return {"rho_d": partial_spearman(y, d, [c]), "rho_c": partial_spearman(y, c, [d]),
            "rho_d_full": partial_spearman(y, d, [c, s, ln, p]), "rho_c_full": partial_spearman(y, c, [d, s, ln, p]),
            "rho_surf_partial": partial_spearman(y, s, [d, c, ln, p])}


# ---------------------------------------------------------------------------------------------- permutations
def restricted_label_perms(cells: list[str], fixed: dict[str, str], moving: dict[str, str], seed: int = 0
                           ) -> tuple[np.ndarray, bool, int]:
    """All assignments of the `moving` labels obtained by permuting them among the cells that share the same `fixed`
    label (e.g. disciplines permuted within container). Returns (array [P, n_cells] of label ids, exact?, total)."""
    labs = sorted(set(moving.values()))
    lid = {l: i for i, l in enumerate(labs)}
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(cells):
        groups.setdefault(fixed[c], []).append(i)
    gl = list(groups.values())
    total = 1
    for g in gl:
        total *= math.factorial(len(g))
    base = np.array([lid[moving[c]] for c in cells])
    if total <= PERM_EXACT_MAX:
        per = [list(itertools.permutations(g)) for g in gl]
        out = np.empty((total, len(cells)), dtype=np.int16)
        for k, combo in enumerate(itertools.product(*per)):
            row = base.copy()
            for g, pg in zip(gl, combo):
                row[g] = base[list(pg)]
            out[k] = row
        return out, True, total
    rng = np.random.default_rng(seed)
    out = np.empty((N_PERM_SAMPLE, len(cells)), dtype=np.int16)
    for k in range(N_PERM_SAMPLE):
        row = base.copy()
        for g in gl:
            row[g] = base[rng.permutation(g)]
        out[k] = row
    return out, False, total


def perm_partial(y: np.ndarray, perm_labels: np.ndarray, controls: list[np.ndarray], n_cells: int) -> np.ndarray:
    """Partial Spearman of y with 1[label_i != label_j] for every permuted labelling (vectorised)."""
    iu = np.triu_indices(n_cells, 1)
    X = (perm_labels[:, iu[0]] != perm_labels[:, iu[1]]).astype(np.float64)         # [P, m]
    m = X.shape[1]
    n1 = X.sum(1, keepdims=True)
    n0 = m - n1
    R = np.where(X > 0, n0 + (n1 + 1) / 2.0, (n0 + 1) / 2.0)                           # average ranks of a binary
    A = np.column_stack([np.ones(m)] + [rankdata(c) for c in controls])
    H = A @ np.linalg.pinv(A)
    ey = rankdata(y) - H @ rankdata(y)
    ER = R - R @ H.T
    num = ER @ ey
    den = np.sqrt((ER ** 2).sum(1) * (ey ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def perm_p(obs: float, null: np.ndarray) -> dict[str, float]:
    null = null[np.isfinite(null)]
    return {"p_greater": float(np.mean(null >= obs - 1e-12)), "p_two_sided": float(np.mean(np.abs(null) >= abs(obs) - 1e-12)),
            "null_q": np.quantile(null, [0.025, 0.5, 0.95, 0.975]).tolist() if len(null) else None, "n": int(len(null))}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


# ---------------------------------------------------------------------------------------------- distances
def geo_rdm(X: np.ndarray, labels: np.ndarray, cells: list[str], k: int) -> tuple[np.ndarray, np.ndarray, dict]:
    geo, info = geometry.geodesics(X, k)
    M, diag = cell_rdm_from_geo(geo, labels, cells)
    return M, diag, {**info, "geo": geo}


def euclid_centroid_rdm(X: np.ndarray, labels: np.ndarray, cells: list[str]) -> np.ndarray:
    C = np.stack([X[labels == c].mean(0) for c in cells])
    return np.sqrt(((C[:, None] - C[None]) ** 2).sum(-1))


def crossval_centroid_rdm(X: np.ndarray, labels: np.ndarray, cells: list[str], n_split: int = 100, seed: int = 0
                          ) -> np.ndarray:
    """Split-half cross-validated squared Euclidean distance between cell means (unbiased: E = 0 under no difference)."""
    rng = np.random.default_rng(seed)
    n = len(cells)
    acc = np.zeros((n, n))
    idx = [np.where(labels == c)[0] for c in cells]
    for _ in range(n_split):
        A, B = [], []
        for g in idx:
            p = rng.permutation(g)
            h = len(p) // 2
            A.append(X[p[:h]].mean(0))
            B.append(X[p[h:2 * h]].mean(0))
        A, B = np.stack(A), np.stack(B)
        dA = A[:, None] - A[None]
        dB = B[:, None] - B[None]
        acc += (dA * dB).sum(-1)
    return acc / n_split


# ---------------------------------------------------------------------------------------------- G1 core
def g1_point(X: np.ndarray, labels: np.ndarray, cells: list[str], disc: dict[str, str], cont: dict[str, str],
             J: np.ndarray, lens: np.ndarray, k: int) -> dict[str, Any]:
    groups = [np.where(labels == c)[0] for c in cells]
    D, diag, info = geo_rdm(X, labels, cells, k)
    Dd, Dc = cell_model_rdms(cells, disc, cont)
    Ds = surface_cell_rdm(J, groups)
    Dl = len_cell_rdm(lens, groups)
    Dp = np.abs(diag[:, None] - diag[None, :])
    st = stats_from(D, Dd, Dc, Ds, Dl, Dp)
    tau = {nm: kendall_tau_a(upper(M), upper(D)) for nm, M in (("disc", Dd), ("cont", Dc), ("surf", Ds), ("len", Dl),
                                                              ("disp", Dp))}
    return {**st, "tau_a": tau, "D": D, "Dd": Dd, "Dc": Dc, "Ds": Ds, "Dl": Dl, "Dp": Dp,
            "graph": {kk: v for kk, v in info.items() if kk != "geo"}, "geo": info["geo"]}


def boot_indices(labels: np.ndarray, cells: list[str], rng: np.random.Generator) -> np.ndarray:
    out = []
    for c in cells:
        g = np.where(labels == c)[0]
        out.append(rng.choice(g, size=len(g), replace=True))
    return np.concatenate(out)


def g1_boot_chunk(args: tuple) -> list[dict[str, float]]:
    (reps, cells, disc, cont, labels, J, lens, k, seeds) = args
    res = []
    for s in seeds:
        rng = np.random.default_rng(s)
        idx = boot_indices(labels, cells, rng)
        lab = labels[idx]
        groups = [np.where(lab == c)[0] for c in cells]
        Jb = J[np.ix_(idx, idx)]
        Ds = surface_cell_rdm(Jb, groups)
        Dl = len_cell_rdm(lens[idx], groups)
        Dd, Dc = cell_model_rdms(cells, disc, cont)
        row = {"seed": int(s)}
        for name, X in reps.items():
            D, diag, _ = geo_rdm(X[idx], lab, cells, k)
            Dp = np.abs(diag[:, None] - diag[None, :])
            st = stats_from(D, Dd, Dc, Ds, Dl, Dp)
            for kk, v in st.items():
                row[f"{name}:{kk}"] = v
        res.append(row)
    return res


def noise_ceiling(X: np.ndarray, labels: np.ndarray, cells: list[str], k: int, n_split: int = 100, seed: int = 0
                  ) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rs = []
    for _ in range(n_split):
        A, B = [], []
        for c in cells:
            g = rng.permutation(np.where(labels == c)[0])
            h = len(g) // 2
            A += list(g[:h])
            B += list(g[h:])
        A, B = np.array(A), np.array(B)
        DA, _, _ = geo_rdm(X[A], labels[A], cells, k)
        DB, _, _ = geo_rdm(X[B], labels[B], cells, k)
        rs.append(spearmanr(upper(DA), upper(DB)).statistic)
    r = float(np.nanmean(rs))
    sb = 2 * r / (1 + r) if r > -1 else float("nan")
    return {"split_half_spearman_mean": r, "spearman_brown": sb,
            "ceiling_sqrt": float(math.sqrt(sb)) if sb > 0 else 0.0, "n_split": n_split,
            "split_half_q": np.quantile(rs, [0.025, 0.5, 0.975]).tolist()}


def commonality(D: np.ndarray, Dd: np.ndarray, Dc: np.ndarray, Ds: np.ndarray, Dl: np.ndarray) -> dict[str, float]:
    y = rankdata(upper(D))
    preds = {"disc": [rankdata(upper(Dd))], "cont": [rankdata(upper(Dc))],
             "surf_len": [rankdata(upper(Ds)), rankdata(upper(Dl))]}

    def r2(keys: tuple[str, ...]) -> float:
        cols = [np.ones(len(y))] + [c for kk in keys for c in preds[kk]]
        A = np.column_stack(cols)
        e = _resid(y, A)
        return float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum())

    full = r2(("disc", "cont", "surf_len"))
    uniq = {kk: full - r2(tuple(x for x in preds if x != kk)) for kk in preds}
    return {"R2_full": full, **{f"unique_{kk}": v for kk, v in uniq.items()},
            "shared": full - sum(uniq.values()), "R2_disc_only": r2(("disc",)), "R2_cont_only": r2(("cont",)),
            "R2_surf_len_only": r2(("surf_len",))}


def verdict_g1(rho_d: float, p_holm: float, p_boot_gt: float) -> str:
    if rho_d >= THRESH_SUPPORT and p_holm < 0.05 and p_boot_gt >= 0.95:
        return "SUPPORTED"
    if rho_d <= THRESH_DISCONF:
        return "LOW (<= 0.1)"
    return "INTERMEDIATE"


# ---------------------------------------------------------------------------------------------- G2 placement
def oos(x: np.ndarray, F: np.ndarray, geo: np.ndarray, k: int) -> np.ndarray:
    """E46 frozen rule: d(x, j) = min_{i in kNN(x)} ||x - i|| + geo(i, j)."""
    d = np.linalg.norm(F - x, axis=1)
    nn = np.argsort(d)[:k]
    return np.min(d[nn][:, None] + geo[nn], axis=0)


def class_of(gx: float, med: float) -> str:
    return "EDGE" if gx < med - 1e-12 else ("OPPOSITE" if gx > med + 1e-12 else "MIDDLE")


def g_mech_ref(geo: np.ndarray, groups: dict[str, np.ndarray], disc_sets: dict[str, np.ndarray],
               refs: list[str]) -> dict[str, float]:
    """g_mech of a reference class = min over banned disciplines of the mean in-frame geodesic between the class's
    programs and that discipline's programs (excluding the class's own programs)."""
    out = {}
    for r in refs:
        a = groups[r]
        vals = []
        for dname, b in disc_sets.items():
            b2 = np.setdiff1d(b, a)
            if len(b2):
                vals.append(float(geo[np.ix_(a, b2)].mean()))
        out[r] = min(vals) if vals else float("nan")
    return out


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def binom_p(k: int, n: int, p0: float) -> float:
    return float(binomtest(k, n, p0, alternative="greater").pvalue) if n > 0 else float("nan")


def mds_embed(D: np.ndarray) -> tuple[np.ndarray, float]:
    Y = geometry.classical_mds(D)
    return Y, geometry.stress1(D, Y)
