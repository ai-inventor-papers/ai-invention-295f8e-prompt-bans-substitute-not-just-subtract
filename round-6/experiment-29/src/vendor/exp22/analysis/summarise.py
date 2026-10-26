#!/usr/bin/env python3
"""Prints the headline numbers of every analysis (results/*.json) in compact form -> results/summary.txt."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def j(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def f(x, n=3):
    return "NA" if x is None else (f"{x:.{n}f}" if isinstance(x, float) else str(x))


def main():
    L = []
    c2a, esc, dec, c2c, c2b, c3b, nov, geo = (j(n) for n in ("c2a", "escape", "decomposition", "c2c", "c2b", "c3b",
                                                              "novelty", "geometry"))
    L.append("== C2a ==")
    for t, r in c2a.get("per_task", {}).items():
        p = r["predictors"]
        L.append(f"{t}: movers {r['n_movers_y_gt_0']}/40 underpowered={r['underpowered']} twin share "
                 f"{f(r['twin']['share'])} pass {f(r['twin']['pass'])} | rho_pi {f(p['pi']['rho'])} p {f(p['pi']['p'], 4)} "
                 f"| rho_pim {f(p['pi_masked']['rho'])} p {f(p['pi_masked']['p'], 4)} | s {f(p['s']['rho'])} "
                 f"| pi_real {f(p.get('pi_real', {}).get('rho'))} | gain {f(p.get('gain', {}).get('rho'))} "
                 f"| pi_wrong {f(p.get('pi_wrong', {}).get('rho'))} | haar q95 {f(r['haar_null']['q95'])} rank "
                 f"{f(r['haar_null']['rank_of_rho_pi'])} | partial|gain {f(r.get('partial_spearman_pi_given_gain'))} "
                 f"| AUC {f(r['split_auc_pi'].get('auc_mean'))} | E_t {r['E_t']} | kappa {f(r['kappa'])}")
    L.append(f"verdict: {c2a.get('verdict')}")
    L.append(f"pooled: {c2a.get('pooled_within_task_rho')}")
    L.append("== escape ==")
    for t, r in esc.items():
        L.append(f"{t}: twin {f(r['twin']['share'])}/{f(r['twin']['pass'])} E1 {r['E_t'].get('1.0')} E2 "
                 f"{r['E_t'].get('2.0')} land {r['push_landing_v4']} screen {r['push_landing_screen']}")
    L.append("== decomposition ==")
    for t, r in dec.get("per_task", {}).items():
        L.append(f"{t}: {r['reading']}")
        for d in r["directions"]:
            L.append(f"   {d['seed']} a{d['alpha']}: shares {d['shares']} R_uperp {f(d.get('R_uperp'))} "
                     f"{d.get('R_uperp_ci')} R_up {f(d.get('R_up'))} R_clamp {f(d.get('R_clamp'))} up_escape "
                     f"{d.get('up_escape', {}).get('passes')} JS {d.get('landing_js')}")
    L.append(f"pooled: {dec.get('pooled')}")
    L.append("== C2c ==")
    for t, r in c2c.get("per_task", {}).items():
        a = r["arms"]
        L.append(f"{t}: ru {r['runner_up']} nu0.5 {f(r['nu_0.5'])} s' {f(r['s_prime']['r']['mean'])} c2c_pass "
                 f"{r.get('c2c_pass')} crossing {r['crossing'].get('s50')} {r['crossing'].get('ci')}")
        for k, v in a.items():
            L.append(f"   {k}: share {f(v['share'])} pass {f(v['pass'])} hill {f(v['hill_correct'])} ru "
                     f"{f(v['runner_up_share'])} n {v['n']} comp {v['composition']}")
        L.append(f"   targeted_vs_random {r.get('targeted_vs_random')}")
        L.append(f"   masked_vs_named {r.get('masked_vs_named')}")
        L.append(f"   r2 {r.get('second_runner_up_lands_on_X2')}; hull {r.get('hull')}")
    L.append(f"verdict: {c2c.get('verdict')}")
    L.append("== C2b ==")
    L.append(f"pooled {c2b.get('pooled')}; classes {c2b.get('class_means')}")
    L.append("== C3b ==")
    L.append(f"{c3b.get('summary_gated')}; mov~avoid {c3b.get('spearman_movability_vs_avoidance')}; "
             f"margin~avoid {c3b.get('spearman_opening_margin_vs_avoidance')}; R2 {c3b.get('R2_prediction')}")
    L.append("== novelty ==")
    L.append(str({k: v for k, v in nov.items() if k != "items"}))
    L.append("== explore ==")
    ex = j("explore")
    for t, v in ex.get("tasks", {}).items():
        L.append(f"{t}: reliability {v.get('y_reliability')} | max proj_r rho {f(v.get('max_rho_proj_r'))} at block "
                 f"{v.get('argmax_block_proj_r')} | N30 {str(v.get('alpha2_N30'))[:300]}")
    L.append("== geometry ==")
    for t, g in geo.get("tasks", {}).items():
        for b in ("18", "23"):
            if b in g:
                L.append(f"{t} b{b}: k10 {g[b].get('k10')} persistence {g[b].get('persistence')}")
    s = "\n".join(L)
    (R / "summary.txt").write_text(s)
    print(s)


if __name__ == "__main__":
    main()
