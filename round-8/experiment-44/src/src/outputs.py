#!/usr/bin/env python3
"""Stage 9 outputs: data/samples.jsonl (every screen row, full text incl. reasoning) and method_out.json
(exp_gen_sol_out: datasets tp_screen, tp_geometry, tp_confirmation; metadata = every analysis, commits, deviations)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from common import (CANON_ORDER, CONFIGS, DATA, PRED, RESULTS, ROOT, STATES, read_json, read_jsonl, sha256_text,
                    write_json, write_jsonl)

ANALYSES = ["labeller_validation", "judge_gate", "renderer_checks", "smoke", "screen", "selection", "adjudication_ban",
            "geometry_M1", "geometry_M2", "landing", "landing_robustness", "confirmation", "quant_check",
            "circle_check", "novelty_audit", "positioning", "costs", "deviations", "carried_rows", "t8_synthetic",
            "rederive", "inputs_status", "openrouter_preflight", "checks", "executor_review", "states_C6_nf4",
            "states_C1_int8", "states_C1_nf4", "adjudication_confirm", "t7_embed_cpu_vs_gpu", "audit_headlines", "positioning"]


def _s(x: Any) -> str:
    return x if isinstance(x, str) else json.dumps(x, default=str)


def _rows(cid: str, arm: str) -> list[dict[str, Any]]:
    return read_jsonl(DATA / f"labelled_{cid}_{arm}.jsonl")


def build(max_output_chars: int = 6000) -> dict[str, Any]:
    import screen as scr

    c2 = read_json(PRED / "commit2.json")
    sel = read_json(RESULTS / "selection.json") if (RESULTS / "selection.json").exists() else {}
    geo = read_json(RESULTS / "geometry_M1.json") if (RESULTS / "geometry_M1.json").exists() else {}
    kp = geo.get("M1", {}).get("k_primary", 10)
    gk = geo.get("M1", {}).get(f"k{kp}", {})
    g = gk.get("g", {})
    edge_alg = min(g, key=g.get) if g else "n/a"
    samples, ex_screen, ex_conf = [], [], []
    for cid in CONFIGS:
        banned = c2["banned_sets"].get(cid, [])
        base = _rows(cid, "baseline")
        modal = max(set(r["adj_label"] for r in base), key=[r["adj_label"] for r in base].count) if base else "n/a"
        for arm in ("baseline", "ban", "confirm"):
            for r in _rows(cid, arm):
                nf = scr.name_free(r, banned) if r.get("adj_label") in banned else (None, None)
                cs = arm != "baseline" and scr.is_correct_survivor(r, banned)
                samples.append({k: r.get(k) for k in (
                    "uid", "config", "arm", "slot", "template", "segment", "prompt", "prompt_sha256", "model", "provider",
                    "quantization", "engine", "seed", "content", "reasoning", "finish_reason", "thinking_truncated",
                    "reasoning_tokens", "completion_tokens", "cost_usd", "code", "label_raw", "labeller_source",
                    "runtime_label", "ast_label", "adj_label", "adj_source", "adj_reason", "adj_other_name",
                    "judge_labels", "passed", "passed_exp2", "test_error", "utc")} |
                    {"thinking": CONFIGS[cid]["thinking"], "banned_set": banned if arm != "baseline" else [],
                     "name_free_code": nf[0], "name_free_all_text": nf[1], "correct_survivor": cs})
                ex = {"input": r.get("prompt") or "", "output": (r.get("content") or "")[:max_output_chars],
                      "metadata_config": cid, "metadata_model": CONFIGS[cid]["model"], "metadata_arm": arm,
                      "metadata_template": str(r.get("template")), "metadata_slot": r.get("slot"),
                      "metadata_provider": str(r.get("provider")), "metadata_quantization": CONFIGS[cid]["quantization"],
                      "metadata_thinking": CONFIGS[cid]["thinking"], "metadata_reasoning_tokens": r.get("reasoning_tokens"),
                      "metadata_finish_reason": r.get("finish_reason"),
                      "metadata_thinking_truncated": bool(r.get("thinking_truncated")),
                      "metadata_cost_usd": r.get("cost_usd"), "metadata_label_raw": r.get("label_raw"),
                      "metadata_adj_label": r.get("adj_label"), "metadata_adj_source": r.get("adj_source"),
                      "metadata_adj_other_name": r.get("adj_other_name"),
                      "metadata_judge_labels": _s(r.get("judge_labels")), "metadata_passed": bool(r.get("passed")),
                      "metadata_passed_exp2": bool(r.get("passed_exp2")),
                      "metadata_banned_set": ",".join(banned) if arm != "baseline" else "",
                      "metadata_correct_survivor": bool(cs), "metadata_name_free_code": nf[0],
                      "metadata_output_truncated": len(r.get("content") or "") > max_output_chars,
                      "predict_baseline_default": modal,
                      "predict_ban_landing_geometry": edge_alg if arm != "baseline" else modal,
                      "predict_labeller": str(r.get("adj_label"))}
                (ex_conf if arm == "confirm" else ex_screen).append(ex)
    write_jsonl(DATA / "samples.jsonl", samples)
    datasets = [{"dataset": "tp_screen", "examples": ex_screen}]
    if geo:
        import prompts_tp

        z = np.load(STATES / f"smean_{geo['tag']}.npz")
        F = z["kind"] == "forced"
        forced = prompts_tp.forced_set()
        pcs = geo.get("forced_pca2", [])
        cvp = geo["layer_curve"].get("cv_pred_at_L", [])
        ex_geo = []
        for i, it in enumerate(forced):
            a = it["algorithm"]
            cls = gk.get("classes", {}).get(a, "BANNED" if a in geo["banned"] else "n/a")
            ex_geo.append({"input": it["prompt"], "output": a, "metadata_algorithm": a,
                           "metadata_template": it["template"], "metadata_alias": it["alias"],
                           "metadata_group": it["group"], "metadata_layer": geo["L_star"],
                           "metadata_pc": pcs[i] if i < len(pcs) else None,
                           "metadata_landing_class": cls, "metadata_g": g.get(a),
                           "predict_cv_label_at_L": str(cvp[i]) if i < len(cvp) else "n/a",
                           "predict_landing_class": cls})
        datasets.append({"dataset": "tp_geometry", "examples": ex_geo})
    if ex_conf:
        datasets.append({"dataset": "tp_confirmation", "examples": ex_conf})
    meta: dict[str, Any] = {"method_name": "top-five ban screen + activation-manifold landing (iteration 8)",
                            "description": "Which open models obey a literal five-name ban on the T1 grid-path task, and "
                                           "where do correct survivors land on the 10-algorithm activation manifold "
                                           "of the selected (or descriptive) model.",
                            "commitments": (ROOT / "commitments.log").read_text().splitlines()}
    for name in ANALYSES:
        p = RESULTS / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name == "geometry_M1":
                d = {k: v for k, v in d.items() if k not in ("overlays",)}
            meta[name] = d
    for c in ("commit1", "commit2", "commit3", "commit4"):
        p = PRED / f"{c}.json"
        if p.exists():
            meta[c] = read_json(p) if c != "commit2" else {k: v for k, v in read_json(p).items() if k != "ban_prompts"}
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out, indent=None)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in datasets]}; samples {len(samples)}")
    return out
