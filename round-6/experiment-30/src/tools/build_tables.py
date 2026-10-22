#!/usr/bin/env python3
"""Markdown tables for README.md, every number read from results/*.json (so the README cannot disagree with them).
Writes tools/readme_tables.md."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def rj(n: str):
    p = R / n
    return json.loads(p.read_text()) if p.exists() else None


def f(x, d=2):
    if x is None:
        return "n/a"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def pf(p):
    if p is None:
        return "n/a"
    return f"{p:.2g}" if p >= 1e-3 else f"{p:.1e}"


def main() -> None:
    out = []
    cl = rj("cells.json") or {}
    # ---- per-site cells
    for t, alphas in (("T03", (1, 2, 4)), ("T10", (1, 2, 4)), ("T2", (2, 4))):
        tw = cl.get(f"{t}|TWIN", {})
        out.append(f"\n**{t}** (twin N = {tw.get('n')}: pass {f(tw.get('pass'))}, correct off-default "
                   f"{f(tw.get('share_correct_off_default'))}, composition {tw.get('composition_correct')})\n")
        out.append("| Site | " + " | ".join(f"α {a}: share [95% CI] / pass / invalid / id" for a in alphas) + " |")
        out.append("|---|" + "---|" * len(alphas))
        for s in ("S0", "S4", "S5", "S1", "S2", "S3", "S1E"):
            cells = []
            for a in alphas:
                c = cl.get(f"{t}|{s}_a{a}")
                if not c:
                    cells.append("–")
                    continue
                cells.append(f"{f(c['share_correct_off_default'])} [{f(c['share_ci'][0])}, {f(c['share_ci'][1])}] / "
                             f"{f(c['pass'])} / {f(c['invalid'])} / {f(c.get('byte_identical_vs_twin'))}")
            out.append(f"| {s} | " + " | ".join(cells) + " |")
        if t in ("T03", "T10"):
            c8 = cl.get(f"{t}|S4_a8")
            if c8:
                out.append(f"\nS4 at α 8 (outcome-blind extension): share {f(c8['share_correct_off_default'])}, pass "
                           f"{f(c8['pass'])}, invalid {f(c8['invalid'])}, residual fraction "
                           f"{f(c8.get('dose_disp_over_h_mean_of_ratios'), 3)}.")
    # ---- S-a
    sa = rj("s_a.json")
    if sa:
        out.append("\n**S-a (committed rule).** Verdict: **" + sa["verdict"] + "**.\n")
        out.append("| Task | selected cell (share, pass) | comparator | b:c | exact p | Holm p | selection-aware Holm p "
                   "| diff (shared slots) |")
        out.append("|---|---|---|---|---|---|---|---|")
        for t, tr in sa["tasks"].items():
            sel = tr.get("selected")
            if not sel:
                out.append(f"| {t} | no gated S0/S4 cell | | | | | | |")
                continue
            for comp, c in tr["contrasts"].items():
                out.append(f"| {t} | {sel['site']} α {sel['alpha']:g} ({f(sel['share'])}, {f(sel['pass'])}) | {comp} | "
                           f"{c['b']}:{c['c']} | {pf(c['p'])} | {pf(c['p_holm'])} | {pf(c['p_holm_selection_aware'])} | "
                           f"{f(c['diff'])} |")
        out.append("\nEvery b:c beside the selected one (S0/S4 at each α against S1/S2/S5 at the same α):\n")
        out.append("| Task | contrast | b:c (p) |")
        out.append("|---|---|---|")
        for t, tr in sa["tasks"].items():
            for k, v in tr.get("all_bc", {}).items():
                out.append(f"| {t} | {k} | {v['b']}:{v['c']} ({pf(v['p'])}) |")
        pi = sa.get("prediction_i")
        if pi:
            out.append("\nPrediction (i) (S4 >= S0 at best gated dose, both above S1/S2/S5): " +
                       "; ".join(f"{t}: S0 {v['best_gated_S0']}, S4 {v['best_gated_S4']}, max comparator "
                                 f"{f(v['max_comparator_share'])} -> {'hit' if v['hit'] else 'miss'}"
                                 for t, v in pi.items()))
    # ---- S-b
    sb = rj("s_b.json")
    if sb:
        m = sb["primary"]["mh"]
        out.append(f"\n**S-b.** Mantel-Haenszel OR (task-spec site S0/S4 vs S5/S1/S1E/S2, strata = task x decile of "
                   f"realised displacement at R, block 35): **{f(m.get('or'))} [{f(m['ci'][0])}, {f(m['ci'][1])}]** "
                   f"over {sb['primary']['n']} prefill rows; PASS = {sb['primary']['pass']}. S0 only: "
                   f"{f(sb['S0_only']['mh'].get('or'))} [{f(sb['S0_only']['mh']['ci'][0])}, "
                   f"{f(sb['S0_only']['mh']['ci'][1])}]; S4 only: {f(sb['S4_only']['mh'].get('or'))} "
                   f"[{f(sb['S4_only']['mh']['ci'][0])}, {f(sb['S4_only']['mh']['ci'][1])}]. Placebo (TS shuffled within "
                   f"task, 200x): CI excludes 1 in {f(sb['placebo_shuffled_TS_within_task']['share_ci_excludes_1'])} "
                   f"of shuffles, median OR {f(sb['placebo_shuffled_TS_within_task']['median_or'])}.")
        lt = sb.get("logistic_transmission")
        if lt:
            out.append("Logistic transmission model (L2, y ~ log disp_R35 + site + template + task): " +
                       ", ".join(f"{k} {f(v)} [{f(lt['ci95'][k][0])}, {f(lt['ci95'][k][1])}]"
                                 for k, v in lt["coef"].items() if k.startswith(("log", "site"))) + ".")
    # ---- S-c
    sc = rj("s_c.json")
    if sc:
        out.append("\n**S-c (S3, generated tokens 1-32, vs the twin on shared slots; one-sided exact McNemar).**\n")
        out.append("| Task | α | b:c | p | excess | S3 pass | gated | hit | S3 KL/step |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for t in ("T03", "T10", "T2"):
            for d in (sc.get(t) or {}).get("by_dose", []):
                kl = (sc[t].get("s3_kl_by_alpha") or {}).get(f"{d['alpha']:g}")
                out.append(f"| {t} | {d['alpha']:g} | {d['b']}:{d['c']} | {pf(d['p_one_sided'])} | {f(d['excess'])} | "
                           f"{f(d['pass_S3'])} | {d['gated']} | {d['hit']} | {f(kl, 3)} |")
    # ---- landings
    la = rj("landings.json")
    if la:
        out.append("\n**Landings (prediction ii).** " + "; ".join(
            f"{t}: {la[t]['per_cell']['modal_is_runner_up']}/{la[t]['per_cell']['n_cells']} moving cells land modally "
            f"on {la[t]['runner_up']} (per event {la[t]['per_event']['n_runner_up']}/{la[t]['per_event']['n_events']}, "
            f"binomial p vs chance 1/(K-1) = {pf(la[t]['per_event']['p_binom_vs_chance'])})"
            for t in ("T03", "T10", "T2") if t in la))
    # ---- F1
    f1 = rj("f1.json")
    if f1:
        d = f1["decision"]
        c = f1["control_label_preserving"]
        out.append(f"\n**F1.** Label-changing CRN pairs: {d['n_label_changing_pairs']}; first divergence < 32 code "
                   f"tokens after the fence line in {d['n_first_div_lt_32']} (**{f(d['share'])}** "
                   f"[{f(d['share_ci'][0])}, {f(d['share_ci'][1])}]; threshold 0.80; PASS = {d['pass']}); "
                   f"{f1['n_d_negative']} diverge before the fence line. Control (label-preserving, text-changing "
                   f"pairs): n {c['n']}, early share {f(c['share'])}; median d {f(c['median_d_change'], 0)} "
                   f"(label-changing) vs {f(c['median_d_keep'], 0)} (label-preserving), Mann-Whitney p "
                   f"{pf(c['mannwhitney_p_change_earlier'])}. Placebo re-pairing across slots: early share "
                   f"{f(f1['placebo_repaired_across_slots']['share_early'])}.")
        out.append("By site: " + "; ".join(f"{s} {v['early']}/{v['n']} ({f(v['share'])})"
                                          for s, v in f1["by_site"].items()))
    # ---- F2
    f2 = rj("f2.json")
    if f2 and isinstance(f2, dict) and f2.get("status") != "not run":
        out.append("\n**F2 (twin margin m, nats; LP48 = log-prob of the first 48 code tokens).**\n")
        out.append("| Task | default | runner-up | m | 2 x scoring SD | m_lme | m_tok | m_fork | m_all | verdict |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for t, v in f2.items():
            if not isinstance(v, dict) or "default" not in v:
                continue
            out.append(f"| {t} | {v.get('default')} | {v.get('r_u')} | {f(v.get('m'))} | "
                       f"{f(2 * v['scoring_sd']) if v.get('scoring_sd') is not None else 'n/a'} | {f(v.get('m_lme'))} | "
                       f"{f(v.get('m_tok'))} | {f(v.get('m_fork_median'))} | {f(v.get('m_all'))} | "
                       f"{v.get('verdict')} |")
        th = f2.get("T2_thinking_on")
        if th:
            out.append(f"\nThinking-on T2: m_think = {f(th.get('m_think_median'))} over {th['n_completed']} of "
                       f"{th['n_traces']} completed traces ({th['verdict']}).")
        ms = f2.get("M_screen_spearman_m_vs_E")
        if ms:
            out.append("M screen (Spearman of m with the escape fraction E, descriptive): " +
                       "; ".join(f"{k}: rho {f(v['rho'])} (p {pf(v['p'])}, n {v['n_tasks']})" for k, v in ms.items()))
    # ---- S-d
    sd = rj("s_d.json")
    if sd:
        out.append("\n**S-d (top-five prohibition as a plan-site push).**\n")
        out.append("| Setting | α | push: n correct / avoidance [CI] / on survivor | random control (S0): avoidance | "
                   "twin avoidance | push vs RC b:c (p) | t (block 18) |")
        out.append("|---|---|---|---|---|---|---|")
        for key in ("T03|TOP5", "T03|TOP3", "T10|TOP5", "T1|TOP5"):
            r = sd.get(key)
            if not r:
                continue
            for a, arm in r["arms"].items():
                p = arm["push"]
                rc = arm.get("random_control") or {}
                tw = arm.get("twin") or {}
                mc = arm.get("push_vs_random_control") or {}
                t18 = r["push_progress"]["block18"]["t"].get(a, {}).get("t_mean")
                ci = p.get("avoidance_ci") or [None, None]
                out.append(f"| {key} | {a} | {p['n_correct']} / {f(p['avoidance'])} [{f(ci[0])}, {f(ci[1])}] / "
                           f"{p['on_survivor']} | {f(rc.get('avoidance'))} | {f(tw.get('avoidance'))} | "
                           f"{mc.get('b')}:{mc.get('c')} ({pf(mc.get('p'))}) | {f(t18)} |")
        out.append("\nGeometry (forced named + masked prompts, PCA-50, k-NN geodesics, 2-D metric MDS):\n")
        out.append("| Setting | block | k | MDS stress-1 | survivor -> nearest banned geodesic | separability min |")
        out.append("|---|---|---|---|---|---|")
        for key in ("T03|TOP5", "T03|TOP3", "T10|TOP5", "T1|TOP5"):
            r = sd.get(key)
            if not r:
                continue
            for b, g in r["geometry"].items():
                sep = g.get("separability") or {}
                out.append(f"| {key} | {b} | {g['k_used']} | {f(g['mds_stress1'], 3)} | "
                           f"{ {k: round(v, 2) for k, v in g['dist_survivor_to_nearest_banned'].items()} } | "
                           f"{f(min(sep.values()) if sep else None)} |")
        out.append("\nEdge tests (|S| >= 2 only):\n")
        for key in ("T03|TOP3", "T1|TOP5"):
            r = sd.get(key)
            if not r:
                continue
            for a, arm in r["arms"].items():
                for k, v in arm.items():
                    if k.startswith("edge_test") and isinstance(v, dict):
                        for b, e in v.items():
                            if isinstance(e, dict):
                                out.append(f"- {key} α {a} {k} {b}: " + (
                                    f"n {e['n_landings']}, D_obs {f(e['D_obs'])}, p_edge {pf(e['p_edge'])}, p_opp "
                                    f"{pf(e['p_opp'])} ({e['method']})" if e.get("computable") else
                                    f"not computable ({e.get('reason')})"))
    # ---- engine checks
    ec = rj("engine_checks.json")
    if ec:
        out.append("\n**Engine checks.**\n")
        for k, v in ec.items():
            if k.startswith("U8"):
                out.append(f"- {k}: composition {v['composition']} vs exp25 {v['exp25_composition']}; off-default correct "
                           f"{v['off_default_correct']} (record {v['record_exp25']}), Fisher p {pf(v['fisher_p'])}, JS "
                           f"{f(v['JS'], 3)}; per-slot label agreement {f(v['per_slot_label_agreement'])}, identical code "
                           f"{f(v['code_identical_share'])}; PASS = {v['pass']}.")
            elif k.startswith("U9"):
                out.append(f"- {k}: n {v['n_shared']}, label agreement {f(v['label_agreement'])}, identical code "
                           f"{f(v['code_identical'])}.")
    (ROOT / "tools" / "readme_tables.md").write_text("\n".join(out) + "\n")
    print(f"wrote {len(out)} lines")


if __name__ == "__main__":
    main()
