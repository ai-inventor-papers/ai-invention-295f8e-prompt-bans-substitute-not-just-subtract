#!/usr/bin/env python3
"""FROZEN ANALYSIS for Claim E (hash-committed in commit #0 before any generation; called unchanged afterwards).

Pure functions over labelled rows (dicts with task, stage, arm, template, slot, label, passed) and the commit-#1
predictor table. Label conventions:
  catalogue(u)   = frozen catalogue modes (+ named extended labels promoted by the structural audit, e.g. R6
                   'linear_scan'); 'other', 'invalid', 'disputed' are never catalogue labels.
  off_cat(rows)  = share of ALL attempts whose label is a catalogue survivor (in catalogue, != D_u)   [PRIMARY]
  off_any(rows)  = share of ALL attempts whose label is not D_u / invalid / disputed (exp23's definition)
  off_corr(rows) = share of ALL attempts that PASS the hidden tests with a catalogue-survivor label
  pass(rows)     = share of attempts passing every hidden test
Escape (per unit u, direction s, dose alpha): stage 1 (N=10) off_cat - off_cat(twin) >= 0.20 and pass >= 0.8 x twin
pass; confirmation (N=30 pooled) the same two criteria and binom.sf(k_off - 1, n, max(p0, 0.01)) < 0.05.
E_u(alpha) = confirmed / n_dirs; E_u = mean over alphas (E_u_max = max over alphas, exp23's definition).
"""

from __future__ import annotations

import collections
import itertools
import math
from typing import Any, Callable, Iterable

import numpy as np
from scipy import stats

NOT_CAT = ("other", "invalid", "disputed", None)
THRESH = {"EXCESS": 0.20, "PASS_FRAC": 0.80, "BINOM_ALPHA": 0.05, "P0_FLOOR": 0.01, "RHO_E": 0.5, "P_E": 0.01,
          "P_PARTIAL": 0.05, "IMMOVABLE_FRAC": 0.8, "BETA_MOVABLE": 0.05, "BETA_DIVERSE": 0.2, "RANGE_MIN": 4,
          "RHO_DISCONFIRM": 0.3, "A2_HIT": 0.7, "A2_P": 0.05, "A2_NATS": 0.10, "A2_MIN_EVENTS_WILCOXON": 5,
          "OTHER_FLOOR": 0.02, "N_PERM": 200_000, "N_BOOT": 10_000, "BOOT_CI": 0.90, "HILL_DEPTH": 25,
          "HILL_SUBSAMPLES": 1000, "T_SHARE_OF_BETA": 0.5, "CONTROL_TOL": 0.05}


# ================================================================================================ shares
def off_cat(rows: list[dict[str, Any]], D: str, cat: Iterable[str]) -> float:
    cat = set(cat)
    if not rows:
        return float("nan")
    return sum(1 for r in rows if r["label"] in cat and r["label"] != D) / len(rows)


def off_any(rows: list[dict[str, Any]], D: str) -> float:
    if not rows:
        return float("nan")
    return sum(1 for r in rows if r["label"] not in (D, "invalid", "disputed")) / len(rows)


def off_corr(rows: list[dict[str, Any]], D: str, cat: Iterable[str]) -> float:
    cat = set(cat)
    if not rows:
        return float("nan")
    return sum(1 for r in rows if r.get("passed") and r["label"] in cat and r["label"] != D) / len(rows)


def pass_rate(rows: list[dict[str, Any]]) -> float:
    return sum(1 for r in rows if r.get("passed")) / len(rows) if rows else float("nan")


def k_off(rows: list[dict[str, Any]], D: str, cat: Iterable[str], kind: str = "cat") -> int:
    cat = set(cat)
    if kind == "cat":
        return sum(1 for r in rows if r["label"] in cat and r["label"] != D)
    if kind == "any":
        return sum(1 for r in rows if r["label"] not in (D, "invalid", "disputed"))
    return sum(1 for r in rows if r.get("passed") and r["label"] in cat and r["label"] != D)


def share_fn(kind: str) -> Callable:
    if kind == "cat":
        return lambda rr, D, cat: off_cat(rr, D, cat)
    if kind == "any":
        return lambda rr, D, cat: off_any(rr, D)
    return lambda rr, D, cat: off_corr(rr, D, cat)


