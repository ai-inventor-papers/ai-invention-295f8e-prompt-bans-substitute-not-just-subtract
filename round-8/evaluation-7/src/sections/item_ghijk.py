#!/usr/bin/env python3
"""Items 0g (not run and deviations), 0h (Table 346 fresh-slot rows), 0i (search as rates and clusters), 0j (scope per
unit; training templates of the manifold claim) and 0k (stale 'Step K' tags and the lost file names)."""

from __future__ import annotations

import difflib
import re
from collections import Counter, defaultdict
from typing import Any

from sections.common import (EVAL6_DIR, REPORT, SUFFIX, TABLES, clopper_pearson, dep, edit, fisher_exact_two_sided,
                             mcnemar_exact, read_json, src_ref, value, wilson, write_csv)


# ------------------------------------------------------------------------------------------------ 0g
def item_g(ctx: dict[str, Any]) -> dict[str, Any]:
    dv = {d["id"]: d["text"] for d in read_json(dep("exp33", "results/deviations.json"))}
    for k in ("D-drop", "D-tfsets", "D-targets", "D-cap", "D-randinit", "D-C-k"):
        value(f"exp33 deviation {k} quoted verbatim", None, dv[k][:80] + "...", "NEW", src_ref("exp33", "results/deviations.json", k), "exact", "0g")
    sec = ("### 7.3.10 Not run and deviations\n\n"
           "The DAS experiment's deviation log records what was not run and what departed from the plan; the four that bear on the "
           "claims above are quoted verbatim from `results/deviations.json` (iteration-8 correction: new subsection).\n\n"
           f"- **D-drop.** \"{dv['D-drop']}\"\n"
           f"- **D-tfsets.** \"{dv['D-tfsets']}\"\n"
           f"- **D-targets.** \"{dv['D-targets']}\"\n"
           f"- **D-cap.** \"{dv['D-cap']}\"\n\n"
           "Two further deviations are used above: D-randinit (the committed untrained-network comparison against the diverged fit, "
           "replaced post hoc by the matched likelihood fit; Section 7.3.5) and D-C-k (forced sources were generated at ranks 1, 4 "
           "and 16 only, so the routing claim is scored at rank 16 and rank 2 is untested for forced sources; Table 297b). Plan "
           "resampling and the literal top-five placement in the fitted coordinates on the grid task remain open items "
           "(Sections 7.10 and 7.11).")
    E = [
        edit("C8-g01", "0g", "7.3.10", "\n\n## 7.4 Where the algorithm is decided in generation (Qwen3-8B)",
             "\n\n" + sec + "\n\n## 7.4 Where the algorithm is decided in generation (Qwen3-8B)", kind="section_insert"),
        edit("C8-g02", "0g", "7.10", "which closes the push route for that question at the doses tried.",
             "which closes the push route for that question at the doses tried.\n\n**Not run.** Plan resampling and the DAS-coordinate top-five placement on the grid task (the T1 extension) were dropped by the DAS experiment's committed drop order (deviation D-drop, Section 7.3.10); the untrained-network control ran on shortest path only (iteration-8 correction)."),
        edit("C8-g03", "0g", "7.11", "so a search on a task whose catalogue already covers the known techniques, where a correct program outside it would be new, is the remaining route to a novel algorithm.",
             "so a search on a task whose catalogue already covers the known techniques, where a correct program outside it would be new, is the remaining route to a novel algorithm. Two items not run in iteration 7 carry forward: plan resampling and the DAS-coordinate top-five placement on the grid task (Section 7.3.10) (iteration-8 correction)."),
    ]
    return {"edits": E, "verdict": "NEW (7.3.10)", "quoted": {k: dv[k] for k in ("D-drop", "D-tfsets", "D-targets", "D-cap")}}


