#!/usr/bin/env python3
"""results/summary.md: every table of the README, generated from results/*.json and the commits (no hand-typed
numbers)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import PRED_DIR, RESULTS_DIR, TASKS15, read_json, read_jsonl  # noqa: E402


def f(x: Any, nd: int = 2) -> str:
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def pval(p: Any) -> str:
    if p is None:
        return "–"
    return f"{p:.2g}" if p >= 1e-3 else f"{p:.1e}"


def main() -> None:
    c1 = read_json(PRED_DIR / "commit1.json")
    c2 = read_json(PRED_DIR / "commit2.json")
    sel = read_json(RESULTS_DIR / "selection.json")
    cf = read_json(RESULTS_DIR / "confirmation.json")
    ds = read_json(RESULTS_DIR / "desharpen.json")
    rv = read_json(RESULTS_DIR / "reverse.json")
    sc = read_json(RESULTS_DIR / "screen_check.json")
    ec = read_json(RESULTS_DIR / "engine_check.json")
    dn = read_json(RESULTS_DIR / "d_norms.json")
    tm = read_json(RESULTS_DIR / "timing.json")
    co = read_json(RESULTS_DIR / "costs.json")
    nv = read_json(RESULTS_DIR / "novelty_audit.json") if (RESULTS_DIR / "novelty_audit.json").exists() else None
    geo = read_json(RESULTS_DIR / "geometry.json") if (RESULTS_DIR / "geometry.json").exists() else None
    rd = read_json(RESULTS_DIR / "rederive.json") if (RESULTS_DIR / "rederive.json").exists() else None
    L: list[str] = []
    per = c1["per_task"]
    L.append("### Base repertoire and strata (COMMIT #1)\n")
    L.append("| Task | instruct default (twin S1 share) | base correct / N | beta_t [95% CI] (basis) | stratum (stability) "
             "| r_t | beta plain | base Hill-1 (d25) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in TASKS15:
        p = per[t]
        L.append(f"| {t} | {p['default']} ({f(p['twin_default_share'])}) | {p['n_correct_base']}/{p['base_chat']['n']} "
                 f"| {f(p['beta'])} [{f(p['beta_ci'][0])}, {f(p['beta_ci'][1])}] ({p['beta_basis']}) | "
                 f"{p['stratum']} ({f(p['stratum_stability'])}) | {p['r_t']} | {f(p['base_plain']['beta_plain'])} | "
                 f"{f(p['base_hill1_rarefied']['hill1'])} |")
    L.append("")
    L.append("### Stage 3 selection on S1 (pass / correct off-default share; N = 50 for T, 30 for MR and READ)\n")
    L.append("| Task | stratum | twin | T(0.25) | T(0.5) | T(1) | MR(0.25) | MR(0.5) | MR(1) | READ(1) | EARLY(1) | "
             "LATE(1) | lambda* |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in TASKS15:
        r = sel["per_task"][t]

        def c(a):
            x = r.get(a)
            return "–" if not x else f"{f(x['pass'])} / {f(x['off_share'])}"
        L.append(f"| {t} | {r['stratum']} | {c('twin_S1')} | {c('T0.25')} | {c('T0.5')} | {c('T1.0')} | {c('MR0.25')} | "
                 f"{c('MR0.5')} | {c('MR1.0')} | {c('READ1.0')} | {c('EARLY1.0')} | {c('LATE1.0')} | "
                 f"{f(r.get('lambda_star'))} |")
    L.append("")
    L.append("### Stage 4 confirmation on fresh S2 slots (N = 50 per cell; one-sided exact McNemar on y, Holm)\n")
    L.append("| Task | lambda* | twin S2 pass | T: pass / off-share / modal | control: pass / off-share | "
             "McNemar b:c, p (Holm) | templates T > control |")
    L.append("|---|---|---|---|---|---|---|")
    for t, r in cf["per_task"].items():
        arms = list(r["arms"])
        T = r["arms"][arms[0]]
        for a in arms[1:]:
            x = r["arms"][a]
            m = x.get("mcnemar_T_vs_this", {})
            h = r.get("holm", {}).get(x.get("control_class"))
            L.append(f"| {t}{'' if r['decisive'] else ' (desc.)'} | {f(r['lambda_star'])} | {f(r['twin_S2']['pass'])} | "
                     f"{f(T['pass'])} / {f(T['off_share'])} / {T['modal_correct_nondefault']} | {a}: {f(x['pass'])} / "
                     f"{f(x['off_share'])} | {m.get('b')}:{m.get('c')}, {pval(m.get('p_one'))} ({pval(h)}) | "
                     f"{x.get('template_robustness', {}).get('n_templates_arm_gt_control')}/5 |")
    L.append("")
    v = cf["verdict"]
    L.append(f"**Claim B (frozen rule): {v['verdict']}** -- PASS on {v.get('n_pass')}/{v.get('n_decisive')} decisive "
             f"tasks (needed {v.get('needed')}); (iii) fails on {v.get('n_iii_fail')}; specificity (point estimates) "
             f"{f(sel['specificity']['holds'])}, noise-robust {f(sel['specificity']['holds_noise_robust'])}.\n")
    for t, r in cf["per_task"].items():
        if r.get("rule"):
            ru = r["rule"]
            L.append(f"- {t}: (i) pass {f(ru['i_pass'])}, (ii) share >= 0.5 beta {f(ru['ii_share'])}, (iii) controls "
                     f"{f(ru['iii_controls'])}, (iv) lands on r_t {f(ru['iv_landing'])} -> PASS {f(ru['PASS'])}")
    if "power_extension_N100" in cf:
        px = cf["power_extension_N100"]
        L.append(f"\nPower extension (COMMIT3_EXT, outcome-blind, descriptive; N = 100 per decisive cell): "
                 f"**{px['verdict']['verdict']}** (PASS {px['verdict'].get('n_pass')}/{px['verdict'].get('n_decisive')}).")
        for t, r in px["per_task"].items():
            arms = list(r["arms"])
            T = r["arms"][arms[0]]
            bits = []
            for a in arms[1:]:
                m = r["arms"][a].get("mcnemar_T_vs_this", {})
                bits.append(f"vs {a} {m.get('b')}:{m.get('c')} p={pval(m.get('p_one'))}")
            L.append(f"- {t}: T pass {f(T['pass'])}, off-share {f(T['off_share'])}; " + "; ".join(bits))
    L.append("")
    L.append("Sensitivities: " + "; ".join(f"{k}: {v['verdict'] if isinstance(v, dict) and 'verdict' in v else v}"
                                         for k, v in cf["sensitivities"].items()
                                         if k in ("stable_stratum_only", "noise_robust_specificity",
                                                  "power_extension_N100_verdict")))
    L.append("")
    L.append("### Claim D (de-sharpening push along unit(D) vs isotropic, ban-free units, N = 30)\n")
    L.append("| Task | twin pass | DS 0.5 / 1 / 2 (pass, off-share) | ISO 0.5 / 1 / 2 (pass, off-share) | a_DS | a_ISO |")
    L.append("|---|---|---|---|---|---|")
    for t, r in ds["per_task"].items():
        cc = r["cells"]

        def s3(k):
            return " ; ".join(f"{f(cc[f'{k}{a}']['pass'])}, {f(cc[f'{k}{a}']['off_share'])}"
                              for a in (0.5, 1.0, 2.0) if f"{k}{a}" in cc)
        L.append(f"| {t} | {f(r['twin']['pass'])} | {s3('DS')} | {s3('ISO')} | {f(r['a_ds'])} | "
                 f"{f(r['a_iso']) if r['a_iso'] is not None else '>2 (censored)'} |")
    L.append(f"\n**Claim D: {ds['verdict']['verdict']}** (PASS {ds['verdict'].get('n_pass')}/{ds['verdict'].get('n_tasks')}).\n")
    L.append("### Reverse interchange (instruct task-spec states into the base model, blocks 12-23, N = 50)\n")
    L.append("| Task | BTWIN default share (correct / attempts) | RT(1) | BMR(1) | predicted min rise | met |")
    L.append("|---|---|---|---|---|---|")
    for t, r in rv["per_task"].items():
        def ds2(a):
            x = r.get(a)
            return "–" if not x else f"{f(x['default_share'])} / {f(x['default_share_attempts'])} (n_correct {x['n_correct']})"
        pc = r.get("prediction_correct") or {}
        L.append(f"| {t} | {ds2('BTWIN')} | {ds2('RT1.0')} | {ds2('BMR1.0')} | {f(pc.get('predicted_min_rise'))} | "
                 f"{f(pc.get('met'))} |")
    L.append("")
    L.append("### Claim A screen check (descriptive; iteration-4 escape fractions)\n")
    for k in ("alpha_1.0", "alpha_2.0", "alpha_mean"):
        L.append(f"- beta_t vs E_t ({k}): Spearman {f(sc[k]['spearman'])}, Kendall {f(sc[k]['kendall'])}, "
                 f"one-sided permutation p {pval(sc[k]['perm_p_one_sided'])} (n = {len(sc['tasks'])})")
    agree = sum(v["agree"] for v in sc["r_t_vs_push_landing"].values())
    L.append(f"- r_t equals the iteration-4 push top-1 landing on {agree}/{len(sc['r_t_vs_push_landing'])} movable tasks")
    L.append("")
    L.append("### Size of D = h_base - h_instruct\n")
    L.append(f"- relative norm at S, blocks 12-23 (mean over tasks): "
             f"{', '.join(f(x) for x in dn['mean_rel_norm_S'][12:24])}")
    L.append(f"- relative norm at R, blocks 12-23: {', '.join(f(x) for x in dn['mean_rel_norm_R'][12:24])}")
    br = {k: sum(v['breakage_share_gt4_banfree'][k] for v in dn['per_task'].values()) / len(dn['per_task'])
          for k in ("0.25", "0.5", "1.0")}
    L.append(f"- share of hooked (l, p) above 4 ban-free units: lambda 0.25 {f(br['0.25'])}, 0.5 {f(br['0.5'])}, "
             f"1 {f(br['1.0'])}")
    L.append(f"- cross-task cosine of the per-task mean D (blocks 12/18/23/27): " + ", ".join(
        f"{l}: {f(v['mean_offdiag'])}" for l, v in dn["cross_task_cosine_Dbar"].items()))
    L.append("")
    L.append("### Engine check (bf16 here vs the FP8 exp17 screen rows)\n")
    for k, v in ec.items():
        if isinstance(v, dict):
            L.append(f"- {k}: per-slot label agreement {f(v['per_slot_label_agreement'])}, JS {f(v['js'], 3)} "
                     f"(template-resampling null q95 {f(v['null_q95'], 3)}), within null {f(v['within_null'])}")
    if geo:
        L.append("\n### Geometry (distance of the T(lambda*) centroid; fraction of the instruct->base twin gap)\n")
        for t, g in geo["panels"].items():
            bits = []
            for s in ("S18", "S23", "S27", "R18", "R23"):
                x = g.get(s)
                if x and x.get("T_frac_of_gap_from_instr") is not None:
                    bits.append(f"{s} {f(x['T_frac_of_gap_from_instr'])} (stress-1 {f(x['mds_stress1'])})")
            L.append(f"- {t} (lambda* {g['lambda_star']}): " + "; ".join(bits))
    if nv:
        L.append(f"\n### Novelty audit\n\n{nv['n_unique_correct_noncatalogue_programs']} unique correct non-catalogue "
                 f"programs (every arm, base included). Judge classes (2 of 3 judges): {nv['class_counts']}. Manual "
                 f"adjudication against the nearest known solution: {nv.get('manual_class_counts')}; NOVEL = "
                 f"{nv.get('n_novel_manual')} (rule-of-three 95% upper bound "
                 f"{f(nv.get('rule_of_three_upper_95_manual'), 3)}); the judges' {nv.get('n_judge_novel_overcalls')} "
                 f"NOVEL calls are linear scans, count loops and a threshold binary search (known techniques "
                 f"outside the frozen catalogue).")
    if rd:
        L.append(f"\n### Re-derivation\n\n{rd['n_checks']} checks, {rd['n_mismatches']} mismatches; arm-shuffle placebo "
                 f"rejection {f((rd.get('placebo_arm_shuffle') or {}).get('rejection_rate'), 3)}; label-shuffle "
                 f"placebo share keeping stratum {f(rd['placebo_label_shuffle']['mean_share_tasks_keeping_stratum'])}")
    L.append(f"\n### Compute and spend\n\nHF engine {tm['programs_hf']} programs (+{tm['pad_rows']} pad rows) in "
             f"{f(tm['hf_gpu_seconds'] / 3600)} GPU-h; vLLM base {tm['programs_vllm']} programs in "
             f"{f(tm['vllm_base_seconds'] / 3600)} GPU-h; total {f(tm['gpu_hours_total'])} GPU-h. "
             f"OpenRouter USD {f(co['total_usd'], 3)} (cap {co['cap_usd']}).")
    (RESULTS_DIR / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
