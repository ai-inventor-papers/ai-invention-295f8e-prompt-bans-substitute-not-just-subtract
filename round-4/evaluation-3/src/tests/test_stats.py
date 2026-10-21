"""Unit tests for src/stats.py and screen_rule.py on hand-computed toy cells."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))

from src import stats as S  # noqa: E402


def _rule():
    spec = importlib.util.spec_from_file_location("screen_rule", WS / "screen_rule.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hill1_counts():
    assert math.isclose(S.hill1_counts([5, 5]), 2.0)
    assert math.isclose(S.hill1_counts([7]), 1.0)
    # three equal categories -> 3
    assert math.isclose(S.hill1_counts([2, 2, 2]), 3.0)


def test_rarefied_hill1_edge_cases():
    rng = np.random.default_rng(0)
    assert S.rarefied_hill1([30], 25, 100, rng) == 1.0
    assert math.isclose(S.rarefied_hill1([10, 15], 25, 100, rng), S.hill1_counts([10, 15]))
    assert math.isnan(S.rarefied_hill1([10, 10], 25, 100, rng))
    # rarefying below the sample size cannot exceed the number of categories
    v = S.rarefied_hill1([20, 20, 10], 25, 500, rng)
    assert 1.0 < v <= 3.0


def test_goods_coverage():
    assert math.isclose(S.goods_coverage([1, 1, 2]), 0.5)
    assert math.isclose(S.goods_coverage([5, 5]), 1.0)


def test_h1r_cell_below_depth():
    out = S.h1r_cell(["a"] * 10 + ["b"] * 5, None, "toy", 25)
    assert out["n_c"] == 15 and math.isnan(out["value"]) and out["S_obs"] == 2


def test_wilson_and_newcombe():
    lo, hi = S.wilson(0, 10)
    assert lo == 0.0 and 0.25 < hi < 0.32
    d, lo, hi = S.newcombe_diff(10, 10, 5, 10)
    assert math.isclose(d, 0.5) and lo < 0.5 < hi


def test_poisson_binomial():
    assert math.isclose(S.poisson_binomial_sf(0, [0.3, 0.4]), 1.0)
    assert math.isclose(S.poisson_binomial_sf(1, [0.5, 0.5]), 0.75)
    assert math.isclose(S.poisson_binomial_sf(2, [0.5, 0.5]), 0.25)


def test_spearman_holm_jackknife_kappa():
    r = S.spearman_perm([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert math.isclose(r["rho"], 1.0) and r["p_perm"] <= 2 / 120 + 1e-12
    assert np.allclose(S.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    assert S.jackknife_ci(1.0, [1.0, 1.0, 1.0]) == [1.0, 1.0]
    assert math.isclose(S.cohen_kappa(list("aabb"), list("aabb")), 1.0)
    assert math.isclose(S.balanced_accuracy([1, 0, 1, 0], [1, 0, 0, 0]), (1.0 + 2 / 3) / 2)


def test_js_and_upper_bound():
    assert math.isclose(S.js_div2([1, 1], [1, 1]), 0.0, abs_tol=1e-12)
    assert math.isclose(S.js_div2([1, 0], [0, 1]), 1.0)
    assert math.isclose(S.upper_bound_zero_of_k(3), 1 - 0.1 ** (1 / 3))
    assert round(S.upper_bound_zero_of_k(15), 2) == 0.14


def test_screen_rule_escape_boundary_and_core():
    rule = _rule()
    row = {"n": 50, "n_attempted": 50, "n_default": 35, "n_passed": 40, "twin_n": 50, "twin_n_attempted": 50,
           "twin_n_default": 45, "twin_n_passed": 50, "offdef_cat_counts": {"x": 15}}
    esc, e = rule.escape_of(row)  # offdef 0.30 vs 0.10 -> excess 0.20 exactly; pass 0.80 = 0.8 x 1.00
    assert esc and math.isclose(e, 0.2)
    row2 = dict(row, n_passed=39)
    assert not rule.escape_of(row2)[0]
    core = rule.build_core({"direction_rows": [dict(row, task="T", alpha=1.0, direction_id="d1", engine="e")],
                            "ban_avoidance": {"T": 0.6}, "tasks": ["T"], "c1_event_set": ["T"], "source_sha256": {}})
    assert core["tasks"]["T"]["movable"] == 1 and core["tasks"]["T"]["push_top1"] == "x"
    assert rule.canonical_bytes(core).endswith(b"\n")
