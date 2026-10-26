#!/usr/bin/env python3
"""Step 6: C1 output-space share test (frozen before any Q3 output is read), plus steps 7.1-7.4.

Per task t and ban row B (survivors S_B = measurable catalogue minus B, |S_B| >= 3):
  replicates r = (w, h), R = 10:  g_Br(j) = L^h_j(ban_w B) - L^h_j(ref_{w,h} B), j in S_B
  (ref = neutral twin with noun A on h1 / noun B on h2 [primary], or the mention twin [reference 2]);
  c_Br = g_Br - mean_j g_Br;  Gbar_B = mean_r c_Br.
  External ladder profile u = mean of the NONCE, RAND (6 matched-norm random prompt-band edits) and NOV family
  profiles; u_B = u on S_B, centred; uhat = u_B / ||u_B||.
  a_B = Gbar_B . uhat (ladder), s_B = Gbar_B - a_B uhat (X-specific).
  Noise (df rule): tot_B = sum_j var_r(c_Br(j)) / R, sigma2 = tot_B / (|S_B| - 1), N_u = sigma2, N_s = (|S_B|-2) sigma2.
  V_u = sum_B (a_B^2 - N_u), V_s = sum_B (||s_B||^2 - N_s), SHARE = V_s / (V_s + V_u).
Bootstrap: templates, programs within algorithm-halves (logsumexp recomputed) and random directions resampled.
AIM: Spearman(s_B from one half, prime-and-veto profile PV_B from the other half with the other noun), averaged over
the two swaps and over rows; null = within-row survivor permutation (200,000 Monte Carlo draws).
"""

from __future__ import annotations

import io
import keyword
import math
import tokenize
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import rankdata, spearmanr

from config import (DATA, ESS_FLAG, LADDER_COS_MIN, MODES, N_BOOT, N_PERM, RESULTS, SEED_BOOT, SHAM_NEIGHBOURS,
                    SHAMS, TASKS, WS, read_json, read_jsonl, setup_logging, utc_now, write_json)
from frlp import VARIANTS, CellArrays, TaskData, build_task_data

RAND_NAMES = ["A1001", "A1002", "A1003", "B2001", "B2002", "B2003"]


def needed_conds(task: str) -> tuple[list[str], dict[str, tuple[str, str]]]:
    conds = ["base0", "novelty"] + [f"edit|{d}" for d in RAND_NAMES]
    virtual = {}
    for x in MODES[task] + list(SHAMS[task]) + ["nonce", "two_step"]:
        for w in WS:
            conds += [f"ban|{x}|{w}", f"neutral|{x}|{w}|A", f"neutral|{x}|{w}|B", f"mention|{x}|{w}"]
            virtual[f"neutral|{x}|{w}|AB"] = (f"neutral|{x}|{w}|A", f"neutral|{x}|{w}|B")
    return conds, virtual


def edit2_conds(td: TaskData) -> list[str]:
    if "total" not in td.L:
        return []
    return sorted({k.split("|", 1)[1] for k in td.L["total"].index if k.startswith("edit2|")})


class Ctx:
    """Cell lookup on top of CellArrays outputs."""

    def __init__(self, ca: CellArrays, L: dict[str, np.ndarray], ess: dict[str, np.ndarray] | None = None):
        self.ca, self.L, self.ess = ca, L, ess

    def v(self, cond: str, h: str = "all") -> np.ndarray:
        i = self.ca.cidx.get(cond)
        if i is None:
            return np.full(len(self.ca.js), np.nan)
        return self.L[h][i]

    def e(self, cond: str, h: str) -> np.ndarray:
        i = self.ca.cidx.get(cond)
        if i is None or self.ess is None:
            return np.full(len(self.ca.js), np.nan)
        return self.ess[h][i]


def family_profiles(cx: Ctx, templates: list[str], dirs: list[str], edit2: list[str] | None = None,
                    half: str = "all") -> dict[str, np.ndarray]:
    nonce = np.nanmean([cx.v(f"ban|nonce|{w}", half) - cx.v(f"neutral|nonce|{w}|AB" if half == "all" else
                                                           f"neutral|nonce|{w}|{'A' if half == 'h1' else 'B'}", half)
                        for w in templates], axis=0)
    base = cx.v("base0", half)
    rand = np.nanmean([cx.v(f"edit|{d}", half) - base for d in dirs], axis=0)
    nov = cx.v("novelty", half) - base
    out = {"NONCE": nonce, "RAND": rand, "NOV": nov}
    if edit2:
        out["RAND_ii"] = np.nanmean([cx.v(c, half) - base for c in edit2], axis=0)
    return out


