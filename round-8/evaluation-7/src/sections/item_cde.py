#!/usr/bin/env python3
"""Items 0c (the Gemma dial's prefill condition), 0d (the fork margin as a readout) and 0e (Gemma controls within their
limits: natural variance at every rank, the dormant-flag rule, and the protocols that make the two families' controls
not comparable)."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from sections.common import (SUFFIX, TABLES, bootstrap_spearman, dep, edit, read_json, read_jsonl, spearman, src_ref,
                             value, write_csv)


# ------------------------------------------------------------------------------------------------ 0c
def item_c(ctx: dict[str, Any]) -> dict[str, Any]:
    g2 = dep("exp38", "src/g2.py").read_text().split("\n")
    l877, l878, l885 = g2[876].strip(), g2[877].strip(), g2[884].strip()
    assert "run.run_cell(ids, cs, rows_w, raw" in l877, l877
    assert "forced-BFS ceiling (natural sampling from index 0" in l878, l878
    assert "run.run_cell(pfz[\"ids\"], [], rows, raw, \"G2:forced\")" in l885, l885
    readme = [l.strip() for l in dep("exp38", "README.md").read_text().split("\n") if "ceiling" in l and "forced" in l.lower()]
    rows = read_jsonl(dep("exp38", "data/raw_g2dose.jsonl"))
    by = defaultdict(list)
    for r in rows:
        by[r["cell"]].append(r)
    uk = lambda c: sorted(tuple(r["ukey"]) for r in by[c])
    pre = lambda c: sorted({r.get("prefix_len") for r in by[c]}, key=str)
    same_slots = uk("forced_bfs_F5") == uk("twin") == uk("DAS|bfs|1.0")
    cnt = lambda c: sum(1 for r in by[c])
    value("Gemma dial: forced-BFS cell shares the CRN slots of the twin and DAS cells", None, same_slots, "NEW",
          src_ref("exp38", "data/raw_g2dose.jsonl", "ukey by cell"), "exact", "0c")
    value("Gemma dial: prefix length of twin / DAS lambda 1 / forced-BFS cells", None,
          {"twin": pre("twin"), "DAS|bfs|1.0": pre("DAS|bfs|1.0"), "forced_bfs_F5": pre("forced_bfs_F5")}, "NEW",
          src_ref("exp38", "data/raw_g2dose.jsonl", "prefix_len"), "exact", "0c")
    ceiling = [l for l in readme if l.startswith("| forced-BFS prompt F5")] + \
        [l for l in dep("exp38", "README.md").read_text().split("\n") if "prompting ceiling" in l and l.strip().startswith("- **")]
    value("exp38 README: the sentences that describe the forced-BFS ceiling", None, [x.strip() for x in ceiling], "NEW",
          src_ref("exp38", "README.md", "grep 'forced' and 'ceiling'"), "exact", "0c",
          "the README calls the unprefilled forced prompt the 'prompting ceiling' and compares the prefilled DAS cell with it")
    evid = {"g2.py:877": l877, "g2.py:878": l878, "g2.py:885": l885, "README": readme,
            "same_slots": same_slots, "prefix_len": {c: pre(c) for c in ("twin", "DAS|bfs|1.0", "forced_bfs_F5")},
            "n_rows": {c: cnt(c) for c in ("twin", "DAS|bfs|1.0", "forced_bfs_F5")}}
    cond = ("with the shared opening prefilled, the edit raises correct BFS from 11 to 42 of 50; the instruction, "
            "sampled without the prefill, gives 35, which is not comparable")
    code = ("the DAS, difference-in-means and twin cells run with the canonical 32-token opening prefilled "
            "(exp38 `src/g2.py` line 877, `run.run_cell(ids, cs, rows_w, raw, ...)`), while the forced-BFS ceiling is "
            "sampled from index 0 with no prefix (lines 878-885, `run.run_cell(pfz[\"ids\"], [], rows, raw, \"G2:forced\")`) "
            "on the same CRN slots")
    E = [
        edit("C8-c01", "0c", "7.8.4", "at lambda 1 it gives more correct BFS programs (42) than the explicit instruction to use BFS (35).",
             f"the explicit instruction to use BFS gives 35, but it was sampled from index 0 without the prefilled opening and is not comparable: {code}{SUFFIX}."),
        edit("C8-c02", "0c", "Table 365", "**Table 365.** Gemma: DAS against difference in means as a dose dial toward BFS (N = 50 per cell, same seed).",
             "**Table 365.** Gemma: DAS against difference in means as a dose dial toward BFS (N = 50 per cell, same seed). (iteration-8 correction: every cell except the forced BFS prompt has the shared 32-token opening prefilled; the forced BFS prompt is sampled from index 0 without it, on the same slots, so its row is not comparable with the edits)", kind="caption"),
        edit("C8-c03", "0c", "Table 365", "| forced BFS prompt, fifth forced source (prompting ceiling) | 50 | 35 | 0.70 | 4e-6 (unadjusted) | - |",
             "| forced BFS prompt, fifth forced source (sampled from index 0 without the prefilled opening; not comparable) | 50 | 35 | 0.70 | 4e-6 (unadjusted) | - |", kind="table_row"),
        edit("C8-c04", "0c", "Table 370", "| gemma-3-4b-it, grid | DAS rank 4 at block 17, lambda 1 | 42/50 BFS | 11/50 | 0.88 |",
             "| gemma-3-4b-it, grid | DAS rank 4 at block 17, lambda 1 (opening prefilled) | 42/50 BFS | 11/50 | 0.88 |", kind="table_row"),
        edit("C8-c05", "0c", "Table 370", "| gemma-3-4b-it, grid | Explicit BFS instruction | 35/50 BFS | 11/50 | 0.70 |",
             "| gemma-3-4b-it, grid | Explicit BFS instruction (no prefill, not comparable) | 35/50 BFS | 11/50 | 0.70 |", kind="table_row"),
        edit("C8-c06", "0c", "Table 370", "**Table 370.** Edits that moved the algorithm in generation in iteration 7.",
             "**Table 370.** Edits that moved the algorithm in generation in iteration 7. (iteration-8 correction: prefill condition of the two Gemma rows stated; kth smallest counting sort row annotated)", kind="caption"),
        edit("C8-c07", "0c", "7.9", "In Gemma the DAS edit at the fork beats the explicit instruction in correct BFS programs, and steering five validated circuit nodes doubles them.",
             f"In Gemma the DAS edit at the fork, with the shared opening prefilled, raises correct BFS programs from 11 to 42 of 50 (the explicit instruction's 35 was sampled without the prefill and is not comparable), and steering five validated circuit nodes doubles them{SUFFIX}."),
    ]
    return {"edits": E, "evidence": evid, "verdict": "CORRECTED (prefill condition stated at every mention)"}


# ------------------------------------------------------------------------------------------------ 0d
def item_d(ctx: dict[str, Any]) -> dict[str, Any]:
    fa = read_json(dep("exp34", "results/f_analysis.json"))
    cells = fa["cells"]["T10"]
    m, y, llr = [c["m"] for c in cells], [c["y"] for c in cells], [c["llr48"] for c in cells]
    rho_m, rho_l = spearman(m, y), spearman(llr, y)
    ci_m, ci_l = bootstrap_spearman(m, y), bootstrap_spearman(llr, y)
    rng = random.Random(11)
    perm = []
    for _ in range(2000):
        yy = y[:]
        rng.shuffle(yy)
        perm.append(spearman(m, yy))
    perm_med = sorted(perm)[len(perm) // 2]
    value("fork margin vs escape share Spearman (T10, 40 directions)", 0.80, rho_m, "MATCH",
          src_ref("exp34", "results/f_analysis.json", "cells.T10[].m,y"), 0.005, "0d", f"bootstrap 95% [{ci_m[0]:.2f}, {ci_m[1]:.2f}]")
    value("48-token opening LLR vs escape share Spearman (T10)", 0.87, rho_l, "MATCH",
          src_ref("exp34", "results/f_analysis.json", "cells.T10[].llr48,y"), 0.005, "0d", f"bootstrap 95% [{ci_l[0]:.2f}, {ci_l[1]:.2f}]")
    assert abs(rho_m - fa["F"]["T10"]["rho"]) < 1e-9 and abs(rho_l - fa["F"]["T10"]["llr48"]["rho"]) < 1e-9
    value("token-map shuffle placebo share reaching 0.80", 0.18, 0.18, "CARRIED",
          src_ref("exp34", "README.md", "Placebo, shuffled fork-token map on T10: 18% of the 200 permutations"), 0.0, "0d")
    p2 = read_json(dep("exp34", "results/p2_analysis.json"))["P2"]
    value("axis projection Spearman T10", 0.17, p2["T10"]["rho_b"], "MATCH", src_ref("exp34", "results/p2_analysis.json", "P2.T10.rho_b"), 0.005, "0d")
    value("axis projection Spearman T2", 0.01, p2["T2"]["rho_b"], "MATCH", src_ref("exp34", "results/p2_analysis.json", "P2.T2.rho_b"), 0.005, "0d")
    value("plan-subspace projection Spearman (iteration 4)", 0.03, 0.03, "CARRIED", "current_report.md#Section 4 item 5 ('ranks them at 0.03')", 0.0, "0d")
    value("permuted-outcome placebo: median Spearman of margin vs shuffled outcomes", None, perm_med, "NEW",
          "audit placebo (2,000 shuffles, seed 11)", 0.05, "0d")
    read = (f"the effect of a push is already expressed at the fork token (a teacher-forced readout of the margin matches "
            f"the sampled outcomes at Spearman {rho_m:.2f}, and the 48-token opening log-likelihood ratio at {rho_l:.2f}); "
            f"no direction-level property predicted which pushes move the fork (axis {p2['T10']['rho_b']:.2f} and "
            f"{p2['T2']['rho_b']:.2f}; plan-subspace projection 0.03 in iteration 4)")
    E = [
        edit("C8-d01", "0d", "7.4.3", "its Spearman with the attempted share is 0.82, and the 48-token opening LLR in place of the fork margin reaches 0.87.",
             f"its Spearman with the attempted share is 0.82, and the 48-token opening LLR in place of the fork margin reaches 0.87. Both are readouts taken where the outcome is already expressed, teacher-forced at the fork token and at the opening, so their agreement with the sampled outcomes measures the outcome there rather than predicting it from the push; no property of the push direction itself predicted which pushes move the fork (axis projection {p2['T10']['rho_b']:.2f} and {p2['T2']['rho_b']:.2f}, Section 7.4.4; plan-subspace projection 0.03 in iteration 4){SUFFIX}."),
        edit("C8-d02", "0d", "7.9", "where it exists its margin predicts the effect of random pushes (connected components) and of temperature (within the committed error on two of the four mixed units).",
             f"where it exists, the effect of a push is already expressed at the fork token on connected components (a teacher-forced readout of the margin matches the sampled outcomes of random pushes at Spearman {rho_m:.2f}, and the 48-token opening log-likelihood ratio at {rho_l:.2f}; no direction-level property predicted which pushes move the fork), and its logits divided by T predicted the temperature response within the committed error on two of the four mixed units{SUFFIX}."),
        edit("C8-d03", "0d", "7.10", "and the fork margin under a random push predicts the effect of the push (Spearman 0.80), through the probability that stays on the default fork tokens rather than through which algorithm each other token leads to (a placebo that shuffles the token map reaches 0.80 in 18% of permutations).",
             f"and the effect of a random push is already expressed at that token: a teacher-forced readout of the fork margin matches the sampled outcomes at Spearman {rho_m:.2f} (the 48-token opening log-likelihood ratio at {rho_l:.2f}), through the probability that stays on the default fork tokens rather than through which algorithm each other token leads to (a placebo that shuffles the token map reaches 0.80 in 18% of permutations); no direction-level property predicted which pushes move the fork (axis {p2['T10']['rho_b']:.2f} and {p2['T2']['rho_b']:.2f}; plan-subspace projection 0.03 in iteration 4){SUFFIX}."),
        edit("C8-d04", "0d", "closing", "The margin at the decision predicts what moves the algorithm. Under 40 random pushes, the fork margin on connected components ranks which pushes change the algorithm (Spearman 0.80), although a placebo that shuffles which fork tokens lead to which algorithm reaches the same value in 18% of permutations, so the ranking rests on how much probability stays on the default fork tokens.",
             f"The effect of a push is already expressed at the decision token. Under 40 random pushes on connected components, a teacher-forced readout of the fork margin matches which pushes change the algorithm (Spearman {rho_m:.2f}; the 48-token opening log-likelihood ratio {rho_l:.2f}), although a placebo that shuffles which fork tokens lead to which algorithm reaches the same value in 18% of permutations, so the agreement rests on how much probability stays on the default fork tokens; no direction-level property predicted which pushes move the fork (axis {p2['T10']['rho_b']:.2f} and {p2['T2']['rho_b']:.2f}; plan-subspace projection 0.03 in iteration 4){SUFFIX}."),
    ]
    return {"edits": E, "verdict": "RESTATED (readout, not predictor)",
            "summary": {"rho_margin": rho_m, "rho_margin_ci": ci_m, "rho_llr48": rho_l, "rho_llr48_ci": ci_l,
                        "perm_median": perm_med}}


# ------------------------------------------------------------------------------------------------ 0e
def item_e(ctx: dict[str, Any]) -> dict[str, Any]:
    gd = read_json(dep("exp38", "results/g2_decisions.json"))
    nv = gd["natural_variance"]
    rows = []
    rec = {1: (0.00093, 0.00098), 2: (0.00116, 0.00185), 4: (0.00187, 0.00275), 8: (0.00565, 0.00486)}
    for k in (1, 2, 4, 8):
        e = nv[str(k)]
        rows.append({"block": 17, "rank": k, "share": e["share"], "random_p95": e["random_p95"], "random_mean": e["random_mean"],
                     "below_p95": e["share"] <= e["random_p95"]})
        value(f"Gemma natural variance share, block 17, rank {k}", rec[k][0], e["share"], "MATCH",
              src_ref("exp38", "results/g2_decisions.json", f"natural_variance.{k}.share"), 0.000005, "0e")
        value(f"Gemma natural variance random 95th percentile, block 17, rank {k}", rec[k][1], e["random_p95"], "MATCH",
              src_ref("exp38", "results/g2_decisions.json", f"natural_variance.{k}.random_p95"), 0.000005, "0e")
    b22 = gd["second_layer"]["22"]["natural_variance_k1"]
    rows.append({"block": 22, "rank": 1, "share": b22["share"], "random_p95": b22["random_p95"],
                 "random_mean": b22["random_mean"], "below_p95": b22["share"] <= b22["random_p95"]})
    value("Gemma natural variance share, block 22, rank 1", None, b22["share"], "NEW",
          src_ref("exp38", "results/g2_decisions.json", "second_layer.22.natural_variance_k1.share"), 0.000005, "0e",
          f"random 95th percentile {b22['random_p95']:.5f}: above")
    write_csv(TABLES / "gemma_natural_variance.csv", rows, ["block", "rank", "share", "random_p95", "random_mean", "below_p95"])
    rho = nv["spearman_R1_coord_vs_yv"]["rho"]
    g2 = dep("exp38", "src/g2.py").read_text().split("\n")
    rule = g2[617].strip()
    assert 'nat["dormant_flag"] = bool(nat[1]["share"] <= nat[1]["random_p95"] and abs(rho) < 0.2)' in rule, rule
    value("Gemma dormant_flag (g2.py:618 rule)", None, gd["dormant_flag"], "NEW",
          src_ref("exp38", "results/g2_decisions.json", "dormant_flag"), "exact", "0e",
          f"rule '{rule}'; share_k1 <= p95 is {nv['1']['share'] <= nv['1']['random_p95']}, |rho| = {abs(rho):.3f}")
    below = [r["rank"] for r in rows if r["block"] == 17 and r["below_p95"]]
    rec_range = [gd["per_k"][str(k)]["das_recovery_seed_median"] for k in (1, 2, 4, 8)]
    protocols = [
        {"family": "Qwen3-8B (Section 7.3)", "objective": "whole-program likelihood LME_Y of the source's programs (amended; the committed contrastive objective diverged)",
         "site_and_readout": "task-specification states at blocks 12-23 (one map over the band); held-out generation of whole programs and teacher-forced LME_Y",
         "permutation_scheme": "labels permuted over the two kept algorithms per task (44% of training labels changed; 56% on kth smallest)",
         "untrained_network": "random-init Qwen3-8B, shortest path only; committed comparison against the diverged fit (0.013), replaced post hoc by the matched LME_Y fit (5.08)",
         "pairs": "all source x base pairs (bans W1-W3, forced families 0-2 -> neutral and padding twins); held-out W5 ban and forced families 3-4, N = 30 slots"},
        {"family": "gemma-3-4b-it (Section 7.8)", "objective": "single-token fork margin (logsumexp over the BFS tokens minus the ' visited' logit)",
         "site_and_readout": "block 17 at the fork position (response index 32, opening prefilled); teacher-forced margin, then generation",
         "permutation_scheme": "BFS/DFS source labels swapped (3 permutations)",
         "untrained_network": "randomly initialised Gemma on the same fork-margin readout",
         "pairs": "768 held-out pairs (held-out templates and forced sources)"},
    ]
    write_csv(TABLES / "control_protocols.csv", protocols, list(protocols[0].keys()))
    tbl = ("**Table 364d.** The controls of the two families were run under different protocols, so their outcomes are not "
           "directly comparable (iteration-8 correction: new table; `tables/control_protocols.csv`).\n\n"
           "| Family | Objective | Site and readout | Permutation scheme | Untrained network | Pairs |\n|-|-|-|-|-|-|\n" +
           "\n".join(f"| {p['family']} | {p['objective']} | {p['site_and_readout']} | {p['permutation_scheme']} | {p['untrained_network']} | {p['pairs']} |" for p in protocols))
    comp = "the Qwen3-8B and Gemma controls used different objectives, readouts and permutation schemes, so their outcomes are not directly comparable"
    nvtxt = (f"the subspace holds less of the twin's natural variance across prompts than the random 95th percentile at ranks 1, 2 and 4 "
             f"({nv['1']['share']:.5f} against {nv['1']['random_p95']:.5f}, {nv['2']['share']:.5f} against {nv['2']['random_p95']:.5f}, "
             f"{nv['4']['share']:.5f} against {nv['4']['random_p95']:.5f}) and more only at rank 8 ({nv['8']['share']:.5f} against "
             f"{nv['8']['random_p95']:.5f}), so the dial's rank-4 subspace lies below it; at block 22 the rank-1 share lies above it "
             f"({b22['share']:.5f} against {b22['random_p95']:.5f}). The committed dormant flag (exp38 `src/g2.py` line 618: rank-1 share "
             f"at or below the random 95th percentile AND |rho| < 0.2) was false only because |rho| = {abs(rho):.3f}, the coordinate "
             f"tracking the natural fork log odds, not because of variance")
    E = [
        edit("C8-e01", "0e", "7.8.3", "This time the controls hold.", "These controls hold (iteration-8 correction: within their limits below)."),
        edit("C8-e02", "0e", "7.8.3", "The DAS claim's Gemma version is therefore supported at every rank, and the controls that failed for Qwen3-8B in Section 7.3 pass here.",
             f"The DAS claim's Gemma version is therefore supported at every rank by the random-subspace, permuted-label and untrained-network controls; the dormancy checks (reverse interchange, projected-map retention) were not run, a recovery of {min(rec_range):.2f} to {max(rec_range):.2f} times the full-state swap is the off-manifold signature Makelov et al. [122] warn about, and {comp} (Table 364d){SUFFIX}."),
        edit("C8-e03", "0e", "7.8.3", "and the subspace holds 0.0009 of the twin's natural variance across prompts, at the random 95th percentile.",
             f"and {nvtxt}{SUFFIX}."),
        edit("C8-e04", "0e", "Table 364b", "**Table 364b.** Gemma: DAS at the fork by rank, with its controls (held-out templates and held-out forced sources, 768 pairs; block 17, and block 22 for comparison).",
             "**Table 364b.** Gemma: DAS at the fork by rank, with its controls (held-out templates and held-out forced sources, 768 pairs; block 17, and block 22 for comparison). (iteration-8 correction: the natural variance share lies below the random 95th percentile at ranks 1, 2 and 4 and above it at rank 8; at block 22, rank 1, it lies above (0.00294 against 0.00078); dormancy checks were not run; the controls are not comparable with those of Qwen3-8B, Table 364d)", kind="caption"),
        edit("C8-e05", "0e", "Table 364d", "\n\n### 7.8.4 A dose dial that keeps the programs", "\n\n" + tbl + "\n\n### 7.8.4 A dose dial that keeps the programs", kind="table_insert"),
        edit("C8-e06", "0c+0e", "Table 372", "| Gemma claims | Temperature law holds; DAS controls hold, calling it one dimensional not licensed; 7 to 8 of 10 circuit nodes validated | Error 0.026; random initialisation at most 0.25 times; dose dial 42 correct BFS against 35 for the instruction |",
             "| Gemma claims | Temperature law holds; DAS passes the random-subspace, permuted-label and untrained-network controls (dormancy checks not run; natural variance below the random 95th percentile at ranks 1, 2 and 4; controls not comparable with Qwen3-8B's), calling it one dimensional not licensed; 7 to 8 of 10 circuit nodes validated (iteration-8 correction) | Error 0.026; random initialisation at most 0.25 times; with the opening prefilled the dial raises correct BFS from 11 to 42 of 50 (the instruction's 35 was sampled without the prefill, not comparable) |", kind="table_row"),
        edit("C8-e07", "0c+0e", "7.10", "In Gemma the analogous subspace at the fork passes all three controls and acts as a dose dial that keeps the programs.",
             f"In Gemma the analogous subspace at the fork passes the random-subspace, permuted-label and untrained-network controls (dormancy checks not run; its natural variance lies below the random 95th percentile at ranks 1, 2 and 4, and it recovers {min(rec_range):.2f} to {max(rec_range):.2f} times the full-state swap) and, with the shared opening prefilled, acts as a dose dial that keeps the programs; {comp}{SUFFIX}."),
        edit("C8-e08", "0c+0e", "closing", "In Gemma, DAS at the fork passes the controls with random subspaces, permuted labels and an untrained network, but the subspace is not unique across seeds and the committed rule does not license calling it one dimensional; as a dose dial it raises correct BFS programs from 11 to 42 of 50, above the 35 of an explicit BFS instruction, while a difference-in-means edit toward BFS at matched teacher-forced effect destroys the programs.",
             f"In Gemma, DAS at the fork passes the controls with random subspaces, permuted labels and an untrained network (dormancy checks not run; its natural variance lies below the random 95th percentile at ranks 1, 2 and 4), but the subspace is not unique across seeds and the committed rule does not license calling it one dimensional; {comp}. With the shared opening prefilled, the edit raises correct BFS from 11 to 42 of 50; the instruction, sampled without the prefill, gives 35, which is not comparable; a difference-in-means edit toward BFS at matched teacher-forced effect destroys the programs{SUFFIX}."),
        edit("C8-e09", "0e", "7.11", "which may require fitting at the fork in generation, where Gemma's controls passed, rather than at the task specification states.",
             f"which may require fitting at the fork in generation, where Gemma's controls passed, rather than at the task specification states; because the Qwen3-8B and Gemma controls used different objectives, readouts and permutation schemes, their outcomes are not directly comparable, and a matched protocol is part of that test{SUFFIX}."),
        edit("C8-e10", "0e", "closing", "First, whether Qwen3-8B's handle can be certified as a variable: a DAS fit at the fork in generation, where Gemma's controls passed, rather than at the task specification states.",
             f"First, whether Qwen3-8B's handle can be certified as a variable: a DAS fit at the fork in generation, where Gemma's controls passed, rather than at the task specification states, under one protocol for both families ({comp}){SUFFIX}."),
    ]
    return {"edits": E, "verdict": "RESTATED (controls within their limits)",
            "summary": {"ranks_below_p95": below, "block22_k1_above": b22["share"] > b22["random_p95"],
                        "dormant_flag": gd["dormant_flag"], "abs_rho": abs(rho), "recovery_range": rec_range}}
