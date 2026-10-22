"""Stage out: corrections.json, eval_out.json (exp_eval_sol_out), metrics, and the publish-safety path scrub."""

from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

from loguru import logger

from src import common as C

WS = C.WS


def _num(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return float(x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _key(s: str) -> str:
    k = re.sub(r"[^A-Za-z0-9_]", "_", s)
    k = re.sub(r"_+", "_", k).strip("_")
    return k if re.match(r"^[A-Za-z_]", k) else "m_" + k


def _ex(inp: str, out: str, **kw) -> dict:
    d = {"input": inp, "output": out}
    for k, v in kw.items():
        if k.startswith("eval_"):
            n = _num(v)
            if n is not None:
                d[_key(k)] = n
        elif k.startswith("predict_"):
            d[_key(k)] = "" if v is None else (v if isinstance(v, str) else json.dumps(C.clean_nan(v)))
        elif k.startswith("metadata_"):
            d[_key(k)] = C.clean_nan(v)
    return d


def merge_corrections(rep: C.Report) -> tuple[list[dict], dict]:
    allc = []
    for s in ("0a", "0b", "0c", "0d", "0e", "0f"):
        p = C.RESULTS / f"corrections_{s}.json"
        if p.exists():
            allc.extend(json.loads(p.read_text()))
    spans = []
    for i, c in enumerate(allc):
        c["id"] = f"C6-{i + 1:03d}"
        st = rep.text.find(c["old_text"])
        spans.append((st, st + len(c["old_text"]), c["id"]))
    spans.sort()
    overlaps = [(a[2], b[2]) for a, b in zip(spans, spans[1:]) if b[0] < a[1]]
    counts = {"MATCH": 0, "CORRECTED": 0, "NEW": 0, "CARRIED": 0}
    for c in allc:
        for v in c["values"]:
            counts[v["status"]] = counts.get(v["status"], 0) + 1
    meta = {"n_corrections": len(allc), "value_status_counts": counts, "overlapping_old_text_spans": overlaps,
            "all_old_text_exact_unique": all(rep.count(c["old_text"]) == 1 for c in allc)}
    return allc, meta


def write_corrections() -> dict:
    rep = C.Report(C.REPORT_PATH)
    corr, cmeta = merge_corrections(rep)
    C.write_json("corrections.json", {"schema": "art_mgek9PfVBNbh corrections schema (id, review_item, location, old_text, "
                                                "new_text, values[name, recorded, recomputed, status, source], marker)",
                                      "report": "current_report.md of iteration 6 (gen_strat)",
                                      "report_sha256": rep.sha256, "meta": cmeta, "corrections": corr})
    logger.info(f"corrections: {cmeta}")
    return cmeta


def build(TNAME: dict, UNAME: dict) -> dict:
    cmeta = write_corrections()
    r = {s: C.read_result(s) for s in ("0a", "0b", "0c", "0d", "0e")}
    f = C.read_result("0f") if (C.RESULTS / "0f.json").exists() else None
    aud = json.loads((WS / "audit" / "rederive_report.json").read_text()) if (WS / "audit" / "rederive_report.json").exists() else {}
    M: dict[str, float] = {}

    def put(k, v):
        n = _num(v)
        if n is not None:
            M[_key(k)] = n
    ds = []
    # ---------------- 0a
    A1 = r["0a"]["A1"]["rows"]
    exs = []
    for row in A1:
        put(f"dose_ratio_meanratio_{row['task']}", row["mean_ratio_knob_exp"])
        put(f"dose_ratio_ratioofmeans_{row['task']}", row["ratio_of_means_table174"])
        exs.append(_ex(f"Dose units for {row['name']} ({row['task']}): ban-free unit over ban unit, Table 174 ratio of mean "
                       f"norms against the knob experiment's mean of per-position ratios.",
                       f"{row['ratio_of_means_table174']}", predict_mean_ratio=f"{row['mean_ratio_knob_exp']}",
                       predict_ratio_of_means_recomputed=f"{row['ratio_of_means_recomputed']}",
                       eval_gap=row["gap_mean_ratio_minus_ratio_of_means"], eval_shortfall=row["shortfall_ratio_of_means"],
                       metadata_status=row["ratio_of_means_status"], metadata_source=row["source_ratio_of_means"] + "; " + row["source_mean_ratio"]))
    ds.append({"dataset": "dose_reconciliation", "examples": exs})
    pt = r["0a"]["A2"]["per_task"]
    exs = []
    for t, v in pt.items():
        bf, fp = v["bf16"], v["fp8"]
        for a in ("1.0", "2.0"):
            put(f"pn_offdef_bf16_a{a[0]}_{t}", bf[a]["share_cor"])
            put(f"pn_offdef_fp8_a{a[0]}_{t}", fp[a]["share_cor"])
            put(f"pn_offdef_att_bf16_a{a[0]}_{t}", bf[a]["share_att"])
            put(f"pn_offdef_att_fp8_a{a[0]}_{t}", fp[a]["share_att"])
            put(f"fisher_p_{t}_a{a[0]}", v["cor"]["fisher_two_sided_matched_alpha"][a])
        put(f"bracket_p_{t}", v["cor"]["bracket"]["p_one_sided_less"])
        put(f"bracket_p_att_{t}", v["att"]["bracket"]["p_one_sided_less"])
        put(f"bracket_pass_{t}", v["cor"]["criterion2_bracket"] and v["att"]["criterion2_bracket"])
        put(f"fold_ratio_{t}", v["cor"]["fold_ratio_a2"]["rr"])
        put(f"tag_not_replicated_{t}", v["tag"].startswith("did NOT"))
        for defn in ("cor", "att"):
            d = v[defn]
            kk, nk = ("cor_off", "n_correct") if defn == "cor" else ("att_off", "n")
            exs.append(_ex(f"Plan noise on {TNAME[t]} ({t}), {'correct-only' if defn == 'cor' else 'all-samples'} off-default "
                           f"share: bf16 alpha 1 {bf['1.0'][kk]}/{bf['1.0'][nk]}, alpha 2 {bf['2.0'][kk]}/{bf['2.0'][nk]}; "
                           f"FP8 W8A8 alpha 1 {fp['1.0'][kk]}/{fp['1.0'][nk]}, alpha 2 {fp['2.0'][kk]}/{fp['2.0'][nk]}.",
                           v["tag"], predict_rule_pass=str(d["rule_pass"]), predict_bracket_inequality=str(d["criterion2_bracket"]),
                           eval_fisher_p_a1=d["fisher_two_sided_matched_alpha"]["1.0"],
                           eval_fisher_p_a2=d["fisher_two_sided_matched_alpha"]["2.0"], eval_holm_min=d["fisher_holm_min"],
                           eval_bracket_p=d["bracket"]["p_one_sided_less"], eval_fold_ratio_a2=d["fold_ratio_a2"]["rr"],
                           eval_dose_matched_p_rom=d["dose_matched"]["ratio_of_means|bf16_a2"]["p_exact_binom_le"],
                           eval_dose_matched_p_mr=d["dose_matched"]["mean_ratio|bf16_a2"]["p_exact_binom_le"],
                           metadata_definition=defn, metadata_source="art_jR6Pyy3W9xum:results/cells.json; art_mWn-MQEnNelg:results/alpha_sweep.json"))
    ds.append({"dataset": "engine_pn_contrast", "examples": exs})
    el = json.loads((WS / "engine_labels.json").read_text())["rows"]
    ds.append({"dataset": "engine_labels", "examples": [
        _ex(f"{x['id']}: {x['claim']} (report: {x['report_location']})", x["status"], predict_engine_class=x["engine_class"],
            predict_bf16_counterpart=x["bf16_counterpart"], metadata_source=x["source"], metadata_device=x["device"],
            metadata_note=x["note"]) for x in el]})
    put("n_engine_rows", len(el))
    put("n_fp8_not_replicated", sum(x["status"].startswith("did NOT") for x in el))
    put("n_bf16_conditional", sum(x["status"] == "bf16-conditional" for x in el))
    put("n_fp8_only_untested", sum(x["status"].startswith("FP8 only") for x in el))
    for k, v in r["0a"]["A5"]["stats"].items():
        put(f"fig_rho_{k}", v["rho"])
        put(f"fig_perm_p_{k}", v["perm_p_one_sided"])
    # ---------------- 0b
    b = r["0b"]
    for s, v in b["tally"].items():
        sk = {"FP8 screen": "fp8screen", "bf16 existing remeasure": "bf16existing", "panel A": "panelA", "panel B": "panelB",
              "Gemma": "gemma", "all": "total"}[s]
        put(f"landing_hits_{sk}", v["hits"])
        put(f"landing_events_{sk}", v["events"])
        put(f"pb_p_{sk}", v["pb_p"])
    put("landing_hits_total", b["tally"]["all"]["hits"])
    put("pb_p_total", b["tally"]["all"]["pb_p"])
    c = b["confound"]
    put("unconf_hits_qwen", c["qwen"]["hits"]); put("unconf_n_qwen", c["qwen"]["n"]); put("unconf_p_qwen", c["qwen"]["pb_p"])
    put("unconf_hits_gemma", c["gemma"]["hits"]); put("unconf_n_gemma", c["gemma"]["n"]); put("unconf_p_gemma", c["gemma"]["pb_p"])
    put("unconf_hits_pooled", c["pooled"]["hits"]); put("unconf_n_pooled", c["pooled"]["n"]); put("unconf_p_pooled", c["pooled"]["pb_p"])
    put("unconf_hits_allsets", c["sensitivity_all_sets"]["hits"]); put("unconf_p_allsets", c["sensitivity_all_sets"]["pb_p"])
    put("item2_moved_to_descriptive", c["pooled"]["pb_p"] >= 0.05)
    tm = b["tmf"]["all"]
    put("tmf_defined_n", tm["tmf_defined_n"]); put("tmf_hits", tm["tmf_hits_defined_only"])
    put("tmf_hits_uniform_fill", tm["tmf_hits_uniform_fill"]); put("base_hits_on_tmf_defined", tm["base_hits_defined_only"])
    put("base_vs_tmf_mcnemar_p", tm["mcnemar_defined"]["p_exact_two_sided"])
    put("base_minus_tmf_hit_diff", tm["paired_hit_diff_base_minus_tmf"])
    put("base_minus_tmf_hit_diff_ci_low", tm["paired_hit_diff_ci95"][0]); put("base_minus_tmf_hit_diff_ci_high", tm["paired_hit_diff_ci95"][1])
    put("base_minus_twin_logscore_defined", tm["logscore_base_minus_twin_defined"]["mean"])
    put("base_minus_twin_logscore_wilcoxon_p", tm["logscore_base_minus_twin_defined"]["wilcoxon_exact_greater_p"])
    ds.append({"dataset": "landing_events", "examples": [
        _ex(f"{e['set']} event {e['event']} ({e['name']}): default {e['default']}; non-default catalogue {e['survivors']}; "
            f"instruct twin correct composition {e['twin_correct']}; base support {e['base_valid_attempts']} valid / "
            f"{e['base_correct']} correct / runner-up {e['base_runner_up_count_correct']}.",
            e["landing"], predict_base_runner_up=e["runner_up"], predict_twin_most_frequent_alternative=",".join(e["tmf"]) or "(undefined)",
            eval_hit=e["hit"], eval_chance=e["chance"], eval_tmf_hit=e["tmf_hit"], eval_unconfounded=e["unconfounded"],
            eval_twin_minority_share_of_landing=e["twin_minority_share_of_landing"],
            eval_logscore_base=e["logscore_base_smoothed"], eval_logscore_twin=e["logscore_twin_nondefault_smoothed"],
            metadata_set=e["set"], metadata_engine_push=e["engine_push"], metadata_source=e["source"]) for e in b["events"]]})
    # ---------------- 0c
    m = r["0c"]
    put("rho_beta_E", m["rho"]); put("rho_perm_p", m["perm"]["p"])
    for k, nm in (("plain", "plain"), ("fieller", "fieller"), ("bonett_wright", "bw")):
        put(f"rho_ci_{nm}_low", m["ci"][k][0]); put(f"rho_ci_{nm}_high", m["ci"][k][1])
    put("rho_ci_boot_low", m["boot"]["percentile"][0]); put("rho_ci_boot_high", m["boot"]["percentile"][1])
    put("rho_ci_bca_low", m["boot"]["bca"][0]); put("rho_ci_bca_high", m["boot"]["bca"][1])
    put("rho_beta_E_n15", m["sens15"]["rho"]); put("rho_perm_p_n15", m["sens15"]["perm"]["p"])
    put("rho_beta_E_correct_only_basis", m["sens_correct_only_basis"]["rho"])
    put("rho_perm_p_correct_only_basis", m["sens_correct_only_basis"]["perm"]["p"])
    for k in ("0.4", "0.6", "0.8"):
        put(f"power_rho{k.replace('.', '')}", m["power"][k]["power"])
        put(f"power_two_sided_rho{k.replace('.', '')}", m["power"][k].get("power_two_sided"))
    put("power_rho06_mc_se", m["power"]["0.6"]["mc_se"])
    put("n_for_power08_at_rho06", m["power"]["n_for_0.8_at_0.6"])
    short = {"R1_opening_margin": "R1", "R4_novelty_excess": "R4", "R6_runtime_merit": "R6", "R7_twin_modal_share": "R7", "K": "K"}
    for k, v in m["rivals"].items():
        s = short[k]
        put(f"rho_{s}", v["rho_with_E"]); put(f"delta_rho_{s}", v["delta_rho_beta_minus_rival"])
        put(f"delta_ci_{s}_low", v["delta_ci95"][0]); put(f"delta_ci_{s}_high", v["delta_ci95"][1])
        put(f"holm_p_{s}", v["holm_p"]); put(f"perm_p_{s}", v["perm_p_one_sided"])
    ds.append({"dataset": "movability_units", "examples": [
        _ex(f"New unit {u['unit']} ({u['name']}, panel {u['panel']}); core set of 13: {u['core13']}.", f"{u['E']}",
            predict_beta=f"{u['beta']}", eval_beta=u["beta"], eval_E=u["E"], eval_R1_opening_margin=u["R1_opening_margin"],
            eval_R4_novelty_excess=u["R4_novelty_excess"], eval_R6_runtime_merit=u["R6_runtime_merit"],
            eval_R7_twin_modal_share=u["R7_twin_modal_share"], eval_K=u["K"], metadata_source=u["source"]) for u in m["units"]]})
    ds.append({"dataset": "rival_scores", "examples": [
        _ex(f"Rival {k} (sign {v['sign']:+d}) against the escape fraction over the 13 new units.", f"{v['rho_with_E']}",
            predict_beats_beta=str(v["delta_ci95"][1] < 0), eval_rho=v["rho_with_E"], eval_delta=v["delta_rho_beta_minus_rival"],
            eval_delta_ci_low=v["delta_ci95"][0], eval_delta_ci_high=v["delta_ci95"][1], eval_holm_p=v["holm_p"],
            metadata_values=v["values"]) for k, v in m["rivals"].items()]})
    # ---------------- 0d
    d = r["0d"]
    exs = []
    for row in d["D1"]:
        lab = row["cell"].replace("LIT_", "").replace(".", "")
        for th in ("0.7", "0.8", "0.9"):
            put(f"n_clusters_{lab}_theta{th.replace('.', '')}", row[f"n_clusters_theta{th}"])
        exs.append(_ex(f"Literal cell {row['cell']}: shortest path, thinking on, top-k 10, N 20.",
                       f"{row['n_clusters_theta0.7']}/{row['n_clusters_theta0.8']}/{row['n_clusters_theta0.9']}",
                       predict_phrasings_per_idea_theta08=row["phrasings_per_idea_theta0.8"],
                       eval_n_clusters_theta07=row["n_clusters_theta0.7"], eval_n_clusters_theta08=row["n_clusters_theta0.8"],
                       eval_n_clusters_theta09=row["n_clusters_theta0.9"], metadata_source=row["source"]))
    ds.append({"dataset": "phrasing_literal_cell", "examples": exs})
    exs = []
    for row in d["D2"]:
        put(f"P15_{row['arm']}_{row['task']}", row["P15"]); put(f"P20_{row['arm']}_{row['task']}", row["P20"])
        exs.append(_ex(f"Prices of {row['arm_name']} on {row['name']} ({row['task']}).", f"{row['H5']}",
                       predict_P15="never" if row["P15"] is None else f"{row['P15']}", predict_P20="never" if row["P20"] is None else f"{row['P20']}",
                       eval_H5=row["H5"], eval_P15=row["P15"], eval_P20=row["P20"],
                       eval_P15_reach_share=row.get("P15_reach_share"), eval_P20_reach_share=row.get("P20_reach_share"),
                       metadata_P15_ci95=row.get("P15_ci95"), metadata_P20_ci95=row.get("P20_ci95"),
                       metadata_source=row["source"]))
    ds.append({"dataset": "prices_p15_p20", "examples": exs})
    exs = []
    for row in d["D3"]:
        exs.append(_ex(f"Panel B unit {row['unit']} ({row['name']}), arm {row['arm']}.",
                       f"{row['pass']} / {row['offdef_share_correct_only']} / {row['hill1_rarefied']}",
                       predict_labels_correct=row["labels_correct"], eval_pass=row["pass"],
                       eval_offdef_share_correct_only=row["offdef_share_correct_only"], eval_hill1_rarefied=row["hill1_rarefied"],
                       eval_n_correct=row["n_correct"], metadata_source=row["source"]))
    ds.append({"dataset": "panelB_knob_rows", "examples": exs})
    put("panelB_push_programs_outside_base", d["D4"]["n_outside"])
    for row in d["D5"]:
        put(f"table126c_hill_{row['row_id']}", row["H1r25"]); put(f"table126c_passcost_{row['row_id']}", row["pass_cost_pts"])
    # ---------------- 0e
    e = r["0e"]
    for k, v in e["E1"]["per_task"].items():
        put(f"pn_dmd_disc_{k}_pn", v["pn_only"]); put(f"pn_dmd_disc_{k}_dmd", v["dmd_only"]); put(f"pn_dmd_p_{k}", v["p_exact"])
    for a, v in e["E1"]["pooled"].items():
        put(f"pn_dmd_pooled_{a}_pn", v["pn_only"]); put(f"pn_dmd_pooled_{a}_dmd", v["dmd_only"]); put(f"pn_dmd_pooled_{a}_p", v["p_exact"])
        put(f"pn_dmd_pooled_{a}_p_without_kth", v["p_without_kth_smallest"])
    put("gemma_margin_uniform", e["E2"]["uniform"]); put("gemma_margin_defined", e["E2"]["defined_only"]); put("gemma_n_defined", e["E2"]["n_defined"])
    # ---------------- 0f
    if f:
        f6 = f["F6"]
        put("readj_novel_k", f["readj_novel_k"]); put("readj_novel_k_second", f["readj_novel_k_second"])
        put("readj_final_novel_count", f["final_novel_count"])
        jp = f6["judge_primary"]
        put("readj_raw_agree", jp["disputed_14"]["raw_agree_4class"]); put("readj_raw_agree_binary", jp["disputed_14"]["raw_agree_binary"])
        put("readj_raw_agree_cp_low", jp["disputed_14"]["raw_agree_4class_cp95"][0]); put("readj_raw_agree_cp_high", jp["disputed_14"]["raw_agree_4class_cp95"][1])
        put("readj_kappa_binary_flag", 0.0 if "0 by construction" in jp["disputed_14"]["kappa_binary_flag"] else (
            -1.0 if "undefined" in jp["disputed_14"]["kappa_binary_flag"] else 1.0))
        put("readj_ac1", jp["disputed_14"]["ac1_4class"]); put("readj_ac1_binary", jp["disputed_14"]["ac1_binary"])
        put("readj_kappa_4class_14", jp["disputed_14"]["kappa_4class"])
        put("readj_kappa_with_controls", jp["all_24"]["kappa_4class"]); put("readj_ac1_with_controls", jp["all_24"]["ac1_4class"])
        put("readj_kappa_with_controls_ci_low", jp["all_24"]["kappa_bootstrap_ci95"][0]); put("readj_kappa_with_controls_ci_high", jp["all_24"]["kappa_bootstrap_ci95"][1])
        put("judge_gate_pass", jp["gate_pass"]); put("judge_controls_correct", jp["controls_correct"])
        js = f6["judge_second"]
        put("judge2_gate_pass", js["gate_pass"]); put("judge2_controls_correct", js["controls_correct"])
        put("readj2_raw_agree", js["disputed_14"]["raw_agree_4class"]); put("readj2_kappa_with_controls", js["all_24"]["kappa_4class"])
        put("judge_fleiss", f6["fleiss_primary_3calls"]); put("judge_primary_unanimous_share", f6["primary_unanimous_share"])
        put("inter_judge_kappa", f6["inter_judge_kappa_all"]); put("inter_judge_raw", f6["inter_judge_raw_all"])
        put("openrouter_spend_usd_last_pass", f["spend_usd"]); put("openrouter_calls_last_pass", f["n_calls"])
        jr_p = WS / "audit" / "judge_runs_summary.json"
        if jr_p.exists():
            jr = json.loads(jr_p.read_text())
            put("openrouter_spend_usd", sum(x["spend_usd_this_pass"] for x in jr.values()))
            put("openrouter_calls", sum(x["paid_calls_this_pass"] for x in jr.values()))
            put("judge_passes", len(jr))
        else:
            put("openrouter_spend_usd", f["spend_usd"])
        exs = []
        for it in f["items"]:
            st = it.get("stress") or {}
            exs.append(_ex(f"[{it['blind_id']}] task {it['task']}; program:\n{it['code']}\nSandboxed outcomes: {it.get('stress_text')}",
                           it["truth"], predict_judge_mistral=it.get("judge_primary", "NOT_JUDGED"),
                           predict_judge_second=it.get("judge_second", "NOT_JUDGED"),
                           predict_judge_mistral_named=it.get("judge_primary_named", ""),
                           eval_primary_correct=it.get("judge_primary") == it["truth"],
                           eval_second_correct=it.get("judge_second") == it["truth"],
                           eval_hidden_pass=st.get("hidden_pass"), eval_all_tests_pass=st.get("all_pass"),
                           eval_nearest_ted=(it.get("nearest") or [{}])[0].get("dist"),
                           metadata_kind=it["kind"], metadata_manual_class=it.get("manual_class"),
                           metadata_final_class=it.get("final_class"), metadata_final_verdict=it.get("final_verdict"),
                           metadata_source=it["source"]))
        ds.append({"dataset": "novelty_readjudication", "examples": exs})
    put("n_corrections", cmeta["n_corrections"])
    for k in ("MATCH", "CORRECTED", "NEW", "CARRIED"):
        put(f"n_{k.lower()}", cmeta["value_status_counts"].get(k, 0))
    put("n_overlapping_corrections", len(cmeta["overlapping_old_text_spans"]))
    if aud:
        put("rederive_checks_passed", aud.get("n_passed")); put("rederive_checks_total", aud.get("n_checks"))
        put("placebos_failed", aud.get("n_placebos_failed")); put("placebos_total", aud.get("n_placebos"))
    out = {"metadata": {
        "evaluation_name": "Iteration-6 Step 0: record repair and a second novelty check",
        "description": "CPU-only recomputation from rows of every number the iteration-6 record repair touches, engine tags, "
                       "landing tallies, movability intervals and power, missing tables, minor fixes and a blind second "
                       "adjudication of 14 programs judged novel in iteration 5.",
        "sections": {"0a": "engine tags and dose-bracketed contrast", "0b": "landings per set, confound subset, TMF rival",
                     "0c": "movability interval, power, rivals under one definition", "0d": "missing tables",
                     "0e": "minor fixes", "0f": "second blind adjudication"},
        "results": {s: _brief(s, r.get(s)) for s in ("0a", "0b", "0c")},
        "readjudication": ({k: f[k] for k in ("readj_novel_k", "readj_novel_k_second", "final_novel_count", "spend_usd",
                                              "flagged_for_final_read", "final_read_unresolved")} if f else None),
        "corrections_meta": cmeta, "audit": {k: aud.get(k) for k in ("n_checks", "n_passed", "n_placebos", "n_placebos_failed")},
        "decision_rules": {"engine": r["0a"]["A2"]["rule"], "confound": c["rule"], "confound_decision": c["decision"]}},
        "metrics_agg": M, "datasets": ds}
    C.write_json("eval_out.json", out)
    logger.info(f"eval_out.json: {len(M)} metrics, {len(ds)} datasets")
    return {"n_metrics": len(M), "n_datasets": len(ds), "corrections": cmeta}


def _brief(s, v):
    if v is None:
        return None
    if s == "0a":
        return {t: x["tag"] for t, x in v["A2"]["per_task"].items()}
    if s == "0b":
        return {"tally": {k: f"{x['hits']}/{x['events']} (p {x['pb_p']:.3g})" for k, x in v["tally"].items()},
                "confound": v["confound"]["decision"]}
    if s == "0c":
        return {"rho": v["rho"], "ci_bw": v["ci"]["bonett_wright"], "power_rho06": v["power"]["0.6"]["power"]}
    return None
