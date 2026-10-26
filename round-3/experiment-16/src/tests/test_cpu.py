#!/usr/bin/env python3
"""CPU tests T3-T5 of the testing plan (T0-T2 are the S0 hash check, the labeller re-check and the S1 assertions).

T3 n-gram rule on a hand-built toy set with a known argmin, tie-break order and co-veto flags.
T4 redraw correctness: a fresh-uniform redraw after masking matches the renormalised distribution (chi-square
   p > 0.01, 200k draws); the same-uniform redraw is biased (documented, not used).
T5 analysis code on simulated arms with known shares (s_a 0.1, s_b 1.0, s_c 0.3, s_d 0.9 over 10 tasks, template
   effect added): recovers F_prompt 0.78 and F_direct 0.11; the 95% bootstrap CI covers the truth in >= 90% of
   simulated datasets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "analysis"))

from forecast_s2 import choose_ngram  # noqa: E402


def t3() -> dict:
    # baseline programs: (5, 6) present everywhere, (7,) in 4/5, (1, 2) everywhere but collateral in mode x
    base = [[1, 2, 5, 6, 9], [1, 2, 5, 6, 7], [1, 2, 5, 6, 7], [1, 2, 5, 6, 7], [5, 6, 1, 2, 7]]
    forced = {"x": [[1, 2, 3], [1, 2], [5, 4]], "y": [[5, 3], [6, 9], [8]]}
    r = choose_ngram(base, forced)
    # candidates with zero max collateral: (5,6) n=2, (7,) n=1 freq 0.8, (6,) has y collateral 1/3, (5,) x 1/3, y 1/3
    ok1 = r["ids"] == [7] and r["max_collateral"] == 0.0 and r["n"] == 1
    # tie at n=1 and zero collateral -> higher baseline frequency wins
    base2 = [[3, 4], [3, 4], [3, 4], [3, 4], [3]]
    r2 = choose_ngram(base2, {"x": [[9]]})
    ok2 = r2["ids"] == [3]
    # equal frequency -> lexicographically smallest
    r3 = choose_ngram([[8, 4], [8, 4]], {"x": [[9]]})
    ok3 = r3["ids"] == [4]
    # co-veto flags (collateral >= 0.5)
    r4 = choose_ngram([[1, 2], [1, 2]], {"x": [[1], [1, 2]], "y": [[2], [3]]})
    # (2,) and (1, 2) tie at max collateral 0.5 -> smaller n wins; (2,) has collateral 1/2 in both x and y
    ok4 = r4["ids"] == [2] and r4["co_vetoed"] == ["x", "y"] and r4["collateral"]["y"] == 0.5
    return {"argmin": ok1, "tie_frequency": ok2, "tie_lexicographic": ok3, "co_veto": ok4,
            "pass": bool(ok1 and ok2 and ok3 and ok4), "detail": [r, r2, r3, r4]}


def t4(n: int = 200_000) -> dict:
    rng = np.random.default_rng(0)
    p = np.array([0.4, 0.25, 0.2, 0.1, 0.05])
    masked = 1
    q = p.copy()
    q[masked] = 0
    q /= q.sum()
    cdf_p = np.cumsum(p)
    cdf_q = np.cumsum(q)
    u = rng.random(n)
    draw = np.searchsorted(cdf_p, u)
    fresh = draw.copy()
    same = draw.copy()
    hit = draw == masked
    fresh[hit] = np.searchsorted(cdf_q, rng.random(hit.sum()))
    same[hit] = np.searchsorted(cdf_q, u[hit])
    cf = np.bincount(fresh, minlength=5)
    cs = np.bincount(same, minlength=5)
    keep = q > 0
    pf = stats.chisquare(cf[keep], n * q[keep]).pvalue
    ps = stats.chisquare(cs[keep], n * q[keep]).pvalue
    return {"fresh_uniform_chi2_p": float(pf), "same_uniform_chi2_p": float(ps), "pass": bool(pf > 0.01 and ps < 0.01)}


def simulate(rng: np.random.Generator, T: int = 10) -> list[dict]:
    rows = []
    D = "full_sort"
    true = {"a": 0.1, "b": 1.0, "c": 0.3, "d": 0.9}
    for ti in range(T):
        t = f"S{ti:02d}"
        for wi, w in enumerate(["W1", "W2", "W3", "W4", "W5"]):
            eff = rng.normal(0, 0.05)
            for k in range(20):
                for a, s in true.items():
                    pr = float(np.clip(s + (eff if a in ("a", "c") else 0), 0, 1))
                    lab = D if rng.random() < pr else "quickselect"
                    rows.append({"task": t, "template": w, "k": k, "arm": a, "label": lab})
    return rows


def t5(n_sets: int = 200, n_boot: int = 1000) -> dict:
    import analysis as an

    orig = an.default_of
    an.default_of = lambda t: "full_sort"
    try:
        rng = np.random.default_rng(1)
        rows = simulate(rng)
        tasks = sorted({r["task"] for r in rows})
        arr = an.slot_arrays(rows, tasks)
        pt = an.point_fractions(arr)
        tf_p, tf_d = (1.0 - 0.3) / (1.0 - 0.1), (1.0 - 0.9) / (1.0 - 0.1)
        cov_p = cov_d = 0
        for i in range(n_sets):
            rr = simulate(np.random.default_rng(100 + i))
            a = an.slot_arrays(rr, tasks)
            b = an.hier_boot(a, n_boot=n_boot, seed=i)
            lo, hi = an.pct_ci(b["F_prompt"])
            cov_p += lo <= tf_p <= hi
            lo, hi = an.pct_ci(b["F_direct"])
            cov_d += lo <= tf_d <= hi
    finally:
        an.default_of = orig
    return {"F_prompt_point": pt["F_prompt"], "F_direct_point": pt["F_direct"], "truth": [tf_p, tf_d],
            "coverage_F_prompt": cov_p / n_sets, "coverage_F_direct": cov_d / n_sets,
            "pass": bool(abs(pt["F_prompt"] - tf_p) < 0.06 and abs(pt["F_direct"] - tf_d) < 0.06
                         and cov_p / n_sets >= 0.9 and cov_d / n_sets >= 0.9)}


if __name__ == "__main__":
    out = {"T3": t3(), "T4": t4(), "T5": t5()}
    (ROOT / "results" / "tests_cpu.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v["pass"] for k, v in out.items()}), json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "detail"} for k, v in out.items()})[:900])