def ladder_u(fp: dict[str, np.ndarray], kind: str = "primary") -> np.ndarray:
    if kind == "primary":
        return np.mean([fp["NONCE"], fp["RAND"], fp["NOV"]], axis=0)
    if kind == "with_ii":
        return np.mean([fp[k] for k in ("NONCE", "RAND", "NOV", "RAND_ii") if k in fp], axis=0)
    if kind == "unit_normalised":
        vs = []
        for k in ("NONCE", "RAND", "NOV"):
            v = fp[k] - np.nanmean(fp[k])
            n = np.linalg.norm(np.nan_to_num(v))
            vs.append(v / n if n > 0 else v)
        return np.mean(vs, axis=0)
    if kind.startswith("only_"):
        return fp[kind[5:]]
    raise ValueError(kind)


def _wcentre(x: np.ndarray, v: np.ndarray) -> np.ndarray:
    return x - np.sum(v * x) / np.sum(v)


def row_stats(cx: Ctx, B: str, u: np.ndarray, templates: list[str], ref: str = "neutral",
              ess_weight: bool = False) -> dict[str, Any] | None:
    js = cx.ca.js
    S = [j for j in js if j != B]
    if len(S) < 3:
        return None
    idx = np.array([js.index(j) for j in S])
    reps, reps_h, ess_min = [], [], []
    for w in templates:
        for h, ns in (("h1", "A"), ("h2", "B")):
            refc = f"neutral|{B}|{w}|{ns}" if ref == "neutral" else f"mention|{B}|{w}"
            g = (cx.v(f"ban|{B}|{w}", h) - cx.v(refc, h))[idx]
            reps.append(g)
            reps_h.append(h)
            if cx.ess is not None:
                ess_min.append(np.fmin(cx.e(f"ban|{B}|{w}", h), cx.e(refc, h))[idx])
    G = np.array(reps)
    if not np.isfinite(G).all():
        return None
    if ess_weight and ess_min:
        med = np.nanmedian(np.array(ess_min), axis=0)
        vw = np.clip(med / ESS_FLAG, 0.0, 1.0)
        vw = np.where(np.isfinite(vw), vw, 1.0)
    else:
        med = np.nanmedian(np.array(ess_min), axis=0) if ess_min else np.full(len(S), np.nan)
        vw = np.ones(len(S))
    C = np.array([_wcentre(g, vw) for g in G])
    R = len(C)
    Gbar = C.mean(0)
    uB = _wcentre(u[idx], vw)
    un = math.sqrt(np.sum(vw * uB * uB))
    if not np.isfinite(un) or un == 0:
        return None
    uhat = uB / un
    a = float(np.sum(vw * Gbar * uhat))
    s = Gbar - a * uhat
    ss_s = float(np.sum(vw * s * s))
    tot = float(np.sum(vw * C.var(axis=0, ddof=1)) / R)
    neff = float(np.sum(vw))
    sigma2 = tot / (neff - 1)
    N_u, N_s = sigma2, (neff - 2) * sigma2
    proj = C @ (vw * uhat)
    N_u_p = float(np.var(proj, ddof=1) / R)
    N_s_p = tot - N_u_p
    out = {"B": B, "survivors": S, "Gbar": Gbar, "uhat": uhat, "a": a, "s": s, "a2": a * a, "ss_s": ss_s,
           "tot_noise": tot, "sigma2": sigma2, "N_u": N_u, "N_s": N_s, "N_u_proj": N_u_p, "N_s_proj": N_s_p,
           "ss_G": float(np.sum(vw * Gbar * Gbar)), "R": R, "weights": vw, "median_ess": med,
           "n_flagged_cells": int(np.sum(np.nan_to_num(med, nan=99.0) < ESS_FLAG))}
    # half-specific residuals for the AIM (h1 replicates vs h2 replicates)
    for hn in ("h1", "h2"):
        Ch = np.array([c for c, hh in zip(C, reps_h) if hh == hn])
        Gh = Ch.mean(0)
        out[f"s_{hn}"] = Gh - float(np.sum(vw * Gh * uhat)) * uhat
    return out