# ================================================================================================ escape screen
def escape_unit(twin: list[dict[str, Any]], cells_s1: dict[str, list[dict[str, Any]]],
                cells_conf: dict[str, list[dict[str, Any]]], D: str, cat: list[str], n_dirs: int,
                alphas: tuple[float, ...] = (1.0, 2.0), kind: str = "cat") -> dict[str, Any]:
    """cells_s1[key] = stage-1 rows (N=10) of direction-alpha key 's_a{alpha}'; cells_conf[key] = the confirmation
    rows (+20). Returns stage-1 / confirmation tables, E_u (mean over alphas), E_u_max and per-alpha E."""
    f = share_fn(kind)
    p0, pt = f(twin, D, cat), pass_rate(twin)
    s1, passing = {}, []
    for key, rr in sorted(cells_s1.items()):
        sh, pr = f(rr, D, cat), pass_rate(rr)
        ok = bool(rr) and (sh - p0 >= THRESH["EXCESS"]) and (pr >= THRESH["PASS_FRAC"] * pt)
        s1[key] = {"n": len(rr), "off_share": sh, "excess": sh - p0, "pass": pr, "stage1_pass": ok}
        if ok:
            passing.append(key)
    conf, confirmed = {}, []
    for key in passing:
        rr = cells_s1[key] + cells_conf.get(key, [])
        n = len(rr)
        k = k_off(rr, D, cat, kind)
        sh, pr = (k / n if n else float("nan")), pass_rate(rr)
        pb = float(stats.binom.sf(k - 1, n, max(p0, THRESH["P0_FLOOR"]))) if n else 1.0
        ok = n >= 30 and (sh - p0 >= THRESH["EXCESS"]) and (pr >= THRESH["PASS_FRAC"] * pt) and pb < THRESH["BINOM_ALPHA"]
        conf[key] = {"n": n, "k_off": k, "off_share": sh, "excess": sh - p0, "pass": pr, "binom_p": pb, "confirmed": ok}
        if ok:
            confirmed.append(key)
    E_alpha = {}
    for a in alphas:
        tag = f"_a{int(a)}"
        E_alpha[f"a{int(a)}"] = sum(1 for k in confirmed if k.endswith(tag)) / n_dirs
    E = float(np.mean(list(E_alpha.values()))) if E_alpha else 0.0
    return {"p0": p0, "twin_pass": pt, "n_twin": len(twin), "stage1": s1, "passing": passing, "confirm": conf,
            "confirmed": confirmed, "E_alpha": E_alpha, "E_u": E, "E_u_max": max(E_alpha.values()) if E_alpha else 0.0,
            "movable": E > 0, "n_dirs": n_dirs, "share_kind": kind}


def landing(rows_confirmed: list[dict[str, Any]], D: str, cat: list[str]) -> dict[str, Any]:
    """Modal catalogue label among CORRECT off-default programs pooled over confirmed cells (ties: frozen order)."""
    c = collections.Counter(r["label"] for r in rows_confirmed if r.get("passed") and r["label"] in cat
                            and r["label"] != D)
    if not c:
        return {"defined": False, "landing": None, "composition": {}}
    top = max(c.values())
    lab = next(m for m in cat if c.get(m, 0) == top)
    return {"defined": True, "landing": lab, "composition": dict(c), "n": sum(c.values())}


# ================================================================================================ diversity
def hill1_rarefied(labels: list[str], depth: int = 25, n_sub: int = 1000, seed: int = 0) -> float | None:
    """Hill number of order 1 (exp of Shannon entropy) rarefied to `depth` by subsampling without replacement."""
    if len(labels) < 2:
        return None
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    d = min(depth, len(arr))
    vals = []
    for _ in range(n_sub):
        sub = rng.choice(arr, size=d, replace=False)
        _, cnt = np.unique(sub, return_counts=True)
        p = cnt / cnt.sum()
        vals.append(math.exp(-float((p * np.log(p)).sum())))
    return float(np.mean(vals))


