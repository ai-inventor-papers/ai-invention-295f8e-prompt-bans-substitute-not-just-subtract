#!/usr/bin/env python3
"""FROZEN ANALYSIS for Claim L in Gemma (iteration 6, step 5; hash-committed in commit #0 before any new sample).

Pure functions over labelled rows (dicts with task, stage, arm, template, slot, label, passed, temperature) and the
commit-#1 forecast table. Conventions:
  catalogue(u)    frozen catalogue modes + named extended labels (R6 'linear_scan'); 'other', 'invalid', 'disputed'
                  are never catalogue labels.
  correct         passed all hidden tests and label not in {invalid, disputed}.
  D_u             modal CORRECT twin label over all N 300 twin rows (T 1.0 N 200 + T 1.3 N 100); share >= 0.6 of the
                  correct programs, >= 10 correct, unique mode, in the catalogue; else NO DEFAULT (unit leaves L).
  nondef(u)       catalogue(u) minus D_u (K_u - 1 algorithms); chance of a blind top-1 = 1 / (K_u - 1).
FORECASTS (all over nondef(u) + one 'other' bin; the same add-one smoothing for every count-based forecast):
  q_base  pt repertoire: add-one over nondef + 'other' of CORRECT pt programs if the task has >= 20 correct pt
          programs, else of VALID catalogue-labelled attempts (LOW_CORRECT). r_u = argmax of the primary counts over
          nondef; ties -> correct count, valid count, few-shot count, alphabetical (TIE flag); undefined at 0.
  q_tail  it twin's own tail: add-one over nondef + 'other' of the CORRECT off-default programs among all 300 twin
          rows; t_u = argmax over nondef (same tie rule on correct, valid, T1.0 count, alphabetical); TAIL-EMPTY iff
          no correct nondef catalogue program in the 300 rows (t_u undefined).
  q_lik   teacher-forced likelihood: s_u(a) = mean over programs and templates of the per-token mean log-prob of the
          first 48 code tokens (norm; raw = sum beside); top-1 = argmax over nondef; distribution = softmax(norm)
          over nondef x 0.98 + 'other' 0.02.
  undefined forecast -> uniform over nondef + 'other' (defined-only result beside).
EVENTS (v6): ONE event per (unit, nudge type in {FD, PN}); cells (direction x alpha, or PN alpha x provenance) qualify
  if pass >= 0.8 x twin T 1.0 pass; EVENT iff the pooled qualifying cells hold >= 5 correct off-default CATALOGUE
  programs; landing = modal catalogue label among them if it leads the next by >= 15 percentage points of those
  programs, else 'no clear landing' (no hit/miss; still in the log-score contest). Outcomes for log scores = every
  correct off-default program (catalogue nondef + 'other'). 'other' is never a landing.
TESTS: L1a (TAIL-EMPTY events) hits of r_u vs chance, exact Poisson-binomial, inferential iff >= 6 events (pass iff
  rate >= 2/3 and p < 0.05); L1b (DISCORDANT: r_u != q_lik top-1) exact one-sided sign test on events where exactly one
  hits, inferential iff >= 6 discordant events; tail rival (r_u != t_u) the same, descriptive; log scores: paired
  differences per event, exact one-sided Wilcoxon, BCa bootstrap over events (10k) and unit-cluster bootstrap;
  non-inferiority to q_tail iff the one-sided 95% BCa lower bound of mean(base - tail) > -0.10 nats; unit-clustered
  version: one pooled landing per unit, Poisson-binomial; per-unit log-score differences, exact sign-flip test.
"""

from __future__ import annotations

import collections
import itertools
import math
from typing import Any, Iterable

import numpy as np
from scipy import stats

NOT_CAT = ("other", "invalid", "disputed", None)
TH = {"DEFAULT_SHARE": 0.6, "DEFAULT_MIN_CORRECT": 10, "MIN_CORRECT_BASE": 20, "PASS_FRAC": 0.8,
      "EVENT_MIN": 5, "LANDING_MARGIN": 0.15, "L1_MIN_EVENTS": 6, "L1_RATE": 2.0 / 3.0, "ALPHA": 0.05,
      "NONINF_NATS": -0.10, "QLIK_OTHER": 0.02, "N_BOOT": 10_000, "THIN_RU": 5, "THIN_QLIK": 3}


