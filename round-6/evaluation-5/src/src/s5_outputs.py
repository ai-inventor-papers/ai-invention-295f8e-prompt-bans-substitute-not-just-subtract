"""S5: corrections.json (exact old_text -> new_text against the iteration-6 report), figures, eval_out.json."""

from __future__ import annotations

import difflib
import json
import math
import re
import time
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from common import (REPORT, TASK_NAME, WS, Inputs, bonett_wright_ci, fnum, fp, prov, spearman,  # noqa: E402
                    write_json)
from load import EXISTING, PANEL, PRIMARY13  # noqa: E402

MARK = "[iteration-6 correction]"
FP8_MARK = ("[iteration-6 correction: FP8 W8A8 engine result (RTX 2000 Ada, exp19-exp22); did not replicate in bf16 "
            "at the population level (Table 222)]")


class Corr:
    def __init__(self, report: str) -> None:
        self.rep, self.items = report, []
        self.lines = report.splitlines()

    def add(self, location: str, kind: str, old: str, new: str, prov_: list[str], values: list[dict],
            note: str = "") -> None:
        n = self.rep.count(old)
        match, line = "exact", None
        if n == 1:
            line = self.rep[: self.rep.index(old)].count("\n") + 1
        else:
            best = max(range(len(self.lines)), key=lambda i: difflib.SequenceMatcher(None, self.lines[i], old[:300]).ratio())
            match, line = (f"fuzzy (count {n})", best + 1)
        sts = [v["status"] for v in values]
        st = ("NOT_REPRODUCIBLE" if "NOT_REPRODUCIBLE" in sts else "CORRECTED" if "CORRECTED" in sts else
              "NEW" if sts and all(s == "NEW" for s in sts) else "MATCH" if sts else "NEW")
        self.items.append({"id": f"C6-{len(self.items) + 1:03d}", "location": location, "line": line, "kind": kind,
                           "old_text": old, "new_text": new, "marker": MARK, "provenance": prov_, "values": values,
                           "status": st, "old_text_match": match, "note": note})


def v(name: str, recorded: Any, recomputed: Any, status: str) -> dict:
    return {"name": name, "recorded": recorded, "recomputed": recomputed, "status": status}


