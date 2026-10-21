#!/usr/bin/env python3
"""Frozen analysis code (sha256 committed in COMMIT #0): statistics and the pre-registered decision rules for
Claim B (transplant reopens the base repertoire), Claim D (de-sharpening push) and the reverse interchange.

Definitions (also restated in predictions/commit0.json):
- correct(r)       := passed every hidden test AND a program was extracted (label != 'invalid').
- catalogue label  := a label in the task's catalogue; 'other' and 'invalid' are never catalogue labels.
- off-default share (among correct) := n(correct, catalogue label != default_t) / n(correct); 'other' stays in the
                      denominator only.
- y(slot)          := 1[correct AND catalogue label != default_t] (per CRN slot; the McNemar outcome).
- default_t        := modal correct label of the S1 twin if its share among correct >= 0.6, else None.
- beta_t           := off-default share of the BASE_CHAT programs w.r.t. default_t (fewer than 20 correct even after
                      the top-up -> the same share over parseable attempts, flagged ATTEMPT).
- r_t              := the most frequent correct non-default catalogue label of BASE_CHAT (ties: more attempts, then
                      alphabetical).
- strata           := BASE-DIVERSE beta >= 0.20; BASE-COLLAPSED beta < 0.05; INTERMEDIATE otherwise.
Tests: one-sided exact McNemar = binomial(b, b + c, 1/2) upper tail on the discordant pairs of y; Holm over the
decisive family; Wilson intervals for shares, Newcombe (hybrid score) intervals for differences.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

import numpy as np
from scipy import stats as sps

NON_CATALOGUE = {"other", "invalid", None, "unknown", "unresolved", "no_code"}


# ------------------------------------------------------------------------------------------------ row helpers
def is_correct(r: dict[str, Any]) -> bool:
    return bool(r.get("passed")) and r.get("label") not in ("invalid", None)


def is_valid(r: dict[str, Any]) -> bool:
    return r.get("label") not in ("invalid", None)


def cat_label(r: dict[str, Any], cat: Iterable[str]) -> str | None:
    lab = r.get("label")
    return lab if lab in set(cat) else None


def y_off(r: dict[str, Any], default: str | None, cat: Iterable[str]) -> int:
    lab = cat_label(r, cat)
    return int(is_correct(r) and lab is not None and default is not None and lab != default)


def z_def(r: dict[str, Any], default: str | None) -> int:
    return int(is_correct(r) and default is not None and r.get("label") == default)


def composition(rows: list[dict[str, Any]], correct_only: bool = True) -> dict[str, int]:
    c = Counter(r.get("label") for r in rows if (is_correct(r) if correct_only else is_valid(r)))
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def off_share(rows: list[dict[str, Any]], default: str | None, cat: Iterable[str],
              attempts: bool = False) -> tuple[float | None, int, int]:
    """(share, k, n): among correct programs (attempts=True: among parseable attempts)."""
    pool = [r for r in rows if (is_valid(r) if attempts else is_correct(r))]
    cs = set(cat)
    k = sum(1 for r in pool if r.get("label") in cs and r.get("label") != default)
    return (k / len(pool) if pool else None), k, len(pool)


def default_share(rows: list[dict[str, Any]], default: str | None, attempts: bool = False
                  ) -> tuple[float | None, int, int]:
    pool = [r for r in rows if (is_valid(r) if attempts else is_correct(r))]
    k = sum(1 for r in pool if r.get("label") == default)
    return (k / len(pool) if pool else None), k, len(pool)


def pass_rate(rows: list[dict[str, Any]]) -> tuple[float | None, int, int]:
    n = len(rows)
    k = sum(is_correct(r) for r in rows)
    return (k / n if n else None), k, n


# ------------------------------------------------------------------------------------------------ diversity
def hill1(counts: dict[str, int] | Counter) -> float | None:
    v = np.array([c for c in counts.values() if c > 0], dtype=float)
    if v.sum() == 0:
        return None
    p = v / v.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def rarefied_hill1(labels: list[str], depth: int = 25, n_sub: int = 1000, seed: int = 20261021
                   ) -> dict[str, Any]:
    """Mean Hill-1 over n_sub subsamples of `depth` correct programs without replacement (fewer: all, flagged)."""
    n = len(labels)
    if n == 0:
        return {"hill1": None, "n": 0, "flag_below_depth": True}
    if n <= depth:
        return {"hill1": hill1(Counter(labels)), "n": n, "flag_below_depth": n < depth}
    rng = np.random.default_rng(seed)
    arr = np.array(labels, dtype=object)
    vals = []
    for _ in range(n_sub):
        sub = arr[rng.choice(n, size=depth, replace=False)]
        vals.append(hill1(Counter(sub.tolist())))
    return {"hill1": float(np.mean(vals)), "n": n, "flag_below_depth": False}


# ------------------------------------------------------------------------------------------------ intervals
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> dict[str, float | None]:
    """Newcombe (1998) method 10 hybrid score interval for p1 - p2 (independent proportions)."""
    if n1 == 0 or n2 == 0:
        return {"diff": None, "lo": None, "hi": None}
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {"diff": d, "lo": lo, "hi": hi}


# ------------------------------------------------------------------------------------------------ tests
def mcnemar_exact(a: list[int], b: list[int]) -> dict[str, Any]:
    """Paired binary outcomes (same CRN slots): H1 one-sided a > b. b_ = #(a=1, b=0), c_ = #(a=0, b=1)."""
    assert len(a) == len(b)
    b_ = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    c_ = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = b_ + c_
    if n == 0:
        return {"b": 0, "c": 0, "n_pairs": len(a), "p_one": 1.0, "p_two": 1.0}
    p_one = float(sps.binom.sf(b_ - 1, n, 0.5))
    p_two = float(min(1.0, 2 * min(sps.binom.cdf(b_, n, 0.5), sps.binom.sf(b_ - 1, n, 0.5))))
    return {"b": b_, "c": c_, "n_pairs": len(a), "p_one": p_one, "p_two": p_two}