# ================================================================================================ basics
def is_correct(r: dict[str, Any]) -> bool:
    return bool(r.get("passed")) and r.get("label") not in ("invalid", "disputed")


def is_valid_attempt(r: dict[str, Any]) -> bool:
    return bool(r.get("valid")) and r.get("label") not in ("invalid", "disputed")


def pass_rate(rows: list[dict[str, Any]]) -> float:
    return sum(1 for r in rows if r.get("passed")) / len(rows) if rows else float("nan")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def rule_of_three(n: int) -> float | None:
    return 3.0 / n if n > 0 else None


# ================================================================================================ default
def default_rule(twin: list[dict[str, Any]], cat: list[str]) -> dict[str, Any]:
    corr = [r for r in twin if is_correct(r)]
    cnt = collections.Counter(r["label"] for r in corr)
    n_c = len(corr)
    out = {"n_twin": len(twin), "n_correct": n_c, "pass_rate": pass_rate(twin), "correct_counts": dict(cnt)}
    if not cnt:
        return {**out, "D": None, "share": None, "defaulted": False, "reason": "no correct twin program"}
    top = max(cnt.values())
    tops = sorted(m for m, c in cnt.items() if c == top)
    lab, share = tops[0], top / n_c
    ok = lab in cat and share >= TH["DEFAULT_SHARE"] and n_c >= TH["DEFAULT_MIN_CORRECT"] and len(tops) == 1
    reason = "ok" if ok else ("modal correct label not in catalogue" if lab not in cat else
                              f"share {share:.2f} < 0.6" if share < TH["DEFAULT_SHARE"] else
                              f"{n_c} correct < 10" if n_c < TH["DEFAULT_MIN_CORRECT"] else "tie")
    return {**out, "D": lab if ok else None, "modal_correct": lab, "share": share, "defaulted": ok, "reason": reason}


def nondef_of(cat: list[str], D: str | None) -> list[str]:
    return [m for m in cat if m != D]


# ================================================================================================ forecasts
def addone(counts: dict[str, int], nondef: list[str], other: int) -> dict[str, float]:
    tot = sum(counts.get(m, 0) for m in nondef) + other + len(nondef) + 1
    q = {m: (counts.get(m, 0) + 1) / tot for m in nondef}
    q["other"] = (other + 1) / tot
    return q


def uniform(nondef: list[str]) -> dict[str, float]:
    k = len(nondef) + 1
    q = {m: 1.0 / k for m in nondef}
    q["other"] = 1.0 / k
    return q


def ranked(nondef: list[str], keys: list[dict[str, int]]) -> list[str]:
    return sorted(nondef, key=lambda m: tuple(-k.get(m, 0) for k in keys) + (m,))


def base_forecast(pt_rows: list[dict[str, Any]], D: str | None, cat: list[str],
                  fewshot_flag: str = "ptfs6") -> dict[str, Any]:
    """pt_rows: labelled pt rows (exp28 pt-chat, exp28 pt-plain, few-shot), each with 'stage'."""
    nondef = nondef_of(cat, D)
    corr = [r for r in pt_rows if is_correct(r)]
    valid = [r for r in pt_rows if is_valid_attempt(r)]
    cc = collections.Counter(r["label"] for r in corr)
    vc = collections.Counter(r["label"] for r in valid)
    fc = collections.Counter(r["label"] for r in pt_rows if r.get("stage") == fewshot_flag and is_valid_attempt(r))
    low = len(corr) < TH["MIN_CORRECT_BASE"]
    prim = vc if low else cc
    q = addone({m: prim.get(m, 0) for m in nondef}, nondef, prim.get("other", 0))
    rk = ranked(nondef, [prim, cc, vc, fc])
    r_u = rk[0] if rk and prim.get(rk[0], 0) > 0 else None
    tie = bool(r_u is not None and len(rk) > 1 and prim.get(rk[1], 0) == prim.get(rk[0], 0))
    return {"q": q, "r_u": r_u, "ranking": rk, "TIE": tie, "LOW_CORRECT": low, "n_rows": len(pt_rows),
            "n_correct": len(corr), "n_valid": len(valid), "correct_counts": dict(cc), "valid_counts": dict(vc),
            "fewshot_valid_counts": dict(fc), "primary": "valid attempts (LOW_CORRECT)" if low else "correct",
            "r_u_correct_support": cc.get(r_u, 0) if r_u else 0, "r_u_valid_support": vc.get(r_u, 0) if r_u else 0,
            "THIN_RU": bool(r_u is not None and cc.get(r_u, 0) < TH["THIN_RU"]),
            "beta": (sum(prim.get(m, 0) for m in nondef) / sum(prim.values())) if sum(prim.values()) else None}


