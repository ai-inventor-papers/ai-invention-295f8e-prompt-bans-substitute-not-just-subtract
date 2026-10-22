"""Synthetic checks of the frozen analysis code (plan testing T5); run before the analysis commit:
    .venv/bin/python -m pytest -q tests/test_pool_l1.py"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

import l2l3  # noqa: E402
import m_k  # noqa: E402
import pool_l1 as P  # noqa: E402


def ev(i, unit, K=4, r_u="b", qlik="c", modal="b", tail_empty=True, counts=None, t_u=None):
    cat = ["a", "b", "c", "d", "e"][:K]
    S = cat[1:]
    q = {x: 1.0 / len(S) for x in S}
    return {"event_id": f"{unit}|E{i}", "unit_id": unit, "set": "CONFIRMATION", "is_event": True,
            "content_free": True, "default": "a", "catalogue": cat, "K": K, "r_u": r_u, "qlik_top1": qlik,
            "t_u": t_u, "tail_empty": tail_empty, "discordant": r_u != qlik, "modal_landing": modal,
            "counts": counts or {modal if modal in S else "b": 6}, "q_base": dict(q), "q_lik": dict(q),
            "q_lik_raw": dict(q), "q_tail": dict(q), "assoc": dict(q)}


def test_planted_l1a_pass():
    es = [ev(i, f"U{i}") for i in range(6)]
    r = P.l1a(es)
    assert r["hits_r_u"] == 6 and r["status"] == "PASS"
    assert abs(r["p"] - (1 / 3) ** 6) < 1e-12


def test_poisson_binomial_brute_force():
    rng = np.random.default_rng(0)
    for n in range(1, 11):
        ps = [1.0 / (int(k) - 1) for k in rng.integers(3, 8, size=n)]
        for k in range(n + 1):
            brute = 0.0
            for bits in itertools.product([0, 1], repeat=n):
                if sum(bits) >= k:
                    brute += math.prod(p if b else 1 - p for p, b in zip(ps, bits))
            assert abs(brute - P.poisson_binomial_tail(ps, k)) < 1e-12


def test_l1b_disconfirming_branch():
    es = [ev(i, f"U{i}", r_u="b", qlik="c", modal="c") for i in range(6)]
    r = P.l1b(es)
    assert r["b_r_u_only"] == 0 and r["c_qlik_only"] == 6 and r["p"] == 1.0
    res = P.analyse(es, {})
    for e in es:
        e["q_lik"] = {"b": 0.1, "c": 0.8, "d": 0.1}
    res = P.analyse(es, {})
    assert res["log_scores"]["E"]["D_lik"]["event"]["mean"] < 0
    assert P.verdict(res) == "DISCONFIRMED-IN-PANEL"


def test_sign_test_matches_scipy():
    for b in range(0, 9):
        for c in range(0, 9):
            if b + c == 0:
                continue
            assert abs(P.sign_test_one_sided(b, c) - binomtest(b, b + c, 0.5, alternative="greater").pvalue) < 1e-12


def test_bootstrap_deterministic():
    v = list(np.random.default_rng(1).normal(size=12))
    assert P.boot(v) == P.boot(v)


def test_no_clear_landing_is_miss_and_uniform_fill():
    e = ev(0, "U0", modal="NO_CLEAR_LANDING", counts={"b": 3, "c": 3})
    assert not P.hit(e, "b")
    e["q_lik"] = None
    assert abs(P.log_score(e, "lik") - P.log_score(e, "uniform")) < 1e-12
    assert P.log_score(e, "lik", undefined_as_uniform=False) is None


def test_unit_clustered_collapse():
    es = [ev(i, "U0") for i in range(3)] + [ev(9, "U1")]
    r = P.unit_level(es, {})
    assert r["n_units"] == 2


def test_l3_gamma_recovery():
    q = np.array([0.6, 0.3, 0.1])
    g_true = 2.0
    p = q ** g_true
    p = p / p.sum()
    counts = np.round(p * 100000)
    assert abs(l2l3.fit_gamma(q, counts) - g_true) <= 0.2


def test_m_exact_permutation():
    x = [0.1, 0.5, 0.2, 0.9, 0.7]
    y = [0.0, 0.3, 0.1, 0.6, 0.2]
    p = m_k.perm_p(x, y, +1)
    rx, ry = rankdata(x), rankdata(y)
    obs = np.corrcoef(rx, ry)[0, 1]
    cnt = sum(np.corrcoef(rx, ry[list(pp)])[0, 1] >= obs - 1e-12 for pp in itertools.permutations(range(5)))
    assert abs(p - cnt / 120) < 1e-12
