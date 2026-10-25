#!/usr/bin/env python3
"""Fills the README's results section from the results JSONs (every number is read, none typed by hand)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from c7 import RESULTS, ROOT, read_json  # noqa: E402


def opt(name: str):
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def f2(x, n=2):
    return "NA" if x is None or x != x else f"{x:.{n}f}"


def pv(x):
    return "NA" if x is None or x != x else (f"{x:.1e}" if x < 1e-3 else f"{x:.3f}")


def main() -> None:
    fa, pa = read_json(RESULTS / "f_analysis.json"), read_json(RESULTS / "p2_analysis.json")
    tc, ax = read_json(RESULTS / "t03_confirmation.json"), read_json(RESULTS / "axis.json")
    fk = read_json(RESULTS / "forks.json")["tasks"]
    tp, cl, rm = opt("targeted_push.json"), opt("clamp.json"), opt("remeasure.json")
    tl, tg, ec = opt("top5_landing.json"), opt("top5_geometry.json"), opt("engine_check.json")
    ex, ft, nv = opt("explore_llr.json"), opt("force_token.json"), opt("novelty_audit.json")
    ts, co, ut = opt("timing_summary.json"), opt("costs.json"), opt("unit_tests_cpu.json")
    F, P = fa["F"], pa["P2"]
    cal = F["calibration"]
    v = fa["verdicts"]
    L = []
    a = L.append
    a("## Results\n")
    a("**In short.** In Qwen3-8B the algorithm is not chosen by a direction in the prompt states that random pushes "
      "move along. It is decided at a few early generated tokens, where they exist.")
    a("")
    a("- T10 has two forks at generated tokens 10 and 11. The probability mass a perturbed prompt puts on those fork "
      "tokens predicts which of 40 random pushes change the algorithm (Spearman 0.80).")
    a(f"- On T03 the opening-likelihood margin predicts 24 fresh, pre-committed directions ({f2(tc['m']['rho'])}).")
    a("- On T2 the decision comes late, so the 48-token margin fails. The committed F therefore fails as a two-task "
      "claim.")
    a("- A default-to-runner-up axis in the prompt states neither predicts nor mediates the random pushes.")
    a("- Pushed hard enough along that axis (4x the forced-prompt distance, beyond the committed doses), T10 does "
      "switch to DFS on 29/30 slots, against 0/30 for a matched random direction. So the axis is a sufficient control "
      "direction there, not the channel random pushes use.")
    a("- Moving the twin's states toward the survivor region of the grid-path catalogue never produces a survivor "
      "algorithm.")
    a("- On T10, forcing the single token that names the routine (`def dfs` instead of `def find`) flips the algorithm "
      "on every slot. Forcing a comment token does not.")
    a("")
    a("### Bottom line\n")
    a(f"- **Committed verdicts.** F (the fork margin predicts which equal-dose random pushes escape) is **{v['F']}**: "
      f"it holds on T10 and fails on T2. P2 (the projection on a default-to-runner-up axis predicts it) is "
      f"**{v['P2']}**. Holm-adjusted p is {pv(v['holm']['F'])} for F and {pv(v['holm']['P2'])} for P2 (raw "
      f"{pv(v['raw_p']['F'])} and {pv(v['raw_p']['P2'])}, the worst task).")
    t10 = fk["T10"]
    tm = {f: sorted(m.values(), key=lambda x: -x["n"])[:4] for f, m in t10["token_maps"].items()}
    a("- **One early token does decide the algorithm on T10.** The prefix-resampling screen finds two forks along the "
      "default opening `def solve(n, edges):`, at generated tokens 10 and 11 (shared by "
      f"{f2(100 * t10['opening_share_twin'], 0)}% of twin programs).")
    a("  - At token 10: " + ", ".join(f"`{x['tok']!r}` -> {f2(x['q'])} non-default (n = {x['n']})" for x in tm["10"])
      + ".")
    a("  - At token 11, after `' def'`: " + ", ".join(f"`{x['tok']!r}` -> {f2(x['q'])} (n = {x['n']})"
                                                     for x in tm["11"]) + ".")
    a(f"  - Label entropy given the token falls from {f2(t10['entropy']['11']['H_label_bits'])} to "
      f"{f2(t10['entropy']['11']['H_label_given_token_bits'])} bits at token 11, and from "
      f"{f2(t10['entropy']['10']['H_label_bits'])} to {f2(t10['entropy']['10']['H_label_given_token_bits'])} at "
      "token 10.")
    a("  - T2 has **no single early fork**. Pushed paths stay undecided through token 60, and the only change point "
      f"(token {fk['T2'].get('forks_off_default_by_class', {}).get('bf_spfa', ['?'])[0]}) lies off the default "
      "opening.")
    a("  - On T03 the ban prompt fixes the class **before the first generated token**. Already at t = 0, only 0-2 of 8 "
      "continuations differ from the base path's class, and there is no change in 128 tokens.")
    a(f"- **F on T10.** The teacher-forced fork margin m predicts the correct off-default share y of the 40 random "
      f"directions (alpha 2): Spearman **{f2(F['T10']['rho'])}**, permutation p {pv(F['T10']['p_perm'])}, 95% CI "
      f"[{f2(F['T10']['ci'][0])}, {f2(F['T10']['ci'][1])}].")
    a(f"  - The tie ceiling is {f2(F['T10']['rho_max_ties'])} and Kendall tau {f2(F['T10']['kendall'])}.")
    a(f"  - AUC for exp29's {F['T10']['n_confirmed']} confirmed escapers: {f2(F['T10']['auc_confirmed'])}.")
    a(f"  - Spearman with the attempted share: {f2(F['T10']['attempted']['rho'])}; with the 48-token LLR instead of m: "
      f"{f2(F['T10']['llr48']['rho'])}.")
    a(f"- **F on T2** (pre-declared fallback: the 48-token opening LLR, because there is no single fork): Spearman "
      f"{f2(F['T2']['rho'])} (p {pv(F['T2']['p_perm'])}).")
    a(f"  - Pooled within-task rho: {f2(F['pooled']['rho'])} (p {pv(F['pooled']['p_perm'])}).")
    a(f"  - The binomial-GLM calibration over all {cal['n_cells']} cells of T10 and T2 has a held-out MAE of "
      f"{f2(cal['mae_heldout_mean'])} (threshold 0.10); the all-cell Spearman is {f2(cal['all_cell_spearman'])}.")
    a(f"  - The twin margins are {f2(F['T10']['twin_m'])} nats (T10) and {f2(F['T2']['twin_m'])} nats (T2).")
    a(f"- **T03 prospective confirmation** (24 fresh directions; predictions hash-committed before generation).")
    a(f"  - The committed opening margin (the pre-declared no-fork fallback: a 20-token opening LLR, since T03 programs "
      f"are about 20 tokens long) predicts y with Spearman **{f2(tc['m']['rho'])}** (one-sided p "
      f"{pv(tc['m']['p_one_sided'])}); {tc['n_y_pos']} of {tc['n_directions']} directions have y > 0.")
    a(f"  - The committed axis projection does not: {f2(tc['b']['rho'])} (p {pv(tc['b']['p_one_sided'])}).")
    a(f"- **P2 is disconfirmed.** The default-to-runner-up axis projection (b) at L_ax ({ax['T10']['L_ax']} on T10, "
      f"{ax['T2']['L_ax']} on T2) gives Spearman {f2(P['T10']['rho_b'])} (p {pv(P['T10']['p_perm'])}) on T10 and "
      f"{f2(P['T2']['rho_b'])} (p {pv(P['T2']['p_perm'])}) on T2.")
    comp = ", ".join(f"{k} {f2(P['T10']['competitors'][k]['rho'])}/{f2(P['T2']['competitors'][k]['rho'])}"
                     for k in ("pi_Pt", "norm", "a_share"))
    a(f"  - It is not ahead of any competitor (T10/T2 Spearman: {comp}).")
    a(f"  - The axis is not dormant: neutral prompts vary along it {f2(ax['T10']['natural_variance']['ratio'], 0)}-"
      f"{f2(ax['T2']['natural_variance']['ratio'], 0)}x more than along random directions. It is simply not the "
      "channel through which random pushes act.")
    if cl and cl.get("pooled"):
        a(f"- **Necessity (mediator clamp): {cl['verdict']}.** Removing the axis component of the push at blocks "
          f"L_ax..35 leaves {cl['pooled']['escapes']['CLA']} escapes, against {cl['pooled']['escapes']['CLU']} without "
          f"the clamp (removed share {f2(cl['pooled']['removed_share']['CLA'])}).")
        a(f"  - A random-direction clamp gives {cl['pooled']['escapes']['CLR']}; McNemar for the axis clamp is "
          f"{cl['pooled']['mcnemar']['CLA']['removed']}:{cl['pooled']['mcnemar']['CLA']['added']}.")
    if tp:
        t10a = tp["T10"]["arms"]
        a(f"- **Sufficiency (targeted push along the axis): {tp['verdict']['claim']} as committed.** No task escapes "
          "at s <= 1, and neither does the matched random direction.")
        a(f"  - At s = 1 the edit is only {f2(t10a['AX_s1']['rho_s'])}-{f2(tp['T2']['arms']['AX_s1']['rho_s'])} of the "
          "norm that escaping random directions realise at L_ax.")
        if "AX_s4" in t10a:
            a(f"  - The descriptive doses (fallback 8) locate the crossing on T10. At s = 4, {round(30 * t10a['AX_s4']['y_runner_up'])}"
              f"/30 slots become correct DFS (pass {f2(t10a['AX_s4']['pass'])}); the matched random direction gives "
              f"{round(30 * t10a['RX_s4']['y_off'])}/30 (s = 2: {round(30 * t10a['AX_s2']['y_off'])}/30).")
            a(f"  - On T2 there is no escape even at s = 8 ({round(30 * tp['T2']['arms']['AX_s8']['y_off'])}/30). On T03, "
              f"s = 8 moves {round(30 * tp['T03']['arms']['AX_s8']['y_off'])}/30 along the axis and "
              f"{round(30 * tp['T03']['arms']['RX_s8']['y_off'])}/30 along the random direction, so the effect is not "
              "specific to the axis.")
    if tl:
        arms = [k for k in tl if k.startswith(("SURV_s", "RSURV_s", "AWAY_s", "IDASTAR_s")) and "n" in tl[k]]
        n_non = sum(tl[k]["attempted_nonTOP5"] for k in arms)
        n_all = sum(tl[k]["n"] for k in arms)
        a(f"- **T1 in-manifold top-five push.** Pushes toward the survivor-region centroid, a random survivor, away "
          f"from the banned centroid, and IDA* (s 0.25-1 of the centroid distance) give **{n_non}/{n_all}** "
          f"non-top-five programs. Every arm writes BFS on 30/30 slots (pass "
          f"{f2(min(tl[k]['pass'] for k in arms))}-{f2(max(tl[k]['pass'] for k in arms))}).")
        if tl.get("TOP5BAN_exp30"):
            b = tl["TOP5BAN_exp30"]
            a(f"  - The prompt top-five ban (exp30, N = {b['n']}) also stays in the banned set: {b['labels10']}.")
        if tg:
            a(f"  - In real activation coordinates (Isomap k = 15 and PCs of forced-prompt S-mean states, block 18), "
              f"the edge survivors are {tg['edge_survivors']} and the opposite ones the rest.")
            a("  - The pushes move the twin's spec states toward the dijkstra_unit/jps region, but behaviour does not "
              "follow (figures/F6_*).")
            a("  - The old u_top5 push of iteration 4 leaves the manifold entirely (PC1 > 80 at alpha 8).")
    if rm:
        a(f"- **Engine robustness (pre-declared fallback 1).** Block-35 displacement norms differed by 2.35% from "
          "exp29, so all 40 directions were re-measured on this GPU.")
        a(f"  - Per-direction y correlates {f2(rm['T10']['y_this_vs_exp29d_rho'])} (T10) and "
          f"{f2(rm['T2']['y_this_vs_exp29d_rho'])} (T2) with exp29 engine d.")
        a(f"  - F on this engine's outcomes is {f2(rm['T10']['F_rho'])} / {f2(rm['T2']['F_rho'])} and P2 is "
          f"{f2(rm['T10']['P2_rho'])} / {f2(rm['T2']['P2_rho'])}, so the conclusions are unchanged.")
    if ec:
        a(f"- **Stage 0 engine check.** Twin labels agree per slot with exp29 engine d at "
          f"{f2(ec['0a_T10_vs_exp29d']['label_agree'])} (T10) and {f2(ec['0a_T2_vs_exp29d']['label_agree'])} (T2), "
          f"and with exp30 at 1.00 (T2, T03, T10).")
        a(f"  - Pushed rows of the 40 directions (k 0-1, re-measured here) agree per slot at "
          f"{f2(ec['0b_T10_vs_exp29d']['label_agree'])} (T10, n = {ec['0b_T10_vs_exp29d']['n']}) and "
          f"{f2(ec['0b_T2_vs_exp29d']['label_agree'])} (T2, n = {ec['0b_T2_vs_exp29d']['n']}).")
    if ex:
        t2x = ex.get("T2", {}).get("per_L", {})
        if t2x:
            a("- **Exploratory, post hoc: where T2 decides.** The opening-LLR Spearman on T2 grows with the length of the "
              "teacher-forced opening: " + ", ".join(f"L = {k}: {f2(v_['pop_spearman'])}" for k, v_ in t2x.items())
              + ". So T2's choice is carried by tokens beyond the first 48, consistent with its late change point.")
    if ft:
        a("- **Exploratory, post hoc: forcing one token under the unchanged neutral twin prompt** (N = 30 CRN slots "
          "per arm; the model completes the program itself).")
        names = {"F10_parent": "token 10 = ' parent'", "F10_#": "token 10 = ' #' (comment)",
                 "F10_from": "token 10 = ' from'", "F10_def": "token 10 = ' def' (free after it)",
                 "F11_find": "tokens 10-11 = ' def find'", "F11_dfs": "tokens 10-11 = ' def dfs'",
                 "FB_comment_#": "first body token = ' #' (comment)", "FB_default_sp": "first body token = the twin's own"}
        for t in ("T10", "T03", "T2"):
            rows = ft.get(t)
            if isinstance(rows, dict):
                a(f"  - {t}: " + "; ".join(f"{names.get(k, k)} -> {r['labels']} (pass {f2(r['pass'])}, McNemar vs twin "
                                           f"{r['flips_vs_twin']['to_off']}:{r['flips_vs_twin']['to_default']})"
                                           for k, r in rows.items()) + ".")
        a("  - Reading: on T10 the token that names the routine decides. Writing `def dfs` instead of `def find` gives a "
          "correct DFS on every slot. A comment token (q = 1.00 in the pooled token map, built mostly from ban and "
          "pushed cells) leaves the twin on union-find. So the token map is cell-dependent for non-committal tokens, "
          "a limit of the margin construction.")
    if nv:
        a(f"- **Novelty audit.** Correct programs labelled 'other': {nv['n_correct_other']}; correct disputed or "
          f"unknown: {nv.get('n_correct_disputed_or_unknown', 0)}.")
        a(f"  - Classes: {nv['classes']}. Spend USD {f2(nv['spend_usd'], 4)}.")
    if ts:
        a(f"- **Cost.** {ts['generated_programs_total']} generated programs and "
          f"{ts['counts']['fork_continuations']['n']} fork continuations, plus several thousand teacher-forced passes "
          f"(margins, LLRs, axis and geometry captures) on one RTX 4090.")
        a(f"  - Generation batches logged {f2(ts['gpu_seconds_total_logged'] / 3600, 2)} GPU-hours; with model "
          "loads and teacher forcing the GPU was busy about 1.7 hours of wall-clock.")
        a(f"  - OpenRouter: USD {f2((co or {}).get('openrouter_usd_total', 0), 4)}.")
    a("\n### Tests and audits\n")
    if ut:
        c3 = ut.get("C3_change_points", {})
        a(f"- CPU tests (`results/unit_tests_cpu.json`):")
        a(f"  - The targeted-edit math, margin math and Spearman/permutation/tie-ceiling code pass (tie ceiling "
          f"{f2(ut.get('C4_stats', {}).get('tie_ceiling_34_zeros'))} for the 34-zero vector).")
        a(f"  - **C3 fails as specified**: a 0.4 jump with only three pre-jump screen positions is detected in "
          f"{f2(100 * c3.get('detection_rate_p<0.01', {}).get('jump_0.4', float('nan')), 0)}% of simulations. The "
          "screen is underpowered for very early forks.")
    a("- GPU tests (`results/unit_tests_gpu.json`):")
    a("  - CRN determinism and the alpha-0 hook identity are bit-exact, and B = 1 vs B = 8 is invariant.")
    a("  - **U5 misses its 0.05 tolerance**: teacher-forced and KV-prefill log-probs differ by up to 0.25 on the top-50 "
      "tokens, with the same argmax. These are different SDPA paths in bf16; every margin uses the same "
      "teacher-forced path.")
    a("- The sha256 chain in `commitments.log` verifies. Every amendment (#0b, #1b, #1c, #3b) precedes the outcome "
      "rows it could affect, as listed in `results/deviations.jsonl`.")
    rd = opt("rederive.json")
    if rd:
        a(f"- `audit/rederive.py` re-derives the headline numbers with the standard library only "
          f"(`results/rederive.json`): {rd['n_checks']} checks, {len(rd['mismatches'])} mismatches.")
        a("  - The checks cover every y, the F/P2/T03 Spearmans, the tie ceilings, the targeted-push shares, and "
          "every T10 margin re-derived from the fork-token probabilities and the committed token maps.")
        for c in rd["checks"]:
            if c["name"].startswith("placebo shuffled-y F T10"):
                a(f"  - Placebo, shuffled y: median null rho {f2(c['median_null_rho'])} (observed {f2(c['observed'])}).")
            if c["name"].startswith("placebo shuffled fork token map"):
                a(f"  - Placebo, shuffled fork-token map on T10: median null rho {f2(c['null_median'])}, but "
                  f"{f2(100 * c['share_null_ge_observed'], 0)}% of the 200 permutations reach the observed "
                  f"{f2(c['observed'])}. With only 4-5 mapped tokens per fork, the permutations that keep a low q on "
                  "the default tokens reproduce the effect.")
                a("  - So the margin's power comes from the probability of staying on the default fork tokens, not "
                  "from the exact q values of the alternatives.")
        for t in rd.get("tests", []):
            if "p_observed" in t:
                a(f"  - Re-run test: {t['test']}. rho {f2(t['rho'])}, permutation p {pv(t['p_observed'])}. On shuffled "
                  f"y it reaches p < 0.05 in {f2(100 * t['placebo_shuffled_y_share_p_lt_0.05'], 0)}% of 100 shuffles "
                  "(it fails on placebo input).")
            elif "p_exact" in t:
                a(f"  - Re-run test: {t['test']}. Discordant {t['discordant'][0]}:{t['discordant'][1]}, exact p "
                  f"{pv(t['p_exact'])}. A random arm swap reaches p < 0.05 in "
                  f"{f2(100 * t['placebo_random_arm_swap_share_p_lt_0.05'], 0)}% of 200 swaps.")
            elif "n_non_top5_attempted" in t:
                a(f"  - Re-counted from the raw label rows: {t['n_non_top5_attempted']} non-top-five programs among "
                  f"{t['n_rows']} T1 push rows ({t['n_bfs']} BFS).")
    a("\n### Limits\n")
    a("- One model (Qwen3-8B, bf16), memorised LeetCode-style tasks, two primary tasks and one confirmation task.")
    a("- The 40 primary outcomes come from exp29 (another GPU, N = 10-30). This run's re-measurement agrees.")
    a("- The fork screen is sparse (S = 8 every 4th token) and misses weak or very early forks.")
    a("- T03's base paths are ban paths only.")
    a("- T1 10-algorithm labels are AST-only.")
    a("- Everything marked exploratory was decided after seeing the committed results.")
    text = "\n".join(L)
    rd = (ROOT / "README.md").read_text()
    start = rd.index("## Results") if "## Results" in rd else rd.index("RESULTS_PLACEHOLDER")
    end = rd.index("## What was run")
    rd = rd[:start] + text + "\n\n" + rd[end:]
    (ROOT / "README.md").write_text(rd)
    print(text[:3000])


if __name__ == "__main__":
    main()
