#!/usr/bin/env python3
"""C2c: does a targeted push along default -> runner-up at the predicted half-distance b_t beat a random push of the
same per-position magnitude?

Arms (per movable task, CRN slots shared): TWIN (s = 0), C2C_r_s{0.25, 0.5, 1.0}, C2C_rand<930x>_s0.5 (random unit
direction, SAME M_s as r at s = 0.5), C2C_rm_s0.5 (masked axis, masked D), C2C_r2_s0.5 (second runner-up),
SWEEP_r_a{4, 8} (r axis at alpha x ban unit).
Committed rule: correct-only Hill-1 >= 1.8 within 5 pass points of the twin at 1 x b_t (s = 0.5) on >= 4 of 6
tasks, with nu(0.5) <= 0.5 x the median alpha of this artifact's confirmed escaping random directions.
DISCONFIRM: targeted-minus-random difference in off-default share AND in Hill (paired CRN bootstrap over slots) has a
CI including 0 on >= 4 of 6 tasks.
Also: exact McNemar on CRN-paired default/off-default flips (targeted vs random); empirical 50% runner-up crossing
dose from a logistic fit of P(label = runner-up) on s in {0, 0.25, 0.5, 1.0} (bootstrap CI) vs b_t (s = 0.5) and
s'; masked vs named axis; does the second-runner-up axis land on X2; the best point on the randomisation hull of
{twin, doses} by correct-only Hill subject to pass within 5 points (linear interpolation between doses as a
sensitivity).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from common import dist, hill1, hill1_rarefied, share


def arm_summary(rows: list[dict[str, Any]], cat: set[str], default: str, ru: str, r2: str) -> dict[str, Any]:
    s = share(rows, cat, default)
    corr = [r["label"] for r in rows if r["passed"] and r["label"] not in ("invalid", "disputed")]
    hr = hill1_rarefied(corr, depth=25)
    valid = [r for r in rows if r["label"] not in ("invalid", "disputed")]
    s.update({"hill_correct": hill1(corr) if corr else float("nan"), "hill_correct_rarefied25": hr["rarefied"],
              "hill_flag_below_depth": hr["flag_below_depth"], "n_correct": len(corr),
              "composition": dist([r["label"] for r in rows]), "composition_correct": dist(corr),
              "runner_up_share": sum(r["label"] == ru for r in valid) / len(valid) if valid else float("nan"),
              "second_share": sum(r["label"] == r2 for r in valid) / len(valid) if valid else float("nan")})
    return s


def paired(rows_a: list[dict], rows_b: list[dict], cat: set[str], default: str, n_boot: int = 2000,
           seed: int = 0) -> dict[str, Any]:
    A = {(r["template"], int(r["sample_id"])): r for r in rows_a}
    Bm = {(r["template"], int(r["sample_id"])): r for r in rows_b}
    keys = sorted(set(A) & set(Bm))
    if not keys:
        return {"n": 0}

    def off(r):
        return int(r["label"] in cat and r["label"] != default)
    oa = np.array([off(A[k]) for k in keys])
    ob = np.array([off(Bm[k]) for k in keys])
    b01 = int(np.sum((oa == 1) & (ob == 0)))
    b10 = int(np.sum((oa == 0) & (ob == 1)))
    from scipy.stats import binomtest
    mc = binomtest(b01, b01 + b10, 0.5).pvalue if b01 + b10 > 0 else 1.0
    rng = np.random.default_rng(seed)
    dsh, dh = [], []
    la = [A[k] for k in keys]
    lb = [Bm[k] for k in keys]
    for _ in range(n_boot):
        idx = rng.integers(0, len(keys), len(keys))
        dsh.append(float(oa[idx].mean() - ob[idx].mean()))
        ca = [la[i]["label"] for i in idx if la[i]["passed"]]
        cb = [lb[i]["label"] for i in idx if lb[i]["passed"]]
        dh.append((hill1(ca) if ca else 1.0) - (hill1(cb) if cb else 1.0))
    ca = [r["label"] for r in la if r["passed"]]
    cb = [r["label"] for r in lb if r["passed"]]
    return {"n": len(keys), "flips_targeted_only": b01, "flips_random_only": b10, "mcnemar_p": float(mc),
            "d_share": float(oa.mean() - ob.mean()), "d_share_ci": [float(np.quantile(dsh, .025)),
                                                                   float(np.quantile(dsh, .975))],
            "d_hill": (hill1(ca) if ca else 1.0) - (hill1(cb) if cb else 1.0),
            "d_hill_ci": [float(np.quantile(dh, .025)), float(np.quantile(dh, .975))]}


def crossing(rows_by_s: dict[float, list[dict]], ru: str, n_boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    """Logistic fit of P(label = runner-up) on s; 50% crossing s50 = -b0 / b1 (bootstrap CI over rows within dose)."""
    from sklearn.linear_model import LogisticRegression

    def fit(data):
        X = np.array([[s] for s, y in data])
        y = np.array([y for s, y in data])
        if y.min() == y.max():
            return float("nan")
        m = LogisticRegression(C=1e4).fit(X, y)
        b1, b0 = float(m.coef_[0][0]), float(m.intercept_[0])
        return -b0 / b1 if abs(b1) > 1e-9 else float("nan")
    data = [(s, int(r["label"] == ru)) for s, rr in rows_by_s.items() for r in rr
            if r["label"] not in ("invalid", "disputed")]
    if not data:
        return {"s50": float("nan")}
    s50 = fit(data)
    rng = np.random.default_rng(seed)
    bs = []
    by = {s: [(s, int(r["label"] == ru)) for r in rr if r["label"] not in ("invalid", "disputed")]
          for s, rr in rows_by_s.items()}
    for _ in range(n_boot):
        d = []
        for s, v in by.items():
            if v:
                d += [v[i] for i in rng.integers(0, len(v), len(v))]
        bs.append(fit(d))
    bs = np.array([b for b in bs if np.isfinite(b)])
    return {"s50": s50, "ci": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))] if len(bs) > 20 else None,
            "p_runner_up_by_s": {str(s): float(np.mean([y for _, y in v])) if v else float("nan")
                                 for s, v in by.items()}}


def hull(summ: dict[float, dict[str, Any]], twin_pass: float) -> dict[str, Any]:
    pts = sorted(summ)
    ok = [s for s in pts if summ[s]["pass"] >= twin_pass - 0.05 - 1e-12]
    best = max(ok, key=lambda s: summ[s]["hill_correct"]) if ok else None
    interp = []
    for a, b in zip(pts[:-1], pts[1:]):
        for f in (0.25, 0.5, 0.75):
            p = (1 - f) * summ[a]["pass"] + f * summ[b]["pass"]
            h = (1 - f) * summ[a]["hill_correct"] + f * summ[b]["hill_correct"]
            if p >= twin_pass - 0.05:
                interp.append((a + f * (b - a), h))
    bi = max(interp, key=lambda x: x[1]) if interp else None
    return {"best_dose_within_5pts": best, "best_hill": summ[best]["hill_correct"] if best is not None else None,
            "interp_best": {"s": bi[0], "hill": bi[1]} if bi else None}


def verdict(per_task: dict[str, dict[str, Any]], median_alpha_confirmed: float) -> dict[str, Any]:
    n_pass, n_dis = 0, 0
    for t, r in per_task.items():
        s05 = r["arms"].get("C2C_r_s0.5")
        if not s05:
            continue
        ok = (np.isfinite(s05["hill_correct"]) and s05["hill_correct"] >= 1.8 and
              s05["pass"] >= r["twin"]["pass"] - 0.05 - 1e-12 and
              r["nu_0.5"] <= 0.5 * median_alpha_confirmed + 1e-12)
        r["c2c_pass"] = bool(ok)
        n_pass += int(ok)
        pr = r.get("targeted_vs_random", {})
        if pr.get("n"):
            inc = pr["d_share_ci"][0] <= 0 <= pr["d_share_ci"][1] and pr["d_hill_ci"][0] <= 0 <= pr["d_hill_ci"][1]
            r["targeted_vs_random_ci_includes_0"] = bool(inc)
            n_dis += int(inc)
    return {"n_tasks_pass": n_pass, "PASS": n_pass >= 4, "n_tasks_ci_include_0": n_dis, "DISCONFIRM": n_dis >= 4,
            "median_alpha_confirmed_random": median_alpha_confirmed,
            "reading": "PASS" if n_pass >= 4 else ("DISCONFIRM" if n_dis >= 4 else "INCONCLUSIVE")}
