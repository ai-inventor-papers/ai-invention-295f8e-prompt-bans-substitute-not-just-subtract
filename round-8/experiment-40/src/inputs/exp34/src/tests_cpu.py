#!/usr/bin/env python3
"""CPU tests C1-C8 -> results/unit_tests_cpu.json."""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from scipy import stats  # noqa: E402

import c7 as common  # noqa: E402
from c7 import RESULTS, read_json, write_json  # noqa: E402


def c1() -> dict:
    import engine7 as E
    g = torch.Generator().manual_seed(0)
    h = torch.randn(1, 30, 64, generator=g)
    h_ref = h[0, 5:20].clone() + 0.1 * torch.randn(15, 64, generator=g)
    u = torch.randn(64, generator=g)
    u = u / u.norm()
    M = torch.randn(15, generator=g)
    out = E.edit_target(5, 20, u, M, h_ref)(h.clone())
    comp = (out[0, 5:20] - h_ref) @ u
    rel = float(((comp - M).abs() / M.abs()).max())
    orth_before = (h[0, 5:20] - h_ref) - ((h[0, 5:20] - h_ref) @ u)[:, None] * u
    orth_after = (out[0, 5:20] - h_ref) - comp[:, None] * u
    hh = torch.zeros(1, 30, 64)
    hh[0, 5:20] = h_ref
    ident = E.edit_target(5, 20, u, torch.zeros(15), h_ref)(hh.clone())
    U = u[None].expand(15, 64)
    out2 = E.edit_target(5, 20, U, M, h_ref)(h.clone())
    cl = E.edit_clamp(5, 20, u, h_ref)(h.clone())
    return {"rel_err_along_u": rel, "pass_rel": rel < 1e-5,
            "orthogonal_unchanged_maxabs": float((orth_before - orth_after).abs().max()),
            "s0_identity_on_clean": bool(torch.allclose(ident, hh)),
            "per_position_u_equals_per_layer": float((out2 - out).abs().max()),
            "clamp_component_zero": float(((cl[0, 5:20] - h_ref) @ u).abs().max()),
            "outside_span_untouched": bool(torch.equal(out[0, :5], h[0, :5]) and torch.equal(out[0, 20:], h[0, 20:]))}


def c2() -> dict:
    rng = np.random.default_rng(0)
    pN, pD = 0.2, 0.8
    m_det = math.log(pN) - math.log(pD)
    e = pN / (pN + pD)
    m_formula = math.log(e) - math.log(1 - e)
    e1, e2 = 0.3, 0.25
    mc = np.mean([(rng.random() < e1) or (rng.random() < e2) for _ in range(200000)])
    return {"single_fork_m_det": m_det, "single_fork_m_formula": m_formula, "equal": abs(m_det - m_formula) < 1e-12,
            "multi_fork_formula": 1 - (1 - e1) * (1 - e2), "multi_fork_mc": float(mc),
            "multi_fork_ok": abs(1 - (1 - e1) * (1 - e2) - mc) < 0.005,
            "unmapped_renorm": {"p_mapped": [0.5, 0.2], "q": [0.0, 1.0], "e": 0.2 / 0.7}}


def _sim(args) -> tuple[float, bool]:
    jump, seed = args
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import c7  # noqa: F401
    from fork import change_points
    rng = np.random.default_rng(seed)
    T, S = 16, 8
    p = np.where(np.arange(T) < 3, 0.05 + jump, 0.05) if jump > 0 else np.full(T, 0.3)
    k = rng.binomial(S, p)
    r = change_points(list(k), [S] * T, n_perm=200, seed=seed)
    return jump, r["p_value"] < 0.01


def c3() -> dict:
    jobs = [(j, s) for j in (0.0, 0.2, 0.3, 0.4) for s in range(100)]
    with ProcessPoolExecutor(8, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_sim, jobs))
    out = {}
    for j in (0.0, 0.2, 0.3, 0.4):
        hits = [h for jj, h in res if jj == j]
        out[f"jump_{j}"] = float(np.mean(hits))
    return {"detection_rate_p<0.01": out, "planted_jump_at": "between positions 2 and 3 (t = 8 -> 12)",
            "n_sims": 100, "n_perm": 200, "pass_power_0.4": out["jump_0.4"] >= 0.95, "pass_null_fpr":
            out["jump_0.0"] <= 0.02}