def tail_forecast(twin: list[dict[str, Any]], D: str | None, cat: list[str]) -> dict[str, Any]:
    nondef = nondef_of(cat, D)
    corr_off = [r for r in twin if is_correct(r) and r["label"] != D]
    cc = collections.Counter(r["label"] for r in corr_off)
    vc = collections.Counter(r["label"] for r in twin if is_valid_attempt(r) and r["label"] != D)
    t10 = collections.Counter(r["label"] for r in corr_off if abs(float(r.get("temperature", 1.0)) - 1.0) < 1e-9)
    q = addone({m: cc.get(m, 0) for m in nondef}, nondef, cc.get("other", 0))
    rk = ranked(nondef, [cc, vc, t10])
    t_u = rk[0] if rk and cc.get(rk[0], 0) > 0 else None
    by_temp = collections.defaultdict(collections.Counter)
    for r in corr_off:
        by_temp[str(r.get("temperature"))][r["label"]] += 1
    return {"q": q, "t_u": t_u, "ranking": rk, "TAIL_EMPTY": t_u is None,
            "TIE": bool(t_u is not None and len(rk) > 1 and cc.get(rk[1], 0) == cc.get(rk[0], 0)),
            "correct_offdefault_counts": dict(cc), "valid_offdefault_counts": dict(vc),
            "by_temperature": {k: dict(v) for k, v in by_temp.items()}, "n_twin": len(twin)}


def softmax(x: dict[str, float]) -> dict[str, float]:
    if not x:
        return {}
    m = max(x.values())
    e = {k: math.exp(v - m) for k, v in x.items()}
    s = sum(e.values())
    return {k: v / s for k, v in e.items()}


def lik_forecast(scores: dict[str, dict[str, float]], nondef: list[str], key: str = "norm") -> dict[str, Any]:
    """scores[a] = {'norm': mean per-token log-prob, 'raw': mean summed log-prob, 'n_programs': int, ...}."""
    defined = [a for a in nondef if a in scores and scores[a].get(key) is not None
               and scores[a].get("n_programs", 0) > 0]
    if len(defined) < 2:
        return {"q": uniform(nondef), "top1": None, "defined": False, "n_scorable": len(defined)}
    s = {a: float(scores[a][key]) for a in defined}
    sm = softmax(s)
    q = {a: (1 - TH["QLIK_OTHER"]) * sm.get(a, 0.0) for a in nondef}
    # an algorithm with no forced program cannot be top-1 and gets the minimum defined score's softmax mass
    missing = [a for a in nondef if a not in defined]
    if missing:
        floor = min(sm.values())
        for a in missing:
            q[a] = (1 - TH["QLIK_OTHER"]) * floor
        z = sum(q.values()) / (1 - TH["QLIK_OTHER"])
        q = {a: v / z for a, v in q.items()}
    q["other"] = TH["QLIK_OTHER"]
    top = sorted(defined, key=lambda a: (-s[a], a))[0]
    return {"q": q, "top1": top, "defined": True, "n_scorable": len(defined), "partial": bool(missing)}


def assoc_forecast(q_assoc: dict[str, float] | None, nondef: list[str]) -> dict[str, Any]:
    """exp28's association forecast (descriptive third rival): catalogue part renormalised x 0.98, 'other' 0.02."""
    if not q_assoc:
        return {"q": uniform(nondef), "defined": False}
    qq = {m: max(float(q_assoc.get(m, 0.0)), 0.0) for m in nondef}
    tot = sum(qq.values())
    if tot <= 0:
        return {"q": uniform(nondef), "defined": False}
    q = {m: (1 - TH["QLIK_OTHER"]) * v / tot for m, v in qq.items()}
    q["other"] = TH["QLIK_OTHER"]
    return {"q": q, "defined": True}