def share_from_rows(rows: list[dict[str, Any]], proj_noise: bool = False) -> dict[str, float]:
    nu, ns = ("N_u_proj", "N_s_proj") if proj_noise else ("N_u", "N_s")
    V_u = float(sum(r["a2"] - r[nu] for r in rows))
    V_s = float(sum(r["ss_s"] - r[ns] for r in rows))
    tot = V_u + V_s
    F = float(sum(r["ss_G"] for r in rows) / max(1e-12, sum(r["tot_noise"] for r in rows)))
    return {"V_u": V_u, "V_s": V_s, "V_tot": tot, "SHARE": V_s / tot if tot != 0 else math.nan, "F": F,
            "n_rows": len(rows)}


def pv_profile(cx: Ctx, B: str, templates: list[str], half: str, idx: np.ndarray) -> np.ndarray:
    ns = "A" if half == "h1" else "B"
    return np.nanmean([(cx.v(f"mention|{B}|{w}", half) - cx.v(f"neutral|{B}|{w}|{ns}", half))[idx]
                       for w in templates], axis=0)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return math.nan
    return float(spearmanr(a, b).correlation)


def perm_null(pairs_by_row: list[list[tuple[np.ndarray, np.ndarray]]], n_perm: int, seed: int) -> np.ndarray:
    """Null of the mean (over rows) of the mean (over pairs in the row) Spearman, permuting the second vector
    within each row with the SAME permutation for all pairs of that row (rows permuted independently)."""
    rng = np.random.default_rng(seed)
    total = np.zeros(n_perm)
    n_rows = 0
    for pairs in pairs_by_row:
        n = len(pairs[0][0])
        perms = np.argsort(rng.random((n_perm, n)), axis=1)
        row_val = np.zeros(n_perm)
        k = 0
        for a, b in pairs:
            ra = rankdata(a)
            rb = rankdata(b)
            ra_c = (ra - ra.mean()) / (np.linalg.norm(ra - ra.mean()) or 1.0)
            rbp = rb[perms]
            rbp_c = rbp - rbp.mean(axis=1, keepdims=True)
            nb = np.linalg.norm(rbp_c, axis=1)
            nb[nb == 0] = 1.0
            row_val += (rbp_c @ ra_c) / nb
            k += 1
        total += row_val / k
        n_rows += 1
    return total / max(1, n_rows)


def norm_tokens(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append(t.string if keyword.iskeyword(t.string) or t.string in dir(__builtins__) else "ID")
            elif t.type == tokenize.NUMBER:
                out.append("NUM")
            elif t.type == tokenize.STRING:
                out.append("STR")
            elif t.type in (tokenize.OP, tokenize.INDENT, tokenize.DEDENT):
                out.append(t.string if t.type == tokenize.OP else tokenize.tok_name[t.type])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def proximity(task: str, js: list[str]) -> dict[str, dict[str, float]]:
    from rapidfuzz.distance import Levenshtein

    sel = [r for r in read_jsonl(DATA / "forced_selected.jsonl") if r["task"] == task]
    toks = {j: [norm_tokens(r["code_scrubbed"]) for r in sel if r["j"] == j][:10] for j in js}
    out: dict[str, dict[str, float]] = {}
    for B in js:
        out[B] = {}
        for j in js:
            if j == B:
                continue
            d = [Levenshtein.normalized_distance(a, b) for a in toks[j] for b in toks[B]]
            out[B][j] = -float(np.mean(d)) if d else math.nan
    return out


def task_point(td: TaskData, ca: CellArrays, cx: Ctx, templates: list[str], dirs: list[str], u_kind: str,
               ref: str, ess_weight: bool = False, edit2: list[str] | None = None,
               cx_u: Ctx | None = None) -> dict[str, Any]:
    """cx_u: context for the generic (ladder) profiles when they come from another variant (unscrubbed C1 uses
    the primary scrubbed generic conditions, which were not scored on raw programs)."""
    fp = family_profiles(cx_u or cx, WS if cx_u is not None else templates, dirs, edit2)
    u = ladder_u(fp, u_kind)
    rows = []
    for B in MODES[td.task]:
        r = row_stats(cx, B, u, templates, ref, ess_weight)
        if r is not None:
            rows.append(r)
    return {"fp": fp, "u": u, "rows": rows, "share": share_from_rows(rows),
            "share_proj": share_from_rows(rows, proj_noise=True)}


def ladder_exists(cx: Ctx, td: TaskData, templates: list[str]) -> dict[str, Any]:
    js = cx.ca.js
    keep = [i for i, j in enumerate(js) if j != {"t1": "bfs", "t2": "dijkstra"}[td.task]]
    base = cx.v("base0")
    profs = {"NONCE": family_profiles(cx, templates, RAND_NAMES)["NONCE"]}
    for d in RAND_NAMES:
        profs[f"RAND_{d}"] = cx.v(f"edit|{d}") - base
    profs["NOV"] = cx.v("novelty") - base
    names = list(profs)
    M = np.array([profs[n][keep] for n in names])
    ok = np.isfinite(M).all(axis=1)
    names = [n for n, o in zip(names, ok) if o]
    M = M[ok]
    cc, rc = [], []
    for i in range(len(M)):
        for k in range(i + 1, len(M)):
            a, b = M[i], M[k]
            ac, bc = a - a.mean(), b - b.mean()
            cc.append(float(ac @ bc / (np.linalg.norm(ac) * np.linalg.norm(bc) + 1e-12)))
            rc.append(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)))
    mat = {n: {m: float(np.corrcoef(M[i], M[k])[0, 1]) for k, m in enumerate(names)} for i, n in enumerate(names)}
    sd = {n: float(np.std(M[i] - M[i].mean())) for i, n in enumerate(names)}
    return {"profiles_over": [js[i] for i in keep], "n_profiles": len(names),
            "mean_pairwise_centred_cosine": float(np.mean(cc)) if cc else math.nan,
            "mean_pairwise_raw_cosine": float(np.mean(rc)) if rc else math.nan,
            "exists": bool(cc and np.mean(cc) >= LADDER_COS_MIN), "matrix": mat, "between_survivor_sd": sd}


