#!/usr/bin/env python3
"""Item 0a: the counting-sort relabel. Edits to 7.3.4, Tables 296, 297, 300, 314, 370, 371, 372, 7.3.6, 7.3.9 and 7.10,
each value traced to exp33's raw label rows through the validated v2 labeller and the gated adjudication."""

from __future__ import annotations

from typing import Any

from sections.common import SUFFIX, clopper_pearson, edit, fmt, src_ref, value


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    rc, adj, val, rel = ctx["a5"], ctx["a4"], ctx["a2"], ctx["a3"]
    S = src_ref("exp33", "data/labels.jsonl", "arm==FULL_F_counting_sort") + " + labeller_v2 + tables/counting_sort_adjudication.csv"
    new = rc["new"]["T03"]
    old = rc["old"]["T03"]
    full_new = new["per_source"]["F_counting_sort"]["full_count"]
    value("T03 forced counting sort: full state correct counting sort (of 30)", 0, full_new, "CORRECTED", S, 0, "0a")
    rec = {}
    for k in (1, 4, 16):
        e, eo = new["per_k"][k], old["per_k"][k]
        rec[k] = e
        value(f"T03 pooled recovery k{k} (old labels, placebo)", round(eo["recovery"], 2), eo["recovery"], "MATCH",
              src_ref("exp33", "results/p1.json", f"tasks.T03.per_k.{k}.recovery"), 0.005, "0a")
        value(f"T03 pooled recovery k{k}", round(eo["recovery"], 2), e["recovery"], "CORRECTED", S, 0.005, "0a",
              f"num {e['num']:.0f} / den {e['den']:.0f}; slot bootstrap 95% [{e['recovery_ci'][0]:.2f}, {e['recovery_ci'][1]:.2f}]")
    rr1, rr16 = new["per_k"][1]["random_recovery"], new["per_k"][16]["random_recovery"]
    value("T03 random-subspace recovery k1 (Table 297)", 0.05, rr1, "MATCH", S, 0.005, "0a",
          "normalised by the full state over the sources that have random arms (ban source only), so the relabel does not touch it")
    value("T03 random-subspace recovery k16 (Table 297)", 0.05, rr16, "MATCH", S, 0.005, "0a")
    pt1, pt16 = new["per_k"][1]["permuted_transfer_max"], new["per_k"][16]["permuted_transfer_max"]
    value("T03 permuted-label transfer k1 (7.3.5)", 0.60, pt1, "MATCH", S, 0.005, "0a",
          "absolute transfer (count - base)/30 of the ban source; not normalised by the full state, so the relabel does not touch it")
    value("T03 permuted-label transfer k16 (Table 297)", 0.47, pt16, "MATCH", S, 0.005, "0a")
    r_old, r_new = rc["routing"]["old_full_counting"], rc["routing"]["new_full_counting"]
    ci = r_new["routing_ci"]
    value("Table 300 kth smallest | counting sort: full state routing", 0.0, r_new["routing"], "CORRECTED", S, 0.005, "0a",
          f"{r_new['correct_Y']}/{r_new['correct_off_default']} [CP {ci[0]:.2f}, {ci[1]:.2f}]")
    na = rc["novelty_audit"]["by_cell_class"]
    n_full = na.get("FULL_F_counting_sort|CATALOGUE_VARIANT", 0)
    n_forced = sum(v for k, v in na.items() if k.startswith(("F1_counting_sort", "F2_counting_sort", "F3_counting_sort")))
    value("7.3.9 catalogue variants from FULL_F_counting_sort (of 36)", None, n_full, "NEW",
          src_ref("exp33", "results/novelty_audit.json", "rows[].arm"), 0, "0a")
    value("7.3.9 catalogue variants from the forced counting sort prompts F1-F3 (of 36)", None, n_forced, "NEW",
          src_ref("exp33", "results/novelty_audit.json", "rows[].arm"), 0, "0a")
    g = adj["gate"]
    value("judge gate A (deepseek-chat-v3.1), of 10", None, g["A"]["score"], "NEW", "audit/judge_gate.json", 0, "0a")
    value("judge gate B (mistral-medium-3.1), of 10", None, g["B"]["score"], "NEW", "audit/judge_gate.json", 0, "0a")
    value("labeller v2: gold kappa runtime-vs-AST", round(val["gate_json_recorded"]["kappa_runtime_ast"], 3),
          val["gold_new"]["kappa_runtime_ast"], "MATCH", val["source_gate"], 0.0005, "0a")
    value("labeller v2: controls passed (of 5)", None, val["controls_pass"], "NEW", "results/a2_validation.json", 0, "0a")

    # implementation form of the counting sorts: array of counts, or a dictionary (sorted keys / walked over the value range)
    import re
    from sections.common import dep, read_jsonl
    form = {}
    for r in read_jsonl(dep("exp33", "data/labels.jsonl")):
        if r["task"] == "T03" and r["arm"] in ("FULL_F_counting_sort", "DASLY_F_counting_sort_k1", "DASLY_F_counting_sort_k4", "DASLY_F_counting_sort_k16"):
            code = r.get("code") or ""
            f = "array" if re.search(r"\[0\]\s*\*", code) else ("dict_sorted_keys" if re.search(r"=\s*\{\}|Counter\(|defaultdict\(int\)|dict\(\)", code) and "sorted(" in code
                                                                else "dict_value_range" if re.search(r"=\s*\{\}|Counter\(|defaultdict\(int\)|dict\(\)", code) else "neither")
            form.setdefault(r["arm"], {}).setdefault(f, 0)
            form[r["arm"]][f] += 1
    for arm, d in sorted(form.items()):
        value(f"counting sort implementation form, {arm}", None, dict(sorted(d.items())), "NEW",
              src_ref("exp33", "data/labels.jsonl", f"arm=={arm} (regex on code)"), "exact", "0a")
    a1, a16 = form["DASLY_F_counting_sort_k1"].get("array", 0), form["DASLY_F_counting_sort_k16"].get("array", 0)
    d16 = 30 - a16
    c = lambda k: f"{rec[k]['recovery']:.2f} [{rec[k]['recovery_ci'][0]:.2f}, {rec[k]['recovery_ci'][1]:.2f}]"
    # the full-state exchange of the forced counting sort source: 29 counting sort (dictionary form) + 1 other
    land = r_new["landing"]
    n_other_full = land.get("other", 0)
    E = []
    E.append(edit("C8-a01", "0a", "7.3.4", "on kth smallest the forced counting sort source transfers 30 of 30 at every rank while the full state exchange gives 0 (29 programs labelled other, read below).",
                  f"on kth smallest the forced counting sort source transfers 30 of 30 at every rank, and the full state exchange of the same prompt gives {full_new} of 30: the 29 programs once labelled other are counting sort in dictionary form (counts in a dictionary walked in sorted key order), which the extended labeller now names counting sort, and the remaining program is a binary search on the value range (Table 300){SUFFIX}.",
                  why="dictionary-form counting sort was labelled other; relabel validated on references, gold set and negative controls"))
    E.append(edit("C8-a02", "0a", "Table 296", "**Table 296.** Kth smallest: correct programs of the target algorithm (of 30) by source and rank.",
                  "**Table 296.** Kth smallest: correct programs of the target algorithm (of 30) by source and rank. (iteration-8 correction: forced counting sort source, full state 0 -> 29 after the labeller was extended to counting sort in dictionary form)", kind="caption"))
    E.append(edit("C8-a03", "0a", "Table 296", "| forced counting sort source | counting sort | 0 | 0 | 30 (pass 1.00) | - | 30 (pass 1.00) | - | 30 (pass 1.00) |  |  | 1.00/1.00 |",
                  f"| forced counting sort source | counting sort | 0 | {full_new} | 30 (pass 1.00) | - | 30 (pass 1.00) | - | 30 (pass 1.00) |  |  | 1.00/1.00 |", kind="table_row"))
    E.append(edit("C8-a04", "0a", "Table 297", "**Table 297.** Kth smallest: pooled recovery and its controls by rank.",
                  "**Table 297.** Kth smallest: pooled recovery and its controls by rank. (iteration-8 correction: pooled recovery recomputed after the counting-sort relabel with exp33's own slot bootstrap, 2,000 resamples; the old values 1.59 / 1.57 / 1.55 are reproduced exactly under the old labels; the permuted-label column is an absolute transfer, (count - base)/30, and the random-subspace recovery uses only the ban source, so neither changes; per-source recovery in Table 297b is the summary)", kind="caption"))
    E.append(edit("C8-a05", "0a", "Table 297", "| 1 | 1.59 [1.47, 1.72] | 0.05 | 20:0 (1.9e-06) | 0.60 | 0.90 |",
                  f"| 1 | {c(1)} | 0.05 | 20:0 (1.9e-06) | 0.60 | 0.90 |", kind="table_row"))
    E.append(edit("C8-a06", "0a", "Table 297", "| 4 | 1.57 [1.44, 1.72] | - | - | - | - |",
                  f"| 4 | {c(4)} | - | - | - | - |", kind="table_row"))
    E.append(edit("C8-a07", "0a", "Table 297", "| 16 | 1.55 [1.42, 1.70] | 0.05 | 21:0 (9.5e-07) | 0.47 | 0.90 |",
                  f"| 16 | {c(16)} | 0.05 | 21:0 (9.5e-07) | 0.47 | 0.90 |", kind="table_row"))
    E.append(edit("C8-a08", "0a", "7.3.6", "and the counting sort source lands on counting sort in 30 of 30 at rank 16 while the full state exchange lands none (Table 300). Connected components is not categorical: the forced BFS source's rank-16 edit lands 21 DFS and 9 BFS. The subspace thus carries which algorithm, and on two tasks it carries it more cleanly than the whole state does.",
                  f"and the counting sort source lands on counting sort in 30 of 30 at rank 16, where the full state exchange of the same prompt also lands {full_new} of 30 on counting sort once its dictionary form is labelled (Table 300). Connected components is not categorical: the forced BFS source's rank-16 edit lands 21 DFS and 9 BFS. The subspace thus carries which algorithm, more cleanly than the full state on one task (shortest path: Floyd-Warshall 28/28 against 8/20); on kth smallest the DAS edit changes the implementation form (mostly an array of counts, {a16} of 30 at rank 16, against the full state's dictionary with sorted keys, {full_new} of 30), not the algorithm{SUFFIX}."))
    E.append(edit("C8-a09", "0a", "Table 300", "**Table 300.** Routing: where correct programs off the default land under the full state exchange and under DAS.",
                  "**Table 300.** Routing: where correct programs off the default land under the full state exchange and under DAS. (iteration-8 correction: kth smallest | counting sort row relabelled; the committed C rule still scores kth smallest categorical, because it reads the DAS columns)", kind="caption"))
    E.append(edit("C8-a10", "0a", "Table 300", "| kth smallest | counting sort | 0.00 (0/30) [0.00, 0.12] | 1.00 (30/30) [0.88, 1.00] | 1.00 (30/30) [0.88, 1.00] | 1.00 (30/30) [0.88, 1.00] | other 29, quickselect 1 | counting sort 30 |",
                  f"| kth smallest | counting sort | {r_new['routing']:.2f} ({r_new['correct_Y']}/{r_new['correct_off_default']}) [{ci[0]:.2f}, {ci[1]:.2f}] | 1.00 (30/30) [0.88, 1.00] | 1.00 (30/30) [0.88, 1.00] | 1.00 (30/30) [0.88, 1.00] | counting sort (dictionary form) {full_new}, binary search on the value range {n_other_full} | counting sort 30 (array of counts {a16}, dictionary walked over the value range {d16}) |", kind="table_row"))
    E.append(edit("C8-a11", "0a", "Table 314", "| kth smallest | full state exchange, forced counting sort source | 30 | 1.00 | 0 | other 29, quickselect 1 |",
                  f"| kth smallest | full state exchange, forced counting sort source | 30 | 1.00 | 0 | counting sort (dictionary form) {full_new}, other {n_other_full} (binary search on the value range; iteration-8 correction) |", kind="table_row"))
    E.append(edit("C8-a12", "0a", "7.3.9", "Of the 38 correct programs labelled other across the experiment, 36 are catalogue variants and 2 are labeller misses; none is novel.",
                  f"Of the 38 correct programs labelled other across the experiment, 36 are catalogue variants and 2 are labeller misses; none is novel. {n_full} of the 36 come from the full state exchange of the forced counting sort source and {n_forced} more from the forced counting sort prompts: they are counting sort in dictionary form, which the extended labeller now names counting sort{SUFFIX}."))
    E.append(edit("C8-a13", "0a", "Table 371", "| DAS experiment | 38 correct programs labelled other | 36 catalogue variants, 2 labeller misses | 0 |",
                  f"| DAS experiment | 38 correct programs labelled other | 36 catalogue variants ({n_full + n_forced} are counting sort in dictionary form, {n_full} of them from the full state exchange of the forced counting sort source; relabelled counting sort in iteration 8), 2 labeller misses | 0 |", kind="table_row"))
    E.append(edit("C8-a16", "0a", "Table 371", "**Table 371.** Novelty audits of iteration 7.",
                  "**Table 371.** Novelty audits of iteration 7. (iteration-8 correction: the DAS experiment row names the counting-sort cells)", kind="caption"))
    E.append(edit("C8-a14", "0a", "Table 372", "| Routing claim | Categorical on shortest path and kth smallest; not on connected components | Floyd-Warshall 28/28 and counting sort 30/30 under DAS; forced BFS lands on DFS |",
                  f"| Routing claim | Categorical by the committed rule on two tasks (shortest path, kth smallest), not on connected components (iteration-8 correction) | Floyd-Warshall 28/28 under DAS against 8/20 for the full state; on kth smallest the full state also lands {full_new} of 30 on counting sort (dictionary form) against 30/30 under DAS ({a16} of them an array of counts); forced BFS lands on DFS |", kind="table_row"))
    E.append(edit("C8-a15", "0a", "Table 370", "| Qwen3-8B, kth smallest | DAS rank 1, forced counting sort source | 30/30 counting sort | 0/30 | 1.00 |",
                  f"| Qwen3-8B, kth smallest | DAS rank 1, forced counting sort source | 30/30 counting sort ({a1} an array of counts; the full state exchange gives {full_new}/30 in dictionary form, iteration-8 correction) | 0/30 | 1.00 |", kind="table_row"))
    # the committed contrastive pilot on shortest path (Table 301): adjudicated labels of its 100 programs
    pil = [r for r in adj["rows"] if r["task"] == "T2" and r["cell"].startswith("DAS_")]
    moved = [r for r in pil if r["old_label"] != r["final_label"]]
    assert not any(r["passed"] for r in moved), "a relabelled pilot program passes: correct-Y counts would change"
    o_deg = sum(r["old_label"] == "other" and r["final_label"] == "other" for r in pil)
    o_dij = sum(r["old_label"] == "other" and r["final_label"] == "dijkstra" for r in pil)
    d_deg = sum(r["old_label"] == "dijkstra" and r["final_label"] == "other" for r in pil)
    n_oth, n_dij = sum(r["old_label"] == "other" for r in pil), sum(r["old_label"] == "dijkstra" for r in pil)
    value("Table 301 pilot: programs labelled other that are degenerate / attempted Dijkstra", None, f"{o_deg} / {o_dij} of {n_oth}", "NEW",
          "tables/counting_sort_adjudication.csv#cell startswith DAS_", "exact", "0a")
    value("Table 301 pilot: programs labelled Dijkstra by the frozen path labeller that are degenerate text", None, f"{d_deg} of {n_dij}", "NEW",
          "tables/counting_sort_adjudication.csv#cell startswith DAS_", "exact", "0a")
    E.append(edit("C8-a17", "0a", "Table 301", "**Table 301.** The pilot of the committed contrastive maps in generation (base cells in parentheses).",
                  f"**Table 301.** The pilot of the committed contrastive maps in generation (base cells in parentheses). (iteration-8 correction: in the adjudicated column of these {len(pil)} programs (rule, two gated judges, manual read; `tables/counting_sort_adjudication.csv`), {o_deg} of the {n_oth} labelled other are degenerate text and {o_dij} are attempted Dijkstra that crash on the edge list, and {d_deg} of the {n_dij} labelled Dijkstra are degenerate text that the frozen path labeller names Dijkstra; no relabelled program passes, so the correct-Y counts stand)", kind="caption"))
    return {"edits": E, "verdict": "CORRECTED",
            "summary": {"forms": form, "full_state_counting_sort": full_new, "kth_pooled_recovery": {k: rec[k]["recovery"] for k in rec},
                        "kth_pooled_recovery_ci": {k: rec[k]["recovery_ci"] for k in rec},
                        "catalogue_variants_from_full_cell": n_full, "from_forced_prompts": n_forced}}