def js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    keys = sorted(set(p) | set(q))
    P = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    Q = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    if P.sum() == 0 or Q.sum() == 0:
        return float("nan")
    P, Q = P / P.sum(), Q / Q.sum()
    M = 0.5 * (P + Q)

    def kl(a, b):
        m = a > 0
        return float((a[m] * np.log2(a[m] / b[m])).sum())
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def composition(rows: list[dict[str, Any]], correct_only: bool = True) -> dict[str, int]:
    return dict(collections.Counter(r["label"] for r in rows if (r.get("passed") or not correct_only)
                                    and r["label"] not in ("invalid", "disputed")))


# ================================================================================================ correlation stats
def rankdata(x: list[float]) -> np.ndarray:
    return stats.rankdata(np.asarray(x, dtype=float), method="average")


def spearman(x: list[float], y: list[float]) -> float | None:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return None
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p_one_sided(x: list[float], y: list[float], n_perm: int = THRESH["N_PERM"], seed: int = 0) -> float | None:
    """P(rho_perm >= rho_obs) with the +1 correction, permuting y over units (Monte-Carlo, n_perm draws)."""
    rho = spearman(x, y)
    if rho is None:
        return None
    rx = rankdata(x)
    ry = rankdata(y)
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    rng = np.random.default_rng(seed)
    n = len(rx)
    hits = 0
    done = 0
    chunk = 20_000
    while done < n_perm:
        m = min(chunk, n_perm - done)
        idx = np.argsort(rng.random((m, n)), axis=1)
        r = (rx[None, :] * ry[idx]).mean(axis=1)
        hits += int((r >= rho - 1e-12).sum())
        done += m
    return (hits + 1) / (n_perm + 1)