def binom_upper(k: int, n: int, p0: float) -> float:
    if n == 0:
        return 1.0
    return float(sps.binom.sf(k - 1, n, min(max(p0, 1e-12), 1 - 1e-12)))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    keys = sorted(pvals, key=lambda k: pvals[k])
    m = len(keys)
    out: dict[str, float] = {}
    run = 0.0
    for i, k in enumerate(keys):
        adj = min(1.0, (m - i) * pvals[k])
        run = max(run, adj)
        out[k] = run
    return out


def pair_rows(a_rows: list[dict[str, Any]], b_rows: list[dict[str, Any]]) -> list[tuple[dict, dict]]:
    """Pair rows of two arms on the same (template, slot)."""
    bm = {(r["template"], int(r["slot"])): r for r in b_rows}
    out = []
    for r in a_rows:
        k = (r["template"], int(r["slot"]))
        if k in bm:
            out.append((r, bm[k]))
    return sorted(out, key=lambda p: (p[0]["template"], int(p[0]["slot"])))


def template_robustness(a_rows: list[dict[str, Any]], b_rows: list[dict[str, Any]], default: str | None,
                        cat: Iterable[str]) -> dict[str, Any]:
    cat = list(cat)
    out = {}
    n_gt = 0
    for w in sorted({r["template"] for r in a_rows}):
        ya = [y_off(r, default, cat) for r in a_rows if r["template"] == w]
        yb = [y_off(r, default, cat) for r in b_rows if r["template"] == w]
        ra = float(np.mean(ya)) if ya else None
        rb = float(np.mean(yb)) if yb else None
        out[w] = {"y_rate_arm": ra, "y_rate_control": rb}
        n_gt += int(ra is not None and rb is not None and ra > rb)
    return {"by_template": out, "n_templates_arm_gt_control": n_gt, "n_templates": len(out)}


# ------------------------------------------------------------------------------------------------ base repertoire
def default_from_twin(rows: list[dict[str, Any]], min_share: float = 0.6) -> tuple[str | None, float | None]:
    comp = composition(rows)
    n = sum(comp.values())
    if n == 0:
        return None, None
    lab, k = max(comp.items(), key=lambda kv: (kv[1], str(kv[0]) == "other" and -1 or 0, str(kv[0])))
    share = k / n
    if lab in NON_CATALOGUE or share < min_share:
        return None, share
    return lab, share


def runner_up(rows: list[dict[str, Any]], default: str | None, cat: Iterable[str]) -> str | None:
    cs = set(cat)
    corr = Counter(r["label"] for r in rows if is_correct(r) and r.get("label") in cs and r["label"] != default)
    if not corr:
        return None
    att = Counter(r["label"] for r in rows if is_valid(r) and r.get("label") in cs)
    return sorted(corr, key=lambda m: (-corr[m], -att.get(m, 0), m))[0]


def stratum(beta: float | None, diverse: float = 0.20, collapsed: float = 0.05) -> str | None:
    if beta is None:
        return None
    if beta >= diverse:
        return "BASE-DIVERSE"
    if beta < collapsed:
        return "BASE-COLLAPSED"
    return "INTERMEDIATE"


