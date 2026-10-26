#!/usr/bin/env python3
"""Builds results/summary.md (markdown tables for the README) from the results/*.json files."""

from __future__ import annotations

import math
from typing import Any

from config import LOGS, MODES, RESULTS, TASKS, read_json, read_jsonl


def f(x: Any, d: int = 2) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(v):
        return "n/a"
    return f"{v:.{d}f}"


def ci(c: Any, d: int = 2) -> str:
    if not c:
        return "n/a"
    return f"[{f(c[0], d)}, {f(c[1], d)}]"


def load(name: str) -> Any:
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def main() -> None:
    out: list[str] = []
    rc = load("labeller_recheck.json")
    yl = load("yields.json")
    gate = load("gate.json")
    c1 = load("c1.json")
    sens = load("sensitivity.json")
    sec = load("secondary.json")
    cov = load("coverage.json")
    ess = load("ess_table.json")
    tp = read_json(LOGS / "throughput.json")
    qf = read_json(LOGS / "queue_final.json") if (LOGS / "queue_final.json").exists() else {}
    units = read_jsonl(RESULTS.parent / "scores" / "units_done.jsonl")
    if rc:
        out.append("### Labeller re-check (`results/labeller_recheck.json`)\n")
        out.append(f"Combined label vs adjudicated gold: **{f(rc['gold_all']['combined_vs_adjudicated'], 3)}** "
                   f"(n={rc['gold_all']['n']}; evaluation split {f(rc['gold_eval']['combined_vs_adjudicated'], 3)}, "
                   f"exp1 reported 0.966); references {rc['references']['combined_correct']}/{rc['references']['n']}"
                   f" (runtime {rc['references']['runtime_correct']}, AST {rc['references']['ast_correct']}).\n")
    if yl:
        out.append("### Forced programs (`results/yields.json`, `data/forced_selected.jsonl`)\n")
        out.append("| task | algorithm | family | attempts | labelled j | yield y_j | verified after scrub | scrub mode |")
        out.append("|---|---|---|---|---|---|---|---|")
        for k, v in yl["yields"].items():
            fam = v["family"]
            out.append(f"| {k.split('|')[0]} | {k.split('|')[1]} | {fam} | {v['attempts_' + fam]} | "
                       f"{v['labelled_' + fam]} | {f(v['yield'])} | {v.get('n_scrub_verified', 'n/a')} | "
                       f"{v.get('scrub_mode', 'n/a')} |")
        out.append(f"\nScored programs per algorithm: M = {tp['M']} (cut rule; halves of {int(tp['M']) // 2}); "
                   f"bidirectional Dijkstra has 11.\n")
    if gate:
        p = gate["primary"]
        out.append("### FRLP validity gate (`results/gate.json`)\n")
        out.append(f"Verdict: **{gate['verdict']}**. (a) calibration: mean S = {f(p['a']['mean_S'])} "
                   f"(target [0.3, 3]), mean default-mode share m = {f(p['a']['mean_m_default'])} (target >= 0.9) -> "
                   f"{'PASS' if p['a']['pass'] else 'FAIL'}; (b) mean d_e = {f(p['b']['mean_d_e'])} nats over uniform "
                   f"(target >= 0.3) -> {'PASS' if p['b']['pass'] else 'FAIL'}; (c) argmax hits "
                   f"{p['c']['hits']}/{p['c']['n_clear']} clear-mode events = {f(p['c']['rate'])} (target >= 0.8) -> "
                   f"{'PASS' if p['c']['pass'] else 'FAIL'}. Pooled Spearman implied vs realised "
                   f"{f(p['pooled_spearman_implied_vs_realised'])}; {p['ess_cells']['n_below_5']}/{p['ess_cells']['n']}"
                   f" gate cells have ESS < 5.\n")
        out.append("| event | realised mode (allowed) | FRLP argmax | hit | d_e (nats) | implied shares > 0.01 |")
        out.append("|---|---|---|---|---|---|")
        for e in p["events"]:
            imp = ", ".join(f"{k} {v:.2f}" for k, v in sorted(e["implied_mean"].items(), key=lambda kv: -kv[1])
                            if v > 0.01)
            out.append(f"| {e['event_id']} | {e['realised_mode']} | {e['argmax']} | {f(e['hit'])} | {f(e['d_e'])} | "
                       f"{imp} |")
        out.append("\nGate (a) per baseline paraphrase: " + "; ".join(
            f"{t} p{r['paraphrase_id']}: S={f(r['S'])}, m={f(r['m_default'])}" for t in TASKS
            for r in p["gate_a"].get(t, [])) + "\n")
        out.append("Sensitivity variants (descriptive; the primary verdict is not re-chosen):\n")
        out.append("| variant | mean S | mean m | (a) | mean d_e | (b) | argmax rate | (c) | all |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for v, s in gate["sensitivity"].items():
            out.append(f"| {v} | {f(s['a']['mean_S'])} | {f(s['a']['mean_m_default'])} | {f(s['a']['pass'])} | "
                       f"{f(s['b']['mean_d_e'])} | {f(s['b']['pass'])} | {f(s['c']['rate'])} | {f(s['c']['pass'])} | "
                       f"{f(s['pass'])} |")
        out.append("")
    if c1:
        out.append("### C1 output-space share test (`results/c1.json`)\n")
        out.append(f"Status: **{c1['frlp_status']}**; two tasks, one model, so every branch label is descriptive.\n")
        out.append("| reference | scope | rows | V_u (ladder) | V_s (X-specific) | SHARE point | SHARE 95% CI | "
                   "V_u+V_s 95% CI | F | branch |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for key, lab in (("primary_neutral", "neutral twin (primary)"), ("reference_mention", "mention twin"),
                         ("ess_weighted", "ESS-weighted")):
            R = c1[key]
            for scope in TASKS + ("pooled",):
                blk = R["pooled"] if scope == "pooled" else R["tasks"][scope]
                sp = blk["share_point"]
                bs = blk.get("bootstrap", {})
                out.append(f"| {lab} | {scope} | {sp['n_rows']} | {f(sp['V_u'])} | {f(sp['V_s'])} | "
                           f"{f(sp['SHARE'])} | {ci(bs.get('SHARE_ci'))} | {ci(bs.get('V_tot_ci'))} | {f(sp['F'])} | "
                           f"{blk.get('branch', 'n/a')} |")
        P = c1["primary_neutral"]
        ap = P.get("aim_prime_veto", {})
        aa = P.get("aim_association", {})
        out.append(f"\nRobust (same pooled branch under both references and the ESS-weighted variant): "
                   f"**{f(c1['robust_pooled'])}**. AIM (prime-and-veto, disjoint halves and nouns): "
                   f"{f(ap.get('aim'))} (null 95th pct {f(ap.get('null_p95'))}, p = {f(ap.get('p'), 3)}, "
                   f"{ap.get('n_rows')} rows); association aim {f(aa.get('aim'))} (null 95th pct "
                   f"{f(aa.get('null_p95'))}, p = {f(aa.get('p'), 3)}).\n")
        out.append("| task | ladder exists (mean centred cos >= 0.5) | mean centred cos | mean raw cos | "
                   "RAND A vs B r | NONCE h1 vs h2 r | aim | aim p |")
        out.append("|---|---|---|---|---|---|---|---|")
        for t in TASKS:
            T = P["tasks"][t]
            le = T.get("ladder_exists", {})
            ur = T.get("u_reliability", {})
            out.append(f"| {t} | {f(le.get('exists'))} | {f(le.get('mean_pairwise_centred_cosine'))} | "
                       f"{f(le.get('mean_pairwise_raw_cosine'))} | {f(ur.get('rand_A_vs_B_pearson'))} | "
                       f"{f(ur.get('nonce_h1_vs_h2_pearson'))} | {f(T.get('aim'))} | {f(T.get('aim_p'), 3)} |")
        out.append("\nPer-row decomposition (primary reference):\n")
        out.append("| task | ban B | a_B^2 | N_u | ||s_B||^2 | N_s | cos(Gbar, u) | replicate SD | between-survivor SD |"
                   " D_B (own-label subtraction) | rho(s, PV) | top residual |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for t in TASKS:
            T = P["tasks"][t]
            for B, r in T["rows"].items():
                ex = T.get("extras", {}).get(B, {})
                top = max(r["s"], key=r["s"].get) if r["s"] else "n/a"
                out.append(f"| {t} | {B} | {f(r['a2'])} | {f(r['N_u'])} | {f(r['ss_s'])} | {f(r['N_s'])} | "
                           f"{f(r['cos_with_u'])} | {f(r['replicate_sd'])} | {f(r['between_survivor_sd'])} | "
                           f"{f(ex.get('subtraction_strength_D'))} | {f(r['rho_pv'])} | {top} |")
        so = c1["primary_neutral"].get("sham_observations_7_1", {})
        if so:
            out.append("\nIteration-1 sham observations under FRLP (7.1):\n")
            for k, v in so.items():
                if v:
                    out.append(f"- {k}: s = {f(v['s_j'])} {ci(v['s_j_ci'])}, largest residual: {f(v['is_largest_residual'])}"
                               f" (bootstrap prob {f(v['boot_prob_largest'])}), Gbar = {f(v['G_j'])} vs fitted ladder "
                               f"{f(v['fitted_ladder_j'])}")
            out.append("")
    if sens:
        out.append("### Sensitivity (`results/sensitivity.json`)\n")
        out.append("| variant | pooled SHARE point | pooled SHARE CI | pooled branch | aim |")
        out.append("|---|---|---|---|---|")
        for k, v in sens.items():
            if "error" in v:
                out.append(f"| {k} | error | {v['error'][:60]} | | |")
                continue
            out.append(f"| {k} | {f(v['pooled_share_point']['SHARE'])} | "
                       f"{ci((v.get('pooled_bootstrap') or {}).get('SHARE_ci'))} | {v.get('pooled_branch')} | "
                       f"{f((v.get('aim_prime_veto') or {}).get('aim'))} |")
        out.append("")
    if sec:
        out.append("### Secondary (`results/secondary.json`)\n")
        for t, v in sec.get("two_step", {}).items():
            out.append(f"- Two-step ban {t} (frozen templates): implied banned mass {f(v['implied_banned_mass_frozen_templates'])}; "
                       f"landing " + ", ".join(f"{k} {f(x)}" for k, x in v["implied_landing_frozen_templates"].items()))
        if gate:
            for k, v in gate.get("succession_step2", {}).items():
                out.append(f"- exp1 step-2 prompts {k}: implied banned mass {f(v['implied_banned_mass'])} vs exp1 banned "
                           f"share {f(v['exp1_banned_share'])}; implied landing {v['implied_landing']}")
        for k, v in sec.get("shams", {}).items():
            out.append(f"- Sham {k}: " + ("not scored (Q8 dropped)" if not v.get("scored") else
                                          f"residual order {v['residual_rank_order']}, declared neighbours "
                                          f"{v['declared_neighbours']} top-k: {f(v['neighbours_top_k'])}"))
        out.append("")
    if cov:
        out.append("### Coverage of natural programs by forced programs (`results/coverage.json`)\n")
        out.append("| task|algorithm | natural programs | share with NN Jaccard >= 0.5 | mean NN Jaccard |")
        out.append("|---|---|---|---|")
        for k, v in cov.items():
            if v["n_natural"]:
                out.append(f"| {k} | {v['n_natural']} | {f(v['share_nn_jaccard_ge_0.5'])} | {f(v['mean_nn_jaccard'])} |")
        out.append("")
    if ess:
        out.append("### ESS per condition family (`results/ess_table.json`)\n")
        out.append("| task|family | half-cells | median ESS | share < 5 |")
        out.append("|---|---|---|---|")
        for k, v in ess.items():
            out.append(f"| {k} | {v['n_cells']} | {f(v['median_ess'])} | {f(v['frac_below_5'])} |")
        out.append("")
    qs: dict[str, int] = {}
    for u in units:
        qs[u["queue"]] = qs.get(u["queue"], 0) + 1
    out.append(f"Scored units by queue: {qs}; skipped after the GPU cutoff: "
               f"{len(qf.get('skipped_after_deadline', []))} units.\n")
    (RESULTS / "summary.md").write_text("\n".join(out))
    print("\n".join(out)[:3000])


if __name__ == "__main__":
    main()