def uniform_other(q: dict[str, float], nondef: list[str]) -> dict[str, float]:
    """Sensitivity: every forecast's catalogue part renormalised to 0.98, 'other' fixed at 0.02."""
    tot = sum(q.get(m, 0.0) for m in nondef)
    out = {m: (1 - TH["QLIK_OTHER"]) * (q.get(m, 0.0) / tot if tot > 0 else 1.0 / len(nondef)) for m in nondef}
    out["other"] = TH["QLIK_OTHER"]
    return out


def catalogue_only(q: dict[str, float], nondef: list[str]) -> dict[str, float]:
    tot = sum(q.get(m, 0.0) for m in nondef)
    return {m: (q.get(m, 0.0) / tot if tot > 0 else 1.0 / len(nondef)) for m in nondef}


def log_score(q: dict[str, float], ys: list[str]) -> float | None:
    """Mean log q(y) (nats) over outcome labels y; labels outside q's support are scored with q['other']."""
    if not ys:
        return None
    return float(np.mean([math.log(max(q.get(y, q.get("other", 1e-12)), 1e-12)) for y in ys]))


# ================================================================================================ events
def landing_rule(comp: dict[str, int], cat_order: list[str]) -> dict[str, Any]:
    c = {k: v for k, v in comp.items() if v > 0}
    n = sum(c.values())
    if n == 0:
        return {"landing": None, "clear": False, "margin": None, "n": 0}
    order = sorted(c, key=lambda m: (-c[m], cat_order.index(m) if m in cat_order else 99, m))
    top = order[0]
    second = c[order[1]] if len(order) > 1 else 0
    margin = (c[top] - second) / n
    clear = margin >= TH["LANDING_MARGIN"]
    return {"landing": top if clear else None, "modal": top, "clear": clear, "margin": margin, "n": n}


def cell_qualifies(rows: list[dict[str, Any]], twin_pass: float) -> bool:
    return bool(rows) and pass_rate(rows) >= TH["PASS_FRAC"] * twin_pass


def build_event(unit: str, nudge: str, cells: dict[str, list[dict[str, Any]]], D: str, cat: list[str],
                twin_pass: float) -> dict[str, Any]:
    """cells: {cell key: labelled rows}. Pools qualifying cells; event iff >= 5 correct off-default catalogue
    programs. Returns the event record (event False when below the floor)."""
    nondef = nondef_of(cat, D)
    qual = {k: rr for k, rr in cells.items() if cell_qualifies(rr, twin_pass)}
    pooled = [r for rr in qual.values() for r in rr]
    corr_off = [r for r in pooled if is_correct(r) and r["label"] != D]
    comp_cat = collections.Counter(r["label"] for r in corr_off if r["label"] in nondef)
    outcomes = [r["label"] if r["label"] in nondef else "other" for r in corr_off]
    n_cat = sum(comp_cat.values())
    is_event = n_cat >= TH["EVENT_MIN"]
    land = landing_rule(dict(comp_cat), cat)
    return {"unit": unit, "nudge": nudge, "event": is_event, "n_cells": len(cells), "n_qualifying_cells": len(qual),
            "qualifying_cells": sorted(qual), "n_rows_pooled": len(pooled), "n_correct_offdefault_catalogue": n_cat,
            "n_correct_other": sum(1 for y in outcomes if y == "other"), "composition": dict(comp_cat),
            "landing": land["landing"] if is_event else None, "modal": land.get("modal"),
            "clear_landing": bool(is_event and land["clear"]), "landing_margin": land["margin"],
            "outcomes": outcomes if is_event else [], "D": D, "nondef": nondef, "K_u": len(cat),
            "chance": 1.0 / max(len(nondef), 1)}


# ================================================================================================ tests
def poisson_binomial_sf(k: int, ps: list[float]) -> float:
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(dist[k:].sum()) if k <= len(ps) else 0.0


