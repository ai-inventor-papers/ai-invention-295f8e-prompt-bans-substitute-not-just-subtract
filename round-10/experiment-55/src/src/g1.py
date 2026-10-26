#!/usr/bin/env python3
"""G1 (plan Stage 4, frozen in COMMIT1c): does the program-state RDM track expansion discipline once storage
container is held fixed?

RDMs over program pairs i<j: D_S = 1 - cos(S_i, S_j); D_disc = 0 same discipline, 0.5 for {BFSO, COST}, 1 otherwise;
D_cont = 0 same container, 1 otherwise; D_surf = 1 - Jaccard of Python-tokenize NAME/OP/NUMBER token sets; D_len =
|n_code_tokens_i - n_code_tokens_j|; D_ctx = 0 same context variant, 1 otherwise.
rho_dc = partial Spearman(D_S, D_disc | D_cont): average ranks, both ranked vectors residualised on [1, rank(D_cont)]
by OLS, Pearson of the residuals; rho_cd the reverse; delta = rho_dc - rho_cd.
Inference: program bootstrap (1,000; pairs rebuilt; self-copy pairs dropped; percentile CI); restricted permutations
(2,000): discipline labels permuted within container strata (rho_dc), container labels within discipline strata
(rho_cd); p = (1 + #{perm >= obs}) / (1 + N)."""

from __future__ import annotations

import io
import math
import tokenize
from typing import Any

import numpy as np
from scipy.stats import kendalltau, rankdata

DISC_HALF = {frozenset(("BFSO", "COST"))}


# ---------------------------------------------------------------------------------------------- RDMs
def d_state(S: np.ndarray) -> np.ndarray:
    X = S.astype(np.float64)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    return 1.0 - X @ X.T


def d_labels(lab: list[str], half: set[frozenset] | None = None) -> np.ndarray:
    n = len(lab)
    D = np.ones((n, n))
    a = np.array(lab)
    D[a[:, None] == a[None, :]] = 0.0
    for pair in (half or set()):
        x, y = tuple(pair)
        D[(a[:, None] == x) & (a[None, :] == y)] = 0.5
        D[(a[:, None] == y) & (a[None, :] == x)] = 0.5
    return D


def d_disc(disc: list[str], heur_split: list[str] | None = None, merge_cost: bool = False) -> np.ndarray:
    lab = ["BFSO" if (merge_cost and d == "COST") else d for d in disc]
    D = d_labels(lab, None if merge_cost else DISC_HALF)
    if heur_split is not None:
        a = np.array(lab)
        hk = np.array([h or "" for h in heur_split])
        both = (a[:, None] == "HEUR") & (a[None, :] == "HEUR") & (hk[:, None] != hk[None, :])
        D[both] = 0.5
    return D


def d_cont(cont: list[str], graded: bool = False) -> np.ndarray:
    return d_labels(cont, {frozenset(("DEQUE", "LIST"))} if graded else None)


