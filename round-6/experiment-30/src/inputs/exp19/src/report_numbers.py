#!/usr/bin/env python3
"""Markdown summary of the headline numbers (results/summary.md), generated from the result files only, so the
README's numbers cannot drift from the analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import AUDIT_DIR, DEFAULT, PRED_DIR, RESULTS_DIR, read_json, read_jsonl

E6 = ("T03", "T05", "T06", "T10", "T1", "T2")


def f(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, str):
        return x
    return f"{x:.{nd}f}"


def ci(c, nd=2):
    if not c or c[0] is None:
        return "–"
    return f"[{c[0]:.{nd}f}, {c[1]:.{nd}f}]"


def main() -> None:
    c1 = read_json(RESULTS_DIR / "c1.json")
    pr = read_json(RESULTS_DIR / "prices.json")
    p = c1["primary"]
    L = []
    L.append(f"**C1 (pre-registered rule): {p['verdict']}**"
             + (f" (failed: {', '.join(p['failed_thresholds'])})" if p["failed_thresholds"] else "") + ".")
    L.append(f"count1 = #{{t: H5_PN >= 1.5}} = {p['count1']}/6; count2 = #{{t: H5_PN > H5_best}} = {p['count2']}/6; "
             f"best NA knob beats PN on {p['n_tasks_best_beats_PN']} tasks; D_bar = {f(p['D_bar'], 3)} "
             f"(task bootstrap 95% CI {ci(p['D_bar_ci95'], 3)}, one-sided p_C1 = {f(p['p_C1_one_sided'], 4)}); "
             f"exact sign test over the 6 D_t: p = {f(p['sign_test_p_one_sided'], 4)}.")
    L.append("")
    L.append("| Task (default) | H5 PN | best NA knob | H5 best NA | D_t [95% CI] | P(H5_PN > H5_best) | P15 PN | P20 PN |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in E6:
        d = p["per_task"].get(t, {})
        pn = pr.get(t, {}).get("PN", {})
        L.append(f"| {t} ({DEFAULT[t]}) | {f(d.get('H5_PN'))} | {d.get('best_na') or '–'} | {f(d.get('H5_best'))} | "
                 f"{f(d.get('D_t'))} {ci(d.get('D_t_boot_ci95'))} | {f(d.get('P_boot_PN_gt_best'))} | "
                 f"{f(pn.get('P15'), 1)} | {f(pn.get('P20'), 1)} |")
    L.append("")
    L.append("H5 per knob class on E6 (randomisation hull, cost <= 5 points; 95% bootstrap CI in results/c1.json "
             "`class_ci`):")
    L.append("")
    cls = ["PN", "TEMP", "TOPK10", "NONCE", "NOVELTY", "SEMSEED", "VETO_1SHOT", "VETO_PERSIST", "VETO_ITER", "MINP", "VS"]
    L.append("| Task | " + " | ".join(cls) + " |")
    L.append("|---|" + "---|" * len(cls))
    for t in E6:
        L.append(f"| {t} | " + " | ".join(f(pr.get(t, {}).get(c, {}).get("H5")) for c in cls) + " |")
    L.append("")
    L.append("Sensitivities (each re-evaluates the full rule):")
    L.append("")
    L.append("| Sensitivity | verdict | count1 | count2 | D_bar [95% CI] |")
    L.append("|---|---|---|---|---|")
    for k, v in c1.items():
        if k in ("primary", "utc", "rule", "class_ci") or not isinstance(v, dict) or "verdict" not in v:
            continue
        L.append(f"| {k} | {v['verdict']} | {v['count1']} | {v['count2']} | {f(v['D_bar'], 3)} "
                 f"{ci(v['D_bar_ci95'], 3)} |")
    ec = read_json(RESULTS_DIR / "engine_check.json")
    L.append("")
    L.append(f"Engine check: **{ec['verdict']}** — per-slot label agreement " + ", ".join(
        f"{k} {v['per_slot_label_agreement']:.2f}" for k, v in ec["cells"].items()) + ".")
    na = AUDIT_DIR / "novelty_audit.json"
    if na.exists():
        a = read_json(na)
        recs = a.get("records", [])
        both = [(r["judge_A"]["class"], r["judge_B"]["class"]) for r in recs
                if r["judge_A"].get("class") and r["judge_B"].get("class")]
        agree = sum(x == y for x, y in both)
        L.append(f"Novelty audit: {a['n_unique_correct_other']} unique correct 'other' programs, classes "
                 f"{a['class_counts']}; confirmed NOVEL = {a['n_confirmed_novel']}; judges A/B agree on {agree}/"
                 f"{len(both)} (Cohen's kappa {f(a['kappa_A_B'])} is uninformative when one class dominates); "
                 f"controls {a['controls_correct_final']}/{len(a['controls'])}; complete = {a['complete']}.")
    lv = AUDIT_DIR / "label_validity.json"
    if lv.exists():
        a = read_json(lv)
        L.append("Label-validity audit (judge vs labeller agreement): " + ", ".join(
            f"{k} {f(v['agreement'])} (n {v['n_judged']})" for k, v in a["per_task_group"].items()) + ".")
    nmp = RESULTS_DIR / "nonmovable.json"
    if nmp.exists():
        nm = read_json(nmp)
        e = nm["E6_H5_PN"]
        L.append("")
        L.append(f"R2 (held out) and the 8 non-movable bench tasks (E6 H5_PN for comparison: min {f(e['min'])}, median "
                 f"{f(e['median'])}, max {f(e['max'])}):")
        L.append("")
        L.append("| Task | PN off-default excess (alpha <= 2) | H5 PN | H5 TEMP | H5 NONCE | H5 NOVELTY | P15 PN |")
        L.append("|---|---|---|---|---|---|---|")
        for t, v in nm["tasks"].items():
            h = v["H5"]
            L.append(f"| {t}{' (held out)' if v.get('held_out') else ''} | {f(v['PN_alpha_le2_off_default_excess'])} | "
                     f"{f(h.get('PN'))} | {f(h.get('TEMP'))} | {f(h.get('NONCE'))} | {f(h.get('NOVELTY'))} | "
                     f"{f(v['P15'].get('PN'), 1)} |")
    rd = RESULTS_DIR / "rederive.json"
    if rd.exists():
        r = read_json(rd)
        L.append("")
        L.append(f"Independent re-derivation: {r['n_checks'] - r['n_mismatches']}/{r['n_checks']} checks match; "
                 f"arm-shuffle placebo fires {r['placebos']['arm_label_shuffle']['n_counts_rule_fires']}/"
                 f"{r['placebos']['arm_label_shuffle']['n_shuffles']}; PN-replaced-by-TWIN placebo D_t <= 0: "
                 f"{r['placebos']['pn_replaced_by_twin']['pass']}; hash chain breaks {r['hash_chain']['breaks']}, "
                 f"commit precedes stage 1: {r['hash_chain']['commit_precedes_stage1']}.")
    ts = RESULTS_DIR / "timing_summary.json"
    if ts.exists():
        t_ = read_json(ts)
        L.append(f"GPU: {t_['rows_generated']} rows in {t_['n_batches']} batches, {t_['gpu_seconds_total'] / 3600:.2f} "
                 f"GPU-hours of batch time; {t_['cap_hit_rows']} rows hit the 1,024-token cap.")
    cs = RESULTS_DIR / "costs.json"
    if cs.exists():
        L.append(f"OpenRouter spend: USD {read_json(cs)['total_usd']:.3f} (cap 1.00).")
    (RESULTS_DIR / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