def branch(share_ci: tuple[float, float], vtot_ci: tuple[float, float], aim: float | None, aim_p95: float | None,
           ladder: bool, n_rows: int = 1) -> str:
    if n_rows == 0:
        return "NOT RUN (no scored rows)"
    if not np.isfinite(vtot_ci[0]) or vtot_ci[0] <= 0:
        return "PURE SUBTRACTION"
    if share_ci[0] > 0.5 and aim is not None and aim_p95 is not None and aim > aim_p95:
        return "SUBSTITUTION"
    if share_ci[0] > 0.5:
        return "X-SPECIFIC-UNAIMED"
    if share_ci[1] < 0.5 and ladder:
        return "LADDER"
    return "UNDETERMINED"


def run_c1(tds: dict[str, TaskData], vname: str = "primary", u_kind: str = "primary", ref: str = "neutral",
           ess_weight: bool = False, n_boot: int = N_BOOT, n_perm: int = N_PERM, full: bool = True,
           templates_all: list[str] | None = None) -> dict[str, Any]:
    templates_all = templates_all or WS
    assoc = read_json(RESULTS / "association.json")["profiles"]
    res: dict[str, Any] = {"variant": vname, "u_kind": u_kind, "reference": ref, "ess_weighted": ess_weight,
                           "tasks": {}}
    per_task_rows, boot_comp = {}, {}
    aim_pairs_pv, aim_pairs_as, aim_vals_pv, aim_vals_as = [], [], [], []
    for t in TASKS:
        td = tds[t]
        conds, virtual = needed_conds(t)
        e2 = edit2_conds(td)
        ca = CellArrays(td, conds + e2, vname, virtual)
        L, E = ca.cells(with_ess=True)
        cx = Ctx(ca, L, E)
        cx_u = None
        if VARIANTS[vname][3] == "unscrubbed":
            ca_u = CellArrays(td, conds + e2, "primary", virtual)
            cx_u = Ctx(ca_u, ca_u.cells())
        pt = task_point(td, ca, cx, templates_all, RAND_NAMES, u_kind, ref, ess_weight, e2, cx_u)
        rows = pt["rows"]
        per_task_rows[t] = rows
        js = ca.js
        tr: dict[str, Any] = {"measurable": js, "u": dict(zip(js, pt["u"].tolist())),
                              "family_profiles": {k: dict(zip(js, v.tolist())) for k, v in pt["fp"].items()},
                              "share_point": pt["share"], "share_point_projection_noise": pt["share_proj"],
                              "rows": {}}
        # AIM per row
        row_aim = {}
        for r in rows:
            B, S = r["B"], r["survivors"]
            idx = np.array([js.index(j) for j in S])
            pv1 = pv_profile(cx, B, templates_all, "h1", idx)
            pv2 = pv_profile(cx, B, templates_all, "h2", idx)
            rho = np.nanmean([_spearman(r["s_h1"], pv2), _spearman(r["s_h2"], pv1)])
            a_prof = np.array([assoc.get(f"{t}|{B}", {}).get(j, math.nan) for j in S])
            rho_as = _spearman(r["s"], a_prof) if np.isfinite(a_prof).all() else math.nan
            aim_pairs_pv.append([(r["s_h1"], pv2), (r["s_h2"], pv1)])
            aim_vals_pv.append(rho)
            if np.isfinite(rho_as):
                aim_pairs_as.append([(r["s"], a_prof)])
                aim_vals_as.append(rho_as)
            row_aim[B] = {"rho_pv": rho, "rho_assoc": rho_as, "pv_h1": dict(zip(S, pv1.tolist())),
                          "pv_h2": dict(zip(S, pv2.tolist())), "assoc": dict(zip(S, a_prof.tolist()))}
            tr["rows"][B] = {"survivors": S, "Gbar": dict(zip(S, r["Gbar"].tolist())),
                             "fitted_ladder": dict(zip(S, (r["a"] * r["uhat"]).tolist())),
                             "s": dict(zip(S, r["s"].tolist())), "a": r["a"], "a2": r["a2"], "ss_s": r["ss_s"],
                             "tot_noise": r["tot_noise"], "N_u": r["N_u"], "N_s": r["N_s"],
                             "n_flagged_cells": r["n_flagged_cells"],
                             "median_ess": dict(zip(S, np.nan_to_num(r["median_ess"], nan=-1).tolist())),
                             "cos_with_u": float(r["a"] / (math.sqrt(r["ss_G"]) + 1e-12)),
                             "replicate_sd": float(math.sqrt(r["tot_noise"] * r["R"] / len(S))),
                             "between_survivor_sd": float(np.std(r["Gbar"])), **row_aim[B]}
        tr["aim_rows"] = {B: v["rho_pv"] for B, v in row_aim.items()}
        tr["aim"] = float(np.nanmean([v["rho_pv"] for v in row_aim.values()])) if row_aim else math.nan
        if full:
            tr["ladder_exists"] = ladder_exists(cx, td, templates_all)
            fpA = family_profiles(cx, templates_all, RAND_NAMES[:3])["RAND"]
            fpB = family_profiles(cx, templates_all, RAND_NAMES[3:])["RAND"]
            n1 = family_profiles(cx, templates_all, RAND_NAMES, half="h1")["NONCE"]
            n2 = family_profiles(cx, templates_all, RAND_NAMES, half="h2")["NONCE"]
            tr["u_reliability"] = {
                "rand_A_vs_B_pearson": float(np.corrcoef(fpA, fpB)[0, 1]) if np.isfinite(fpA).all() and np.isfinite(fpB).all() else math.nan,
                "nonce_h1_vs_h2_pearson": float(np.corrcoef(n1, n2)[0, 1]) if np.isfinite(n1).all() and np.isfinite(n2).all() else math.nan}
            # per-ban extras
            extras = {}
            for r in rows:
                B, S = r["B"], r["survivors"]
                idx = np.array([js.index(j) for j in S])
                prime = np.nanmean([(cx.v(f"mention|{B}|{w}") - cx.v(f"neutral|{B}|{w}|AB"))[idx] for w in templates_all], axis=0)
                veto = np.nanmean([(cx.v(f"ban|{B}|{w}") - cx.v(f"mention|{B}|{w}"))[idx] for w in templates_all], axis=0)
                pc, vc = prime - prime.mean(), veto - veto.mean()
                vt = float(np.sum((pc + vc) ** 2))
                D = None
                if B in js:
                    k = js.index(B)
                    D = float(np.nanmean([cx.v(f"ban|{B}|{w}")[k] - cx.v(f"neutral|{B}|{w}|AB")[k] for w in templates_all]))
                cos_other = {}
                for r2 in rows:
                    if r2["B"] == B:
                        continue
                    common = [j for j in S if j in r2["survivors"]]
                    if len(common) >= 3:
                        a1 = np.array([r["Gbar"][S.index(j)] for j in common])
                        a2 = np.array([r2["Gbar"][r2["survivors"].index(j)] for j in common])
                        a1c, a2c = a1 - a1.mean(), a2 - a2.mean()
                        cos_other[r2["B"]] = float(a1c @ a2c / (np.linalg.norm(a1c) * np.linalg.norm(a2c) + 1e-12))
                extras[B] = {"subtraction_strength_D": D, "prime": dict(zip(S, prime.tolist())),
                             "veto": dict(zip(S, veto.tolist())),
                             "prime_share_of_ss": float(np.sum(pc ** 2) / vt) if vt > 0 else math.nan,
                             "veto_share_of_ss": float(np.sum(vc ** 2) / vt) if vt > 0 else math.nan,
                             "prime_veto_cross_share": float(2 * np.sum(pc * vc) / vt) if vt > 0 else math.nan,
                             "centred_cos_with_other_bans": cos_other}
            tr["extras"] = extras
            prox = proximity(t, js)
            tr["proximity"] = {B: (_spearman(np.array(list(tr["rows"][B]["s"].values())),
                                             np.array([prox[B][j] for j in tr["rows"][B]["survivors"]]))
                                   if B in prox else math.nan) for B in tr["rows"]}
        # bootstrap
        if n_boot:
            rng = np.random.default_rng(SEED_BOOT + (0 if t == "t1" else 1))
            comps = []
            for _b in range(n_boot):
                tw = list(rng.choice(templates_all, size=len(templates_all), replace=True))
                dw = list(rng.choice(RAND_NAMES, size=len(RAND_NAMES), replace=True))
                W = ca.boot_weights(rng)
                Lb = ca.cells(W)
                cb = Ctx(ca, Lb, E)
                pb = task_point(td, ca, cb, tw, dw, u_kind, ref, ess_weight, e2, cx_u)
                sh = pb["share"]
                srow = {r["B"]: r["s"] for r in pb["rows"]}
                comps.append({"V_u": sh["V_u"], "V_s": sh["V_s"], "SHARE": sh["SHARE"], "srow": srow,
                              "Gbar": {r["B"]: r["Gbar"] for r in pb["rows"]},
                              "surv": {r["B"]: r["survivors"] for r in pb["rows"]}})
            boot_comp[t] = comps
            tr["bootstrap"] = _ci_block(comps)
        res["tasks"][t] = tr
    # pooled
    pooled_rows = per_task_rows["t1"] + per_task_rows["t2"]
    res["pooled"] = {"share_point": share_from_rows(pooled_rows),
                     "share_point_projection_noise": share_from_rows(pooled_rows, True)}
    if n_boot:
        def _sh(a, b):
            den = a["V_u"] + b["V_u"] + a["V_s"] + b["V_s"]
            return (a["V_s"] + b["V_s"]) / den if den != 0 else math.nan

        pc = [{"V_u": a["V_u"] + b["V_u"], "V_s": a["V_s"] + b["V_s"], "SHARE": _sh(a, b)}
              for a, b in zip(boot_comp["t1"], boot_comp["t2"])]
        res["pooled"]["bootstrap"] = _ci_block(pc)
    # AIM nulls
    if n_perm:
        null = perm_null(aim_pairs_pv, n_perm, 99)
        aim = float(np.nanmean(aim_vals_pv))
        res["aim_prime_veto"] = {"aim": aim, "null_p95": float(np.quantile(null, 0.95)),
                                 "p": float((np.sum(null >= aim - 1e-12) + 1) / (len(null) + 1)), "n_rows": len(aim_vals_pv)}
        if aim_pairs_as:
            null2 = perm_null(aim_pairs_as, n_perm, 98)
            aim2 = float(np.nanmean(aim_vals_as))
            res["aim_association"] = {"aim": aim2, "null_p95": float(np.quantile(null2, 0.95)),
                                      "p": float((np.sum(null2 >= aim2 - 1e-12) + 1) / (len(null2) + 1)),
                                      "n_rows": len(aim_vals_as)}
        for t in TASKS:
            idx = [i for i, r in enumerate(pooled_rows) if r in per_task_rows[t]]
            sub = [aim_pairs_pv[i] for i in idx]
            if sub:
                nt = perm_null(sub, n_perm // 4, 97)
                res["tasks"][t]["aim_null_p95"] = float(np.quantile(nt, 0.95))
                res["tasks"][t]["aim_p"] = float((np.sum(nt >= res["tasks"][t]["aim"] - 1e-12) + 1) / (len(nt) + 1))
    # branches
    if n_boot:
        for t in TASKS:
            tr = res["tasks"][t]
            bs = tr["bootstrap"]
            le = tr.get("ladder_exists", {}).get("exists", False)
            tr["branch"] = branch(bs["SHARE_ci"], bs["V_tot_ci"], tr["aim"], tr.get("aim_null_p95"), le,
                                  len(per_task_rows[t]))
        bs = res["pooled"]["bootstrap"]
        le_all = all(res["tasks"][t].get("ladder_exists", {}).get("exists", False) for t in TASKS)
        ap = res.get("aim_prime_veto", {})
        res["pooled"]["branch"] = branch(bs["SHARE_ci"], bs["V_tot_ci"], ap.get("aim"), ap.get("null_p95"), le_all,
                                         len(pooled_rows))
        res["pooled"]["ladder_exists_both_tasks"] = le_all
    if n_boot and full:
        res["sham_observations_7_1"] = sham_obs(res, boot_comp)
    return res


def _ci_block(comps: list[dict[str, Any]]) -> dict[str, Any]:
    def ci(key):
        v = np.array([c[key] for c in comps], dtype=float)
        v = v[np.isfinite(v)]
        return (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) if len(v) else (math.nan, math.nan)

    vt = np.array([c["V_u"] + c["V_s"] for c in comps])
    return {"n_boot": len(comps), "SHARE_ci": ci("SHARE"), "V_u_ci": ci("V_u"), "V_s_ci": ci("V_s"),
            "V_tot_ci": (float(np.quantile(vt, 0.025)), float(np.quantile(vt, 0.975)))}


def sham_obs(res: dict[str, Any], boot: dict[str, list]) -> dict[str, Any]:
    """7.1: row floyd (t2): is s(bf_spfa) the largest residual and > 0; row iddfs (t1): same for dfs."""
    out = {}
    for t, B, j in (("t2", "floyd", "bf_spfa"), ("t1", "iddfs", "dfs")):
        row = res["tasks"][t]["rows"].get(B)
        if not row or j not in row["s"]:
            out[f"{t}|{B}->{j}"] = None
            continue
        s = row["s"]
        vals = [c["srow"][B][c["surv"][B].index(j)] for c in boot[t] if B in c["srow"]]
        largest = [float(np.argmax(c["srow"][B]) == c["surv"][B].index(j)) for c in boot[t] if B in c["srow"]]
        out[f"{t}|{B}->{j}"] = {"s_j": s[j], "is_largest_residual": max(s, key=s.get) == j,
                                "residual_positive": s[j] > 0,
                                "s_j_ci": (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))),
                                "boot_prob_largest": float(np.mean(largest)),
                                "G_j": row["Gbar"][j], "fitted_ladder_j": row["fitted_ladder"][j]}
    return out


