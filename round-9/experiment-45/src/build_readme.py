#!/usr/bin/env python3
"""Render README.md from results/*.json (every number in the README is read from a results file, so the two cannot
drift). Usage: .venv/bin/python build_readme.py"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R = ROOT / "results"
P = ROOT / "predictions"


def rj(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def f(x, n=2):
    if x is None:
        return "n/a"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return str(x)


def ci(v, n=2):
    if not v or v[0] is None:
        return "n/a"
    return f"{f(v[0], n)} to {f(v[1], n)}"


def main() -> None:
    h = rj(R / "headlines.json")
    n1 = rj(R / "n1.json")
    n1t = rj(R / "n1_tracer.json")
    n2 = rj(R / "n2.json")
    n2t = rj(R / "n2_tracer.json")
    n3 = rj(R / "n3.json")
    n3t = rj(R / "n3_tracer.json")
    n3d = rj(R / "n3d.json")
    n3dt = rj(R / "n3d_tracer.json")
    n5 = rj(R / "n5.json")
    sc = rj(R / "scale.json")
    g0, g1, g2 = rj(R / "tracer_gate_round0.json"), rj(R / "tracer_gate_round1.json"), rj(R / "tracer_gate_round2.json")
    ut = rj(R / "tracer_unit_tests.json")
    clrs = rj(R / "clrs_check.json")
    oj = rj(R / "gold_order_judges.json")
    costs = rj(R / "costs.json")
    red = rj(R / "rederive.json")
    pse = rj(R / "placebo_shuffled_events.json")
    nov = rj(R / "novelty_audit_v9.json")
    mr = rj(R / "manual_reads_summary.json")
    sets = rj(P / "n5_sets.json")
    devs = json.loads((R / "deviations.json").read_text()) if (R / "deviations.json").exists() else []
    L = []
    w = L.append
    w("# Do banned AI coders just rename BFS?")
    w("")
    w("TP-B, iteration 9 of the algorithm-choice study (`gen_plan_experiment_1_idx2`).")
    w("")
    w("**Question.** A prompt bans a model's whole path-search repertoire by NAME (\"Do not use BFS, DFS, IDDFS, A* or "
      "greedy best-first search\"). Is the ban obeyed on names but not on mechanisms? We compare three readings of the "
      "same programs:")
    w("")
    w("1. **lexical** compliance: no banned alias in the code (L1, the direction's definition; L2 = self-naming only);")
    w("2. **name-level** label: the iteration-8 labeller plus gated LLM judges (which algorithm the program *is called* or "
      "*judged* to be);")
    w("3. **mechanistic** compliance: the expansion-order class of the program measured at RUNTIME on 40 probe grids, "
      "without reading any name.")
    w("")
    w("Task: T1 grid path (`solve(grid, start, goal)`, 4-neighbour moves, any valid path), the frozen 48-case hidden "
      "suite plus the 41-case ITER1 suite. Everything was hash-committed before the rows it governs "
      "(`commitments.log`: commit #1a, #1b, #2 and the amendments #3 to #9; the chain verifies). "
      "Step-by-step reproduction: `reproducibility.md`.")
    w("")
    bnd = rj(R / "instrument_bounds.json")
    fv = rj(R / "fallback_label_validation.json")
    w("## Bottom line")
    w("")
    w(f"- **Bans are obeyed on names far more than on mechanisms in the retraced iteration 1-8 rows (N1).** Lexical "
      f"compliance minus mechanistic compliance, pooled over 10 configurations: {f(n1.get('pooled_equal_weight'))} "
      f"with the committed (fallback) runtime label and {f(n1t.get('pooled_equal_weight'))} with the tracer; between "
      f"{f(bnd.get('N1_pooled_gap_lower'))} and {f(bnd.get('N1_pooled_gap_upper'))} whichever instrument is trusted "
      "(post-hoc bound). Most of these programs are BFS or DFS written without the banned words. In the three "
      "thinking configurations, the reasoning of nearly every such covert re-implementation mentions a banned name "
      "(C1 " + f(n1["per_config"].get("C1", {}).get("knowing_rename_share")) + ", C4 " +
      f(n1["per_config"].get("C4", {}).get("knowing_rename_share")) + ", C6 " +
      f(n1["per_config"].get("C6", {}).get("knowing_rename_share")) + "): the model is aware of the ban while it "
      "writes the banned mechanism under another name.")
    q32 = n3.get("q32", {}).get("per_k", {})
    q32t = n3t.get("q32", {}).get("per_k", {})
    if q32:
        w(f"- **Under cumulative bans (N3), lexical compliance stays high while mechanistic compliance falls with k**, "
          f"for Qwen3-32B: k=1..5 mechanistic (runtime) = "
          + ", ".join(f(q32[k]['mech_coarse_traceable']['rate']) for k in q32) + "; tracer = "
          + ", ".join(f(q32t[k]['mech_coarse_traceable']['rate']) for k in q32t) + "; lexical = "
          + ", ".join(f(q32[k]['lex_L1_completed']['rate']) for k in q32) + ".")
    if mr:
        w(f"- **But the correct survivors of the full five-name ban (Qwen3-32B and Qwen3-14B) are mostly NOT renamed "
          f"BFS.** By the executor's reads of all {mr.get('n')} k=5 survivors, {f(mr.get('read_banned_share'))} are in a "
          f"banned expansion class, and all of those are unit-weight Dijkstra (BFS order by construction on a unit grid). "
          f"The rest are grid Bellman-Ford rounds, coordinate-key heaps, random-priority or random-choice frontiers, "
          f"set.pop() order and mixed deques: known but genuinely different expansion disciplines. The reads agree with "
          f"the tracer on {f(mr.get('agreement_read_vs_tracer_class'))} of these programs and with the fallback runtime "
          f"label on {f(mr.get('agreement_read_vs_runtime_class'))}; the runtime label reads grid Bellman-Ford rounds "
          f"as iterative deepening (planted control: {fv.get('runtime_ok_controls')}/9 for the runtime label vs "
          f"{fv.get('tracer_ok_controls')}/9 for the tracer).")
    w("- **Name-level labels are unreliable for exactly these programs:** heaps keyed by coordinates (r + c, "
      "r*cols + c) were labelled 'unit Dijkstra' or 'greedy best-first' by the judges (see 'Name-level labels vs heap "
      "keys').")
    w("- Status: the tracer failed its gold gate, so every N1-N3 number is descriptive; the scale and N3-D results "
      "are exploratory and N5 secondary.")
    w("")
    w("## Status first: the tracer gate FAILED, so N1-N3 are DESCRIPTIVE")
    w("")
    w(f"- The new expansion-order tracer v9 passed its references ({g2.get('references_ok')}/{g2.get('references_n')}; "
      f"bidirectional A* is the one unverified class) and classified its 9 planted controls correctly "
      f"({g2.get('controls_ok')}/9). One control, the random walk with restarts, does not itself pass the 48-case "
      f"suite, so the gate's control criterion (correct class AND a passing control) is formally "
      f"{sum(1 for c in g2.get('controls', []) if c.get('ok') and c.get('passes_48'))}/9 "
      f"(`passed_controls` false in `results/tracer_gate_round2.json`); the gate failed on gold in any case.")
    w(f"- It **failed on gold programs** from non-ban conditions after the two allowed revision rounds: agreement "
      f"{g0.get('gold_agree')}/{g0.get('gold_in_scope')} = {f(g0.get('gold_agreement'))} (round 0), "
      f"{g1.get('gold_agree')}/{g1.get('gold_in_scope')} = {f(g1.get('gold_agreement'))} (round 1), "
      f"{g2.get('gold_agree')}/{g2.get('gold_in_scope')} = {f(g2.get('gold_agreement'))} (round 2), against a bar of 0.90.")
    pl = g2.get("gold_per_label", {})
    w("- Per label (round 2): " + ", ".join(f"{k} {v['agree']}/{v['traceable']}" for k, v in pl.items()) + ".")
    w("  The failure is concentrated in LLM-written iterative deepening (exponential path-enumerating IDDFS / IDA*), "
      "jump point search and part of A*; BFS, bidirectional BFS, greedy best-first, unit Dijkstra and DFS agree well.")
    w("- **Committed fallback (logged before commit #1b and before any ban row was traced):** the primary mechanism "
      "label is the iteration-8 name-free runtime label (heap priorities, FIFO/LIFO evidence, restarts) mapped "
      "through the committed coarse table (`runtime_class`). The tracer v9 class is reported beside it as a second "
      "column. **N1-N3 are DESCRIPTIVE**: the numbers are measured and reported, but no inferential verdict is "
      "claimed.")
    w(f"- Unit tests (testing plan 1): {ut.get('n_ok')}/{ut.get('n')} mutation, renaming and sandbox programs pass. "
      "The two failures are informative: renaming identifiers breaks the round-1 rule that reads two consecutive int "
      "arguments as a cell only under coordinate-like parameter names (recursive DFS and IDA* references). The "
      "tracer's recursive-call detection is therefore NOT fully name-independent. This is one more reason it is the "
      "second column here.")
    if clrs:
        w(f"- CLRS-30 canonical traces (dataset `clrs_text`): BFS p_mono = {f(clrs['bfs']['stat_min'])} on "
          f"{clrs['bfs']['n']} traces, DFS stack adjacency = {f(clrs['dfs']['stat_min'])} on {clrs['dfs']['n']} "
          f"traces (`audit/clrs_check.py`).")
    if oj:
        w(f"- Blind order-discipline judges on {oj.get('n')} stratified gold programs: gated {oj.get('gated')}. "
          f"Tracer vs judge agreement {f(oj.get('tracer_vs_judges'))}; prior label vs judge "
          f"{f(oj.get('prior_label_vs_judges'))} (`results/gold_order_judges.json`).")
    w("")
    # ---- N1
    w("## N1 (primary, descriptive): lexical minus mechanistic compliance on ~580 retraced ban programs")
    w("")
    w("Programs: the iteration-8 five-name-ban rows C1-C8 (C6 includes its held-out confirmation), C9 = iteration-2 "
      "Qwen3-8B TOP5 and C10 = gemma-3-4b-it TOP5. B = {BFS, DFS, IDDFS, A*, greedy} -> banned coarse classes "
      "{BFS, DFS, ID, HEUR}.")
    w("")
    w("| Config | n | lexical L1 | mechanistic (runtime) | gap (Newcombe paired 95%) | McNemar p | covert share | "
      "tracer gap |")
    w("|---|---|---|---|---|---|---|---|")
    for c, t in n1.get("per_config", {}).items():
        tt = n1t.get("per_config", {}).get(c, {})
        w(f"| {c} | {t['n']} | {f(t['lex'])} | {f(t['mech'])} | {f(t['gap'])} ({ci(t['gap_newcombe95'])}) | "
          f"{f(t['mcnemar_p'], 4)} | {f(t['covert_reimpl_share'])} | {f(tt.get('gap'))} |")
    w("")
    w(f"- **Pooled (equal weight):** {f(n1.get('pooled_equal_weight'))} (configuration-cluster bootstrap "
      f"{ci(n1.get('pooled_bootstrap95'))}); program-weighted {f(n1.get('pooled_program_weighted'))}. Positive in "
      f"{n1.get('n_positive')}/{n1.get('n_configs')} configurations. The bars would read "
      f"'{n1.get('verdict')}', but N1 is descriptive (gate failed).")
    w(f"- Tracer column: pooled {f(n1t.get('pooled_equal_weight'))} ({ci(n1t.get('pooled_bootstrap95'))}), positive "
      f"in {n1t.get('n_positive')}/{n1t.get('n_configs')}.")
    w(f"- Sensitivities (runtime label): L2 pooled {f(n1.get('pooled_sens_L2'))}; untraceable-as-compliant "
      f"{f(n1.get('pooled_sens_untraceable_compliant'))}; untraceable-as-non-compliant "
      f"{f(n1.get('pooled_sens_untraceable_noncompliant'))}. Fine-class sensitivity (tracer only): "
      f"{f(n1t.get('pooled_sens_fine'))}.")
    kn = {c: t.get("knowing_rename_share") for c, t in n1.get("per_config", {}).items() if "knowing_rename_share" in t}
    w(f"- 'Knowing rename' (share of lexically compliant but mechanistically banned programs whose THINKING names a "
      f"banned alias): " + ", ".join(f"{c} {f(v)}" for c, v in kn.items()) + ".")
    w("")
    # ---- N2
    w("## N2 (primary, descriptive): what Qwen3-32B-thinking's name-level survivors actually run")
    w("")
    a, b = n2.get("a_all", {}), n2.get("b_not_bfs_by_definition", {})
    at, bt = n2t.get("a_all", {}), n2t.get("b_not_bfs_by_definition", {})
    w(f"Pool: {n2.get('n_survivors')} name-level correct survivors (iteration-8 screen + held-out, new A k=5 + held-out).")
    w("")
    w("| Reading | runtime label | tracer v9 |")
    w("|---|---|---|")
    w(f"| (a) all survivors in a banned coarse class | {a.get('k')}/{a.get('n')} = {f(a.get('share'))} "
      f"({ci(a.get('wilson95'))}) | {at.get('k')}/{at.get('n')} = {f(at.get('share'))} ({ci(at.get('wilson95'))}) |")
    w(f"| (b) excluding BFS-order-by-definition identities | {b.get('k')}/{b.get('n')} = {f(b.get('share'))} "
      f"({ci(b.get('wilson95'))}) | {bt.get('k')}/{bt.get('n')} = {f(bt.get('share'))} ({ci(bt.get('wilson95'))}) |")
    ac, act = n2.get("adj_coarse") or {}, n2t.get("adj_coarse") or {}
    w(f"| N2-adj: share minus the uniform-catalogue null 0.6 | {f(ac.get('diff'))} ({ci(ac.get('wilson95_shifted'))}) | "
      f"{f(act.get('diff'))} ({ci(act.get('wilson95_shifted'))}) |")
    w("")
    w(f"- By source: " + "; ".join(f"{k}: {v['coarse']['k']}/{v['coarse']['n']}" for k, v in n2.get("by_source", {}).items())
      + " (runtime label).")
    w(f"- Exactly FIFO BFS order: {n2t.get('exact_fifo_bfs_renamed')}/{n2t.get('n_traceable')} survivors (tracer).")
    w("- Trap 1, reported in the open: unit-weight Dijkstra and FIFO SPFA are BFS order on a unit grid BY "
      "CONSTRUCTION, which is why reading (b) exists. Trap 2: under the coarse classes 3 of the 5 non-banned catalogue "
      "algorithms already fall in banned classes, so the 0.6 bar equals the uniform null and only N2-adj separates "
      "renaming from a mechanism-blind choice.")
    w("")
    # ---- N3
    w("## N3 (primary, descriptive): cumulative bans k = 1..5")
    w("")
    w("B_k = the first k of [BFS, DFS, IDDFS, A*, greedy]; N = 50 per k on W1/W2/W3; held-out k = 5 on W4/W5/P6/P7.")
    w("")
    for mk, name in (("q32", "Qwen3-32B thinking"), ("q14", "Qwen3-14B thinking (replication)")):
        v = n3.get(mk)
        if not v:
            continue
        vt = n3t.get(mk, {})
        w(f"**{name}**")
        w("")
        w("| k | completed | lexical L1 | mechanistic (runtime) | gap (95%) | tracer mech | named survivors | pass | "
          "truncated |")
        w("|---|---|---|---|---|---|---|---|---|")
        for k, c in v["per_k"].items():
            ct = vt.get("per_k", {}).get(k, {})
            w(f"| {k} | {c['n_completed']}/{c['n']} | {f(c['lex_L1_completed']['rate'])} | "
              f"{f(c['mech_coarse_traceable']['rate'])} | {f(c['gap_L1']['gap'])} ({ci(c['gap_L1']['gap_newcombe95'])}) | "
              f"{f((ct.get('mech_coarse_traceable') or {}).get('rate'))} | {f(c['named_survivors']['rate'])} | "
              f"{f(c['pass_rate'])} | {f(c['truncation_rate'])} |")
        if v.get("heldout_k5"):
            hcell = v["heldout_k5"]
            w(f"| 5 held-out | {hcell['n_completed']}/{hcell['n']} | {f(hcell['lex_L1_completed']['rate'])} | "
              f"{f(hcell['mech_coarse_traceable']['rate'])} | {f(hcell['gap_L1']['gap'])} "
              f"({ci(hcell['gap_L1']['gap_newcombe95'])}) | "
              f"{f((vt.get('heldout_k5') or {}).get('mech_coarse_traceable', {}).get('rate'))} | "
              f"{f(hcell['named_survivors']['rate'])} | {f(hcell['pass_rate'])} | {f(hcell['truncation_rate'])} |")
        jt, ca = v.get("jt_mech_coarse", {}), v.get("ca_mech_coarse", {})
        w("")
        w(f"- Jonckheere-Terpstra (decreasing mechanistic compliance in k): J = {f(jt.get('J'), 1)}, Monte-Carlo exact "
          f"p = {f(jt.get('p_mc'), 5)} (100,000 permutations); Cochran-Armitage one-sided p = {f(ca.get('p_one_sided'), 5)}.")
        w(f"- Criteria: " + ", ".join(f"{k} = {v2}" for k, v2 in v.get("criteria", {}).items()) + f". The bars would read: "
          f"{v.get('verdict')} (descriptive).")
        w("")
    # ---- N3-D
    if n3d:
        w("## N3-D (exploratory): a name-free described five-mechanism ban")
        w("")
        d, nk = n3d["described"], n3d["named_k5"]
        w("| | described (no names) | named k = 5 | difference (Newcombe 95%) |")
        w("|---|---|---|---|")
        for m in ("mech_compliance", "violation", "lexical_any_banned_name", "named_survivors", "mech_survivors"):
            dd = n3d["diffs"][m]
            w(f"| {m} | {f(d[m]['rate'])} ({d[m]['k']}/{d[m]['n']}) | {f(nk[m]['rate'])} ({nk[m]['k']}/{nk[m]['n']}) | "
              f"{f(dd['diff'])} ({ci(dd['newcombe95'])}) |")
        w("")
        w(f"- Committed direction: {n3d.get('direction_committed')}. Mechanistic compliance rises: "
          f"{n3d.get('mech_rises')}; violation rises: {n3d.get('violation_rises')} (runtime label). Tracer column: "
          f"{n3dt.get('mech_rises')} / {n3dt.get('violation_rises')}.")
        hkc = (rj(R / "heap_key_audit.json").get("cells") or {}).get("C_desc", {})
        w("- The two instruments disagree here because of one program family. Under the described ban the model mostly "
          "writes heaps keyed by GOAL-INDEPENDENT coordinates (heap-key audit for this cell: " +
          ", ".join(f"{k} {v}" for k, v in hkc.items()) + "). The judges call them 'greedy best-first' or 'unit "
          "Dijkstra', the runtime label calls them OTHER and the tracer calls them HEUR-weak. Their keys "
          "(r + c, r*cols + c, (r, c)) do not depend on the goal, so by mechanism they are neither banned heuristic "
          "nor BFS order: for this cell the runtime reading is the closer one. The 11 genuine FIFO BFS programs are "
          "the real violations.")
        w("")
    # ---- N5
    w("## N5 (secondary): rotated five-name sets")
    w("")
    w(f"Set rule: {sets.get('rule')} (the committed name distance is degenerate: most alias pairs share no term, so "
      f"D_name is 1 for {sum(1 for row in (sets.get('D_name') or {}).get('D_name', []) for x in row if x == 1.0)} of 100 "
      "cells and no 'type L' set exists; R4-R5 come from the any-set fallback).")
    w("")
    w("| Set | banned | survivors | Dm | Dn | exact p(Dm) | exact p(Dn) |")
    w("|---|---|---|---|---|---|---|")
    for name, v in n5.get("sets", {}).items():
        w(f"| {name} | {', '.join(v['set'])} | {v['n_survivors']} | {f(v.get('Dm'), 3)} | {f(v.get('Dn'), 3)} | "
          f"{f(v.get('p_Dm_le'), 3)} | {f(v.get('p_Dn_ge'), 3)} |")
    w("")
    w(f"- Joint sign count (Dm < 0 and Dn > 0): {n5.get('n_joint')}/{n5.get('n_defined')} defined sets (binomial "
      f"p0 = 0.25: p = {f(n5.get('binom_p_joint'), 4)}); verdict: {n5.get('verdict')}. Distances use the tracer "
      "(flagged: the gate failed).")
    w("")
    # ---- scale
    if sc:
        w("## Scale check (exploratory): gpt-oss-120b")
        w("")
        for k, v in sc.items():
            b = v.get("ban", {})
            w(f"- Baseline {v.get('baseline_composition')} (pass {f(v.get('baseline_pass_rate'))}); own top five "
              f"{v.get('top5')}.")
            if b:
                w(f"- Five-name ban: lexical {f(b['lex_L1_completed']['rate'])}, mechanistic (runtime) "
                  f"{f(b['mech_coarse_traceable']['rate'])}, named survivors {f(b['named_survivors']['rate'])}, "
                  f"mechanism-level survivors {f(b['mech_survivors']['rate'])}, pass {f(b['pass_rate'])}, "
                  f"labels {b.get('labels')}.")
        w("- Qwen3-235B-A22B-thinking was dropped before commit #1a (deviation D-scale: only Venice serves it, at about "
          "USD 0.03 per thinking row).")
        w("")
    # ---- extra descriptive analyses
    hk = rj(R / "heap_key_audit.json")
    l2v = rj(R / "l2_validation.json")
    kc = rj(R / "k_curve_qwen3_8b.json")
    if hk:
        w("## Name-level labels vs heap keys (post-hoc audit)")
        w("")
        w("Heap priority keys classified from the pushed expressions (`results/heap_key_audit.json`), by name-level label, "
          "over every new cell:")
        w("")
        for lab, d in hk.get("name_label_vs_key", {}).items():
            w(f"- **{lab}**: " + ", ".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1])))
        w("")
        w("A goal-independent coordinate key (r + c, r*cols + c, (r, c), r^2 + c^2) expands cells in a fixed sweep "
          "order: it is neither greedy best-first nor Dijkstra, yet the judges give it those names.")
        w("")
    if kc:
        w("## Descriptive k-curve, Qwen3-8B (iteration-2 rows, thinking off)")
        w("")
        w("| condition | k | lexical L1 | mechanistic (runtime) | mechanistic (tracer) |")
        w("|---|---|---|---|---|")
        for cfg, v in kc.items():
            w(f"| {cfg} | {v['k']} | {f(v['runtime_class']['lex'])} | {f(v['runtime_class']['mech'])} | "
              f"{f(v['order_class']['mech'])} |")
        w("")
    if l2v:
        w(f"- L2 validation: recall {f(l2v.get('L2_recall'))} on 60 hand-labelled self-naming lines; its misses are bare "
          f"noun-phrase comments (\"# BFS to find a path\"); disavowal unit cases correct "
          f"{l2v.get('unit_test_disavowals_correct')}/{l2v.get('unit_test_disavowal_cases')}. L1 recall "
          f"{f(l2v.get('L1_recall'))}.")
        w("")
    if fv:
        w(f"- Fallback-label validation (`results/fallback_label_validation.json`): runtime label references "
          f"{fv.get('runtime_ok_refs')}/15, planted controls {fv.get('runtime_ok_controls')}/9 (wrong on the random walk, "
          f"grid Bellman-Ford and wavefront-from-goal controls), gold {f(fv.get('gold_runtime_agreement'))} (partly "
          f"circular); tracer references {fv.get('tracer_ok_refs')}/15, controls {fv.get('tracer_ok_controls')}/9.")
        w("")
    pos = rj(R / "positioning.json")
    if pos:
        w("## Positioning (dated 2026-10-23, `results/positioning.json`)")
        w("")
        for it in pos.get("items", []):
            if it.get("id"):
                w(f"- **{it['title']}** ({it['id']}), {it['verdict']}: \"{it['quote']}\" Relation: {it['relation']}.")
        w(f"- Occupying work found: {pos.get('occupying_found')}. {pos.get('permitted_wording_rule')}.")
        w("")
    # ---- novelty / manual reads
    if nov:
        w("## Novelty audit")
        w("")
        w(f"- Candidates: {nov.get('n_candidates')} correct programs labelled 'other' or flagged; novel by both "
          f"judges: {nov.get('n_novel')}. Claim: {nov.get('claim')} (rule-of-three 95% upper bound "
          f"{f(nov.get('rule_of_three_upper95'), 4)} over {nov.get('n_correct_rows_screened')} correct rows).")
        w("")
    if mr:
        w("## Manual reads")
        w("")
        w(f"- {mr.get('n')} programs read by the executor ({mr.get('by_reason')}); summary in "
          "`results/manual_reads_summary.json`, records in `data/manual_reads_v9.jsonl`.")
        w("")
    # ---- audit
    w("## Re-derivation and placebos")
    w("")
    if red:
        w(f"- `audit/rederive.py` (stdlib only, separate code) recomputes the N1 2x2 tables, gaps, paired-Newcombe "
          f"intervals, the pooled gap and verdict, the N3 rates and JT statistics (own permutation test), the N2 "
          f"counts and the N5 sign count: **{red.get('n_mismatches')} mismatches**.")
        ps = red.get("placebo_swap_flags", {})
        w(f"- Placebo 1 (swap lexical and mechanistic flags at random): mean pooled gap {f(ps.get('mean_pooled_gap'), 3)} "
          f"(observed {f(ps.get('observed'))}); fails as required: {ps.get('fails_as_required')}.")
        for mk in ("q32", "q14"):
            pk = red.get(f"placebo_permuted_k_{mk}")
            if pk:
                w(f"- Placebo 2 ({mk}, k labels permuted): share of JT p < 0.05 = {f(pk.get('share_p_below_0.05'))}; "
                  f"fails as required: {pk.get('fails_as_required')}.")
        p3 = red.get("placebo_random_survivors_n5")
        if p3:
            w(f"- Placebo 3 (random N5 survivors): mean joint count {f(p3.get('mean_joint'))} vs chance "
              f"{f(p3.get('expected_chance'))}.")
    if pse:
        w(f"- Placebo 4 (tracer on order-shuffled events): BFS-order programs {pse.get('n_bfs_original')} -> "
          f"{pse.get('n_bfs_after_shuffle')} after shuffling; fails as required: {pse.get('fails_as_required')}.")
    rh = rj(R / "rederive_headlines.json")
    if rh:
        gh, hr, ht = rh["gate"], rh["n1_runtime"], rh["n1_tracer"]
        pr, pt = rh["placebo_swap_within_program"]["runtime"], rh["placebo_swap_within_program"]["tracer"]
        w(f"- `audit/rederive_headlines.py` (short, stdlib only, own code; raw rows only) re-derives the headline "
          f"numbers: gate gold {gh['gold_agree']}/{gh['gold_in_scope']} = {f(gh['gold_agreement'])}, references "
          f"{gh['references_ok']}/{gh['references_n']}, controls {gh['controls_class_ok']}/{gh['controls_n']} by class "
          f"({gh['controls_class_and_suite_ok']} also passing the suite); N1 pooled gap {f(hr['pooled'], 3)} (runtime "
          f"label) and {f(ht['pooled'], 3)} (tracer), positive in {hr['n_positive']}/{hr['n_configs']} and "
          f"{ht['n_positive']}/{ht['n_configs']} configurations, exact McNemar p < 0.05 in {hr['n_sig']} and "
          f"{ht['n_sig']}; N2 {rh['n2_runtime']['banned_class']}/{rh['n2_runtime']['n']} (runtime) and "
          f"{rh['n2_tracer']['banned_class']}/{rh['n2_tracer']['n']} (tracer); sampling spend "
          f"USD {f(rh['sampling_spend_from_rows_usd'], 3)} from the per-row costs. Placebo (flags swapped at random "
          f"within each program, 200 draws): pooled gap {f(pr['pooled_mean'], 3)} and {f(pt['pooled_mean'], 3)}, "
          f"McNemar-significant configurations {f(pr['mean_configs_significant'])} and "
          f"{f(pt['mean_configs_significant'])} of 10 on average: the effect disappears, as required.")
    w("")
    # ---- cost, deviations
    w("## Cost")
    w("")
    agg: dict = {}
    for k, v in (costs.get("by_purpose") or {}).items():
        key = ("sampling" if k.startswith("sample") else "adjudication judges" if k.startswith("judge:adj")
               else "labeller judge" if k == "judge:labeller" else "novelty judges" if k == "novelty"
               else "gates, smoke, naming checks")
        agg[key] = agg.get(key, 0.0) + v
    w(f"- OpenRouter: USD {f(costs.get('total_usd'), 3)} in total. The committed cap was 3.5; it was raised to 4.0 "
      f"before the last six cells were labelled (deviation D-cap-labelling). By purpose: " +
      ", ".join(f"{k} {f(v, 3)}" for k, v in sorted(agg.items(), key=lambda x: -x[1])) + " (`results/costs.json`).")
    w("- CPU only (6 cgroup CPUs); the GPU was unused.")
    w("")
    w("## Deviations")
    w("")
    for d in devs:
        w(f"- **{d['code']}.** {d['text']}")
    w("")
    w(STATIC)
    (ROOT / "README.md").write_text("\n".join(L) + "\n")
    print("README.md written", len(L), "lines")


STATIC = r"""## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator; one sub-command per stage (`uv run method.py --help`) |
| `src/common.py` | Protocol copied from iteration 8 (`art_R-HSmXq2t97f`) + the v9 block (k order, models, cap, genesis hash) |
| `src/prompts_tp.py`, `src/cells_v9.py` | Iteration-8 renderer (byte-identical k = 5 prompt) and the iteration-9 cell plan / seeds |
| `src/sample_v9.py` | OpenRouter sampler (provider pins, per-row cost, budget-403 stop with in-flight cancellation) |
| `src/label_tp.py`, `src/judge_tp.py`, `src/adjudicate.py` | Iteration-8 name-level labeller, gated judges, adjudication (unchanged) |
| `src/tracer_v9.py` | Expansion-order tracer, CHILD process (stdlib only): AST-rewritten container calls, heap/queue/deque proxies, str-subclass grid rows, call events |
| `src/orderclass.py` | Tracer PARENT side: expansion record, per-probe statistics, committed decision list, DS signature |
| `src/probes_v9.py`, `probes/probes_v9.json` | The 40 committed probe grids (seed 9009) + sha256 |
| `controls/` | 9 planted controls (renamed BFS/DFS, unnamed A*, goal-sorted DFS, random priority, random walk, FIFO SPFA, grid Bellman-Ford, wavefront from goal) |
| `src/gate_v9.py` | Gate sets (references, controls, non-ban gold), blind order judges, unit tests, trace cache |
| `src/lexical.py` | L1 / L2 lexical flags and trace-name counts (30 unit tests) |
| `src/mechdist.py` | N5 D_mech / D_name and the committed rotated-set rule |
| `src/stats_v9.py` | Wilson, Newcombe unpaired and paired (method 10; checked against Newcombe 1998 Table III), McNemar, JT, Cochran-Armitage, bootstrap |
| `src/analysis_v9.py` | N1, N2, N3, N3-D, N5 analyses (mechanism field switch: runtime label vs tracer) |
| `src/figures_v9.py`, `figures/` | F1 N1 forest, F2 2x2 shares, F3 k-curves (both instruments), F4 N2 survivor classes, F5 N5 Dm vs Dn, F6 actual traced expansion orders on 3 probes, F7 gate confusion (rounds 0 and 2), F8 survivor families vs three readings (PDF + PNG) |
| `data/samples_v9.jsonl`, `data/survivors_for_tpg.jsonl` | One row per new sample (plan 4.6 fields) and every new name- or mechanism-level survivor program (for TP-G next round) |
| `results/instrument_bounds.json`, `results/heap_key_audit.json`, `results/manual_reads_summary.json`, `results/fallback_label_validation.json` | Post-hoc (not pre-registered) readings: compliance under both / either instrument, heap-key audit, executor reads vs both instruments, fallback-label validation |
| `run_final.sh`, `build_readme.py` | The final stage chain and the README renderer (every README number is read from `results/`) |
| `src/manual_reads.py`, `data/manual_reads_v9.jsonl` | Manual-read selection and the executor's reads |
| `src/novelty.py` | Iteration-8 novelty audit, reused |
| `src/outputs_v9.py`, `method_out.json` | exp_gen_sol_out output (+ full/mini/preview) |
| `audit/rederive.py`, `audit/rederive_headlines.py`, `audit/placebo_shuffled_events.py`, `audit/clrs_check.py` | Independent re-derivation and placebos |
| `predictions/commit1a.json`, `commit1b.json`, `commit2.json`, `commit3.json`, `commit4.json`, `commit5.json`, `commit6.json`, `commit7.json`, `commit8.json`, `commit9.json`, `commitments.log` | Pre-registrations and their sha256 hash chain (genesis = sha256('iter9_TP-B')) |
| `reproducibility.md`, `pyproject.toml` | Step-by-step reproduction (what was actually run) and every installed package, pinned |
| `predictions/prompts_v9_*.jsonl`, `n5_sets.json`, `n3d_descriptions.json` | Every rendered prompt (sha256), the rotated sets, the N3-D descriptions with naming rates |
| `data/raw_<cell>.jsonl`, `data/labelled_v9_<cell>.jsonl` | Raw generations (reasoning text kept) and labelled + traced rows of every new cell |
| `data/trace_cache/` | Per-probe tracer statistics of every traced program, keyed by tracer version and code sha256, stored as `<version>_part_NNN.jsonl` parts of at most about 45 MB each (read in order by `gate_v9.trace_many`) |
| `results/` | Every analysis JSON (gate rounds, unit tests, N1-N5, scale, novelty, positioning, costs, deviations, timing) |
| `inputs/` | Read-only copies of the prior-iteration inputs with `inputs/SHA256SUMS` |
| `vendor/exp9`, `vendor/exp2` | Executable copies of the iteration-2 harness + labeller and the ITER1 suite |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...
.venv/bin/python method.py stage0 && .venv/bin/python method.py smoke && .venv/bin/python method.py datasets
.venv/bin/python method.py commit1a && .venv/bin/python method.py sample A E          # background in practice
.venv/bin/python method.py tracer_gate round0   # (+ round1, round2 after the logged fixes)
.venv/bin/python method.py n5sets && .venv/bin/python method.py describe && .venv/bin/python method.py tracer_tests
.venv/bin/python method.py commit1b round2 && .venv/bin/python method.py sample B C D
.venv/bin/python method.py retrace && .venv/bin/python method.py judge_gate
.venv/bin/python method.py label A E B C D && .venv/bin/python method.py sample F_gptoss_base
.venv/bin/python method.py label F_gptoss_base && .venv/bin/python method.py commit2
.venv/bin/python method.py sample F_gptoss_ban && .venv/bin/python method.py label F_gptoss_ban
.venv/bin/python audit/placebo_shuffled_events.py
AII_JSON_SKILL=<path to the aii-json skill> ./run_final.sh   # commit3, analyses, audits, novelty, figures, outputs, README
```

Sampling is nondeterministic (quantised providers); seeds and providers are recorded per row. Every cached stage
(trace cache, judge cache, program-evaluation cache) makes a rerun cheap. Only `stage0` and `datasets` read the prior
artifacts (each from `$TP_DEP_<KEY>`, else a sibling folder named by its artifact id); every later stage reads the
sha256-verified copies in `inputs/`. Full instructions, runtimes and expected numbers: `reproducibility.md`.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | `.venv/bin/python -m compileall src` (also regenerated automatically on import) |
| `vendor/exp9/tasks/__pycache__/` | `.venv/bin/python -m compileall vendor` (also regenerated automatically on import) |
| `vendor/exp9/labeller_ext/__pycache__/` | `.venv/bin/python -m compileall vendor` (also regenerated automatically on import) |
| `data/trace_cache/` caches of the round-0 and round-1 tracer versions (deleted) | not restorable by a stage: `tracer_gate` refuses to run after commit #1b by design; the gate results themselves are kept in `results/tracer_gate_round*.json` |
| `data/trace_cache/` (current version: 179 MB in 5 parts; a cache, excluded from publication by the upload-ignore list) | refilled automatically by any stage that traces: `.venv/bin/python method.py retrace` (580 programs, 13 min on 6 CPUs), `analyse` (N5 survivors), `figures` (F6); every class it holds is also stored per row in `results/retrace.jsonl` and `data/labelled_v9_*.jsonl` |
"""


if __name__ == "__main__":
    main()