def sign_test(n_plus: int, n_minus: int) -> float | None:
    n = n_plus + n_minus
    if n == 0:
        return None
    return float(stats.binom.sf(n_plus - 1, n, 0.5))


def wilcoxon_greater(d: list[float]) -> float | None:
    d = [x for x in d if x is not None and abs(x) > 1e-12]
    if not d:
        return None
    try:
        return float(stats.wilcoxon(d, alternative="greater", zero_method="wilcox", method="exact").pvalue)
    except (ValueError, TypeError):
        return None


def bca_ci(d: list[float], n_boot: int = TH["N_BOOT"], alpha: float = 0.05, seed: int = 0) -> dict[str, Any]:
    """BCa bootstrap of the mean: two-sided (1 - alpha) CI and the one-sided (1 - alpha) lower bound."""
    x = np.asarray([v for v in d if v is not None], dtype=float)
    n = len(x)
    if n < 3 or np.allclose(x, x[0]):
        m = float(x.mean()) if n else None
        return {"mean": m, "lo": m, "hi": m, "lower_one_sided": m, "n": n, "note": "degenerate (n < 3 or constant)"}
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, n, (n_boot, n))].mean(axis=1)
    th = x.mean()
    prop = (np.sum(bs < th) + 0.5 * np.sum(bs == th)) / n_boot
    prop = min(max(prop, 1.0 / n_boot), 1 - 1.0 / n_boot)
    z0 = stats.norm.ppf(prop)
    jack = np.array([np.delete(x, i).mean() for i in range(n)])
    jm = jack.mean()
    num = np.sum((jm - jack) ** 3)
    den = 6.0 * (np.sum((jm - jack) ** 2) ** 1.5)
    a = num / den if den > 0 else 0.0

    def q(z_a: float) -> float:
        adj = stats.norm.cdf(z0 + (z0 + z_a) / (1 - a * (z0 + z_a)))
        return float(np.quantile(bs, min(max(adj, 0.0), 1.0)))
    return {"mean": float(th), "lo": q(stats.norm.ppf(alpha / 2)), "hi": q(stats.norm.ppf(1 - alpha / 2)),
            "lower_one_sided": q(stats.norm.ppf(alpha)), "n": n, "z0": float(z0), "accel": float(a)}


def cluster_boot(d_by_unit: dict[str, list[float]], n_boot: int = TH["N_BOOT"], seed: int = 0) -> dict[str, Any]:
    units = sorted(u for u, v in d_by_unit.items() if v)
    if len(units) < 2:
        return {"lo": None, "hi": None, "lower_one_sided": None, "n_units": len(units)}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(units), len(units))
        xs = [x for i in pick for x in d_by_unit[units[i]]]
        vals.append(float(np.mean(xs)))
    return {"lo": float(np.quantile(vals, 0.025)), "hi": float(np.quantile(vals, 0.975)),
            "lower_one_sided": float(np.quantile(vals, 0.05)), "n_units": len(units)}


def signflip_p(d: list[float]) -> float | None:
    """Exact one-sided sign-flip permutation p of mean(d) > 0 (all 2^n flips; n <= 20)."""
    x = np.asarray([v for v in d if v is not None], dtype=float)
    n = len(x)
    if n == 0:
        return None
    if n > 20:
        rng = np.random.default_rng(0)
        signs = rng.choice([-1.0, 1.0], size=(200_000, n))
    else:
        signs = np.array(list(itertools.product([-1.0, 1.0], repeat=n)))
    obs = x.mean()
    perm = (signs * x[None, :]).mean(axis=1)
    return float(np.mean(perm >= obs - 1e-12))


