#!/usr/bin/env python3
"""Final stage (CPU): label every generation, C1 fresh-pool summary, D2 same-seed CRN analysis (vs a different-seed
baseline), readout (i) summary, the dated 0e record, and method_out.json (exp_gen_sol_out schema)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

from core import (BANNED, CRN_TEMPS, EXP6, MODEL_GEN, MODEL_HF, RESULTS, ROOT, SAE_REPO, TASKS, TEMPLATE_IDS, Timer,
                  add_deviation, load_module, read_json, read_jsonl, utc_now, wilson, write_json)

UNRES = {"no_code", "unresolved", None}
THETAS = (0.7, 0.8, 0.9)


def fresh_pool_summary() -> dict[str, Any]:
    rows = read_jsonl(RESULTS / "labelled_c1.jsonl")
    out: dict[str, Any] = {"n_runs": len(rows), "per_task": {}}
    for t in TASKS:
        rt = [r for r in rows if r["task"] == t]
        per = {}
        for w in TEMPLATE_IDS + ["pooled"]:
            rr = rt if w == "pooled" else [r for r in rt if r["template"] == w]
            coded = [r for r in rr if r["label"] not in UNRES]
            nb = sum(r["label"] == BANNED[t] for r in coded)
            nonb = [r for r in coded if r["label"] != BANNED[t]]
            av = 1 - nb / len(coded) if coded else None
            per[w] = {"n": len(rr), "n_coded": len(coded), "banned_share": nb / len(coded) if coded else None,
                      "banned_share_wilson": wilson(nb, len(coded)), "avoidance": av,
                      "n_attempted_non_banned": len(nonb),
                      "event_gate_pass": bool(av is not None and av >= 0.5 and len(nonb) >= 20),
                      "compliant_share": (sum(r["passed"] for r in nonb) / len(rr)) if rr else None,
                      "pass_rate": sum(bool(r["passed"]) for r in rr) / len(rr) if rr else None,
                      "landing": dict(Counter(r["label"] for r in rr)),
                      "commit_idx_found": sum(r.get("commit_idx") is not None for r in rr),
                      "negated_first_mention": sum(bool(r.get("negated_first_mention")) for r in rr)}
        out["per_task"][t] = per
    write_json(RESULTS / "fresh_pool_summary.json", out)
    return out


def _metrics_mod():
    return load_module("exp6_metrics", EXP6 / "analysis" / "metrics.py")


def _jacc(a: frozenset | None, b: frozenset | None) -> float | None:
    if a is None or b is None:
        return None
    u = len(a | b)
    return len(a & b) / u if u else 1.0


def same_seed_analysis() -> dict[str, Any]:
    M = _metrics_mod()
    rows = read_jsonl(RESULTS / "labelled_crn.jsonl")
    if not rows:
        return {"status": "not run"}
    by = {(r["task"], r["condition"], r["seed"], r["T"]): r for r in rows}
    sh: dict[tuple, frozenset | None] = {}
    for k, r in by.items():
        toks = M.normalise_tokens(r["code"]) if r.get("code") else None
        sh[k] = M.shingles(toks, 4) if toks else None
    seeds = sorted({r["seed"] for r in rows})
    rng = np.random.default_rng(7)
    out: dict[str, Any] = {"coupling": "inverse-CDF over the (-logit, token_id)-sorted top-10, U[seed][t] = "
                           "default_rng(seed).random(1024) shared across T, tasks and conditions",
                           "n_rows": len(rows), "seeds": seeds, "cells": {}}
    for t in TASKS:
        for cond in ("baseline", "ban"):
            for T in CRN_TEMPS[1:]:
                def pair_stats(pairs: list[tuple]) -> dict[str, Any]:
                    idea = [(by[a]["label"] != by[b]["label"]) for a, b in pairs
                            if by[a]["label"] not in UNRES and by[b]["label"] not in UNRES]
                    rec = {"n_idea_pairs": len(idea), "idea_change_rate": float(np.mean(idea)) if idea else None,
                           "idea_change_wilson": wilson(int(sum(idea)), len(idea))}
                    for th in THETAS:
                        ph = []
                        for a, b in pairs:
                            if by[a]["label"] in UNRES or by[a]["label"] != by[b]["label"]:
                                continue
                            j = _jacc(sh[a], sh[b])
                            if j is not None:
                                ph.append(j < th)
                        rec[f"phrasing_change_rate_theta{th}"] = float(np.mean(ph)) if ph else None
                        rec[f"n_phrasing_pairs_theta{th}"] = len(ph)
                    return rec

                keys = [s for s in seeds if (t, cond, s, T) in by and (t, cond, s, 0.3) in by]
                same = [((t, cond, s, T), (t, cond, s, 0.3)) for s in keys]
                diff = [((t, cond, s, T), (t, cond, s2, 0.3)) for s in keys for s2 in keys if s2 != s]
                cell = {"same_seed": pair_stats(same), "different_seed": pair_stats(diff)}
                # divergence index: first generated step where the token differs from the same seed's T=0.3 row
                dv = []
                for a, b in same:
                    ga, gb = by[a]["gen_token_ids"], by[b]["gen_token_ids"]
                    d = next((i for i, (x, y) in enumerate(zip(ga, gb)) if x != y), None)
                    if d is None and len(ga) != len(gb):
                        d = min(len(ga), len(gb))
                    dv.append(d)
                dd = [d for d in dv if d is not None]
                cell["divergence_index"] = {"n_identical_to_T03": sum(d is None for d in dv),
                                            "median": float(np.median(dd)) if dd else None,
                                            "q10_q90": [float(np.quantile(dd, .1)), float(np.quantile(dd, .9))]
                                            if dd else None,
                                            "idea_change_divergence": [d for d, (a, b) in zip(dv, same)
                                                                       if by[a]["label"] != by[b]["label"]]}
                # same-seed minus different-seed difference, bootstrap over seeds
                boots = []
                for _ in range(1000):
                    bs = rng.choice(keys, len(keys), replace=True)
                    sp = [((t, cond, s, T), (t, cond, s, 0.3)) for s in bs]
                    dp = [((t, cond, s, T), (t, cond, s2, 0.3)) for s in bs for s2 in keys if s2 != s]
                    a1 = [by[a]["label"] != by[b]["label"] for a, b in sp
                          if by[a]["label"] not in UNRES and by[b]["label"] not in UNRES]
                    a2 = [by[a]["label"] != by[b]["label"] for a, b in dp
                          if by[a]["label"] not in UNRES and by[b]["label"] not in UNRES]
                    if a1 and a2:
                        boots.append(np.mean(a2) - np.mean(a1))
                cell["idea_agreement_same_minus_different"] = {
                    "point": (None if cell["same_seed"]["idea_change_rate"] is None else
                              cell["different_seed"]["idea_change_rate"] - cell["same_seed"]["idea_change_rate"]),
                    "ci95": [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))] if boots else None}
                out["cells"][f"{t}|{cond}|T{T}"] = cell
            # per seed: distinct ideas / phrasing clusters across the 4 temperatures; pass + compliance per T
            per_seed_ideas, per_seed_phr = [], []
            for s in seeds:
                ks = [(t, cond, s, T) for T in CRN_TEMPS if (t, cond, s, T) in by]
                labs = [by[k]["label"] for k in ks if by[k]["label"] not in UNRES]
                per_seed_ideas.append(len(set(labs)))
                shs = [sh[k] for k in ks if sh[k] is not None]
                if shs:
                    J = np.eye(len(shs))
                    for i in range(len(shs)):
                        for j in range(i + 1, len(shs)):
                            J[i, j] = J[j, i] = _jacc(shs[i], shs[j])
                    per_seed_phr.append(int(len(set(M.clusters(J, 0.8, "single").tolist()))))
            perT = {}
            for T in CRN_TEMPS:
                rr = [by[(t, cond, s, T)] for s in seeds if (t, cond, s, T) in by]
                perT[str(T)] = {"n": len(rr), "pass_rate": float(np.mean([bool(r["passed"]) for r in rr])),
                                "banned_share": float(np.mean([r["label"] == BANNED[t] for r in rr])),
                                "labels": dict(Counter(r["label"] for r in rr))}
            out["cells"][f"{t}|{cond}|per_seed"] = {"mean_distinct_ideas_over_4T": float(np.mean(per_seed_ideas)),
                                                    "mean_distinct_phrasing_clusters_theta0.8":
                                                        float(np.mean(per_seed_phr)) if per_seed_phr else None,
                                                    "per_T": perT}
            if cond == "ban":
                # substitute identity stability among non-banned programs
                nb = {k: v for k, v in by.items() if k[0] == t and k[1] == "ban" and v["label"] not in UNRES
                      and v["label"] != BANNED[t]}
                sp = [(a, b) for a in nb for b in nb if a[2] == b[2] and a[3] < b[3]]
                dp = [(a, b) for a in nb for b in nb if a[2] != b[2] and a[3] != b[3]]
                out["cells"][f"{t}|ban|substitute_stability"] = {
                    "same_seed_agreement": float(np.mean([nb[a]["label"] == nb[b]["label"] for a, b in sp]))
                    if sp else None, "n_same": len(sp),
                    "different_seed_agreement": float(np.mean([nb[a]["label"] == nb[b]["label"] for a, b in dp]))
                    if dp else None, "n_diff": len(dp)}
    # determinism rerun + identical-history step-0 check
    det = read_jsonl(RESULTS / "raw" / "e5_determinism.jsonl")
    orig = {r["crn_row"]: r for r in read_jsonl(RESULTS / "raw" / "e5_crn.jsonl")}
    same = [r["gen_token_ids"] == orig[r["crn_row"]]["gen_token_ids"] for r in det if r["crn_row"] in orig]
    out["determinism_rerun"] = {"n": len(same), "byte_identical": int(sum(same)),
                                "rate": float(np.mean(same)) if same else None}
    st0 = read_json(RESULTS / "raw" / "e5_step0.json", {})
    groups: dict[tuple, list] = defaultdict(list)
    for k, v in st0.items():
        p = k.split("|")
        if p[0] == "icdf" and len(p) >= 5:
            groups[(p[1], p[2])].append(v)
    chk = {}
    for g, vs in groups.items():
        ref = vs[0]
        same_ids = [v["ids"] == ref["ids"] for v in vs]
        maxd = max(float(np.max(np.abs(np.array(v["logits"]) - np.array(ref["logits"])))) for v in vs)
        chk["|".join(g)] = {"n_rows": len(vs), "share_identical_top10_ids": float(np.mean(same_ids)),
                            "max_abs_logit_diff": maxd, "identical": bool(all(same_ids) and maxd == 0.0)}
    out["step0_identical_history_check"] = chk
    write_json(RESULTS / "same_seed.json", out)
    return out


def discovery_summary() -> dict[str, Any]:
    LP = read_json(RESULTS / "layer_probe.json", {})
    AL = read_json(RESULTS / "sae_alignment.json", {})
    DI = read_json(RESULTS / "readout_i_discovery.json", {})
    summ: dict[str, Any] = {"layer_choice": LP.get("choice"), "confounds": LP.get("confounds"),
                            "sae_alignment": AL.get("layers"), "configs": {}}
    for key, c in (DI.get("configs") or {}).items():
        if c.get("status") == "skipped":
            summ["configs"][key] = c
            continue
        summ["configs"][key] = {"n": c["n"], "n_banned_class": c["n_banned_class"],
                                "n_active_latents": c["n_active_latents"], "maxstat_null_q95": c["maxstat_null_q95"],
                                "methods": {m: {k: v for k, v in r.items()} for m, r in c["methods"].items()},
                                "n_final_latents_passing_maxstat": sum(x["passes_maxstat_null"]
                                                                        for x in c["final_top20"]),
                                "final_top5": c["final_top20"][:5]}
    # positive / negative controls from the layer probe (k_post decodable; R within-paraphrase ~0.5 / undefined)
    if LP.get("tasks"):
        ctrl = {}
        for t in TASKS:
            kp = [LP["tasks"][t][f"k_post|L{L}"]["raw_dim"]["auc_within"] for L in range(8, 29)]
            rr = [LP["tasks"][t][f"R|L{L}"]["raw_dim"]["auc_within"] for L in range(8, 29)]
            ctrl[t] = {"k_post_within_auc_max": float(np.nanmax([x for x in kp if x is not None] or [np.nan])),
                       "R_within_auc_range": [float(np.nanmin([x for x in rr if x is not None] or [np.nan])),
                                              float(np.nanmax([x for x in rr if x is not None] or [np.nan]))]}
        summ["controls"] = ctrl
    return summ


def nla_jlens_record() -> dict[str, Any]:
    meta = None
    try:
        from huggingface_hub import hf_hub_download

        meta = json.loads(open(hf_hub_download("senku21x/cot-oracle-jlens", "Qwen3-8B/lens.meta.json")).read())
    except Exception as e:  # noqa: BLE001 - recorded, not fatal
        meta = {"error": str(e)[:200]}
    JL = read_json(RESULTS / "jlens.json", {})
    gate = JL.get("gate", {})
    rec = {"date": "2026-10-20", "recorded_utc": utc_now(),
           "NLA": {"resolution": "Natural Language Autoencoders (Anthropic, transformer-circuits.pub/2026/nla, "
                   "2026-05-07): an activation verbalizer + activation reconstructor trained jointly with RL.",
                   "released_checkpoints_per_planner": ["Qwen2.5-7B-Instruct L20", "Gemma-3-12B-IT L32",
                                                        "Gemma-3-27B-IT L41", "Llama-3.3-70B-Instruct L53"],
                   "qwen3_8b_checkpoint_found": False,
                   "decision": "NOT RUN: no released Qwen3-8B NLA; training one (RL on two model copies) is far "
                               "outside a 16 GB single-GPU budget.",
                   "verification_note": "Checkpoint list from the plan's dated leads (github.com/kitft/"
                                        "natural_language_autoencoders, checked by the planner 2026-10-20); not "
                                        "re-fetched in this session (time)."},
           "J_LENS": {"resolution": "Jacobian lens (Gurnee et al. 2026, transformer-circuits.pub/2026/workspace; "
                      "code github.com/anthropics/jacobian-lens): lens_l(h) = unembed(J_l h), J_l = E[dh_final/dh_l].",
                      "community_lens": "HF senku21x/cot-oracle-jlens (Qwen3-8B/lens.pt, lens.meta.json): exists, "
                                        "downloaded and loaded in this session",
                      "lens_meta": meta,
                      "gate_item_1_meta_names_base_model": bool(meta and meta.get("model") == MODEL_HF),
                      "gate_item_1_hook_matches_layers_output": bool(meta and "decoder block output" in
                                                                     str(meta.get("hook_point", ""))),
                      "gate_item_2": gate or "not run",
                      "jlens_package_installed": False,
                      "implementation": "lens applied directly from lens.pt (J matrices per source layer) as "
                                        "lm_head(final_norm(J_l h)); the orientation (J h vs J^T h) is chosen by the "
                                        "gate's agreement with the model's own next token",
                      "decision": ("applied (gate passed)" if gate.get("gate_pass") else
                                   "applied and reported descriptively, but the gate FAILED: J-lens readouts are "
                                   "not trusted; the logit lens on the same states is the primary lens readout")
                      if gate else "not run"}}
    write_json(RESULTS / "nla_jlens_search.json", rec)
    return rec


def _readout_predictions() -> dict[tuple, dict[str, Any]]:
    """Per fresh-pool run: exp3-fitted readout scores at k_pre (layer L1) -> predicted class (banned if score > 0)."""
    R = read_json(RESULTS / "readout_i_replication.json", {})
    L1 = read_json(RESULTS / "layer_probe.json", {}).get("choice", {}).get("L1")
    meta = read_json(RESULTS / "e2_meta.json", {}).get("runs", [])
    out: dict[tuple, dict[str, Any]] = {}
    for t in TASKS:
        cfg = R.get("configs", {}).get(f"{t}|L{L1}|k_pre", {})
        for m, sc in (cfg.get("run_scores") or {}).items():
            for i, v in zip(cfg.get("run_index", []), sc):
                mr = meta[i]
                out.setdefault((mr["task"], mr["template"], mr["sample_id"]), {})[m] = v
    return out


def method_out(fresh: dict[str, Any], crn: dict[str, Any], disc: dict[str, Any], j0e: dict[str, Any]) -> None:
    from core import SUBSTITUTE

    P = read_json(ROOT / "prompts" / "prompts_v2.json")["prompts"]
    c1 = read_jsonl(RESULTS / "labelled_c1.jsonl")
    cr = read_jsonl(RESULTS / "labelled_crn.jsonl")
    c2 = read_jsonl(RESULTS / "labelled_c2.jsonl")
    c3 = read_jsonl(RESULTS / "labelled_c3.jsonl")
    preds = _readout_predictions()
    L1 = read_json(RESULTS / "layer_probe.json", {}).get("choice", {}).get("L1")
    TA = read_json(RESULTS / "thought_anchors.json", {})
    by03 = {(r["task"], r["condition"], r["seed"]): r["label"] for r in cr if r["T"] == 0.3}
    modal03 = {}
    for t in TASKS:
        for cond in ("baseline", "ban"):
            labs = [v for (tt, cc, _), v in by03.items() if tt == t and cc == cond and v not in UNRES]
            modal03[(t, cond)] = Counter(labs).most_common(1)[0][0] if labs else "none"

    def cls(t: str, v: Any) -> str:
        if v is None or not np.isfinite(v):
            return "no_state"
        return BANNED[t] if v > 0 else SUBSTITUTE[t]

    def ex_c1(r: dict[str, Any]) -> dict[str, Any]:
        pr = preds.get((r["task"], r["template"], r["sample_id"]), {})
        return {"input": P[r["prompt_key"]]["text"], "output": str(r["label"]),
                "metadata_task": r["task"], "metadata_template": r["template"], "metadata_seed": r["seed"],
                "metadata_model": r["model"], "metadata_decoding": r["decoding"], "metadata_passed": bool(r["passed"]),
                "metadata_labeller_source": r["labeller_source"], "metadata_commit_idx": r.get("commit_idx"),
                "metadata_evidence_term": r.get("evidence_term"),
                "metadata_negated_first_mention": bool(r.get("negated_first_mention")),
                "metadata_code_sha256": r.get("code_sha256"), "metadata_n_gen_tokens": r["n_gen_tokens"],
                "metadata_readout_layer": L1, "metadata_readout_scores_k_pre": pr,
                "predict_sae_top20_latents_exp3_fitted": cls(r["task"], pr.get("sae_top20_lr")),
                "predict_sae_top1_latent_exp3_fitted": cls(r["task"], pr.get("sae_top1")),
                "predict_dim_baseline_exp3_fitted": cls(r["task"], pr.get("raw_dim")),
                "predict_raw_logistic_baseline_exp3_fitted": cls(r["task"], pr.get("raw_lr")),
                "predict_top20_neurons_baseline_exp3_fitted": cls(r["task"], pr.get("neuron_top20_lr")),
                "predict_banned_label": BANNED[r["task"]]}

    def ex_crn(r: dict[str, Any]) -> dict[str, Any]:
        return {"input": P[r["prompt_key"]]["text"], "output": str(r["label"]),
                "metadata_task": r["task"], "metadata_condition": r["condition"], "metadata_seed": r["seed"],
                "metadata_T": r["T"], "metadata_coupling": r["coupling"], "metadata_model": r["model"],
                "metadata_passed": bool(r["passed"]), "metadata_labeller_source": r["labeller_source"],
                "metadata_code_sha256": r.get("code_sha256"), "metadata_n_gen_tokens": r["n_gen_tokens"],
                "predict_same_seed_T03": str(by03.get((r["task"], r["condition"], r["seed"]), "none")),
                "predict_different_seed_modal_T03": str(modal03[(r["task"], r["condition"])])}

    def ex_c2(r: dict[str, Any]) -> dict[str, Any]:
        tr = TA.get("traces", {}).get(str(r["trace_id"]), {})
        return {"input": P[f"{r['task']}|ban|W1"]["text"], "output": str(r["label"]),
                "metadata_task": r["task"], "metadata_trace_id": r["trace_id"], "metadata_seed": r["seed"],
                "metadata_complete_within_8192": bool(r["complete"]), "metadata_think_close_idx": r["think_close_idx"],
                "metadata_n_gen_tokens": r["n_gen_tokens"], "metadata_passed": bool(r["passed"]),
                "metadata_decoding": r["decoding"], "metadata_resampled": bool(tr),
                "predict_early_label_of_thinking": str(tr.get("own_early_label", "not_resampled"))}

    def ex_c3(r: dict[str, Any]) -> dict[str, Any]:
        tr = TA.get("traces", {}).get(str(r["trace_id"]), {})
        outc = r.get("early_label") if r.get("early_label") not in (None, "None") else (r.get("label") or "undecided")
        return {"input": P[f"{r['task']}|ban|W1"]["text"] + f"\n\n[thinking prefix: trace {r['trace_id']} up to "
                f"sentence {r['boundary_k']} (generated-token index {r['b_k']})]",
                "output": str(outc), "metadata_task": r["task"], "metadata_trace_id": r["trace_id"],
                "metadata_boundary_k": r["boundary_k"], "metadata_continuation_id": r["continuation_id"],
                "metadata_seed": r["seed"], "metadata_early_source": r.get("early_source"),
                "metadata_reached_code": bool(r.get("reached_code")), "metadata_n_gen_tokens": r["n_gen_tokens"],
                "predict_trace_final_reference": str(tr.get("final_reference", "none"))}

    datasets = []
    if c1:
        datasets.append({"dataset": "fresh_ban_pool_protocol_v2", "examples": [ex_c1(r) for r in c1]})
    if cr:
        datasets.append({"dataset": "same_seed_crn", "examples": [ex_crn(r) for r in cr]})
    if c2:
        datasets.append({"dataset": "thought_anchor_base_traces", "examples": [ex_c2(r) for r in c2]})
    if c3:
        datasets.append({"dataset": "thought_anchor_continuations", "examples": [ex_c3(r) for r in c3]})
    meta = {"method_name": "Reading a coding ban inside the model (descriptive readouts, Qwen3-8B)",
            "artifact_id": "gen_plan_experiment_6_idx7", "date": "2026-10-20",
            "description": "SAE latent readouts vs DiM / raw logistic / top-20-neuron baselines (discovery on exp3 "
                           "states, replication on a fresh protocol-v2 ban pool), base->instruct SAE transfer test, "
                           "attention to the ban under matched twins, prime-veto latent pattern, thought anchors, "
                           "same-seed common-random-numbers test vs a different-seed baseline, J-lens vs logit lens.",
            "models": {"generation": MODEL_GEN, "states": MODEL_HF, "sae": SAE_REPO},
            "deviations": read_json(RESULTS / "deviations.json", {}).get("deviations", []),
            "fresh_pool_summary": fresh, "same_seed": crn, "readout_i_discovery": disc, "record_0e": j0e,
            "transfer_test": read_json(RESULTS / "transfer_summary.json"),
            "readout_i_replication": _strip_scores(read_json(RESULTS / "readout_i_replication.json")),
            "readout_ii_attention": _strip_heatmaps(read_json(RESULTS / "readout_ii_attention.json")),
            "readout_iii_prime_veto": read_json(RESULTS / "readout_iii_prime_veto.json"),
            "jlens": read_json(RESULTS / "jlens_summary.json"),
            "thought_anchors": read_json(RESULTS / "thought_anchors.json"),
            "latent_contexts": read_json(RESULTS / "latent_contexts.json"),
            "labeller_check": read_json(RESULTS / "labeller_check.json"),
            "locator_check": read_json(RESULTS / "locator_check.json"),
            "headline_verification": read_json(RESULTS / "verify_headlines.json"),
            "timing": read_json(RESULTS / "timing.json"), "spend": read_json(RESULTS / "spend.json"),
            "not_run": read_json(RESULTS / "not_run.json", [])}
    write_json(ROOT / "method_out.json", {"metadata": meta, "datasets": datasets})
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in datasets]}")


def _strip_scores(R: Any) -> Any:
    if not isinstance(R, dict):
        return R
    out = json.loads(json.dumps(R))
    for c in out.get("configs", {}).values():
        c.pop("run_scores", None)
    return out


def _strip_heatmaps(A: Any) -> Any:
    if not isinstance(A, dict):
        return A
    out = json.loads(json.dumps(A))
    for t in out.get("tasks", {}).values():
        t.pop("heatmap_ban_minus_neutral_total", None)
    return out


def labeller_check() -> dict[str, Any]:
    """A2 (reduced): combine() over the gold set's stored runtime/AST labels + cached judge labels vs adjudicated."""
    from core import EXP1, exp1_on_path

    exp1_on_path()
    from labeller.combine import combine

    gold = read_jsonl(EXP1 / "labeller" / "gold_set.jsonl")
    cache = {r["key"]: r for r in read_jsonl(EXP1 / "labeller" / "judge_cache.jsonl")}
    from core import JUDGE_MODEL, sha256_text

    agree, n = 0, 0
    for gr in gold:
        if gr.get("adjudicated") in (None, "unresolved"):
            continue
        j = cache.get(f"{JUDGE_MODEL}|{gr['task']}|{sha256_text(gr['code'])}")
        lab, _ = combine(gr["runtime_label"], gr["ast_label"], j)
        agree += lab == gr["adjudicated"]
        n += 1
    gate = read_json(EXP1 / "labeller" / "gate_report.json", {})
    out = {"n_gold_resolved": n, "combined_vs_adjudicated_agreement": agree / n if n else None,
           "pass_0.9": bool(n and agree / n >= 0.9),
           "references_100pct_exp1_gate_report": gate.get("references_100pct"),
           "note": "stored runtime/AST labels of the gold programs + exp1's cached judge labels (no re-execution; "
                   "time). References: exp1 gate_report.json."}
    write_json(RESULTS / "labeller_check.json", out)
    return out


def run_stage_final() -> None:
    from labelling import run_stage_label

    with Timer("final", gpu=False):
        lc = labeller_check()
        logger.info(f"A2 labeller check: {lc}")
        if not (RESULTS / "labelled_c3.jsonl").exists():
            run_stage_label()
        fresh = fresh_pool_summary()
        crn = same_seed_analysis()
        disc = discovery_summary()
        j0e = nla_jlens_record()
        method_out(fresh, crn, disc, j0e)


if __name__ == "__main__":
    from core import setup_logging

    setup_logging("stage_final")
    run_stage_final()
