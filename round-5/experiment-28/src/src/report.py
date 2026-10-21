#!/usr/bin/env python3
"""Builds results/report.md (the README's result tables) from results/*.json and predictions/commit_E1.json."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, PRED_DIR, RESULTS_DIR, read_json


def f(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def opt(name: str):
    p = RESULTS_DIR / f"{name}.json"
    return read_json(p) if p.exists() else None


def main() -> None:
    c1 = read_json(PRED_DIR / "commit_E1.json")
    esc, a1, a2, tp, pn = opt("escape"), opt("e_a1"), opt("e_a2"), opt("transplant"), opt("pn")
    na, la, reg, verd = opt("novelty_audit"), opt("pt_label_audit"), opt("regate"), opt("verdicts")
    out = []
    out.append("### Per-unit table\n")
    out.append("| Unit | D_u (twin share) | β (pt) | class | r_u | E_u (α1, α2) | E_u max | landing | r_u = landing | "
               "PN excess | novelty off | twin modal | open. margin |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in ALL_TASKS:
        u = c1["units"][t]
        e = (esc or {}).get(t, {})
        prim = e.get("primary", {})
        ea = prim.get("E_alpha", {})
        land = (e.get("landing") or {}).get("landing")
        hit = (land == u["r_u"]) if land else None
        out.append(f"| {t} | {u['D']} ({f(u['default']['share'])}) | {f(u['beta'])} | {u['class']} | {u['r_u']} | "
                   f"{f(e.get('E_u'), 3)} ({f(ea.get('a1'), 3)}, {f(ea.get('a2'), 3)}) | {f(e.get('E_u_max'), 3)} | "
                   f"{land or '–'} | {f(hit)} | {f((pn or {}).get(t, {}).get('pn_excess'))} | "
                   f"{f(u['rivals']['novelty_off_cat'])} | {f(u['rivals']['twin_modal_share'])} | "
                   f"{f(u['rivals']['opening_margin'], 1)} |")
    if a1:
        out.append("\n### E-A1\n")
        out.append(f"- n = {a1['n']} defaulted units; Spearman ρ(β, E_u) = {f(a1['rho'], 3)}, one-sided permutation p = "
                   f"{f(a1['p_one_sided_perm'], 4)} ({a1['n_perm']:,} permutations); Kendall τ-b = {f(a1['kendall_tau_b'], 3)}.")
        out.append(f"- Base-collapsed units immovable: {f(a1['immovable_frac_collapsed'])} of {a1['n_collapsed']}; "
                   f"base-diverse units with E_u = 0: {f(a1['diverse_zero_frac'])} of {a1['n_diverse']}; "
                   f"units with β ≥ 0.05: {a1['n_beta_ge_movable']}.")
        out.append(f"- Partial ρ given catalogue size K and exp23's forced-'can' count: {f(a1.get('partial_spearman_given_K_and_can'), 3)}"
                   f" (given K only: {f(a1.get('partial_spearman_given_K'), 3)}).")
        out.append(f"- **Verdict: {a1['verdict']}** ({a1['why']}).\n")
        out.append("| Rival | sign | n | ρ(rival, E) | ρ(β,E) − ρ(rival,E) | 90% bootstrap CI | β ahead |")
        out.append("|---|---|---|---|---|---|---|")
        for k, v in a1["rivals"].items():
            b = v.get("boot") or {}
            out.append(f"| {k} | {v.get('sign', '')} | {v['n']} | {f(v['rho'], 3)} | {f(b.get('diff'), 3)} | "
                       f"[{f(b.get('lo'), 3)}, {f(b.get('hi'), 3)}] | {f(v['ahead'])} |")
        out.append("\n| Sensitivity | n | ρ | p (one-sided) | verdict under the same rule |")
        out.append("|---|---|---|---|---|")
        for k, v in a1["sensitivities"].items():
            if "rho" in v:
                out.append(f"| {k} | {v['n']} | {f(v['rho'], 3)} | {f(v['p_one_sided_perm'], 4)} | {v['verdict']} |")
        fv = a1["sensitivities"].get("fresh_vs_iteration4_movability")
        if fv:
            out.append(f"\nFresh vs iteration-4 movability agreement: {f(fv['agreement'])} "
                       f"({sum(1 for v in fv['per_unit'].values() if v['fresh_movable'])} fresh movable, "
                       f"{sum(1 for v in fv['per_unit'].values() if v['iter4_movable'])} iteration-4 movable).")
    if a2:
        out.append("\n### E-A2\n")
        out.append(f"- Events: {a2['n_events']}; hits {a2['hits']}; hit rate {f(a2['hit_rate'])}; mean chance "
                   f"{f(a2['mean_chance'])}; exact Poisson-binomial p = {f(a2['poisson_binomial_p'], 4)}.")
        if a2.get("mean_base_minus_assoc") is not None:
            out.append(f"- Log score base − association = {f(a2['mean_base_minus_assoc'], 3)} nats; base − proximity = "
                       f"{f(a2.get('mean_base_minus_prox'), 3)} nats; test: {a2.get('log_score_test')}.")
        out.append(f"- **Verdict: {a2['verdict']}**.")
        if a2.get("events"):
            out.append("\n| Event | r_u | landing | landing composition | n outcomes |")
            out.append("|---|---|---|---|---|")
            for e in a2["events"]:
                out.append(f"| {e['unit']} | {e['r_u']} | {e['landing']} | {e['landing_composition']} | {e['n_outcomes']} |")
    if tp and tp.get("per_unit"):
        out.append("\n### Transplant (pt → it task-spec states)\n")
        out.append(f"λ = {tp['lambda'].get('lambda')} ({tp['lambda'].get('n_broken_at_lambda1')} of "
                   f"{tp['lambda'].get('n_S_T')} S_T tasks broke at λ = 1).\n")
        out.append("| Unit | β | twin s | T s [95% CI] | RND s | XT s | RP s | T pass ratio | RND pass ratio | McNemar T>RND (b10/b01, p) | "
                   "T>XT (b10/b01, p) | T lands on r_u | JS(T,pt) < JS(twin,pt) |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for u, v in tp["per_unit"].items():
            def s(k):
                return f((v.get(k) or {}).get("s"))
            mr = v.get("mcnemar_T_vs_RND", {})
            mx = v.get("mcnemar_T_vs_XT", {})
            ci = (v.get("T") or {}).get("s_ci95") or [None, None]
            out.append(f"| {u} | {f(v['beta'])} | {f(v['twin']['s'])} | {s('T')} [{f(ci[0])}, {f(ci[1])}] | {s('RND')} | "
                       f"{s('XT')} | {s('RP')} | {f((v.get('T') or {}).get('pass_ratio'))} | "
                       f"{f((v.get('RND') or {}).get('pass_ratio'))} | {mr.get('a_only')}/{mr.get('b_only')}, "
                       f"{f(mr.get('p_one_sided'), 3)} | {mx.get('a_only')}/{mx.get('b_only')}, {f(mx.get('p_one_sided'), 3)} | "
                       f"{f(v.get('T_lands_on_r_u'))} | {f(v.get('T_closer_to_pt'))} |")
        sm = tp["summary"]
        out.append(f"\nSupport share among valid S_T tasks: {f(sm.get('share_supporting_of_valid'))} "
                   f"(n valid = {sm.get('n_valid')}); collapsed controls within 0.05 of the twin: "
                   f"{f(sm.get('collapsed_controls_all_within_tol'))}; read-position control within 0.05 everywhere: "
                   f"{f(sm.get('rp_all_within_tol'))}.")
        if tp.get("controls"):
            out.append("\n| Collapsed control | twin s | T s | T pass ratio |")
            out.append("|---|---|---|---|")
            for u, v in tp["controls"].items():
                out.append(f"| {u} | {f(v['twin']['s'])} | {f(v['T']['s'])} | {f(v['T']['pass_ratio'])} |")
    if pn:
        out.append("\n### Plan noise (descriptive)\n")
        out.append("| Unit | twin pass | twin Hill-1 | PN α1 pass | PN α1 off-corr | PN α1 Hill-1 | PN α2 pass | PN α2 off-corr | PN α2 Hill-1 |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for t in ALL_TASKS:
            v = pn[t]
            out.append(f"| {t} | {f(v['twin']['pass'])} | {f(v['twin']['hill1_correct_d25'])} | {f(v['a1']['pass'])} | "
                       f"{f(v['a1']['off_corr'])} | {f(v['a1']['hill1_correct_d25'])} | {f(v['a2']['pass'])} | "
                       f"{f(v['a2']['off_corr'])} | {f(v['a2']['hill1_correct_d25'])} |")
    if na:
        out.append(f"\n### Novelty audit\n\n{na['n_correct_other']} correct 'other' programs across all arms; novel "
                   f"algorithms: {na['novel_count']}; by arm: {na.get('by_arm')}; rule-of-three upper bound: "
                   f"{f(na.get('rule_of_three_upper_95'), 3)}.")
    if la:
        out.append(f"\npt label audit: {la['n']} pt programs, agreement of the combined label with the two-family "
                   f"adjudication {f(la['overall_agreement_adjudicated'])}.")
    if reg:
        g = reg["gate"]
        out.append(f"\n### Re-gate\n\nbench: κ(runtime, AST) {f(g['bench']['kappa_runtime_vs_ast'])}, runtime vs adjudicated "
                   f"{f(g['bench']['runtime_vs_adjudicated'])}, final label vs adjudicated {f(g['bench']['final_label_vs_adjudicated'])}; "
                   f"suite: κ {f(g['suite']['kappa_runtime_vs_ast'])}, runtime vs adjudicated {f(g['suite']['runtime_vs_adjudicated'])}, "
                   f"final vs adjudicated {f(g['suite']['final_label_vs_adjudicated'])}; flagged tasks {reg.get('flagged_tasks')}.")
    if verd:
        out.append(f"\n### Verdicts\n\n```\n{verd}\n```")
    (RESULTS_DIR / "report.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
