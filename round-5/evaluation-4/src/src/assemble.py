"""Assemble eval_out.json (exp_eval_sol_out schema) from the stage outputs of eval.py, the rival scripts, the quote
check and the independent audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

from io_util import DEPS, NAMES, TASKS


def _num(x: Any) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def build(ws: Path) -> None:
    corr = json.loads((ws / "corrections.json").read_text())
    m = json.loads((ws / "results" / "corrections_metrics.json").read_text())
    riv = json.loads((ws / "rivals.json").read_text())
    sc = json.loads((ws / "results" / "rival_scores.json").read_text())
    qp = ws / "quotes" / "quotes_verified.json"
    quotes = json.loads(qp.read_text()) if qp.exists() else []
    ap = ws / "audit" / "rederive.json"
    audit = json.loads(ap.read_text()) if ap.exists() else {}
    r5p = ws / "rivals" / "r5_human_raw.json"
    cache = ws / "rivals" / "judge_cache.jsonl"
    judge_cost = sum(json.loads(ln).get("cost", 0.0) for ln in cache.read_text().splitlines() if ln.strip()) \
        if cache.exists() else 0.0
    # ---------------------------------------------------------------- provenance
    allv = []
    for sec in ("0a", "0b", "0c", "0d", "0e"):
        allv += [dict(v, section=sec) for v in m.get(sec, {}).get("values", [])]
    allv += [dict(v, section="base") for v in m.get("base_values", [])]
    for e in corr:
        for v in e["values"]:
            if v["tag"] == "CARRIED":
                allv.append(dict(v, section=e["item"]))
    for q in quotes:
        allv.append({"name": f"Table 92c row {q['row']} quote", "tag": q["tag"], "status": q["match_status"],
                     "section": "0f"})
    prov_tags = Counter(v["tag"] for v in allv)
    prov_status = Counter(v["status"] if v["status"] in ("MATCH", "CORRECTED", "NEW", "CARRIED", "NOT_COMPUTABLE")
                          else ("RE-VERIFIED" if v["status"] == "RE-VERIFIED" else "OTHER") for v in allv)
    discrepancies = [v for v in allv if v.get("status") == "CORRECTED"]
    not_comp = [{"rival": rv, "task": t, "reason": (riv["details"][rv].get(t) or {}).get("status")}
                for rv in riv["values"] for t, x in riv["values"][rv].items() if x is None]
    not_comp += m.get("not_computable_sections", [])
    # ---------------------------------------------------------------- headline metrics
    va = {v["variant"]: v for v in m["0a"]["variants"]}
    prim = va["primary: catalogue-only avoidance A_t"]
    drop = va["sensitivity: default-share drop"]
    no12 = va["without T1 and T2 (A_t)"]
    nd = va["descriptive: without NO-DEFAULT tasks (A_t)"]
    tab = {r["forecast"]: r for r in m["0c"]["table"]}
    em = m["0b"]["energy_matched"]
    fl = m["0b"]["flips_S3_vs_S0"]
    agg: dict[str, float | None] = {
        "BA_primary": prim["BA"], "BA_primary_ci_lo": prim["BA_ci95"][0], "BA_primary_ci_hi": prim["BA_ci95"][1],
        "fisher_p_primary": prim["fisher_p_two_sided"], "spearman_primary": prim["spearman_rho"],
        "BA_default_drop": drop["BA"], "fisher_p_default_drop": drop["fisher_p_two_sided"],
        "spearman_default_drop": drop["spearman_rho"], "BA_without_T1_T2": no12["BA"],
        "spearman_without_T1_T2": no12["spearman_rho"], "spearman_p_one_sided_without_T1_T2": no12["spearman_p_one_sided"],
        "BA_without_no_default_tasks": nd["BA"], "n_no_default_tasks_gemma":
            sum(1 for v in m["0a"]["per_task"].values() if v["iter5_default_rule"] == "NO DEFAULT"),
        "placebo_E_permuted_BA_mean": m["0a"]["placebo_E_permuted"]["BA_mean"],
        "S1E_excess_find_duplicate": em["S1E|T06"]["excess"], "S1E_excess_connected_components": em["S1E|T10"]["excess"],
        "S3_vs_S0_flips_find_duplicate_S3_only": fl["T06|2|attempts"]["S3_only"],
        "mcnemar_p_find_duplicate_alpha2": fl["T06|2|attempts"]["mcnemar_p_exact"],
        "push_logscore_on_3_defined_events": tab["PUSH"]["mean_bench_push_defined"],
        "associate_logscore_on_3_defined_events": tab["ASSOCIATE"]["mean_bench_push_defined"],
        "proximity_logscore_on_3_defined_events": tab["PROXIMITY"]["mean_bench_push_defined"],
        "push_logscore_5_events_uniform_fill": tab["PUSH"]["mean_bench_all_gated_uniform_fill"],
        "associate_logscore_5_events": tab["ASSOCIATE"]["mean_bench_all_gated_uniform_fill"],
        "push_screen_logscore_on_4_defined_events": tab["PUSH_SCREEN"]["mean_bench_push_screen_defined"],
        "n_corrections": len(corr), "n_values_matched": prov_status.get("MATCH", 0),
        "n_values_corrected": prov_status.get("CORRECTED", 0), "n_values_new": prov_status.get("NEW", 0),
        "n_values_carried": prov_status.get("CARRIED", 0),
        "n_quotes_reverified": sum(1 for q in quotes if q["tag"] == "RE-VERIFIED"),
        "audit_n_checks": audit.get("n_checks"), "audit_n_fail": audit.get("n_fail"),
        "openrouter_judge_cost_usd": judge_cost,
        "dose_check_rho_ban_unit_over_residual_vs_E_pool":
            m["0d"]["dose_confound_check_ban_unit_over_residual_vs_E_pool"]["rho"],
        "dose_check_auc_ban_unit_over_residual_movable":
            m["0d"]["dose_confound_check_ban_unit_over_residual_vs_E_pool"]["auc_movable"]["auc"],
        "n_movable_tasks_E_pool": sum(sc["movable_E_pool_gt_0"].values()),
        "n_tasks_E_pool_zero": sc["ties"]["E_pool"]["n_at_zero"],
    }
    for rv, d in sc["scores"].items():
        e = d["E_pool"]
        agg[f"rho_{rv}_E_pool"] = e["rho"]
        agg[f"rho_oriented_{rv}_E_pool"] = e["rho_oriented"]
        agg[f"p_perm_{rv}_E_pool"] = e["p_perm_two_sided"]
        agg[f"auc_oriented_{rv}_movable"] = e.get("auc_oriented_movable")
        agg[f"n_tasks_{rv}"] = e["n"]
    agg = {k: float(v) for k, v in agg.items() if _num(v) is not None}
    # ---------------------------------------------------------------- datasets
    ds_corr = []
    for i, e in enumerate(corr):
        vs = e["values"]
        ds_corr.append({
            "input": f"[{e['item']}] {e['report_location']} :: OLD: {e['old_text']}",
            "output": e["new_text"],
            "metadata_item": e["item"], "metadata_marker": e["marker"], "metadata_values": vs,
            "metadata_note": e.get("note"),
            "predict_iteration4_record": e["old_text"], "predict_iteration5_correction": e["new_text"],
            "eval_n_values": float(len(vs)), "eval_n_match": float(sum(1 for v in vs if v["status"] == "MATCH")),
            "eval_n_corrected": float(sum(1 for v in vs if v["status"] == "CORRECTED")),
            "eval_n_carried": float(sum(1 for v in vs if v["status"] == "CARRIED"))})
    ds_riv = []
    T = sc["targets"]
    for t in TASKS:
        ex = {"input": f"Task {t} ({NAMES[t]}): ban-free rival predictors of plan-push movability (frozen "
                       f"rivals.json sha256 {sc['freeze_verification']['rivals_sha256'][:16]}...)",
              "output": json.dumps({k: T[k][t] for k in T} | {"movable_E_pool_gt_0": sc["movable_E_pool_gt_0"][t]}),
              "metadata_task": t, "metadata_default_exp22_twin": riv["default_exp22_twin"][t],
              "metadata_rival_details": {rv: riv["details"][rv].get(t) for rv in riv["values"]}}
        for rv in riv["values"]:
            v = riv["values"][rv].get(t)
            ex[f"predict_{rv}"] = "NOT_COMPUTABLE" if v is None else f"{v:.6g}"
        for k in T:
            ex[f"eval_{k}"] = float(T[k][t])
        ds_riv.append(ex)
    rows = []
    import csv
    with (ws / "tables" / "direction_distributions.csv").open() as fh:
        for r_ in csv.DictReader(fh):
            rows.append(r_)
    ds_dir = []
    for r_ in rows:
        ex = {"input": f"exp22 direction {r_['direction']} at alpha {r_['alpha']} on {r_['task']} ({NAMES[r_['task']]})",
              "output": "escape confirmed" if r_["escape_confirmed"] == "True" else "no confirmed escape",
              "metadata_task": r_["task"], "metadata_alpha": float(r_["alpha"]), "metadata_direction": int(r_["direction"]),
              "metadata_hill_depth": int(r_["hill_depth"]) if r_["hill_depth"] not in ("", "None") else None,
              "metadata_depth_flag": r_["depth_flag"] or None,
              "predict_escape_confirmed": "yes" if r_["escape_confirmed"] == "True" else "no",
              "eval_N": float(r_["N"]), "eval_pass": float(r_["pass"]),
              "eval_correct_off_default_share": float(r_["correct_off_default_share"]),
              "eval_escape_confirmed": 1.0 if r_["escape_confirmed"] == "True" else 0.0}
        if r_["hill1_correct"] not in ("", "None"):
            ex["eval_hill1_correct"] = float(r_["hill1_correct"])
        ds_dir.append(ex)
    ds_q = [{"input": f"Table 92c row {q['row']} ({q['lane']}): {q['cite']}" + (f" '{q['title']}'" if q["title"] else ""),
             "output": " | ".join(x["quote"] for x in q["quotes"]),
             "metadata_url": q["url"], "metadata_version": q["version"], "metadata_access_date": q["access_date"],
             "metadata_match_status": q["match_status"], "metadata_tag": q["tag"], "metadata_relation": q["relation"],
             "metadata_peer_reviewed": q["peer_reviewed"], "metadata_adds": q["adds"],
             "predict_relation": q["relation"],
             "eval_reverified": 1.0 if q["tag"] == "RE-VERIFIED" else 0.0} for q in quotes]
    cov = Counter(v.get("source", "").split(":")[0] for v in allv if v.get("source"))
    ds_dep = [{"input": f"Dependency {art} ({key})", "output": f"{cov.get(art, 0)} provenance-tagged values sourced",
               "metadata_workspace_key": key, "predict_used": "yes" if cov.get(art, 0) else "no",
               "eval_n_values_sourced": float(cov.get(art, 0))}
              for key, (art, _) in DEPS.items()]
    datasets = [{"dataset": "corrections", "examples": ds_corr}, {"dataset": "rivals", "examples": ds_riv},
                {"dataset": "direction_distributions", "examples": ds_dir}, {"dataset": "table92c", "examples": ds_q},
                {"dataset": "dependency_coverage", "examples": ds_dep}]
    # ---------------------------------------------------------------- metadata
    commits = [json.loads(ln) for ln in (ws / "commitments.log").read_text().splitlines() if ln.strip()]
    meta = {
        "evaluation_name": "Fix the record, freeze rival predictors (iteration 5, Step 0, CPU only)",
        "description": "Record corrections (0a)-(0h) re-derived from the declared dependencies with provenance tags and "
                       "tolerance checks; eight ban-free rival task predictors frozen by sha256 before scoring; "
                       "descriptive scoring against the iteration-4 escape fractions; independent stdlib audit.",
        "conventions": {"tags": ["RE-DERIVED", "READ", "CARRIED", "RE-VERIFIED", "NOT_COMPUTABLE"],
                        "status": ["MATCH", "CORRECTED", "NEW (no record value)", "CARRIED", "NOT_COMPUTABLE"],
                        "tolerances": {"counts": 0, "rates": 0.005, "hill_logscore_correlation": 0.01, "intervals": 0.02},
                        "seed": 20261021, "n_boot": 10000, "n_perm": 200000,
                        "diversity": "correct-only Hill-1, exact expectation over subsamples without replacement at "
                                     "depth 25 (or own depth, flagged)"},
        "sections": {
            "a_heldout_verdict_per_measure": {k: m["0a"][k] for k in ("variants", "placebo_E_permuted", "separating_tasks",
                                                                     "t2_bf_spfa_counts", "gemma_disagreeing_events",
                                                                     "gemma_diff_disagreeing")} |
                                             {"per_task": m["0a"]["per_task"]},
            "b_site": {k: v for k, v in m["0b"].items() if k != "values"},
            "c_landings": {k: v for k, v in m["0c"].items() if k != "values"},
            "d_missing_results": {k: v for k, v in m["0d"].items() if k != "values"},
            "e_distributions": {k: v for k, v in m["0e"].items() if k != "values"},
            "f_table92c": quotes,
            "g_exposure_class": m.get("0g"),
            "h_table76": m.get("0h"),
            "i_rivals": {"definitions": riv["definitions"], "values": riv["values"], "flags": riv["flags"],
                         "n_tasks": riv["n_tasks"], "freeze": sc["freeze_verification"], "commitments": commits,
                         "scores": sc["scores"], "holm_E_pool_descriptive": sc["holm_E_pool"],
                         "sensitivities_E_pool": sc["sensitivities_E_pool"], "ties": sc["ties"],
                         "targets": sc["targets"], "intercorrelation": sc["intercorrelation"],
                         "label": sc["label"], "base_compositions_iteration1": m.get("base"),
                         "r5_pooled_audit": riv["details"]["R5"].get("_pooled_audit")},
        },
        "provenance_counts": {"by_tag": dict(prov_tags), "by_status": dict(prov_status)},
        "discrepancies": discrepancies + [
            {"name": "E = 0 ties", "value": sc["ties"]["E_pool"]["n_at_zero"], "record_value": 9,
             "note": "10 of 15 tasks have E_pool = 0 on the fresh draws (T06 plus the nine 8-direction tasks); the plan "
                     "expected 9"},
            {"name": "rival freeze chain", "note": "commitments.log: freeze 11:59:44 UTC -> targets opened 11:59:50 -> "
                                                   "re-freeze 12:06:07 (a re-freeze guard added to compute_rivals.py "
                                                   "changed its sha256) -> re-freeze 12:26:58 (path-portability edits "
                                                   "changed the sha256 of the R5/R6 scripts and of the timing file's "
                                                   "path field); both re-freezes carry "
                                                   "values_identical_to_previous_freeze = true"}],
        "not_computable": not_comp,
        "costs": {"openrouter_usd_judge_r5": judge_cost, "cpu_only": True, "gpu_used": False},
        "audit": {k: v for k, v in audit.items() if k != "checks"},
        "audit_scope": {
            "independently_re_derived_by_audit/rederive.py (stdlib, raw rows)": [
                "(0a) confusion tables, balanced accuracy, Fisher p and Spearman for the primary, default-drop and "
                "without-T1/T2 variants; placebo BA under permuted E",
                "(0b) S1/S2/S5 correct off-default counts; S3:S0 flips and exact McNemar p on find duplicate; S1E "
                "excesses on find duplicate and connected components; S0/S1 swap placebo",
                "(0c) PUSH and ASSOCIATE mean log scores on the 3 push-defined events and on all 5 (uniform fill); "
                "landing-shuffle placebo",
                "(0d) PNPLAIN_a1 and PN_a1 off-default shares",
                "split-half values (two stored sources agree)",
                "all rival values R1-R8 and K, the exp22 twin defaults, every rival Spearman with E_pool; "
                "permuted-E rejection placebo"],
            "not_independently_re_derived": [
                "bootstrap intervals, permutation p-values, exact AUCs, partial and Kendall correlations of the rival "
                "scores (computed once, in rivals/score_rivals.py)",
                "READ values (Mantel-Haenszel OR and indicator, hull winners and P15, GPU hours, triangle check)",
                "CARRIED values (Llama block, Table 127 route landings, iteration-3 direction counts, 0.33 vs 0.37)",
                "(0e) direction distributions and quantiles, signed-progress breakdown, Table 147 depths; iteration-1 "
                "base compositions; the post-freeze dose-confound check"]},
        "honesty_notes": [
            "The rival freeze happens after the iteration-4 targets were seen by the run: it protects the Step-2 "
            "confirmation, not this screen; every rival score here is descriptive.",
            "CARRIED values come from the iteration-4 record because their source artifacts are not declared "
            "dependencies; they were not re-derived here.",
            "R5 is gate-lite (AST-primary labels + blind judge on unknowns; no runtime labeller on human code).",
        ],
    }
    # one input manifest for the whole artifact (plan 0.3): sha256 of every dependency file read by any stage
    manifest: dict[str, Any] = {}
    for f, stage in (("input_hashes_corrections.json", "eval.py"), ("input_hashes_rivals.json", "compute_rivals.py")):
        fp = ws / "results" / f
        if fp.exists():
            for k, v in json.loads(fp.read_text()).items():
                manifest.setdefault(k, dict(v, read_by=[]))["read_by"].append(stage)
    for k, v in sc.get("inputs_sha256", {}).items():
        manifest.setdefault(k, {"sha256": v, "read_by": []})["read_by"].append("score_rivals.py")
    (ws / "results" / "input_hashes.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    meta["n_input_files_hashed"] = len(manifest)
    out = {"metadata": meta, "metrics_agg": agg, "datasets": datasets}
    (ws / "eval_out.json").write_text(json.dumps(out, indent=1, default=str))
    logger.info(f"eval_out.json written: {len(agg)} metrics, datasets " +
                ", ".join(f"{d['dataset']}={len(d['examples'])}" for d in datasets))
