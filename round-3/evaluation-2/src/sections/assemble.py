"""Assemble full/mini/preview eval_out.json (exp_eval_sol_out): numeric metrics_agg, seven datasets, and metadata
holding each section's summary. predict_* values are strings, eval_* values are numbers (missing values omitted)."""

from __future__ import annotations

import copy
import json
import math
from typing import Any

from loguru import logger

from common.paths import RESULTS, WS, read_json, write_json


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _s(x: Any) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float) and not math.isfinite(x):
        return "NA"
    if isinstance(x, (dict, list, tuple)):
        return json.dumps(x, default=str)
    return str(x)


def _ex(input_: str, output: str, preds: dict[str, Any], evals: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    e = {"input": input_, "output": output}
    for k, v in preds.items():
        e[f"predict_{k}"] = _s(v)
    for k, v in evals.items():
        fv = _f(v) if not isinstance(v, bool) else float(v)
        if fv is not None:
            e[f"eval_{k}"] = fv
    for k, v in meta.items():
        e[f"metadata_{k}"] = v if isinstance(v, (str, int, float, bool)) or v is None else json.loads(json.dumps(v, default=str))
    return e


def run() -> dict[str, Any]:
    c1 = read_json(RESULTS / "c1_diagnostics.json")
    man = read_json(RESULTS / "manifold.json")
    nov = read_json(RESULTS / "novelty_audit.json")
    lla = read_json(RESULTS / "llama_correct_only.json")
    knob = read_json(RESULTS / "knob_table.json")
    pos = read_json(RESULTS / "positioning.json")
    cor = read_json(WS / "corrections.json")
    rd = read_json(WS / "audit" / "rederive_report.json") if (WS / "audit" / "rederive_report.json").exists() else {}
    met = c1["event_table"]["metrics"]

    def hit(key: str) -> float | None:
        b = met.get(key)
        return b["rate"] if b else None

    ma = c1["m_arithmetic"]
    vr = c1["variance_ratio_two_stage"]
    g16 = man["bfs_bibfs_verdict_g16"]
    top = next(a for a in nov["multiban_avoidance"] if a["condition"] == "multi:TOP")
    t1b = next(e for e in lla["events"] if e["task"] == "t1" and e["event"] == "baseline")
    best = knob["ranking"][0] if knob["ranking"] else {}
    sep_g16 = next(r["bfs_bibfs"]["separability"] for r in man["tasks"]["t1"]["grid"]
                   if r["layer"] == 24 and r["position"] == "g16" and r["k"] == 10)
    metrics = {
        "c1_events_n": len(c1["event_table"]["table"]),
        "c1_events_qwen_n": sum(1 for r in c1["event_table"]["table"] if r["model"].startswith("Qwen")),
        "c1_hit_argmax_full": hit("Qwen|Gbar_neutral|all_events"),
        "c1_hit_argmax_resid": hit("Qwen|s_neutral|all_events"),
        "c1_hit_argmax_mass": hit("Qwen|mass|all_events"),
        "c1_hit_argmax_full_modal_bans": hit("Qwen|Gbar_neutral|modal_bans"),
        "c1_hit_argmax_resid_modal_bans": hit("Qwen|s_neutral|modal_bans"),
        "c1_hit_argmax_mass_modal_bans": hit("Qwen|mass|modal_bans"),
        "c1_hit_argmax_full_llama": hit("meta-llama|Gbar_neutral|all_events"),
        "c1_hit_argmax_resid_llama": hit("meta-llama|s_neutral|all_events"),
        "c1_hit_argmax_mass_llama": hit("meta-llama|mass|all_events"),
        "c1_mean_rank_landing_resid_qwen": (met.get("Qwen|s_neutral|all_events") or {}).get("mean_rank_landing"),
        "c1_mass_rows_kept": c1["mass_c1"]["n_rows_kept"],
        "c1_mass_rows_total": c1["mass_c1"]["n_rows_total"],
        "qwen_boot_rep_ratio_median": vr["row_ratio_median"],
        "qwen_boot_rep_ratio_min": vr["row_ratio_range"][0],
        "qwen_boot_rep_ratio_max": vr["row_ratio_range"][1],
        "qwen_boot_rep_ratio_one_stage_median": c1["variance_ratio_one_stage"]["row_ratio_median"],
        "llama_boot_rep_ratio_min": c1["llama_variance_ratio_exp10"]["range"][0],
        "llama_boot_rep_ratio_max": c1["llama_variance_ratio_exp10"]["range"][1],
        "qwen_pooled_share_basic_lo": c1["intervals"]["qwen|pooled|SHARE"]["basic_ci95"][0],
        "qwen_pooled_share_basic_hi": c1["intervals"]["qwen|pooled|SHARE"]["basic_ci95"][1],
        "aim_obs_qwen_mention": c1["aim"]["observed"]["qwen_mention_ref"],
        "aim_null_mean_qwen_split_half": c1["aim"]["null"]["qwen_split_half_estimated"]["mean"],
        "aim_null_mean_shared_cell_equal_var": c1["aim"]["null"]["qwen_shared_cell_equal_var"]["mean"],
        "aim_null_q_qwen": c1["aim"]["observed_quantile"]["qwen_mention_ref|split_half_estimated"],
        "aim_null_q_llama": c1["aim"]["observed_quantile"]["llama_mention_ref|shared_cell_equal_var"],
        "aim_placebo_independent_mention_mean": c1["aim"]["null"]["placebo_independent_mention"]["mean"],
        "ess_weighted_share_t1": c1["ess_weighted"]["reported_SHARE_t1"],
        "m5_plugin_median": ma["M5_plugin_median_qwen"],
        "m5_lognormal_median_log10": math.log10(ma["M5_lognormal_median_qwen"]) if ma["M5_lognormal_median_qwen"] > 0 else None,
        "khat_frac_gt07": ma["khat_frac_gt_0.7"],
        "gpu_hours_per_event_plugin_lower_bound": ma["conversion"]["plugin_median_lower_bound"]["gpu_hours_per_event"],
        "share_events_needed_qwen": c1["bench_events"]["qwen"]["n_mdd_0.10"],
        "share_events_needed_llama": c1["bench_events"]["llama"]["n_mdd_0.10"],
        "bfs_bibfs_g16_sep": sep_g16,
        "bfs_bibfs_g16_n1_p": g16["N1_p_bfs"],
        "bfs_bibfs_g16_n2_p": g16["N2_p"],
        "bfs_bibfs_g16_survives": float(g16["survives"]),
        "h1_power_g16_t1": man["tasks"]["t1"]["persistence"]["L24|g16"]["power"]["planted_loop_power"],
        "h1_power_g16_t2": man["tasks"]["t2"]["persistence"]["L24|g16"]["power"]["planted_loop_power"],
        "h1_power_pre_t1": man["tasks"]["t1"]["persistence"]["L24|pre"]["power"]["planted_loop_power"],
        "h1_power_pre_t2": man["tasks"]["t2"]["persistence"]["L24|pre"]["power"]["planted_loop_power"],
        "h1_radius0_placebo_rate_t1": man["tasks"]["t1"]["persistence"]["L24|g16"]["power"]["radius0_placebo_rate"],
        "manifold_figures_found": man["figures_found"]["fig_manifold"],
        "novelty_correct_other_unique": nov["novelty_answer"]["correct_other_unique"],
        "novelty_confirmed_novel": nov["novelty_answer"]["confirmed_novel_correct"],
        "novelty_rule_of_three_upper": nov["novelty_answer"]["rule_of_three_upper_95_over_correct_other"],
        "novelty_items_judged": nov["n_items"],
        "judge_kappa": nov["kappa_A_B"],
        "judge_kappa_collapsed": nov["kappa_collapsed_known_novel_degenerate"],
        "judge_posctrl_hits": nov["controls"]["pos_hits"],
        "judge_negctrl_hits": nov["controls"]["neg_hits"],
        "judge_posctrl_identity_both": nov["controls_identity_both_judges"],
        "judge_spend_usd": nov["spend_usd_judges"],
        "manual_agreement_setA_collapsed": nov["manual_agreement_setA_collapsed"],
        "top_avoidance_raw": top["avoidance_raw"],
        "top_avoidance_corrected": top["avoidance_corrected"],
        "top_other_share": top["other_share"],
        "llama_t1_hill_cc": t1b["hill_cc"],
        "llama_t1_hill_all": t1b["hill_all"],
        "knob_best_hill_lt20pts": best.get("hill_rar25"),
        "knob_best_hill_lt20pts_ci_hi": (best.get("hill_rar25_ci90") or [None, None])[1],
        "knob_rows_rebuilt": knob["n_rows_primary"],
        "knob_rankable": knob["n_rankable_knobs"],
        "positioning_verified": pos["n_verified"],
        "corrections_items": cor["n_items"],
        "reproduction_targets_n": cor.get("n_targets"),
        "reproduction_targets_matched": cor.get("n_targets_matched"),
        "rederive_checks": rd.get("n_checks"),
        "rederive_passed": rd.get("n_passed"),
        "placebos_failed_as_required": rd.get("n_placebos_ok"),
    }
    metrics = {k: float(v) for k, v in metrics.items() if _f(v) is not None}
    ds = []
    # 1 c1_events
    ex = []
    for r in c1["event_table"]["table"]:
        ex.append(_ex(f"{r['model']} | {r['task']} | ban {r['banned']} ({r['ban_kind']}) | event {r['event']} | "
                      f"survivors {','.join(r['survivors'])}",
                      _s(r["modal_landing"]),
                      {"argmax_full": r.get("argmax_Gbar_neutral"), "argmax_resid": r.get("argmax_s_neutral"),
                       "argmax_mass": r.get("argmax_mass"), "argmax_full_mention": r.get("argmax_Gbar_mention"),
                       "argmax_resid_mention": r.get("argmax_s_mention")},
                      {"rank_full": r.get("rank_landing_Gbar_neutral"), "rank_resid": r.get("rank_landing_s_neutral"),
                       "rank_mass": r.get("rank_landing_mass"),
                       "hit_full": r.get("hit_Gbar_neutral"), "hit_resid": r.get("hit_s_neutral"), "hit_mass": r.get("hit_mass"),
                       "modal_landing_share": r.get("modal_landing_share"), "n_nonbanned": r.get("n_nonbanned"),
                       "n_correct_nonbanned": r.get("n_correct_nonbanned")},
                      {"attempted_counts": r.get("attempted_counts"), "correct_nonbanned_counts": r.get("correct_nonbanned_counts"),
                       "modal_landing_wilson": r.get("modal_landing_wilson"), "median_ess": r.get("median_ess_per_survivor"),
                       "source": r.get("source"), "reference_source": r.get("reference_source")}))
    ds.append({"dataset": "c1_events", "examples": ex})
    # 2 novelty_audit
    tab = read_json(RESULTS / "novelty_audit.json")["table"]
    from sections import s0c_novelty as N  # code text is not stored in results JSON; rebuild from the selection
    from common.rows import iter_rows

    sel = N.build_selection(list(iter_rows(include_exp12_extra=True)))
    code = {it["item_id"]: it["code"] for it in sel["A"] + sel["B_TOP"] + sel["B"]}
    ex = []
    for r in tab:
        ex.append(_ex(f"TASK {r['task']}\n{code.get(r['item_id'], '')}", _s(r["final_class"]),
                      {"judge_a": r["judge_A"], "judge_b": r["judge_B"], "judge_c": r["judge_C"], "labeller": r["label"],
                       "manual": r["manual_class"]},
                      {"max_ast4_jaccard": r["max_ast4_jaccard"], "passed": float(bool(r["passed"])),
                       "n_copies": r["n_copies"], "instruction_driven": float(bool(r["instruction_driven"]))},
                      {"item_id": r["item_id"], "set": r["set"], "models": r["models"], "exps": r["exps"],
                       "conditions": r["conditions"], "closest_known": r["closest_known"], "final_how": r["final_how"],
                       "manual_reason": r["manual_reason"], "provenance": r["provenance"][:10]}))
    ds.append({"dataset": "novelty_audit", "examples": ex})
    # 3 knob_table
    ex = []
    for r in knob["primary"]:
        ex.append(_ex(f"{r['exp']} | {r['model']} | {r['task']} | {r['condition']} | arm {r['arm'] or '-'} | {r['decoding']}",
                      _s(r["cc_counts"]),
                      {"class": r["class"], "reference": r["reference"], "second_algorithm": r["second_algorithm"]},
                      {"hill_rar25": r["hill_rar25"], "hill_rar25_ci90_lo": (r["hill_rar25_ci90"] or [None])[0],
                       "hill_rar25_ci90_hi": (r["hill_rar25_ci90"] or [None, None])[1], "pass_points": r["pass_points"],
                       "pass_rate": r["pass_rate"], "n_cc": r["n_cc"], "second_share": r["second_share"], "N": r["N"]},
                      {"class_reason": r["class_reason"], "source": r["source"], "pass_points_ci90": r["pass_points_ci90"]}))
    ds.append({"dataset": "knob_table", "examples": ex})
    # 4 llama_correct_only
    ex = []
    for e in lla["events"]:
        q = e.get("qwen_counterpart") or {}
        ex.append(_ex(f"Llama-3.1-8B-Instruct | {e['task']} | {e['event']}", _s(e["correct_compliant_counts"]),
                      {"attempted_counts": e["attempted_counts"], "qwen_correct_counts": q.get("correct_compliant_counts")},
                      {"hill_cc": e["hill_cc"], "hill_all": e["hill_all"], "hill_cc_rar10": e["hill_cc_rarefied_d10"],
                       "hill_cc_rar20": e["hill_cc_rarefied_d20"], "hill_cc_mm": e["hill_cc_miller_madow"],
                       "n_correct": e["n_correct_compliant"], "pass_rate": e["pass_rate"], "qwen_hill_cc": q.get("hill_cc"),
                       "qwen_hill_cc_rar10": q.get("hill_cc_rarefied_d10")},
                      {"source": e["source"], "flag": e["hill_cc_rarefied_d10_flag"]}))
    for b in lla["bench"]:
        ex.append(_ex(f"bench pilot | {b['task']}", _s(b["llama"]["correct_compliant_counts"]),
                      {"attempted_counts": b["llama"]["attempted_counts"], "qwen_correct_counts": b["qwen"]["correct_compliant_counts"]},
                      {"hill_cc": b["llama"]["hill_cc"], "hill_all": b["llama"]["hill_all"],
                       "hill_cc_rar10": b["llama"]["hill_cc_rarefied_d10"], "hill_cc_rar20": b["llama"]["hill_cc_rarefied_d20"],
                       "hill_cc_mm": b["llama"]["hill_cc_miller_madow"], "n_correct": b["llama"]["n_correct_compliant"],
                       "qwen_hill_cc": b["qwen"]["hill_cc"], "qwen_hill_cc_rar10": b["qwen"]["hill_cc_rarefied_d10"]},
                      {"source": b["source"]}))
    ds.append({"dataset": "llama_correct_only", "examples": ex})
    # 5 manifold_grid
    ex = []
    for t in ("t1", "t2"):
        for g in man["tasks"][t]["grid"]:
            bb = g.get("bfs_bibfs", {})
            ex.append(_ex(f"{t} | layer {g['layer']} | position {g['position']} | k {g['k']}", _s(g["nearest"]),
                          {"nearest_exp9_sweep": g["nearest_exp9_sweep"]},
                          {"stress1": g["stress1"], "bridges": g["bridges"],
                           "nearest_matches_exp9": float(bool(g["nearest_matches_exp9"])) if g["nearest_matches_exp9"] is not None else None,
                           "bfs_bibfs_separability": bb.get("separability"), "bfs_bibfs_rank": bb.get("rank_among_bfs_neighbours")},
                          {"stress1_source": g["stress1_source"]}))
    ds.append({"dataset": "manifold_grid", "examples": ex})
    # 6 positioning
    ex = [_ex(f"{r['claim_id']}: {r['this_run_claim']}", r["neighbour_finding_quote"] or "unverified",
              {"relation": r["relation"], "neighbour": r["neighbour"]}, {"verified": float(bool(r["verified"])),
                                                                          "quote_words": r["quote_words"]},
              {"url": r["url"], "what_this_run_adds": r["what_this_run_adds"], "date": r["date"]}) for r in pos["rows"]]
    ds.append({"dataset": "positioning", "examples": ex})
    # 7 corrections
    ex = [_ex(f"{c['id']} ({c['report_location']}): {c['old_claim']}", c["new_text"], {"status": c["status"]},
              {"n_numbers": len(c["numbers"])}, {"numbers": c["numbers"]}) for c in cor["items"]]
    ds.append({"dataset": "corrections", "examples": ex})
    meta = {
        "evaluation_name": "Iteration-3 Step 0: record repair and novelty audit (CPU only)",
        "description": ("C1 likelihood diagnostics restricted to estimable mass, manifold re-test at the label-independent "
                        "g16 position with nulls and power, blind two-family LLM-judge audit of every correct out-of-catalogue "
                        "program, Llama correct-only diversity, a knob table under a declared class rule, dated positioning "
                        "and a 12-item corrections log. Sources are cited as '<artifact_id>:<relative path>'."),
        "c1_diagnostics": {k: c1[k] for k in ("mass_branch", "mass_prediction_stated_before", "variance_ratio_two_stage",
                                               "variance_ratio_one_stage", "intervals", "llama_intervals", "aim", "ess_weighted",
                                               "m_arithmetic", "bench_events", "notes")} | {"event_metrics": met,
                                                                                         "reproduction": c1["event_table"]["reproduction"],
                                                                                         "mass_dropped_rows": [{k: r[k] for k in ("task", "B", "n_mass_ge_1pct", "n_ess_ge_5_both", "status")} for r in c1["mass_c1"]["dropped"]]},
        "manifold": {k: man[k] for k in ("figures_found", "top5_banned_counts", "bfs_bibfs_verdict_g16", "sources")} |
                    {t: {k: man["tasks"][t][k] for k in ("n_points", "class_sizes", "rederive_primary_D_max_abs_diff",
                                                          "nulls_layer24_k10", "persistence")} for t in ("t1", "t2")},
        "novelty_audit": {k: v for k, v in nov.items() if k not in ("table", "sources")},
        "llama_correct_only": {k: lla[k] for k in ("reproduction", "cross_model_sentence")},
        "knob_table": {k: knob[k] for k in ("n_rows_primary", "n_rows_primary_without_exp5", "n_rows_audit", "class_counts",
                                            "n_rankable_knobs", "verdict", "reproduction", "depth")},
        "positioning": {k: pos[k] for k in ("n_verified", "n_rows", "date", "method")},
        "corrections": {"n_items": cor["n_items"], "note": cor["note"], "ids": [c["id"] for c in cor["items"]],
                        "reproduction_targets": cor.get("reproduction_targets")},
        "rederive": rd, "deviations": read_json(WS / "deviations.json") if (WS / "deviations.json").exists() else [],
    }
    out = {"metadata": meta, "metrics_agg": metrics, "datasets": ds}
    write_json(WS / "eval_out.json", out, indent=None)       # primary output; full/mini/preview variants follow
    write_json(WS / "full_eval_out.json", out, indent=None)
    mini = copy.deepcopy(out)
    for d in mini["datasets"]:
        d["examples"] = d["examples"][:3]
    write_json(WS / "mini_eval_out.json", mini, indent=1)

    def trunc(o: Any) -> Any:
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        if isinstance(o, list):
            return [trunc(v) for v in o[:20]]
        return o

    prev = trunc(copy.deepcopy(mini))
    prev["metrics_agg"] = mini["metrics_agg"]
    write_json(WS / "preview_eval_out.json", prev, indent=1)
    logger.info(f"assembled: {len(metrics)} metrics, datasets {[(d['dataset'], len(d['examples'])) for d in ds]}")
    return out
