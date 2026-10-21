#!/usr/bin/env python3
"""CPU unit tests T1-T5 of the testing plan (run before any decisive analysis):
T1 hook maths on synthetic tensors; T2 hull; T3 two-survivor permutation null; T4 screen byte-identity;
T5 binomial p for the C1-site count. Writes results/unit_tests_cpu.json."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cfg import RESULTS_DIR, utc_now, write_json  # noqa: E402
from hooks import apply_edit_tensor  # noqa: E402
from hull import binom_tail, hull_prices, rarefied_hill  # noqa: E402


def t1_hook(realistic: bool = True) -> dict:
    """realistic: residual norms and per-position targets taken from units/units_T03.npz at block 18 (the scales the
    GPU edits actually see); stress: targets 1-11 on |h| ~ 190 (reported, not gated)."""
    g = torch.Generator().manual_seed(0)
    D, P = 4096, 40
    idx = torch.arange(5, 30)
    if realistic:
        from cfg import UNITS_DIR

        z = np.load(UNITS_DIR / "units_T03.npz")
        scale = float(np.median(z["twin_norm_S"][18])) / np.sqrt(D)
        tgt = torch.tensor(z["nS"][18][:len(idx)], dtype=torch.float32)
    else:
        scale = 3.0
        tgt = torch.rand(len(idx), generator=g) * 10 + 1
    h_ref = torch.randn(P, D, generator=g) * scale
    h = (h_ref + torch.randn(P, D, generator=g) * scale / 6).to(torch.bfloat16)[None]
    u = torch.randn(D, generator=g)
    u = u / u.norm()
    out = apply_edit_tensor(h, idx, u, tgt, h_ref[idx])
    along = (out[0, idx].float() - h_ref[idx]) @ u
    rel = float(((along - tgt).abs() / tgt).max())
    # orthogonal components unchanged (up to the bf16 cast)
    d_before = h[0, idx].float() - h_ref[idx]
    d_after = out[0, idx].float() - h_ref[idx]
    orth_b = d_before - (d_before @ u)[:, None] * u
    orth_a = d_after - (d_after @ u)[:, None] * u
    orth_err = float(((orth_a - orth_b).norm(dim=-1) / orth_b.norm(dim=-1)).max())
    # alpha = 0 on the twin itself is the identity
    tw = h_ref.to(torch.bfloat16)[None]
    ident = torch.equal(apply_edit_tensor(tw, idx, u, torch.zeros(len(idx)), tw[0, idx].float()), tw)
    # positions outside idx untouched
    outside = torch.equal(out[0, :5], h[0, :5]) and torch.equal(out[0, 30:], h[0, 30:])
    # per-row batching equals the batch-1 loop
    hb = torch.cat([h, h], 0)
    ob = apply_edit_tensor(hb, idx, u, tgt, h_ref[idx])
    batch_eq = torch.equal(ob[0], out[0]) and torch.equal(ob[1], out[0])
    return {"max_rel_err_along_u_bf16": rel, "orthogonal_rel_change_max": orth_err, "identity_alpha0": ident,
            "outside_untouched": outside, "batch_equals_loop": batch_eq,
            "pass": rel < 1e-2 and ident and outside and batch_eq and orth_err < 2e-2}


def t2_hull() -> dict:
    s = [{"pass": 1.0, "correct_labels": ["A"] * 30},
         {"pass": 1.0, "correct_labels": ["B"] * 30}]
    r = hull_prices(s, n_draws=400, step=0.05)
    mono = []
    from hull import COST_BOUND
    import hull as H

    for b in (0.0, 0.05, 0.2):
        H.COST_BOUND = b
        s2 = [{"pass": 1.0, "correct_labels": ["A"] * 30}, {"pass": 0.8, "correct_labels": ["B"] * 20 + ["C"] * 4},
              {"pass": 0.5, "correct_labels": ["D"] * 15}]
        mono.append(hull_prices(s2, n_draws=300, step=0.1)["H5"])
    H.COST_BOUND = COST_BOUND
    # lambda = 1 (pure single setting) equals the single-arm rarefied Hill
    labs = ["A"] * 12 + ["B"] * 8 + ["C"] * 10
    single = rarefied_hill(labs, depth=25, n_sub=4000)["hill"]
    pure = hull_prices([{"pass": 1.0, "correct_labels": labs}, {"pass": 1.0, "correct_labels": ["Z"] * 30}],
                       n_draws=4000, step=0.5)
    from hull import HullSampler

    hs = HullSampler([{"pass": 1.0, "correct_labels": labs}, {"pass": 1.0, "correct_labels": ["Z"] * 30}],
                     n_draws=4000)
    h_pure = hs.hill_of(np.array([1.0, 0.0]))
    return {"equal_mix_H5": r["H5"], "equal_mix_mixture": r["H5_mixture"], "H5_monotone_in_bound": mono,
            "single_rarefied": single, "hull_pure_setting": h_pure,
            "pass": abs(r["H5"] - 2.0) < 0.1 and mono[0] <= mono[1] <= mono[2] and abs(single - h_pure) < 0.03}


def t3_perm() -> dict:
    d = {"bibfs": 1.0, "idastar": 3.0}
    q = {"bibfs": 0.7, "idastar": 0.3}
    obs = sum(q[y] * d[y] for y in q)
    vals = []
    for perm in itertools.permutations(list(d.values())):
        dd = dict(zip(d.keys(), perm))
        vals.append(sum(q[y] * dd[y] for y in q))
    p_edge = float(np.mean([v <= obs + 1e-12 for v in vals]))
    return {"n_perm": len(vals), "p_edge": p_edge, "pass": len(vals) == 2 and p_edge in (0.5, 1.0)}


def t4_screen() -> dict:
    from screen import write_screen

    a = write_screen()
    b = write_screen()
    return {"sha_a": a, "sha_b": b, "pass": a == b}


def t5_binom() -> dict:
    p = binom_tail(4, 6, 1 / 6)
    return {"p_4_of_6": p, "pass": abs(p - 0.0087) < 5e-4}


if __name__ == "__main__":
    res = {"utc": utc_now(), "T1_hook": t1_hook(True), "T2_hull": t2_hull(), "T3_perm": t3_perm(),
           "T4_screen": t4_screen(), "T5_binom": t5_binom()}
    res["all_pass"] = all(v["pass"] for k, v in res.items() if isinstance(v, dict))
    st = t1_hook(False)
    res["T1_hook_stress_small_targets"] = {k: v for k, v in st.items() if k != "pass"}
    write_json(RESULTS_DIR / "unit_tests_cpu.json", res)
    print({k: (v.get("pass") if isinstance(v, dict) else v) for k, v in res.items()})