def holm(ps: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted(((k, p) for k, p in ps.items() if p is not None), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, float | None] = {k: None for k, p in ps.items() if p is None}
    run = 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


# ================================================================================================ the L1 contest
def hit_test(events: list[dict[str, Any]], key: str = "r_u") -> dict[str, Any]:
    ev = [e for e in events if e.get("landing") is not None and e.get(key) is not None]
    hits = [e for e in ev if e[key] == e["landing"]]
    ps = [e["chance"] for e in ev]
    n, k = len(ev), len(hits)
    p = poisson_binomial_sf(k, ps) if n else None
    return {"forecast": key, "n_events": n, "hits": k, "rate": (k / n) if n else None,
            "mean_chance": float(np.mean(ps)) if ps else None, "poisson_binomial_p": p, "wilson95": wilson(k, n),
            "per_event": [{"unit": e["unit"], "nudge": e["nudge"], "landing": e["landing"], key: e[key],
                           "hit": e[key] == e["landing"], "chance": e["chance"]} for e in ev]}


def l1a(events: list[dict[str, Any]]) -> dict[str, Any]:
    ev = [e for e in events if e.get("TAIL_EMPTY")]
    h = hit_test(ev, "r_u")
    inferential = h["n_events"] >= TH["L1_MIN_EVENTS"]
    if inferential:
        verdict = "PASS" if (h["rate"] >= TH["L1_RATE"] and h["poisson_binomial_p"] < TH["ALPHA"]) else "NOT PASSED"
    else:
        verdict = f"DESCRIPTIVE ({h['n_events']} tail-empty events with a clear landing < 6)"
    return {**h, "subset": "TAIL-EMPTY", "inferential": inferential, "verdict": verdict,
            "n_tail_empty_events_total": len(ev)}


def discordant_sign(events: list[dict[str, Any]], rival: str, flag: str) -> dict[str, Any]:
    ev = [e for e in events if e.get(flag) and e.get("landing") is not None and e.get("r_u") is not None
          and e.get(rival) is not None]
    b_only = sum(1 for e in ev if e["r_u"] == e["landing"] and e[rival] != e["landing"])
    r_only = sum(1 for e in ev if e[rival] == e["landing"] and e["r_u"] != e["landing"])
    both = sum(1 for e in ev if e[rival] == e["landing"] and e["r_u"] == e["landing"])
    neither = len(ev) - b_only - r_only - both
    p = sign_test(b_only, r_only)
    return {"subset": flag, "rival": rival, "n_events": len(ev), "base_only": b_only, "rival_only": r_only,
            "both": both, "neither": neither, "sign_test_p_one_sided": p,
            "inferential": len(ev) >= TH["L1_MIN_EVENTS"],
            "per_event": [{"unit": e["unit"], "nudge": e["nudge"], "landing": e["landing"], "r_u": e["r_u"],
                           rival: e[rival]} for e in ev]}


def logscore_table(events: list[dict[str, Any]], forecasts: list[str], variant: str = "primary") -> list[dict[str, Any]]:
    """Per event mean log score of every forecast. variant: 'primary' | 'uniform_other' | 'other_excluded'."""
    out = []
    for e in events:
        ys = e.get("outcomes") or []
        if variant == "other_excluded":
            ys = [y for y in ys if y != "other"]
        if not ys:
            continue
        rec = {"unit": e["unit"], "nudge": e["nudge"], "provenance": e.get("provenance"), "n_outcomes": len(ys)}
        for f in forecasts:
            fq = e.get(f)
            if fq is None:
                continue
            q, defined = fq["q"], fq.get("defined", True)
            if variant == "uniform_other":
                q = uniform_other(q, e["nondef"])
            elif variant == "other_excluded":
                q = catalogue_only(q, e["nondef"])
            rec[f] = log_score(q, ys)
            rec[f + "_defined"] = defined
        out.append(rec)
    return out


def paired_contest(table: list[dict[str, Any]], a: str, b: str, noninf: bool = False, seed: int = 0) -> dict[str, Any]:
    rows = [r for r in table if r.get(a) is not None and r.get(b) is not None]
    d = [r[a] - r[b] for r in rows]
    if not d:
        return {"a": a, "b": b, "n_events": 0}
    by_unit: dict[str, list[float]] = collections.defaultdict(list)
    for r, x in zip(rows, d):
        by_unit[r["unit"]].append(x)
    bca = bca_ci(d, seed=seed)
    res = {"a": a, "b": b, "n_events": len(d), "mean_diff_nats": float(np.mean(d)), "median_diff": float(np.median(d)),
           "n_positive": sum(1 for x in d if x > 0), "wilcoxon_exact_p_one_sided": wilcoxon_greater(d),
           "bca95": bca, "unit_cluster_boot95": cluster_boot(by_unit, seed=seed),
           "unit_level_signflip_p": signflip_p([float(np.mean(v)) for v in by_unit.values()]),
           "n_units": len(by_unit)}
    dd = [r[a] - r[b] for r in rows if r.get(b + "_defined", True)]
    res["defined_only_mean_diff"] = float(np.mean(dd)) if dd else None
    res["n_defined_only"] = len(dd)
    if noninf:
        lb = bca.get("lower_one_sided")
        res["noninferior_margin"] = TH["NONINF_NATS"]
        res["noninferior"] = bool(lb is not None and lb > TH["NONINF_NATS"])
    return res


def unit_clustered(events: list[dict[str, Any]], forecasts: list[str]) -> dict[str, Any]:
    """One pooled landing per unit (FD + PN outcomes pooled; same 15-point rule) and per-unit log scores."""
    by = collections.defaultdict(list)
    for e in events:
        by[e["unit"]].append(e)
    units = []
    for u, ee in sorted(by.items()):
        comp = collections.Counter()
        ys: list[str] = []
        for e in ee:
            comp.update(e["composition"])
            ys += e["outcomes"]
        e0 = ee[0]
        land = landing_rule(dict(comp), e0["nondef"] + [e0["D"]])
        rec = {"unit": u, "nudges": [e["nudge"] for e in ee], "composition": dict(comp),
               "landing": land["landing"], "margin": land["margin"], "r_u": e0.get("r_u"), "t_u": e0.get("t_u"),
               "qlik_top1": e0.get("qlik_top1"), "chance": e0["chance"], "TAIL_EMPTY": e0.get("TAIL_EMPTY"),
               "DISCORDANT": e0.get("DISCORDANT"), "TAIL_DISCORDANT": e0.get("TAIL_DISCORDANT")}
        for f in forecasts:
            if e0.get(f) is not None:
                rec[f] = log_score(e0[f]["q"], ys)
        rec["n_outcomes"] = len(ys)
        units.append(rec)
    res = {"units": units, "hits_r_u": hit_test(units, "r_u"), "hits_t_u": hit_test(units, "t_u"),
           "hits_qlik": hit_test(units, "qlik_top1")}
    for b in [f for f in forecasts if f != "q_base"]:
        d = [r["q_base"] - r[b] for r in units if r.get("q_base") is not None and r.get(b) is not None]
        res[f"signflip_base_vs_{b}"] = {"n_units": len(d), "mean": float(np.mean(d)) if d else None,
                                        "p_one_sided": signflip_p(d)}
    return res


def l1_contest(events: list[dict[str, Any]], forecasts: tuple[str, ...] = ("q_base", "q_tail", "q_lik", "q_lik_raw"),
               assoc: bool = True) -> dict[str, Any]:
    ev = [e for e in events if e.get("event")]
    fs = list(forecasts) + (["q_assoc"] if assoc else [])
    tab = logscore_table(ev, fs)
    res: dict[str, Any] = {"n_events": len(ev),
                           "n_clear_landing": sum(1 for e in ev if e.get("landing") is not None),
                           "hits_r_u_all": hit_test(ev, "r_u"), "hits_t_u_all": hit_test(ev, "t_u"),
                           "hits_qlik_all": hit_test(ev, "qlik_top1"), "L1a_tail_empty": l1a(ev),
                           "L1b_discordant_lik": discordant_sign(ev, "qlik_top1", "DISCORDANT"),
                           "tail_rival_discordant": discordant_sign(ev, "t_u", "TAIL_DISCORDANT"),
                           "logscore_table": tab}
    contests = {"base_vs_tail": paired_contest(tab, "q_base", "q_tail", noninf=True),
                "base_vs_lik_norm": paired_contest(tab, "q_base", "q_lik"),
                "base_vs_lik_raw": paired_contest(tab, "q_base", "q_lik_raw")}
    if assoc:
        contests["base_vs_assoc"] = paired_contest(tab, "q_base", "q_assoc")
    res["logscore_contests"] = contests
    for variant in ("uniform_other", "other_excluded"):
        t2 = logscore_table(ev, fs, variant)
        res[f"logscore_contests_{variant}"] = {"base_vs_tail": paired_contest(t2, "q_base", "q_tail", noninf=True),
                                               "base_vs_lik_norm": paired_contest(t2, "q_base", "q_lik")}
    res["unit_clustered"] = unit_clustered(ev, list(forecasts))
    ps = {"L1a": res["L1a_tail_empty"]["poisson_binomial_p"], "L1b": res["L1b_discordant_lik"]["sign_test_p_one_sided"],
          "tail_sign": res["tail_rival_discordant"]["sign_test_p_one_sided"],
          "ls_base_vs_tail": contests["base_vs_tail"].get("wilcoxon_exact_p_one_sided"),
          "ls_base_vs_lik": contests["base_vs_lik_norm"].get("wilcoxon_exact_p_one_sided"),
          "hits_all": res["hits_r_u_all"]["poisson_binomial_p"]}
    res["holm_within_artifact"] = holm(ps)
    res["raw_p"] = ps
    return res


# ================================================================================================ self-test (T12)
def self_test(seed: int = 0) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    out: dict[str, Any] = {}
    # (1) planted r_u = landing on 8 of 8 events (K = 4) -> Poisson-binomial p < 0.01
    ev = [{"unit": f"U{i}", "nudge": "FD", "landing": "a", "r_u": "a", "chance": 1 / 3} for i in range(8)]
    out["planted_8_of_8_p"] = hit_test(ev)["poisson_binomial_p"]
    out["planted_detected"] = out["planted_8_of_8_p"] < 0.01
    # (2) r_u shuffled across units -> rejection rate ~ 5% (<= 0.08 over 1,000 placebos)
    rej = 0
    for _ in range(1000):
        evs = []
        for i in range(8):
            K = int(rng.integers(3, 7))
            nd = [f"m{j}" for j in range(K - 1)]
            evs.append({"unit": f"U{i}", "nudge": "FD", "landing": nd[int(rng.integers(0, len(nd)))],
                        "r_u": nd[int(rng.integers(0, len(nd)))], "chance": 1 / len(nd)})
        p = hit_test(evs)["poisson_binomial_p"]
        rej += int(p is not None and p < 0.05)
    out["placebo_rejection_rate"] = rej / 1000
    out["placebo_ok"] = out["placebo_rejection_rate"] <= 0.08
    # (3) undefined forecast -> uniform
    lf = lik_forecast({}, ["a", "b", "c"])
    out["undefined_is_uniform"] = (not lf["defined"]) and all(abs(v - 0.25) < 1e-12 for v in lf["q"].values())
    # (4) the 15-point margin rule
    out["margin_clear"] = landing_rule({"a": 6, "b": 4}, ["a", "b"])["clear"] is True          # 0.20 >= 0.15
    out["margin_unclear"] = landing_rule({"a": 5, "b": 4}, ["a", "b"])["clear"] is False       # 0.11 < 0.15
    # (5) the 'other' bin: an 'other' outcome is scored with q['other'] and is never a landing
    q = addone({"a": 3}, ["a", "b"], 1)
    out["other_scored"] = abs(log_score(q, ["other"]) - math.log(2 / 7)) < 1e-12
    e = build_event("U", "FD", {"c1": [{"label": "other", "passed": True}] * 9 + [{"label": "a", "passed": True}] * 5},
                    "d", ["d", "a", "b"], 1.0)
    out["other_never_landing"] = e["landing"] == "a" and e["outcomes"].count("other") == 9
    # (6) sign-flip and Wilcoxon sanity
    out["signflip_all_positive_n5"] = signflip_p([1, 2, 3, 4, 5])          # 1/32
    out["wilcoxon_all_positive_n5"] = wilcoxon_greater([1, 2, 3, 4, 5])    # 1/32
    out["all_ok"] = bool(out["planted_detected"] and out["placebo_ok"] and out["undefined_is_uniform"]
                         and out["margin_clear"] and out["margin_unclear"] and out["other_scored"]
                         and out["other_never_landing"] and abs(out["signflip_all_positive_n5"] - 1 / 32) < 1e-12
                         and abs(out["wilcoxon_all_positive_n5"] - 1 / 32) < 1e-9)
    return out


if __name__ == "__main__":
    import json

    print(json.dumps(self_test(), indent=1))
