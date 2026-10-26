#!/usr/bin/env python3
"""DECOMPOSITION (causal; committed reading rule): is the plan component of confirmed escaping pushes necessary and
sufficient?

For each listed (task, direction u, escaping alpha): arms on the same CRN slots k 0-3 x W1-W5 (N = 20):
  original POP (U_l = u), UPERP (u with its P_t component removed, renormalised), UP (only the P_t component,
  renormalised = amplified), optional CLAMP (u with the realised displacement's P_t component clamped to 0).
R_arm = (share_arm - share_twin) / (share_orig - share_twin), slots shared by all arms (twin on k 0-3 too).
CI: CRN-paired bootstrap of the 20 slots (2,000 resamples), all arms resampled together.
Reading per task (median over its listed directions; bootstrap over slots within direction, directions resampled):
  'P_t not needed' if median R_uperp >= 0.7 with lower bound >= 0.4; 'Necessary' if median R_uperp <= 0.3 with
  upper bound <= 0.5; 'Sufficient (amplified)' if u_P passes the escape rule at N = 20 (excess >= 0.20 over the
  N = 50 twin, one-sided binomial p < 0.05 vs p0, pass >= 0.8 x twin) for the majority of the task's directions;
  otherwise 'mixed'. Landing comparison: JS(u_P landing, original landing) vs a slot-resampling null.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from common import binom_greater_p, dist, js, share

SLOTS = [0, 1, 2, 3]


def _slot_vec(rows: list[dict[str, Any]], arm: str, cat: set[str], default: str) -> dict[tuple[str, int], dict]:
    return {(r["template"], int(r["sample_id"])): r for r in rows if r["arm"] == arm and int(r["sample_id"]) in SLOTS}


def r_ratio(sa: float, so: float, st: float) -> float:
    den = so - st
    return float((sa - st) / den) if abs(den) > 1e-12 else float("nan")


def analyse_direction(rows: list[dict[str, Any]], seed: int, alpha: float, cat: set[str], default: str,
                      twin_all: list[dict[str, Any]], n_boot: int = 2000, seed_rng: int = 0) -> dict[str, Any]:
    arms = {"orig": f"POP_d{seed}_a{alpha}", "uperp": f"UPERP_d{seed}_a{alpha}", "up": f"UP_d{seed}_a{alpha}",
            "clamp": f"CLAMP_d{seed}_a{alpha}"}
    sv = {k: _slot_vec(rows, a, cat, default) for k, a in arms.items()}
    sv["twin"] = _slot_vec(rows, "TWIN", cat, default)
    keys = sorted(set(sv["orig"]) & set(sv["twin"]) & set(sv["uperp"]))
    if not keys:
        return {"n_slots": 0}

    def off(r):
        return int(r["label"] in cat and r["label"] != default) if r["label"] not in ("invalid", "disputed") else np.nan

    mat = {k: np.array([off(sv[k][s]) if s in sv[k] else np.nan for s in keys], float) for k in sv}
    res: dict[str, Any] = {"n_slots": len(keys)}
    shares = {k: float(np.nanmean(v)) if np.isfinite(v).any() else float("nan") for k, v in mat.items()}
    res["shares"] = shares
    for a in ("uperp", "up", "clamp"):
        res[f"R_{a}"] = r_ratio(shares[a], shares["orig"], shares["twin"]) if np.isfinite(mat[a]).any() else None
    rng = np.random.default_rng(seed_rng)
    boots = {a: [] for a in ("uperp", "up", "clamp")}
    n = len(keys)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        sh = {k: np.nanmean(v[idx]) if np.isfinite(v[idx]).any() else np.nan for k, v in mat.items()}
        for a in boots:
            if np.isfinite(mat[a]).any():
                boots[a].append(r_ratio(sh[a], sh["orig"], sh["twin"]))
    for a, b in boots.items():
        b = np.array([x for x in b if np.isfinite(x)])
        res[f"R_{a}_ci"] = [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))] if len(b) > 20 else None
    # u_P sufficiency (escape rule at N = 20 vs the committed twin, N = 50)
    tw = share(twin_all, cat, default)
    p0 = (tw["k_off"] + 0.5) / (tw["n_valid"] + 1)
    up_rows = [sv["up"][s] for s in keys if s in sv["up"]]
    su = share(up_rows, cat, default)
    res["up_escape"] = {"share": su["share"], "pass": su["pass"], "excess": su["share"] - tw["share"],
                        "binom_p": binom_greater_p(su["k_off"], su["n_valid"], p0),
                        "passes": bool(su["share"] - tw["share"] >= 0.2 - 1e-12 and
                                       binom_greater_p(su["k_off"], su["n_valid"], p0) < 0.05 and
                                       su["pass"] >= 0.8 * tw["pass"] - 1e-12)}
    # landing comparison u_P vs original
    lo = [sv["orig"][s]["label"] for s in keys if sv["orig"][s]["label"] in cat and sv["orig"][s]["label"] != default]
    lu = [sv["up"][s]["label"] for s in keys if s in sv["up"] and sv["up"][s]["label"] in cat and
          sv["up"][s]["label"] != default]
    res["landing_orig"] = dist(lo)
    res["landing_up"] = dist(lu)
    if lo and lu:
        obs = js(dist(lo), dist(lu))
        pool = lo + lu
        null = []
        for _ in range(500):
            p = rng.permutation(pool)
            null.append(js(dist(list(p[:len(lo)])), dist(list(p[len(lo):]))))
        res["landing_js"] = {"js": obs, "null_q95": float(np.quantile(null, 0.95))}
    for k in ("uperp", "up", "clamp"):
        res[f"pass_{k}"] = share([sv[k][s] for s in keys if s in sv[k]], cat, default)["pass"] if sv[k] else None
    res["pass_orig"] = share([sv["orig"][s] for s in keys], cat, default)["pass"]
    return res


def reading(dirs: list[dict[str, Any]], n_boot: int = 2000, seed: int = 0) -> dict[str, Any]:
    vals = [d["R_uperp"] for d in dirs if d.get("R_uperp") is not None and np.isfinite(d["R_uperp"])]
    if not vals:
        return {"reading": "not evaluable", "n": 0}
    med = float(np.median(vals))
    rng = np.random.default_rng(seed)
    bs = [float(np.median(rng.choice(vals, len(vals)))) for _ in range(n_boot)]
    # add within-direction slot uncertainty: widen by the mean CI half-width when directions are few
    halfw = np.nanmean([(d["R_uperp_ci"][1] - d["R_uperp_ci"][0]) / 2 for d in dirs if d.get("R_uperp_ci")]) \
        if any(d.get("R_uperp_ci") for d in dirs) else 0.0
    lo = min(float(np.quantile(bs, 0.025)), med - halfw / max(np.sqrt(len(vals)), 1))
    hi = max(float(np.quantile(bs, 0.975)), med + halfw / max(np.sqrt(len(vals)), 1))
    suff = sum(bool(d.get("up_escape", {}).get("passes")) for d in dirs)
    if med >= 0.7 and lo >= 0.4:
        rd = "P_t not needed"
    elif med <= 0.3 and hi <= 0.5:
        rd = "Necessary"
    else:
        rd = None
    if suff > len(dirs) / 2:
        rd = (rd + " + " if rd else "") + "Sufficient (amplified)"
    return {"reading": rd or "mixed", "median_R_uperp": med, "ci": [lo, hi], "n_directions": len(vals),
            "n_up_sufficient": suff, "median_R_up": float(np.nanmedian([d["R_up"] for d in dirs
                                                                       if d.get("R_up") is not None]))}
