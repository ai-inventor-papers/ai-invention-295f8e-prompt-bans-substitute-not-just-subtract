#!/usr/bin/env python3
"""results/summary.md: every number quoted in README.md, generated from the result files (never typed by hand)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import NEW_UNITS, PRED, RESERVE_UNITS, RESULTS, ROOT, read_json, read_jsonl  # noqa: E402


def f(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def main() -> None:
    L = []
    gate = read_json(RESULTS / "units_gate.json")
    summ = read_json(RESULTS / "unit_summaries_with_extension.json")
    preds = {read_json(p)["unit"]: read_json(p) for p in sorted(PRED.glob("unit_*.json"))}
    L.append("### Units: gate, forecast (committed before any push) and outcome\n")
    L.append("| Unit | Gate (kappa / rt-vs-adj) | Default (twin share) | Base pass | beta [95% CI] | r_u | Pred. class | "
             "E (a1 / a2) | Landing L_u | PN excess S |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for u in NEW_UNITS + RESERVE_UNITS:
        g = gate.get(u, {})
        gs = f"{g.get('status')} ({f(g.get('kappa_runtime_ast'))} / {f(g.get('runtime_vs_adjudicated'))})"
        tag = " (ext.)" if u in RESERVE_UNITS else ""
        if u not in preds:
            L.append(f"| {u}{tag} | {gs} | – | – | – | – | – | – | – | – |")
            continue
        p = preds[u]
        s = summ.get(u, {})
        oc = s.get("outcome", {})
        L.append(f"| {u}{tag} | {gs} | {p['default']} ({f(p.get('twin_share'))}) | "
                 f"{f(p['base_chat']['pass_rate'])} ({p['base_chat']['n_correct']} correct) | "
                 f"{f(p['beta'])} [{f(p['beta_ci'][0])}, {f(p['beta_ci'][1])}] | {p['r']} | {p['predicted_class']} | "
                 f"{f(oc.get('E'), 3)} ({f(oc.get('E1'), 3)} / {f(oc.get('E2'), 3)}) | {oc.get('landing')} | "
                 f"{f(oc.get('S'))} |")
    for name, a1f, a2f in (("Primary set (pre-registered units)", "a1.json", "a2.json"),
                           ("With the reserve extension (A8, A9)", "a1_with_extension.json", "a2_with_extension.json")):
        a1 = read_json(RESULTS / a1f)
        a2 = read_json(RESULTS / a2f)
        L.append(f"\n### A1 / A2 -- {name}\n")
        L.append(f"- n = {a1['n_units']} units ({', '.join(a1['units'])}); Spearman rho(beta, E) = "
                 f"{f(a1['rho_beta_E'], 3)}, exact one-sided permutation p = {f(a1['perm_p_one_sided'], 3)}; "
                 f"Kendall tau-b = {f(a1['kendall_tau_b'], 3)}; rho(beta, S) = {f(a1.get('rho_beta_S'), 3)}.")
        L.append(f"- Collapsed (beta < 0.05) units that are immovable: {f(a1['collapsed_immovable'])} "
                 f"(n = {a1['n_collapsed']}); diverse (beta >= 0.2) units that are immovable: "
                 f"{f(a1['diverse_immovable'])} (n = {a1['n_diverse']}).")
        mb = a1.get("measurement_bootstrap") or {}
        L.append(f"- Measurement-error bootstrap (2,000 replicates): median rho {f(mb.get('median'), 3)}, 90% interval "
                 f"[{f((mb.get('ci90') or [None, None])[0], 3)}, {f((mb.get('ci90') or [None, None])[1], 3)}].")
        L.append(f"- Panel-level wording: {a1['wording']}.")
        L.append("\n| Rival (sign) | rho(rival, E) | Delta = rho(beta,E) - sign*rho(rival,E) | 95% task-bootstrap CI |")
        L.append("|---|---|---|---|")
        for k, v in a1["rivals"].items():
            ci = v.get("delta_ci95")
            L.append(f"| {k} ({'+' if v.get('sign', 0) > 0 else '-'}) | {f(v.get('rho_r_E'), 3)} | {f(v.get('delta'), 3)} | "
                     f"{('[' + f(ci[0], 2) + ', ' + f(ci[1], 2) + ']') if ci else '–'} |")
        L.append(f"\nA2: {a2['n_events']} events (default, beta >= 0.05, observed movable); hits r_u == L_u: "
                 f"{a2['hits']}/{a2['n_events']}; Poisson-binomial P(H >= h) = {f(a2.get('p_poisson_binomial'), 4)}.")
        if a2["events"]:
            L.append("\n| Event | r_u | L_u | n realised | log score base | association | proximity |")
            L.append("|---|---|---|---|---|---|---|")
            for e in a2["events"]:
                sc = e["log_scores"]
                L.append(f"| {e['unit']} | {e['r']} | {e['L']} | {e['n_realised']} | {f(sc['base'], 3)} | "
                         f"{f(sc['assoc'], 3)} | {f(sc['prox'], 3)} |")
            ba, bp = a2["base_minus_assoc"], a2["base_minus_prox"]
            L.append(f"\nMean base - association = {f(ba['mean'], 3)} nats (exact Wilcoxon two-sided p = "
                     f"{f(ba.get('p_two_sided'), 3)}); base - proximity = {f(bp['mean'], 3)} nats (p = "
                     f"{f(bp.get('p_two_sided'), 3)}).")
    ac = read_json(RESULTS / "assoc_corrected.json")
    a2c = read_json(RESULTS / "a2_assoc_corrected.json")
    L.append("\n### POST HOC: association rival with the corrected mapping (deviation D-assoc-mapping)\n")
    L.append("The committed association counts are 0 for every unit (every answer restates the default named in the "
             "question and the committed mapping took the earliest mention). Corrected mapping = earliest non-default "
             "mention, on the same pre-commitment answers:\n")
    L.append("| Unit | Association top-1 | Base r_u | Corrected counts |")
    L.append("|---|---|---|---|")
    for u, v in ac["units"].items():
        L.append(f"| {u} | {v['association_top1']} | {v['base_r']} | {v['corrected_counts']} |")
    L.append(f"\nA2 with the corrected association: base hits {a2c['hits']}/{a2c['n_events']}, association top-1 hits "
             f"{a2c['association_top1_hits']}/{a2c['n_events']}; log scores (base / association / proximity): " +
             "; ".join(f"{e['unit']} {f(e['log_scores']['base'], 3)} / {f(e['log_scores']['assoc'], 3)} / "
                       f"{f(e['log_scores']['prox'], 3)}" for e in a2c["events"]) +
             f"; mean base - association = {f(a2c['base_minus_assoc']['mean'], 3)} nats (exact Wilcoxon p = "
             f"{f(a2c['base_minus_assoc'].get('p_two_sided'), 3)}).")
    hs = read_json(RESULTS / "half_screen.json")["primary"]
    if hs.get("all"):
        a, e = hs["all"], hs["existing_only"]
        L.append("\n### 'Half + screen' (descriptive; Step 1's committed beta for the 15 existing tasks)\n")
        L.append(f"- Step 1 file hash verified against its commitments.log: {hs['step1_sha256_in_its_commitments_log']}.")
        L.append(f"- All {a['n_units']} units (6 new + 15 existing): rho(beta, E) = {f(a['rho_beta_E'], 3)}, one-sided "
                 f"permutation p = {f(a['perm_p_one_sided'], 4)}; collapsed immovable {f(a['collapsed_immovable'])} "
                 f"(n = {a['n_collapsed']}), diverse immovable {f(a['diverse_immovable'])} (n = {a['n_diverse']}).")
        L.append(f"- Existing tasks only (n = {e['n_units']}): rho = {f(e['rho_beta_E'], 3)}, p = "
                 f"{f(e['perm_p_one_sided'], 4)}; diverse immovable {f(e['diverse_immovable'])} (n = {e['n_diverse']}).")
        L.append(f"- Landing checks on escaping existing tasks: "
                 + "; ".join(f"{h['task']}: Step 1 r = {h['step1_r']}, L = {h['landing']} ({'hit' if h['hit'] else 'miss'})"
                             for h in hs["existing_landing_checks"]) + ".")
    xa = read_json(RESULTS / "extra_arm_a.json")
    L.append("\n### Extra arm A: the 15 existing tasks under the ban-free unit\n")
    L.append("| Task | Default | Twin off-default share / pass | E ban-free (a1 / a2) | Landing | Iteration 4 E (a1 / a2) | "
             "Frozen screen E (a1 / a2), movable | Verdict change |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t, v in xa.items():
        L.append(f"| {t} | {v['default']} | {f(v['twin']['share'])} / {f(v['twin']['pass'])} | {f(v['E'], 3)} "
                 f"({f(v['E1'], 3)} / {f(v['E2'], 3)}) | {v['landing']} | {f(v['iter4_E1_E2'][0])} / "
                 f"{f(v['iter4_E1_E2'][1])} | {f(v['screen_E1'])} / {f(v['screen_E2'])}, {v['screen_movable']} | "
                 f"{v['verdict_change']} |")
    ec = read_json(RESULTS / "engine_check.json")
    L.append(f"\n### Engine check (bf16 vs the screen's FP8 rows): {ec['verdict']}\n")
    L.append("| Cell | Per-slot label agreement | JSD | Null p95 | This run | Screen |")
    L.append("|---|---|---|---|---|---|")
    for k, v in ec["cells"].items():
        L.append(f"| {k} | {f(v['per_slot_label_agreement'])} | {f(v['JSD'], 4)} | {f(v['null_p95'], 4)} | "
                 f"{v['this_run_composition']} | {v['screen_composition']} |")
    nov = read_json(RESULTS / "novelty_audit.json")
    L.append(f"\n### Novelty audit\n\n{nov['n_correct_other']} correct 'other' programs among {nov['n_correct_programs_total']} "
             f"correct programs; classes {nov['class_counts']}; statement: {nov['statement']}"
             + (f" (rule-of-three 95% upper bound {nov['rule_of_three_upper95_per_correct_program']:.5f} per correct "
                f"program)." if nov.get("rule_of_three_upper95_per_correct_program") else "."))
    xr = read_json(RESULTS / "external_reference_check.json")
    L.append(f"\n### External cross-check (dependency thealgorithms_python, MIT; descriptive)\n")
    L.append(f"{xr['n_passed_tests']}/{xr['n']} independent implementations pass the frozen hidden tests; runtime label = "
             f"intended mode {xr['n_runtime_match']}/{xr['n']}, AST {xr['n_ast_match']}/{xr['n']}.\n")
    L.append("| Unit | Implementation | Intended | Tests | Runtime | AST |")
    L.append("|---|---|---|---|---|---|")
    for o in xr["items"]:
        L.append(f"| {o['unit']} | {o['path'].split(':')[-1]} | {o['intended_mode']} | "
                 f"{o['n_pass']}/{o['n_cases']}{' (load error)' if o.get('load_error') else ''} | {o['runtime_label']} | "
                 f"{o['ast_label']} |")
    rc = read_json(RESULTS / "repertoire_check_with_extension.json")
    L.append("\n### Repertoire check (do nudges reach beyond the base repertoire?)\n")
    L.append("| Unit | base Hill-1 (depth) | PN a1 | PN a2 | escape cells | correct off-default push programs outside the "
             "base repertoire |")
    L.append("|---|---|---|---|---|---|")
    for u, v in rc.items():
        L.append(f"| {u} | {f(v['base_hill1']['hill1'])} ({v['base_hill1']['depth']}) | {f(v['PN_a1_hill1']['hill1'])} | "
                 f"{f(v['PN_a2_hill1']['hill1'])} | {f(v['ESC_hill1']['hill1'])} | {v['n_outside']} |")
    kr = read_json(RESULTS / "knob_rows_with_extension.json")
    L.append("\n### Knob rows (pass rate / off-default share / correct-only Hill-1 at depth 25)\n")
    arms = ["TWIN", "PN_a1", "PN_a2", "T1.3", "NOVELTY", "BASE", "PLAINC"]
    L.append("| Unit | " + " | ".join(arms) + " |")
    L.append("|---|" + "---|" * len(arms))
    for u, v in kr.items():
        L.append(f"| {u} | " + " | ".join(
            (f"{f(v[a]['pass'])} / {f(v[a]['off_default_share'])} / {f(v[a]['hill1_correct'])}" if a in v else "–")
            for a in arms) + " |")
    sens = read_json(RESULTS / "sensitivities.json")
    L.append("\n### Pre-specified sensitivities (descriptive)\n")
    for k in ("primary", "with_extension"):
        v = sens[k]
        L.append(f"- {k}: " + "; ".join(f"rho({m}, E) = {f(v[m]['rho_E'], 3)} (p = {f(v[m]['perm_p_one_sided'], 3)}, "
                                         f"n = {v[m]['n']})" for m in ("beta_plain", "beta_other", "base_hill1") if m in v))
    rd = json.loads((ROOT / "audit" / "rederive_report.json").read_text())
    L.append(f"\n### Audit\n\n- Independent stdlib re-derivation (audit/rederive.py): {rd['n_mismatches']} mismatches.")
    L.append("- Placebo 1 (beta shuffled across units): mean rho over all permutations = "
             f"{f(rd['primary']['mean_rho_over_all_permutations'], 3)}.")
    pl = rd["placebo_label_shuffle"]
    L.append("- Placebo 2 (labels shuffled between twin and escape rows, 20 shuffles): " +
             "; ".join(f"{u} observed E {f(v['observed_E'], 3)} vs placebo mean {f(v['placebo_mean_E'], 3)}"
                       for u, v in pl.items()) + ".")
    gc = read_json(RESULTS / "guard_check.json")
    L.append(f"- Every unit's commitment precedes its first push row: {gc['all_commitments_precede_pushes']}.")
    cst = read_json(RESULTS / "costs.json")
    tm = read_json(RESULTS / "timing_summary.json")
    L.append(f"- OpenRouter spend: USD {cst['total_usd']:.3f} (cap 2.00). GPU batch time: {tm['gpu_hours']:.2f} h over "
             f"{tm['total_rows']} sampled rows; {tm['n_switches']} model loads.")
    dv = read_jsonl(RESULTS / "deviations.jsonl")
    L.append("\n### Deviations\n")
    for d in dv:
        L.append(f"- **{d['id']}**: {d['deviation']}")
    (RESULTS / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L)[:6000])


if __name__ == "__main__":
    main()