def kendall_tau_b(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    t = stats.kendalltau(x, y, variant="b")
    return None if t.statistic is None or not np.isfinite(t.statistic) else float(t.statistic)


def partial_spearman(x: list[float], y: list[float], Z: list[list[float]]) -> float | None:
    """Spearman partial correlation of x and y given covariates Z (rank-transform, regress out, correlate)."""
    if len(x) < len(Z) + 3:
        return None
    rx, ry = rankdata(x), rankdata(y)
    Zr = np.column_stack([np.ones(len(x))] + [rankdata(z) for z in Z])
    ex = rx - Zr @ np.linalg.lstsq(Zr, rx, rcond=None)[0]
    ey = ry - Zr @ np.linalg.lstsq(Zr, ry, rcond=None)[0]
    if ex.std() == 0 or ey.std() == 0:
        return None
    return float(np.corrcoef(ex, ey)[0, 1])


def boot_rho_diff(x: list[float], r: list[float], y: list[float], n_boot: int = THRESH["N_BOOT"],
                  ci: float = THRESH["BOOT_CI"], seed: int = 0) -> dict[str, Any]:
    """Paired task bootstrap of rho(x, y) - rho(r, y): resample units with replacement; degenerate draws skipped."""
    rng = np.random.default_rng(seed)
    x, r, y = np.asarray(x, float), np.asarray(r, float), np.asarray(y, float)
    n = len(x)
    d = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        a, b = spearman(x[i], y[i]), spearman(r[i], y[i])
        if a is None or b is None:
            continue
        d.append(a - b)
    if not d:
        return {"diff": None, "lo": None, "hi": None, "n_valid": 0, "ahead": False}
    lo, hi = np.quantile(d, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    obs_a, obs_b = spearman(x, y), spearman(r, y)
    diff = None if (obs_a is None or obs_b is None) else obs_a - obs_b
    return {"diff": diff, "lo": float(lo), "hi": float(hi), "n_valid": len(d), "ahead": bool(lo > 0)}


# ================================================================================================ E-A1
def e_a1(units: list[str], beta: dict[str, float], E: dict[str, float], cls: dict[str, str],
         rivals: dict[str, dict[str, float | None]], rival_sign: dict[str, int], n_perm: int = THRESH["N_PERM"],
         n_boot: int = THRESH["N_BOOT"], seed: int = 0) -> dict[str, Any]:
    """units: defaulted units; beta, E per unit; cls per unit in {COLLAPSED, INTERMEDIATE, DIVERSE}; rivals[name][u]
    raw rival values; rival_sign[name] = +1 if higher predicts MORE movability, -1 if higher predicts less."""
    u = [x for x in units if beta.get(x) is not None and E.get(x) is not None]
    b = [beta[x] for x in u]
    e = [E[x] for x in u]
    rho = spearman(b, e)
    p = perm_p_one_sided(b, e, n_perm=n_perm, seed=seed) if rho is not None else None
    tau = kendall_tau_b(b, e)
    collapsed = [x for x in u if cls[x] == "COLLAPSED"]
    diverse = [x for x in u if cls[x] == "DIVERSE"]
    immov = (sum(1 for x in collapsed if E[x] == 0) / len(collapsed)) if collapsed else None
    div_zero = (sum(1 for x in diverse if E[x] == 0) / len(diverse)) if diverse else None
    n_range = sum(1 for x in u if beta[x] >= THRESH["BETA_MOVABLE"])
    riv = {}
    for name, vals in rivals.items():
        uu = [x for x in u if vals.get(x) is not None and np.isfinite(vals[x])]
        if len(uu) < 4:
            riv[name] = {"n": len(uu), "rho": None, "boot": None, "ahead": False, "note": "too few units"}
            continue
        s = rival_sign.get(name, 1)
        rv = [s * float(vals[x]) for x in uu]
        bt = boot_rho_diff([beta[x] for x in uu], rv, [E[x] for x in uu], n_boot=n_boot, seed=seed)
        riv[name] = {"n": len(uu), "rho": spearman(rv, [E[x] for x in uu]), "boot": bt, "ahead": bt["ahead"],
                     "sign": s}
    ahead_all = all(v["ahead"] for v in riv.values()) if riv else False
    if n_range < THRESH["RANGE_MIN"]:
        verdict = "INCONCLUSIVE"
        why = f"range restriction: {n_range} units with beta >= {THRESH['BETA_MOVABLE']} (< {THRESH['RANGE_MIN']})"
    elif rho is not None and rho >= THRESH["RHO_E"] and p is not None and p < THRESH["P_E"] and immov is not None \
            and immov >= THRESH["IMMOVABLE_FRAC"] and ahead_all:
        verdict, why = "CONFIRMED", "all criteria met"
    elif (rho is not None and rho < THRESH["RHO_DISCONFIRM"]) or (div_zero is not None and div_zero > 0.5):
        verdict = "DISCONFIRMED"
        why = "rho < 0.3" if (rho is not None and rho < THRESH["RHO_DISCONFIRM"]) else "most DIVERSE units immovable"
    elif rho is not None and rho >= THRESH["RHO_E"] and p is not None and p < THRESH["P_PARTIAL"]:
        verdict = "PARTIAL"
        fails = []
        if not (p < THRESH["P_E"]):
            fails.append("p >= 0.01")
        if immov is None or immov < THRESH["IMMOVABLE_FRAC"]:
            fails.append("immovable fraction < 0.8 (or no collapsed units)")
        if not ahead_all:
            fails.append("not ahead of every rival")
        why = "; ".join(fails)
    else:
        verdict, why = "INCONCLUSIVE", "criteria neither met nor disconfirmed"
    return {"units": u, "n": len(u), "beta": {x: beta[x] for x in u}, "E": {x: E[x] for x in u}, "rho": rho,
            "p_one_sided_perm": p, "n_perm": n_perm, "kendall_tau_b": tau, "immovable_frac_collapsed": immov,
            "n_collapsed": len(collapsed), "n_diverse": len(diverse), "diverse_zero_frac": div_zero,
            "n_beta_ge_movable": n_range, "rivals": riv, "ahead_of_every_rival": ahead_all, "verdict": verdict,
            "why": why}


# ================================================================================================ E-A2
def poisson_binomial_sf(k: int, ps: list[float]) -> float:
    """P(X >= k) for X = sum of independent Bernoulli(p_i) (exact DP)."""
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(dist[k:].sum())


def log_score(q: dict[str, float], ys: list[str], cat_surv: list[str]) -> float | None:
    """Mean log q(y) over outcomes y; q is renormalised over the survivors + an 'other' bin with floor 0.02."""
    if not ys:
        return None
    qq = {m: max(float(q.get(m, 0.0)), 0.0) for m in cat_surv}
    tot = sum(qq.values())
    if tot <= 0:
        qq = {m: 1.0 / len(cat_surv) for m in cat_surv}
        tot = 1.0
    qq = {m: (1 - THRESH["OTHER_FLOOR"]) * v / tot for m, v in qq.items()}
    qq["other"] = THRESH["OTHER_FLOOR"]
    return float(np.mean([math.log(max(qq.get(y, 1e-12), 1e-12)) for y in ys]))


def e_a2(events: list[dict[str, Any]]) -> dict[str, Any]:
    """events: [{unit, r_u, landing, K_u, outcomes: [labels of correct off-default catalogue programs of confirmed
    escapes], survivors, q_base, q_assoc, q_prox}]. Hit = r_u == landing; chance = 1/(K_u - 1)."""
    ev = [e for e in events if e.get("landing") is not None and e.get("r_u") is not None]
    n = len(ev)
    hits = sum(1 for e in ev if e["r_u"] == e["landing"])
    chance = [1.0 / max(e["K_u"] - 1, 1) for e in ev]
    p = poisson_binomial_sf(hits, chance) if n else None
    rate = hits / n if n else None
    mean_chance = float(np.mean(chance)) if chance else None
    passed = bool(n and rate >= THRESH["A2_HIT"] and p is not None and p < THRESH["A2_P"])
    disconf = bool(n and rate <= mean_chance)
    ls = []
    for e in ev:
        ys = e.get("outcomes", [])
        if not ys:
            continue
        rec = {"unit": e["unit"], "n_outcomes": len(ys)}
        for k in ("q_base", "q_assoc", "q_prox"):
            q = e.get(k)
            if not q:
                q = {m: 1.0 / len(e["survivors"]) for m in e["survivors"]}
                rec[f"{k}_defined"] = False
            else:
                rec[f"{k}_defined"] = True
            rec[k] = log_score(q, ys, e["survivors"])
        ls.append(rec)
    out = {"n_events": n, "hits": hits, "hit_rate": rate, "chance": chance, "mean_chance": mean_chance,
           "poisson_binomial_p": p, "pass_hit": passed, "disconfirm_hit": disconf, "log_scores": ls}
    if ls:
        d_assoc = [r["q_base"] - r["q_assoc"] for r in ls]
        d_prox = [r["q_base"] - r["q_prox"] for r in ls]
        out["mean_base_minus_assoc"] = float(np.mean(d_assoc))
        out["mean_base_minus_prox"] = float(np.mean(d_prox))
        if len(ls) >= THRESH["A2_MIN_EVENTS_WILCOXON"]:
            try:
                w = stats.wilcoxon(d_assoc, alternative="greater", zero_method="wilcox")
                out["wilcoxon_p_base_vs_assoc"] = float(w.pvalue)
            except ValueError:
                out["wilcoxon_p_base_vs_assoc"] = None
            out["log_score_test"] = "decisive"
            out["pass_logscore"] = bool(out["mean_base_minus_assoc"] >= THRESH["A2_NATS"]
                                        and (out.get("wilcoxon_p_base_vs_assoc") or 1.0) < 0.05)
        else:
            out["log_score_test"] = (f"descriptive: {len(ls)} matched events < {THRESH['A2_MIN_EVENTS_WILCOXON']} "
                                     "(minimum attainable one-sided Wilcoxon p at n=4 is 0.0625)")
            out["pass_logscore"] = None
        defined = [r for r in ls if r["q_assoc_defined"]]
        if defined:
            out["mean_base_minus_assoc_defined_only"] = float(np.mean([r["q_base"] - r["q_assoc"] for r in defined]))
    if n < 3:
        out["verdict"] = "DESCRIPTIVE (fewer than 3 events)"
    elif passed and out.get("pass_logscore") is not False:
        out["verdict"] = "PASS"
    elif disconf:
        out["verdict"] = "DISCONFIRMED (hit rate at or below chance)"
    else:
        out["verdict"] = "NOT PASSED"
    return out


# ================================================================================================ transplant
def mcnemar_one_sided(a_succ: dict[Any, bool], b_succ: dict[Any, bool]) -> dict[str, Any]:
    """Exact one-sided McNemar on CRN-paired slots: H1 'a succeeds more than b'. b10 = a only, b01 = b only."""
    keys = sorted(set(a_succ) & set(b_succ))
    b10 = sum(1 for k in keys if a_succ[k] and not b_succ[k])
    b01 = sum(1 for k in keys if b_succ[k] and not a_succ[k])
    n = b10 + b01
    p = float(stats.binom.sf(b10 - 1, n, 0.5)) if n else 1.0
    return {"n_pairs": len(keys), "a_only": b10, "b_only": b01, "p_one_sided": p}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def transplant_unit(arms: dict[str, list[dict[str, Any]]], twin: list[dict[str, Any]], D: str, cat: list[str],
                    beta: float, r_u: str | None, pt_comp: dict[str, int]) -> dict[str, Any]:
    """arms: {'T', 'RND', 'XT', 'RP'} -> rows on the twin's CRN slots (template, slot)."""
    def succ(rr):
        return {(r["template"], r["slot"]): bool(r.get("passed") and r["label"] in cat and r["label"] != D) for r in rr}

    out: dict[str, Any] = {"twin": {"n": len(twin), "s": off_corr(twin, D, cat), "pass": pass_rate(twin)}}
    for k, rr in arms.items():
        kk = k_off(rr, D, cat, "corr")
        from_ci = _wilson(kk, len(rr))
        out[k] = {"n": len(rr), "s": off_corr(rr, D, cat), "s_ci95": from_ci, "pass": pass_rate(rr),
                  "pass_ratio": (pass_rate(rr) / out["twin"]["pass"]) if out["twin"]["pass"] else None,
                  "composition_correct": composition(rr), "composition_all": composition(rr, correct_only=False)}
    kt = k_off(twin, D, cat, "corr")
    out["twin"]["s_ci95"] = _wilson(kt, len(twin))
    out["twin"]["composition_correct"] = composition(twin)
    if "T" in arms:
        sT = succ(arms["T"])
        for ctl in ("RND", "XT", "RP"):
            if ctl in arms:
                out[f"mcnemar_T_vs_{ctl}"] = mcnemar_one_sided(sT, succ(arms[ctl]))
        out["mcnemar_T_vs_twin"] = mcnemar_one_sided(sT, succ(twin))
        lt = landing(arms["T"], D, cat)
        out["T_landing"] = lt
        out["T_lands_on_r_u"] = bool(lt["defined"] and r_u is not None and lt["landing"] == r_u)
        ptd = {k: v for k, v in pt_comp.items() if k not in ("invalid", "disputed")}
        out["JS_T_pt"] = js_divergence({k: float(v) for k, v in composition(arms["T"]).items()}, ptd)
        out["JS_twin_pt"] = js_divergence({k: float(v) for k, v in composition(twin).items()}, ptd)
        out["T_closer_to_pt"] = (out["JS_T_pt"] < out["JS_twin_pt"]) if (np.isfinite(out["JS_T_pt"])
                                                                         and np.isfinite(out["JS_twin_pt"])) else None
        out["T_valid"] = bool(out["T"]["pass_ratio"] is not None and out["T"]["pass_ratio"] >= THRESH["PASS_FRAC"])
        out["s_T_ge_half_beta"] = bool(out["T"]["s"] >= THRESH["T_SHARE_OF_BETA"] * beta)
        if "RND" in arms:
            out["norm_confounded"] = bool(out["RND"]["pass_ratio"] is not None
                                          and out["RND"]["pass_ratio"] < THRESH["PASS_FRAC"] and out["T_valid"])
    return out


def _wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def transplant_summary(per_unit: dict[str, dict[str, Any]], controls: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """B-style summary: Holm across S_T tasks per comparison; a task 'supports' iff T valid, s_T >= 0.5 beta, beats RND
    (unless norm-confounded) and XT (Holm-adjusted one-sided p < 0.05) and T lands on r_u."""
    out: dict[str, Any] = {}
    for comp in ("RND", "XT", "RP", "twin"):
        ps = {u: v[f"mcnemar_T_vs_{comp}"]["p_one_sided"] for u, v in per_unit.items() if f"mcnemar_T_vs_{comp}" in v}
        out[f"holm_T_vs_{comp}"] = holm(ps) if ps else {}
    support = {}
    for u, v in per_unit.items():
        if "T" not in v:
            continue
        beats_rnd = out["holm_T_vs_RND"].get(u, 1.0) < 0.05
        beats_xt = out["holm_T_vs_XT"].get(u, 1.0) < 0.05
        rnd_ok = beats_rnd or v.get("norm_confounded", False)
        support[u] = {"valid": v["T_valid"], "s_T_ge_half_beta": v["s_T_ge_half_beta"], "beats_RND": beats_rnd,
                      "norm_confounded": v.get("norm_confounded", False), "beats_XT": beats_xt,
                      "lands_on_r_u": v["T_lands_on_r_u"],
                      "supports": bool(v["T_valid"] and v["s_T_ge_half_beta"] and rnd_ok and beats_xt
                                       and v["T_lands_on_r_u"])}
    valid = [u for u, s in support.items() if s["valid"]]
    out["per_unit_support"] = support
    out["n_valid"] = len(valid)
    out["share_supporting_of_valid"] = (sum(1 for u in valid if support[u]["supports"]) / len(valid)) if valid else None
    ctl = {u: {"s_T": v["T"]["s"], "s_twin": v["twin"]["s"],
               "within_tol": abs(v["T"]["s"] - v["twin"]["s"]) <= THRESH["CONTROL_TOL"]} for u, v in controls.items()
           if "T" in v}
    out["collapsed_controls"] = ctl
    out["collapsed_controls_all_within_tol"] = all(c["within_tol"] for c in ctl.values()) if ctl else None
    rp = {u: {"s_RP": v["RP"]["s"], "s_twin": v["twin"]["s"],
              "within_tol": abs(v["RP"]["s"] - v["twin"]["s"]) <= THRESH["CONTROL_TOL"]} for u, v in per_unit.items()
          if "RP" in v}
    out["read_position_site_control"] = rp
    out["rp_all_within_tol"] = all(c["within_tol"] for c in rp.values()) if rp else None
    return out


# ================================================================================================ self test (CPU T6)
def self_test() -> dict[str, Any]:
    """Synthetic table with hand-computable answers."""
    res: dict[str, Any] = {}
    x = [0.0, 0.1, 0.2, 0.3, 0.4]
    y = [0.0, 0.1, 0.3, 0.2, 0.5]
    res["spearman"] = spearman(x, y)                       # ranks 1..5 vs 1,2,4,3,5 -> 1 - 6*2/(5*24) = 0.9
    res["spearman_ok"] = abs(res["spearman"] - 0.9) < 1e-12
    # exact permutation p for n=5: count permutations with rho >= 0.9 -> (1 identity + 4 adjacent swaps) / 120
    exact = sum(1 for perm in itertools.permutations(range(5))
                if spearman(x, [y[i] for i in perm]) >= 0.9 - 1e-12) / 120
    mc = perm_p_one_sided(x, y, n_perm=200_000, seed=1)
    res["perm_p_exact"] = exact
    res["perm_p_mc"] = mc
    res["perm_ok"] = abs(mc - exact) < 0.005
    res["poisson_binomial"] = poisson_binomial_sf(2, [0.5, 0.5, 0.5])   # P(X >= 2) = 0.5
    res["pb_ok"] = abs(res["poisson_binomial"] - 0.5) < 1e-12
    mc2 = mcnemar_one_sided({i: i < 6 for i in range(10)}, {i: i >= 4 for i in range(10)})
    res["mcnemar"] = mc2                                    # a only: 0-3 (4), b only: 6-9 (4) -> p = P(X>=4|8) = 0.636
    res["mcnemar_ok"] = mc2["a_only"] == 4 and mc2["b_only"] == 4 and abs(mc2["p_one_sided"] - 0.63671875) < 1e-9
    res["holm"] = holm({"a": 0.01, "b": 0.04, "c": 0.03})   # 0.03, 0.06, 0.06
    res["holm_ok"] = abs(res["holm"]["a"] - 0.03) < 1e-12 and abs(res["holm"]["c"] - 0.06) < 1e-12 \
        and abs(res["holm"]["b"] - 0.06) < 1e-12
    res["hill1_uniform2"] = hill1_rarefied(["a"] * 50 + ["b"] * 50, depth=100, n_sub=5)
    res["hill_ok"] = abs(res["hill1_uniform2"] - 2.0) < 1e-9
    res["all_ok"] = all(v for k, v in res.items() if k.endswith("_ok"))
    return res
