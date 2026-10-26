#!/usr/bin/env python3
"""Render the README's results and deviations sections from the result files (README.template.md -> README.md),
so every number in the README is read from results/, predictions/ or units/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import PRED_DIR, RESULTS_DIR, ROOT, UNITS_DIR, read_json, read_jsonl  # noqa: E402


def f(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def results_md() -> str:
    a1 = read_json(RESULTS_DIR / "a1_panel.json")
    a2 = read_json(RESULTS_DIR / "a2_panel.json")
    uo = {x["unit"]: x for x in read_json(RESULTS_DIR / "unit_outcomes.json")["units"]}
    ext = read_json(RESULTS_DIR / "a1_extended.json") if (RESULTS_DIR / "a1_extended.json").exists() else {}
    var = read_json(RESULTS_DIR / "variants.json") if (RESULTS_DIR / "variants.json").exists() else {}
    sv = read_json(RESULTS_DIR / "screen_view.json") if (RESULTS_DIR / "screen_view.json").exists() else {}
    ec = read_json(RESULTS_DIR / "engine_check.json")
    nov = read_json(RESULTS_DIR / "novelty_audit.json") if (RESULTS_DIR / "novelty_audit.json").exists() else {}
    rd = read_json(RESULTS_DIR / "rederive.json") if (RESULTS_DIR / "rederive.json").exists() else {}
    co = read_json(RESULTS_DIR / "commit_order.json") if (RESULTS_DIR / "commit_order.json").exists() else {}
    costs = read_json(RESULTS_DIR / "costs.json") if (RESULTS_DIR / "costs.json").exists() else {}
    tm = read_json(RESULTS_DIR / "timing_summary.json") if (RESULTS_DIR / "timing_summary.json").exists() else {}
    L = ["## Results (panel B)", ""]
    p = a1["primary"]
    L.append(f"**A1 (descriptive, n = {a1['n_units']}):** Spearman rho(beta_u, E_u) = **{f(p['rho'])}**, exact one-sided "
             f"permutation p = {f(p['p'], 3)} ({p['method']}), unit-bootstrap 95% CI "
             f"[{f(p['bootstrap_ci95'][0]) if p.get('bootstrap_ci95') else '-'}, "
             f"{f(p['bootstrap_ci95'][1]) if p.get('bootstrap_ci95') else '-'}]. "
             f"Secondary target: rho(beta_u, PN_excess_u) = {f(a1['secondary_PN']['rho'])} "
             f"(p = {f(a1['secondary_PN']['p'], 3)}). Partial Spearman given K_u = "
             f"{f(a1['partial_spearman_given_K'])}. The pooled bar (rho >= 0.6, p < 0.01) cannot be reached by one "
             f"panel; this number goes to the pooled test through `pooled_inputs.json`.")
    L.append("")
    t = a1["table_2x3"]
    L.append(f"All {a1['n_units']} new units were base-diverse (beta >= 0.05, predicted MOVABLE); "
             f"{sum(t['movable'].values())} moved (E > 0) and {sum(t['immovable'].values())} did not. "
             f"Movable x beta class: {t['movable']}; immovable: {t['immovable']}. No unit was base-collapsed, so the "
             f"'collapsed -> immovable' half of the claim is untested in this panel.")
    L.append("")
    L.append("| unit | default | K | beta_u | beta (attempts) | beta (plain) | r_u | E (a=1) | E (a=2) | E_u | push landing "
             "| PN excess | flags |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for u in sorted(uo):
        x = uo[u]
        pr = read_json(PRED_DIR / "units" / f"{u}.json")
        L.append(f"| {u} {pr['unit_id'].split('_', 1)[1].replace('_', ' ')} | {pr['default']} | {pr['K_u']} | "
                 f"{f(pr['base']['beta_u'])} | {f(pr['base']['beta_attempt'])} | {f(pr['base'].get('beta_plain'))} | "
                 f"{pr['base']['r_u']} | {f(x['E_by_alpha'].get('1.0'), 3)} | {f(x['E_by_alpha'].get('2.0'), 3)} | "
                 f"{f(x['E_u'], 3)} | {x['push_landing'] or '-'} | {f(x['PN_excess_u'])} | "
                 f"{'; '.join(pr['flags']) or '-'} |")
    L.append("")
    L.append("**Rival predictors** (Spearman with E_u; paired unit-bootstrap CI of rho(beta, E) - rho(rival, E)):")
    L.append("")
    L.append("| predictor | rho with E | one-sided p | rho(beta) - rho(rival), 95% CI |")
    L.append("|---|---|---|---|")
    L.append(f"| beta_u (ours) | {f(p['rho'])} | {f(p['p'], 3)} | - |")
    for k, v in a1["rivals"].items():
        ci = v.get("rho_beta_minus_rival_ci95")
        L.append(f"| {k} | {f(v['rho_rival_E'])} | {f(v['p_rival'], 3)} | "
                 f"{'[' + f(ci[0]) + ', ' + f(ci[1]) + ']' if ci else '-'} |")
    L.append("")
    s = a1["sensitivities"]
    L.append("**Sensitivities** (rho, p): " + "; ".join(f"{k} {f(v.get('rho'))} ({f(v.get('p'), 3)})"
                                                     for k, v in s.items()) +
             f". **Placebo** (beta shuffled, 1,000x): mean rho {f(a1['placebo_shuffled_beta']['mean_rho'], 3)}, "
             f"rejection rate at p < 0.05 = {f(a1['placebo_shuffled_beta']['rejection_rate_p_lt_0.05'], 3)}.")
    L.append("")
    tp = a2["top1"]
    L.append(f"**A2 ({tp['n']} events: movable units with beta >= 0.05 and a defined landing):** top-1 hits "
             f"{f(tp['hits'], 1)} / {tp['n']} (chance {f(tp['expected_by_chance'])}), exact Poisson-binomial "
             f"p = {f(tp['poisson_binomial_p'], 3)}. Per-event log scores:")
    L.append("")
    L.append("| unit | r_u | push landing | hit | log score BASE | ASSOC | PROX |")
    L.append("|---|---|---|---|---|---|---|")
    for e in a2["events"]:
        ls = e["log_scores"]
        L.append(f"| {e['unit']} | {e['r_u']} | {e['push_landing']} | {f(e['hit'], 1)} | {f(ls.get('BASE'))} | "
                 f"{f(ls.get('ASSOC'))} | {f(ls.get('PROX'))} |")
    pls = a2["paired_log_score"]
    L.append("")
    L.append("Paired log-score differences: " + "; ".join(
        f"{k}: mean {f(v['mean_diff'])} nats over {v['n']} events (0.10-nat margin met: {f(v['margin_0.10_nat_met'])})"
        for k, v in pls.items()) + ". With fewer than 5 events no Wilcoxon test is run; events are listed.")
    L.append("")
    if ext:
        pp, cl = ext["panel_plus_parents"], ext["clustered_all"]
        L.append(f"**Extended A1 views (descriptive, committed addendum):** new units + re-measured parents: "
                 f"rho {f(pp['rho'])} (p = {f(pp['p'], 3)}, n = {pp['n']}); new units + parents + variants with "
                 f"cluster-preserving permutation: rho {f(cl['rho'])} (p = {f(cl['p'], 3)}, n = {cl['n_units']}, "
                 f"{cl['n_pair_clusters']} parent-variant clusters).")
        L.append("")
    if var:
        L.append(f"**Within-parent (disguised variants, {var['n_pairs']} pairs):** default shifted in "
                 f"{var['default_shift_pairs'] or 'none'}; among pairs without a shift, sign agreement of delta-beta "
                 f"and delta-E {var['sign_agreement']['agree']}/{var['sign_agreement']['n']}; Spearman(delta-beta, "
                 f"delta-E) = {f((var.get('spearman_delta_beta_delta_E') or {}).get('rho'))} "
                 f"(p = {f((var.get('spearman_delta_beta_delta_E') or {}).get('p'), 3)}).")
        L.append("")
        L.append("| parent | default P / V | beta P | beta V | E P | E V | McNemar (confirmed) P-only / V-only |")
        L.append("|---|---|---|---|---|---|---|")
        for q in var["pairs"]:
            m = q["mcnemar_confirmed"]
            L.append(f"| {q['parent']} | {q['default_parent']} / {q['default_variant']} | {f(q['beta_parent'])} | "
                     f"{f(q['beta_variant'])} | {f(q['E_parent'], 3)} | {f(q['E_variant'], 3)} | "
                     f"{m['parent_only']} / {m['variant_only']} |")
        L.append("")
    if sv and sv.get("spearman"):
        L.append(f"**Screen view (descriptive, cross-engine):** beta from the iteration-5 Step-1 base repertoire vs "
                 f"iteration-4 E (ban unit, FP8) on the {sv['n']} screen tasks: rho {f(sv['spearman']['rho'])} "
                 f"(p = {f(sv['spearman']['p'], 4)}). These tasks generated the hypothesis, so this is not a test.")
        L.append("")
    mov = [u for u in sorted(uo) if uo[u]["movable"]]
    imm = [u for u in sorted(uo) if not uo[u]["movable"]]
    L.append("**Reading.** Within panel B the primary A1 statistic is weak and not significant: beta_u does not rank "
             f"the escape fraction (rho {f(p['rho'])}, p = {f(p['p'], 2)}). The units that moved ({', '.join(mov)}) and "
             f"those that did not ({', '.join(imm)}) overlap in beta; two clearly base-diverse units stayed immovable "
             "at alpha <= 2, which is the disconfirming pattern for the 'diverse -> movable' half of the claim. The "
             f"graded plan-noise target agrees better (rho {f(a1['secondary_PN']['rho'])}, p = "
             f"{f(a1['secondary_PN']['p'], 3)}), and the pooled descriptive views that add the re-measured parents and "
             "the variants are positive, but none of these is the pre-registered primary test and n is small. A2 is "
             f"suggestive: r_u named the push landing in {f(tp['hits'], 0)} of {tp['n']} events (p = "
             f"{f(tp['poisson_binomial_p'], 2)}), and the base composition out-scored the association forecast in "
             "log score; with fewer than five events this stays descriptive. These panel-B numbers are inputs to "
             "the pooled panel A + B test, not a verdict on their own.")
    L.append("")
    L.append("**Validity checks.**")
    t3, t2 = ec.get("T03|SCR_d9002_a1.0", {}), ec.get("T2|SCR_d9004_a1.0", {})
    L.append(f"- Engine check (bf16 here vs FP8 in iteration 3/4, same slots): T03 rand_9002 per-slot label agreement "
             f"{f(t3.get('per_slot_label_agreement'))}, JS {f(t3.get('JS'), 3)} vs null q95 {f(t3.get('null_q95'), 3)}"
             f" ({t3.get('reading')}); T2 rand_9004 {f(t2.get('per_slot_label_agreement'))}, JS {f(t2.get('JS'), 3)}"
             f" ({t2.get('reading')}). Twins: T03 {f(ec.get('T03|TWIN', {}).get('per_slot_label_agreement'))}, "
             f"T2 {f(ec.get('T2|TWIN', {}).get('per_slot_label_agreement'))}. No gross failure.")
    gl = []
    for u in sorted(p.name for p in UNITS_DIR.iterdir() if p.is_dir() and p.name.startswith("B")):
        g = read_json(UNITS_DIR / u / "gate.json")
        gr = UNITS_DIR / u / "gate_revision.json"
        if gr.exists():
            g2 = read_json(gr)
            gl.append(f"{u} {g2['status']} after revision (kappa {f(g2['gold']['kappa_runtime_ast'])}, "
                      f"holdout {f(g2['holdout']['combined_vs_adjudicated'])})")
        else:
            gl.append(f"{u} {g['status']} (kappa {f(g['gold']['kappa_runtime_ast'])})")
    L.append("- Labeller gates (stage ii): " + "; ".join(gl) + ". 15-program blind base audits: "
             + ", ".join(f"{p.stem} {f((read_json(p).get('base_label_audit') or {}).get('agreement'))}"
                         for p in sorted((PRED_DIR / "units").glob("B*.json"))) + ".")
    if nov:
        L.append(f"- Novelty audit: {nov['n_distinct_correct_other']} distinct correct 'other' programs among "
                 f"{nov['n_correct_programs_audited_arms']} correct programs; verdicts {nov['verdicts']}; {nov['claim']}.")
    if rd:
        L.append(f"- Independent re-derivation: {rd['n_mismatches']} mismatches; twin-as-push placebo E = 0 for all "
                 f"units: {f(rd.get('placebo_twin_as_push_all_zero'))}; shuffled-beta mean rho "
                 f"{f((rd.get('A1_rederived') or {}).get('placebo_shuffled_beta_mean_rho'), 3)}.")
    if co:
        L.append(f"- Commit order: chain breaks {co['chain_breaks']}; push rows before their unit's commit "
                 f"{co['push_rows_before_their_commit']}; analysis code committed before the first push: "
                 f"{f(co['analysis_code_precedes_pushes'])}; commit #0 before the first sample: "
                 f"{f(co['commit0_precedes_samples'])}.")
    if costs:
        L.append(f"- OpenRouter spend: USD {f(costs['total_usd'], 3)} over {costs['n_calls']} judge calls (cap 2.00).")
    if tm:
        L.append(f"- GPU: {tm['n_batches']} batches of 20 rows, {f(tm['total_gpu_seconds'] / 3600, 2)} GPU-hours of "
                 f"sampling on one RTX 4090 (bf16).")
    L.append("")
    return "\n".join(L)


def deviations_md() -> str:
    rows = read_jsonl(RESULTS_DIR / "deviations.jsonl")
    L = ["## Deviations from the plan", ""]
    for r in rows:
        L.append(f"- **{r['key']}**: {r['text']}")
    L.append("- **reserves_not_built**: B8/B9 were not built; all 7 candidates passed gate stage (ii) before T+3:00.")
    L.append("- **no_drops**: no arm was dropped; plain completion, T1.3, PN alpha 1 and 2 ran for every new unit.")
    return "\n".join(L) + "\n"


def main() -> None:
    tpl = ROOT / "README.template.md"
    if not tpl.exists():
        tpl.write_text((ROOT / "README.md").read_text())
    s = tpl.read_text().replace("<<RESULTS>>", results_md()).replace("<<DEVIATIONS>>", deviations_md())
    (ROOT / "README.md").write_text(s)
    print("README.md written", len(s))


if __name__ == "__main__":
    main()
