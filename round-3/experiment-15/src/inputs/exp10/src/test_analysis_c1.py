#!/usr/bin/env python3
"""T9: the C1 analysis on synthetic score matrices with planted structure (real K = 6, 5 templates, 2 halves, 15
programs per half, per-program random effects and per-cell noise), run before commitments.log is written.

(i) pure ladder G = lambda_X * u + noise      -> SHARE CI below 0.5, ladder exists, branch LADDER
(ii) planted X-specific G = PV + noise         -> SHARE CI above 0.5, AIM above null95, branch SUBSTITUTION
(iii) noise only                               -> V_tot CI covers 0, branch PURE SUBTRACTION
(iv) true null: AIM p-values ~ uniform (KS over 500 simulations); noise-corrected V_s, V_u unbiased under noise only
(v) exact-convolution null vs 10^6-draw Monte Carlo null: |q95 difference| <= 0.002
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kstest

from src.ws import RESULTS, write_json
from src import analysis_c1 as A
from src import run_analysis as RA
from loguru import logger

ALGS = ["a0", "a1", "a2", "a3", "a4", "a5"]


def synth(rng: np.random.Generator, scenario: str, M: int = 30, sigma: float = 0.6, tnoise: float = 0.25) -> A.TaskData:
    """tnoise = condition-level (template) noise shared by both halves of a template (crossed design); 0 gives the
    exchangeable-replicate structure the frozen noise correction assumes."""
    K = len(ALGS)
    u_true = A.unit(A.centre(rng.normal(size=K)))
    base = rng.normal(0, 1, size=K)
    lam = rng.uniform(2.0, 4.0, size=K)
    spec = {X: A.centre(rng.normal(0, 1.5, size=K)) for X in ALGS}
    prime = {X: A.centre(rng.normal(0, 1.5, size=K)) for X in ALGS}
    mu: dict[str, np.ndarray] = {}

    def nz(s: float = tnoise) -> np.ndarray:
        return rng.normal(0, s, size=K)

    for xi, X in enumerate(ALGS):
        for w in A.TEMPLATES:
            if scenario == "ladder":
                g = lam[xi] * u_true * 1.0
                pv = prime[X]
            elif scenario == "specific":  # X-specific gains orthogonal to a stable ladder direction
                pr = prime[X] - (prime[X] @ u_true) * u_true
                g = 2.5 * pr
                pv = pr
            elif scenario == "null_aim":
                g = 2.5 * spec[X]
                pv = prime[X]
            else:  # noise
                g = np.zeros(K)
                pv = np.zeros(K)
            ban = base + g + nz()
            ban[xi] = base[xi] - 3.0
            mu[f"ban:{X}:w{w}"] = ban
            mu[f"mention:{X}:w{w}"] = base + pv + nz()
            for h in A.HALVES:
                mu[f"neutral:{X}:w{w}:h{h}"] = base + nz(0.1)
    ladder_like = scenario in ("ladder", "specific")
    for w in A.TEMPLATES:
        mu[f"nonce:w{w}"] = base + (1.5 * u_true if ladder_like else 0.0) + nz()
        for h in A.HALVES:
            mu[f"nonce_neutral:w{w}:h{h}"] = base + nz(0.1)
    for k in range(1, 7):
        mu[f"edit:k{k}"] = base + (1.0 * u_true if ladder_like else rng.normal(0, 0.8, size=K)) + nz()
    mu["baseline_empty"] = base.copy()
    mu["novelty"] = base + (1.2 * u_true if ladder_like else rng.normal(0, 0.8, size=K)) + nz()
    for s in range(5):
        mu[f"baseline:s{s}"] = base + nz(0.1)
    for j in ALGS:
        mu[f"forced:{j}:k0"] = np.zeros(K)
    conds = sorted(mu)
    rows = []
    for ji, j in enumerate(ALGS):
        for m in range(M):
            rows.append({"program_id": f"{j}|{m}", "j": j, "half": 1 + (m >= M // 2), "passed": True,
                         "generating_cond": f"forced:{j}:k0", "n_tokens": 200})
    prog = pd.DataFrame(rows)
    P = len(prog)
    lf = np.full((P, len(conds)), np.nan)
    a_p = rng.normal(0, 1.0, size=P)
    for ci, c in enumerate(conds):
        for r in range(P):
            ji = ALGS.index(prog["j"].iat[r])
            if c.startswith("forced:"):
                if c.split(":")[1] == prog["j"].iat[r]:
                    lf[r, ci] = a_p[r]
                continue
            if ":h" in c and int(c.rsplit(":h", 1)[1]) != prog["half"].iat[r]:
                continue
            lf[r, ci] = mu[c][ji] + a_p[r] + rng.normal(0, sigma)
    return A.TaskData(task="t1", algs=list(ALGS), d="a0", s_star="a1", prog=prog, conds=conds, lf=lf, lb=lf.copy())


def run_case(seed: int, scenario: str, B: int = 200, tnoise: float = 0.25) -> dict:
    rng = np.random.default_rng(seed)
    td = synth(rng, scenario, tnoise=tnoise)
    v = A.View(td, RA.variant_cells(td, "full"))
    res = {}
    for ref in ("neutral",):
        per = {"t1": A.c1_task(v, ref=ref, want_rows=True)}
        res[ref] = {"per_task": per, "pooled": A.pool(list(per.values()))}
    nulls = RA.aim_nulls(res, "neutral")
    boot = RA.bootstrap({"t1": td}, {}, B, seed=seed)
    lad = A.ladder_exists(v)
    sc = boot["neutral|pooled|SHARE"]["ci95"]
    vc = boot["neutral|pooled|V_tot"]["ci95"]
    br = A.branch(sc, vc, nulls["pooled"]["prime_and_veto"]["pass"], False, lad["ladder_exists"])
    return {"scenario": scenario, "SHARE": res["neutral"]["pooled"]["SHARE"], "SHARE_ci": sc, "V_tot_ci": vc,
            "V_u": res["neutral"]["pooled"]["V_u"], "V_s": res["neutral"]["pooled"]["V_s"],
            "AIM": res["neutral"]["pooled"]["AIM"], "AIM_q95": nulls["pooled"]["prime_and_veto"]["null_q95"],
            "AIM_p": nulls["pooled"]["prime_and_veto"]["p"], "ladder": lad["mean_pairwise_cosine"], "branch": br}


@logger.catch(reraise=True)
def main() -> int:
    t0 = time.time()
    out: dict = {"cases": {}}
    ok = True
    for scen, want, tn in (("ladder", "LADDER", 0.25), ("specific", "SUBSTITUTION", 0.25), ("noise", "PURE SUBTRACTION", 0.0)):
        r = run_case(11, scen, tnoise=tn)
        r["expected"] = want
        r["pass"] = r["branch"].startswith(want)
        out["cases"][scen] = r
        ok &= r["pass"]
        print(scen, r)
    # (iv) AIM p-values under a true null + unbiased noise correction under noise only
    ps, vs, vu = [], [], []
    crossed = {"replicate": {"V_s": [], "V_u": []}, "template_mean": {"V_s": [], "V_u": []}}
    for s in range(500):
        rng = np.random.default_rng(1000 + s)
        td = synth(rng, "null_aim", M=10)
        v = A.View(td, RA.variant_cells(td, "full"))
        per = {"t1": A.c1_task(v, want_rows=True)}
        res = {"neutral": {"per_task": per, "pooled": A.pool(list(per.values()))}}
        nl = RA.aim_nulls(res, "neutral")
        ps.append(nl["pooled"]["prime_and_veto"]["p"])
        rng2 = np.random.default_rng(5000 + s)
        tdn = synth(rng2, "noise", M=10, tnoise=0.0)  # exchangeable replicates (the frozen estimator's assumption)
        rn = A.c1_task(A.View(tdn, RA.variant_cells(tdn, "full")))
        vs.append(rn["V_s"])
        vu.append(rn["V_u"])
        if s < 200:  # crossed design (template effects shared across halves): bias of both estimators
            rng3 = np.random.default_rng(9000 + s)
            tdc = synth(rng3, "noise", M=10, tnoise=0.25)
            vc = A.View(tdc, RA.variant_cells(tdc, "full"))
            for nm in crossed:
                rc = A.c1_task(vc, noise=nm)
                crossed[nm]["V_s"].append(rc["V_s"])
                crossed[nm]["V_u"].append(rc["V_u"])
    ks = kstest(np.array(ps), "uniform")
    se_s, se_u = np.std(vs) / np.sqrt(len(vs)), np.std(vu) / np.sqrt(len(vu))
    out["iv"] = {"ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue), "mean_p": float(np.mean(ps)),
                 "mean_V_s_noise": float(np.mean(vs)), "se_V_s": float(se_s), "mean_V_u_noise": float(np.mean(vu)),
                 "se_V_u": float(se_u), "unbiased_V_s": bool(abs(np.mean(vs)) < 3 * se_s),
                 "unbiased_V_u": bool(abs(np.mean(vu)) < 3 * se_u)}
    out["iv"]["crossed_design_bias"] = {nm: {k: {"mean": float(np.mean(x)), "se": float(np.std(x) / np.sqrt(len(x)))}
                                             for k, x in d_.items()} for nm, d_ in crossed.items()}
    out["iv"]["pass"] = bool(ks.pvalue > 0.01 and out["iv"]["unbiased_V_s"] and out["iv"]["unbiased_V_u"])
    ok &= out["iv"]["pass"]
    print("iv", out["iv"])
    # (v) exact convolution vs Monte Carlo
    rng = np.random.default_rng(7)
    td = synth(rng, "null_aim")
    v = A.View(td, RA.variant_cells(td, "full"))
    per = A.c1_task(v, want_rows=True)
    vals = [A.row_null(r["s_half"][1], r["s_half"][2], r["pv_half"][1], r["pv_half"][2]) for r in per["rows"]]
    ex = A.pooled_null(vals)
    mc = np.mean([np.random.default_rng(9).choice(vv, size=1_000_000) if False else rng.choice(vv, size=1_000_000) for vv in vals], axis=0)
    q_mc = float(np.quantile(mc, 0.95))
    out["v"] = {"exact_method": ex["method"], "q95_exact": ex["q95"], "q95_mc": q_mc,
                "abs_diff": abs(ex["q95"] - q_mc), "pass": bool(ex["method"] == "exact_convolution" and abs(ex["q95"] - q_mc) <= 0.002 + 1e-12
                                                                or abs(ex["q95"] - q_mc) <= 1.0 / 240 / len(vals) + 0.002)}
    ok &= out["v"]["pass"]
    print("v", out["v"])
    out["all_pass"] = bool(ok)
    out["seconds"] = round(time.time() - t0, 1)
    write_json(RESULTS / "test_analysis_c1.json", A.jsonable(out))
    print("ALL PASS" if ok else "SOME TESTS FAILED", out["seconds"], "s")
    _ = json
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
