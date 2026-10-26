#!/usr/bin/env python3
"""CPU tests of the analysis code (testing plan 1-9) -> results/tests_cpu.json. Run before any population sample."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from common import binom_greater_p, hill1, perm_spearman  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))


def t1_projection() -> dict:
    rng = np.random.default_rng(0)
    D, k = 4096, 5
    Q = np.linalg.qr(rng.standard_normal((D, k)))[0]
    errs = []
    for target in (0.0, 0.001, 0.1, 0.5, 0.9):
        a = rng.standard_normal(k)
        a /= np.linalg.norm(a)
        b = rng.standard_normal(D)
        b -= Q @ (Q.T @ b)
        b /= np.linalg.norm(b)
        u = math.sqrt(target) * (Q @ a) + math.sqrt(1 - target) * b
        pi = float(np.sum((Q.T @ u) ** 2) / (u @ u))
        errs.append(abs(pi - target))
    orth_err = float(np.abs(Q.T @ Q - np.eye(k)).max())
    import torch
    sys.path.insert(0, str(ROOT / "src_base"))
    from hooks4 import make_edits_v4
    from cfg4 import EDIT_BLOCKS
    S = 7
    h = torch.randn(1, 20, D, dtype=torch.float32)
    href = {l: h[0, 3:3 + S].clone() + 0.1 * torch.randn(S, D) for l in EDIT_BLOCKS}
    u = torch.nn.functional.normalize(torch.randn(D), dim=0)
    M = {l: torch.rand(S) * 5 for l in EDIT_BLOCKS}
    Qt = torch.tensor(Q, dtype=torch.float32)
    e = make_edits_v4("TARGET", 3, 3 + S, {l: u for l in EDIT_BLOCKS}, M, href)
    out = e[12](h)
    comp = (out[0, 3:3 + S] - href[12]) @ u
    t_err = float((comp - M[12]).abs().max())
    e2 = make_edits_v4("CLAMP", 3, 3 + S, {l: u for l in EDIT_BLOCKS}, M, href, Q={l: Qt for l in EDIT_BLOCKS})
    out2 = e2[12](h)
    c_err = float(((out2[0, 3:3 + S] - href[12]) @ Qt).abs().max())
    untouched = bool(torch.equal(out[0, :3], h[0, :3]) and torch.equal(out[0, 3 + S:], h[0, 3 + S:]))
    return {"pi_recovery_max_err": max(errs), "Q_orthonormal_err": orth_err, "TARGET_fp32_max_err": t_err,
            "CLAMP_fp32_max_P_component": c_err, "positions_outside_S_untouched": untouched,
            "pass": max(errs) < 1e-6 and orth_err < 1e-10 and t_err < 1e-3 and c_err < 1e-3 and untouched}


def t2_spearman() -> dict:
    rng = np.random.default_rng(1)
    n, sims = 40, 500
    hits = 0
    for i in range(sims):
        x = rng.standard_normal(n)
        z = rng.standard_normal(n)
        r = 0.5
        y = r * x + math.sqrt(1 - r * r) * z   # Pearson 0.5 -> Spearman ~0.48
        hits += perm_spearman(x, y, n_perm=2000, seed=i)["p"] < 0.01
    ps = [perm_spearman(rng.standard_normal(n), rng.standard_normal(n), n_perm=2000, seed=10_000 + i)["p"]
          for i in range(sims)]
    ks = stats.kstest(ps, "uniform")
    x = rng.standard_normal(n)
    y = np.zeros(n)
    y[np.argsort(-x)[:10]] = rng.random(10)  # 30 of 40 zeros, movers among high x
    tie = perm_spearman(x, y, n_perm=10000, seed=3)
    y0 = np.zeros(n)
    y0[:10] = rng.random(10)
    tie_null = perm_spearman(x, y0, n_perm=10000, seed=4)
    return {"power_planted_r0.5_n40_p<0.01": hits / sims, "null_ks_p": float(ks.pvalue),
            "ties_30_zeros_rho": tie["rho"], "ties_30_zeros_p": tie["p"], "ties_null_p": tie_null["p"],
            "pass": hits / sims >= 0.6 and ks.pvalue > 0.05 and tie["p"] < 0.05}


def t3_escape() -> dict:
    p_true, N = 0.05, 10
    exact = 1 - stats.binom.cdf(1, N, p_true)   # >= 2 of 10 off-default (excess >= 0.2 over a collapsed twin)
    rng = np.random.default_rng(2)
    sims = 200_000
    k10 = rng.binomial(N, p_true, sims)
    passed = k10 >= 2
    k30 = k10 + rng.binomial(20, p_true, sims)
    p0 = 0.5 / 51
    pv = {k: binom_greater_p(k, 30, p0) for k in range(31)}
    conf = passed & (k30 >= 6) & np.array([pv[k] < 0.05 for k in k30])
    # null mover (true rate = the twin's, 0): false confirmation
    knull = rng.binomial(N, 0.01, sims)
    k30n = knull + rng.binomial(20, 0.01, sims)
    fconf = (knull >= 2) & (k30n >= 6)
    return {"screen_pass_prob_true5pct_N10": float(exact), "simulated": float(passed.mean()),
            "confirm_prob_true5pct": float(conf.mean()), "false_confirm_rate_rate1pct": float(fconf.mean()),
            "pass": abs(exact - 0.086) < 0.002 and float(fconf.mean()) < 0.05}


def t4_hill() -> dict:
    labs = ["quickselect"] * 51 + ["size_k_heap"] * 38 + ["full_sort"] * 3
    h = hill1(labs)
    return {"hill1_T03_correct": h, "expected": 2.234201807899341, "pass": abs(h - 2.234201807899341) < 1e-9}


def t5_logscore() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("score13", ROOT / "inputs/exp13/src/score.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    ev = None
    for l in open(ROOT / "inputs/exp13/results/c1_events.jsonl"):
        r = json.loads(l)
        if r["task"] == "T03":
            ev = r
            break
    S = [k for k in ev["forecasts"]["LADDER"] if k != "other"]
    labels = [k for k, v in ev["landing_counts"].items() for _ in range(v)]
    got = {}
    for fam in ("LADDER", "ASSOCIATE"):
        p = sc.smooth(ev["forecasts"][fam], S)
        got[fam] = sc.logscore(p, labels)
    return {"LADDER": got["LADDER"], "ASSOCIATE": got["ASSOCIATE"], "expected": {"LADDER": -1.3262, "ASSOCIATE": -1.8417},
            "pass": abs(got["LADDER"] + 1.3262) < 1e-3 and abs(got["ASSOCIATE"] + 1.8417) < 1e-3}


def t6_screen() -> dict:
    s = json.loads((ROOT / "results/screen.json").read_text())
    h = s["hypothesis_numbers_check"]
    t03 = s["tasks"]["T03"]["by_alpha"]["1.0"]["directions"]
    n17 = sum(v["escape"] for k, v in t03.items() if k.startswith("exp17"))
    return {"T03_alpha1_exp17_only": f"{n17}/15", "T03_alpha1_pooled": h["T03_alpha1"], "T2_alpha1": h["T2_alpha1"],
            "T05_alpha2": h["T05_alpha2"], "T06_alpha2": h["T06_alpha2"], "expected": h["expected"],
            "pass": n17 == 7 and h["T2_alpha1"] == 3 and h["T05_alpha2"] == 2 and h["T06_alpha2"] == 1}


def t7_ripser() -> dict:
    from ripser import ripser
    rng = np.random.default_rng(5)
    n = 60
    th = rng.uniform(0, 2 * np.pi, n)
    X = np.c_[np.cos(th), np.sin(th)] + 0.08 * rng.standard_normal((n, 2))
    X = np.c_[X, 0.05 * rng.standard_normal((n, 8))]
    def h1max(Y):
        d = ripser(Y, maxdim=1)["dgms"][1]
        return float(np.max(d[:, 1] - d[:, 0])) if len(d) else 0.0
    obs = h1max(X)
    null = []
    for i in range(100):
        Y = X.copy()
        for j in range(Y.shape[1]):
            Y[:, j] = rng.permutation(Y[:, j])
        null.append(h1max(Y))
    noise = rng.standard_normal((n, 10)) * 0.5
    obs_noise = h1max(noise)
    null_n = []
    for i in range(100):
        Y = noise.copy()
        for j in range(Y.shape[1]):
            Y[:, j] = rng.permutation(Y[:, j])
        null_n.append(h1max(Y))
    p_circle = (1 + sum(v >= obs for v in null)) / 101
    p_noise = (1 + sum(v >= obs_noise for v in null_n)) / 101
    return {"planted_circle_h1": obs, "null_q95": float(np.quantile(null, 0.95)), "p_circle": p_circle,
            "noise_p": p_noise, "pass": p_circle < 0.05 and p_noise > 0.05}


def t8_leak() -> dict:
    from describe import leak_terms, leaks, mechanisms
    m = mechanisms("T03")["median_of_medians"]
    h = leaks(m, leak_terms("T03"))
    return {"median_of_medians_mechanism_hits": h, "pass": "quickselect" in h}


def t9_r2() -> dict:
    rep = json.loads((ROOT / "prompts/prompts4_report.json").read_text())
    return {**rep["r2_ban_check"], "pass": rep["r2_ban_check"]["pass"]}


def main() -> None:
    t0 = time.time()
    res = {}
    for name, f in (("1_projection", t1_projection), ("2_spearman", t2_spearman), ("3_escape", t3_escape),
                    ("4_hill", t4_hill), ("5_logscore", t5_logscore), ("6_screen", t6_screen),
                    ("7_ripser", t7_ripser), ("8_leak", t8_leak), ("9_r2", t9_r2)):
        try:
            res[name] = f()
        except Exception as e:  # noqa: BLE001 - a failing test is recorded, never hidden
            res[name] = {"pass": False, "error": repr(e)}
        print(name, res[name].get("pass"), {k: v for k, v in res[name].items() if k != "pass"})
    res["all_pass"] = all(v.get("pass") for v in res.values() if isinstance(v, dict))
    res["seconds"] = time.time() - t0
    (ROOT / "results/tests_cpu.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
