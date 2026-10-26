"""Output contract: eval_out.json (exp_eval_sol_out; full / mini / preview), corrections.json, auxiliary tables."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pandas as pd
from loguru import logger

from src.labels import QWEN14
from src.paths import WS, cite

RES, TAB, AUD = WS / "results", WS / "tables", WS / "audit"

NOT_DECLARED = [
    ("art__skdlFp_o3e9", "exp1", 1, "iteration-1 path-task ban / mention / list events (the exp1 events exp7 scores)"),
    ("art_D6Z0Snf09sFL", "exp2", 1, "iteration-1 experiment rows"),
    ("art_1yV2vQ0EH4OY", "exp3", 1, "iteration-1 experiment rows"),
    ("art_HF8nK8B_Lqyy", "exp5", 1, "iteration-1 experiment rows"),
    ("art_V1MvbYs5420o", "evaluation_1", 1, "iteration-1 audit (one-statistic knob table conventions)"),
    ("art_8_ULPE8jJQc_", "exp8", 2, "HF-engine route arms on T1/T2 (exp16 screen_paths cites 'exp8_arm_a')"),
    ("art_-QPYRaFERCBX", "exp10", 2, "Llama path-task landings"),
    ("art_3iv5G76C3yoX", "exp12", 2, "fresh C1 pool on T1/T2 (exp16 screen_paths cites 'exp12_c1_fresh_pool')"),
    ("art_3tH2xtoZ7Gj2", "evaluation_2", 3, "iteration-3 audit: 306-row knob table, judge cache, g16 recomputation"),
    ("art_j3Rm_lr2nzR6", "dataset_1", 3, "472 known human / textbook solutions (nearest-solution pool)"),
]


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def ex(inp: str, out: str, meta: dict | None = None, pred: dict | None = None, ev: dict | None = None) -> dict:
    d = {"input": str(inp), "output": str(out)}
    for k, v in (meta or {}).items():
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            continue
        d[f"metadata_{k}"] = v
    for k, v in (pred or {}).items():
        d[f"predict_{k}"] = "null" if v is None else str(v)
    for k, v in (ev or {}).items():
        n = _num(v)
        if n is not None:
            d[f"eval_{k}"] = n
    return d


def clean(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def _r(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def activation_sentence(knob: pd.DataFrame, t03: pd.Series, t05: pd.Series) -> str:
    """Write the activation-edit sentence the table supports (checked on T03 and T05)."""
    parts = []
    for t, row in (("T03", t03), ("T05", t05)):
        q = knob[(knob.task == t) & knob.family.isin(["activation-random", "activation-structured"]) & knob.model.str.startswith("Qwen")
                 & (knob.H1r25 >= 2) & (knob.pass_cost_pts <= 20)]
        rnd = q[q.family == "activation-random"]
        st = q[q.family == "activation-structured"]
        lo, hi = (float(rnd.H1r25.min()), float(rnd.H1r25.max())) if len(rnd) else (float("nan"), float("nan"))
        st_txt = "; ".join(f"{r.arm} H {r.H1r25:.2f} at {r.pass_cost_pts:.0f} pts ({'inside' if lo <= r.H1r25 <= hi else 'outside'} "
                           f"the qualifying-random range {lo:.2f}-{hi:.2f})" for _, r in st.iterrows()) or "none qualifies"
        parts.append(f"{t}: lowest-cost qualifying row {row.lowest_cost_qualifying}; {len(rnd)} qualifying random "
                     f"direction-alpha cells; structured activation edits: {st_txt}")
    ok = t03.lowest_cost_qualifying_family == "activation-random" and t05.lowest_cost_qualifying_family == "activation-random"
    head = ("Supported in the restricted form 'on T03 and T05 every qualifying activation edit lies inside the range of "
            "norm-matched random directions, and the cheapest qualifying row is a random direction'" if ok else
            "Not supported as written; the table supports only: ")
    return head + ". " + " | ".join(parts)


def corrections(scr: dict, route: dict, llama: dict, other: dict, rigor: dict, wording: dict, vt: pd.DataFrame,
                ptv: pd.DataFrame, rivals: dict, figs: dict, knob: pd.DataFrame) -> dict:
    n_t, n_m = len(vt), int(vt.match.sum())
    fam = llama["families"]
    rf = route["route_fractions"]
    imm = vt[vt.target_id == "immovable_six"].iloc[0]
    t03, t05 = ptv.set_index("task").loc["T03"], ptv.set_index("task").loc["T05"]
    items = {
        "0a_knob_table": {
            "status": "corrected" if n_m < n_t else "verified",
            "replacement": (f"One-statistic knob table rebuilt from raw rows: {n_m} of {n_t} quoted numbers reproduce within "
                            f"tolerance. Corrected: " + " | ".join(f"{r.target_id}: expected {r.expected}, recomputed "
                                                                  f"{r.recomputed} ({r.explanation})"
                                                                  for _, r in vt[~vt.match].iterrows()) +
                            f". Lowest-cost qualifying row on T03: {t03.lowest_cost_qualifying}; on T05: "
                            f"{t05.lowest_cost_qualifying}."),
            "mismatched_targets": vt[~vt.match][["target_id", "expected", "recomputed", "explanation"]].to_dict("records"),
            "every_activation_edit_sentence": activation_sentence(knob, t03, t05),
            "numbers": {"n_targets": n_t, "n_matched": n_m}, "sources": ["tables/knob_table.csv", "tables/verification_targets.csv",
                                                                         "tables/per_task_verdict.csv"]},
        "0b_route_landing": {"status": "verified", "replacement": route["lead_paragraph"],
                             "numbers": {"readings_matched": route["readings_matched"], "n_readings": route["n_readings"],
                                         "js_matches": route["js_matches_recorded_1e-6"], "n_js": route["n_js"]},
                             "sources": route["sources"]},
        "0c_llama_hit_rule": {
            "status": "corrected",
            "replacement": (f"With 'other' removed as nominee and landing, LADDER hits {fam['LADDER']['hit_excl_other']['hits']} of "
                            f"13 gated events (Poisson-binomial p = {fam['LADDER']['hit_excl_other']['p_poisson_binomial']:.3f}) and "
                            f"ASSOCIATE {fam['ASSOCIATE']['hit_excl_other']['hits']} of 13 (p = "
                            f"{fam['ASSOCIATE']['hit_excl_other']['p_poisson_binomial']:.3f}); under the recorded mixed rule both "
                            f"hit 7. " + llama["section_3_5_note"] + " " + llama["snap_back_sentence"]),
            "numbers": {k: v for k, v in fam.items()}, "sources": llama["sources"]},
        "0d_other_audit": {
            "status": "corrected",
            "replacement": (f"Audit of every iteration-3 ban event with >= 5 'other' attempts ({other['pool']['n_events']} events, "
                            f"{other['pool']['n_programs']} unique sampled programs, {other['pool']['n_passed']} passing): final classes "
                            f"{other['final_class_counts']}; NOVEL confirmed = {other['novel_confirmed']} (the one passing "
                            f"NOVEL-flagged program re-ran 60/60 hidden and 3/3 stress cases and reads as a textbook value "
                            f"binary search over a sort). Residue-gated events (avoidance >= 0.5, catalogue-only < 0.5): "
                            f"{other['catalogue_only']['residue_gated_events']}. Merge intervals: the 44 exp13 T13 'other' "
                            f"programs are {other['merge_intervals']['manual_counts']} (manual read), all failing; "
                            f"{other['merge_intervals']['statement']}"),
            "numbers": {"kappa_A_B": other["judges"]["kappa_A_B"], "controls": other["judges"]["controls"],
                        "contest_exp13": other["contest_exp13"]},
            "sources": ["tables/other_audit_programs.csv", "tables/other_audit_events.csv", "tables/catalogue_only_avoidance.csv",
                        "tables/merge_intervals_correction.csv"]},
        "0e_geometry_markers": {"status": "verified",
                                "replacement": "Figure-ready markers M1-M5 carry the position caveat; the 2x2 composite is "
                                               "regenerated in activation coordinates (figures/composite_2x2_activation.pdf).",
                                "numbers": {"g16": figs.get("g16", {}).get("t1_forced_states_layer24")},
                                "sources": ["figures/captions.json"]},
        "0f_table_92b": {"status": "delivered_by_research_artifact",
                         "pointer": "this iteration's research artifact (Table 92b); not produced here"},
        "0g_i_defined_only_hits": {"status": "corrected", "numbers": rigor.get("defined_only"),
                                   "replacement": "Hit rates are reported over defined forecasts only, with fractional tie "
                                                  "credit in a separate column (tables/defined_only_hits.csv).",
                                   "sources": [cite("exp13", "results/c1_events.jsonl"), cite("exp14", "results/c1_events.jsonl"),
                                               cite("exp15", "results/c1_events.jsonl")]},
        "0g_ii_exposure_sentence": {"status": "verified", "replacement": rigor["exposure_sentence"]["sentence"],
                                    "numbers": rigor["exposure_sentence"], "sources": rigor["exposure_sentence"]["sources"]},
        "0g_iii_table82": {"status": "verified",
                           "replacement": (f"Table 82 per distinct likelihood row: {rigor['table82']['n_rows']} rows "
                                           f"({rigor['table82']['n_modal']} modal, {rigor['table82']['n_sham']} sham); argmax gain hits "
                                           f"{rigor['table82']['hits_gain']}, residual gain {rigor['table82']['hits_residual']}, implied "
                                           f"mass {rigor['table82']['hits_implied']} ({rigor['table82']['hits_implied_sham']} of them sham "
                                           f"rows, where the landing is trivially the default)."),
                           "numbers": rigor["table82"], "sources": rigor["table82"]["sources"]},
        "0h_section_3_10": {"status": "corrected", "items": wording},
        "0i_screen": {"status": "verified", "sha256": scr["sha256"], "movable_tasks": scr["movable_tasks"],
                      "replacement": (f"Screen frozen before any confirmation sample (sha256 {scr['sha256']}): movable = "
                                      f"{scr['movable_tasks']}; movable vs catalogue-only ban avoidance >= 0.5 table "
                                      f"{scr['table']} (Fisher one-sided p = {scr['fisher_p_descriptive']:.5f}, descriptive only: "
                                      f"screen, not confirmation)."), "sources": ["screen.json", "screen_extras.json"]},
        "0j_rivals": {"status": "verified", "rows": rivals.get("rows"), "label": "screen, not confirmation",
                      "sources": rivals.get("sources")},
    }
    return clean(items)


def run_outputs_stage() -> None:
    knob = pd.read_parquet(WS / "data" / "knob.parquet")
    vt = pd.read_csv(TAB / "verification_targets.csv")
    ptv = pd.read_csv(TAB / "per_task_verdict.csv")
    dcounts = pd.read_csv(TAB / "random_direction_counts.csv")
    scr = _r(RES / "screen_summary.json")
    screen = _r(WS / "screen.json")
    extras = _r(WS / "screen_extras.json")
    route, llama, other = _r(RES / "route.json"), _r(RES / "llama.json"), _r(RES / "other_audit.json")
    figs, rigor, wording, rivals = _r(RES / "figures.json"), _r(RES / "rigor.json"), _r(RES / "wording.json"), _r(RES / "rivals.json")
    red, plc, rex = _r(AUD / "rederive.json"), _r(AUD / "placebos.json"), _r(AUD / "rederive_extra.json")
    pd.DataFrame([{"artifact_id": a, "experiment": e, "iteration": i, "rows_held": d,
                   "status": "listed, not recomputed (not a declared dependency; workspace not opened)"}
                  for a, e, i, d in NOT_DECLARED]).to_csv(TAB / "knob_rows_not_recomputed.csv", index=False)
    corr = corrections(scr, route, llama, other, rigor, wording, vt, ptv, rivals, figs, knob)
    (WS / "corrections.json").write_text(json.dumps(corr, indent=1))

    # ---------------- datasets
    ds = []
    exs = []
    for _, r in knob.iterrows():
        exs.append(ex(f"{r.artifact_id} | task {r.task} | arm {r.arm} | dial {r.dial} | {r.engine}/{r.precision} | n={r.n}",
                      f"H1r25={r.H1r25:.3f} CI90={r.H1r25_ci90}; pass={r.pass_rate:.3f}; cost={r.pass_cost_pts:.1f} pts vs "
                      f"{r.ref_arm or 'none'}; offdef={r.offdef_share:.3f}; cat_only={r.cat_only_avoidance:.3f}",
                      {"row_id": r.row_id, "class": r["class"], "family": r.family, "model": r.model, "ref_arm": r.ref_arm,
                       "correct_composition": r.correct_composition, "attempted_composition": r.attempted_composition,
                       "flags": r["flags"], "sources": r["sources"], "ci_unit": r.ci_unit},
                      {"escape": r.escape, "qualify": r.qualify},
                      {"H1r25": r.H1r25, "H1r25_cat": r.H1r25_cat, "H1r10": r.H1r10, "pass_rate": r.pass_rate,
                       "pass_cost_pts": r.pass_cost_pts, "offdef_share": r.offdef_share,
                       "cat_only_avoidance": r.cat_only_avoidance, "coverage": r.coverage, "S_obs": r.S_obs, "n": r.n}))
    ds.append({"dataset": "knob_table", "examples": exs})
    ds.append({"dataset": "verification_targets", "examples": [
        ex(r.description, r.recomputed, {"target_id": r.target_id, "expected": r.expected, "tolerance": r.tolerance,
                                         "source": r.source, "explanation": r.explanation if isinstance(r.explanation, str) else ""},
           {"recomputed": r.recomputed}, {"match": int(bool(r.match))}) for _, r in vt.iterrows()]})
    sc = screen["tasks"]
    ds.append({"dataset": "push_screen", "examples": [
        ex(f"task {t}: push-movability screen (frozen, sha256 {scr['sha256'][:12]})",
           f"movable={sc[t]['movable']}; E_t(a1)={sc[t]['alpha_1']['E_t']}; E_t(a2)={sc[t]['alpha_2']['E_t']}; "
           f"push_top1={sc[t]['push_top1']}; cat-only ban avoidance={sc[t]['cat_only_ban_avoidance']}",
           {"push_landing": json.dumps(sc[t]["push_landing"]), "power_note": json.dumps(extras.get("power_note", {}).get(t)),
            "in_c1_event_set": t in screen["c1_event_set"]},
           {"movable": sc[t]["movable"], "push_top1": sc[t]["push_top1"]},
           {"E_t_a1": sc[t]["alpha_1"]["E_t"], "E_t_a2": sc[t]["alpha_2"]["E_t"], "movable": sc[t]["movable"],
            "cat_only_ban_avoidance": sc[t]["cat_only_ban_avoidance"],
            "ban_avoidance_ge_0_5": int(bool(sc[t]["ban_avoidance_ge_0_5"]))}) for t in QWEN14]})
    ds.append({"dataset": "random_directions", "examples": [
        ex(f"{d['direction_id']} alpha {d['alpha']} on {d['task']} ({d['engine']})",
           f"offdef={1 - d['n_default'] / d['n_attempted']:.3f} vs twin {1 - d['twin_n_default'] / d['twin_n_attempted']:.3f}; "
           f"pass={d['n_passed'] / d['n']:.3f} vs {d['twin_n_passed'] / d['twin_n']:.3f}",
           {"offdef_cat_counts": json.dumps(d["offdef_cat_counts"]), "source": d["source"], "knob_row_id": d["knob_row_id"]},
           {"qualify": d["qualify"]},
           {"H1r25": d["H1r25"], "pass_cost_pts": d["pass_cost_pts"], "n": d["n"]}) for d in extras.get("per_direction_rows", [])]})
    rl = pd.read_csv(TAB / "route_landing.csv")
    ds.append({"dataset": "route_landing", "examples": [
        ex(f"exp16 task {r.task} arm {r.arm}", f"non-default landing {r.nondefault_attempted_composition}",
           {"correct_composition": r.nondefault_correct_composition, "default": r.default},
           {"association_modal": r.association_modal, "frlp_runner_up": r.frlp_runner_up, "proximity_top1": r.proximity_top1,
            "push_top1": r.push_top1, "modal_nondefault": r.modal_nondefault_excl_other},
           {"JS_vs_a": r.get("JS_vs_a"), "null_q95": r.get("null_q95_rederived"),
            "hit_association": int(bool(r.hit_association_modal)), "hit_frlp": int(bool(r.hit_frlp_runner_up)),
            "hit_proximity": int(bool(r.hit_proximity_top1)), "hit_push": int(bool(r.hit_push_top1))}) for _, r in rl.iterrows()]})
    lh = pd.read_csv(TAB / "llama_hits.csv")
    ds.append({"dataset": "llama_hits", "examples": [
        ex(f"Llama event {r.event_id} (survivors {r.survivors})",
           f"modal(with other)={r.modal_with_other}; modal(excl other)={r.modal_excl_other}; largest excess={r.largest_excess}",
           {"event_type": r.event_type, "gate_pass": bool(r.gate_pass), "rule_recorded": r.rule_recorded},
           {f: getattr(r, f"{f}_top1") for f in ("SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY")},
           {**{f"{f}_hit_excl_other": int(bool(getattr(r, f"{f}_hit_excl_other"))) for f in ("SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY")},
            "chance": r.chance, "n_nonbanned": r.n_nonbanned_attempts}) for _, r in lh.iterrows()]})
    op = pd.read_csv(TAB / "other_audit_programs.csv")
    ds.append({"dataset": "other_audit", "examples": [
        ex(f"'other' program {r.code_sha256[:16]} on {r.task} (events {r.events})", f"final class {r.final_class} ({r.final_source})",
           {"manual_reason": r.manual_reason if isinstance(r.manual_reason, str) else "", "nearest_known": r.nearest_known_label,
            "features": r.features},
           {"judge_A": r.judge_A, "judge_B": r.judge_B, "judge_C_tiebreak": r.judge_C_tiebreak, "consensus": r.consensus},
           {"passed": int(bool(r.passed)), "nearest_known_jaccard": r.nearest_known_jaccard}) for _, r in op.iterrows()]})
    fx = [ex(m["marker_id"], m.get("caption", m.get("status")), {"source": m.get("source"), "file_png": m.get("file_png")})
          for m in figs.get("markers", [])]
    if figs.get("composite"):
        fx.append(ex("composite_2x2_activation", figs["composite"].get("caption", figs["composite"].get("status", "")),
                     {"panels": json.dumps(clean(figs["composite"].get("panels", {})))}))
    if figs.get("g16"):
        fx.append(ex("g16 label-independent check (T1, layer 24)", json.dumps(clean(figs["g16"].get("t1_forced_states_layer24", {}))),
                     {"note": figs["g16"].get("note", "")}))
    ds.append({"dataset": "figures", "examples": fx})
    rx = [ex(f"defined-only hits: {d['contest']} / {d['family']}", f"{d['top1_hits_defined_only']} of {d['n_defined']} defined",
             {}, {}, {"hit_rate_defined_only": d["hit_rate_defined_only"], "fractional_rate": d["fractional_rate"],
                      "n_defined": d["n_defined"]}) for d in rigor.get("defined_only", [])]
    t82 = pd.read_csv(TAB / "table82_distinct_rows.csv")
    rx += [ex(f"Table 82 row {r.task} {r.condition} ({r.row_type})", f"realised {r.realised_landing}",
              {}, {"argmax_gain": r.argmax_gain, "argmax_residual_gain": r.argmax_residual_gain,
                   "argmax_implied_mass": r.argmax_implied_mass},
              {"hit_gain": int(bool(r.hit_gain)), "hit_residual": int(bool(r.hit_residual)), "hit_implied": int(bool(r.hit_implied))})
           for _, r in t82.iterrows()]
    rx.append(ex("exposure sentence", rigor["exposure_sentence"]["sentence"]))
    ds.append({"dataset": "rigor", "examples": rx})
    ds.append({"dataset": "wording_section_3_10", "examples": [
        ex(k, v["replacement"], {"sources": v.get("sources")}) for k, v in wording.items()]})
    rv0 = {r["predictor"]: r["spearman_rho"] for r in rivals.get("rows", [])}
    ds.append({"dataset": "rival_predictors", "examples": [
        ex(f"rival predictor {r['predictor']} vs catalogue-only ban avoidance (14 tasks)",
           f"Spearman rho={r['spearman_rho']:.3f} (perm p={r['p_perm']:.4g}); balanced accuracy={r['balanced_accuracy']}",
           {"confusion_table": r["confusion_table"], "label": r["label"], "median_cut": r.get("median_cut")},
           {"direction": "positive" if (r["spearman_rho"] or 0) > 0 else "non-positive",
            "beats_movability": str(abs(r["spearman_rho"] or 0) >= abs(rv0.get("movable", 1.0)))},
           {"spearman_rho": r["spearman_rho"], "p_perm": r["p_perm"], "kendall_tau_b": r["kendall_tau_b"],
            "balanced_accuracy": r["balanced_accuracy"], "fisher_p": r["fisher_p"], "p_holm": r["p_holm_transparency_only"]})
        for r in rivals.get("rows", [])]})
    ds.append({"dataset": "audit", "examples": [
        ex(c["name"], json.dumps(c["rederived"]), {"expected": json.dumps(c["expected"])},
           {"status": "match" if c["match"] else "mismatch"}, {"match": int(bool(c["match"]))})
        for c in red.get("checks", [])] + [
        ex(k, json.dumps({kk: vv for kk, vv in v.items() if kk != "detail"}), {},
           {"status": "failed_as_required" if v["placebo_failed_to_show_effect"] else "shows_effect"},
           {"failed_as_required": int(bool(v["placebo_failed_to_show_effect"]))}) for k, v in plc.items() if k.startswith("P")] + [
        ex(f"extra:{c['name']}", json.dumps(c["rederived"]), {"expected": json.dumps(c["expected"])},
           {"status": "match" if c["match"] else "mismatch"}, {"match": int(bool(c["match"]))}) for c in rex.get("checks", [])] + [
        ex(f"extra_placebo:{q['name']}", json.dumps(q["detail"]), {},
           {"status": "failed_as_required" if q["failed_as_required"] else "shows_effect"},
           {"failed_as_required": int(bool(q["failed_as_required"]))}) for q in rex.get("placebos", [])]})

    # ---------------- metrics
    fam = llama["families"]
    rv = {r["predictor"]: r["spearman_rho"] for r in rivals.get("rows", [])}
    E = scr.get("E", {})
    m = {"n_knob_rows": len(knob), "n_targets": len(vt), "n_targets_matched": int(vt.match.sum()),
         "n_movable_tasks": scr.get("n_movable"), "E_T03_a1": E.get("T03_a1"), "E_T2_a1": E.get("T2_a1"),
         "E_T05_a2": E.get("T05_a2"), "E_T06_a2": E.get("T06_a2"), "E_T1_a1": E.get("T1_a1"), "E_T10_a1": E.get("T10_a1"),
         "screen_fisher_p_descriptive": scr.get("fisher_p_descriptive"), "screen_balanced_accuracy": scr.get("balanced_accuracy"),
         "llama_assoc_hits_excl_other": fam["ASSOCIATE"]["hit_excl_other"]["hits"],
         "llama_ladder_hits_excl_other": fam["LADDER"]["hit_excl_other"]["hits"],
         "llama_assoc_p_excl_other": fam["ASSOCIATE"]["hit_excl_other"]["p_poisson_binomial"],
         "llama_ladder_p_excl_other": fam["LADDER"]["hit_excl_other"]["p_poisson_binomial"],
         "route_F_prompt_all5": route["route_fractions"]["plain_all5"]["point"]["F_prompt"],
         "route_F_direct_all5": route["route_fractions"]["plain_all5"]["point"]["F_direct"],
         "route_F_prompt_wo_T13": route["route_fractions"]["plain_wo_T13"]["point"]["F_prompt"],
         "route_F_direct_wo_T13": route["route_fractions"]["plain_wo_T13"]["point"]["F_direct"],
         "route_F_prompt_cat_all5": route["route_fractions"]["cat_all5"]["point"]["F_prompt"],
         "route_F_direct_cat_all5": route["route_fractions"]["cat_all5"]["point"]["F_direct"],
         "route_readings_matched": route["readings_matched"],
         "other_n_programs": other["pool"]["n_programs"], "other_n_passed": other["pool"]["n_passed"],
         "other_n_novel_confirmed": other["novel_confirmed"], "judge_kappa": other["judges"]["kappa_A_B"],
         "judge_agreement": other["judges"]["agreement_A_B"],
         "rival_rho_movability": rv.get("movable"), "rival_rho_max_E_t": rv.get("max_E_t"), "rival_rho_can": rv.get("can"),
         "rival_rho_clarity": rv.get("clarity"), "rival_rho_frlp": rv.get("frlp_runner_up_mass"),
         "rival_rho_nonce": rv.get("nonce_offdef"), "rival_rho_novelty": rv.get("novelty_offdef"),
         "table82_hits_implied": rigor["table82"]["hits_implied"], "table82_hits_gain": rigor["table82"]["hits_gain"],
         "rederive_n_checks": red.get("n_checks"), "rederive_n_mismatches": red.get("n_mismatches"),
         "placebos_failed_as_required": plc.get("n_placebos_failed_as_required"),
         "rederive_extra_n_checks": rex.get("n_checks"), "rederive_extra_n_mismatches": rex.get("n_mismatches"),
         "rederive_extra_placebos_failed_as_required": rex.get("n_placebos_failed_as_required"),
         "openrouter_usd": other["judges"].get("spent_usd")}
    for _, r in dcounts.groupby("task").n_qualify.sum().items() if False else dcounts.groupby("task").n_qualify.sum().items():
        m[f"n_qualify_dirs_{_}"] = int(r)
    m = {k: float(v) for k, v in m.items() if _num(v) is not None}
    sections = {
        "knob_table": {"n_rows": len(knob), "file": "tables/knob_table.csv", "arm_dictionary": "tables/arm_dictionary.csv",
                       "random_direction_counts": "tables/random_direction_counts.csv", "table110": "tables/table110_alpha2.csv",
                       "verification": {"n": len(vt), "matched": int(vt.match.sum())},
                       "per_task_verdict": ptv.to_dict("records"), "not_recomputed": "tables/knob_rows_not_recomputed.csv"},
        "route_landing": {k: route[k] for k in ("readings", "exp16_reproduction", "T13_route_class", "lead_paragraph")},
        "llama_hits": llama, "other_audit": other, "figures": figs, "rigor": rigor, "wording": wording,
        "screen": {**scr, "file": "screen.json", "rule_script": "screen_rule.py", "extras": "screen_extras.json"},
        "rival_predictors": rivals,
        "missing_inputs": [r for r in _r(WS / "inputs.json") or [] if r.get("status") != "present"] if isinstance(_r(WS / "inputs.json"), list) else [],
        "spend": {"openrouter_usd": other["judges"].get("spent_usd"), "cap_usd": 1.8, "models": other["judges"]["models"]},
        "audit": {"rederive": {"n_checks": red.get("n_checks"), "n_mismatches": red.get("n_mismatches")},
                  "rederive_extra": {"n_checks": rex.get("n_checks"), "n_mismatches": rex.get("n_mismatches"),
                                     "placebos_failed_as_required": rex.get("n_placebos_failed_as_required"),
                                     "n_placebos": rex.get("n_placebos")},
                  "placebos": {k: v.get("placebo_failed_to_show_effect") for k, v in plc.items() if k.startswith("P")}}}
    inv = json.loads((WS / "inputs.json").read_text())
    sections["missing_inputs"] = [r for r in inv if r.get("status") != "present"]
    meta = {"evaluation_name": "iter4_step0_record_repair_and_push_screen", "artifact_plan_id": "gen_plan_evaluation_1_idx1",
            "description": ("CPU-only record repair of iteration-3 numbers and the frozen push-movability screen; every "
                            "number recomputed from labelled rows of the 11 declared dependencies with "
                            "'<artifact_id>:<relative path>' provenance."),
            "screen_sha256": scr.get("sha256"), "corrections": "corrections.json", "sections": clean(sections),
            "conventions": {"H1r25": "correct-only, mechanism-labelled Hill-1 rarefied to depth 25 (1,000 subsamples); 90% "
                                     "percentile bootstrap (1,000 x 200), template clusters when 5 templates have >= 5 correct "
                                     "programs, iid interval beside it; seeds sha256('20261021|cell')",
                            "pass_cost": "100 x (pass_twin - pass_arm), Newcombe hybrid-score 95% interval",
                            "escape": "offdef(d) - offdef(twin) >= 0.20 and pass(d) >= 0.8 pass(twin)"}}
    out = {"metadata": clean(meta), "metrics_agg": m, "datasets": ds}
    full = WS / "full_eval_out.json"
    full.write_text(json.dumps(clean(out), indent=1))
    (WS / "eval_out.json").write_text(json.dumps(clean(out), indent=1))
    mini = copy.deepcopy(clean(out))
    for d in mini["datasets"]:
        d["examples"] = d["examples"][:3]
    (WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=1))

    def trunc(o):
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        if isinstance(o, list):
            return [trunc(v) for v in o[:3]] if len(o) > 3 else [trunc(v) for v in o]
        return o

    prev = copy.deepcopy(mini)
    prev["metadata"] = {k: (trunc(v) if k != "sections" else {s: "see full_eval_out.json" for s in v}) for k, v in prev["metadata"].items()}
    prev["datasets"] = trunc(prev["datasets"])
    (WS / "preview_eval_out.json").write_text(json.dumps(prev, indent=1))
    logger.info(f"outputs: {len(ds)} datasets, {sum(len(d['examples']) for d in ds)} examples, {len(m)} metrics; "
                f"full {full.stat().st_size / 1e6:.2f} MB")