# ------------------------------------------------------------------------------------------------ 0h
def item_h(ctx: dict[str, Any]) -> dict[str, Any]:
    e3 = read_json(dep("exp36", "results/e3_replicate.json"))["T10_fresh_k10_19"]
    pc = e3["profiles"]["cells"]
    D1, PT, PR, PS = (pc[k]["Y"] for k in ("D1", "PTOP", "PREST", "PSHUF"))
    tr, ds = e3["profiles"]["PTOP_vs_PREST"], e3["profiles"]["D1_vs_PSHUF"]
    xy = e3["2x2|Y"]
    for nm, c, rec in (("D1 full absolute unit", D1, 0.42), ("PTOP top-quartile cells", PT, 0.48), ("PREST rest of cells", PR, 0.18),
                       ("PSHUF position-shuffled cells", PS, 0.08)):
        w = wilson(c["k"], c["n"])
        value(f"Table 346 fresh slots: {nm}, share Y", None if nm.startswith(("PT", "PR", "PS")) else rec, c["k"] / c["n"],
              "NEW" if nm.startswith(("PT", "PR", "PS")) else "MATCH",
              src_ref("exp36", "results/e3_replicate.json", f"T10_fresh_k10_19.profiles.cells.{nm.split()[0]}.Y"), 0.005, "0h",
              f"{c['k']}/{c['n']} Wilson [{w[0]:.2f}, {w[1]:.2f}]")
    value("Table 346: McNemar top quartile vs rest (fresh slots)", None, f"{tr['n10']}:{tr['n01']}", "NEW",
          src_ref("exp36", "results/e3_replicate.json", "T10_fresh_k10_19.profiles.PTOP_vs_PREST"), "exact", "0h",
          f"exact p {mcnemar_exact(tr['n10'], tr['n01']):.2g} (file {tr['p']:.2g}, one-sided)")
    value("Table 346: McNemar full unit vs shuffled (fresh slots)", None, f"{ds['n10']}:{ds['n01']}", "NEW",
          src_ref("exp36", "results/e3_replicate.json", "T10_fresh_k10_19.profiles.D1_vs_PSHUF"), "exact", "0h")
    value("Table 346: fresh-slot seed effect RD_seed", None, xy["RD_seed"], "NEW",
          src_ref("exp36", "results/e3_replicate.json", "T10_fresh_k10_19.2x2|Y.RD_seed"), 0.005, "0h",
          f"95% [{xy['RD_seed_ci95'][0]:.2f}, {xy['RD_seed_ci95'][1]:.2f}]")
    # recompute from the slot-level rows (data/samples.jsonl, stage E3_fresh), paired on (template, slot)
    from sections.common import read_jsonl
    sl = defaultdict(dict)
    for r in read_jsonl(dep("exp36", "data/samples.jsonl")):
        if r["task"] == "T10" and r.get("stage") == "E3_fresh" and r["arm"] != "TWIN":
            sl[r["design"]][(r["template"], r["k"])] = int(r["Y"])
    sums = {d: sum(v.values()) for d, v in sl.items()}
    n10 = lambda a, b: sum(sl[a][k] == 1 and sl[b][k] == 0 for k in sl[a])
    assert (sums["D1"], sums["PTOP"], sums["PREST"], sums["PSHUF"]) == (D1["k"], PT["k"], PR["k"], PS["k"]), sums
    assert (n10("PTOP", "PREST"), n10("PREST", "PTOP")) == (tr["n10"], tr["n01"])
    assert (n10("D1", "PSHUF"), n10("PSHUF", "D1")) == (ds["n10"], ds["n01"])
    rd_seed = ((sums["D1"] + sums["D3"]) - (sums["D2"] + sums["D4"])) / (2 * 50)
    assert abs(rd_seed - xy["RD_seed"]) < 1e-9
    value("Table 346: slot-level recomputation (data/samples.jsonl, E3_fresh) reproduces the aggregates", None, True, "NEW",
          src_ref("exp36", "data/samples.jsonl", "stage==E3_fresh"), "exact", "0h",
          f"sums {sums}; McNemar PTOP:PREST {n10('PTOP', 'PREST')}:{n10('PREST', 'PTOP')}, D1:PSHUF {n10('D1', 'PSHUF')}:{n10('PSHUF', 'D1')}; RD_seed {rd_seed:.2f}")
    wl = lambda c: wilson(c["k"], c["n"])
    rows = [
        f"| top-quartile cells only, absolute unit, iteration-4 seeds | {PT['k']/PT['n']:.2f} ({PT['k']}/{PT['n']}; Wilson [{wl(PT)[0]:.2f}, {wl(PT)[1]:.2f}]) |",
        f"| the other three quartiles at the same energy | {PR['k']/PR['n']:.2f} ({PR['k']}/{PR['n']}); McNemar top quartile against rest {tr['n10']}:{tr['n01']} |",
        f"| same energy at shuffled positions | {PS['k']/PS['n']:.2f} ({PS['k']}/{PS['n']}); McNemar full unit against shuffled {ds['n10']}:{ds['n01']} |",
        f"| seed effect on the fresh slots (RD_seed) | {xy['RD_seed']:.2f} [{xy['RD_seed_ci95'][0]:.2f}, {xy['RD_seed_ci95'][1]:.2f}], at the edge of the committed +-0.10 band |",
    ]
    E = [
        edit("C8-h01", "0h", "Table 346", "**Table 346.** Connected components on 50 fresh slots (exploratory replication).",
             "**Table 346.** Connected components on 50 fresh slots (exploratory replication). (iteration-8 correction: profile rows and the fresh-slot seed effect added from the dose-unit experiment's `results/e3_replicate.json`, block T10_fresh_k10_19)", kind="caption"),
        edit("C8-h02", "0h", "Table 346", "| relative unit, iteration-5 seeds | 0.10 |\n\n**Table 347.**",
             "| relative unit, iteration-5 seeds | 0.10 |\n" + "\n".join(rows) + "\n\n**Table 347.**", kind="table_rows_insert"),
        edit("C8-h03", "0h", "7.10", "The weak plan noise of iteration 5 came from its dose unit; the absolute unit's peaky profile on a few task tokens carries the effect.",
             f"The weak plan noise of iteration 5 came from its dose unit; profile and energy each carry part of the effect on connected components (profile +0.22 [0.08, 0.36], energy +0.18 [0.06, 0.30]); the shortest-path profile contrast is confounded by a massive-activation cell holding 82% of the unit's energy{SUFFIX}."),
        edit("C8-h04", "0h", "closing", "the absolute unit concentrates 81% of its energy on a few task tokens, and the same energy at shuffled positions moves almost nothing.",
             f"on connected components the absolute unit concentrates 81% of its energy in its top quartile of cells, on bands of a few task tokens (on shortest path a different quantity, one massive-activation cell, holds 82%), profile and energy each carry part of the effect (+0.22 [0.08, 0.36] and +0.18 [0.06, 0.30]), and the same energy at shuffled positions moves almost nothing{SUFFIX}."),
    ]
    return {"edits": E, "verdict": "ADDED (Table 346 rows)", "summary": {"PTOP": PT["k"], "PREST": PR["k"], "D1": D1["k"], "PSHUF": PS["k"],
                                                                         "RD_seed": xy["RD_seed"], "RD_seed_ci": xy["RD_seed_ci95"]}}


