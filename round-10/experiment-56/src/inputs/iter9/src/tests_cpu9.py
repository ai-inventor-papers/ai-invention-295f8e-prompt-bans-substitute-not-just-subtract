#!/usr/bin/env python3
"""S0.5 CPU unit tests (must pass before COMMIT #0): results/tests_cpu.json."""

from __future__ import annotations

import numpy as np
import torch
from loguru import logger
from scipy.spatial.distance import jensenshannon
from scipy.stats import binomtest

import stats9 as S
from cfg9 import RESULTS_DIR, setup_logging, write_json
from units9 import load_units


def run() -> dict:
    out: dict = {}
    rng = np.random.default_rng(1)
    # js_div vs scipy (full support -> no tail)
    errs = []
    for _ in range(50):
        p = rng.dirichlet(np.ones(30))
        q = rng.dirichlet(np.ones(30))
        ids = list(range(30))
        js = S.js_div(ids, np.log(p).tolist(), ids, np.log(q).tolist())
        errs.append(abs(js - jensenshannon(p, q) ** 2))
    out["js_vs_scipy_max_err"] = float(max(errs))
    out["js_vs_scipy_pass"] = max(errs) < 1e-9
    # tail bucket: two top-2 supports with equal tails -> js of the renormalised 3-bucket distributions
    js_t = S.js_div([0, 1], [np.log(0.5), np.log(0.3)], [0, 2], [np.log(0.5), np.log(0.3)])
    ref = jensenshannon([0.5, 0.3, 0.0, 0.2], [0.5, 0.0, 0.3, 0.2]) ** 2
    out["js_tail_bucket_pass"] = abs(js_t - ref) < 1e-9
    # share
    mI, mB = np.array([5.0, 3.0, 4.0]), np.array([1.0, 2.0, 0.0])
    out["share_instr_is_0"] = abs(S.share(mI, mI, mB)) < 1e-12
    out["share_base_is_1"] = abs(S.share(mI, mB, mB) - 1) < 1e-12
    mX = np.array([3.0, 2.5, 2.0])
    out["share_ratio_of_sums"] = S.share(mI, mX, mB)
    out["share_mean_of_ratios"] = S.share_mean_of_ratios(mI, mX, mB)
    out["share_ros_expected"] = abs(out["share_ratio_of_sums"] - (2 + 0.5 + 2) / (4 + 1 + 4)) < 1e-12
    # bootstrap reproducibility
    a = S.boot_mean_ci([1, 2, 3, 4, 5.5], B=2000, seed=7)
    b = S.boot_mean_ci([1, 2, 3, 4, 5.5], B=2000, seed=7)
    out["bootstrap_reproducible"] = a == b
    # McNemar vs scipy binomtest
    mc = {}
    for b_, c_ in ((8, 0), (7, 1), (6, 0)):
        ours = S.mcnemar_exact(b_, c_)
        ref = binomtest(b_, b_ + c_, 0.5).pvalue
        mc[f"{b_}:{c_}"] = [ours, ref]
    out["mcnemar"] = mc
    out["mcnemar_pass"] = all(abs(x - y) < 1e-12 for x, y in mc.values())
    # sign flip enumerates 1024 patterns: all-positive 10 values -> p = 2/1024
    out["sign_flip_10_pos"] = S.sign_flip_p(np.ones(10))
    out["sign_flip_pass"] = abs(out["sign_flip_10_pos"] - 2 / 1024) < 1e-12
    # Holm
    out["holm_pass"] = S.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
    # random-set sampler: determinism, type, band, tolerance
    from cmap9 import draw_random_sets, parse
    norms = {}
    r2 = np.random.default_rng(3)
    for l in range(36):
        norms[f"mlp|L{l}"] = float(r2.uniform(1, 10))
        for h in range(32):
            norms[f"head|L{l}|H{h}"] = float(r2.uniform(0.1, 2))
    tg = ["mlp|L27", "head|L23|H10"]
    s1 = draw_random_sets(norms, tg, 90901, 50, (20, 35), set(tg))
    s2 = draw_random_sets(norms, tg, 90901, 50, (20, 35), set(tg))
    ok = s1["sets"] == s2["sets"]
    for s in s1["sets"]:
        for t, k in zip(tg, s):
            kt, lt, _ = parse(t)
            kk, lk, _ = parse(k)
            tol = s1["meta"][t]["tolerance"]
            ok &= kk == kt and 20 <= lk <= 35 and k not in tg
            if isinstance(tol, list):
                ok &= tol[0] * norms[t] - 1e-9 <= norms[k] <= tol[1] * norms[t] + 1e-9
    out["random_sampler_pass"] = bool(ok)
    # aligned MeanCache interpolation
    from meancache_aligned import interp_rows
    x = torch.randn(7, 16)
    out["interp_identity_max_abs"] = float((interp_rows(x, 7) - x).abs().max())
    c = torch.full((5, 16), 3.25)
    out["interp_const_max_abs"] = float((interp_rows(c, 9) - 3.25).abs().max())
    out["interp_pass"] = out["interp_identity_max_abs"] == 0.0 and out["interp_const_max_abs"] < 1e-6
    # hash chain verification on a scratch chain
    from cfg9 import GENESIS, sha256_text
    links, prev = [], GENESIS
    for fs in ("a" * 64, "b" * 64):
        prev = sha256_text(prev + fs)
        links.append(prev)
    out["hash_chain_pass"] = links[1] == sha256_text(sha256_text(GENESIS + "a" * 64) + "b" * 64)
    # class-token decode asserts
    U = load_units()
    exp = {"B3": (" Kr", " Prim"), "T10": (" find", " dfs"), "G-GRID": ("visited", "\n")}
    dec = {}
    for u, (d0, a0) in exp.items():
        f = U[u]["forks"][0]
        dec[u] = {"D_str": f["D_str"][:3], "A_str": f["A_str"][:3], "pass": d0 in f["D_str"] and a0 in f["A_str"]}
    out["token_decode"] = dec
    out["token_decode_pass"] = all(v["pass"] for v in dec.values())
    out["all_pass"] = all(v for k, v in out.items() if k.endswith("_pass") or k.startswith("share_instr")
                          or k.startswith("share_base") or k == "bootstrap_reproducible" or k == "share_ros_expected")
    write_json(RESULTS_DIR / "tests_cpu.json", out)
    logger.info(f"CPU tests all_pass={out['all_pass']}")
    return out


if __name__ == "__main__":
    setup_logging("tests_cpu9")
    run()