def base_beta(rows: list[dict[str, Any]], default: str | None, cat: Iterable[str], min_correct: int = 20
              ) -> dict[str, Any]:
    s, k, n = off_share(rows, default, cat)
    flag = n < min_correct
    if flag:
        s2, k2, n2 = off_share(rows, default, cat, attempts=True)
        return {"beta": s2, "k": k2, "n": n2, "basis": "ATTEMPT", "n_correct": n, "beta_correct_only": s}
    return {"beta": s, "k": k, "n": n, "basis": "CORRECT", "n_correct": n}


def beta_bootstrap(rows: list[dict[str, Any]], default: str | None, cat: Iterable[str], B: int = 2000,
                   seed: int = 20261021, min_correct: int = 20) -> dict[str, Any]:
    """Template-cluster bootstrap: resample the 5 templates with replacement (all rows of a template together)."""
    by_w: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_w.setdefault(r["template"], []).append(r)
    ws = sorted(by_w)
    rng = np.random.default_rng(seed)
    point = base_beta(rows, default, cat, min_correct)
    st0 = stratum(point["beta"])
    vals, same = [], 0
    for _ in range(B):
        pick = rng.choice(len(ws), size=len(ws), replace=True)
        rr = [r for i in pick for r in by_w[ws[i]]]
        b = base_beta(rr, default, cat, min_correct)["beta"]
        if b is None:
            continue
        vals.append(b)
        same += int(stratum(b) == st0)
    if not vals:
        return {"ci": [None, None], "stability": None, "n_boot": 0}
    return {"ci": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
            "stability": same / len(vals), "n_boot": len(vals)}


def smoothed_landing(rows: list[dict[str, Any]], default: str | None, cat: Iterable[str]) -> dict[str, float]:
    modes = [m for m in cat if m != default]
    c = Counter(r["label"] for r in rows if is_correct(r) and r.get("label") in set(modes))
    tot = sum(c.values()) + 0.5 * len(modes)
    return {m: (c.get(m, 0) + 0.5) / tot for m in modes} if modes else {}


def derangement(tasks: list[str], seed: int) -> dict[str, str]:
    """Seeded random derangement (no fixed points) by rejection sampling of permutations."""
    rng = np.random.default_rng(seed)
    ts = sorted(tasks)
    if len(ts) < 2:
        return {}
    while True:
        perm = rng.permutation(len(ts))
        if all(perm[i] != i for i in range(len(ts))):
            return {ts[i]: ts[int(perm[i])] for i in range(len(ts))}


# ------------------------------------------------------------------------------------------------ rules
def select_lambda(cells: dict[float, dict[str, Any]], twin_pass: float, frac: float = 0.8) -> float | None:
    """cells[lam] = {'pass': p, 'off_share': s}; lam* = argmax off_share among lam with pass >= frac * twin_pass;
    ties -> the smaller lambda; none -> None (UNTESTED)."""
    ok = [(lam, c) for lam, c in cells.items() if c.get("pass") is not None and c["pass"] >= frac * twin_pass
          and c.get("off_share") is not None]
    if not ok:
        return None
    best = max(c["off_share"] for _, c in ok)
    return min(lam for lam, c in ok if c["off_share"] == best)


def broken(pass_arm: float | None, twin_pass: float, frac: float = 0.8) -> bool:
    return pass_arm is None or pass_arm < frac * twin_pass


def claim_b_task(*, beta: float, r_t: str | None, pass_T: float, pass_twin: float, offshare_T: float | None,
                 p_holm: dict[str, float], mr_broke: bool, modal_T: str | None) -> dict[str, Any]:
    c1 = pass_T >= 0.8 * pass_twin
    c2 = offshare_T is not None and offshare_T >= 0.5 * beta
    need = ["MR", "XT"] + (["MRp"] if mr_broke else [])
    c3 = all(p_holm.get(k, 1.0) < 0.05 for k in need)
    c3_mr = p_holm.get("MR", 1.0) < 0.05 and (not mr_broke or p_holm.get("MRp", 1.0) < 0.05)
    c3_xt = p_holm.get("XT", 1.0) < 0.05
    c4 = modal_T is not None and modal_T == r_t
    return {"i_pass": c1, "ii_share": c2, "iii_controls": c3, "iii_vs_MR": c3_mr, "iii_vs_XT": c3_xt,
            "iv_landing": c4, "PASS": bool(c1 and c2 and c3 and c4), "controls_required": need}