# ------------------------------------------------------------------------------------------------ 0i
def item_i(ctx: dict[str, Any]) -> dict[str, Any]:
    ar = read_json(dep("exp37", "results/arm_rates.json"))["level_b"]["T03"]
    lvs = read_json(dep("exp37", "results/L_vs_S.json"))
    rt = read_json(dep("exp37", "results/ratio_tests.json"))["levels"]["b"]["per_task"]["T03"]
    pc = read_json(dep("exp37", "results/program_classes.json"))
    cl, tech = defaultdict(set), defaultdict(Counter)
    for k, v in pc.items():
        if v["final_class"] == "KNOWN OUTSIDE CATALOGUE" and v.get("is_first_of_distinct"):
            t, a, _ = k.split("|")
            cl[(t, a)].add(v["merged_cluster_id"])
            nm = v["named_algorithm"].lower()
            fam = ("value-range binary search" if "binary search" in nm else "Fenwick tree order statistics" if "fenwick" in nm
                   else "treap" if "treap" in nm else "bucket select" if "bucket" in nm else
                   "partial selection sort" if "selection sort" in nm else nm)
            tech[(t, a)][fam] += 1
    arm_name = {"S": "search", "L": "larger mutator (qwen3-235b)", "I0": "instruction only", "EAP": "enumerate and pick",
                "NE": "no evolution", "BINT": "base intent", "B0": "neutral twin"}
    rows = []
    for a in ("S", "L", "I0", "EAP", "NE", "BINT", "B0"):
        x = lvs["L"] if a == "L" else ar[a]
        k, n = x["X_b"], x["N"]
        ci = clopper_pearson(k, n)
        nclu = len(cl[("T03", a)])
        assert nclu == x["clusters_b"], (a, nclu, x["clusters_b"])
        rows.append({"task": "T03", "arm": a, "arm_name": arm_name[a], "level_b_programs": k, "calls": n, "rate": k / n,
                     "rate_cp95_lo": ci[0], "rate_cp95_hi": ci[1], "merged_clusters": nclu,
                     "techniques": "; ".join(f"{t} {c}" for t, c in tech[("T03", a)].most_common())})
        value(f"search level b, T03, arm {a}: programs / calls", None, f"{k}/{n}", "NEW",
              src_ref("exp37", "results/arm_rates.json" if a != "L" else "results/L_vs_S.json", f"level_b.T03.{a}.X_b"), "exact", "0i",
              f"rate {k/n:.4f} [CP {ci[0]:.4f}, {ci[1]:.4f}], {nclu} clusters")
    write_csv(TABLES / "search_by_arm.csv", rows, list(rows[0].keys()))
    si = rt["secondary"]["S_vs_I0"]
    R = (si["X_S"] / si["N_S"]) / (si["X_K"] / si["N_K"])
    value("search vs instruction-only rate ratio (level b, T03)", None, R, "NEW",
          src_ref("exp37", "results/ratio_tests.json", "levels.b.per_task.T03.secondary.S_vs_I0.R_hat"), 0.005, "0i",
          f"lower 95% bound {si['LB95']:.2f} (conditional binomial, the file's method)")
    assert abs(R - si["R_hat"]) < 1e-9
    d = Counter(v["final_class"] for v in pc.values() if v.get("is_first_of_distinct"))
    value("Table 371 search row: distinct / catalogue / known outside / degenerate", "816 / 707 / 103 / 6",
          f"{sum(d.values())} / {d['CATALOGUE VARIANT']} / {d['KNOWN OUTSIDE CATALOGUE']} / {d['DEGENERATE']}",
          "MATCH" if (sum(d.values()), d["CATALOGUE VARIANT"], d["KNOWN OUTSIDE CATALOGUE"], d["DEGENERATE"]) == (816, 707, 103, 6) else "CORRECTED",
          src_ref("exp37", "results/program_classes.json", "is_first_of_distinct"), "exact", "0i")
    S, L, I0 = rows[0], rows[1], rows[2]
    rate = lambda r: f"{r['level_b_programs']} of {r['calls']:,} calls ({r['rate']:.4f} [{r['rate_cp95_lo']:.4f}, {r['rate_cp95_hi']:.4f}], {r['merged_clusters']} merged cluster{'s' if r['merged_clusters'] != 1 else ''})"
    txt = (f"search {rate(S)} against {rate(I0)} for the instruction alone (rate ratio {R:.1f}, lower 95% bound {si['LB95']:.2f}, "
           f"short of the committed 10x), 0 of 1,250 for enumerate and pick and 0 of 500 without evolution; the larger mutator "
           f"reached {rate(L)}")
    E = [
        edit("C8-i01", "0i", "Table 372", "| Search claim | Not met at levels a and b | 6.65 times on kth smallest at level a; 78 known techniques against 0 at level b on kth smallest only; 0 novel |",
             f"| Search claim | Not met at levels a and b | 6.65 times on kth smallest at level a; at level b on kth smallest only, {txt}; 0 novel (iteration-8 correction) |", kind="table_row"),
        edit("C8-i02", "0i", "7.10", "Evolutionary search with an evaluator reaches known techniques outside the catalogue on kth smallest at a rate no arm that draws single samples approaches (78 distinct programs against at most 2).",
             f"Evolutionary search with an evaluator reaches known techniques outside the catalogue on kth smallest: {txt}; about five techniques in all (value-range binary search, Fenwick tree order statistics, a treap, bucket select, partial selection sort){SUFFIX}."),
        edit("C8-i03", "0i", "closing", "against 0 for enumerate and pick, 0 for the same prompt without evolution and 2 for the instruction alone.",
             f"against 0 of 1,250 calls for enumerate and pick, 0 of 500 for the same prompt without evolution and 2 of 500 for the instruction alone: rates of {S['rate']:.3f} and {I0['rate']:.3f}, a ratio of {R:.1f} with a lower 95% bound of {si['LB95']:.2f}, short of the committed 10x{SUFFIX}."),
        edit("C8-i04", "0i", "7.11", "Fourth, evolutionary search found known techniques outside the catalogue on kth smallest at a rate no knob applied to single samples approaches,",
             f"Fourth, evolutionary search found known techniques outside the catalogue on kth smallest at {S['rate']:.3f} per call against {I0['rate']:.3f} for the instruction alone (ratio {R:.1f}, lower bound {si['LB95']:.2f}, short of the committed 10x; iteration-8 correction),"),
    ]
    return {"edits": E, "verdict": "RESTATED (rates and clusters)", "summary": {"rate_ratio": R, "LB95": si["LB95"], "rows": rows}}


