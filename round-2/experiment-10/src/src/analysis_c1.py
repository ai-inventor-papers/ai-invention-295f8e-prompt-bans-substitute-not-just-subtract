#!/usr/bin/env python3
"""S6 analysis (CPU), frozen in commitments.log before the first S5 score.

FRLP cell  L_j(c) = logmeanexp_m [ l(p_jm | c) - l(p_jm | F_j) ]  (mixture proposal over the forced prompts used for j),
ESS = 1 / sum(w^2) with normalised importance weights. Gains G^h[X, j, w] = L_j^h(ban_w X) - L_j^h(neutral_w^h X);
prime = mention - neutral; veto = ban - mention. External ladder profile u = mean of the unit-normed, centred nonce,
mean-edit and novelty profiles. C1: per row X (>= 3 survivors), replicates r = (w, h), g_r centred over S_X, gbar,
projection f on the centred u, residual s, replicate covariance Sigma / (R(R-1)); V_u = sum(|f|^2 - vhat'Sigma vhat),
V_s = sum(|s|^2 - (tr Sigma - vhat'Sigma vhat)), SHARE = V_s / (V_s + V_u). AIM = mean over rows of the split-half
Spearman of s with the prime-and-veto profile, against the exact within-row survivor-permutation null. Bootstrap over
templates (shared draw across ban/mention/neutral/nonce/two-step) and programs within (task, algorithm, half).
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

TEMPLATES = (1, 2, 3, 4, 5)
HALVES = (1, 2)
ESS_FLOOR = 5.0
B_DEFAULT = 2000
GATE = {"a_sigma_lo": 0.3, "a_sigma_hi": 3.0, "a_default_mass": 0.9, "b_nats": 0.3, "c_argmax": 0.8,
        "b_min_nonbanned": 15, "q_other": 0.02, "q_mix": 0.05}
EVENT_GATE = {"avoidance": 0.5, "min_nonbanned": 20, "clear_margin": 0.15}


# ================================================================================================ data
@dataclass
class TaskData:
    task: str
    algs: list[str]  # FRLP-measured algorithms (catalogue order)
    d: str
    s_star: str
    prog: pd.DataFrame  # program_id, j, half, passed, generating_cond (row order of the matrices)
    conds: list[str]
    lf: np.ndarray  # [P, C] l_full (NaN = not scored)
    lb: np.ndarray  # [P, C] l_body
    cidx: dict[str, int] = field(default_factory=dict)
    jidx: np.ndarray | None = None  # [P] algorithm index
    hidx: np.ndarray | None = None  # [P] half index 0/1

    def __post_init__(self):
        self.cidx = {c: i for i, c in enumerate(self.conds)}
        self.jidx = np.array([self.algs.index(j) for j in self.prog["j"]])
        self.hidx = np.array([int(h) - 1 for h in self.prog["half"]])

    def has(self, c: str) -> bool:
        return c in self.cidx


def logmeanexp(a: np.ndarray, axis: int = -1) -> np.ndarray:
    m = np.nanmax(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    with np.errstate(invalid="ignore"):
        e = np.exp(a - m)
    e = np.where(np.isnan(a), 0.0, e)
    n = np.sum(~np.isnan(a), axis=axis, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = m + np.log(np.sum(e, axis=axis, keepdims=True) / n)
    return np.where(n > 0, out, np.nan).squeeze(axis)


def proposal(td: TaskData, variant: str = "full") -> np.ndarray:
    """log q(p) = l(p | F_j): mixture over every forced prompt used for j (full / body), the generating paraphrase
    ('gen_proposal'), or exp1's 5 standard templates ('exp1_5tpl')."""
    mat = td.lb if variant == "body" else td.lf
    out = np.full(len(td.prog), np.nan)
    pcols = [i for c, i in td.cidx.items() if c.startswith("forced:") or c.startswith("forced_desc:")]
    for r, (j, gen) in enumerate(zip(td.prog["j"], td.prog["generating_cond"])):
        if variant == "gen_proposal":
            out[r] = mat[r, td.cidx[gen]]
            continue
        if variant == "exp1_5tpl":
            cols = [td.cidx[f"forced:{j}:k{k}"] for k in range(5) if f"forced:{j}:k{k}" in td.cidx]
        else:
            cols = [i for i in pcols if td.conds[i].split(":")[1] == j]
        v = mat[r, cols]
        out[r] = logmeanexp(v[~np.isnan(v)]) if np.any(~np.isnan(v)) else np.nan
    return out