def shams_and_two_step(tds: dict[str, TaskData]) -> dict[str, Any]:
    """7.3 off-catalogue shams (descriptive stratum) and 7.2 two-step landing under the frozen templates."""
    out: dict[str, Any] = {"shams": {}, "two_step": {}}
    for t in TASKS:
        td = tds[t]
        conds, virtual = needed_conds(t)
        ca = CellArrays(td, conds, "primary", virtual)
        cx = Ctx(ca, ca.cells())
        js = ca.js
        u = ladder_u(family_profiles(cx, WS, RAND_NAMES))
        uc = u - u.mean()
        uhat = uc / (np.linalg.norm(uc) + 1e-12)
        for x in SHAMS[t]:
            reps = []
            for w in WS:
                for h, ns in (("h1", "A"), ("h2", "B")):
                    g = cx.v(f"ban|{x}|{w}", h) - cx.v(f"neutral|{x}|{w}|{ns}", h)
                    reps.append(g - np.nanmean(g))
            G = np.nanmean(reps, axis=0)
            if not np.isfinite(G).all():
                out["shams"][f"{t}|{x}"] = {"scored": False}
                continue
            a = float(G @ uhat)
            s = G - a * uhat
            order = [js[i] for i in np.argsort(-s)]
            neigh = [j for j in SHAM_NEIGHBOURS[x] if j in js]
            out["shams"][f"{t}|{x}"] = {"scored": True, "Gbar": dict(zip(js, G.tolist())),
                                        "residual": dict(zip(js, s.tolist())), "a_ladder": a,
                                        "residual_rank_order": order, "declared_neighbours": neigh,
                                        "neighbours_top_k": bool(set(order[:len(neigh)]) == set(neigh)) if neigh else None,
                                        "neighbour_mean_rank": float(np.mean([order.index(j) + 1 for j in neigh])) if neigh else None}
        banned = {"t1": ["bfs", "dfs"], "t2": ["dijkstra", "bf_spfa"]}[t]
        land = []
        bm = []
        for w in WS:
            Lv = cx.v(f"ban|two_step|{w}")
            if not np.isfinite(Lv).any():
                continue
            p = np.exp(Lv - np.nanmax(Lv))
            p = np.where(np.isfinite(p), p, 0.0)
            p /= p.sum()
            bm.append(float(sum(p[js.index(b)] for b in banned if b in js)))
            allowed = [i for i, j in enumerate(js) if j not in banned]
            q = p[allowed] / max(1e-300, p[allowed].sum())
            land.append(dict(zip([js[i] for i in allowed], q.tolist())))
        if land:
            keys = land[0].keys()
            out["two_step"][t] = {"implied_landing_frozen_templates": {k: float(np.mean([d[k] for d in land])) for k in keys},
                                  "implied_banned_mass_frozen_templates": float(np.mean(bm)), "n_templates": len(land)}
    return out