def c4() -> dict:
    import stats7 as S
    rng = np.random.default_rng(1)
    x, y = rng.normal(size=40), rng.normal(size=40)
    rs = S.spearman(x, y)
    y2 = np.zeros(40)
    y2[:6] = rng.random(6) + 0.1
    ps = [S.perm_p(rng.normal(size=40), rng.random(40), 2000, seed=i) for i in range(40)]
    return {"spearman_vs_scipy": abs(rs - stats.spearmanr(x, y).statistic) < 1e-12,
            "tie_ceiling_34_zeros": S.tie_ceiling(y2), "placebo_median_rho": float(np.median(
                [S.spearman(rng.normal(size=40), rng.normal(size=40)) for _ in range(200)])),
            "placebo_p_uniform_ks": float(stats.kstest(ps, "uniform").pvalue),
            "kendall_vs_scipy": abs(S.kendall(x, y) - stats.kendalltau(x, y).statistic) < 1e-12}


def c6() -> dict:
    import fork7 as F
    out = {}
    for t in ("T2", "T10", "T03"):
        v = F.validate(t, 200)
        out[f"opening_classifier_{t}"] = {k: v[k] for k in ("agreement", "abstain_rate", "lexical_share", "pass",
                                                             "confusion")}
    sys.path.insert(0, str(common.V9))
    from labeller_ext import ast_rules as AX
    gold = [json.loads(l) for l in open(common.V9 / "labeller_ext" / "gold_set_v2.jsonl")]
    t1 = [g for g in gold if g.get("task") == "t1" and g.get("code")]
    agree = 0
    n = 0
    for g in t1:
        ref = g.get("adjudicated") or g.get("combined") or g.get("gold_label") or g.get("label")
        if not ref:
            continue
        n += 1
        agree += AX.label(g["code"], "t1")[0] == ref
    out["labeller_ext_t1_gold_ast_agreement"] = {"n": n, "agree": agree}
    return out


def c8() -> dict:
    from c7 import BlindnessError, guarded_e29_rows
    tmp = Path(tempfile.mkdtemp(dir=str(common.CACHE)))
    p = tmp / "dummy.jsonl"
    p.write_text(json.dumps({"key": "d|T10|W1|POP_d1_a2.0|0", "task": "T10", "arm": "POP_d1_a2.0", "label": "x"})
                 + "\n" + json.dumps({"key": "d|T10|W1|TWIN|0", "task": "T10", "arm": "TWIN", "label": "y"}) + "\n")
    skipped = len(guarded_e29_rows(p)) == 1
    refused = None
    if not common.pop_rows_released():
        try:
            guarded_e29_rows(p, allow_pop=True)
            refused = False
        except BlindnessError:
            refused = True
    return {"pop_rows_skipped_by_default": skipped, "pop_rows_refused_before_commit3": refused,
            "chain": common.verify_chain()["ok"]}


def main() -> None:
    res = {}
    for name, f in (("C1_targeted_edit", c1), ("C2_margin_math", c2), ("C3_change_points", c3),
                    ("C4_stats", c4), ("C6_labellers", c6), ("C8_blindness_chain", c8)):
        try:
            res[name] = f()
        except Exception as e:  # noqa: BLE001 - a failing test is recorded, never hidden
            res[name] = {"error": repr(e)}
    ax = RESULTS / "axis.json"
    if ax.exists():
        res["C7_seed_disjointness"] = read_json(ax).get("seed_disjointness")
    res["C5_spec_alignment"] = "asserted in axis7.fit_task / prompts7.positions for every forced, pad, twin, ban, " \
                               "placebo and T1 forced prompt (a mismatch raises)"
    write_json(RESULTS / "unit_tests_cpu.json", res)
    print(json.dumps(res, default=str)[:3000])


if __name__ == "__main__":
    main()