def token_set(code: str) -> set[str]:
    out = set()
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type in (tokenize.NAME, tokenize.OP, tokenize.NUMBER):
                out.add(t.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def d_jaccard(sets: list[set[str]], weights: dict[str, float] | None = None) -> np.ndarray:
    n = len(sets)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = sets[i], sets[j]
            if weights is None:
                inter, uni = len(a & b), len(a | b)
            else:
                inter = sum(weights.get(t, 1.0) for t in a & b)
                uni = sum(weights.get(t, 1.0) for t in a | b)
            D[i, j] = D[j, i] = 1.0 - (inter / uni if uni else 1.0)
    return D


def ast_ngrams(code: str, n: int = 4) -> set[tuple[str, ...]]:
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    seq = [type(x).__name__ for x in ast.walk(tree)]
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def d_len(n_tok: list[int]) -> np.ndarray:
    a = np.array(n_tok, dtype=float)
    return np.abs(a[:, None] - a[None, :])


# ---------------------------------------------------------------------------------------------- statistics
def _resid(r: np.ndarray, Z: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(Z, r, rcond=None)
    return r - Z @ beta


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b) / den if den > 0 else float("nan")


def partial_spearman(y: np.ndarray, x: np.ndarray, z: np.ndarray | list[np.ndarray]) -> float:
    zs = z if isinstance(z, list) else [z]
    Z = np.column_stack([np.ones(len(y))] + [rankdata(v) for v in zs])
    return _pearson(_resid(rankdata(y), Z), _resid(rankdata(x), Z))


def spearman(y: np.ndarray, x: np.ndarray) -> float:
    return _pearson(rankdata(y), rankdata(x))


def tau_a(y: np.ndarray, x: np.ndarray) -> float:
    """Kendall tau-a from scipy's tau-b and the tie counts."""
    tb = kendalltau(x, y).statistic
    n0 = len(x) * (len(x) - 1) / 2

    def ties(v: np.ndarray) -> float:
        _, c = np.unique(v, return_counts=True)
        return float((c * (c - 1) / 2).sum())

    n1, n2 = ties(x), ties(y)
    return float(tb * math.sqrt((n0 - n1) * (n0 - n2)) / n0) if n0 > 0 else float("nan")


def rank_regression(y: np.ndarray, X: dict[str, np.ndarray]) -> dict[str, Any]:
    names = list(X)
    ry = rankdata(y)
    R = np.column_stack([rankdata(X[k]) for k in names])
    zy = (ry - ry.mean()) / ry.std()
    Zx = (R - R.mean(0)) / np.where(R.std(0) > 0, R.std(0), 1.0)
    A = np.column_stack([np.ones(len(zy)), Zx])
    beta, *_ = np.linalg.lstsq(A, zy, rcond=None)
    pred = A @ beta
    r2 = 1 - float(((zy - pred) ** 2).sum() / ((zy - zy.mean()) ** 2).sum())
    semi = {}
    for i, k in enumerate(names):
        others = np.column_stack([np.ones(len(zy))] + [Zx[:, j] for j in range(len(names)) if j != i])
        rx = _resid(Zx[:, i], others)
        semi[k] = _pearson(zy, rx)
    return {"std_beta": {k: float(beta[i + 1]) for i, k in enumerate(names)}, "semi_partial": semi, "r2": r2}


def upper(M: np.ndarray) -> np.ndarray:
    return M[np.triu_indices(len(M), 1)]


def core_stats(DS: np.ndarray, DD: np.ndarray, DC: np.ndarray) -> dict[str, float]:
    y, x, z = upper(DS), upper(DD), upper(DC)
    rdc = partial_spearman(y, x, z)
    rcd = partial_spearman(y, z, x)
    return {"rho_dc": rdc, "rho_cd": rcd, "delta": rdc - rcd, "spearman_disc": spearman(y, x),
            "spearman_cont": spearman(y, z)}


def boot_pairs(n: int, rng: np.random.Generator, groups: np.ndarray | None = None) -> np.ndarray:
    if groups is None:
        return rng.choice(n, size=n, replace=True)
    ug = np.unique(groups)
    pick = rng.choice(ug, size=len(ug), replace=True)
    return np.concatenate([np.where(groups == g)[0] for g in pick])


def stats_on_index(DS: np.ndarray, DD: np.ndarray, DC: np.ndarray, idx: np.ndarray) -> dict[str, float]:
    iu = np.triu_indices(len(idx), 1)
    a, b = idx[iu[0]], idx[iu[1]]
    keep = a != b                                        # copies of the same program are not a pair
    a, b = a[keep], b[keep]
    y, x, z = DS[a, b], DD[a, b], DC[a, b]
    rdc = partial_spearman(y, x, z)
    rcd = partial_spearman(y, z, x)
    return {"rho_dc": rdc, "rho_cd": rcd, "delta": rdc - rcd}


def bootstrap(DS: np.ndarray, DD: np.ndarray, DC: np.ndarray, n_boot: int = 1000, seed: int = 0,
              groups: np.ndarray | None = None) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    vals = {"rho_dc": [], "rho_cd": [], "delta": []}
    for _ in range(n_boot):
        idx = boot_pairs(len(DS), rng, groups)
        s = stats_on_index(DS, DD, DC, idx)
        for k in vals:
            vals[k].append(s[k])
    out = {}
    for k, v in vals.items():
        a = np.array([x for x in v if np.isfinite(x)])
        out[k] = {"ci95": [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))], "sd": float(a.std()),
                  "n": int(len(a))}
    return out


def restricted_perm(DS: np.ndarray, labels_perm: list[str], labels_fixed: list[str], obs: float,
                    make_D: Any, D_fixed: np.ndarray, n_perm: int = 2000, seed: int = 0) -> dict[str, Any]:
    """Permute labels_perm within strata of labels_fixed; statistic = partial Spearman(D_S, make_D(perm) | D_fixed)."""
    rng = np.random.default_rng(seed)
    lp = np.array(labels_perm, dtype=object)
    lf = np.array(labels_fixed)
    strata = [np.where(lf == s)[0] for s in np.unique(lf)]
    y, z = upper(DS), upper(D_fixed)
    Z = np.column_stack([np.ones(len(y)), rankdata(z)])
    ry = _resid(rankdata(y), Z)
    null = []
    for _ in range(n_perm):
        perm = lp.copy()
        for idx in strata:
            perm[idx] = lp[rng.permutation(idx)]
        x = upper(make_D(list(perm)))
        null.append(_pearson(ry, _resid(rankdata(x), Z)))
    null = np.array(null)
    return {"p": float((1 + np.sum(null >= obs - 1e-12)) / (1 + n_perm)), "null_mean": float(null.mean()),
            "null_q95": float(np.quantile(null, 0.95)), "n_perm": n_perm}


