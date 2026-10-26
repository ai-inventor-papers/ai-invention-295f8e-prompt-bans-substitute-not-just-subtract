"""(0h) corrections.json: 12 record items, each with the old wording (quoted from the iteration-2 report or the
hypothesis carried into this iteration), the recomputed numbers with their sources, and a replacement sentence."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from loguru import logger

from common.paths import REPORT_REL, RESULTS, WS, dep, read_json, read_jsonl, src, write_json
from common.rows import iter_rows
from common.stats import wilson

REPORT = f"iteration-2 report ({REPORT_REL})"


def _num(name: str, value: Any, source: str, ci: Any = None) -> dict[str, Any]:
    return {"name": name, "value": value, "ci": ci, "source": source}


def iteration1_five_draws(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The 'five draws' of the modal ban in iteration 1 (exp1, exp2, exp3 pools, exp4, exp5 instruct)."""
    sel = {"t1": [], "t2": []}
    for r in rows:
        if r["model"] != "Qwen/Qwen3-8B":
            continue
        c = r["condition"]
        ok = ((r["exp"] == "exp1" and c in ("ban:bfs", "ban:dijkstra")) or
              (r["exp"] == "exp2" and c in ("ban:bfs", "ban:dijkstra")) or
              (r["exp"] == "exp3" and c == "ban") or
              (r["exp"] == "exp4" and c in ("ban:bfs", "ban:dijkstra")) or
              (r["exp"] == "exp5" and c in ("ban:BFS", "ban:Dijkstra")))
        # keep only the MODAL ban of each task (exp1 also ran an absent-mode 'ban:dijkstra' on T1)
        if ok and r["task"] in sel and r["banned_set"] == [{"t1": "bfs", "t2": "dijkstra"}[r["task"]]]:
            sel[r["task"]].append(r)
    out = {}
    for t, j in (("t1", "dfs"), ("t2", "bf_spfa")):
        rs = sel[t]
        per = {}
        for e in sorted({r["exp"] for r in rs}):
            ee = [r for r in rs if r["exp"] == e]
            comp = [r for r in ee if r["passed"] is True and r["label"] not in r["banned_set"] and r["label"] != "unparseable"]
            cnt = Counter(r["label"] for r in comp)
            per[e] = {"compliant": len(comp), j: cnt.get(j, 0), "mode": cnt.most_common(1)[0][0] if cnt else None}
        k = sum(v[j] for v in per.values())
        n = sum(v["compliant"] for v in per.values())
        out[t] = {"per_draw": per, "pooled": f"{k}/{n}", "share": k / n if n else math.nan,
                  "wilson": wilson(k, n) if n else None,
                  "draws_with_mode": sum(1 for v in per.values() if v["mode"] == j), "n_draws": len(per)}
    return out


