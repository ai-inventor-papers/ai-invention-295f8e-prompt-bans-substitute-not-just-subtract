#!/usr/bin/env python3
"""Headline tables generated from the result files -> results/summary.md (pasted into README.md)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import AUDIT_DIR, PRED_DIR, RESULTS_DIR, read_json  # noqa: E402
from cfg5 import D5, ND10  # noqa: E402


def mx(p: Path):
    try:
        return read_json(p)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def f2(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x))):
        return "–"
    if isinstance(x, float) and math.isinf(x):
        return "not reached"
    return f"{x:.2f}"


def main() -> None:
    L = []
    lc = mx(RESULTS_DIR / "literal_cell.json") or {}
    ct = lc.get("C_T", {})
    nf = lc.get("noise_floor", {})
    pe = lc.get("paired_exp21", {})
    L.append("### Claim F — the literal cell (T2, thinking on, top-k 10, same seed, T ∈ {0.3, 0.7, 1.0, 1.3})\n")
    L.append(f"- **C_T = {ct.get('n_change_final_label')} of {ct.get('n_seeds_all4_completed')} seeds** change their "
             f"final-code algorithm across temperature (Clopper-Pearson one-sided 95% upper bound "
             f"{f2((ct.get('clopper_pearson') or {}).get('upper95_one_sided'))}); the committed prediction C_T ≤ 1 is "
             f"{'met' if ct.get('prediction_met') else 'not met'}.")
    L.append(f"- First approach named in the thinking: {ct.get('n_change_first_approach')} of "
             f"{ct.get('n_seeds_all4_completed')} seeds change.")
    per = lc.get("per_T", {})
    L.append("\n| T | completed | final labels (completed) | first approach | median think tokens | Dijkstra style |")
    L.append("|---|---|---|---|---|---|")
    for k, v in per.items():
        q = v.get("think_tokens_quantiles", {})
        L.append(f"| {k} | {v['completed']}/{v['n']} | {v['final_label_composition']} | {v['first_approach_composition']} | "
                 f"{f2(q.get('0.5') if '0.5' in q else q.get(0.5))} | {v['dijkstra_style']} |")
    L.append(f"\n- Noise floor (T 0.7 vs its repeat, same seed): byte-identical thinking {nf.get('byte_identical_thinking')}"
             f"/{nf.get('n_pairs')}, label agreement {f2(nf.get('label_agreement'))}, median common prefix "
             f"{f2(nf.get('common_prefix_tokens_median'))} tokens.")
    L.append(f"- Paired with exp21's top-p-1 traces at the same (seed, T): label agreement {f2(pe.get('label_agreement'))}"
             f" on {pe.get('n_pairs')} pairs; median common token prefix "
             f"{f2((pe.get('common_prefix_tokens_quantiles') or {}).get('0.5'))} tokens (top-k 10 vs top-k 0 diverge early, "
             "yet the algorithm never changes).")
    la = lc.get("lexicon_audit", {})
    L.append(f"- Lexicon audit: judge agreement {f2(la.get('agreement'))} on {la.get('n_judged')} traces.\n")
    cc = mx(RESULTS_DIR / "claim_c.json") or {}
    pr = mx(RESULTS_DIR / "prices.json") or {}
    if cc:
        p = cc["primary"]
        L.append(f"### Claim C — plan noise vs text-level plan samplers: **{cc['verdict']}** "
                 f"(PN wins {p['wins']} of {p['n_tasks_evaluable']} decisive tasks; threshold {p['threshold']})\n")
        L.append("| Task | H5 PN | H5 IFG | H5 PSL-lite | H5 EAP | H5 BINT | best text | PN wins | P(PN ≥ best) | flag | H5 DMD |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for t in D5:
            v = p["per_task"].get(t, {})
            tx = v.get("text_H5", {})
            pw = cc["p_PN_ge_best_text"].get(t)
            un = "UNRESOLVED" if cc["unresolved"].get(t) else ""
            L.append(f"| {t} | {f2(v.get('H5_PN'))} | {f2(tx.get('IFG'))} | {f2(tx.get('PSL'))} | {f2(tx.get('EAP'))} | "
                     f"{f2(tx.get('BINT'))} | {v.get('best_text_class')} | {'yes' if v.get('PN_wins') else 'no'} | "
                     f"{f2(pw)} | {un} | {f2(pr.get(t, {}).get('DMD', {}).get('H5'))} |")
        L.append(f"\nD̄ = mean(H5_PN − best_text) = {f2(cc.get('D_bar'))}, 95% CI {[f2(x) for x in cc.get('D_bar_ci95', [])]}; "
                 f"replicate win-count distribution {cc.get('replicate_win_count_distribution')} "
                 f"({cc.get('n_replicates')} replicates).\n")
        L.append("| Sensitivity | verdict | wins | D̄ |")
        L.append("|---|---|---|---|")
        for k, v in cc.get("sensitivities", {}).items():
            L.append(f"| {k} | {v.get('verdict')} | {v.get('wins')}/{v.get('n_tasks_evaluable')} | {f2(v.get('D_bar'))} |")
    pvd = mx(RESULTS_DIR / "pn_vs_dmd.json") or {}
    if pvd:
        L.append("\n### PN vs departure-matched decoding (DMD), correct off-default share of N\n")
        L.append("| Task | α | T_dmd | K_PN | f_on | PN | DMD | TWIN | McNemar PN vs DMD (PN-only/DMD-only, p) |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for t in D5:
            for a in ("alpha1", "alpha2"):
                v = pvd["per_task"].get(t, {}).get(a)
                if not v:
                    continue
                m = v["mcnemar_PN_vs_DMD"]
                L.append(f"| {t} | {a[-1]} | {f2(v['T_dmd'])} | {v['K_PN']:.4f} | {v['f_on_DMD']:.4f} | "
                         f"{f2(v['PN_off_default_share'])} | {f2(v['DMD_off_default_share'])} | "
                         f"{f2(v['TWIN_off_default_share'])} | {m['x_only']}/{m['y_only']}, p={m['p_exact']:.3g} |")
        L.append(f"\nPooled exact test over D5: {pvd.get('pooled_D5_exact')}\n")
    pvt = mx(RESULTS_DIR / "plain_vs_twin.json") or {}
    if pvt:
        L.append("### PN plain vs PN twin (same direction, same stream)\n")
        L.append("| Task | PN plain-only / PN twin-only (p) | pass plain | pass twin | Hill plain | Hill twin |")
        L.append("|---|---|---|---|---|---|")
        for t, v in pvt.items():
            x = v.get("PNPLAIN_a1_vs_PN_a1")
            if x:
                m = x["mcnemar"]
                L.append(f"| {t} | {m['x_only']}/{m['y_only']} (p={m['p_exact']:.3g}) | {f2(x['pass_x'])} | {f2(x['pass_y'])} "
                         f"| {f2(x['hill_x'])} | {f2(x['hill_y'])} |")
    ec = mx(RESULTS_DIR / "engine_check.json") or {}
    if ec:
        L.append(f"\n### Engine check (bf16 here vs exp19's FP8 W8A8): **{ec.get('verdict')}**\n")
        L.append("| Cell | byte-identical | per-slot label agreement | JSD | null p95 |")
        L.append("|---|---|---|---|---|")
        for k, v in ec["cells"].items():
            L.append(f"| {k} | {v['byte_identical']}/{v['n_paired']} | {f2(v['per_slot_label_agreement'])} | "
                     f"{f2(v['jsd'])} | {f2(v['null_p95'])} |")
    nov = mx(AUDIT_DIR / "novelty_audit.json") or {}
    rg = mx(AUDIT_DIR / "style_regate.json") or {}
    L.append(f"\n- Novelty audit: {nov.get('n_unique_correct_other')} unique correct 'other' programs, classes "
             f"{nov.get('classes')}; novel = {nov.get('n_novel')}.")
    L.append(f"- Style re-gate: {rg.get('n_sampled')} programs; flagged tasks {rg.get('flagged_tasks')}; per-task "
             f"agreement {({t: f2(v.get('agreement')) for t, v in (rg.get('per_task') or {}).items()})}.")
    costs = mx(RESULTS_DIR / "costs.json") or {}
    tm = mx(RESULTS_DIR / "timing_summary.json") or {}
    L.append(f"- GPU: {tm.get('hf_rows')} HF rows in {tm.get('hf_gpu_hours')} GPU-hours of batch time + literal cell "
             f"{f2((tm.get('vllm_literal_seconds') or 0) / 60)} min on vLLM; OpenRouter spend USD {f2(costs.get('total_usd'))}.")
    (RESULTS_DIR / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