# ================================================================================================ cells
@dataclass
class Cells:
    Lh: np.ndarray  # [J, 2, C]
    La: np.ndarray  # [J, C]
    ESSh: np.ndarray  # [J, 2, C]
    ESSa: np.ndarray  # [J, C]
    Nh: np.ndarray  # [J, 2] programs per half (with multiplicity)


def make_cells(td: TaskData, D: np.ndarray, counts: np.ndarray | None = None, mask: np.ndarray | None = None) -> Cells:
    """D [P, C] = log importance ratios; counts [P] bootstrap multiplicities; mask [P] program subset."""
    P, C = D.shape
    J = len(td.algs)
    w = np.ones(P) if counts is None else counts.astype(float)
    if mask is not None:
        w = w * mask
    Lh = np.full((J, 2, C), np.nan)
    ESSh = np.full((J, 2, C), np.nan)
    La = np.full((J, C), np.nan)
    ESSa = np.full((J, C), np.nan)
    Nh = np.zeros((J, 2))
    for j in range(J):
        sel_j = td.jidx == j
        Dj = D[sel_j]
        wj = w[sel_j]
        hj = td.hidx[sel_j]
        valid = ~np.isnan(Dj)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                M = np.nanmax(np.where(valid & (wj[:, None] > 0), Dj, np.nan), axis=0) if np.any(wj > 0) else np.full(C, np.nan)
        M = np.where(np.isfinite(M), M, 0.0)
        E = np.where(valid, np.exp(np.where(valid, Dj, 0.0) - M), 0.0)
        for h in (0, 1):
            sh = (hj == h)
            ww = (wj * sh)[:, None] * valid
            s1 = np.sum(ww * E, axis=0)
            s2 = np.sum(ww * E ** 2, axis=0)
            n = np.sum(ww, axis=0)
            Nh[j, h] = float(np.sum(wj * sh))
            with np.errstate(divide="ignore", invalid="ignore"):
                Lh[j, h] = np.where((n > 0) & (s1 > 0), M + np.log(s1 / n), np.nan)
                ESSh[j, h] = np.where(s2 > 0, s1 ** 2 / s2, np.nan)
        ww = wj[:, None] * valid
        s1 = np.sum(ww * E, axis=0)
        s2 = np.sum(ww * E ** 2, axis=0)
        n = np.sum(ww, axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            La[j] = np.where((n > 0) & (s1 > 0), M + np.log(s1 / n), np.nan)
            ESSa[j] = np.where(s2 > 0, s1 ** 2 / s2, np.nan)
    return Cells(Lh=Lh, La=La, ESSh=ESSh, ESSa=ESSa, Nh=Nh)


def importance(td: TaskData, variant: str = "full") -> np.ndarray:
    base = td.lb if variant == "body" else td.lf
    lq = proposal(td, variant if variant in ("body", "gen_proposal", "exp1_5tpl") else "full")
    return base - lq[:, None]


# ================================================================================================ helpers
def centre(v: np.ndarray) -> np.ndarray:
    return v - np.mean(v)


def unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v * np.nan


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else float("nan")


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.any(np.isnan(a)) or np.any(np.isnan(b)):
        return float("nan")
    ra, rb = rankdata(a), rankdata(b)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


class View:
    """Accessors over one Cells object with a template draw `tw` (list of 5 template ids)."""

    def __init__(self, td: TaskData, cells: Cells, tw: list[int] | None = None):
        self.td, self.c = td, cells
        self.tw = list(tw) if tw is not None else list(TEMPLATES)
        self.ai = {a: i for i, a in enumerate(td.algs)}

    def h(self, cond: str, h: int, algs: list[str]) -> np.ndarray:
        if cond not in self.td.cidx:
            return np.full(len(algs), np.nan)
        ci = self.td.cidx[cond]
        return np.array([self.c.Lh[self.ai[a], h - 1, ci] for a in algs])

    def a(self, cond: str, algs: list[str]) -> np.ndarray:
        if cond not in self.td.cidx:
            return np.full(len(algs), np.nan)
        ci = self.td.cidx[cond]
        return np.array([self.c.La[self.ai[a], ci] for a in algs])

    def ess_h(self, cond: str, h: int, algs: list[str]) -> np.ndarray:
        if cond not in self.td.cidx:
            return np.full(len(algs), np.nan)
        ci = self.td.cidx[cond]
        return np.array([self.c.ESSh[self.ai[a], h - 1, ci] for a in algs])

    # ---- gains
    def G(self, X: str, w: int, h: int, algs: list[str], ref: str = "neutral") -> np.ndarray:
        ban = self.h(f"ban:{X}:w{w}", h, algs)
        if ref == "neutral":
            return ban - self.h(f"neutral:{X}:w{w}:h{h}", h, algs)
        return ban - self.h(f"mention:{X}:w{w}", h, algs)  # veto row (mention reference)

    def prime(self, X: str, w: int, h: int, algs: list[str]) -> np.ndarray:
        return self.h(f"mention:{X}:w{w}", h, algs) - self.h(f"neutral:{X}:w{w}:h{h}", h, algs)

    # ---- generic profiles over all algorithms
    def generic(self, half: int | None = None) -> dict[str, np.ndarray]:
        algs = self.td.algs
        out: dict[str, np.ndarray] = {}
        hs = HALVES if half is None else (half,)
        out["nonce"] = np.nanmean([self.h(f"nonce:w{w}", h, algs) - self.h(f"nonce_neutral:w{w}:h{h}", h, algs)
                                   for w in self.tw for h in hs], axis=0)
        get = (lambda c: self.a(c, algs)) if half is None else (lambda c: self.h(c, half, algs))
        for k in range(1, 7):
            if self.td.has(f"edit:k{k}"):
                out[f"edit{k}"] = get(f"edit:k{k}") - get("baseline_empty")
        out["novelty"] = get("novelty") - np.nanmean([get(f"baseline:s{s}") for s in range(5)], axis=0)
        return out

    def u(self, half: int | None = None, raw_mean: bool = False) -> np.ndarray:
        g = self.generic(half)
        edits = [g[k] for k in g if k.startswith("edit")]
        if raw_mean:
            return np.mean([g["nonce"]] + edits + [g["novelty"]], axis=0)
        types = [g["nonce"], np.mean(edits, axis=0) if edits else np.full(len(self.td.algs), np.nan), g["novelty"]]
        types = [unit(centre(t)) for t in types if not np.any(np.isnan(t))]
        if not types:  # degenerate bootstrap draw (a half with no programs): undefined profile
            return np.full(len(self.td.algs), np.nan)
        return np.mean(types, axis=0)


# ================================================================================================ C1
def survivors(td: TaskData, X: str, drop_default: bool = False) -> list[str]:
    s = [j for j in td.algs if j != X]
    if drop_default and X != td.d:
        s = [j for j in s if j != td.d]
    return s


def c1_task(v: View, ref: str = "neutral", weighted: bool = True, iso: bool = False, raw_u: bool = False,
            drop_default: bool = False, drop_flagged: bool = False, assoc: dict[str, dict[str, int]] | None = None,
            want_rows: bool = False, noise: str = "replicate") -> dict[str, Any]:
    """noise='replicate' (frozen primary): Sigma over the R = 10 template x half replicates treated as exchangeable;
    noise='template_mean' (sensitivity): Sigma from the 5 template means (each the mean of its 2 halves) / (W(W-1)),
    unbiased for the crossed template x half design when template effects are shared across halves."""
    td = v.td
    K = len(td.algs)
    u_full = v.u(raw_mean=raw_u)
    u_half = {h: v.u(half=h, raw_mean=raw_u) for h in HALVES}
    ai = v.ai
    rows = []
    Vu = Vs = Vt = 0.0
    for X in td.algs:
        if X not in td.algs:
            continue
        S = survivors(td, X, drop_default)
        if drop_flagged:
            ess = np.array([[np.nanmin([v.ess_h(f"ban:{X}:w{w}", h, S), v.ess_h(f"neutral:{X}:w{w}:h{h}", h, S)], axis=0)
                             for h in HALVES] for w in v.tw])
            ok = np.nanmin(ess.reshape(-1, len(S)), axis=0) >= ESS_FLOOR
            S = [j for j, o in zip(S, ok) if o]
        if len(S) < 3:
            continue
        reps = []
        wts = []
        for w in v.tw:
            for h in HALVES:
                g = v.G(X, w, h, S, ref)
                reps.append(g)
                eb = v.ess_h(f"ban:{X}:w{w}", h, S)
                er = v.ess_h(f"neutral:{X}:w{w}:h{h}", h, S) if ref == "neutral" else v.ess_h(f"mention:{X}:w{w}", h, S)
                wts.append(np.minimum(1.0, np.nanmin([eb, er], axis=0) / ESS_FLOOR))
        reps = np.array(reps)
        if np.any(np.isnan(reps)):
            good = ~np.any(np.isnan(reps), axis=0)
            if good.sum() < 3:
                continue
            S = [j for j, g_ in zip(S, good) if g_]
            reps = reps[:, good]
            wts = [w_[good] for w_ in wts]
        n = len(S)
        reps = np.array([centre(r) for r in reps])
        wt = np.nanmean(np.array(wts), axis=0) if weighted else np.ones(n)
        wt = np.where(np.isnan(wt), 0.0, wt)
        reps_w = np.array([centre(wt * r) for r in reps])
        R = len(reps_w)
        gbar = reps_w.mean(axis=0)
        dev = reps_w - gbar
        Sigma = dev.T @ dev / (R * (R - 1))
        if noise == "template_mean":
            W_ = len(v.tw)
            mw = reps_w.reshape(W_, len(HALVES), n).mean(axis=1)
            dm = mw - gbar
            Sigma = dm.T @ dm / (W_ * (W_ - 1))
        vv = centre(u_full[[ai[j] for j in S]])
        vhat = unit(vv)
        if np.any(np.isnan(vhat)):
            continue
        a = float(gbar @ vhat)
        f = a * vhat
        s = gbar - f
        trS = float(np.trace(Sigma))
        if iso:
            sig2 = trS / (n - 1)
            nu, ns = sig2, sig2 * (n - 2)
        else:
            nu = float(vhat @ Sigma @ vhat)
            ns = trS - nu
        vu_r, vs_r = a * a - nu, float(s @ s) - ns
        vt_r = float(gbar @ gbar) - trS
        Vu += vu_r
        Vs += vs_r
        Vt += vt_r
        # AIM (split halves): s^h residual of centred mean_w G^h on centred u^h; PV^h centred mean_w prime^h
        sh, pv = {}, {}
        for h in HALVES:
            gh = centre(np.mean([v.G(X, w, h, S, ref) for w in v.tw], axis=0))
            uh = unit(centre(u_half[h][[ai[j] for j in S]]))
            sh[h] = gh - (gh @ uh) * uh if not np.any(np.isnan(uh)) else gh * np.nan
            pv[h] = centre(np.mean([v.prime(X, w, h, S) for w in v.tw], axis=0))
        rho = 0.5 * (spearman(sh[1], pv[2]) + spearman(sh[2], pv[1]))
        rhoA = None
        if assoc is not None:
            cnt = assoc.get(X, {})
            nA = np.array([cnt.get(j, 0) for j in S], dtype=float)
            A = (nA + 1.0) / (nA.sum() + len(S))
            rhoA = 0.5 * (spearman(sh[1], A) + spearman(sh[2], A))
        row = {"X": X, "survivors": S, "n_surv": n, "gbar": gbar, "f2": a * a, "s2": float(s @ s), "noise_u": nu,
               "noise_s": ns, "trSigma": trS, "V_u": vu_r, "V_s": vs_r, "V_tot": vt_r, "rho": rho, "rhoA": rhoA,
               "cos_u": cosine(gbar, vv), "s": s, "weights": wt}
        if want_rows:
            row.update({"s_half": {h: sh[h] for h in HALVES}, "pv_half": {h: pv[h] for h in HALVES}})
        rows.append(row)
    share = clip_share(Vu, Vs)
    aim = float(np.nanmean([r["rho"] for r in rows])) if rows else float("nan")
    aimA = float(np.nanmean([r["rhoA"] for r in rows if r["rhoA"] is not None])) if rows and assoc is not None else None
    return {"rows": rows, "V_u": Vu, "V_s": Vs, "V_tot": Vt, "SHARE": share, "AIM": aim, "AIM_assoc": aimA,
            "n_rows": len(rows), "K": K}


def clip_share(Vu: float, Vs: float) -> float:
    a, b = max(Vu, 0.0), max(Vs, 0.0)
    return b / (a + b) if (a + b) > 0 else float("nan")


def pool(results: list[dict[str, Any]]) -> dict[str, Any]:
    Vu = sum(r["V_u"] for r in results)
    Vs = sum(r["V_s"] for r in results)
    Vt = sum(r["V_tot"] for r in results)
    rows = [row for r in results for row in r["rows"]]
    aim = float(np.nanmean([row["rho"] for row in rows])) if rows else float("nan")
    rA = [row["rhoA"] for row in rows if row.get("rhoA") is not None]
    return {"V_u": Vu, "V_s": Vs, "V_u_clipped": max(Vu, 0.0), "V_s_clipped": max(Vs, 0.0), "V_tot": Vt,
            "SHARE": clip_share(Vu, Vs), "AIM": aim, "AIM_assoc": float(np.nanmean(rA)) if rA else None,
            "n_rows": len(rows)}


# ================================================================================================ AIM null
def row_null(s1: np.ndarray, s2: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """All |S|! survivor permutations applied to PV (same permutation for both halves)."""
    n = len(s1)
    vals = []
    for perm in itertools.permutations(range(n)):
        pp = list(perm)
        vals.append(0.5 * (spearman(s1, p2[pp]) + spearman(s2, p1[pp])))
    return np.array(vals)


def row_null_single(s1: np.ndarray, s2: np.ndarray, A: np.ndarray) -> np.ndarray:
    n = len(s1)
    return np.array([0.5 * (spearman(s1, A[list(p)]) + spearman(s2, A[list(p)])) for p in itertools.permutations(range(n))])


def pooled_null(row_vals: list[np.ndarray], n_mc: int = 1_000_000, seed: int = 0) -> dict[str, Any]:
    """Null of the mean over rows: exact convolution on the rational grid (step 1/(2*LCM of n(n^2-1)/6)) when every
    value lies on it; otherwise n_mc Monte Carlo joint draws."""
    row_vals = [np.asarray(v)[~np.isnan(v)] for v in row_vals if np.sum(~np.isnan(v)) > 0]
    if not row_vals:
        return {"method": "none"}
    grid = 1.0 / 240.0  # Spearman for n<=5 without ties: multiples of 1/120 (n=5: 6/120; n=4: 6/60; n=3: 6/24); avg of 2 -> 1/240
    on_grid = all(np.allclose(np.round(v / grid) * grid, v, atol=1e-9) for v in row_vals)
    R = len(row_vals)
    if on_grid:
        pmf = np.array([1.0])
        offset = 0
        for v in row_vals:
            ks = np.round(v / grid).astype(int)
            lo = ks.min()
            h = np.bincount(ks - lo).astype(float)
            h /= h.sum()
            pmf = np.convolve(pmf, h)
            offset += lo
        support = (np.arange(len(pmf)) + offset) * grid / R
        cdf = np.cumsum(pmf)
        q95 = float(support[np.searchsorted(cdf, 0.95 - 1e-12)])
        return {"method": "exact_convolution", "support": support, "pmf": pmf, "q95": q95}
    rng = np.random.default_rng(seed)
    draws = np.mean([rng.choice(v, size=n_mc) for v in row_vals], axis=0)
    return {"method": f"monte_carlo_{n_mc}", "draws": draws, "q95": float(np.quantile(draws, 0.95))}


def null_p(null: dict[str, Any], obs: float) -> float:
    if null.get("method") == "none" or obs is None or np.isnan(obs):
        return float("nan")
    if "pmf" in null:
        return float(np.sum(null["pmf"][null["support"] >= obs - 1e-12]))
    return float(np.mean(null["draws"] >= obs - 1e-12))


# ================================================================================================ ladder
def ladder_exists(v: View) -> dict[str, Any]:
    td = v.td
    g = v.generic()
    nd = [j for j in td.algs if j != td.d]
    idx = [td.algs.index(j) for j in nd]
    prof = {k: centre(val[idx]) for k, val in g.items() if not np.any(np.isnan(val[idx]))}
    keys = sorted(prof)
    cos = {f"{a}|{b}": cosine(prof[a], prof[b]) for a, b in itertools.combinations(keys, 2)}
    mean_cos = float(np.nanmean(list(cos.values()))) if cos else float("nan")
    edits = [k for k in keys if k.startswith("edit")]
    t_prof = {"nonce": prof.get("nonce"), "edit_mean": centre(np.mean([prof[k] for k in edits], axis=0)) if edits else None,
              "novelty": prof.get("novelty")}
    t_prof = {k: x for k, x in t_prof.items() if x is not None}
    tb = [cosine(t_prof[a], t_prof[b]) for a, b in itertools.combinations(sorted(t_prof), 2)]
    s0 = [k for k in edits if int(k[4:]) <= 3]
    s1 = [k for k in edits if int(k[4:]) >= 4]
    by_seed = {f"seed{i}": float(np.nanmean([cosine(prof[a], prof[b]) for a, b in itertools.combinations(ks, 2)]))
               if len(ks) > 1 else None for i, ks in ((0, s0), (1, s1))}
    return {"n_profiles": len(keys), "n_pairs": len(cos), "mean_pairwise_cosine": mean_cos,
            "ladder_exists": bool(mean_cos >= 0.5), "type_balanced_mean_cosine": float(np.nanmean(tb)) if tb else None,
            "by_edit_seed": by_seed, "pairwise": cos, "non_default_algorithms": nd,
            "profiles": {k: x.tolist() for k, x in prof.items()}}


# ================================================================================================ cosine table
def cosine_table(v: View, rows: list[dict[str, Any]]) -> dict[str, Any]:
    td = v.td
    per_ban = {r["X"]: r["cos_u"] for r in rows}
    pair = {}
    gb = {r["X"]: dict(zip(r["survivors"], r["gbar"])) for r in rows}
    for a, b in itertools.combinations(sorted(gb), 2):
        common = [j for j in gb[a] if j in gb[b]]
        if len(common) >= 2:
            pair[f"{a}|{b}"] = cosine(centre(np.array([gb[a][j] for j in common])), centre(np.array([gb[b][j] for j in common])))
    own = {}
    for X in td.algs:
        ban = np.mean([v.h(f"ban:{X}:w{w}", h, [X])[0] for w in v.tw for h in HALVES])
        neu = np.mean([v.h(f"neutral:{X}:w{w}:h{h}", h, [X])[0] for w in v.tw for h in HALVES])
        men = np.mean([v.h(f"mention:{X}:w{w}", h, [X])[0] for w in v.tw for h in HALVES])
        own[X] = {"D_X": float(ban - neu), "prime": float(men - neu), "veto": float(ban - men)}
    return {"cos_with_u": per_ban, "pairwise": pair,
            "mean_off_diagonal": float(np.nanmean(list(pair.values()))) if pair else None, "own_drop": own}


# ================================================================================================ route test
def route_numbers(views: list[View]) -> dict[str, Any] | None:
    Da = Dc = Dd = 0.0
    prof = {"a": [], "c": [], "d": []}
    n = 0
    for v in views:
        td = v.td
        X = td.d
        S = [j for j in td.algs if j != X]
        for w in v.tw:
            for h in HALVES:
                cc, dc = f"route_c:{X}:w{w}:h{h}", f"route_d:{X}:w{w}:h{h}"
                if not (td.has(cc) and td.has(dc)):
                    continue
                b = v.h(f"neutral:{X}:w{w}:h{h}", h, [X] + S)
                a = v.h(f"ban:{X}:w{w}", h, [X] + S) - b
                c_ = v.h(cc, h, [X] + S) - b
                d_ = v.h(dc, h, [X] + S) - b
                Da += a[0]
                Dc += c_[0]
                Dd += d_[0]
                prof["a"].append(centre(a[1:]))
                prof["c"].append(centre(c_[1:]))
                prof["d"].append(centre(d_[1:]))
                n += 1
    if n == 0:
        return None
    out = {"n_cells": n, "sum_D_a": Da, "sum_D_c": Dc, "sum_D_d": Dd,
           "F_direct": Dd / Da if Da != 0 else float("nan"), "F_prompt": Dc / Da if Da != 0 else float("nan"),
           "interaction": Da - Dc - Dd, "survivor_profile_cosines": {}}
    # cosine of each arm's (centred, template x half mean) survivor-gain profile with the full ban's, per task
    for length in sorted({len(x) for x in prof["a"]}):
        idx = [i for i, x in enumerate(prof["a"]) if len(x) == length]
        if length < 2:
            continue
        pa = np.mean([prof["a"][i] for i in idx], axis=0)
        out["survivor_profile_cosines"][f"{length}_survivors"] = {
            "cos_c_with_a": cosine(np.mean([prof["c"][i] for i in idx], axis=0), pa),
            "cos_d_with_a": cosine(np.mean([prof["d"][i] for i in idx], axis=0), pa), "n_cells": len(idx)}
    return out


# ================================================================================================ gate
def frlp_gate(views: dict[str, View], events: dict[str, list[dict[str, Any]]], sampled_share: dict[str, Any]) -> dict[str, Any]:
    """(a) calibration on the 5 baselines, (b) >= 0.3 nats/sample over uniform on events with >= 15 attempted
    non-banned samples, (c) argmax = realised mode on >= 80% of clear-mode events."""
    out: dict[str, Any] = {"a": {}, "b_events": [], "c_events": []}
    a_ok = True
    for task, v in views.items():
        td = v.td
        sig, dm = [], []
        for s in range(5):
            L = v.a(f"baseline:s{s}", td.algs)
            S_ = float(np.nansum(np.exp(L)))
            sig.append(S_)
            dm.append(float(np.exp(L[td.algs.index(td.d)]) / S_) if S_ > 0 else float("nan"))
        ms, md = float(np.mean(sig)), float(np.mean(dm))
        lit = GATE["a_sigma_lo"] <= ms <= GATE["a_sigma_hi"] and md >= GATE["a_default_mass"]
        ci = sampled_share[task]["modal_share_wilson"]
        intent = GATE["a_sigma_lo"] <= ms <= GATE["a_sigma_hi"] and ci[0] <= md <= ci[1]
        implied = {j: float(np.mean([np.exp(v.a(f"baseline:s{s}", [j])[0]) / sig[s] for s in range(5)])) for j in td.algs}
        out["a"][task] = {"sigma_per_s": sig, "mean_sigma": ms, "default_mass_per_s": dm, "mean_default_mass": md,
                          "pass_literal": bool(lit), "pass_intent": bool(intent), "sampled_modal_share_wilson": ci,
                          "implied_distribution": implied}
        a_ok = a_ok and lit
    deltas, hits = [], []
    for task, evs in events.items():
        v = views[task]
        td = v.td
        for ev in evs:
            banned = set(ev["banned"])
            Se = [j for j in td.algs if j not in banned]
            samples = [s for s in ev["samples"] if s["label"] not in banned and s["label"] != "no_code"]
            if len(samples) >= GATE["b_min_nonbanned"] and Se:
                dl = []
                for s in samples:
                    L = v.a(s["cond"], Se)
                    if np.any(np.isnan(L)):
                        continue
                    sm = np.exp(L - L.max())
                    sm /= sm.sum()
                    q = (1 - GATE["q_other"]) * ((1 - GATE["q_mix"]) * sm + GATE["q_mix"] / len(Se))
                    lab = s["label"]
                    if lab in Se:
                        lq_, lu = math.log(q[Se.index(lab)]), math.log((1 - GATE["q_other"]) / len(Se))
                    else:  # 'other' or a catalogue label outside the FRLP set
                        lq_, lu = math.log(GATE["q_other"]), math.log(GATE["q_other"])
                    dl.append(lq_ - lu)
                # unsmoothed variant: 'other' samples excluded, raw softmax vs uniform
                du = []
                for s in samples:
                    if s["label"] not in Se:
                        continue
                    L = v.a(s["cond"], Se)
                    if np.any(np.isnan(L)):
                        continue
                    sm = np.exp(L - L.max())
                    sm /= sm.sum()
                    du.append(math.log(max(sm[Se.index(s["label"])], 1e-300)) - math.log(1.0 / len(Se)))
                rec = {"task": task, "event": ev["name"], "n_scored": len(dl), "delta": float(np.mean(dl)) if dl else None,
                       "delta_unsmoothed": float(np.mean(du)) if du else None, "S_e": Se}
                out["b_events"].append(rec)
                if dl:
                    deltas.append(rec["delta"])
            if ev.get("clear_mode") and Se:
                Lm = np.nanmean([v.a(c, Se) for c in ev["conds"]], axis=0)
                if np.all(np.isnan(Lm)):  # event conditions not scored
                    out["c_events"].append({"task": task, "event": ev["name"], "skipped": "conditions not scored"})
                    continue
                am = Se[int(np.nanargmax(Lm))]
                hits.append(am == ev["mode"])
                out["c_events"].append({"task": task, "event": ev["name"], "frlp_argmax": am, "realised_mode": ev["mode"],
                                        "hit": am == ev["mode"], "template_mean_L": dict(zip(Se, Lm.tolist()))})
    out["b_mean_delta"] = float(np.mean(deltas)) if deltas else None
    out["b_n_events"] = len(deltas)
    out["b_pass"] = bool(deltas) and out["b_mean_delta"] >= GATE["b_nats"]
    out["c_hit_rate"] = float(np.mean(hits)) if hits else None
    out["c_n_events"] = len(hits)
    out["c_pass"] = bool(hits) and out["c_hit_rate"] >= GATE["c_argmax"]
    out["a_pass"] = bool(a_ok)
    out["a_pass_intent_all"] = all(x["pass_intent"] for x in out["a"].values())
    out["GATE"] = bool(out["a_pass"] and out["b_pass"] and out["c_pass"])
    out["thresholds"] = GATE
    return out


# ================================================================================================ branch
def branch(share_ci: tuple[float, float], vtot_ci: tuple[float, float], aim_pass_pv: bool, aim_pass_assoc: bool,
           ladder: bool) -> str:
    lo, hi = share_ci
    if vtot_ci[0] <= 0:
        return "PURE SUBTRACTION"
    if lo > 0.5 and (aim_pass_pv or aim_pass_assoc):
        return "SUBSTITUTION (" + ("prime-and-veto" if aim_pass_pv else "association") + ")"
    if lo > 0.5:
        return "X-SPECIFIC BUT UNAIMED"
    if hi < 0.5 and ladder:
        return "LADDER"
    if hi < 0.5:
        return "UNDETERMINED"
    return "not resolved at this N"


def ci(a: list[float] | np.ndarray) -> tuple[float, float]:
    a = np.asarray([x for x in a if x is not None and not np.isnan(x)])
    if len(a) == 0:
        return (float("nan"), float("nan"))
    return (float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975)))


# ================================================================================================ bootstrap
def boot_counts(td: TaskData, rng: np.random.Generator) -> np.ndarray:
    cnt = np.zeros(len(td.prog))
    for j in range(len(td.algs)):
        for h in (0, 1):
            idx = np.where((td.jidx == j) & (td.hidx == h))[0]
            if len(idx):
                cnt[idx] = rng.multinomial(len(idx), np.ones(len(idx)) / len(idx))
    return cnt


def jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [jsonable(v) for v in o.tolist()]
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) or isinstance(o, np.floating)) and not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


_ = json