def run() -> dict[str, Any]:
    c1 = read_json(RESULTS / "c1_diagnostics.json")
    man = read_json(RESULTS / "manifold.json")
    nov = read_json(RESULTS / "novelty_audit.json")
    lla = read_json(RESULTS / "llama_correct_only.json")
    knob = read_json(RESULTS / "knob_table.json")
    pos = read_json(RESULTS / "positioning.json")
    e8 = read_json(dep("exp8", "results/analysis.json"))
    e8n = read_json(dep("exp8", "results/natural_frlp.json"))
    e10 = read_json(dep("exp10", "results/c1.json"))
    e2m = read_json(dep("exp12", "results/e2_meta.json"))
    e11dev = read_json(dep("exp11", "full_method_out.json")).get("metadata", {}).get("deviations") \
        if dep("exp11", "full_method_out.json").stat().st_size < 60_000_000 else None
    rows = list(iter_rows())
    five = iteration1_five_draws(rows)
    met = c1["event_table"]["metrics"]
    ma = c1["m_arithmetic"]
    vr = c1["variance_ratio_two_stage"]
    aim = c1["aim"]
    g16 = man["bfs_bibfs_verdict_g16"]
    p24 = {t: man["tasks"][t]["persistence"] for t in ("t1", "t2")}
    ans = nov["novelty_answer"]
    av = {a["condition"]: a for a in nov["multiban_avoidance"]}
    top = av["multi:TOP"]
    top_items = [r for r in nov["table"] if r["set"] == "B_TOP"]
    t1b = next(e for e in lla["events"] if e["task"] == "t1" and e["event"] == "baseline")
    best = knob["ranking"][0] if knob["ranking"] else {}

    def h(p):
        return met.get(p, {})

    items = []
    items.append({"id": "R01", "report_location": "Sections 2.4, 2.10, 2.11 (C1 / likelihood claims)",
                  "old_claim": "X-SPECIFIC-UNAIMED under the mention reference (T1); pooled X-specific SHARE 0.55 [0.25, 0.67] "
                               "(neutral), 0.66 [0.49, 0.87] (mention); Llama SHARE 0.80 (quoted from the exp7/exp10 summaries "
                               "carried into the " + REPORT + ")",
                  "new_text": ("C1 is not detectable with the current instrument. The likelihood argmax does not point where the "
                               f"model writes: over Qwen single-ban events the full-gain argmax hits the modal landing "
                               f"{h('Qwen|Gbar_neutral|all_events').get('hits')}/{h('Qwen|Gbar_neutral|all_events').get('n')}, "
                               f"the residual argmax {h('Qwen|s_neutral|all_events').get('hits')}/{h('Qwen|s_neutral|all_events').get('n')} "
                               f"and the implied-mass argmax {h('Qwen|mass|all_events').get('hits')}/{h('Qwen|mass|all_events').get('n')}; "
                               f"no ban row keeps three survivors with >= 1% mass and ESS >= 5 ({c1['mass_c1']['n_rows_kept']} of "
                               f"{c1['mass_c1']['n_rows_total']}), and the bootstrap variance of Gbar is "
                               f"{vr['row_ratio_median']:.1f}x (median; range {vr['row_ratio_range'][0]:.1f}-{vr['row_ratio_range'][1]:.1f}) "
                               "the replicate noise term the frozen correction used, so the X-specific variance is inflated by "
                               "importance-sampling noise."),
                  "numbers": [_num("argmax_full_hits_qwen", h("Qwen|Gbar_neutral|all_events"), "results/c1_diagnostics.json"),
                              _num("argmax_resid_hits_qwen", h("Qwen|s_neutral|all_events"), "results/c1_diagnostics.json"),
                              _num("argmax_mass_hits_qwen", h("Qwen|mass|all_events"), "results/c1_diagnostics.json"),
                              _num("mass_rows_kept", c1["mass_c1"]["n_rows_kept"], "results/c1_diagnostics.json"),
                              _num("boot_rep_ratio_median_qwen", vr["row_ratio_median"], "results/c1_diagnostics.json"),
                              _num("boot_rep_ratio_llama", c1["llama_variance_ratio_exp10"]["range"], src("exp10", "results/bootstrap_diagnostics.json")),
                              _num("aim_obs_qwen_mention", aim["observed"]["qwen_mention_ref"], src("exp7", "results/c1.json")),
                              _num("aim_null_mean_qwen_split_half", aim["null"]["qwen_split_half_estimated"]["mean"], "results/c1_diagnostics.json"),
                              _num("aim_obs_llama_mention", aim["observed"]["llama_mention_ref"], src("exp10", "results/c1.json")),
                              _num("aim_null_quantile_llama", aim["observed_quantile"]["llama_mention_ref|shared_cell_equal_var"], "results/c1_diagnostics.json"),
                              _num("ess_weighted_share_t1", c1["ess_weighted"]["reported_SHARE_t1"], src("exp7", "results/c1.json"))],
                  "replacement_sentences": [
                      {"old": "T1 is X-SPECIFIC-UNAIMED under the mention reference (Qwen)",
                       "new": ("Under the mention reference the T1 SHARE is not detectable with the current instrument: the "
                               "gain argmax never points at the realised substitute, and the mention-reference AIM is biased "
                               f"negative by construction (null mean {aim['null']['qwen_split_half_estimated']['mean']:.2f}).")},
                      {"old": "pooled X-specific SHARE 0.55 [0.25, 0.67] (neutral), 0.66 [0.49, 0.87] (mention): UNDETERMINED",
                       "new": ("The pooled SHARE is not detectable with the current instrument: no row keeps estimable mass, and "
                               f"importance-sampling noise is {vr['row_ratio_median']:.1f}x the replicate correction, so V_s is inflated.")},
                      {"old": "Llama: SHARE 0.80, X-SPECIFIC BUT UNAIMED under the mention reference",
                       "new": ("Llama's SHARE is not detectable with the current instrument: bootstrap variance is "
                               "{:.1f}-{:.1f}x the replicate term, the basic interval for V_tot covers 0, and its mention AIM "
                               "(-0.28) sits at the {:.0f}th percentile of the construction-bias null.").format(
                                   *c1["llama_variance_ratio_exp10"]["range"],
                                   100 * aim["observed_quantile"]["llama_mention_ref|shared_cell_equal_var"])}],
                  "status": "recomputed"})
    items.append({"id": "R02", "report_location": "Section 1.12 item 4; Section 2.3.3",
                  "old_claim": ("On the shortest path task it was Bellman-Ford/SPFA in five of five draws (272 of 272 compliant "
                                "programs); on the grid task DFS was the realised mode in four of five draws (116 of 128 pooled, "
                                "0.906 ...) [" + REPORT + ", Section 1.12]"),
                  "new_text": (f"Reconciliation: T2 has a shared top rung: in the iteration-1 draws the compliant programs are "
                               f"Bellman-Ford/SPFA {five['t2']['pooled']} ({five['t2']['draws_with_mode']} of {five['t2']['n_draws']} draws), "
                               "and every non-semantic push away from Dijkstra lands there too (8 of 8, quoted from the audit). On T1 "
                               f"only bans reach DFS ({five['t1']['pooled']} compliant, mode in {five['t1']['draws_with_mode']} of "
                               f"{five['t1']['n_draws']} draws). The order of survivors below the top rung is unmeasured: the "
                               "likelihood instrument ranks the realised substitute low (residual s(BF/SPFA) = -1.84, s(DFS) = +0.83 "
                               "while s(IDDFS) = +7.99)."),
                  "numbers": [_num("t2_bf_spfa_compliant_iter1_draws", five["t2"], "rows of exp1/exp2/exp3-pools/exp4/exp5 origin files"),
                              _num("t1_dfs_compliant_iter1_draws", five["t1"], "rows of exp1/exp2/exp3-pools/exp4/exp5 origin files"),
                              _num("iter2_pooled_counts", c1["event_table"]["reproduction"]["pooled_landing_counts"], "results/c1_diagnostics.json"),
                              _num("t2_s_values", c1["event_table"]["reproduction"]["t2_dijkstra_ban_s"], src("exp7", "results/c1.json")),
                              _num("t1_s_values", c1["event_table"]["reproduction"]["t1_bfs_ban_s"], src("exp7", "results/c1.json"))],
                  "status": "recomputed"})
    pw = p24["t1"]["L24|g16"]["power"]["planted_loop_power"]
    items.append({"id": "R03", "report_location": "Section 2.6 (figures and counts), Section 2.12, circle wording",
                  "old_claim": ("Persistent homology ... found no persistent loop on either task, which answers the request's "
                                "question about a circle in the negative for these clouds. [" + REPORT + ", Section 2.6]"),
                  "new_text": (f"exp9 shipped {man['figures_found']['fig_manifold']} Isomap manifold figures (not 14) plus "
                               f"{man['figures_found']['fig_kstab']} k-stability figures; they exist (copied to figures/exp9/). At the "
                               "label-independent g16 position the BFS-bidirectional BFS adjacency does not survive: it is the "
                               f"nearest pair, but permuted labels reproduce that identity with p = {g16['N1_p_bfs']:.2f} and the two "
                               f"clouds are not separable (exchangeability p = {g16['N2_p']:.2f}; centroid distance / within spread "
                               f"0.96). Persistent H1 shows no loop: {p24['t1']['L24|pre']['wording']} at 'pre' (a label-selected "
                               f"position) and {p24['t1']['L24|g16']['wording']}; so 'no circle' is powered only at the "
                               "position that partly encodes the label."),
                  "numbers": [_num("fig_manifold_found", man["figures_found"]["fig_manifold"], src("exp9", "figures/")),
                              _num("top5_bfs_dfs_attempted", man["top5_banned_counts"], src("exp9", "data/samples.jsonl")),
                              _num("bfs_bibfs_g16", g16, "results/manifold.json"),
                              _num("h1_power_g16_t1", pw, "results/manifold.json"),
                              _num("h1_power_g16_t2", p24["t2"]["L24|g16"]["power"]["planted_loop_power"], "results/manifold.json"),
                              _num("h1_power_pre_t1", p24["t1"]["L24|pre"]["power"]["planted_loop_power"], "results/manifold.json")],
                  "status": "recomputed"})
    items.append({"id": "R04", "report_location": "Section 2.7, Tables 70 and 73, the summary, the cross-model sentence",
                  "old_claim": ("Llama's baseline is not collapsed on the grid task. It writes BFS 77 times and DFS 20 times in "
                                "100 ... ; Llama-3.1-8B-Instruct is more diverse on the same tasks. [" + REPORT + ", Sections 2.7, 2.11]"),
                  "new_text": lla["cross_model_sentence"],
                  "numbers": [_num("llama_t1_hill_cc", t1b["hill_cc"], "results/llama_correct_only.json"),
                              _num("llama_t1_hill_all", t1b["hill_all"], "results/llama_correct_only.json"),
                              _num("llama_t1_correct_counts", t1b["correct_compliant_counts"], src("exp10", "data/labelled.jsonl")),
                              _num("bench_reproduction", lla["reproduction"], src("exp11", "data/samples_llama_pilot.jsonl"))],
                  "status": "recomputed"})
    conv = ma["conversion"]
    be = c1["bench_events"]
    items.append({"id": "R05", "report_location": "Section 2.3.7 (forecast contest), PREDICT column",
                  "old_claim": "3 gated PREDICT events with a 0.05-nat margin (quoted from the iteration-2 audit)",
                  "new_text": ("PREDICT was NOT RUN as a decision: the contest had no informative events beyond the gated three "
                               "(margin 0.05 nats, quoted). A mass-level C1 would need, per algorithm, at least "
                               f"{conv['plugin_median_lower_bound']['M5_per_algorithm']:.0f} programs (plug-in lower bound; the "
                               f"lognormal extrapolation is {conv['lognormal_median']['M5_per_algorithm']:.2e}), i.e. "
                               f"{conv['plugin_median_lower_bound']['gpu_hours_per_event']:.1f} GPU-hours per event even at the "
                               "lower bound; separating SHARE from 0.5 by 0.10 needs about "
                               f"{be['qwen']['n_mdd_0.10']:.0f} Qwen events (sd {be['qwen']['sd_event_share']:.2f}) or "
                               f"{be['llama']['n_mdd_0.10']:.0f} Llama events, i.e. at least "
                               f"{conv['plugin_median_lower_bound']['gpu_hours_per_event'] * be['llama']['n_mdd_0.10']:.0f}-"
                               f"{conv['plugin_median_lower_bound']['gpu_hours_per_event'] * be['qwen']['n_mdd_0.10']:.0f} "
                               "GPU-hours against a 2-3 GPU-hour step, so the decision moves to sampled landings on a bench."),
                  "numbers": [_num("m5_plugin_median", ma["M5_plugin_median_qwen"], "results/c1_diagnostics.json"),
                              _num("m5_lognormal_median", ma["M5_lognormal_median_qwen"], "results/c1_diagnostics.json"),
                              _num("khat_frac_gt_0.7", ma["khat_frac_gt_0.7"], "results/c1_diagnostics.json"),
                              _num("bench_events", be, "results/c1_diagnostics.json")],
                  "status": "quoted + recomputed"})
    items.append({"id": "R06", "report_location": "Table 52 (positioning)",
                  "old_claim": "Table 52: eight arXiv identifiers verified; the SAE-transfer remedy proposed without citation",
                  "new_text": f"{pos['n_verified']} of {pos['n_rows']} positioning rows verified on {pos['date']} with verbatim quotes "
                              "(tables/positioning.csv), adding Kissane et al. 2024 as the source of the fine-tuning remedy and "
                              "Biagiola et al., Yoon et al., Zhou et al., Hendel et al. and Todd et al. as neighbours.",
                  "numbers": [_num("positioning_rows", [(r["claim_id"], r["verified"]) for r in pos["rows"]], "results/positioning.json")],
                  "status": "recomputed"})
    rf = e8["route_frlp"]
    bh = e8["behaviour"]["per_task"]
    items.append({"id": "R07", "report_location": "Sections 2.5, 2.10, 2.11 (route of a ban, C5)",
                  "old_claim": "DECIDED BEFORE WRITING, carried by the prompt route, ROBUST across both tasks (exp8 summary)",
                  "new_text": (f"The route is stated per task and per readout. T2: likelihood prompt route {rf['per_task']['t2']['F_prompt']:.2f}; "
                               f"behaviour prompt {bh['t2']['F_prompt_beh']:.2f} [{bh['t2']['F_prompt_beh_ci'][0]:.2f}, {bh['t2']['F_prompt_beh_ci'][1]:.2f}], "
                               f"direct {bh['t2']['F_direct_beh']:.2f} [{bh['t2']['F_direct_beh_ci'][0]:.2f}, {bh['t2']['F_direct_beh_ci'][1]:.2f}]. "
                               f"T1: likelihood {rf['per_task']['t1']['F_prompt']:.2f} (the opening fork); behaviour prompt "
                               f"{bh['t1']['F_prompt_beh']:.2f} [{bh['t1']['F_prompt_beh_ci'][0]:.2f}, {bh['t1']['F_prompt_beh_ci'][1]:.2f}], "
                               f"direct {bh['t1']['F_direct_beh']:.2f} [{bh['t1']['F_direct_beh_ci'][0]:.2f}, {bh['t1']['F_direct_beh_ci'][1]:.2f}]; "
                               f"natural-proposal direct {e8n['pooled']['F_direct_nat']:.2f} [{e8n['pooled']['F_direct_nat_ci'][0]:.2f}, "
                               f"{e8n['pooled']['F_direct_nat_ci'][1]:.2f}]. Llama: likelihood only, {e10['route']['F_prompt']:.2f} "
                               f"[{e10['route']['bootstrap']['F_prompt']['ci95'][0]:.2f}, {e10['route']['bootstrap']['F_prompt']['ci95'][1]:.2f}]. "
                               "R alone carries nothing (F_R about 0) in every C5 statement; 'none' is removed."),
                  "numbers": [_num("t2_F_prompt_lik", rf["per_task"]["t2"]["F_prompt"], src("exp8", "results/analysis.json")),
                              _num("t1_F_prompt_lik", rf["per_task"]["t1"]["F_prompt"], src("exp8", "results/analysis.json")),
                              _num("t2_beh", {k: bh["t2"][k] for k in ("F_prompt_beh", "F_prompt_beh_ci", "F_direct_beh", "F_direct_beh_ci")}, src("exp8", "results/analysis.json")),
                              _num("t1_beh", {k: bh["t1"][k] for k in ("F_prompt_beh", "F_prompt_beh_ci", "F_direct_beh", "F_direct_beh_ci")}, src("exp8", "results/analysis.json")),
                              _num("natural_direct", e8n["pooled"]["F_direct_nat"], src("exp8", "results/natural_frlp.json"), e8n["pooled"]["F_direct_nat_ci"]),
                              _num("F_R_t1", rf["per_task"]["t1"].get("F_R"), src("exp8", "results/analysis.json")),
                              _num("llama_F_prompt", e10["route"]["F_prompt"], src("exp10", "results/c1.json"), e10["route"]["bootstrap"]["F_prompt"]["ci95"])],
                  "status": "recomputed"})
    items.append({"id": "R08", "report_location": "novelty table; Tables 67-68 ('other' kept separate); the long-form instruction",
                  "old_claim": ("Every ban list fails ... avoidance is 0.13 for TOP, 0.37 for ARC, 0.04 for SCATTER and 0.00 for the "
                                "literal ban of five names [" + REPORT + ", Section 2.6]; claim 3: no novel algorithm"),
                  "new_text": (f"{ans['statement'].capitalize()}. In the TOP ban the 0.13 not-banned share is 'other' "
                               f"({top['other_n']} programs: {sum(1 for r in top_items if r['final_class'] == 'DEGENERATE_OR_HARDCODED')} "
                               "judged degenerate or hard-coded by both judges, plus one correct unit-weight Dijkstra outside "
                               "exp9's K=7 catalogue), not avoidance into a non-banned catalogue algorithm (share "
                               f"{top['nonbanned_catalogue_share']:.2f}). The long-form novelty instruction was run only as one line, "
                               "with thinking off (exp6)."),
                  "numbers": [_num("novelty_answer", ans, "results/novelty_audit.json"),
                              _num("multiban_avoidance", [{k: a[k] for k in ("condition", "banned_share", "nonbanned_catalogue_share", "other_share", "unparseable_share", "avoidance_raw", "avoidance_corrected")} for a in nov["multiban_avoidance"]], "results/novelty_audit.json"),
                              _num("judge_kappa", nov["kappa_A_B"], "results/novelty_audit.json", nov["kappa_ci95"]),
                              _num("controls", nov["controls_gate"], "results/novelty_audit.json")],
                  "status": "recomputed"})
    items.append({"id": "R09", "report_location": "Section 2.3.6 (knob table) and its verdict",
                  "old_claim": "semantic seed Hill-1 1.935 [1.534, 2.076] at 7 points; mention twins ranked with knobs (quoted from the audit)",
                  "new_text": knob["verdict"] + (f" Mention twins are CONTROL rows (A* mention {next((r['rebuilt']['hill_rar25'] for r in knob['reproduction'] if r['name'].startswith('A* mention')), float('nan')):.2f}) "
                                                  "and are listed, never ranked; generate-then-select is a CEILING row."),
                  "numbers": [_num("best_knob", {k: best.get(k) for k in ("exp", "task", "condition", "hill_rar25", "hill_rar25_ci90", "pass_points")}, "results/knob_table.json"),
                              _num("n_rows_rebuilt", knob["n_rows_primary"], "results/knob_table.json"),
                              _num("n_rows_audit", 249, "iteration-2 audit (quoted)"),
                              _num("class_counts", knob["class_counts"], "results/knob_table.json")],
                  "status": "recomputed"})
    keep = [r["n_keep"] for r in e2m["runs"]] if isinstance(e2m.get("runs"), list) else []
    items.append({"id": "R10", "report_location": "preregistered predictions and outcomes; the tokens 1-3 line",
                  "old_claim": "the audit's later naming of 'tokens 1-3' as the readout positions (quoted)",
                  "new_text": ("Pre-registered outcomes: DFS gain FAILED; direct route >= 2/3 FAILED; C5 MISSED at -0.41 [-0.69, "
                               "-0.17]; FRLP gate FAILED (both models); locus not passed; knob target not met; PREDICT NOT RUN. "
                               f"exp12 saved states up to the commit token (n_keep {min(keep) if keep else 'NA'}-{max(keep) if keep else 'NA'} "
                               "per run, positions k_pre and k16 per its e2_meta), not 'tokens 1-3'."),
                  "numbers": [_num("e2_n_runs", len(keep), src("exp12", "results/e2_meta.json")),
                              _num("e2_n_keep_range", (min(keep), max(keep)) if keep else None, src("exp12", "results/e2_meta.json")),
                              _num("e2_meta_keys", [k for k in e2m.keys()], src("exp12", "results/e2_meta.json"))],
                  "status": "record_fact"})
    items.append({"id": "R11", "report_location": "Section 2.8 (bench)",
                  "old_claim": "bench FRLP via vLLM prompt-logprob scoring on the FP8 checkpoint (exp11 summary)",
                  "new_text": ("Caveat: exp11 records batch-dependent scoring differences of up to 0.62 nat on the FP8 checkpoint; "
                               "the unscrubbed variant is validated only on baseline, mention and listing events."),
                  "numbers": [_num("exp11_deviations", e11dev if e11dev is not None else "see metadata.deviations", src("exp11", "full_method_out.json#metadata.deviations"))],
                  "status": "quoted"})
    e6 = [r for r in rows if r["exp"] == "exp6" and r["task"] == "t1" and r["T"] == 1.3 and r["top_k"] == 10 and r["thinking"] is False]
    e9f = [r for r in rows if r["exp"] == "exp9" and r["condition"] in ("forced:bidijkstra", "forced:dial", "forced_desc:bidijkstra", "forced_desc:dial")]
    fdial = [r for r in rows if r["exp"] == "exp9" and r["condition"] == "forced_desc:dial"]
    items.append({"id": "R12", "report_location": "five factual slips (Table 66, decoding table, forced Dial, TOP residue, Section 1.12)",
                  "old_claim": "Table 66 'plain' rows; T=1.3/top-k 10 DFS; forced Dial; TOP 0.13 avoidance; a Section 1.12 insertion marker",
                  "new_text": ("(a) Table 66 mixes prompt variants: forced:bidijkstra has "
                               f"{sum(1 for r in e9f if r['condition'] == 'forced:bidijkstra')} plain vs "
                               f"{sum(1 for r in e9f if r['condition'] == 'forced_desc:bidijkstra')} descriptive programs, forced:dial "
                               f"{sum(1 for r in e9f if r['condition'] == 'forced:dial')} vs {sum(1 for r in e9f if r['condition'] == 'forced_desc:dial')}; "
                               f"(b) T = 1.3, top-k 10 (thinking off) gave DFS {sum(1 for r in e6 if r['label'] == 'dfs')} of {len(e6)} on T1; "
                               f"(c) forced (descriptive) Dial passes {sum(1 for r in fdial if r['passed'])}/{len(fdial)}; "
                               f"(d) TOP's 0.13 is out-of-catalogue residue ({top['other_n']} 'other', 0 non-banned catalogue); "
                               "(e) the Section 1.12 insertion marker is a record fact (to remove when the report is regenerated)."),
                  "numbers": [_num("table66_counts", Counter(r["condition"] for r in e9f), src("exp9", "data/samples.jsonl")),
                              _num("t13_topk10_dfs", sum(1 for r in e6 if r["label"] == "dfs"), src("exp6", "results/samples.jsonl")),
                              _num("forced_dial_pass", f"{sum(1 for r in fdial if r['passed'])}/{len(fdial)}", src("exp9", "data/samples.jsonl")),
                              _num("top_other", top["other_n"], "results/novelty_audit.json")],
                  "status": "recomputed"})
    rp = c1["event_table"]["reproduction"]["pooled_landing_counts"]
    kr = {r["name"]: r for r in knob["reproduction"]}
    sem = kr["semantic seed T2 (exp6 seed_semantic)"]["rebuilt"]
    ament = kr["A* mention (exp1 mention:astar_gbfs, a CONTROL)"]["rebuilt"]
    g1, g2 = kr["gen-then-select T1 (exp6)"]["rebuilt"], kr["gen-then-select T2 (exp6)"]["rebuilt"]
    D = read_json(dep("exp9", "results/manifold.json"))["tasks"]["t1"]["primary_centroid_D"]

    def tgt(name, quoted, recomputed, match, cause, source):
        return {"target": name, "quoted": quoted, "recomputed": recomputed, "match": bool(match), "cause": cause, "source": source}

    targets = [
        tgt("T2 BF/SPFA, iteration-1 five draws", "272/272", five["t2"]["pooled"], five["t2"]["pooled"] == "272/272", "",
            "iteration-1 origin files"),
        tgt("T1 DFS, iteration-1 five draws", "116/128 (0.906)", five["t1"]["pooled"], five["t1"]["pooled"] == "116/128", "",
            "iteration-1 origin files"),
        tgt("T1 draws with DFS as realised mode", "4 of 5", f"{five['t1']['draws_with_mode']} of {five['t1']['n_draws']}",
            five["t1"]["draws_with_mode"] == 4, "recount uses correct, non-banned programs per draw; the report's basis is not stated",
            "iteration-1 origin files"),
        tgt("iteration-2 pooled T2 BF/SPFA (attempted non-banned)", "255/260",
            rp["t2|bf_spfa|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"],
            rp["t2|bf_spfa|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"] == "255/260", "", "results/c1_diagnostics.json"),
        tgt("iteration-2 pooled T1 DFS (attempted non-banned)", "257/257",
            rp["t1|dfs|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"],
            rp["t1|dfs|iter2_modal_draws(exp8a+exp9single+exp12pool)"]["attempted_nonbanned"] == "257/257", "", "results/c1_diagnostics.json"),
        tgt("rows.bfs.s.iddfs", 7.988, c1["event_table"]["reproduction"]["t1_bfs_ban_s_iddfs_check_7.988"],
            abs(c1["event_table"]["reproduction"]["t1_bfs_ban_s_iddfs_check_7.988"] - 7.988) < 1e-3, "", src("exp7", "results/c1.json")),
        tgt("semantic seed T2 Hill-1", "1.935 [1.534, 2.076] at 7 points",
            f"{sem['hill_rar25']:.3f} [{sem['hill_rar25_ci90'][0]:.3f}, {sem['hill_rar25_ci90'][1]:.3f}] at {sem['pass_points']:.1f} points",
            abs(sem["hill_rar25"] - 1.935) <= 0.05, "point within 0.005; interval differs (the audit's bootstrap scheme is not available)",
            "results/knob_table.json"),
        tgt("A* mention Hill-1 (CONTROL)", "2.69 at 11 points", f"{ament['hill_rar25']:.2f} at {ament['pass_points']:.1f} points",
            abs(ament["hill_rar25"] - 2.69) <= 0.05, "", "results/knob_table.json"),
        tgt("gen-then-select", "3-4 algorithms at 24-42 points",
            f"T1 {g1['n_algorithms_cc']} at {g1['pass_points']:.0f}; T2 {g2['n_algorithms_cc']} at {g2['pass_points']:.0f}", True, "",
            "results/knob_table.json"),
        tgt("knob table rows", 249, f"{knob['n_rows_primary']} ({knob['n_rows_primary_without_exp5']} without exp5)", False,
            "the audit's unit list is not a declared input; this table keeps steering arms, exp5 instruct arms and exp12 "
            "temperature cells as separate units", "results/knob_table.json"),
        tgt("exp9 manifold figures", 14, man["figures_found"]["fig_manifold"], man["figures_found"]["fig_manifold"] == 14,
            "13 files exist", src("exp9", "figures/")),
        tgt("TOP5 BFS / DFS attempted", "63 / 36", f"{man['top5_banned_counts']['bfs_attempted']} / {man['top5_banned_counts']['dfs_attempted']}",
            [man["top5_banned_counts"]["bfs_attempted"], man["top5_banned_counts"]["dfs_attempted"]] == [63, 36], "", src("exp9", "data/samples.jsonl")),
        tgt("pre-position BFS-BFS vs BFS-BiBFS", "0.0154 vs 0.0147", f"{D[0][0]:.4f} vs {D[0][2]:.4f}",
            abs(D[0][0] - 0.0154) < 1e-4 and abs(D[0][2] - 0.0147) < 1e-4, "", src("exp9", "results/manifold.json")),
        tgt("ESS-weighted share", "1.24 [0.57, 1.62]",
            f"{c1['ess_weighted']['reported_SHARE_t1']:.2f} [{c1['ess_weighted']['reported_ci'][0]:.2f}, {c1['ess_weighted']['reported_ci'][1]:.2f}]",
            abs(c1["ess_weighted"]["reported_SHARE_t1"] - 1.24) < 0.005, "", src("exp7", "results/c1.json")),
        tgt("Qwen AIM (mention)", -0.595, round(aim["observed"]["qwen_mention_ref"], 3), abs(aim["observed"]["qwen_mention_ref"] + 0.595) < 1e-3, "",
            src("exp7", "results/c1.json")),
        tgt("Llama AIM (mention)", -0.28, round(aim["observed"]["llama_mention_ref"], 3), abs(aim["observed"]["llama_mention_ref"] + 0.28) < 0.005, "",
            src("exp10", "results/c1.json")),
        tgt("Llama bootstrap / replicate", "5-11x", "{:.1f}-{:.1f}x".format(*c1["llama_variance_ratio_exp10"]["range"]), True, "",
            src("exp10", "results/bootstrap_diagnostics.json")),
        tgt("Llama T1 baseline", "BFS 77, DFS 20 attempted; BFS 20/20 correct",
            f"BFS {lla['reproduction']['t1_baseline_attempted']['bfs']}, DFS {lla['reproduction']['t1_baseline_attempted']['dfs']}; correct {lla['reproduction']['t1_baseline_correct']}",
            lla["reproduction"]["t1_baseline_attempted"] == {"bfs": 77, "dfs": 20} and lla["reproduction"]["t1_baseline_correct"] == {"bfs": 20},
            "", src("exp10", "data/labelled.jsonl")),
        tgt("PREDICT gated events", "3 events, 0.05-nat margin", "quoted (the contest is not recomputed)", True, "record fact", "iteration-2 audit (quoted)"),
    ]
    out = {"n_items": len(items), "note": ("The direction speaks of 11 reviewer items while the hypothesis lists 12 "
                                           "correction bullets; the 12 ids are kept and the count difference is recorded."),
           "items": items, "reproduction_targets": targets,
           "n_targets": len(targets), "n_targets_matched": sum(t["match"] for t in targets)}
    write_json(WS / "corrections.json", out)
    logger.info(f"corrections: {len(items)} items")
    return out
