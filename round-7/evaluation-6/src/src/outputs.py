"""eval_out.json (exp_eval_sol_out): metrics_agg M1 to M12, seven datasets, metadata.sections 0a to 0l; plus the
full, mini (3 examples per dataset) and preview (mini with strings cut to 200 characters) variants."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from common import READ_DATE, write_json


def _num(x: Any) -> float:
    if isinstance(x, bool):
        return float(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _s(x: Any) -> str:
    return x if isinstance(x, str) else json.dumps(x, default=str)


def _trunc(o: Any, n: int = 200) -> Any:
    if isinstance(o, str):
        return o[:n]
    if isinstance(o, list):
        return [_trunc(v, n) for v in o]
    if isinstance(o, dict):
        return {k: _trunc(v, n) for k, v in o.items()}
    return o


def write_outputs(*, ws: Path, corr, apply_res, by_status, lint_before, lint_after, A, B, GE, G8, H, U, nov, figs, pos,
                  audit, hashes, discrepancies, cons, J, F, L, ledger, XC, HC, cpu_secs, wall_secs) -> dict:
    cells = A["cells"]
    m: dict[str, float] = {
        "m1_n_corrections": len(corr), "m1_values_match": by_status.get("MATCH", 0),
        "m1_values_corrected": by_status.get("CORRECTED", 0), "m1_values_new": by_status.get("NEW", 0),
        "m1_values_carried": by_status.get("CARRIED", 0), "m1_apply_pass_rate": apply_res["pass_rate"],
        "m1_overlapping_corrections": len(apply_res["overlaps"]),
        "m2_lint_flags_uncorrected": len(lint_before), "m2_lint_flags_corrected": len(lint_after),
        "m3_n_cells": len(cells), "m3_cells_failing_gate": sum(1 for c in cells.values() if c.get("gate_ok") is False),
    }
    for t, cell in (("T2", "X_0-35"), ("T2", "X_12-23"), ("T03", "X_0-35"), ("T1", "X_0-35"), ("T1", "COND"),
                    ("T2", "FORCEDX_0-35"), ("T10", "FORCEDX_0-35")):
        c = cells[f"{t}|{cell}"]
        k = f"{t}_{cell}".replace("-", "_")
        m[f"m3_{k}_attempted_Y"] = c["attempted_Y"]
        m[f"m3_{k}_correct_Y"] = c["correct_Y"]
        m[f"m3_{k}_transfer_commit0"] = c["transfer"]
    for t, r in A["mr_posthoc"].items():
        m[f"m3_posthoc_correctY_vs_MR_{t}_b"] = r["correct_b"]
        m[f"m3_posthoc_correctY_vs_MR_{t}_c"] = r["correct_c"]
        m[f"m3_posthoc_correctY_vs_MR_{t}_p"] = r["correct_p"]
    for t in ("T03", "T10"):
        b, cb, pr = B["posthoc_S2"][t]
        m[f"m4_posthoc_condspan_beta_{t}"] = b
        m[f"m4_posthoc_condspan_boot_lo_{t}"] = cb[0]
        m[f"m4_posthoc_condspan_boot_hi_{t}"] = cb[1]
        m[f"m4_concordant_{t}"] = float(B["concordance"][t]["concordant"])
    m.update({"m4_S4_beta_T10": B["S4"][0], "m4_flips_S0_only_T10": B["flips_S0_vs_S4"]["S0_only"],
              "m4_flips_S4_only_T10": B["flips_S0_vs_S4"]["other_only"], "m4_flips_p_T10": B["flips_S0_vs_S4"]["p"],
              "m4_X011_off_default_T10": B["depth_redundancy"]["X_0-11_off_default"],
              "m4_X2435_off_default_T10": B["depth_redundancy"]["X_24-35_off_default"]})
    m.update({"m5_das_k1_heldout_dy": GE["das"]["1"]["das"], "m5_das_k4_heldout_dy": GE["das"]["4"]["das"],
              "m5_das_random_max_abs_dy": max(abs(v["random"]) for v in GE["das"].values()),
              "m5_das_shuffled_k1_dy": GE["das"]["1"]["shuffled"], "m5_das_k4_generation_bfs": GE["das_gen"]["bfs"],
              "m5_das_k4_generation_passing": GE["das_gen"]["passing"], "m5_readout_lasso_r2": GE["lasso"],
              "m5_readout_ridge_std_r2": GE["ridge_std"], "m5_readout_ridge_control_r2": GE["ridge_ctrl"],
              "m5_readout_ridge_delta": GE["ridge_delta"], "m5_raw_ridge_max_r2": GE["raw_ridge"][1],
              "m5_twin_pass": GE["twin_pass"], "m5_sae_top5_pass": GE["top5"]["pass"],
              "m5_sae_top5_bfs": GE["top5"]["bfs"], "m5_bfsward_pass_min_main4": GE["main4_pass"][0],
              "m5_bfsward_pass_max_main4": GE["main4_pass"][1]})
    for key, a in G8["pn_correct"].items():
        e, t, arm = key.split("|")
        m[f"m6_{t}_{arm}_{e}_correct_off_default"] = a["correct_off"]
        m[f"m6_{t}_{arm}_{e}_correct"] = a["correct"]
    for e, v in G8["screen"].items():
        m[f"m6_T2_screen_passes_{e}"] = v
        m[f"m6_T2_excess_met_pass_failed_{e}"] = G8["excess_met_pass_failed"][e]
    m.update({"m7_units": H["n_units"], "m7_b": H["b"], "m7_c": H["c"], "m7_p": H["p"],
              "m7_cluster_boot_lo": H["cluster_boot_ci"][0], "m7_cluster_boot_hi": H["cluster_boot_ci"][1],
              "m7_n_clusters": len(H["clusters"]), "m7_n_samples": H["n_samples"],
              "m7_one_unit_b": H["one_unit_first"]["b"], "m7_one_unit_c": H["one_unit_first"]["c"],
              "m7_one_unit_p": H["one_unit_first"]["p"], "m7_random_unit_median_p": H["random_unit"]["median_p"],
              "m7_random_unit_share_p_lt_05": H["random_unit"]["share_p_lt_05"],
              "m7_sign_test_per_sample_p": H["sign_test_per_sample"]["p"],
              "m7_durkalski_p": H["durkalski"]["p"] if H["durkalski"]["p"] is not None else float("nan"),
              "m7_cluster_sign_floor_p": H["cluster_floor_p"]})
    m.update({"m8_u6_t0_bfs_share": U["U6"]["t0_bfs_share"], "m8_u6_exact_binomial_p": U["U6"]["exact_binomial_p"],
              "m8_d12_reported": 1.0})
    m.update({"m9_n_programs": nov["n_programs"], "m9_n_novel_final": nov["n_novel_final"],
              "m9_kappa_merged": nov["kappa_merged_classes"] if nov["kappa_merged_classes"] is not None else float("nan"),
              "m9_kappa_exact": nov["kappa_exact_classes"] if nov["kappa_exact_classes"] is not None else float("nan"),
              "m9_programs_all_hidden_pass": sum(p["tests"]["hidden"]["all_pass"] for p in nov["programs"]),
              "m9_programs_all_stress_pass": sum(all(p["tests"][k]["all_pass"] for k in ("max_size_random",
                                                                                        "adversarial", "random_small"))
                                                 for p in nov["programs"]),
              "m9_openrouter_usd": nov["spend"]["cached_total_usd"]})
    for i, (jm, g) in enumerate(nov["gate"].items(), 1):
        m[f"m9_judge{i}_gate_merged_correct"] = g["merged_correct"]
        m[f"m9_judge{i}_gate_exact_correct"] = g["exact_correct"]
        m[f"m9_judge{i}_gate_passed"] = float(g["passed"])
    m.update({"m10_figures_verified": sum(f["exists"] for f in figs), "m10_figures_total": len(figs),
              "m10_caption_fields_min": min(f["caption_fields_present"] for f in figs)})
    vc = {v: sum(pos["verdict_counts"][t][v] for t in pos["verdict_counts"]) for v in ("occupies", "adjacent", "irrelevant")}
    m.update({"m11_quotes_verified": pos["quotes_verified"], "m11_quotes_attempted": pos["quotes_attempted"],
              "m11_queries": pos["n_queries"], "m11_scholarly_queries": pos["n_scholarly_queries"],
              "m11_hits": pos["n_hits"], "m11_unique_hits": pos["n_unique_hits"], "m11_screened": pos["n_screened"],
              "m11_occupies": vc["occupies"], "m11_adjacent": vc["adjacent"], "m11_irrelevant": vc["irrelevant"],
              "m11_consistency_check_passed": float(cons["passed"])})
    m.update({"m12_checks": audit.get("n_checks", float("nan")), "m12_mismatches": audit.get("n_mismatches", float("nan")),
              "m12_placebos_run": audit.get("n_placebos", float("nan")),
              "m12_placebos_failing": audit.get("n_placebos_failing", float("nan")),
              "m12_predict_crosschecks": XC["n_checks"], "m12_predict_crosscheck_mismatches": XC["n_mismatches"],
              "m12_headline_checks": HC.get("n_checks", -1), "m12_headline_checks_failed": HC.get("n_failed", -1),
              "m12_headline_placebos": HC.get("n_placebos", -1),
              "m12_headline_placebos_failing": HC.get("n_placebos_failing", -1),
              "m12_inputs_hashed": hashes["n_files"] - hashes["n_missing"], "m12_inputs_missing": hashes["n_missing"],
              "m12_openrouter_usd": nov["spend"]["cached_total_usd"], "m12_cpu_secs": cpu_secs,
              "m12_wall_secs": wall_secs})
    metrics = {k: _num(v) for k, v in m.items()}
    metrics = {k: (v if v == v else -1.0) for k, v in metrics.items()}  # NaN is not valid JSON for the schema

    ds = []
    ex = [{"input": c["old_text"], "output": c["new_text"], "metadata_id": c["id"], "metadata_item": c["item"],
           "metadata_also_items": c["also_items"], "metadata_section": c["section"], "metadata_table": c["table"],
           "metadata_line_at_read": c["line_at_read"], "metadata_kind": c["kind"], "metadata_values": c["values"],
           "metadata_rationale": c["rationale"],
           "eval_applies": float(next(x["pass"] for x in apply_res["checks"] if x["id"] == c["id"])),
           "eval_n_values": float(len(c["values"]))} for c in corr]
    ds.append({"dataset": "corrections", "examples": ex})
    ex = []
    for k, c in sorted(cells.items()):
        ex.append({"input": f"Stage A cell {c['cell']} on task {c['task']} (Y = {c['Y']}, default {c['default']})",
                   "output": f"attempted Y {c['attempted_Y']}/{c['n']}; correct Y {c['correct_Y']}/{c['n']}",
                   "metadata_task": c["task"], "metadata_cell": c["cell"], "metadata_twin_cell": c.get("twin_cell"),
                   "metadata_Y_ci95_cp": c["Y_ci95_cp"], "metadata_correct_Y_ci95_cp": c["correct_Y_ci95_cp"],
                   "metadata_attempted_comp": c["attempted_comp"], "metadata_correct_comp": c["correct_comp"],
                   "predict_commit0_share": f"{c['Y_share']:.4f}", "predict_correct_Y_share": f"{c['correct_Y_share']:.4f}",
                   "eval_Y_share": c["Y_share"], "eval_correct_Y_share": c["correct_Y_share"],
                   "eval_transfer_commit0": _num(c.get("transfer")), "eval_pass": c["pass"],
                   "eval_pass_ratio": _num(c.get("pass_ratio")) if c.get("pass_ratio") is not None else -1.0,
                   "eval_gate_ok": float(bool(c.get("gate_ok")))})
    ds.append({"dataset": "stage_a_cells", "examples": ex})
    ex = []
    for key, a in sorted(G8["pn_correct"].items()):
        e, t, arm = key.split("|")
        ex.append({"input": f"per-sample plan noise {arm} on {t} under engine {e}",
                   "output": f"correct off-default {a['correct_off']}/{a['correct']} correct programs; "
                             f"{a['correct_off']}/{a['n']} of all",
                   "metadata_engine": e, "metadata_task": t, "metadata_arm": arm,
                   "predict_correct_only": f"{a['correct_off']}/{a['correct']}", "eval_n": float(a["n"]),
                   "eval_correct": float(a["correct"]), "eval_off_default": float(a["off"]),
                   "eval_correct_off_default": float(a["correct_off"])})
    ds.append({"dataset": "table238_rows", "examples": ex})
    ex = [{"input": f"NLA sample {r['sample']} ({r['task']}), {r['n_units']} pre-identifying units",
           "output": f"first unit g{r['first_g']}: NLA {r['x_first']}, outside reader {r['y_first']}",
           "metadata_task": r["task"], "metadata_first_g": r["first_g"],
           "predict_nla_first_unit": str(r["x_first"]), "predict_outside_reader_first_unit": str(r["y_first"]),
           "eval_n_units": float(r["n_units"]), "eval_mean_x": r["mean_x"], "eval_mean_y": r["mean_y"]}
          for r in H["rows"]]
    ds.append({"dataset": "nla_one_unit", "examples": ex})
    ex = []
    for p in nov["programs"]:
        e = {"input": f"engine-control program {p['sha12']} ({p['engine']}, {p['arm']})",
             "output": p["final_class"], "metadata_kind": "program", "metadata_manual_read": p["manual_read"],
             "metadata_tests": {k: {kk: v[kk] for kk in ("n", "n_pass", "all_pass")} for k, v in p["tests"].items()},
             "metadata_nearest3": p["nearest3"], "predict_manual": p["manual_class"],
             "eval_hidden_pass": float(p["tests"]["hidden"]["all_pass"]), "eval_novel": float(p["final_class"] == "NOVEL")}
        for i, (jm, c) in enumerate(p["judge_majority"].items(), 1):
            e[f"predict_judge{i}"] = c
        ex.append(e)
    for c in nov["controls"]:
        e = {"input": f"control {c['cid']} ({c['kind']})", "output": c["truth"], "metadata_kind": "control",
             "metadata_tests": {k: {kk: v[kk] for kk in ("n", "n_pass", "all_pass")} for k, v in c["tests"].items()},
             "eval_hidden_pass": float(c["tests"]["hidden"]["all_pass"])}
        for i, (jm, cl) in enumerate(c["judge_majority"].items(), 1):
            e[f"predict_judge{i}"] = cl
            merge = {"LABELLER_MISS": "CAT", "CATALOGUE_VARIANT": "CAT"}
            e[f"eval_judge{i}_correct_merged"] = float(merge.get(cl, cl) == merge.get(c["truth"], c["truth"]))
        ex.append(e)
    ds.append({"dataset": "novelty_judgements", "examples": ex})
    ds.append({"dataset": "figure_markers", "examples": [
        {"input": f"{f['fig_id']} ({', '.join(f['files'])})", "output": f["caption"], "metadata_sha256": f["sha256"],
         "metadata_code_ref": f["code_ref"], "metadata_insert_after": f["insert_after"],
         "metadata_pdf_axis_labels_found": f["pdf_axis_labels_found"],
         "metadata_realised_label_dependence": f["realised_label_dependence"],
         "eval_files_exist": float(f["exists"]), "eval_caption_fields_present": float(f["caption_fields_present"]),
         "eval_mds_stress": float(f["mds_stress"]) if f["mds_stress"] is not None else -1.0} for f in figs]})
    ex = [{"input": f"neighbour {v['name']} (arXiv {v['arxiv']})", "output": str(v.get("quote")),
           "metadata_version_found": v.get("version_found"), "metadata_venue_found": v.get("venue_found"),
           "metadata_venue_status": v.get("venue_status"), "metadata_arxiv_comment": v.get("arxiv_comment"),
           "predict_quote_status": v["quote_status"], "eval_quote_verified": float(v["quote_status"] in
                                                                                  ("VERIFIED", "VERIFIED-ABSTRACT"))}
          for v in pos["neighbours"].values()]
    for t, vs in pos["verdicts"].items():
        for v in vs:
            ex.append({"input": f"saturation candidate [{t}]: {v['candidate']}", "output": v["verdict"],
                       "metadata_why": v["why"], "predict_verdict": v["verdict"],
                       "eval_occupies": float(v["verdict"] == "occupies")})
    ds.append({"dataset": "positioning_rows", "examples": ex})
    sections = {
        "0a": {"commit0_transfer": A["commit0"]["transfer"], "commit0_pass_ratio": A["commit0"]["pass_ratio"],
               "mr_posthoc_correct_Y": A["mr_posthoc"], "occurrence_ledger_rows": len(ledger),
               "occurrence_ledger_stageA": sum(r["class"] == "stageA_share" for r in ledger)},
        "0b": {"rule_label": B["rule_label"], "posthoc_condition_span": B["posthoc_S2"], "S4": B["S4"],
               "flips": B["flips_S0_vs_S4"], "concordance": B["concordance"], "depth_redundancy": B["depth_redundancy"]},
        "0c": {k: GE[k] for k in ("das", "das_gen", "lasso", "ridge_std", "ridge_ctrl", "ridge_delta", "unstd_sae",
                                  "raw_ridge", "twin_pass", "top5", "main4_pass", "other_pass")},
        "0d": {"table": "Table 279 (NEW)", "paragraphs": ["6.9", "6.10 dead ends", "6.10 item 2", "6.11", "closing",
                                                         "What remains open"]},
        "0e": {"figures": [f["fig_id"] for f in figs], "verified": sum(f["exists"] for f in figs)},
        "0f": {"centroid_pc1_range": F["centroid_pc1_range"], "twin_pc1": F["twin_pc1"], "push_pc1": F["push_pc1"],
               "pass": F["pass"]},
        "0g": {"screen": G8["screen"], "excess_met_pass_failed": G8["excess_met_pass_failed"],
               "verdict_T2": G8["verdict_T2"]},
        "0h": {k: H[k] for k in ("n_units", "b", "c", "p", "cluster_boot_ci", "clusters", "n_samples", "one_unit_first",
                                 "random_unit", "sign_test_per_sample", "durkalski", "per_task", "task_level_sign",
                                 "cluster_floor_p")},
        "0i": {"U6": U["U6"], "D12": U["D12"], "novelty": {k: nov[k] for k in ("n_programs", "gate",
                                                                               "kappa_merged_classes", "kappa_exact_classes",
                                                                               "n_novel_final", "spend", "corpus_note")}},
        "0j": {"insertion_found_by": J["found_by"], "insertion": J["insertion"], "other_lines_with_claim":
               J["lint_other_lines"]},
        "0k": {"neighbours": pos["neighbours"], "verdict_counts": pos["verdict_counts"], "wording": pos["wording"],
               "consistency_check": cons},
        "0l": L,
    }
    meta = {"evaluation_name": "iteration-7 Step 0 record repair", "read_date": READ_DATE,
            "dependencies": ["art_lpQalcAXMGr1", "art_rMlbrjVB1c__", "art_zNyBP6zieI5u", "art_dbUtqBjT0tPf"],
            "read_by_path": ["art_aRTQM6CQ0Dre", "art_OUuQUYQn5voE", "iter_7 current_report.md"],
            "sections": sections, "discrepancies": discrepancies, "apply_test": {k: apply_res[k] for k in
                                                                                ("n", "n_pass", "pass_rate", "overlaps",
                                                                                 "passed")},
            "lint": {"uncorrected": lint_before, "corrected": lint_after}, "audit": audit, "predict_crosscheck": XC,
            "headline_check": HC,
            "departures": ["no new model compute (Gemma random-init, shuffled-target and forced-DFS DAS controls and a "
                           "logit-lens control are named, not run)",
                           "one-unit-per-sample NLA test assumes independent samples; 5 task clusters cap any cluster-level "
                           "test at p >= 0.0625",
                           "nearest-known comparison against bench references, the run's correct catalogue-labelled "
                           "programs and a 406-solution subset of the 18,237-solution corpus (34 shortest-path)",
                           "3 programs: no rate or rule-of-three bound is quoted",
                           "mini saturation search, not the frozen-protocol search",
                           "Firth profile and cluster-bootstrap intervals are read from site_grid.json, not refitted",
                           "figure captions from code and PDF text, not regenerated figures"]}
    out = {"metadata": meta, "metrics_agg": metrics, "datasets": ds}
    write_json(ws / "eval_out.json", out)
    write_json(ws / "full_eval_out.json", out)
    mini = copy.deepcopy(out)
    for d in mini["datasets"]:
        d["examples"] = d["examples"][:3]
    write_json(ws / "mini_eval_out.json", mini)
    prev = _trunc(copy.deepcopy(mini))
    prev["metrics_agg"] = metrics
    write_json(ws / "preview_eval_out.json", prev)
    return out