# ------------------------------------------------------------------------------------------------ 0j
def item_j(ctx: dict[str, Any]) -> dict[str, Any]:
    t2 = read_json(dep("exp35", "results/test2.json"))["per_unit"]
    ph = read_json(dep("exp35", "results/posthoc.json"))["B3"]["twin_vs_sweep_T1"]
    c10 = t2["B3"]["cells"]["T1.0_p1"]
    k10 = round(c10["a_min"] * c10["n"])
    w = wilson(k10, c10["n"])
    pred = c10["pred_a_min"]
    value("B3 T1.0 Wilson 95% for 20/50", None, w, "NEW", src_ref("exp35", "results/test2.json", "per_unit.B3.cells.T1.0_p1"), 0.005, "0j",
          f"prediction {pred:.3f} outside: {not (w[0] <= pred <= w[1])}")
    (tk, tn), (sk, sn) = ph["twin"], ph["sweep_T1.0_p1"]
    pf = fisher_exact_two_sided(tk, tn - tk, sk, sn - sk)
    value("B3 stream-lean Fisher p (twin 20/100 vs sweep 20/50)", None, pf, "NEW",
          src_ref("exp35", "results/posthoc.json", "B3.twin_vs_sweep_T1.fisher_p"), 0.0005, "0j", f"file {ph['fisher_p']:.4f}")
    assert abs(pf - ph["fisher_p"]) < 5e-4
    value("B3 twin minority share: Table 330 (Prim only) vs posthoc (off the Kruskal default)", 0.19, tk / tn, "CARRIED",
          src_ref("exp35", "results/posthoc.json", "B3.twin_vs_sweep_T1.twin"), 0.0, "0j",
          "Table 330 counts Prim with heap 19 of 100 (one disputed program not counted); posthoc.json counts 20 of 100 off the Kruskal default (19 Prim + 1 disputed); both are right under their definitions, the report's 0.19 stays")
    maes = {u: t2[u]["MAE"] for u in ("B3", "A3", "B6")}
    for u, rec in (("B3", 0.083), ("A3", 0.105), ("B6", 0.043)):
        value(f"temperature unit {u} MAE", rec, maes[u], "MATCH", src_ref("exp35", "results/test2.json", f"per_unit.{u}.MAE"), 0.0005, "0j",
              f"test 2 {'pass' if t2[u]['pass'] else 'fail'}")
    mm = read_json(dep("exp33", "results/m_manifold.json"))
    sem = mm["probes"]["T2|seed_sem|-|-"]
    nul = mm["paraphrase_null"]
    value("semantic seed null percentile", 94.0, sem["null_percentile"], "CORRECTED", src_ref("exp33", "results/m_manifold.json", "probes.T2|seed_sem|-|-.null_percentile"), 0.05, "0j",
          f"D {sem['D']:.4f} against the null 95th percentile {nul['D_95']:.4f}: on the boundary")
    cfg = dep("exp33", "src/cfg7.py").read_text()
    assert 'TRAIN_W = ("W1", "W2", "W3")' in cfg and 'HELD_W = "W5"' in cfg
    bans = {w_: mm["probes"][f"T2|ban|{w_}|-"]["D"] for w_ in ("W1", "W2", "W3", "W4", "W5")}
    value("manifold: training templates of the map", None, "W1, W2, W3 (TRAIN_W); held-out W5 (HELD_W); W4 reported separately", "NEW",
          src_ref("exp33", "src/cfg7.py", "TRAIN_W, HELD_W"), "exact", "0j",
          "D by template: " + ", ".join(f"{k} {v:.2f}" for k, v in bans.items()))
    E = [
        edit("C8-j01", "0j", "closing", "Temperature acts on the algorithm only through the fork. Dividing the fork logits by T predicted the minority share at each temperature before sampling within the committed error on Gemma's grid task (mean absolute error 0.026) and on minimum spanning tree weight (0.083, with the observed drop twice the predicted one), just outside it on trapped rain water (0.105), and not in direction on valid anagram, where a second decision follows the fork.",
             f"Temperature acts through one or two decision tokens whose logits fix the odds. Dividing the fork logits by T predicted the minority share before sampling within the committed error on Gemma's grid task (mean absolute error 0.026, pass) and on minimum spanning tree weight (0.083, pass), although there the T 1.0 prediction ({pred:.3f}) lies outside the observed Wilson 95% interval for {k10} of 50 ([{w[0]:.2f}, {w[1]:.2f}]) and the stream-lean explanation (the twin's {tk} of {tn} against the sweep's {sk} of {sn}, Fisher p {pf:.3f}) is post hoc; it fails on trapped rain water (0.105, which has a second opening with its own split) and on valid anagram, which has a second decision a few tokens after the fork{SUFFIX}."),
        edit("C8-j02", "0j", "7.3.8", "All five ban templates lie outside it (D 1.73 to 2.62, at the 100th percentile), each displaced toward the second choice",
             "Every ban template lies outside it (D 1.73 to 2.62, at the 100th percentile; the first three, W1-W3, are training templates of the map, so the conclusion that bans leave the null rests on the held-out fifth template, D 2.62, and the fourth, D 1.73; iteration-8 correction), each displaced toward the second choice"),
        edit("C8-j03", "0j", "7.3.8", "The semantic seed was predicted outside and lies inside, at the 94th percentile (Table 309).",
             f"The semantic seed was predicted outside and lies on the boundary, at the {sem['null_percentile']:.1f}th percentile (D {sem['D']:.3f} against a null 95th percentile of {nul['D_95']:.3f}; Table 309){SUFFIX}."),
        edit("C8-j04", "0j", "Table 309", "**Table 309.** Shortest path: placement of prompts in the rank-16 DAS coordinates against the paraphrase null.",
             "**Table 309.** Shortest path: placement of prompts in the rank-16 DAS coordinates against the paraphrase null. (iteration-8 correction: the first three ban templates are training templates of the map; the semantic seed sits on the boundary of the null 95%)", kind="caption"),
        edit("C8-j05", "0j", "Table 309", "| ban, first template | 2.25 | 100.0 | no | 1.55 |", "| ban, first template (training template of the map) | 2.25 | 100.0 | no | 1.55 |", kind="table_row"),
        edit("C8-j06", "0j", "Table 309", "| ban, second template | 1.95 | 100.0 | no | 1.39 |", "| ban, second template (training template of the map) | 1.95 | 100.0 | no | 1.39 |", kind="table_row"),
        edit("C8-j07", "0j", "Table 309", "| ban, third template | 1.79 | 100.0 | no | 1.15 |", "| ban, third template (training template of the map) | 1.79 | 100.0 | no | 1.15 |", kind="table_row"),
        edit("C8-j08", "0j", "Table 372", "| Manifold claim | Bans outside the null, seeds and instructions inside; semantic seed missed | D 1.73 to 2.62 against a null 95th percentile of 1.13 |",
             f"| Manifold claim | Bans outside the null (resting on the held-out templates, fourth D 1.73 and fifth D 2.62; the first three are training templates), seeds and instructions inside; semantic seed on the boundary ({sem['null_percentile']:.1f}th percentile) (iteration-8 correction) | D 1.73 to 2.62 against a null 95th percentile of 1.13 |", kind="table_row"),
    ]
    return {"edits": E, "verdict": "RESTATED (per unit)", "summary": {"B3_T1_wilson": w, "B3_T1_pred": pred, "fisher_p": pf,
                                                                       "semantic_seed_percentile": sem["null_percentile"], "maes": maes}}


