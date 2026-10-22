#!/usr/bin/env python3
"""STEP 8 - analysis (hash-committed in commit #0; descriptive figures live in src/figures.py).

Inputs: data/samples.jsonl (one row per generated program, with ooc_screen / distinct_id / cluster_id / final_class)
and results/adjudication.json. Outputs: results/arm_rates.json, ratio_tests.json, matched_effort.json, lineage.json,
dynamics.json, placebo.json, verdict.json.

PRIMARY per task: X_S/N_S vs X_K/N_K at level a (distinct OOC_screen programs), K = whichever of EAP and BINT has the
higher level-a rate (max rule). Exact conditional test: X_S | X_S + X_K ~ Binomial(m, p), p(R) = N_S R / (N_S R + N_K).
LB95 = one-sided 95% Clopper-Pearson lower bound of p mapped to R = p N_K / (N_S (1 - p)); two-sided 95% CI beside it.
VERDICT: STRONG if LB95 >= 10; MET if R_hat >= 10 and LB95 > 1; UNRESOLVED if R_hat >= 10 and LB95 <= 1; NOT MET if
R_hat < 10; NOT ESTIMABLE if X_S = X_K = 0 (X_K = 0 < X_S: R_hat infinite, verdict from LB95). Overall MET if >= 2 tasks
are MET or STRONG (2 tasks run: both). Holm-adjusted one-sided p for R > 1 across tasks. Same test at level b.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from scipy import stats

ARMS = ("S", "NE", "I0", "EAP", "BINT", "B0")
FLOORS = {"S": 1000, "EAP": 400, "BINT": 400, "NE": 300, "I0": 300, "B0": 100}
SECONDARY = [("S", "NE"), ("S", "I0"), ("NE", "I0"), ("I0", "K"), ("K", "B0")]


# ------------------------------------------------------------------------------------------------ statistics
def rate_ratio_test(xs: int, ns: int, xk: int, nk: int, alpha: float = 0.05) -> dict[str, Any]:
    """Exact conditional binomial test of two Poisson rates (S over K)."""
    m = xs + xk
    out: dict[str, Any] = {"X_S": xs, "N_S": ns, "X_K": xk, "N_K": nk, "m": m}
    if ns <= 0 or nk <= 0:
        out.update(R_hat=None, LB95=None, CI95=[None, None], p_one_sided=None, estimable=False)
        return out
    if m == 0:
        out.update(R_hat=None, LB95=None, CI95=[None, None], p_one_sided=1.0, estimable=False)
        return out
    r_hat = (xs / ns) / (xk / nk) if xk > 0 else math.inf
    to_r = (lambda p: p * nk / (ns * (1.0 - p)) if p < 1.0 else math.inf)
    p_lo1 = stats.beta.ppf(alpha, xs, m - xs + 1) if xs > 0 else 0.0
    p_lo2 = stats.beta.ppf(alpha / 2, xs, m - xs + 1) if xs > 0 else 0.0
    p_hi2 = stats.beta.ppf(1 - alpha / 2, xs + 1, m - xs) if xs < m else 1.0
    p0 = ns / (ns + nk)
    p_one = float(stats.binom.sf(xs - 1, m, p0))      # P(X >= xs | R = 1)
    out.update(R_hat=r_hat, LB95=to_r(p_lo1), CI95=[to_r(p_lo2), to_r(p_hi2)], p_one_sided=p_one, estimable=True)
    return out


def verdict_of(t: dict[str, Any]) -> str:
    if not t.get("estimable"):
        return "NOT ESTIMABLE"
    r, lb = t["R_hat"], t["LB95"]
    if lb is not None and lb >= 10:
        return "STRONG"
    if r is not None and r >= 10:
        return "MET" if lb > 1 else "UNRESOLVED"
    return "NOT MET"


def holm(pvals: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted([(p, k) for k, p in pvals.items() if p is not None])
    m = len(items)
    adj: dict[str, float | None] = {k: None for k in pvals}
    run = 0.0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        adj[k] = run
    return adj


def rule_of_three(n: int) -> float | None:
    return 3.0 / n if n > 0 else None


def poisson_ci(x: int, n: int, alpha: float = 0.05) -> list[float | None]:
    if n <= 0:
        return [None, None]
    lo = stats.chi2.ppf(alpha / 2, 2 * x) / 2 if x > 0 else 0.0
    hi = stats.chi2.ppf(1 - alpha / 2, 2 * x + 2) / 2
    return [lo / n, hi / n]


def hill1(labels: list[str]) -> float | None:
    if not labels:
        return None
    c = np.array(list(Counter(labels).values()), dtype=float)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


# ------------------------------------------------------------------------------------------------ matched effort
def rarefy_extrapolate(cluster_counts: list[int], n_calls: int, m: int) -> dict[str, Any]:
    """Abundance-based (calls as individuals) rarefaction / Chao-1 extrapolation of cluster richness to m calls
    (Chao et al. 2014; extrapolation trusted to 2x the reference sample)."""
    x = [c for c in cluster_counts if c > 0]
    s_obs = len(x)
    n = n_calls
    res: dict[str, Any] = {"S_obs": s_obs, "n": n, "m": m, "trusted": m <= 2 * n}
    if n <= 0:
        res["S_m"] = None
        return res
    if m <= n:
        lg = math.lgamma
        def lc(a: int, b: int) -> float:
            return lg(a + 1) - lg(b + 1) - lg(a - b + 1) if 0 <= b <= a else -math.inf
        s = 0.0
        for xi in x:
            s += 1.0 - (math.exp(lc(n - xi, m) - lc(n, m)) if n - xi >= m else 0.0)
        res["S_m"] = s
        res["mode"] = "rarefaction"
        return res
    f1 = sum(1 for c in x if c == 1)
    f2 = sum(1 for c in x if c == 2)
    f0 = (n - 1) / n * (f1 * f1 / (2 * f2) if f2 > 0 else f1 * (f1 - 1) / 2)
    ms = m - n
    if f0 > 0 and f1 > 0:
        s = s_obs + f0 * (1 - (1 - f1 / (n * f0 + f1)) ** ms)
    else:
        s = float(s_obs)
    res.update(S_m=s, mode="extrapolation", f1=f1, f2=f2, f0_hat=f0, chao1=s_obs + f0)
    return res


def island_bootstrap(per_island: list[tuple[int, int]], reps: int = 2000, seed: int = 7) -> dict[str, Any]:
    """Island-cluster bootstrap of S's rate: resample islands with replacement."""
    if not per_island:
        return {}
    rng = random.Random(seed)
    rates = []
    k = len(per_island)
    for _ in range(reps):
        pick = [per_island[rng.randrange(k)] for _ in range(k)]
        n = sum(p[1] for p in pick)
        rates.append(sum(p[0] for p in pick) / n if n else 0.0)
    rates.sort()
    return {"rate_lo95": rates[int(0.025 * reps)], "rate_hi95": rates[int(0.975 * reps) - 1],
            "rate_median": rates[reps // 2], "reps": reps}


# ------------------------------------------------------------------------------------------------ tables
def arm_counts(rows: list[dict[str, Any]], task: str, arm: str, level: str = "a",
               max_calls: int | None = None) -> dict[str, Any]:
    """Counts for one task x arm. level a = distinct OOC_screen programs; level b = distinct adjudicated
    KNOWN OUTSIDE CATALOGUE + NOVEL ALGORITHM programs."""
    rs = sorted([r for r in rows if r["task"] == task and r["arm"] == arm], key=lambda r: r["slot"])
    if max_calls is not None:
        rs = rs[:max_calls]
    n = len(rs)
    corr = [r for r in rs if r.get("correct")]
    ooc = [r for r in corr if r.get("ooc_screen")]
    xa = len({r["distinct_id"] for r in ooc if r.get("distinct_id")})
    lb = [r for r in ooc if r.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")]
    xb = len({r["distinct_id"] for r in lb if r.get("distinct_id")})
    novel = len({r["distinct_id"] for r in ooc if r.get("final_class") == "NOVEL ALGORITHM"})
    clusters_a = {r["cluster_id"] for r in ooc if r.get("cluster_id")}
    clusters_b = {r.get("merged_cluster_id") or r["cluster_id"] for r in lb if r.get("cluster_id")}
    return {"task": task, "arm": arm, "N": n, "valid": sum(1 for r in rs if r.get("valid")),
            "correct": len(corr), "correct_default": sum(1 for r in corr if r.get("label") == r.get("default_label")),
            "ooc_screen_programs": len(ooc), "X_a": xa, "X_b": xb, "novel": novel,
            "clusters_a": len(clusters_a), "clusters_b": len(clusters_b),
            "hill1_correct_labels": hill1([r.get("label") or "unlabelled" for r in corr]),
            "gpu_seconds": round(sum(float(r.get("gpu_seconds") or 0) for r in rs), 2),
            "usd": round(sum(float(r.get("usd") or 0) for r in rs), 4),
            "rate_a": xa / n if n else None, "rate_a_ci95": poisson_ci(xa, n),
            "rate_b": xb / n if n else None, "rate_b_ci95": poisson_ci(xb, n),
            "rule_of_three_a": rule_of_three(n) if xa == 0 else None,
            "rule_of_three_b": rule_of_three(n) if xb == 0 else None,
            "label_mix": dict(Counter(r.get("label") or "unlabelled" for r in corr)),
            "descriptive_only": n < FLOORS.get(arm, 0)}


def pick_k(tab: dict[str, dict[str, Any]], level: str) -> str:
    key = "rate_" + level
    cands = [a for a in ("EAP", "BINT") if a in tab and tab[a]["N"] > 0]
    if not cands:
        return "EAP"
    return max(cands, key=lambda a: ((tab[a][key] or 0.0), a == "EAP"))


def primary_tests(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"per_task": {}, "levels": {}}
    for level in ("a", "b"):
        per = {}
        pv = {}
        for t in tasks:
            tab = {a: arm_counts(rows, t, a, level) for a in ARMS}
            if tab["S"]["N"] == 0:
                continue
            k = pick_k(tab, level)
            x = "X_" + level
            test = rate_ratio_test(tab["S"][x], tab["S"]["N"], tab[k][x], tab[k]["N"])
            test["K_arm"] = k
            test["verdict"] = verdict_of(test)
            sec = {}
            for a, b in SECONDARY:
                aa = k if a == "K" else a
                bb = k if b == "K" else b
                if tab[aa]["N"] and tab[bb]["N"]:
                    st = rate_ratio_test(tab[aa][x], tab[aa]["N"], tab[bb][x], tab[bb]["N"])
                    st["verdict_if_primary_rule"] = verdict_of(st)
                    sec[f"{a}_vs_{b}" + (f"({k})" if "K" in (a, b) else "")] = st
            test["secondary"] = sec
            per[t] = test
            pv[t] = test["p_one_sided"]
        adj = holm(pv)
        for t in per:
            per[t]["p_holm"] = adj.get(t)
        n_met = sum(1 for t in per if per[t]["verdict"] in ("MET", "STRONG"))
        need = 2 if len(per) >= 2 else 1
        overall = "MET" if n_met >= need else ("NOT ESTIMABLE" if all(per[t]["verdict"] == "NOT ESTIMABLE"
                                                                       for t in per) else "NOT MET")
        out["levels"][level] = {"per_task": per, "n_tasks_met_or_strong": n_met, "needed": need, "overall": overall}
    return out


def matched_effort(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    out = {}
    for t in tasks:
        ns = sum(1 for r in rows if r["task"] == t and r["arm"] == "S")
        if ns == 0:
            continue
        res = {"N_S": ns}
        s_rows = [r for r in rows if r["task"] == t and r["arm"] == "S" and r.get("correct") and r.get("ooc_screen")]
        res["S_clusters_observed"] = len({r["cluster_id"] for r in s_rows if r.get("cluster_id")})
        per_isl = defaultdict(lambda: [0, 0])
        for r in rows:
            if r["task"] == t and r["arm"] == "S":
                per_isl[r.get("island")][1] += 1
        seen_isl: dict[Any, set] = defaultdict(set)
        for r in s_rows:
            if r.get("distinct_id") and r["distinct_id"] not in seen_isl[r.get("island")]:
                seen_isl[r.get("island")].add(r["distinct_id"])
                per_isl[r.get("island")][0] += 1
        res["S_per_island"] = {str(k): {"X_a": v[0], "N": v[1]} for k, v in per_isl.items()}
        res["S_island_bootstrap"] = island_bootstrap([tuple(v) for v in per_isl.values()])
        for a in ("NE", "I0", "EAP", "BINT", "B0"):
            ar = [r for r in rows if r["task"] == t and r["arm"] == a]
            if not ar:
                continue
            cl = Counter(r["cluster_id"] for r in ar if r.get("correct") and r.get("ooc_screen") and r.get("cluster_id"))
            res[a] = rarefy_extrapolate(list(cl.values()), len(ar), ns)
        out[t] = res
    return out


def lineage(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    out = {}
    byid = {r["id"]: r for r in rows}
    for t in tasks:
        s = [r for r in rows if r["task"] == t and r["arm"] == "S" and r.get("correct") and r.get("ooc_screen")]
        lb = [r for r in s if r.get("final_class") in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM")]

        def nonseed_parents(r: dict[str, Any]) -> bool:
            ps = r.get("parent_ids") or []
            return bool(ps) and all(not str(p).startswith("seed:") for p in ps)
        out[t] = {"ooc_depth_hist": dict(Counter(r.get("depth") for r in s)),
                  "levelb_depth_hist": dict(Counter(r.get("depth") for r in lb)),
                  "levelb_n": len(lb),
                  "levelb_depth_ge2_nonseed_parents": sum(1 for r in lb if (r.get("depth") or 0) >= 2 and
                                                          nonseed_parents(r)),
                  "ooc_depth_ge2_nonseed_parents": sum(1 for r in s if (r.get("depth") or 0) >= 2 and
                                                       nonseed_parents(r)),
                  "levelb_ids": [r["id"] for r in lb][:200],
                  "parents_present": sum(1 for r in s for p in (r.get("parent_ids") or []) if p in byid)}
    return out


def placebo(rows: list[dict[str, Any]], tasks: list[str], reps: int = 200, seed: int = 11) -> dict[str, Any]:
    """Arm labels shuffled within task between S and K: R_hat should move to ~1 and significance should vanish."""
    out = {}
    rng = random.Random(seed)
    for t in tasks:
        tab = {a: arm_counts(rows, t, a) for a in ARMS}
        if tab["S"]["N"] == 0:
            continue
        k = pick_k(tab, "a")
        pool = [r for r in rows if r["task"] == t and r["arm"] in ("S", k)]
        flags = []
        for r in pool:
            flags.append(1 if (r.get("correct") and r.get("ooc_screen") and r.get("is_first_of_distinct")) else 0)
        ns = tab["S"]["N"]
        ps, rh = [], []
        for _ in range(reps):
            idx = list(range(len(pool)))
            rng.shuffle(idx)
            xs = sum(flags[i] for i in idx[:ns])
            xk = sum(flags[i] for i in idx[ns:])
            tt = rate_ratio_test(xs, ns, xk, len(pool) - ns)
            if tt["estimable"]:
                ps.append(tt["p_one_sided"])
                if tt["R_hat"] not in (None, math.inf):
                    rh.append(tt["R_hat"])
        out[t] = {"K_arm": k, "reps": reps, "frac_p_below_0.05": (sum(p < 0.05 for p in ps) / len(ps)) if ps else None,
                  "median_R_hat": float(np.median(rh)) if rh else None, "n_estimable": len(ps)}
    return out


def seeds_check(rows: list[dict[str, Any]], seed_shas: dict[str, set[str]]) -> dict[str, Any]:
    """Level-b counts must not change when S's seeds are scored as children (seeds are never rows)."""
    out = {}
    for t, shas in seed_shas.items():
        hits = [r["id"] for r in rows if r["task"] == t and r.get("code_sha256") in shas]
        out[t] = {"rows_identical_to_a_seed": len(hits), "examples": hits[:5]}
    return out


def dynamics(archives: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for t, a in archives.items():
        hist = a.get("history") or []
        out[t] = {"t": [h["t"] for h in hist], "coverage": [h["n_cells"] for h in hist],
                  "qd_score": [h["qd_score"] for h in hist], "best_nu": [h["best_nu"] for h in hist],
                  "resets": [x for h in hist for x in (h.get("resets") or [])],
                  "final_cells": [i["n_cells"] for i in a["final"]["islands"]],
                  "final_qd": [i["qd_score"] for i in a["final"]["islands"]]}
    return out


def discovery_curve(rows: list[dict[str, Any]], task: str, arm: str, key: str = "distinct_id") -> list[int]:
    rs = sorted([r for r in rows if r["task"] == task and r["arm"] == arm], key=lambda r: r["slot"])
    seen: set = set()
    curve = []
    for r in rs:
        if r.get("correct") and r.get("ooc_screen") and r.get(key):
            seen.add(r[key])
        curve.append(len(seen))
    return curve


def run_all(rows: list[dict[str, Any]], tasks: list[str], archives: dict[str, dict[str, Any]],
            seed_shas: dict[str, set[str]]) -> dict[str, Any]:
    tabs = {t: {a: arm_counts(rows, t, a) for a in ARMS} for t in tasks}
    tabs_b = {t: {a: arm_counts(rows, t, a, "b") for a in ARMS} for t in tasks}
    return {"arm_rates": tabs, "arm_rates_b": tabs_b, "ratio_tests": primary_tests(rows, tasks),
            "matched_effort": matched_effort(rows, tasks), "lineage": lineage(rows, tasks),
            "placebo": placebo(rows, tasks), "seeds_check": seeds_check(rows, seed_shas),
            "dynamics": dynamics(archives)}