def claim_b_verdict(task_res: dict[str, dict[str, Any]], n_div: int, specificity: bool, valid: bool
                    ) -> dict[str, Any]:
    if not valid:
        return {"verdict": "UNTESTED", "reason": "validity gate failed"}
    if n_div < 3:
        return {"verdict": "DESCRIPTIVE", "reason": f"only {n_div} BASE-DIVERSE tasks with a default (< 3)"}
    dec = {t: r for t, r in task_res.items() if r.get("decisive")}
    n_pass = sum(1 for r in dec.values() if r["rule"]["PASS"])
    need = math.ceil(2 * n_div / 3)
    n_iii_fail = sum(1 for r in dec.values() if not r["rule"]["iii_controls"])
    pass_ok = all(r["rule"]["i_pass"] for r in dec.values())
    if n_pass >= need and specificity:
        v = "CONFIRMED"
    elif pass_ok and n_iii_fail > len(dec) / 3:
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    branches = []
    if v == "PARTIAL":
        if any(r["rule"]["iii_vs_MR"] and not r["rule"]["iii_vs_XT"] for r in dec.values()):
            branches.append("beats MR but not XT -> a generic base shift reopens")
        if not specificity:
            branches.append("specificity failed (READ moves or collapsed tasks move)")
        if any(r["rule"]["iii_controls"] and not r["rule"]["iv_landing"] for r in dec.values()):
            branches.append("lands off r_t -> reopens, but not the base runner-up")
    return {"verdict": v, "n_decisive": len(dec), "n_pass": n_pass, "needed": need, "n_iii_fail": n_iii_fail,
            "specificity": specificity, "branches": branches}


def escapes(*, k_off: int, n: int, off_share_arm: float | None, off_share_twin: float, pass_arm: float,
            pass_twin: float, twin_k: int, twin_n: int) -> dict[str, Any]:
    """Claim D cell rule: off-default share (among correct) >= twin + 0.20 AND pass >= 0.8 x twin AND one-sided exact
    binomial p < 0.05 of k_off (correct off-default slots out of n) against the twin's smoothed per-slot rate
    p0 = (twin_k + 0.5) / (twin_n + 1)."""
    p0 = (twin_k + 0.5) / (twin_n + 1)
    p = binom_upper(k_off, n, p0)
    ok = (off_share_arm is not None and off_share_arm >= off_share_twin + 0.20 and pass_arm >= 0.8 * pass_twin
          and p < 0.05)
    return {"escapes": bool(ok), "p_binom": p, "p0": p0}


def claim_d_task(a_ds: float | None, a_iso: float | None, ds_landing: str | None, r_t: str | None) -> dict[str, Any]:
    if a_ds is None:
        return {"PASS": False, "reason": "DS never escapes"}
    if a_iso is None:  # ISO censored above 2
        ok = a_ds <= 1.0
    else:
        ok = a_ds <= 0.5 * a_iso
    return {"PASS": bool(ok and ds_landing == r_t), "dose_ok": bool(ok), "landing_ok": ds_landing == r_t}


def claim_d_verdict(task_res: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not task_res:
        return {"verdict": "UNTESTED"}
    n = len(task_res)
    n_pass = sum(1 for r in task_res.values() if r["rule"]["PASS"])
    better = sum(1 for r in task_res.values()
                 if r["a_ds"] is not None and (r["a_iso"] is None or r["a_ds"] < r["a_iso"]))
    if n_pass >= math.ceil(2 * n / 3):
        v = "CONFIRMED"
    elif better == 0:
        v = "DISCONFIRMED"
    else:
        v = "PARTIAL"
    return {"verdict": v, "n_tasks": n, "n_pass": n_pass, "n_ds_earlier_than_iso": better}


def reverse_prediction(share_rt: float | None, share_btwin: float | None, share_instr_twin: float | None
                       ) -> dict[str, Any]:
    if None in (share_rt, share_btwin, share_instr_twin):
        return {"met": None}
    need = share_btwin + 0.5 * (share_instr_twin - share_btwin)
    return {"met": bool(share_rt >= need), "threshold": need, "rise": share_rt - share_btwin,
            "predicted_min_rise": 0.5 * (share_instr_twin - share_btwin)}


def jsd(p: dict[str, int], q: dict[str, int]) -> float:
    keys = sorted(set(p) | set(q), key=str)
    a = np.array([p.get(k, 0) for k in keys], float)
    b = np.array([q.get(k, 0) for k in keys], float)
    if a.sum() == 0 or b.sum() == 0:
        return float("nan")
    a, b = a / a.sum(), b / b.sum()
    m = (a + b) / 2

    def kl(x, y):
        nz = x > 0
        return float((x[nz] * np.log2(x[nz] / y[nz])).sum())
    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def log_score(landings: list[str], dist: dict[str, float]) -> float | None:
    if not landings or not dist:
        return None
    return float(np.mean([math.log(max(dist.get(l, 0.0), 1e-12)) for l in landings]))