@logger.catch(reraise=True)
def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--sens-boot", type=int, default=400)
    args = ap.parse_args()
    setup_logging("c1")
    tds = build_task_data()
    out: dict[str, Any] = {"utc": utc_now()}
    gate = read_json(RESULTS / "gate.json") if (RESULTS / "gate.json").exists() else None
    out["frlp_status"] = ("FRLP gate passed" if gate and gate["primary"]["pass"] else
                          "descriptive: FRLP gate failed" if gate else "gate not computed")
    out["primary_neutral"] = run_c1(tds, "primary", "primary", "neutral", n_boot=args.n_boot, n_perm=args.n_perm)
    out["reference_mention"] = run_c1(tds, "primary", "primary", "mention", n_boot=args.n_boot, n_perm=args.n_perm,
                                      full=False)
    out["ess_weighted"] = run_c1(tds, "primary", "primary", "neutral", ess_weight=True, n_boot=args.n_boot,
                                 n_perm=args.n_perm, full=False)
    br = [out[k]["pooled"].get("branch") for k in ("primary_neutral", "reference_mention", "ess_weighted")]
    out["robust_pooled"] = bool(len(set(br)) == 1)
    out["branches"] = {k: {"pooled": out[k]["pooled"].get("branch"),
                           **{t: out[k]["tasks"][t].get("branch") for t in TASKS}}
                       for k in ("primary_neutral", "reference_mention", "ess_weighted")}
    write_json(RESULTS / "c1.json", out)
    logger.info(f"C1 branches: {out['branches']}")
    # 7.4 sensitivity
    sens: dict[str, Any] = {}
    for v in ("code_body_only", "correct_only", "single_proposal", "truncated_256"):
        try:
            r = run_c1(tds, v, "primary", "neutral", n_boot=args.sens_boot, n_perm=20000, full=False)
            sens[f"variant:{v}"] = _sens_summary(r)
        except (KeyError, ValueError, ZeroDivisionError) as e:
            sens[f"variant:{v}"] = {"error": f"{type(e).__name__}: {e}"}
    for uk in ("with_ii", "unit_normalised", "only_NONCE", "only_RAND", "only_NOV"):
        try:
            r = run_c1(tds, "primary", uk, "neutral", n_boot=args.sens_boot, n_perm=20000, full=False)
            sens[f"u:{uk}"] = _sens_summary(r)
        except (KeyError, ValueError, ZeroDivisionError) as e:
            sens[f"u:{uk}"] = {"error": f"{type(e).__name__}: {e}"}
    for v in ("unscrubbed", "unscrubbed_body_single"):
        try:
            r = run_c1(tds, v, "primary", "neutral", n_boot=args.sens_boot, n_perm=20000, full=False,
                       templates_all=["W1"])
            sens[f"variant:{v}_W1_only"] = _sens_summary(r)
        except (KeyError, ValueError, ZeroDivisionError, IndexError) as e:
            sens[f"variant:{v}_W1_only"] = {"error": f"{type(e).__name__}: {e}"}
    # the same W1-only reduction on the primary (scrubbed) scores, for a like-for-like comparison
    try:
        r = run_c1(tds, "primary", "primary", "neutral", n_boot=args.sens_boot, n_perm=20000, full=False,
                   templates_all=["W1"])
        sens["variant:primary_W1_only"] = _sens_summary(r)
    except (KeyError, ValueError, ZeroDivisionError, IndexError) as e:
        sens["variant:primary_W1_only"] = {"error": f"{type(e).__name__}: {e}"}
    write_json(RESULTS / "sensitivity.json", sens)
    write_json(RESULTS / "secondary.json", shams_and_two_step(tds))
    logger.info("sensitivity + secondary written")


def _sens_summary(r: dict[str, Any]) -> dict[str, Any]:
    return {"pooled_share_point": r["pooled"]["share_point"], "pooled_bootstrap": r["pooled"].get("bootstrap"),
            "pooled_branch": r["pooled"].get("branch"), "aim_prime_veto": r.get("aim_prime_veto"),
            "per_task": {t: {"share_point": r["tasks"][t]["share_point"], "branch": r["tasks"][t].get("branch"),
                             "aim": r["tasks"][t].get("aim")} for t in TASKS}}


if __name__ == "__main__":
    main()