# ------------------------------------------------------------------------------------------------ 0k
PATH_RX = re.compile(r"[A-Za-z0-9_./-]+\.(?:jsonl|json|py|md|npz)")


def item_k(ctx: dict[str, Any]) -> dict[str, Any]:
    rt = read_json(dep("exp36", "results/retag.json"))
    mv = rt["movability_at_D_star"]
    movable = [t for t, v in mv.items() if v["movable"]]
    value("retag: D_star", None, rt["D_star"], "NEW", src_ref("exp36", "results/retag.json", "D_star"), "exact", "0k")
    value("retag: movable tasks at D*", None, movable, "NEW", src_ref("exp36", "results/retag.json", "movability_at_D_star"), "exact", "0k")
    ps = ("(ban-free unit and iteration-5 seeds; re-tagged by iteration 7's dose-unit experiment, Section 7.6: at the moving design "
          "D* = D1 the plan-sampler rule is still disconfirmed, at 2 of 5) (iteration-8 correction)")
    ms = ("(ban-free unit and iteration-5 seeds; re-tagged by iteration 7's dose-unit experiment, Section 7.6: at D* = D1 kth smallest "
          "and connected components are movable, and shortest path, two sum and the grid are not) (iteration-8 correction)")
    tag = "(ban-free unit and iteration-5 seeds; pending the 2x2 of Step K)"
    E = [
        edit("C8-k01", "0k", "5.7", f"**The plan sampler comparison is DISCONFIRMED** (Table 207) {tag}.", f"**The plan sampler comparison is DISCONFIRMED** (Table 207) {ps}."),
        edit("C8-k02", "0k", "5.11", f"Not supported as a strong predictor, and not disconfirmed {tag}:", f"Not supported as a strong predictor, and not disconfirmed {ms}:"),
        edit("C8-k03", "0k", "5.11", f"Disconfirmed (1 of 5 decisive tasks) {tag};", f"Disconfirmed (1 of 5 decisive tasks) {ps};"),
        edit("C8-k04", "0k", "6.2.4", f"(correction in Section 5.11) {tag}.", f"(correction in Section 5.11) {ms}."),
    ]
    # file names lost between the record audit's corrected report and the current report
    old = (EVAL6_DIR / "report_corrected.md").read_text().split("\n")
    cur = REPORT.read_text().split("\n")
    sm = difflib.SequenceMatcher(None, old, cur, autojunk=False)
    lost = []
    for tagx, i1, i2, j1, j2 in sm.get_opcodes():
        if tagx == "replace":
            for a, b in zip(range(i1, i2), range(j1, j2)):
                miss = sorted(set(PATH_RX.findall(old[a])) - set(PATH_RX.findall(cur[b])))
                if miss:
                    lost.append({"old_line": a + 1, "new_line": b + 1, "lost": miss})
    cfg = "`src/cfg.py` line 7; file name restored, iteration-8 correction"
    fixes = []
    # Table 238 caption (two references)
    fixes.append(("Source: the plan-noise results and per-row samples of the engine control.",
                  "Source: engine control `results/pn.json`, `data/samples.jsonl` (iteration-8 correction: file names restored)."))
    fixes.append(("(from the per-row labels of the samples, the engine-a rows coming from iteration 4)",
                  "(from the per-row labels of `data/samples.jsonl` (file name restored, iteration-8 correction), the engine-a rows coming from iteration 4)"))
    fixes.append(("(MDS stress not recorded). Points: 28 prompt states", "(MDS stress not recorded in `top5_push.json`; file name restored, iteration-8 correction). Points: 28 prompt states"))
    fixes.append(("The deviation log records what did not run: the clamp read-back and matched-norm realisation tests as separate unit tests (the matched norm is imposed by construction in the clamp code,",
                  "The deviation log records what did not run: the clamp read-back and matched-norm realisation tests as separate unit tests (the matched norm is imposed by construction in the clamp code, `src/clamp.py` (file name restored, iteration-8 correction),"))
    fixes.append(("The deviation log of the Gemma experiment adds what it did not run: the clamp read-back and matched-norm realisation tests as separate unit tests (the matched norm is imposed by construction in the clamp code,",
                  "The deviation log of the Gemma experiment adds what it did not run: the clamp read-back and matched-norm realisation tests as separate unit tests (the matched norm is imposed by construction in the clamp code, `src/clamp.py` (file name restored, iteration-8 correction),"))
    fixes.append(("(MDS stress not recorded). Points: one point per centroid", "(MDS stress not recorded in `results/geometry.json`; file name restored, iteration-8 correction). Points: one point per centroid"))
    fixes.append(("to the last token of the user message), so Gemma does not", f"to the last token of the user message, {cfg}), so Gemma does not"))
    # the four Gemma figure notes share the same clause; anchor each on its own PCA numbers
    for ln in (5932, 5947, 5960, 5966):
        line = cur[ln - 1]
        i = line.index("to the last token of the user message), so neither")
        m = re.search(r"\(first component 0\.\d\d, second 0\.\d\d", line[i:])
        seg = line[i:i + m.end()]
        fixes.append((seg, seg.replace("to the last token of the user message), so neither", f"to the last token of the user message, {cfg}), so neither", 1)))
    for n, (o, nw) in enumerate(fixes, 1):
        assert "iteration-8 correction" in nw, nw
        E.append(edit(f"C8-k1{n:02d}", "0k", "file names", o, nw, kind="file_name_restore"))
    value("file-name losses found by difflib (report_corrected.md -> current_report.md)", None, len(lost), "NEW",
          src_ref("eval6", "report_corrected.md") + " vs current_report.md", "exact", "0k", "; ".join(f"line {x['new_line']}: {x['lost']}" for x in lost))
    return {"edits": E, "verdict": "CORRECTED (tags replaced, file names restored)", "lost": lost, "n_restore_edits": len(fixes)}
