#!/usr/bin/env python3
"""Round-one audit: when is the algorithm chosen?  Entry point.

Runs the stages that are missing (or all with --rerun) and assembles eval_out.json (exp_eval_sol_out) and
corrections.json from their outputs:
  inventory.py  (G2)       -> results/inventory.json
  locus.py      (0a, GPU)  -> results/locus.json, tables/locus_cells.csv
  geometry.py   (0b)       -> results/geometry.json, tables/geometry_stability.csv
  tables.py     (G3, 0c-0g)-> results/tables.json, results/harmonise.json, results/reference_map.json,
                              tables/perturbation_table.csv, tables/knob_table.csv
  results/positioning.json (0h, dated web check, written from logs/web/*.md)
  figures.py               -> figures/*.pdf|png
No generation, no LLM calls, no OpenRouter spend.

Usage: uv run eval.py [--rerun]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from loguru import logger

from common import HERE, RES, TAB, clean, jdump, setup_logging

STAGES = [("inventory", "inventory.py", RES / "inventory.json"), ("locus", "locus.py", RES / "locus.json"),
          ("geometry", "geometry.py", RES / "geometry.json"), ("tables", "tables.py", RES / "tables.json"),
          ("figures", "figures.py", RES / "figures.json"), ("audit", "audit.py", RES / "audit.json"),
          ("audit_extra", "audit_extra.py", RES / "audit_extra.json")]
VERDICT_CODE = {"R (no candidate passed the 20-point rule)": 0, "NOT PASSING": 0, "POST-COMMIT READOUT": 1,
                "DECISION LOCUS": 2}


def run_stages(rerun: bool) -> dict:
    timing = {}
    for name, script, out in STAGES:
        if out.exists() and not rerun:
            logger.info(f"stage {name}: output present, skipped")
            continue
        t0 = time.time()
        logger.info(f"stage {name}: running {script}")
        subprocess.run([sys.executable, str(HERE / script)], check=True, cwd=HERE)
        timing[name] = time.time() - t0
    return timing


def fnum(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def locus_section(loc: dict) -> tuple[dict, dict]:
    sec = {"failure_cause": loc["failure_cause"], "device": loc["device"], "dtype": loc["dtype"],
           "solver_unit_test": {t: {"passed": u["passed"], "max_rel_coef_diff": u["max_rel_coef_diff"],
                                    "n_checks": len(u["checks"]),
                                    "max_rel_coef_diff_vs_sklearn_default_tol": max(c["rel_coef_diff_vs_default_tol"] for c in u["checks"])}
                                for t, u in loc["unit_test"].items()},
           "design": ("contrast W = within-ban same prompts (T1 G2 DFS=1 vs BFS=0, unit_dijkstra excluded; T2 G2 BF_SPFA=1 vs "
                      "DIJKSTRA=0); P1 baseline-default vs ban-default; P2 baseline-default vs ban-substitute. LOPO 10 folds; "
                      "in-fold StandardScaler + PCA(64); L2 logistic, balanced class weights, unpenalised intercept, C in "
                      "{0.01,0.1,1} by inner GroupKFold(3) pooled log-loss; batched Newton-IRLS in torch (float32 on GPU). "
                      "Nulls: 200 global + 200 within-paraphrase refits for W (same permutation vectors at every layer of a "
                      "position), 50 global for P1/P2."),
           "timing_s": loc["timing"], "tasks": {}}
    flat = {}
    for t, T in loc["tasks"].items():
        W = T["contrasts"]["W"]["positions"]
        lm = {}
        for p, pr in W.items():
            li = pr["layers"].index(pr["L_star"])
            lm[p] = {"n": pr["n"], "n_min": pr["n_min"], "median_k": pr["median_k"], "L_star": pr["L_star"],
                     "layer_max_BA": pr["layer_max_BA"], "BA_ci_at_L_star": pr["BA_ci"][li], "AUC_at_L_star": pr["AUC"][li],
                     "CE_bits_at_L_star": pr["CE_bits"][li], "IG_bits_at_L_star": pr["IG_bits"][li],
                     "C_chosen_at_L_star": pr["C_chosen"][li], "null_global_p95": pr["layer_max_null_global_p95"],
                     "null_within_p95": pr["layer_max_null_within_p95"], "p_layermax_global": pr["p_layermax_global"],
                     "p_layermax_within": pr["p_layermax_within"], "n_precommit": pr["n_precommit"],
                     "precommit_class_counts": pr["precommit_class_counts"],
                     "precommit_layer_max_BA": pr.get("precommit_layer_max_BA"),
                     "BA_text": T["text"]["per_position"].get(p, {}).get("BA_text"),
                     "DiM_AUC_at_L_star": pr["DiM_AUC"][li], "DiM_AUC_ci": pr["DiM_AUC_ci"][li]}
        curve = {k: v["BA_text"] for k, v in T["text"]["curve"].items()}
        ks = sorted(int(k) for k in curve)
        first_reveal = next((k for k in ks if curve[str(k)] >= 0.6), None)
        rule = T["rule"]
        mech = rule["mechanical_locus"]
        qual = rule["qualified_verdict"]
        if t == "T2":
            target = ("The written prefix first separates the classes at k=4 (BA_text 0.762 on tokens 0..3: Dijkstra rows "
                      "write '```python\\nimport' then ' heapq'; BF_SPFA rows write '```python\\nfrom collections import' then "
                      "' deque'), so the deciding token is generated index 3 and it is emitted from the state at k=3 (absolute "
                      "index prompt_len+2). States k=1..3 are unsaved: extract them in the next round's GPU step. exp3's own "
                      "resampling fork screen independently confirmed forks at generated index 3 ('import', TVD 0.80 and "
                      "0.77; exp3/forks.json T2|ban|0 and T2|ban|1). The literal rule (first k with BA_text >= 0.8) gives "
                      f"k={T['text']['first_k_BA_text_ge_0.8']}.")
        else:
            target = ("No prefix up to k=64 reaches BA_text 0.8 (max 0.673 at k=7..16): DFS and BFS rows share the commit "
                      "token (' deque' for 55/78 DFS and 21/21 BFS rows), so the AST commit index does not separate the classes "
                      "on T1 and the within-ban signal at every saved position is paraphrase-level (within-paraphrase null "
                      "p95 >= observed). Extraction target: per-row first token where DFS and BFS code diverge (beyond k=64, "
                      "e.g. pop vs popleft), plus k=1..7.")
        sec["tasks"][t] = {"counts": T["counts"], "commit_idx_distribution": T["commit_idx_distribution"],
                           "pool_join": T["pool_join"], "position_order": rule["position_order"],
                           "positions_unavailable": T["contrasts"]["W"].get("positions_unavailable", {}),
                           "layer_max_table": lm, "rule_trace": rule["trace"], "mechanical_locus": mech,
                           "qualified_verdict": qual, "decision_locus_positions": rule["decision_locus_positions"],
                           "power_note": rule["power_note"], "use_for_next_round": rule["use_for_next_round"],
                           "text_locus_curve": curve, "text_first_k_BA_ge_0.8": T["text"]["first_k_BA_text_ge_0.8"],
                           "text_first_k_BA_ge_0.6": first_reveal, "extraction_target": target,
                           "decoded_prefixes": T["text"].get("decoded_prefixes"),
                           "token_strings_first12": T["text"].get("token_strings_first12"),
                           "dim": T["dim"], "commit_aligned_curve": T["commit_aligned_curve"],
                           "R_compliance_preview": T["R_compliance_preview"],
                           "pca_views_explained": {k: v["explained"] for k, v in T["pca_views"].items()},
                           "positive_controls": {c: {p: {"layer_max_BA": pr["layer_max_BA"], "L_star": pr["L_star"],
                                                         "p_layermax_global": pr["p_layermax_global"], "n": pr["n"]}
                                                     for p, pr in T["contrasts"][c]["positions"].items()} for c in ("P1", "P2")},
                           "layer_convention": T["layer_convention"]}
        kp = W["k_pre"]
        kli = kp["layers"].index(kp["L_star"])
        trace = {r["position"]: r for r in rule["trace"]}
        flat.update({f"locus_{t}_BA_kpre": kp["layer_max_BA"], f"locus_{t}_Lstar_kpre": kp["L_star"],
                     f"locus_{t}_delta_vs_R_kpre": trace["k_pre"]["delta_vs_R"],
                     f"locus_{t}_BA_R": W["R"]["layer_max_BA"], f"locus_{t}_BA_k8": W["k8"]["layer_max_BA"],
                     f"locus_{t}_BA_text_kpre": T["text"]["per_position"]["k_pre"]["BA_text"],
                     f"locus_{t}_p_within_kpre": kp["p_layermax_within"],
                     f"locus_{t}_verdict_mechanical_is_R": 1.0 if mech == "R" else 0.0,
                     f"locus_{t}_verdict_code": VERDICT_CODE.get(qual, 0),
                     f"locus_{t}_n_decision_locus_positions": len(rule["decision_locus_positions"]),
                     f"text_locus_{t}_first_k_ge_0p8": T["text"]["first_k_BA_text_ge_0.8"] or -1,
                     f"text_locus_{t}_first_k_ge_0p6": first_reveal or -1,
                     f"dim_auc_{t}_kpre": T["dim"]["k_pre"]["DiM_AUC_at_L_star"],
                     f"dim_auc_{t}_R": T["dim"]["R"]["DiM_AUC_at_L_star"],
                     f"dim_auc_{t}_k8": T["dim"]["k8"]["DiM_AUC_at_L_star"],
                     f"R_compliance_{t}_spearman": T["R_compliance_preview"]["spearman_rho"],
                     f"R_compliance_{t}_exact_p": T["R_compliance_preview"]["exact_perm_p"]})
        flat[f"locus_{t}_delta_vs_R_mech"] = trace[mech]["delta_vs_R"] if mech in trace else 0.0
    return sec, flat


def fork_thresholds() -> dict:
    """exp3 fork confirmation-threshold sensitivity (TVD 0.10/0.15/0.20/0.30) from exp3/forks.json."""
    from common import EXP
    d = json.loads((EXP["exp3"] / "forks.json").read_text())
    cands = []
    for c in d.get("forks", []):
        cands.append({k: c.get(k) for k in ("bp_id", "task", "condition", "t", "token", "tvd", "p_perm", "commit_idx",
                                            "confirmed_tvd0.10", "confirmed_tvd0.15", "confirmed_tvd0.20", "confirmed_tvd0.30",
                                            "confirmed")})
    summ = {}
    for th in ("0.10", "0.15", "0.20", "0.30"):
        for t in ("T1", "T2"):
            summ[f"{t}_confirmed_at_tvd{th}"] = sum(1 for c in cands if c["task"] == t and c.get(f"confirmed_tvd{th}"))
    return {"candidates": cands, "summary": summ, "source": "exp3/forks.json#forks"}


def geometry_section(g: dict) -> tuple[dict, dict]:
    grid = [c for c in g["grid"]]
    head = {}
    for c in grid:
        if c["kind"] == "forced" and ((c["task"] == "t2" and c["layer"] == 24) or (c["task"] == "t1" and c["layer"] == 27)):
            head[f"{c['task']}_L{c['layer']}_k{c['k']}"] = {k: v for k, v in c.items() if k not in ("task", "layer", "k", "kind")}
    sens = g["reproduce"]["t2"]["sensitivity"]
    sec = {"reproduce": g["reproduce"], "headline_settings": head, "across_settings": g["across_settings"],
           "masked_sensitivity": [{k: c[k] for k in ("task", "layer", "k", "full_order", "share_nearest", "top1_stability")}
                                  for c in grid if c["kind"] == "masked"],
           "sensitivity_matrix_T2_dijkstra_row": sens["dijkstra_row_named"], "nearest_survivor_sensitivity": sens["nearest_survivor"],
           "wording": g["wording"], "table": "tables/geometry_stability.csv", "figure": "figures/fig_geometry_heatmap.pdf",
           "resampling": "1000 draws of 24 of 30 paraphrase ids without replacement, same ids for every mode; PCA, graph and centroids rebuilt per draw"}
    t2 = next(c for c in grid if c["task"] == "t2" and c["layer"] == 24 and c["k"] == 10 and c["kind"] == "forced")
    t1 = next(c for c in grid if c["task"] == "t1" and c["layer"] == 27 and c["k"] == 10 and c["kind"] == "forced")
    t1_24 = next(c for c in grid if c["task"] == "t1" and c["layer"] == 24 and c["k"] == 10 and c["kind"] == "forced")
    t2f = [c for c in grid if c["task"] == "t2" and c["kind"] == "forced"]
    flat = {"geo_T2_P_BF_nearest_L24_k10": t2["P_BF_SPFA_nearest"], "geo_T2_P_FW_nearest_L24_k10": t2["P_FW_nearest"],
            "geo_T2_P_BF_nearer_than_BIDIR_L24_k10": t2["P_BF_SPFA_nearer_than_BIDIR_DIJKSTRA"],
            "geo_T2_min_P_FW_nearest_all_settings": min(c["P_FW_nearest"] for c in t2f),
            "geo_T2_max_P_BF_nearest_all_settings": max(c["P_BF_SPFA_nearest"] for c in t2f),
            "geo_T1_P_DFS_nearest_L27_k10": t1["P_DFS_nearest"], "geo_T1_P_DFS_nearest_L24_k10": t1_24["P_DFS_nearest"],
            "geo_T1_P_DFS_UNITDIJ_two_nearest_L27_k10": t1["P_DFS_UNIT_DIJKSTRA_two_nearest"],
            "geo_T1_kendall_tau_mean": g["across_settings"]["t1"]["kendall_tau_b_mean"],
            "geo_T2_kendall_tau_mean": g["across_settings"]["t2"]["kendall_tau_b_mean"],
            "geo_T1_share_settings_realised_rank1": g["across_settings"]["t1"]["share_settings_realised_rank"]["1"],
            "geo_T2_share_settings_realised_rank1": g["across_settings"]["t2"]["share_settings_realised_rank"]["1"],
            "geo_T2_kruskal_stress_L24_k10": t2["kruskal_stress1_mds2"], "geo_T1_kruskal_stress_L27_k10": t1["kruskal_stress1_mds2"],
            "geo_reproduce_max_abs_diff": max(g["reproduce"]["t1"]["max_abs_diff"], g["reproduce"]["t2"]["max_abs_diff"],
                                              sens["max_abs_diff"])}
    return sec, flat


def examples_from_tables(pt: pd.DataFrame, kt: pd.DataFrame, cells: pd.DataFrame, geo: dict) -> list[dict]:
    def ev(d: dict) -> dict:
        return {k: v for k, v in d.items() if v is not None}

    ds = []
    ex = []
    for _, r in pt.iterrows():
        e = {"input": f"{r.experiment}|{r.task}|{r.condition} (type={r.type}; reference={r.reference or 'none'}; engine={r.engine})",
             "output": str(r.composition_correct),
             "predict_runner_up_share_correct": "" if pd.isna(r.runner_up_share_correct) else f"{r.runner_up_share_correct:.4f} {r.runner_up_ci_correct}",
             "predict_default_share_correct": "" if pd.isna(r.default_share_correct) else f"{r.default_share_correct:.4f} {r.default_ci_correct}",
             "metadata_source": r.source, "metadata_composition_attempted": str(r.composition_attempted),
             "metadata_type": r.type}
        e.update(ev({"eval_N": fnum(r.N), "eval_attempted": fnum(r.attempted), "eval_correct": fnum(r.correct),
                     "eval_pass_rate": fnum(r.pass_rate), "eval_pass_cost_pts": fnum(r.get("pass_cost_pts")),
                     "eval_pass_cost_ci_lo": fnum(r.get("pass_cost_ci_lo")), "eval_pass_cost_ci_hi": fnum(r.get("pass_cost_ci_hi")),
                     "eval_runner_up_share_correct": fnum(r.runner_up_share_correct),
                     "eval_runner_up_share_attempted": fnum(r.runner_up_share_attempted),
                     "eval_default_share_correct": fnum(r.default_share_correct),
                     "eval_n_distinct_labels": fnum(r.n_distinct_labels_attempted),
                     "eval_runtime_vs_ast_disagree": fnum(r.runtime_vs_ast_disagree)}))
        ex.append(e)
    ds.append({"dataset": "perturbation_table", "examples": ex})
    ex = []
    for _, r in cells.iterrows():
        e = {"input": f"{r.task}|{r.contrast}|{r.position}|layer {int(r.layer)}",
             "output": f"BA={r.BA:.4f} [{r.CI_lo:.3f},{r.CI_hi:.3f}] n={int(r.n)} n_min={int(r.n_min)}",
             "predict_probe_label": "substitute (1) vs default (0)" if r.contrast == "W" else "ban (1) vs baseline (0)",
             "metadata_C_chosen": str(r.C_chosen)}
        e.update(ev({"eval_BA": fnum(r.BA), "eval_BA_ci_lo": fnum(r.CI_lo), "eval_BA_ci_hi": fnum(r.CI_hi), "eval_AUC": fnum(r.AUC),
                     "eval_CE_bits": fnum(r.CE_bits), "eval_IG_bits": fnum(r.IG), "eval_p_global": fnum(r.p_global),
                     "eval_p_within": fnum(r.p_within), "eval_BA_text": fnum(r.BA_text),
                     "eval_BA_precommit": fnum(r.BA_precommit), "eval_n_precommit": fnum(r.n_precommit),
                     "eval_n": fnum(r.n), "eval_DiM_AUC": fnum(r.DiM_AUC)}))
        ex.append(e)
    ds.append({"dataset": "locus_cells", "examples": ex})
    ex = []
    for _, r in kt.iterrows():
        e = {"input": f"{r.task}|{r.knob} (type={r.type}; class={r.knob_class})",
             "output": str(r.compliant_composition),
             "predict_positive_target": str(bool(r.positive_target)),
             "metadata_below_depth": str(bool(r.below_depth)), "metadata_ci90": str(r.get("hill1_ci90"))}
        e.update(ev({"eval_hill1_rarefied_d25": fnum(r.hill1_rarefied), "eval_n_compliant": fnum(r.n_compliant),
                     "eval_pass_points": fnum(r.pass_points), "eval_hill1_plugin": fnum(r.hill1_plugin_compliant)}))
        ex.append(e)
    ds.append({"dataset": "knob_table", "examples": ex})
    ex = []
    for c in geo["grid"]:
        e = {"input": f"{c['task'].upper()}|{c['kind']}|layer {c['layer']}|k={c['k']}",
             "output": ">".join(c["full_order"]), "predict_nearest_survivor": c["full_order"][0],
             "metadata_share_nearest": json.dumps(c["share_nearest"])}
        vals = {"eval_top1_stability": c["top1_stability"], "eval_realised_rank": c["realised_substitute_rank_full"],
                "eval_kruskal_stress1": c.get("kruskal_stress1_mds2"), "eval_mst_added_share": c["mst_added_share"],
                "eval_geodesic_euclid_agree_share": c["geodesic_euclid_agree_share"]}
        for k in ("P_BF_SPFA_nearest", "P_FW_nearest", "P_BF_SPFA_nearer_than_BIDIR_DIJKSTRA", "P_DFS_nearest",
                  "P_UNIT_DIJKSTRA_nearest", "P_DFS_UNIT_DIJKSTRA_two_nearest"):
            if k in c:
                vals[f"eval_{k}"] = c[k]
        e.update(ev({k: fnum(v) for k, v in vals.items()}))
        ex.append(e)
    ds.append({"dataset": "geometry_grid", "examples": ex})
    return ds


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", action="store_true")
    args = ap.parse_args()
    setup_logging("eval")
    timing = run_stages(args.rerun)
    loc = json.loads((RES / "locus.json").read_text())
    geo = json.loads((RES / "geometry.json").read_text())
    tab = json.loads((RES / "tables.json").read_text())
    pos = json.loads((RES / "positioning.json").read_text())
    inv = json.loads((RES / "inventory.json").read_text())
    harm = json.loads((RES / "harmonise.json").read_text())
    pt = pd.read_csv(TAB / "perturbation_table.csv")
    kt = pd.read_csv(TAB / "knob_table.csv")
    cells = pd.read_csv(TAB / "locus_cells.csv")
    figs = json.loads((RES / "figures.json").read_text()) if (RES / "figures.json").exists() else {}
    aud = json.loads((RES / "audit.json").read_text()) if (RES / "audit.json").exists() else {}
    aud2 = json.loads((RES / "audit_extra.json").read_text()) if (RES / "audit_extra.json").exists() else {}
    lsec, lflat = locus_section(loc)
    gsec, gflat = geometry_section(geo)
    mb = tab["corrections"]["modal_ban_draws"]
    pg = tab["predict_gated"]
    sh = tab["sham"]
    # knob summary
    ksum = {}
    for t in ("T1", "T2"):
        k = kt[kt.task == t]
        pos_rows = k[k.positive_target]
        ksum[t] = {"n_rows": int(len(k)), "n_below_depth": int(k.below_depth.sum()),
                   "positive_target_rows": pos_rows[["knob", "type", "hill1_rarefied", "pass_points"]].to_dict("records"),
                   "positive_target_literal_rows": k[k.positive_target_literal][["knob", "type", "knob_class", "hill1_rarefied", "pass_points"]].to_dict("records"),
                   "top_diversity_knobs": k[k.knob_class == "diversity_knob"].sort_values("hill1_rarefied", ascending=False)
                   .head(6)[["knob", "hill1_rarefied", "pass_points", "n_compliant"]].to_dict("records"),
                   "ceiling_gen_then_select": k[k.ceiling_row][["knob", "hill1_rarefied", "pass_points"]].to_dict("records"),
                   "pooled_modal_ban": k[k.type == "ban_single_pooled"][["knob", "hill1_rarefied", "pass_points", "per_draw_hill", "between_draw_spread"]].to_dict("records")}
    both = {}
    for typ in sorted(set(kt.type)):
        v = [kt[(kt.task == t) & (kt.type == typ)].hill1_rarefied.mean() for t in ("T1", "T2")]
        if all(np.isfinite(v)):
            both[typ] = {"T1_mean": v[0], "T2_mean": v[1], "mean_of_tasks": float(np.mean(v))}
    ksum["mean_of_per_task_values_by_type"] = both
    ksum["statistic"] = ("compliant-only rarefied Hill-1 at depth 25 (mean over 1000 draws without replacement of exp(Shannon) "
                         "of mechanism labels; banned labels excluded as non-compliant); 90% CI from 1000 paraphrase-cluster "
                         "bootstrap resamples x 200 rarefaction draws; cells below depth marked, never extrapolated")
    ksum["positive_target_rule"] = ("Hill >= 2 at < 20 pass points; 'positive_target' counts diversity knobs and bans, "
                                    "'positive_target_literal' also counts named-mode cues (mention/listall), which recommend a mode")
    checks = list(tab["checks"])
    # locus / geometry checks against the plan
    def chk(name, expected, recomputed, ok, source, note=""):
        checks.append({"name": name, "expected": expected, "recomputed": recomputed, "match": bool(ok), "note": note, "source": source})
    for t, exp_counts in (("T1", {"G2|ban|BFS": 21, "G2|ban|DFS": 78, "G2|ban|unit_dijkstra": 1, "G1|baseline|BFS": 200}),
                          ("T2", {"G2|ban|dijkstra": 20, "G2|ban|bellman_ford_spfa": 80, "G1|baseline|dijkstra": 200})):
        got = loc["tasks"][t]["counts"]
        chk(f"exp3 {t} state-row counts", exp_counts, {k: got.get(k) for k in exp_counts},
            all(got.get(k) == v for k, v in exp_counts.items()), f"exp3/states/{t}_meta.json")
    srow = geo["reproduce"]["t2"]["sensitivity"]["dijkstra_row_named"]
    for k, v in (("BF_SPFA", 42.18), ("BIDIR_DIJKSTRA", 40.91), ("FW", 25.49), ("DIAL", 58.01)):
        chk(f"exp2 sensitivity Dijkstra row {k}", v, round(srow[k], 3), abs(srow[k] - v) <= 0.005 + 1e-9,
            "exp2/results/manipulation_sensitivity.json#t2.centroid_geodesic_sensitivity[0]")
    chk("exp2 committed matrices reproduced (T1 L27, T2 L24, k=10)", "<=0.05 abs", gflat["geo_reproduce_max_abs_diff"],
        gflat["geo_reproduce_max_abs_diff"] <= 0.05, "exp2/results/geometry_b.json")
    sd = tab["seeds"]["behaviour"]
    chk("T2 semantic seed shift toward BF_SPFA (pts, among correct)", 66.3, round(sd["T2|seed_semantic"]["BF_SPFA"]["diff_pts_among_correct"], 2),
        abs(sd["T2|seed_semantic"]["BF_SPFA"]["diff_pts_among_correct"] - 66.3) <= 0.5, "exp6/results/samples.jsonl",
        "the plan's +66.3 is a share among correct programs; among attempted it is +61.0")
    chk("T2 semantic seed DIJKSTRA share change (pts, among correct)", -67.39, round(sd["T2|seed_semantic"]["DIJKSTRA"]["diff_pts_among_correct"], 2),
        abs(sd["T2|seed_semantic"]["DIJKSTRA"]["diff_pts_among_correct"] + 67.39) <= 0.5, "exp6/results/samples.jsonl")
    chk("T1 semantic seed shift toward BIDIR_BFS (pts, among correct)", 2.2, round(sd["T1|seed_semantic"]["BIDIR_BFS"]["diff_pts_among_correct"], 2),
        abs(sd["T1|seed_semantic"]["BIDIR_BFS"]["diff_pts_among_correct"] - 2.2) <= 0.5, "exp6/results/samples.jsonl")
    ft = fork_thresholds()
    g9 = next((c for c in ft["candidates"] if c["bp_id"] == "T1|ban|0" and c["t"] == 9), None)
    if g9:
        chk("exp3 grid fork candidate (T1|ban|0, t=9) confirms at TVD 0.10 and 0.15, not 0.20", [True, True, False],
            [g9["confirmed_tvd0.10"], g9["confirmed_tvd0.15"], g9["confirmed_tvd0.20"]],
            [g9["confirmed_tvd0.10"], g9["confirmed_tvd0.15"], g9["confirmed_tvd0.20"]] == [True, True, False], "exp3/forks.json#forks")
    n_match = sum(c["match"] for c in checks)
    mismatch_notes = {
        "n gated events (primary, informative)": "3 informative events pass the literal gate: exp1 T1 ban:bfs, exp1 T2 ban:dijkstra and exp4 T1_ban1 (its forecasts are degenerate ties); the literal gate also admits exp1's nine absent-mode bans (12 in all). Under every variant no family can advance.",
        "T2 semantic seed rarefied Hill": "different statistic: this audit's compliant-only rarefied Hill-1 at depth 25 is 1.935 (plug-in 1.988); the quoted 1.99 matches the plug-in Hill over compliant programs, not the rarefied value."}
    for c in checks:
        if not c["match"] and c["name"] in mismatch_notes:
            c["explanation"] = mismatch_notes[c["name"]]
    # metrics_agg
    metrics = {**lflat, **gflat}
    metrics.update({
        "T2_pooled_substitute_share": mb["T2"]["pooled"]["share"], "T2_pooled_substitute_n": mb["T2"]["pooled"]["compliant"],
        "T1_pooled_substitute_share": mb["T1"]["pooled"]["share"], "T1_pooled_substitute_n": mb["T1"]["pooled"]["compliant"],
        "T1_n_draws_realised_mode_runner_up": mb["T1"]["n_draws_realised_mode_runner_up"],
        "T2_n_draws_realised_mode_runner_up": mb["T2"]["n_draws_realised_mode_runner_up"],
        "n_gated_events": pg["n_gated_primary"], "n_gated_events_literal": pg["n_gated_primary_literal"],
        "n_gated_disagreement_events": pg["n_disagreement_events"], "n_families_advancing": len(pg["families_advancing"]),
        "knob_positive_target_T1": int(kt[(kt.task == "T1")].positive_target.sum()),
        "knob_positive_target_T2": int(kt[(kt.task == "T2")].positive_target.sum()),
        "knob_positive_target_literal_T1": int(kt[(kt.task == "T1")].positive_target_literal.sum()),
        "knob_positive_target_literal_T2": int(kt[(kt.task == "T2")].positive_target_literal.sum()),
        "n_sham_promotions": sh["n_promotions"], "n_sham_promotions_runner_up": sum(1 for p in sh["promotions"] if p["class"] in ("runner-up", "both")),
        "n_perturbation_rows": len(pt), "n_programs": int(pt.N.sum()),
        "rival_T2_share_majority_runner_up": tab["rival"]["T2"]["share_majority_runner_up"] or 0.0,
        "n_checks": len(checks), "n_checks_match": n_match,
        "cumulative_ban_nonreplicating": 1.0 if tab["corrections"]["cumulative_bans"]["non_replicating"] else 0.0,
        "openrouter_spend_usd": 0.0,
        "audit_n_rederived": aud.get("n_rederived", 0), "audit_n_match": aud.get("n_match", 0),
        "audit_all_placebos_failed": 1.0 if aud.get("all_placebos_failed") else 0.0,
        "audit_extra_all_match": 1.0 if aud2.get("all_match") else 0.0,
        "audit_extra_all_placebos_failed": 1.0 if aud2.get("all_placebos_failed") else 0.0,
        "audit_extra_locus_T2_kpre_L8_p_within_40perm": (aud2.get("locus") or {}).get("p_within", -1.0)})
    metrics = {k: float(v) for k, v in metrics.items() if fnum(v) is not None}
    corrections = {
        "locus_probe_never_ran": {"cause": loc["failure_cause"],
                                  "now": {t: {"mechanical": lsec["tasks"][t]["mechanical_locus"], "qualified": lsec["tasks"][t]["qualified_verdict"]} for t in lsec["tasks"]},
                                  "source": "results/locus.json"},
        "same_substitute_in_five_draws": {"per_draw": {t: [{k: d[k] for k in ("experiment", "condition", "substitute", "compliant", "wilson", "composition", "source")} for d in mb[t]["draws"]] for t in mb},
                                          "pooled": {t: mb[t]["pooled"] for t in mb}},
        "cumulative_bfs_dfs_ban": tab["corrections"]["cumulative_bans"],
        "knob_table_one_statistic": ksum,
        "predict_on_gated_events": {k: pg[k] for k in ("n_events_with_forecasts", "n_generated", "n_gated_primary", "n_gated_primary_literal",
                                                       "gated_event_ids", "gating_note", "family_means_gated", "disagreement_events",
                                                       "wins_by_0.10_nats", "families_advancing", "rule", "outcome", "smoothing", "unforecast")},
        "buy_rule": tab["buy"],
        "geometry_stability_0.985": {"note": "iteration-1 point resampling on a fixed graph; replaced by paraphrase-level subsampling that rebuilds PCA, graph and centroids",
                                     "headline": {k: v for k, v in gflat.items()}},
        "seeds_double_dissociation": tab["seeds"]["double_dissociation"],
        "sham_bans": {k: sh[k] for k in ("n_sham_events", "n_promotions", "promotions", "all_promoted_are_runner_up", "note")},
        "checks": checks}
    jdump(clean(corrections), HERE / "corrections.json")
    metadata = {
        "evaluation_name": "Round-one audit: when is the algorithm chosen?",
        "description": ("Evaluation of the six iteration-1 experiments (run_4VFKidE1bxPG) read in place: locus probe on saved "
                        "Qwen3-8B states, geometry robustness, cross-experiment perturbation table, record corrections, "
                        "one-statistic knob table, PREDICT on gated events, seeds, missing outputs, sham bans, positioning. "
                        "No generation, no LLM calls, $0 OpenRouter spend."),
        "inputs": {"root": "ITER1_ROOT (sibling run on the volume; cited as expN/<path>)",
                   "experiments": {"exp1": "association (art__skdlFp_o3e9)", "exp2": "geometry (art_D6Z0Snf09sFL)",
                                   "exp3": "forking token (art_1yV2vQ0EH4OY)", "exp4": "decommitment (art_U5UKkFrOgSsE)",
                                   "exp5": "instruction tuning (art_HF8nK8B_Lqyy)", "exp6": "decoding (art_UoCVh2Qe5RZ0)"},
                   "inventory": {"n_files": inv["n_files"], "missing": inv["missing"], "file": "inventory.json"}},
        "harmonisation": {"file": "results/harmonise.json", "unmapped_to_OTHER": harm["unmapped_to_OTHER"],
                          "reference_map": "results/reference_map.json"},
        "locus": lsec, "geometry_robustness": gsec,
        "perturbation_table": {"n_rows": len(pt), "table": "tables/perturbation_table.csv", "rival": tab["rival"],
                               "figure": [figs.get("perturbation_composition_T1"), figs.get("perturbation_composition_T2")]},
        "corrections": {k: corrections[k] for k in ("same_substitute_in_five_draws", "cumulative_bfs_dfs_ban")},
        "knob_table": ksum, "predict_gated": corrections["predict_on_gated_events"], "buy": tab["buy"],
        "seeds": tab["seeds"], "missing_outputs": tab["missing_outputs"] | {"exp3_fork_threshold_sensitivity": fork_thresholds()},
        "sham_promotion": corrections["sham_bans"] | {"rows_file": "results/tables.json#sham.rows"},
        "positioning": pos, "recompute_then_compare": {"n": len(checks), "n_match": n_match, "checks": checks},
        "figures": figs, "stage_timing_s": timing, "audit": aud, "audit_extra": aud2,
        "departures": ["n=99-100 within-ban rows per task, 20-21 minority, 10 clusters: only ~15-20 BA-point effects detectable",
                       "one model, two tasks, one draw; decodability only (no causal test at the locus)",
                       "commit_idx is an AST upper bound; positions 1-3 unsaved",
                       "k_fork has no saved states on T1 and on the baseline arms (exp3 mask), so it is a T2-ban-only position",
                       "PREDICT gate: sham (absent-mode) bans excluded as uninformative; literal count reported",
                       "None-as-[] re-execution dropped (drop order item 1)"]}
    out = {"metadata": metadata, "metrics_agg": metrics, "datasets": examples_from_tables(pt, kt, cells, geo)}
    jdump(clean(out), HERE / "eval_out.json")
    logger.info(f"wrote eval_out.json ({len(metrics)} metrics, {sum(len(d['examples']) for d in out['datasets'])} examples) "
                f"and corrections.json; checks {n_match}/{len(checks)} match")


if __name__ == "__main__":
    main()