def corr_design(DD: np.ndarray, DC: np.ndarray) -> dict[str, float]:
    x, z = upper(DD), upper(DC)
    r = float(np.corrcoef(x, z)[0, 1])
    return {"corr_Ddisc_Dcont": r, "vif": float(1.0 / max(1e-12, 1 - r * r))}


def full_g1(S: np.ndarray, disc: list[str], cont: list[str], n_boot: int = 1000, n_perm: int = 2000,
            seed: int = 0, cell_groups: np.ndarray | None = None) -> dict[str, Any]:
    DS = d_state(S)
    DD, DC = d_disc(disc), d_cont(cont)
    obs = core_stats(DS, DD, DC)
    out: dict[str, Any] = {"n_programs": len(S), "n_pairs": int(len(S) * (len(S) - 1) / 2), **obs,
                           **corr_design(DD, DC)}
    out["bootstrap"] = bootstrap(DS, DD, DC, n_boot, seed)
    out["perm_rho_dc"] = restricted_perm(DS, disc, cont, obs["rho_dc"], d_disc, DC, n_perm, seed + 1)
    out["perm_rho_cd"] = restricted_perm(DS, cont, disc, obs["rho_cd"], d_cont, DD, n_perm, seed + 2)
    if cell_groups is not None:
        out["cell_cluster_bootstrap"] = bootstrap(DS, DD, DC, n_boot, seed + 3, groups=cell_groups)
    return out


def verdict(per_model: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sup = [m for m, r in per_model.items() if r["rho_dc"] >= 0.30 and r["bootstrap"]["delta"]["ci95"][0] > 0]
    dis = all(r["rho_dc"] <= 0.10 for r in per_model.values())
    if sup:
        v = "SUPPORTED"
        why = f"rho_dc >= 0.30 and delta CI > 0 on {sup}"
    elif dis:
        v = "DISCONFIRMED"
        why = "rho_dc <= 0.10 on " + ", ".join(per_model)
    else:
        v = "INDETERMINATE"
        fails = {m: [c for c, ok in (("rho_dc >= 0.30", r["rho_dc"] >= 0.30),
                                    ("delta CI > 0", r["bootstrap"]["delta"]["ci95"][0] > 0)) if not ok]
                 for m, r in per_model.items()}
        why = f"failed conditions: {fails}"
    return {"verdict": v, "why": why, "models": list(per_model), "restricted_to_8b": list(per_model) == ["8b"]}


# ---------------------------------------------------------------------------------------------- synthetic tests (T7)
def synthetic_states(disc: list[str], cont: list[str], mode: str, seed: int, dim: int = 64,
                     noise: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    D = sorted(set(disc))
    C = sorted(set(cont))
    md = {d: rng.normal(size=dim) * 2.0 for d in D}
    if "BFSO" in md and "COST" in md:          # the hypothesised geometry: COST sits half-way from BFSO
        md["COST"] = md["BFSO"] + 0.5 * (md["COST"] - md["BFSO"])
    mc = {c: rng.normal(size=dim) * 2.0 for c in C}
    base = rng.normal(size=dim) * 5
    X = []
    for d, c in zip(disc, cont):
        v = base.copy()
        if mode in ("disc", "both"):
            v += md[d]
        if mode in ("cont", "both"):
            v += mc[c]
        if mode == "surface":
            v += rng.normal(size=dim) * 2.0
        X.append(v + noise * rng.normal(size=dim))
    return np.array(X)


def t7(disc: list[str], cont: list[str], n_null: int = 200, seed: int = 0) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mode in ("disc", "cont", "surface"):
        S = synthetic_states(disc, cont, mode, seed, noise=0.6)
        DS, DD, DC = d_state(S), d_disc(disc), d_cont(cont)
        out[mode] = core_stats(DS, DD, DC)
    rej, cover = 0, 0
    for s in range(n_null):
        S = synthetic_states(disc, cont, "noise", seed + 100 + s)
        DS, DD, DC = d_state(S), d_disc(disc), d_cont(cont)
        obs = core_stats(DS, DD, DC)
        pr = restricted_perm(DS, disc, cont, obs["rho_dc"], d_disc, DC, n_perm=199, seed=s)
        rej += int(pr["p"] < 0.05)
        bs = bootstrap(DS, DD, DC, n_boot=100, seed=s)
        lo, hi = bs["rho_dc"]["ci95"]
        cover += int(lo <= 0 <= hi)
    out["null"] = {"n_sim": n_null, "rejection_rate_p_lt_0.05": rej / n_null, "bootstrap_ci_covers_0": cover / n_null,
                   "pass_rate_band": abs(rej / n_null - 0.05) <= 0.03}
    out["pass"] = (out["disc"]["rho_dc"] > 0.5 and abs(out["disc"]["rho_cd"]) < 0.15 and out["cont"]["rho_cd"] > 0.5
                   and abs(out["cont"]["rho_dc"]) < 0.15 and abs(out["surface"]["rho_dc"]) < 0.15 and
                   out["null"]["pass_rate_band"])
    return out
