"""CPU tests of the frozen analysis on synthetic data (testing_plan 5, 6)."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from escape_rule import cell_decision, share  # noqa: E402
from metrics import (hill1_rarefied, log_score, mixture_q, perm_p_spearman, poisson_binomial_sf,  # noqa: E402
                     wilson)


def test_planted_monotone_exact_p():
    x = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    y = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.9]
    r = perm_p_spearman(x, y)
    assert abs(r["rho"] - 1.0) < 1e-12
    assert r["exact"] and abs(r["p"] - 1 / math.factorial(7)) < 1e-12


def test_shuffled_placebo_uniform():
    rng = np.random.default_rng(0)
    ps = []
    for _ in range(100):
        x = rng.normal(size=8)
        y = rng.normal(size=8)
        ps.append(perm_p_spearman(x, y)["p"])
    frac = np.mean(np.array(ps) < 0.05)
    assert 0.0 <= frac <= 0.13, frac


def test_poisson_binomial_mc():
    ps = [0.2, 0.5, 0.33, 0.1, 0.25]
    rng = np.random.default_rng(1)
    sims = (rng.random((200000, len(ps))) < np.array(ps)).sum(1)
    for h in range(len(ps) + 1):
        assert abs(poisson_binomial_sf(h, ps) - np.mean(sims >= h)) < 0.005


def test_mixture_sums_to_one_and_undefined_is_uniform():
    surv = ["a", "b", "c"]
    q = mixture_q({"a": 3, "b": 1, "c": 0}, surv)
    assert abs(sum(q.values()) - 1.0) < 1e-12
    qu = mixture_q(None, surv)
    qe = mixture_q({}, surv)
    assert qu == qe
    assert abs(qu["a"] - 0.98 / 3) < 1e-12
    assert abs(log_score(qu, ["a", "zzz"]) - np.mean([math.log(0.98 / 3), math.log(0.02)])) < 1e-12


def test_hill_and_wilson():
    assert abs(hill1_rarefied(["a"] * 30)["hill1"] - 1.0) < 1e-12
    h = hill1_rarefied(["a", "b"] * 20, depth=25)
    assert 1.8 < h["hill1"] <= 2.0
    lo, hi = wilson(25, 50)
    assert abs((hi - lo) / 2 - 0.135) < 0.01


def test_escape_rule_logic():
    cat, d = {"x", "y", "z"}, "x"
    twin = [{"label": "x", "passed": True, "slot": k} for k in range(50)]
    tw = share(twin, cat, d)
    cell = [{"label": "y", "passed": True, "slot": k % 6} for k in range(30)]
    dd = cell_decision(cell, tw, cat, d)
    assert dd["screen_pass"] and dd["confirmed"] and abs(dd["p0"] - 0.5 / 51) < 1e-12
    cell2 = [{"label": "x", "passed": True, "slot": k % 2} for k in range(10)]
    assert not cell_decision(cell2, tw, cat, d)["screen_pass"]
    # 'other' is never off-default; invalid rows leave the denominator
    cell3 = [{"label": "other", "passed": True, "slot": k % 6} for k in range(30)]
    assert not cell_decision(cell3, tw, cat, d)["screen_pass"]
