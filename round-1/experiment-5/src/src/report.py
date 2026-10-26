"""Render results/summary.md (markdown tables) from results/analysis.json. Used verbatim in README.md.
  .venv/bin/python src/report.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS  # noqa: E402


def f(x, d=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    if isinstance(x, float):
        return f"{x:.{d}f}"
    return str(x)


def ci(dct, d=2):
    if not dct or dct.get("est") is None:
        return "–"
    lo, hi = dct.get("lo"), dct.get("hi")
    return f"{f(dct['est'], d)} [{f(lo, d)}, {f(hi, d)}]"


def wl(t, d=2):
    if not t:
        return "–"
    return f"{f(t[0], d)} [{f(t[1], d)}, {f(t[2], d)}]"


def main() -> None:
    a = json.loads((RESULTS / "analysis.json").read_text())
    qa = a.get("labeller_qa", {}).get("per_arm", {})
    L = []
    L.append("### Per-arm results (vLLM arms; T=1.0, top-p 1.0, no top-k, thinking off)\n")
    L.append("| arm | task | N | parse | pass [95% Wilson] | n correct | modal (correct) | modal share | Hill_cc [95% cluster-bootstrap] | Hill_all [95%] | audit acc. vs judge | judge-label Hill_cc |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    order = ["base_tf", "base_chat", "instruct_tf", "instruct_chat", "base_tf_ban", "instruct_chat_ban"]
    sens = a.get("labeller_qa", {}).get("judge_label_sensitivity", {})
    for arm in order:
        for t in ("t1", "t2"):
            v = a["arms"].get(f"{arm}|{t}")
            if not v:
                continue
            q = qa.get(f"{arm}|{t}", {})
            s = sens.get(f"{arm}|{t}", {})
            L.append(f"| {arm} | {t} | {v['N']} | {f(v['parse_rate'])} | {wl(v['pass_rate'])} | {v['n_correct_labelled']} | "
                     f"{v.get('modal_correct', '–')} | {wl(v.get('modal_share_correct'))} | {ci(v['hill_cc_ci'])} | {ci(v['hill_all_ci'])} | "
                     f"{wl(q.get('audit_accuracy_vs_judge'))} | {f(s.get('hill_cc_judge'))} |")
    L.append("\nLabel counts over correct programs:\n")
    for arm in order:
        for t in ("t1", "t2"):
            v = a["arms"].get(f"{arm}|{t}")
            if v:
                L.append(f"- **{arm} / {t}** correct: `{v['label_counts_correct']}`; all parseable: `{v['label_counts_all']}`")
    L.append("\n### Collapse screen (2x2 weights x format), Hill_cc differences with paraphrase-joint cluster bootstrap\n")
    L.append("| task | D_weights = H(instruct_chat) - H(base_chat) | D_format = H(base_chat) - H(base_tf) | D_format_instruct = H(instruct_chat) - H(instruct_tf) | interaction | verdict (Hill_cc, pre-registered) | verdict (Hill_all, fallback-3 co-primary) |")
    L.append("|---|---|---|---|---|---|---|")
    for t in ("t1", "t2"):
        c = a["collapse_screen"].get(t, {})
        if "verdict_cc" not in c:
            continue
        L.append(f"| {t} | {ci(c.get('D_weights_cc'))} | {ci(c.get('D_format_cc'))} | {ci(c.get('D_format_instruct_cc'))} | "
                 f"{ci(c.get('interaction_cc'))} | **{c['verdict_cc']['verdict']}** | **{c['verdict_all']['verdict']}** |")
    L.append("\nSame contrasts on Hill_all (all parseable labelled programs):\n")
    L.append("| task | D_weights_all | D_format_all | D_format_instruct_all | interaction_all |")
    L.append("|---|---|---|---|---|")
    for t in ("t1", "t2"):
        c = a["collapse_screen"].get(t, {})
        L.append(f"| {t} | {ci(c.get('D_weights_all'))} | {ci(c.get('D_format_all'))} | {ci(c.get('D_format_instruct_all'))} | {ci(c.get('interaction_all'))} |")
    L.append("\nVerdict ingredients (Hill_cc):\n")
    for t in ("t1", "t2"):
        c = a["collapse_screen"].get(t, {})
        if "verdict_cc" not in c:
            continue
        v = c["verdict_cc"]
        L.append(f"- {t}: H(base_chat) - H(instruct_chat) = {ci(v['hill_base_chat_minus_instruct_chat'])}; modal-share gap "
                 f"{f(v['modal_share_gap_pp_weights'], 1)} pp (instruct modal `{v['instruct_modal']}`, base_tf modal `{v['base_tf_modal']}`, "
                 f"base_chat modal `{v['base_chat_modal']}`); H(base_tf) - H(instruct_chat) = {ci(v['hill_base_tf_minus_instruct_chat'])}; "
                 f"bars met: weights={v['weights_bar_met']}, format={v['format_bar_met']}, already_in_base={v['already_in_base_bar_met']}")
        p = c.get("permutation_chi2", {})
        L.append(f"  - permutation chi-square p (correct labels): instruct_chat vs base_chat {f(p.get('instruct_chat_vs_base_chat_cc', {}).get('p'), 4)}, "
                 f"base_chat vs base_tf {f(p.get('base_chat_vs_base_tf_cc', {}).get('p'), 4)}, instruct_chat vs instruct_tf "
                 f"{f(p.get('instruct_chat_vs_instruct_tf_cc', {}).get('p'), 4)}")
    L.append(f"\nAlternate 4 passes the screen (Hill_cc rule): **{a['collapse_screen'].get('alternate_passes_screen_cc')}**; "
             f"(Hill_all rule): **{a['collapse_screen'].get('alternate_passes_screen_all')}**\n")
    cs = a.get("collapse_screen_sensitivity", {})
    if cs:
        L.append("Sensitivity of the verdict:\n")
        for k, c in cs.items():
            if "verdict_cc" in c:
                L.append(f"- {k}: Hill_cc verdict {c['verdict_cc']['verdict']} (D_weights {ci(c.get('D_weights_cc'))}); "
                         f"Hill_all verdict {c['verdict_all']['verdict']} (D_weights_all {ci(c.get('D_weights_all'))}); sizes {c.get('arm_sizes')}")
    L.append("\n### Steering (HF, Qwen3-8B, coupled seeds; all deltas vs the hooked c=0 control S0)\n")
    L.append("| task | arm | N | parse | pass | format_ok_loose | degenerate | Hill_cc | dHill_cc vs S0 | dpass (pp) vs S0 | flip rate vs S0 | restoration idx vs base_chat (add-0.5 / unsmoothed) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in ("t1", "t2"):
        st = a["steering"].get(t, {})
        if "S0" not in st:
            continue
        s0 = st["S0"]
        L.append(f"| {t} | S0 none c=0 | {s0['N']} | {f(s0['parse_rate'])} | {wl(s0['pass_rate'])} | {f(s0['format_ok_loose_rate'])} | "
                 f"{f(s0['degenerate_rate'])} | {f(s0['hill_cc'])} | – | – | – | – |")
        for k, v in sorted(st["arms"].items()):
            L.append(f"| {t} | {k.replace('steer:', '')} | {v['N']} | {f(v['parse_rate'])} | {wl(v['pass_rate'])} | {f(v['format_ok_loose_rate'])} | "
                     f"{f(v['degenerate_rate'])} | {f(v['hill_cc'])} | {ci(v['delta_hill_cc_vs_S0'])} | {ci(v['delta_pass_pp_vs_S0'], 1)} | "
                     f"{f(v['flips_vs_S0'].get('flip_rate'))} | {ci(v.get('restoration_index_vs_base_chat'))} / "
                     f"{ci(v.get('restoration_index_unsmoothed_vs_base_chat'))} |")
        L.append(f"| {t} | **knob verdict (band 8-28)** | | | | | | | **{st.get('knob_verdict')}** | c* = {st.get('c_star')} {st.get('c_star_flag') or ''} | | |")
        for k, v in st.items():
            if k.startswith("family_verdict|"):
                L.append(f"| {t} | **{k.split('|')[1]}** | | | | | | | **{v['verdict']}** | | | |")
        L.append("")
        for k, v in sorted(st["arms"].items()):
            if v.get("nocode_rows"):
                L.append(f"- {t} {k.replace('steer:', '')}: thinking-style opening rate {f(v.get('thinking_style_opening_rate'))}; "
                         f"{v['nocode_rows']} rows without parseable code; algorithm keywords in those rows: `{v.get('nocode_keyword_mentions')}`")
        if st.get("S0_vs_vllm_B1"):
            sv = st["S0_vs_vllm_B1"]
            L.append(f"\n{t}: S0 (HF engine) vs B1 (vLLM) implementation check: Hill_cc {f(sv['hill_cc_S0'])} vs {f(sv['hill_cc_B1'])}, "
                     f"pass {wl(sv['pass_S0'])} vs {wl(sv['pass_B1'])}, permutation p = {f(sv['perm_chi2_cc'].get('p'), 4)}\n")
        for k, v in st.items():
            if k.startswith("cutoff_validation|"):
                L.append(f"{t}: 512-token no-code rule validation for {k.split('|')[1]} on {v['n_coupled']} coupled samples: parse "
                         f"{f(v['parse_rate_with_cutoff'])} with rule vs {f(v['parse_rate_without_cutoff'])} without (max 1024 tokens); pass "
                         f"{f(v['pass_rate_with_cutoff'])} vs {f(v['pass_rate_without_cutoff'])}; correct labels without rule "
                         f"`{ {a: b for a, b in v['labels_without_cutoff_correct'].items() if b} }`\n")
        for k, v in st.items():
            if k.startswith("Ronly_vs_random_control"):
                L.append(f"{t}: R-only sharpening vs R-only random control ({k.split('|')[1]}): Hill diff {ci(v['hill_diff'])}, "
                         f"flip diff {ci(v['flip_diff_vs_control'])}, permutation p {f(v['perm_chi2_cc'].get('p'), 4)}\n")
    man = a.get("manipulation", {})
    if man:
        L.append("\nManipulation check, gap_closed = 1 - ||mean h_steered - mean h_B|| / ||mean h_I - mean h_B|| at R:\n")
        for src, d in man.items():
            dd = d.get("gap_closed", d)
            for t, arms_ in dd.items():
                if not isinstance(arms_, dict):
                    continue
                for arm, g in arms_.items():
                    if isinstance(g, dict):
                        L.append(f"- {src} {t} {arm}: " + ", ".join(f"{k} {f(x)}" for k, x in g.items()))
    L.append("\n### BUY rows\n")
    L.append("| task | knob | Hill_cc | pass | dHill_cc | pass loss (pp) | efficiency | price Hill 2 | price Hill 3 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in a["rows"]["BUY"]:
        L.append(f"| {r['task']} | {r['knob']} | {f(r['hill_cc'])} | {f(r['pass_rate'])} | {f(r['delta_hill_cc'])} | {f(r['pass_loss_pp'], 1)} | "
                 f"{f(r['efficiency'], 3)} | {f(r.get('price_hill2'))} | {f(r.get('price_hill3'))} |")
    L.append("\n### PREDICT rows (hash-committed before phase C; primary = base_tf all-samples, fallback 3)\n")
    L.append("| task | predictor | primary | n compliant | realised mode | top-1 | hit | log score | JS to realised | hash match |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in a["rows"]["PREDICT"]:
        L.append(f"| {r['task']} | {r['predictor']} | {r['primary']} | {r['n_compliant']} | {r['realised_mode']} | {r['top1']} | {r['top1_hit']} | "
                 f"{f(r['log_score'], 3)} | {f(r['js_to_realised'], 3)} | {r['hash_match']} |")
    if a["rows"]["PREDICT"]:
        L.append("\nRealised compliant landing counts: " + "; ".join(
            f"{r['task']}: `{r['realised_counts']}`" for r in a["rows"]["PREDICT"] if r["primary"]))
    L.append("\n### Base-model ban obedience (template-free A3 vs A1)\n")
    for t, v in a.get("base_ban_obedience", {}).items():
        if not v:
            continue
        L.append(f"- {t}: banned `{v['banned_mode']}` share among parseable: ban {wl(v.get('banned_share_ban_parseable'))} vs baseline "
                 f"{wl(v.get('banned_share_baseline_parseable'))} (diff {ci(v.get('diff_ban_minus_baseline_parseable'))}); "
                 f"compliance (correct and not banned) {wl(v.get('compliance_rate'))}; base landing `{v.get('survivor_landing_base')}`; "
                 f"instruct landing `{v.get('survivor_landing_instruct')}` (instruct compliance {wl(v.get('instruct_compliance_rate'))}); "
                 f"JS(base, instruct landing) {f(v.get('js_base_vs_instruct_landing'), 3)}")
    q = a.get("labeller_qa", {})
    L.append("\n### Labeller QA\n")
    g = q.get("reference_gate", {})
    L.append(f"- Reference gate (15 catalogue references + 10 variants/mutants): AST accuracy {f(g.get('ast_accuracy'))}, runtime never-wrong rate "
             f"{f(g.get('runtime_no_wrong_rate'))} (exact {f(g.get('runtime_exact_accuracy'))}; array-scan Dijkstra and Dial are 'unknown' at runtime by design), gate ok = {g.get('gate_ok')}")
    L.append(f"- Cohen's kappa runtime vs AST (all parseable programs): {f(q.get('kappa_runtime_vs_ast_overall'))}")
    sj = q.get("second_judge")
    if sj:
        L.append(f"- Second judge ({sj['model']}) on {sj['n']} audit programs: inter-judge kappa {f(sj['kappa_inter_judge'])}, raw agreement {f(sj['raw_agreement'])}")
    L.append("\n| arm / task | n parseable | kappa runtime-AST | audit acc. (15) | final vs judge (all) | runtime+AST labels vs judge | sources |")
    L.append("|---|---|---|---|---|---|---|")
    for k, v in q.get("per_arm", {}).items():
        L.append(f"| {k} | {v['n_parseable']} | {f(v['kappa_runtime_vs_ast'])} | {wl(v['audit_accuracy_vs_judge'])} | "
                 f"{wl(v['full_agreement_final_vs_judge'])} | {wl(v['deterministic_labels_agreement_with_judge'])} | {v['sources']} |")
    L.append("\n### Priors (context, not tests)\n")
    L.append(f"- T2: {json.dumps(a.get('priors', {}).get('t2'))}")
    L.append(f"- T1: {json.dumps(a.get('priors', {}).get('t1'))}")
    (RESULTS / "summary.md").write_text("\n".join(L) + "\n")
    print(f"wrote {RESULTS / 'summary.md'} ({len(L)} lines)")


if __name__ == "__main__":
    main()