def build_corrections(S: dict, A: dict, F: dict, report: str) -> list[dict]:
    C = Corr(report)
    a, b, c, d, e = S["0a"], S["0b"], S["0c"], S["0d"], S["0e"]
    dose = {r["task"]: r for r in a["dose"]["rows"] if "D_rmn" in r}
    con = {(r["task"], r["alpha"]): r for r in a["contrast"]}
    ci = {(r["units"], r["beta"]): r for r in c["ci"]}
    p13 = ci[("primary13", "beta_iter5_committed")]
    p15 = ci[("with_A8_A9_15", "beta_iter5_committed")]
    pw = {(r["generator"], r["n"], r["rho"]): r["power"] for r in c["power"]["rows"]}
    nreq = c["power"]["n_required_power0.8_rho0.5_copula"]
    riv = {(r["units"], r["rival"]): r for r in c["rivals"]}
    rcmp = {(r["units"], r["rival"]): r for r in c["rival_comparison"]}
    tal = b["tallies"]
    unc = b["unconfounded"]
    ev = {(x["set"], x["unit"]): x for x in b["events"]}
    m = F["m_candidates"]["units"]
    # ---------------------------------------------------------------- 0a: Section 4.10 items 2-4 and the movable set
    for item, head in (("2", "2. *A random displacement of the task-specification states changes the algorithm, and changing the plan noise draw under a fixed seed changes it often.*"),
                       ("3", "3. *The site is the task-specification states at early to middle blocks.*"),
                       ("4", "4. *Plan noise is the cheapest knob on some tasks and not on others.*")):
        C.add(f"4.10 Established item {item}", "REPLACE", head, head + " " + FP8_MARK,
              [prov("exp19", "results/alpha_sweep.json"), prov("exp27", "results/cells.json")],
              [v(f"bf16 PN correct off-default share at alpha 2, five decisive tasks", None,
                 {TASK_NAME[t]: con[(t, 2.0)]["bf16_share"] for t in ("T03", "T10", "T2", "T05", "T1")}, "NEW")])
    old = ("names six movable tasks: kth smallest, two sum, find duplicate, connected components, and the grid and "
           "shortest path tasks, the set the price claim froze.")
    C.add("4.2.6 frozen screen paragraph", "REPLACE", old,
          old[:-1] + ", under the 8-bit W8A8 engine and the ban unit; it is a property of that engine, unit and direction "
          "population, not of the tasks alone: under bf16 and the ban-free unit only kth smallest and connected components "
          "escape (Table 196). " + FP8_MARK,
          [prov("exp25", "results/extra_arm_a.json")],
          [v("bf16 escape fraction kth smallest / connected components", "0.250 / 0.125",
             f"{S['units_E']['T03']:.3f} / {S['units_E']['T10']:.3f}", "MATCH")])
    old = "On fresh draws the movable set is kth smallest, two sum, connected components and the two path tasks,"
    C.add("4.9 movability on fresh directions", "REPLACE", old,
          "On fresh draws under the 8-bit engine and the ban unit " + FP8_MARK + " the movable set is kth smallest, two sum, "
          "connected components and the two path tasks,", [prov("exp22", "results/escape.json")], [])
    # ---------------------------------------------------------------- 0c: Ruled out bullet 1 (verdict)
    old = ("- *The movability half: the base repertoire predicts which tasks a nudge moves.* Spearman -0.03 in panel A, "
           "0.21 in panel B and 0.15 pooled over 13 new units, below the disconfirming bound of 0.3; 4 of 10 new units "
           "diverse in the base never moved, and in panel A the runtime merit gap and the twin modal share tracked "
           "movability better than beta. The screen correlation of 0.78 did not transfer to new tasks.")
    r6 = riv[("primary13", "R6_runtime_merit")]
    r7 = riv[("primary13", "R7_twin_modal_share")]
    new = ("- *The movability half: beta is not a strong predictor of which tasks a nudge moves; a moderate relation is "
           f"not excluded at this n* (conditional on bf16 and the ban-free unit). Pooled over 13 new units Spearman is "
           f"{p13['rho']:.2f} (95% interval {p13['bonett_wright_95'][0]:.2f} to {p13['bonett_wright_95'][1]:.2f}, Bonett-Wright; "
           f"BCa bootstrap {p13['boot_bca_95'][0]:.2f} to {p13['boot_bca_95'][1]:.2f}; one-sided permutation p "
           f"{p13['p_one_sided_perm_200k']:.2f}); {p15['rho']:.3f} with the two extension units. At n 13 the power to detect "
           f"rho 0.6 is about {pw[('b', 13, 0.6)]:.2f} (copula on the observed marginals; {pw[('a', 13, 0.6)]:.2f} bivariate "
           f"normal), and about {nreq} units are needed for power 0.8 at rho 0.5. 4 of 10 new units diverse in the base "
           "never moved. With one runtime-merit harness for all 30 units, the re-timed merit tracks movability at "
           f"{r6['rho']:.2f} (one-sided p {r6['p_one_sided_perm']:.3f}) and the twin modal share at {r7['oriented_rho']:.2f} "
           f"(oriented), but neither difference from beta is resolved (paired bootstrap 95% intervals "
           f"{rcmp[('primary13', 'R6_runtime_merit')]['boot_pct95'][0]:.2f} to {rcmp[('primary13', 'R6_runtime_merit')]['boot_pct95'][1]:.2f} "
           f"and {rcmp[('primary13', 'R7_twin_modal_share')]['boot_pct95'][0]:.2f} to {rcmp[('primary13', 'R7_twin_modal_share')]['boot_pct95'][1]:.2f}). "
           "Measured in bf16 with the ban-free unit only. The screen correlation of 0.78 (8-bit engine) did not transfer "
           "to new tasks. " + MARK)
    C.add("5.11 Ruled out bullet 1", "REPLACE", old, new,
          [prov("exp25", "pooled_inputs.json"), prov("exp26", "pooled_inputs.json"), "iter6:tables/movability_ci.csv",
           "iter6:tables/power_sim.csv", "iter6:tables/rivals_harmonised.csv"],
          [v("rho(beta,E) n 13", 0.146, round(p13["rho"], 4), p13["rho_status"]),
           v("one-sided p n 13", 0.315, round(p13["p_one_sided_perm_200k"], 4), p13["p_status"]),
           v("rho n 15", 0.006, round(p15["rho"], 4), p15["rho_status"]),
           v("Bonett-Wright 95% n 13", None, [round(x, 3) for x in p13["bonett_wright_95"]], "NEW"),
           v("power rho 0.6 n 13 (copula)", None, round(pw[("b", 13, 0.6)], 3), "NEW"),
           v("n for power 0.8 at rho 0.5 (copula)", None, nreq, "NEW"),
           v("re-timed runtime merit rho n 13", "panel A -0.88 (other orientation), panel B 0.54", round(r6["rho"], 3), "NEW")])
    old = ("- *The plan sampler comparison: plan noise prices at least as well as text-level plan samplers.* Disconfirmed "
           "(1 of 5 decisive tasks); base intent won on connected components, the shortest path task and two sum.")
    C.add("5.11 Ruled out bullet 4", "REPLACE", old,
          old + " Conditional on bf16 and the ban-free unit: plan noise moved fewer programs in this engine than in "
          "iteration 4's 8-bit engine at a matched dose (Section 5.10). " + MARK,
          [prov("exp27", "results/claim_c.json")], [])
    # ---------------------------------------------------------------- 5.10 paragraph 1 and 2
    old = ("On the 15 existing tasks, with the beta of Step 1 and the escape fractions of iteration 4, Spearman is 0.78 "
           "to 0.79; with this iteration's own bf16 escape fractions it is 0.59; on the new tasks it is -0.03 in panel A, "
           "0.21 in panel B and 0.15 pooled; in Gemma it is 0.42.")
    bwE = S["fig"]["facetA"]
    new = ("Measured within one engine at a time: in bf16 with the ban-free unit, Spearman is "
           f"{bwE['existing']['rho']:.2f} on the 15 existing tasks (95% interval {bwE['existing']['bw'][0]:.2f} to "
           f"{bwE['existing']['bw'][1]:.2f}) and {bwE['new13']['rho']:.2f} on the 13 new units ({bwE['new13']['bw'][0]:.2f} to "
           f"{bwE['new13']['bw'][1]:.2f}); -0.03 in panel A and 0.21 in panel B separately; in Gemma (bf16) 0.42. The "
           "0.78 to 0.79 of the screen pairs Step 1's bf16 beta with iteration 4's 8-bit escape fractions and is not "
           "pooled with the bf16 values (figure fig_beta_escape_bf16, facet B). " + MARK)
    C.add("5.10 paragraph 1", "REPLACE", old, new, [prov("exp25", "results/extra_arm_a.json"), prov("exp22", "results/escape.json")],
          [v("bf16 existing-task Spearman (Step 1 beta)", 0.59, round(bwE["existing"]["rho"], 3),
             "MATCH" if abs(bwE["existing"]["rho"] - 0.59) <= 0.005 else "CORRECTED")])
    old = ("The landing half replicates everywhere it could be measured: the base runner-up named the push landing on 5 "
           "of 5 movable existing tasks (screen), 3 of 3 in panel A, 3 of 4 in panel B and 5 of 7 in Gemma, 16 of 19 "
           "events in all.")
    C.add("5.10 paragraph 1", "DELETE", old, "",
          ["iter6:tables/landing_tally.csv"],
          [v("events in the tally", "16 of 19", f"{tal['ALL21']['hits']} of {tal['ALL21']['n']} (adds the bf16 remeasure: 1 of 2)", "CORRECTED")],
          note="the universal reading is moved to 'Descriptive leads' in 5.11 (C6 INSERT_AFTER item 5)")
    old = ("On the shortest path task, per-sample plan noise moved 26% of programs at alpha 1 in iteration 4 and 0% at "
           "alpha 1 here (4% at alpha 2, about 1.7 ban units).")
    sp1, sp2 = con[("T2", 1.0)], con[("T2", 2.0)]
    C.add("5.10 paragraph 2", "REPLACE", old,
          f"On the shortest path task, per-sample plan noise moved {sp1['fp8_share_correct']:.0%} of programs to a correct "
          f"off-default algorithm at alpha 1 in iteration 4 (26% of attempts, failing programs included) and 0% at alpha 1 "
          f"here ({sp2['bf16_share']:.0%} at alpha 2, {2 * dose['T2']['D_mpr']:.2f} ban units as a mean of per-position "
          f"ratios, {2 * dose['T2']['D_rmn']:.2f} as a ratio of mean norms). " + MARK,
          [prov("exp19", "results/alpha_sweep.json", "T2.sweep"), prov("exp27", "results/cells.json", "T2|PN_a1")],
          [v("iteration-4 shortest path share at alpha 1", 0.26, sp1["fp8_share_attempts_recorded_field"], "MATCH"),
           v("iteration-4 shortest path CORRECT off-default share at alpha 1", 0.26, sp1["fp8_share_correct"], "CORRECTED")],
          note="definition: the record compared FP8 attempt shares with bf16 correct-only shares")
    sf = a["shortfall"]
    dm = {(r["task"], r["alpha_bf16"], r["definition"]): r for r in a["dose_matched"]}
    new = (" The dose does not explain the difference. Two dose definitions are both right: the mean of per-position "
           f"ratios of the ban-free unit to the ban unit is {dose['T10']['D_mpr']:.2f}, {dose['T2']['D_mpr']:.2f}, "
           f"{dose['T05']['D_mpr']:.2f}, {dose['T1']['D_mpr']:.2f} and {dose['T03']['D_mpr']:.2f} on connected components, "
           "shortest path, two sum, grid and kth smallest, and the ratio of mean norms over blocks 12 to 23 is "
           f"{dose['T10']['D_rmn']:.2f}, {dose['T2']['D_rmn']:.2f}, {dose['T05']['D_rmn']:.2f}, {dose['T1']['D_rmn']:.2f} and "
           f"{dose['T03']['D_rmn']:.2f} (Table 174); the ratio of mean norms equals the ban-norm-weighted mean of the "
           "per-block ratios exactly (residual below 1e-6), and the gap between the definitions sits within blocks "
           "(per-position ratios against ratios of block means, which also mixes the bf16 engine's own ban unit), not in the "
           "weighting across blocks. At the bf16 dose expressed in 8-bit ban units, the 8-bit dose-response curve "
           "(correct off-default share, alpha 0 to 4) predicts more escapes than bf16 produced on connected components at "
           f"alpha 2 (exact binomial p {fp(dm[('T10', 2.0, 'D_mpr')]['p_binom_le_x'])} under both definitions), shortest path at "
           f"alpha 1 and 2 (p {fp(dm[('T2', 1.0, 'D_rmn')]['p_binom_le_x'])} and {fp(dm[('T2', 2.0, 'D_rmn')]['p_binom_le_x'])}; "
           f"{fp(dm[('T2', 2.0, 'D_rmn')]['p_binom_conservative'])} at the lower Clopper-Pearson bound) and kth smallest "
           f"(alpha 1, p {fp(dm[('T03', 1.0, 'D_rmn')]['p_binom_le_x'])}), and not on grid or two sum. With correct-only shares "
           f"on both engines the alpha-2 drop is {sf['fold_alpha2_correct_only']['T10']:.0f}-fold on connected components, "
           f"{sf['fold_alpha2_correct_only']['T2']:.0f}-fold on shortest path, {sf['fold_alpha2_correct_only']['T1']:.0f}-fold on "
           f"grid and {sf['fold_alpha2_correct_only']['T03']:.1f}-fold on kth smallest (Fisher p "
           f"{fp(con[('T10', 2.0)]['fisher_p_correct_only'])} and {fp(con[('T2', 2.0)]['fisher_p_correct_only'])} on the first "
           f"two), against a dose shortfall of at most {100 * sf['one_minus_min_D_mpr']:.0f}% (mean of ratios) or "
           f"{100 * sf['one_minus_min_D_rmn']:.0f}% (ratio of means). The cause is not established: engine, GPU, kernel and "
           "sampler streams all differ between the two runs, and Claim E decides it. " + MARK)
    C.add("5.10 paragraph 2", "INSERT_AFTER", "Those two directions therefore do not explain the difference, and its cause is not established here.",
          "Those two directions therefore do not explain the difference, and its cause is not established here." + new,
          [prov("exp27", "data/samples_raw.jsonl", "unit_ratio_banfree_over_ban"), prov("exp27", "data/realised.jsonl", "target_mean"),
           prov("exp19", "data/realised.jsonl", "target_mean"), prov("exp19", "results/alpha_sweep.json"), "iter6:tables/dose_matched.csv"],
          [v(f"D_mpr {t}", dose[t]["D_mpr_recorded"], round(dose[t]["D_mpr"], 4), dose[t]["D_mpr_status"]) for t in ("T10", "T2", "T05", "T1", "T03")]
          + [v(f"D_rmn {t}", dose[t]["D_rmn_recorded_table174"], round(dose[t]["D_rmn"], 4), dose[t]["D_rmn_status"]) for t in ("T10", "T2", "T05", "T1", "T03")]
          + [v("Fisher p alpha 2 connected components (correct-only)", "about 4e-11", con[("T10", 2.0)]["fisher_p_correct_only"], "MATCH"),
             v("Fisher p alpha 2 shortest path", "about 1e-8 (FP8 attempt share)", con[("T2", 2.0)]["fisher_p_correct_only"], "CORRECTED"),
             v("fold drop alpha 2 components / shortest path / grid", "12- to 30-fold",
               [round(sf["fold_alpha2_correct_only"][t], 1) for t in ("T10", "T2", "T1")], "CORRECTED")])
    # Table 222: correct-only iteration-4 column
    rows = "\n".join(f"| {TASK_NAME[t]} | {con[(t, 1.0)]['fp8_share_attempts_recorded_field']:.2f} / {con[(t, 2.0)]['fp8_share_attempts_recorded_field']:.2f} | "
                     f"{con[(t, 1.0)]['fp8_share_correct']:.2f} / {con[(t, 2.0)]['fp8_share_correct']:.2f} | {con[(t, 1.0)]['bf16_share']:.2f} / {con[(t, 2.0)]['bf16_share']:.2f} |"
                     for t in ("T03", "T10", "T2", "T05", "T1"))
    cap = [ln for ln in report.splitlines() if ln.startswith("**Table 222.**")][0]
    C.add("Table 222", "NEW_COLUMN", cap,
          cap + f"\n\n{MARK} The column 'Iteration 4 per-sample plan noise' counts attempts off the default (failing "
          "programs included); the iteration-5 column counts correct programs off the default. On one definition:\n\n"
          "| Task | iteration 4, attempts off default (a1 / a2) | iteration 4, correct off default (a1 / a2) | iteration 5 bf16, correct off default (a1 / a2) |\n|-|-|-|-|\n" + rows,
          [prov("exp19", "results/alpha_sweep.json"), prov("exp27", "results/cells.json")],
          [v(f"iteration-4 {TASK_NAME[t]} a{int(al)}", con[(t, al)]["fp8_share_recorded_in_report"], con[(t, al)]["fp8_share_correct"],
             con[(t, al)]["fp8_status_vs_correct_only"]) for t in ("T03", "T10", "T2", "T05", "T1") for al in (1.0, 2.0)])
    cap = [ln for ln in report.splitlines() if ln.startswith("**Table 174.**")][0]
    rows = "\n".join(f"| {TASK_NAME[t]} | {dose[t]['D_rmn']:.3f} | {dose[t]['D_mpr']:.3f} | {dose[t]['gap_part_within_block']:.3f} | {dose[t]['gap_part_weighting']:.3f} |"
                     for t in ("T1", "T2", "T03", "T05", "T10", "T04", "T06", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6"))
    C.add("Table 174", "NEW_COLUMN", cap,
          cap + f"\n\n{MARK} Both dose definitions from the same logged per-block displacements (exp27 bf16 ban-free unit "
          "over exp19 8-bit ban unit; blocks 12 to 23). The ratio of mean norms is the ban-norm-weighted mean of the per-block "
          "ratios (identity holds to 1e-6); the gap to the mean of per-position ratios is within blocks:\n\n"
          "| Task | ratio of mean norms | mean of per-position ratios (exp27 unit_ratio) | gap within blocks | gap from block weighting |\n|-|-|-|-|-|\n" + rows,
          [prov("exp27", "data/samples_raw.jsonl"), prov("exp27", "data/realised.jsonl"), prov("exp19", "data/realised.jsonl")],
          [v(f"ban-free/ban {TASK_NAME[t]}", dose[t]["D_rmn_recorded_table174"], round(dose[t]["D_rmn"], 4), dose[t]["D_rmn_status"])
           for t in dose] + [v(f"ban unit {TASK_NAME[t]}", dose[t]["ban_unit_table174"], round(dose[t]["ban_unit_mean_norm_exp19"], 3),
                               dose[t]["ban_unit_status"]) for t in dose])
    # ---------------------------------------------------------------- 0b: Established item 2 -> Descriptive leads
    old = ("2. *Where a random nudge moves the instruct model, it lands on the base model's runner-up.* On new tasks the "
           "base runner-up named the push landing in 6 of 7 events (Poisson-binomial p 0.003), with the base composition "
           "ahead of association by 0.75 nats (exact Wilcoxon p 0.055 with the corrected association) and of proximity by "
           "0.50. In Gemma it named 5 of 7 (p 0.025; 1.50 nats over association, p 0.023), and on the existing Qwen3-8B "
           "tasks 5 of 5. In panel A no nudged program landed outside the base repertoire.")
    C.add("5.11 Established item 2", "DELETE", old, "", ["iter6:tables/landing_tally.csv"],
          [v("new-task hits", "6 of 7, p 0.003", f"{tal['QWEN_NEW_A+B']['hits']} of {tal['QWEN_NEW_A+B']['n']}, p {tal['QWEN_NEW_A+B']['p_poisson_binomial']:.4f}", "MATCH")],
          note="MOVE: re-inserted as item 1 of 'Descriptive leads' (next correction)")
    tw = {r["scope"]: r for r in b["twin_rival"]}["ALL21"]
    twl = sum(1 for x in b["events"] if x["hit"] and x["TWIN_WROTE_LANDING"])
    g = {x["unit"]: x for x in b["events"] if x["set"] == "GEMMA"}
    anchor = ("5. *The record repairs.* The held-out movability test is inconclusive under catalogue-only avoidance and "
              "disconfirmed under the drop sensitivity; the read position and condition sentence are inert only at "
              "per-position doses up to 4 ban units; landing comparisons on matched events give push -0.76 against "
              "association -3.11 on 3 events and -1.37 against -3.46 on 5.")
    new = (anchor + "\n\n**Descriptive leads.** " + MARK + "\n\n1. *Where a random nudge moves the instruct model, it "
           "often lands on the base model's runner-up, but the tuned twin had often written that landing already.* Over "
           f"the 21 iteration-5 landing events the base runner-up named the modal landing {tal['ALL21']['hits']} times "
           f"(new Qwen3-8B units {tal['QWEN_NEW_A+B']['hits']} of {tal['QWEN_NEW_A+B']['n']}, Poisson-binomial p "
           f"{tal['QWEN_NEW_A+B']['p_poisson_binomial']:.4f}; Gemma {tal['GEMMA']['hits']} of {tal['GEMMA']['n']}, p "
           f"{tal['GEMMA']['p_poisson_binomial']:.3f}; 8-bit screen 5 of 5; bf16 remeasure 1 of 2; {tal['UNIT_CLUSTERED']['cluster_hits']} of "
           f"{tal['UNIT_CLUSTERED']['n_clusters']} unit clusters). {twl} of the hits are landings the twin had already "
           f"written among its 50 programs, and the twin's own most frequent correct non-default program names the landing "
           f"on {tw['t_u_hits_defined_only']} of the {tw['t_u_defined']} events where it exists, with no event on which the two "
           f"forecasts disagree ({tw['discordant_pairs(r_u!=t_u)']} discordant pairs). On the events whose twin wrote no "
           f"correct non-default program, the base runner-up hits {unc['QWEN_NEW_A+B']['hits']} of {unc['QWEN_NEW_A+B']['n']} "
           f"in Qwen3-8B (p {unc['QWEN_NEW_A+B']['p_poisson_binomial']:.3f}) and {unc['GEMMA']['hits']} of {unc['GEMMA']['n']} in "
           f"Gemma (p {unc['GEMMA']['p_poisson_binomial']:.2f}), {unc['POOLED']['hits']} of {unc['POOLED']['n']} pooled (p "
           f"{unc['POOLED']['p_poisson_binomial']:.3f}), short of 0.05. Gemma's forecasts rest on thin support: its grid runner-up "
           f"comes from {g['T1']['r_u_count_valid']} valid attempts and {g['T1']['r_u_count_correct']} correct programs, kth "
           f"smallest's and connected components' from {g['T03']['r_u_count_valid']} and {g['T10']['r_u_count_valid']} valid "
           "attempts, and its base labels agree with adjudication at 0.64. The base composition is ahead of association by "
           "0.75 nats on new tasks (exact Wilcoxon p 0.055) and 1.50 in Gemma (p 0.023; 1.57 over the 6 events where "
           "association is defined).")
    C.add("5.11 after Established item 5", "INSERT_AFTER", anchor, new,
          [prov("exp25", "results/a2_assoc_corrected.json"), prov("exp26", "results/a2_panel.json"), prov("exp28", "results/e_a2.json"),
           prov("exp24", "results/screen_check.json"), prov("exp25", "results/extra_arm_a.json"), "iter6:tables/landing_events_iter5.csv"],
          [v("all events", "17/21", f"{tal['ALL21']['hits']}/{tal['ALL21']['n']}", tal["ALL21"]["status"]),
           v("unconfounded Qwen", "3/4 p 0.052", f"{unc['QWEN_NEW_A+B']['hits']}/{unc['QWEN_NEW_A+B']['n']} p {unc['QWEN_NEW_A+B']['p_poisson_binomial']:.4f}", unc["QWEN_NEW_A+B"]["status"]),
           v("unconfounded Gemma", "2/4 p 0.42", f"{unc['GEMMA']['hits']}/{unc['GEMMA']['n']} p {unc['GEMMA']['p_poisson_binomial']:.4f}", unc["GEMMA"]["status"]),
           v("unconfounded pooled", "5/8 p 0.053", f"{unc['POOLED']['hits']}/{unc['POOLED']['n']} p {unc['POOLED']['p_poisson_binomial']:.4f}", unc["POOLED"]["status"]),
           v("hits the twin had written", 6, twl, "MATCH" if twl == 6 else "CORRECTED"),
           v("t_u discordant pairs", None, tw["discordant_pairs(r_u!=t_u)"], "NEW")])
    old = ("Its landing half held in both families and on unseen tasks: when a nudge moves the instruct model, it moves it "
           "to the algorithm the base model writes next, and a forecast built from base samples, before any push, names "
           "that landing better than the model's stated alternative.")
    C.add("5.12 paragraph 1", "DELETE", old, "", ["iter6:tables/landing_tally.csv", "iter6:tables/twin_rival.csv"],
          [v("unconfounded pooled p", "(universal claim)", round(unc["POOLED"]["p_poisson_binomial"], 4), "CORRECTED")],
          note="universal sentence; the descriptive version is in 5.11 'Descriptive leads'")
    old = "Where pushes move the model, the base model says where they will land."
    C.add("What we have learned so far, paragraph 4", "REPLACE", old,
          "Where pushes move the model, the base model's runner-up often names where they land, although the tuned twin had "
          "usually written that landing already. " + MARK, [], [])
    old = ("This held on 5 of 5 movable existing tasks, on 6 of 7 events on new tasks (Poisson-binomial p 0.003) and on 5 "
           "of 7 in Gemma (p 0.025), and in panel A no nudged program landed outside the base repertoire.")
    C.add("What we have learned so far, paragraph 4", "REPLACE", old,
          old + f" On the events whose twin wrote no correct non-default program it held on {unc['POOLED']['hits']} of "
          f"{unc['POOLED']['n']} (p {unc['POOLED']['p_poisson_binomial']:.3f}), so the lead is descriptive. " + MARK,
          [], [v("unconfounded pooled", "5/8 p 0.053", f"{unc['POOLED']['hits']}/{unc['POOLED']['n']}", unc["POOLED"]["status"])])
    old = ("A forecast built from base samples, before any push, beats the model's own stated alternative on log score "
           "(by 0.75 nats on new tasks and 1.50 in Gemma).")
    C.add("What we have learned so far, paragraph 4", "REPLACE", old,
          old[:-1] + "; descriptively, with p 0.055 on new tasks and Gemma's base forecasts resting on 4 to 6 valid attempts "
          "for three of its seven events). " + MARK, [], [])
    # support columns for Tables 203, 214, 217
    for tab, setn in (("Table 203", "QWEN_NEW_B"), ("Table 214", "GEMMA"), ("Table 217", "GEMMA")):
        cap = [ln for ln in report.splitlines() if ln.startswith(f"**{tab}.**")][0]
        es = [x for x in b["events"] if x["set"] == setn]
        rows = "\n".join(f"| {x['name']} | {x['r_u']} | {x['base_chat_valid']} / {x['base_chat_correct']} | {x['base_plain_valid']} / "
                         f"{x['base_plain_correct']} | {x['base_pooled_correct']} | {x['r_u_count_valid']} / {x['r_u_count_correct']} | "
                         f"{x['t_u'] or '-'} | {'yes' if x['TWIN_WROTE_LANDING'] else 'no'} |" for x in es)
        C.add(tab, "NEW_COLUMN", cap, cap + f"\n\n{MARK} Support behind each landing forecast:\n\n| Unit | base runner-up | chat valid / correct | "
              "plain valid / correct | pooled correct | runner-up valid / correct | twin minority t_u | twin wrote the landing |\n|-|-|-|-|-|-|-|-|\n" + rows,
              ["iter6:tables/base_support.csv"], [v(f"support {x['unit']}", None, x["base_pooled_correct"], "NEW") for x in es])
    # mixed twins
    mx = {x["unit"]: x for x in b["mixed"]}
    mixed_txt = (f" The instruct twin is not always collapsed: on trapped rain water (default share "
                 f"{mx['A3']['twin_default_share_of_N']:.2f}; correct off-default {mx['A3']['twin_off_default_correct_share_of_N']:.2f} "
                 f"against beta {mx['A3']['beta_iter5']:.2f}), minimum spanning tree weight ({mx['B3']['twin_default_share_of_N']:.2f}; "
                 f"{mx['B3']['twin_off_default_correct_share_of_N']:.2f} against {mx['B3']['beta_iter5']:.2f}) and valid anagram "
                 f"({mx['B6']['twin_default_share_of_N']:.2f}) the tuned model itself writes a second correct algorithm, in two of them "
                 "more often than the base model does, which partly contradicts a uniform narrowing and is in line with reports of "
                 "retained algorithmic diversity on other problems [72]. " + MARK)
    mixed_vals = [v("trapped rain water twin default share", 0.64, round(mx["A3"]["twin_default_share_of_N"], 3), "MATCH" if abs(mx["A3"]["twin_default_share_of_N"] - 0.64) < 0.005 else "CORRECTED"),
                  v("MST twin default share", 0.66, round(mx["B3"]["twin_default_share_of_N"], 3), "MATCH" if abs(mx["B3"]["twin_default_share_of_N"] - 0.66) < 0.005 else "CORRECTED"),
                  v("valid anagram twin default share", 0.76, round(mx["B6"]["twin_default_share_of_N"], 3), "MATCH" if abs(mx["B6"]["twin_default_share_of_N"] - 0.76) < 0.005 else "CORRECTED")]
    for loc, anchor in (("5.4 movability paragraph", "The twin's own modal share reaches -0.70, ahead of beta by a task-bootstrap interval that excludes zero (-1.90 to -0.09)."),
                        ("5.5 landing paragraph", "With fewer than five events no Wilcoxon test was run."),
                        ("5.11 Established item 3", "and every new unit but one had beta of at least 0.05."),
                        ("What we have learned so far, paragraph 4", "(5 of the 15 existing tasks are diverse in the base and 7 intermediate).")):
        C.add(loc, "INSERT_AFTER", anchor, anchor + mixed_txt, ["iter6:tables/mixed_twins.csv"], mixed_vals)
    # Table 205 row with intervals
    old = "| Spearman between beta and the escape fraction | 0.146 (one-sided permutation p 0.315) | 0.006 (p 0.492) |"
    C.add("Table 205", "REPLACE", old,
          f"| Spearman between beta and the escape fraction | {p13['rho']:.3f} (one-sided permutation p {p13['p_one_sided_perm_200k']:.3f}; "
          f"95% interval {p13['bonett_wright_95'][0]:.2f} to {p13['bonett_wright_95'][1]:.2f} Bonett-Wright, {p13['fieller_95'][0]:.2f} to "
          f"{p13['fieller_95'][1]:.2f} Fieller, {p13['boot_bca_95'][0]:.2f} to {p13['boot_bca_95'][1]:.2f} BCa) {MARK} | {p15['rho']:.3f} (p "
          f"{p15['p_one_sided_perm_200k']:.3f}; {p15['bonett_wright_95'][0]:.2f} to {p15['bonett_wright_95'][1]:.2f}) |",
          ["iter6:tables/movability_ci.csv"],
          [v("rho n 13", 0.146, round(p13["rho"], 4), p13["rho_status"]), v("rho n 15", 0.006, round(p15["rho"], 4), p15["rho_status"])])
    # ---------------------------------------------------------------- 0d
    cap = [ln for ln in report.splitlines() if ln.startswith("**Table 206.**")][0]
    ph = d["phrasing"]
    rows = "\n".join(f"| {r['cell']} | {r['theta_0.7']} | {r['theta_0.8']} | {r['theta_0.9']} |" for r in ph)
    C.add("Table 206", "NEW_COLUMN", cap, cap + f"\n\n{MARK} Phrasing clusters per temperature (20 traces per cell; Jaccard "
          "thresholds), with the repeat cell as the noise floor. The rise at theta 0.8 (3 at T 0.7 against 7 at T 1.3) is "
          "within the noise floor of the repeated cell (3 against 6).\n\n| Cell | theta 0.7 | theta 0.8 | theta 0.9 |\n|-|-|-|-|\n" + rows,
          [prov("exp27", "results/literal_cell.json", "per_T.*.phrasing")],
          [v(f"phrasing {r['cell']}", r["recorded"], [r["theta_0.7"], r["theta_0.8"], r["theta_0.9"]], r["status"]) for r in ph])
    pr = {r["task"]: r for r in d["prices"]}
    def pv(x: Any) -> str:
        return "not reached" if x is None else f"{max(x, 0.0):.2f}"
    for tab, ts in (("Table 207", ["T03", "T10", "T2", "T05", "T1"]), ("Table 208", ["T04", "T06", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6"])):
        cap = [ln for ln in report.splitlines() if ln.startswith(f"**{tab}.**")][0]
        rows = "\n".join(f"| {TASK_NAME[t]} | " + " | ".join(f"{pv(pr[t].get(k + '_P15'))} / {pv(pr[t].get(k + '_P20'))}" for k in ("PN", "IFG", "PSL", "EAP", "BINT")) + " |"
                         for t in ts if t in pr)
        C.add(tab, "NEW_COLUMN", cap, cap + f"\n\n{MARK} Price of Hill-1 1.5 and 2 (P15 / P20, pass-point cost as a fraction; "
              "full-simplex hull; bootstrap reach rates in tables/t207_t208_prices.csv):\n\n| Task | plan noise | intent factored "
              "generation | plan search (lite) | enumerate and pick | base intent |\n|-|-|-|-|-|-|\n" + rows,
              [prov("exp27", "results/prices.json"), prov("exp27", "results/bootstrap.json")],
              [v(f"H5 plan noise {TASK_NAME[t]}", pr[t].get("PN_H5_recorded_T207"), round(pr[t]["PN_H5"], 3), pr[t].get("PN_H5_status", "NEW")) for t in ts if t in pr])
    kn = [r for r in d["panelB_knob"]]
    rows = "\n".join(f"| {r['name']} | {r['arm']} | {r['N']} | {r['pass']:.2f} | {r['off_default_share']:.2f} | "
                     + ", ".join(f"{k} {vv}" for k, vv in sorted(r['correct_composition'].items(), key=lambda kv: -kv[1]))
                     + f" | {fnum(r['hill1_rarefied'], 2)} ({r['depth']}) |" for r in kn)
    anchor = "| count inversions | sorted insertion with bisect | sorted insertion with bisect | 1.0 | -2.39 | -3.18 | -1.02 |"
    b3 = {r["arm"]: r for r in kn if r["unit"] == "B3"}
    C.add("after Table 203", "NEW_TABLE", anchor, anchor + f"\n\n**Table 203b.** {MARK} Knob rows of the panel B units: N, pass rate, "
          "correct off-default share, correct composition and correct-only Hill-1 rarefied at depth 25 (depth in brackets when "
          "fewer correct programs). Source: panel B `pooled_inputs.json` (records[].outcomes).\n\n| Unit | arm | N | pass | off-default share | "
          "correct composition | Hill-1 (depth) |\n|-|-|-|-|-|-|-|\n" + rows,
          [prov("exp26", "pooled_inputs.json", "records[].outcomes.twin_cell|pn_cells|t13_cell")],
          [v("MST T1.3 Prim", "18/49", f"{b3['T1.3']['correct_composition'].get('prim_heap')}/{b3['T1.3']['n_correct']}", "MATCH" if b3['T1.3']['correct_composition'].get('prim_heap') == 18 and b3['T1.3']['n_correct'] == 49 else "CORRECTED"),
           v("MST plan noise Prim (alpha 1)", "20/50", f"{b3['PN_a1']['correct_composition'].get('prim_heap')}/{b3['PN_a1']['n_correct']}", "MATCH" if b3['PN_a1']['correct_composition'].get('prim_heap') == 20 else "CORRECTED")])
    rc = d["repertoire_check"]["units"]
    nviol = sum(len(x.get("support_violations") or {}) for x in rc.values())
    viol = [(u, alg, n_) for u, x in rc.items() for alg, n_ in (x.get("support_violations") or {}).items()]
    att = S["panelB_base_attempted"]
    vtxt = "; ".join(f"{TASK_NAME[u]}: {n_} correct nudged {alg} programs, against {att.get(u, {}).get(alg, 0)} valid and 0 "
                     "correct base programs" for u, alg, n_ in viol)
    anchor = "Twelve distinct correct programs labelled other appeared among 10,366 correct programs (7 catalogue variants, 5 degenerate); 0 novel."
    txt = (f" Repertoire check: {nviol} of the {len(rc)} new units has a correct nudged program on an algorithm with no correct "
           f"base program ({vtxt}); the record's statement that no nudged program landed outside the base repertoire holds "
           "for panel A only." if nviol else f" Repertoire check: no correct nudged program landed on an algorithm with no "
           f"correct base program on any of the {len(rc)} new units.")
    C.add("5.5 checks", "INSERT_AFTER", anchor, anchor + txt + " " + MARK,
          [prov("exp26", "results/repertoire_check.json", "units.*.support_violations"),
           prov("exp26", "pooled_inputs.json", "records[].base.attempted_composition")],
          [v("panel B support violations (expected by the plan)", 0, nviol, "MATCH" if nviol == 0 else "CORRECTED")])
    old = "| the other three qualifying cells | not staged in the iteration-5 audit | prompt bans |"
    rows = "\n".join(f"| {r['arm']} (row {r['row_id']}) | {r['H1r25']:.2f} (90% {r['H1r25_ci90']}) | pass cost {r['pass_cost_pts']:.0f} points "
                     f"(95% {r['pass_cost_ci95']}), CI unit {r['ci_unit']}{', flags ' + r['flags'] if r['flags'] else ''} {MARK} |" for r in d["t126c"])
    C.add("Table 126c", "REPLACE", old, rows, [prov("eval3", "tables/knob_table.csv", "K0522-K0524")],
          [v(f"Hill-1 {r['row_id']}", r["recorded_hill"], round(r["H1r25"], 3), r["status"]) for r in d["t126c"]])
    # ---------------------------------------------------------------- 0e
    t211 = {(r["task"], r["alpha"]): r for r in e["t211"]}
    cap = [ln for ln in report.splitlines() if ln.startswith("**Table 211.**")][0]
    rows = "\n".join(f"| {r['task'] if r['task'].startswith('POOLED') else TASK_NAME[r['task']]} | {r['alpha'][-1]} | {r['PN_only']}:{r['DMD_only']} | {fp(r['p_exact_recomputed'])} |"
                     for r in e["t211"])
    C.add("Table 211", "NEW_COLUMN", cap, cap + f"\n\n{MARK} Discordant slots per task (plan noise only : matched departure only, exact "
          "two-sided McNemar):\n\n| Task | alpha | b:c | p |\n|-|-|-|-|\n" + rows,
          [prov("exp27", "results/pn_vs_dmd.json", "per_task")],
          [v("pooled alpha 2", "19:3 p 0.0009", f"{t211[('POOLED_D5', 'alpha2')]['PN_only']}:{t211[('POOLED_D5', 'alpha2')]['DMD_only']} p {t211[('POOLED_D5', 'alpha2')]['p_exact_recomputed']:.4f}", "MATCH"),
           v("kth smallest alpha 2", "13:0", f"{t211[('T03', 'alpha2')]['PN_only']}:{t211[('T03', 'alpha2')]['DMD_only']}", "MATCH"),
           v("other four tasks alpha 2", "6:3", f"{t211[('POOLED_without_T03', 'alpha2')]['PN_only']}:{t211[('POOLED_without_T03', 'alpha2')]['DMD_only']}", "MATCH"),
           v("alpha 1 pooled", "4:3", f"{t211[('POOLED_D5', 'alpha1')]['PN_only']}:{t211[('POOLED_D5', 'alpha1')]['DMD_only']}", "MATCH")])
    old = ("4. *Plan noise's effect is not its token-level departure from the twin.* At alpha 2 it moved 19 slots against 3 "
           "for decoding matched to its per-token KL (exact p 0.0009).")
    C.add("5.11 Established item 4", "REPLACE", old,
          "4. *Plan noise's effect is not its token-level departure from the twin: established on kth smallest at alpha 2 "
          f"(13:0, exact p {t211[('T03', 'alpha2')]['p_exact_recomputed']:.5f}); not resolved on the other four decisive tasks "
          f"(6:3, p {t211[('POOLED_without_T03', 'alpha2')]['p_exact_recomputed']:.2f}) or at alpha 1 (4:3).* The pooled 19:3 "
          "(exact p 0.0009) is carried by one task. " + MARK, [prov("exp27", "results/pn_vs_dmd.json")], [])
    gf = e["gemma_fill"]
    anchor = ("the pt composition beats iteration 4's association forecast by 1.50 nats per event (exact Wilcoxon p 0.023) and "
              "AST proximity by 0.51 (Table 217).")
    C.add("5.8", "INSERT_AFTER", anchor, anchor + f" Fill rule: the one event without a defined association forecast (first and "
          f"last position) is scored as uniform over its survivors; over the {gf[1]['n']} events where association is defined the "
          f"margin is {gf[1]['mean']:.2f} nats (exact one-sided Wilcoxon p {gf[1]['wilcoxon_exact_p_one_sided']:.3f}). " + MARK,
          [prov("exp28", "results/e_a2.json", "log_scores")],
          [v("mean, all 7", 1.50, round(gf[0]["mean"], 4), gf[0]["status"]), v("Wilcoxon p, all 7", 0.023, round(gf[0]["wilcoxon_exact_p_one_sided"], 4), "MATCH"),
           v("mean, defined only", 1.57, round(gf[1]["mean"], 4), gf[1]["status"]), v("Wilcoxon p, defined only", None, round(gf[1]["wilcoxon_exact_p_one_sided"], 4), "NEW")])
    adj = A
    pj = adj["metrics"].get("per_judge_descriptive", {})
    jtxt = "; ".join(f"{k.split('/')[-1]} {vv['gate']['controls_correct']} of 8 controls, {vv['novel_items']} of 14 novel" for k, vv in pj.items())
    old = ("| Transplant experiment | all arms, base model included | 48 | 27 known techniques outside the frozen catalogue, "
           "12 degenerate, 9 catalogue variants (judges called 14 novel) | 0 |")
    C.add("Table 223", "REPLACE", old,
          "| Transplant experiment | all arms, base model included | 48 | 27 known techniques outside the frozen catalogue, 12 "
          "degenerate, 9 catalogue variants (judges called 14 novel; a third-family blind adjudication with 8 controls did not "
          f"complete under its frozen gate of 6 of 8 controls: {jtxt}) {MARK} | 0 (judges 14 of 48, manual 0) |",
          ["iter6:results/adjudication.json", prov("exp24", "results/novelty_audit.json")],
          [v("third-family novel count", None, {k: vv["novel_items"] for k, vv in pj.items()}, "NEW"),
           v("adjudication outcome", None, adj["outcome_status"], "NEW")])
    # runtime merit leads (5.4 and 5.12)
    def mm(u: str) -> str:
        x = m[u]["runtime_merit"]
        return f"{2 ** x:.1f}x" if x is not None else "n/a"
    old = ("In panel A the three units that moved had an alternative at least twice as fast as the default and the three "
           "that did not had none, although median of two sorted lists broke the pattern.")
    C.add("5.12 paragraph 2", "REPLACE", old,
          "In panel A the three units that moved had an alternative at least twice as fast as the default; re-timed with one "
          f"harness for all 30 units (fastest correct alternative over default: majority element {mm('A1')}, trapped rain water "
          f"{mm('A3')}, longest mirrored substring {mm('A7')}), the immovable longest common prefix ({mm('A5')}) and median of two "
          f"sorted lists ({mm('A9')}) also have one, so the pattern holds in rank (Spearman {r6['rho']:.2f} over 13 new units) but "
          "not as a rule. " + MARK, ["iter6:tables/rivals_retimed.csv", "iter6:frozen/m_candidates.json"],
          [v("runtime merit A5 (fastest alternative speed-up)", "none at least 2x", mm("A5"), "CORRECTED"),
           v("runtime merit A9", "breaks the pattern", mm("A9"), "MATCH")])
    anchor = ("the extension unit median of two sorted lists breaks this (ratio 0.11, never escapes), and with it the rival "
              "falls to -0.66.")
    C.add("5.4 movability paragraph", "INSERT_AFTER", anchor, anchor + " Re-timed with one harness for all units (single-threaded "
          "fresh interpreters, 5 to 9 repeats, stress cases), longest common prefix also has an alternative about "
          f"{mm('A5')} faster than the default and never escapes. " + MARK, ["iter6:tables/rivals_retimed.csv"],
          [v("A5 fastest alternative speed-up", "ratio 0.86 to 4.35 group (none twice as fast)", mm("A5"), "CORRECTED")])
    # kth smallest bf16 landing has no clear mode
    k3 = ev[("QWEN_BF16_REMEASURE", "T03")]
    srt = sorted(k3["landing_counts"].items(), key=lambda kv: -kv[1])
    anchor = "Step 1 runner-up quickselect, landing size-k heap)."
    C.add("5.4 existing tasks paragraph", "INSERT_AFTER", anchor, anchor + f" The kth smallest landing has no clear mode under the "
          f"15-point rule ({', '.join(f'{k} {vv}' for k, vv in srt)} of {sum(k3['landing_counts'].values())} correct off-default programs in "
          f"confirmed cells; lead {k3['lead']:.2f}), and per-sample plan noise in the knob experiment lands on quickselect "
          f"in {S['kth_q'][0]} of its {S['kth_q'][1]} correct off-default programs at alpha 2. " + MARK, [prov("exp25", "results/extra_arm_a.json", "T03.cells"), prov("exp27", "results/cells.json", "T03|PN_a2")],
          [v("kth smallest bf16 landing lead", None, round(k3["lead"], 3), "NEW")])
    return C.items


def movable_scan(report: str, corr: list[dict]) -> list[dict]:
    """M-0a.4: every sentence of Sections 4.x and 5.x that mentions the screen's movable set, with a decision.
    Corrections are added only where a summary treats the 8-bit movable set as a task property (4.10, 4.11, the 4.6
    summary sentence) and for the cross-engine screen check of 5.3; Section 4 is 8-bit throughout (4.10 preamble)."""
    lines = report.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("# Iteration 4"))
    it5 = next(i for i, ln in enumerate(lines) if ln.startswith("# Iteration 5"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("# What we have learned so far"))
    s410 = next(i for i, ln in enumerate(lines) if ln.startswith("## 4.10 "))
    qual = ("8-bit", "FP8", "bf16", "engine", "ban unit", "ban-free", "W8A8", "[iteration-6 correction")
    spans = []
    for c in corr:
        k = report.find(c["old_text"])
        if k >= 0:
            spans.append((k, k + len(c["old_text"])))
    found, out = [], []
    for i in range(start, end):
        ln = lines[i]
        if ln.startswith("|") or "movable" not in ln.replace("immovable", ""):
            continue
        for sent in [x.strip() for x in ln.replace("? ", ". ").split(". ") if "movable" in x.replace("immovable", "")]:
            sent = sent if sent.endswith(".") else sent + "."
            if not ("screen" in sent or "six" in sent or "movable set" in sent or "movable tasks" in sent or "movable task" in sent):
                continue
            k = report.find(sent)
            overl = k >= 0 and any(a < k + len(sent) and k < b for a, b in spans)
            unq = not any(q in sent for q in qual)
            if overl:
                dec = "already corrected (overlaps an earlier correction)"
            elif not unq:
                dec = "already names its engine or unit"
            elif i >= it5 and "screen check" in sent:
                dec = "corrected: cross-engine screen check"
            elif i >= it5:
                dec = "not applicable: iteration-5 sentence about bf16 measurements"
            elif s410 <= i < it5 or "the five movable tasks have avoidance" in sent:
                dec = "corrected: summary treats the 8-bit movable set as a task property"
            else:
                dec = "context: Section 4 reports the 8-bit engine throughout (4.10 preamble); no change"
            found.append({"line": i + 1, "sentence": sent[:400], "unqualified": unq, "unique": report.count(sent) == 1,
                          "decision": dec})
            if dec.startswith("corrected") and report.count(sent) == 1:
                tail = (" [iteration-6 correction: cross-engine; beta from the bf16 base repertoire against escape fractions "
                        "measured under the 8-bit W8A8 engine and the ban unit (exp19-exp22); in bf16 with the ban-free unit "
                        "the same beta gives 0.59 on these tasks (Table 196)]" if "screen check" in sent else
                        " [iteration-6 correction: movable under the 8-bit W8A8 engine and the ban unit (exp19-exp22); in "
                        "bf16 with the ban-free unit only kth smallest and connected components escape (Table 196)]")
                out.append({"id": None, "location": f"line {i + 1} (M-0a.4 scan)", "line": i + 1, "kind": "INSERT_AFTER",
                            "old_text": sent, "new_text": sent + tail, "marker": MARK,
                            "provenance": [prov("exp25", "results/extra_arm_a.json"), prov("exp22", "results/escape.json")],
                            "values": [], "status": "NEW", "old_text_match": "exact",
                            "note": "M-0a.4 scan: " + dec})
                spans.append((k, k + len(sent)))
    write_json(WS / "results" / "movable_sentence_scan.json", found)
    for k, c in enumerate(out):
        c["id"] = f"C6-{len(corr) + k + 1:03d}"
    return out


# ============================================================================================= figures
def fig_beta_escape(S: dict, F: dict, inp: Inputs) -> dict:
    m = F["m_candidates"]["units"]
    esc = inp.json("exp22", "results/escape.json")
    scr = inp.json("exp24", "results/screen_check.json")
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=False)
    out = {}
    ex = [(m[u]["beta_iter5_committed"], m[u]["E_u"]) for u in EXISTING]
    nw = [(m[u]["beta_iter5_committed"], m[u]["E_u"]) for u in PRIMARY13]
    ext = [(m[u]["beta_iter5_committed"], m[u]["E_u"]) for u in ("A8", "A9")]
    for name, pts in (("existing", ex), ("new13", nw)):
        r = spearman([p[0] for p in pts], [p[1] for p in pts])
        out[name] = {"rho": r, "bw": list(bonett_wright_ci(r, len(pts))), "n": len(pts)}
    ax[0].scatter([p[0] for p in ex], [p[1] for p in ex], marker="o", color="#2b6cb0", label=f"15 existing tasks (rho {out['existing']['rho']:.2f} [{out['existing']['bw'][0]:.2f}, {out['existing']['bw'][1]:.2f}])", zorder=3)
    ax[0].scatter([p[0] for p in nw], [p[1] for p in nw], marker="^", color="#c05621", label=f"13 new units (rho {out['new13']['rho']:.2f} [{out['new13']['bw'][0]:.2f}, {out['new13']['bw'][1]:.2f}])", zorder=3)
    ax[0].scatter([p[0] for p in ext], [p[1] for p in ext], marker="^", facecolors="none", edgecolors="#c05621", label="A8/A9 extension", zorder=3)
    ax[0].set_title("A. bf16, ban-free unit (iteration 5)")
    ax[0].set_xlabel("beta (base correct-only off-default share; iteration-5 committed)")
    ax[0].set_ylabel("escape fraction E_u (8 directions, alpha 1-2)")
    ax[0].legend(fontsize=7, loc="upper left", frameon=False)
    screen_mv = set(inp.json("eval3", "screen.json")["movable_tasks"])  # the frozen screen's verdicts
    xs, ys, mv = [], [], []
    for t in EXISTING:
        e = esc[t]["E_t"]
        xs.append(m[t]["beta_iter5_committed"])
        ys.append((e["1.0"]["E_t"] + e["2.0"]["E_t"]) / 2)
        mv.append(t in screen_mv)
    rB = scr["alpha_mean"]["spearman"]
    ax[1].scatter([x for x, k in zip(xs, mv) if k], [y for y, k in zip(ys, mv) if k], marker="s", color="#2f855a", label="frozen screen: movable", zorder=3)
    ax[1].scatter([x for x, k in zip(xs, mv) if not k], [y for y, k in zip(ys, mv) if not k], marker="s", facecolors="none", edgecolors="#2f855a", label="frozen screen: immovable", zorder=3)
    ax[1].set_title("B. 8-bit W8A8, bench unit (iteration 4; not pooled)")
    ax[1].set_xlabel("beta (same committed values)")
    ax[1].set_ylabel("escape fraction, 40 fresh directions (mean of alpha 1, 2)")
    ax[1].legend(fontsize=7, loc="upper left", frameon=False, title=f"rho {rB:.2f} (screen check)", title_fontsize=7)
    for a_ in ax:
        a_.grid(alpha=0.25)
    fig.tight_layout()
    (WS / "figures").mkdir(exist_ok=True)
    for ext_ in ("pdf", "png"):
        fig.savefig(WS / "figures" / f"fig_beta_escape_bf16.{ext_}", dpi=200)
    plt.close(fig)
    return out


def fig_dose(S: dict) -> None:
    cur = S["0a"]["dose"]["curves"]
    fig, ax = plt.subplots(1, 5, figsize=(12, 2.8), sharey=True)
    for i, t in enumerate(("T10", "T2", "T05", "T1", "T03")):
        c = cur[t]
        bl = [int(x) for x in c["blocks"]]
        ax[i].plot(bl, c["r_rmn"], "o-", ms=3, label="ratio of block means (bf16 / 8-bit ban unit)")
        if all(x is not None for x in c["r_mpr"]):
            ax[i].plot(bl, c["r_mpr"], "s--", ms=3, label="mean of per-position ratios (exp27)")
        ax[i].axhline(1, color="grey", lw=0.6)
        ax[i].set_title(TASK_NAME[t], fontsize=9)
        ax[i].set_xlabel("block")
    ax[0].set_ylabel("ban-free unit / ban unit")
    ax[0].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    for ext_ in ("pdf", "png"):
        fig.savefig(WS / "figures" / f"fig_dose_reconciliation.{ext_}", dpi=200)
    plt.close(fig)


def fig_power(S: dict) -> None:
    rows = S["0c"]["power"]["rows"]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for gen, ls in (("a", "--"), ("b", "-")):
        for rho, col in ((0.3, "#718096"), (0.5, "#2b6cb0"), (0.6, "#c05621")):
            pts = sorted((r["n"], r["power"]) for r in rows if r["generator"] == gen and r["rho"] == rho)
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, marker="o", ms=3, color=col,
                        label=f"rho {rho}, {'bivariate normal' if gen == 'a' else 'copula, observed marginals'}")
    ax.axhline(0.8, color="black", lw=0.6)
    ax.axvline(13, color="grey", lw=0.6, ls=":")
    ax.set_xlabel("units n")
    ax.set_ylabel("power (one-sided 0.05, Spearman)")
    ax.legend(fontsize=6, frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    for ext_ in ("pdf", "png"):
        fig.savefig(WS / "figures" / f"fig_power.{ext_}", dpi=200)
    plt.close(fig)


# ============================================================================================= eval_out
def num(x: Any) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def build_eval_out(S: dict, A: dict, F: dict, corr: list[dict], audit: dict | None, timings: dict) -> dict:
    a, b, c, d, e = S["0a"], S["0b"], S["0c"], S["0d"], S["0e"]
    M: dict[str, float] = {}

    def put(k: str, x: Any) -> None:
        f = num(x)
        if f is not None:
            M[re.sub(r"[^A-Za-z0-9_]", "_", k.replace("+", "plus"))] = f
    st = [x["status"] for x in corr]
    put("n_corrections", len(corr))
    for s_ in ("MATCH", "CORRECTED", "NEW", "NOT_REPRODUCIBLE"):
        put(f"n_corrections_{s_.lower()}", st.count(s_))
    vals = [vv for x in corr for vv in x["values"]]
    for s_ in ("MATCH", "CORRECTED", "NEW", "NOT_REPRODUCIBLE"):
        put(f"n_values_{s_.lower()}", sum(1 for vv in vals if vv["status"] == s_))
    put("n_old_text_fuzzy", sum(1 for x in corr if x["old_text_match"] != "exact"))
    for r in a["dose"]["rows"]:
        if "D_rmn" in r:
            put(f"dose_D_mpr_{r['task']}", r["D_mpr"])
            put(f"dose_D_rmn_{r['task']}", r["D_rmn"])
    put("dose_identity_max_abs_residual", max(abs(r["identity_residual"]) for r in a["dose"]["rows"] if "D_rmn" in r))
    for r in a["contrast"]:
        k = f"{r['task']}_a{int(r['alpha'])}"
        put(f"engine_bf16_share_{k}", r["bf16_share"])
        put(f"engine_fp8_correct_share_{k}", r["fp8_share_correct"])
        put(f"engine_fp8_attempt_share_{k}", r["fp8_share_attempts_recorded_field"])
        put(f"engine_fisher_p_correct_only_{k}", r["fisher_p_correct_only"])
        put(f"engine_fold_correct_only_{k}", r["fold_fp8_over_bf16_haldane"])
    for r in a["dose_matched"]:
        if r["definition"] in ("D_mpr", "D_rmn"):
            put(f"dose_matched_p_{r['task']}_a{int(r['alpha_bf16'])}_{r['definition']}", r["p_binom_le_x"])
            put(f"dose_matched_p_conservative_{r['task']}_a{int(r['alpha_bf16'])}_{r['definition']}", r["p_binom_conservative"])
    put("dose_shortfall_max_mpr", a["shortfall"]["one_minus_min_D_mpr"])
    put("dose_shortfall_max_rmn", a["shortfall"]["one_minus_min_D_rmn"])
    for k, t in b["tallies"].items():
        put(f"landing_hits_{k}", t.get("hits", t.get("cluster_hits")))
        put(f"landing_n_{k}", t.get("n", t.get("n_clusters")))
        put(f"landing_p_{k}", t.get("p_poisson_binomial", t.get("p_cluster_mc")))
    for k, t in b["unconfounded"].items():
        put(f"unconfounded_hits_{k}", t["hits"])
        put(f"unconfounded_n_{k}", t["n"])
        put(f"unconfounded_p_{k}", t["p_poisson_binomial"])
    tw = {r["scope"]: r for r in b["twin_rival"]}["ALL21"]
    put("twin_rival_defined", tw["t_u_defined"])
    put("twin_rival_hits_defined", tw["t_u_hits_defined_only"])
    put("twin_rival_discordant_pairs", tw["discordant_pairs(r_u!=t_u)"])
    put("hits_twin_already_wrote", sum(1 for x in b["events"] if x["hit"] and x["TWIN_WROTE_LANDING"]))
    for r in c["ci"]:
        k = f"{r['units']}_{'committed' if r['beta'] == 'beta_iter5_committed' else 'v6'}"
        put(f"movability_rho_{k}", r["rho"])
        put(f"movability_p_{k}", r["p_one_sided_perm_200k"])
        put(f"movability_bw_lo_{k}", r["bonett_wright_95"][0])
        put(f"movability_bw_hi_{k}", r["bonett_wright_95"][1])
        put(f"movability_fieller_lo_{k}", r["fieller_95"][0])
        put(f"movability_fieller_hi_{k}", r["fieller_95"][1])
        put(f"movability_bca_lo_{k}", r["boot_bca_95"][0])
        put(f"movability_bca_hi_{k}", r["boot_bca_95"][1])
    for r in c["power"]["rows"]:
        put(f"power_{r['generator']}_n{r['n']}_rho{str(r['rho']).replace('.', 'p')}", r["power"])
    put("power_n_required_0p8_rho0p5_copula", c["power"]["n_required_power0.8_rho0.5_copula"])
    for r in c["rivals"]:
        put(f"rival_rho_{r['units']}_{r['rival']}", r["rho"])
        put(f"rival_p_{r['units']}_{r['rival']}", r["p_one_sided_perm"])
    for r in c["rival_comparison"]:
        put(f"rival_delta_{r['units']}_{r['rival']}", r["delta_oriented_rival_minus_beta"])
    for sname, dd in F["m_candidates"]["screen_ranking"].items():
        for cand, vv in dd.items():
            put(f"screen_{sname}_{cand}_stat", vv.get("rho", vv.get("auc_E_class1_over_0")))
            put(f"screen_{sname}_{cand}_p", vv["p_one_sided_perm"])
    put("l3_pooled_logscore_q_base_gamma", F["l3_screen"]["pooled_mean_heldout_logscore"]["q_base_gamma"])
    put("l3_pooled_logscore_uniform", F["l3_screen"]["pooled_mean_heldout_logscore"]["uniform"])
    put("l3_pooled_logscore_association", F["l3_screen"]["pooled_mean_heldout_logscore"]["association"])
    put("l3_pooled_logscore_q_tail", F["l3_screen"]["pooled_mean_heldout_logscore"]["q_tail"])
    ph = d["phrasing"][-1]
    put("phrasing_noise_floor_theta0p8", ph["theta_0.8"])
    for r in e["t211"]:
        put(f"t211_{r['task']}_{r['alpha']}_pn_only", r["PN_only"])
        put(f"t211_{r['task']}_{r['alpha']}_dmd_only", r["DMD_only"])
    put("gemma_fill_mean_all7", e["gemma_fill"][0]["mean"])
    put("gemma_fill_p_all7", e["gemma_fill"][0]["wilcoxon_exact_p_one_sided"])
    put("gemma_fill_mean_defined6", e["gemma_fill"][1]["mean"])
    put("gemma_fill_p_defined6", e["gemma_fill"][1]["wilcoxon_exact_p_one_sided"])
    am = A["metrics"]
    cost = json.loads((WS / "results" / "costs.json").read_text()) if (WS / "results" / "costs.json").exists() else \
        {"openrouter_usd_total": am["cost_usd"], "calls_total": am["calls"]}
    put("adjudication_cost_usd_total", cost["openrouter_usd_total"])
    put("adjudication_paid_calls_total", cost["calls_total"])
    put("adjudication_completed", 0 if A["outcome_status"] == "NOT_COMPLETED" else 1)
    for k, vv in (am.get("per_judge_descriptive") or {}).items():
        kk = k.split("/")[-1].replace("-", "_").replace(".", "p")
        put(f"adjudication_{kk}_controls_correct", vv["gate"]["controls_correct"])
        put(f"adjudication_{kk}_novel_items", vv["novel_items"])
        put(f"adjudication_{kk}_binary_ac1", vv["binary_ac1"])
        put(f"adjudication_{kk}_five_class_agreement", vv["five_class_agreement"])
    if audit:
        put("audit_n_checks", audit["n_checks"])
        put("audit_n_mismatches", audit["n_mismatches"])
        put("audit_placebos_failing_as_required", audit["placebos_failing"])
        put("audit_chain_ok", 1 if audit["chain_ok"] else 0)
        put("audit_frozen_predate_s3", 1 if audit["frozen_predate_s3"] else 0)
    for k, vv in timings.items():
        put(f"timing_{k}_s", vv)
    # datasets
    ds_corr = [{"input": f"{x['id']} {x['kind']} at {x['location']} (report line {x['line']}): {x['old_text'][:4000]}",
                "output": x["new_text"][:6000] if x["new_text"] else "(deleted)",
                "metadata_kind": x["kind"], "metadata_status": x["status"], "metadata_location": x["location"],
                "metadata_old_text_match": x["old_text_match"], "metadata_provenance": x["provenance"],
                "metadata_values": x["values"], "predict_status": x["status"],
                "eval_n_values": len(x["values"]), "eval_n_values_corrected": sum(1 for vv in x["values"] if vv["status"] == "CORRECTED")}
               for x in corr]
    ds_land = []
    for x in b["events"]:
        row = {"input": f"{x['set']} | {x['unit']} ({x['name']}) | nudge: {x['nudge']} | survivors: {', '.join(x['S'])}",
               "output": str(x["landing"]), "predict_base_runner_up": str(x["r_u"]), "predict_twin_minority": str(x["t_u"] or ""),
               "metadata_set": x["set"], "metadata_landing_counts": x["landing_counts"], "metadata_twin_correct": x["twin_correct"],
               "metadata_support": {k: x[k] for k in ("base_chat_valid", "base_chat_correct", "base_plain_valid", "base_plain_correct",
                                                      "base_pooled_correct", "r_u_count_valid", "r_u_count_correct")},
               "metadata_src": x["src"], "eval_hit_base_runner_up": float(x["hit"]), "eval_hit_twin_minority": float(x["t_u_hit"]),
               "eval_chance": float(x["chance"]), "eval_twin_wrote_landing": float(x["TWIN_WROTE_LANDING"])}
        if not math.isnan(x["lead"]):
            row["eval_lead"] = float(x["lead"])
        ds_land.append(row)
    ds_m = []
    for u, x in F["m_candidates"]["units"].items():
        row = {"input": f"unit {u} ({TASK_NAME[u]}), set {x['set']}, default {x['default']}", "output": f"E_u={x['E_u']}",
               "metadata_values": {k: x[k] for k in ("beta_v6", "beta_iter5_committed", "replacement_class", "runtime_merit",
                                                     "twin_modal_share_correct", "K", "LOW_SUPPORT", "E_u")},
               "metadata_merit_detail": x["runtime_merit_detail"], "predict_replacement_class": str(x["replacement_class"])}
        for k in ("beta_v6", "beta_iter5_committed", "runtime_merit", "twin_modal_share_correct", "K", "E_u"):
            f = num(x[k])
            if f is not None:
                row[f"eval_{k}"] = f
        ds_m.append(row)
    ds_adj = []
    for x in A["entries"]:
        row = {"input": f"{x['id']} ({x['kind']}, task {x['task']}):\n{x['code'][:3000]}",
               "output": str(x["expect"] or x["manual_class"]), "metadata_kind": x["kind"],
               "metadata_exp24_judges": x["exp24_judges"], "metadata_nearest_known": x["nearest_known"]}
        for mname, lab in (x.get("pass1_by_judge") or {}).items():
            kk = mname.split("/")[-1].replace("-", "_").replace(".", "p")
            row[f"predict_{kk}"] = str((lab or {}).get("class", "NOT_JUDGED"))
            row[f"eval_{kk}_novel"] = float((lab or {}).get("class") == "NOVEL_ALGORITHM")
        ds_adj.append(row)
    meta = {"evaluation_name": "iteration-6 Step 0: repair the record, freeze the inputs",
            "description": "CPU-only record audit of the iteration-5 review's must-fix items with exact old_text -> new_text "
                           "corrections, a hash-chained freeze of iteration 6's screen inputs, a third-family blind "
                           "adjudication and an independent stdlib re-derivation with placebos",
            "sections": {"0a_engine": {"shortfall": a["shortfall"], "contrast": a["contrast"], "dose_rows": a["dose"]["rows"]},
                         "0b_landing": {"tallies": b["tallies"], "unconfounded": b["unconfounded"], "twin_rival": b["twin_rival"],
                                        "kth_pn_note": b["kth_pn_note"]},
                         "0c_movability": {"ci": c["ci"], "power_n_required": c["power"]["n_required_power0.8_rho0.5_copula"],
                                           "rivals": c["rivals"], "rival_comparison": c["rival_comparison"]},
                         "0d_missing": {"phrasing": d["phrasing"], "t126c": d["t126c"]},
                         "0e_minor": {"gemma_fill": e["gemma_fill"]},
                         "0f_frozen": {"files": F["hashes"], "chain": F["chain"]},
                         "adjudication": {"outcome": A["outcome"], "status": A["outcome_status"], "metrics": A["metrics"]}},
            "hypothesis_text_discrepancies": S["discrepancies"], "deviations": S["deviations"],
            "costs": json.loads((WS / "results" / "costs.json").read_text()) if (WS / "results" / "costs.json").exists() else
                     {"openrouter_usd": A["metrics"]["cost_usd"], "calls": A["metrics"]["calls"]},
            "timings_s": timings, "engines": "no model run; all rows read from exp19/exp22 (FP8 W8A8, RTX 2000 Ada) and "
                                             "exp24-exp28 (bf16, RTX 4090 / L4) files, kept apart in every table"}
    return {"metadata": meta, "metrics_agg": M,
            "datasets": [{"dataset": "corrections", "examples": ds_corr}, {"dataset": "landing_events", "examples": ds_land},
                         {"dataset": "m_candidates", "examples": ds_m}, {"dataset": "adjudication", "examples": ds_adj}]}


def discrepancies(S: dict, F: dict) -> list[dict]:
    a, c = S["0a"], S["0c"]
    con = {(r["task"], r["alpha"]): r for r in a["contrast"]}
    pw = {(r["generator"], r["n"], r["rho"]): r["power"] for r in c["power"]["rows"]}
    pat = F["m_candidates"]["replacement_pattern"]["beta_iter5_committed"]
    dose = {r["task"]: r for r in a["dose"]["rows"] if "D_rmn" in r}
    sf = a["shortfall"]
    return [
        {"quote": "3 of the 6 base-diverse immovable new units against 1 of the 7 movable (replacement class)",
         "recomputed": f"{pat['replacement_in_diverse_immovable']} of {len(pat['diverse_immovable'])} against {pat['replacement_in_movable']} of {len(pat['movable'])} (Fisher p {pat['fisher_p_two_sided']:.3f}) with the v6 definition (base modal correct algorithm over chat and plain pooled); the quoted 3 of 6 against 1 of 7 reproduces with the chat-only composition, where single number's base modal correct algorithm is XOR fold (pooled, it is the hash count default)"},
        {"quote": "12- to 30-fold drop at alpha 2 on components, shortest path and grid",
         "recomputed": f"correct-only on both engines: {sf['fold_alpha2_correct_only']['T10']:.1f}x, {sf['fold_alpha2_correct_only']['T2']:.1f}x, {sf['fold_alpha2_correct_only']['T1']:.1f}x; with FP8 attempt shares (the record's mixed definition) {sf['fold_alpha2_attempt_shares']['T10']:.1f}x, {sf['fold_alpha2_attempt_shares']['T2']:.1f}x, {sf['fold_alpha2_attempt_shares']['T1']:.1f}x"},
        {"quote": "Fisher at alpha 2: shortest path about 1e-8",
         "recomputed": f"{con[('T2', 2.0)]['fisher_p_correct_only']:.2g} with correct-only shares; {con[('T2', 2.0)]['fisher_p_attempt_shares']:.2g} only with the FP8 attempt share"},
        {"quote": "FP8 shares shortest path 0.26/0.54, grid 0.06/0.24, kth 0.28/0.50 (targets of M-0a.2)",
         "recomputed": "these are exp19 'off_default_share' (attempts off the default, failing programs included); correct-only: "
                       f"shortest path {con[('T2', 1.0)]['fp8_share_correct']:.2f}/{con[('T2', 2.0)]['fp8_share_correct']:.2f}, grid {con[('T1', 1.0)]['fp8_share_correct']:.2f}/{con[('T1', 2.0)]['fp8_share_correct']:.2f}, kth {con[('T03', 1.0)]['fp8_share_correct']:.2f}/{con[('T03', 2.0)]['fp8_share_correct']:.2f}"},
        {"quote": "power about 0.46 at rho 0.6",
         "recomputed": f"n 13: {pw[('b', 13, 0.6)]:.2f} (copula) / {pw[('a', 13, 0.6)]:.2f} (bivariate normal); n 6: {pw[('b', 6, 0.6)]:.2f} / {pw[('a', 6, 0.6)]:.2f}; panel A's 0.46 is not reproduced at either n"},
        {"quote": "exp19 alpha_sweep.json stores 'off_default_share' and 'off_default_share_invalid_counts'; record which one matches the correct-only definition",
         "recomputed": "neither: both count attempts (the second also counts invalid output); the correct-only share is computed from correct_comp"},
        {"quote": "R1 may not be harmonisable (A1 -8.72 against B values from -8.8 to 26.9)",
         "recomputed": "harmonisable by recomputation: both panels logged first-16-body-token log-probs under W1-W5; panel B stored the negated margin over survivors"},
        {"quote": "Table 174 ban-free/ban for substring search 0.30",
         "recomputed": f"{dose['T04']['D_rmn']:.3f} from exp27/exp19 realised rows (the only Table 174 value outside 0.01)"},
        {"quote": "M-0d.4 panel B repertoire check: expected violations 0",
         "recomputed": "1: count inversions (B7), 3 correct nudged fenwick_tree programs with no correct base program (exp26 results/repertoire_check.json)"},
        {"quote": "the 40 fresh directions, ids to be confirmed rand_9101..rand_9140",
         "recomputed": f"confirmed: {F['e_inputs_ids_ok']}"},
    ]


def run(inp: Inputs) -> None:
    t0 = time.time()
    S = json.loads((WS / "results" / "s3_analyses.json").read_text())
    A = json.loads((WS / "results" / "adjudication.json").read_text())
    F = {"m_candidates": json.loads((WS / "frozen" / "m_candidates.json").read_text()),
         "l3_screen": json.loads((WS / "frozen" / "l3_screen.json").read_text()),
         "f2_screen": json.loads((WS / "frozen" / "f2_screen.json").read_text())}
    e_in = json.loads((WS / "frozen" / "e_inputs.json").read_text())
    F["e_inputs_ids_ok"] = e_in["directions"]["ids_match_expected"]
    chain = [ln.split(" | ") for ln in (WS / "commitments.log").read_text().splitlines() if ln.strip()]
    F["chain"] = [{"utc": c_[0], "file": c_[1], "sha256": c_[2], "chain": c_[4]} for c_ in chain]
    F["hashes"] = {c_[1]: c_[2] for c_ in chain}
    S["units_E"] = {u: x["E_u"] for u, x in F["m_candidates"]["units"].items()}
    kc = S["0b"]["kth_pn_note"]["exp27_T03_PN_a2_correct_composition"]
    S["kth_q"] = (kc.get("quickselect", 0), sum(vv for k, vv in kc.items() if k != "full_sort"))
    pbr = inp.json("exp26", "pooled_inputs.json")["records"]
    S["panelB_base_attempted"] = {r["unit_id"]: r["base"].get("attempted_composition", {}) for r in pbr}
    S["fig"] = {"facetA": fig_beta_escape(S, F, inp)}
    fig_dose(S)
    fig_power(S)
    import csv as _csv
    with (WS / "tables" / "adjudication.csv").open("w", newline="") as f_:
        w_ = _csv.writer(f_)
        judges = list((A["metrics"].get("per_judge_descriptive") or {}).keys())
        w_.writerow(["id", "kind", "task", "expect", "manual_class", "exp24_judges"] + [f"pass1_{j}" for j in judges] +
                    ["nearest_known_sources"])
        for x in A["entries"]:
            w_.writerow([x["id"], x["kind"], x["task"], x["expect"], x["manual_class"], json.dumps(x["exp24_judges"])] +
                        [((x.get("pass1_by_judge") or {}).get(j) or {}).get("class", "") for j in judges] +
                        [json.dumps([(k["source"], round(k["ratio"], 3)) for k in x["nearest_known"]])])
    report = REPORT.read_text()
    corr = build_corrections(S, A, F, report)
    corr += movable_scan(report, corr)
    write_json(WS / "corrections.json", corr)
    bad = [c_ for c_ in corr if c_["old_text_match"] != "exact"]
    logger.info(f"corrections: {len(corr)} ({len(bad)} not exact: {[c_['id'] + ' ' + c_['location'] for c_ in bad]})")
    S["discrepancies"] = discrepancies(S, F)
    S["deviations"] = json.loads((WS / "results" / "deviations.json").read_text()) if (WS / "results" / "deviations.json").exists() else []
    audit = json.loads((WS / "audit" / "rederive_result.json").read_text()) if (WS / "audit" / "rederive_result.json").exists() else None
    timings = {"s5_outputs": time.time() - t0}
    if (WS / "results" / "timings.json").exists():
        timings.update(json.loads((WS / "results" / "timings.json").read_text()))
    out = build_eval_out(S, A, F, corr, audit, timings)
    write_json(WS / "eval_out.json", out)
    logger.info(f"eval_out.json: {len(out['metrics_agg'])} metrics, datasets {[(x['dataset'], len(x['examples'])) for x in out['datasets']]}")
