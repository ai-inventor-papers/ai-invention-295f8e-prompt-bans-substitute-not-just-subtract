#!/usr/bin/env python3
"""S12 outputs: data/samples.jsonl (shared analysis schema, one row per sample) and method_out.json
(exp_gen_sol_out: datasets novr_samples / novr_cells / novr_instrument [/ novr_p3_candidates], metadata = every
analysis, verdict, commit, cost and engine tag, plus the deviations)."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from loguru import logger

import analysis
from common import DATA, PRED, RESULTS, ROOT, read_json, read_jsonl, setup_logging, verify_chain, write_json

ENGINES = {"q8": "vLLM0.11/Qwen3-8B-FP8/W8A16-Marlin (local, thinking off)",
           "q14": "OpenRouter qwen/qwen3-14b, DeepInfra fp8 pinned (thinking on)",
           "q32": "OpenRouter qwen/qwen3-32b, DeepInfra fp8 pinned (thinking on)"}


def _rj(name: str) -> Any:
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def banned_for_row(r: dict[str, Any], orders: dict[str, Any]) -> list[str]:
    o = orders.get(r["model"])
    if not o:
        return []
    c = r["cell"]
    return analysis.banned_for(c if c.startswith(("NAME_", "DESC_")) else "HOLD_5", o)


def sample_row(r: dict[str, Any], orders: dict[str, Any]) -> dict[str, Any]:
    B = banned_for_row(r, orders)
    valid = bool(r.get("valid"))
    return {"row_id": r["row_id"], "model": r["model"], "model_id": r.get("model_id"), "engine": r.get("engine"),
            "provider": r.get("provider"), "task": "online_bin_packing", "cell": r["cell"],
            "condition": r.get("condition"), "k": r.get("k"), "template": r.get("template"), "slot": r.get("slot"),
            "seed": r.get("seed"), "banned": B, "label": analysis.row_class(r), "stochastic": r.get("stochastic"),
            "A": r.get("A"), "A_informative": r.get("A_inf"), "rf_match": r.get("rf_match"),
            "max_agree_banned": analysis.max_agree_banned(r, B) if (B and valid and r.get("A")) else None,
            "L1": analysis.lex(r, B, "L1") if valid else None, "L2": analysis.lex(r, B, "L2") if valid else None,
            "L_text": analysis.lex(r, B, "L_text"), "L_reason": analysis.lex(r, B, "L_reason"),
            "mech_compliant": analysis.mech(r, B) if valid else None,
            "hits_program": r.get("hits_program"), "hits_text": r.get("hits_text"), "hits_reason": r.get("hits_reason"),
            "synonyms": r.get("synonyms"), "syn_category": r.get("syn_category"),
            "claims_novelty": r.get("claims_novelty"), "self_id_rules": r.get("self_id_rules"),
            "passed": valid, "error_type": r.get("error_type"), "error_msg": (r.get("error_msg") or "")[:200],
            "probe_err_share": r.get("probe_err_share"), "valid_full": r.get("valid_full"),
            "quality": r.get("quality"), "F": r.get("F"), "F_parts": r.get("F_parts"),
            "h_or3_excess": r.get("h_or3_excess"), "h_fsw5k_excess": r.get("h_fsw5k_excess"),
            "better_heldout": analysis.better(r), "novel": analysis.novel(r),
            "novel_max_agree": r.get("corpus_max_agree"), "nearest_corpus": r.get("corpus_nearest"),
            "corpus_top3": r.get("corpus_top3"), "truncated": r.get("truncated"),
            "finish_reason": r.get("finish_reason"), "prompt_tokens": r.get("prompt_tokens"),
            "completion_tokens": r.get("completion_tokens"), "reasoning_tokens": r.get("reasoning_tokens"),
            "cost_usd": r.get("cost_usd"), "gen_seconds": r.get("gen_seconds"), "code_sha256": r.get("code_sha256"),
            "extract_how": r.get("extract_how"), "code": r.get("code")}


def tri(x: Any) -> str:
    return "n/a" if x is None else ("true" if x else "false")


def run_all() -> dict[str, Any]:
    setup_logging("outputs")
    rows = sorted(analysis.load_rows(), key=lambda r: (r["model"], r["cell"], int(r["slot"])))
    orders = analysis.load_orders()
    samples = [sample_row(r, orders) for r in rows]
    with (DATA / "samples.jsonl").open("w") as fh:
        for s in samples:
            fh.write(json.dumps(s, default=str) + "\n")
    # ---------------------------------------------------------------- datasets
    ex_samples = []
    for s in samples:
        cond = s["condition"] or "(no condition segment: BASE)"
        ex = {"input": f"[{s['model']} | {s['cell']}] {cond}",
              "output": s["code"] or "(no priority function extracted)",
              "predict_mechanism_class": s["label"],
              "predict_lexical_L1": "n/a" if s["L1"] is None else ("compliant" if s["L1"] else "violates"),
              "predict_mechanistic_compliance": "n/a" if s["mech_compliant"] is None else
              ("compliant" if s["mech_compliant"] else "non_compliant"),
              "predict_valid": tri(s["passed"]), "predict_better_heldout": tri(s["better_heldout"]),
              "predict_novel": tri(s["novel"])}
        for k in ("model", "cell", "k", "template", "slot", "seed", "banned", "A", "max_agree_banned", "stochastic",
                  "rf_match", "novel_max_agree", "nearest_corpus", "h_or3_excess", "h_fsw5k_excess", "F", "quality",
                  "valid_full", "synonyms", "hits_program", "hits_reason", "truncated", "finish_reason",
                  "reasoning_tokens", "completion_tokens", "cost_usd", "engine", "provider", "code_sha256",
                  "error_type", "claims_novelty"):
            ex[f"metadata_{k}"] = s[k]
        ex_samples.append(ex)
    cells = _rj("cells.json") or {}
    ex_cells = []
    for key, c in sorted(cells.items()):
        m, cell = key.split("|")
        summ = {"N": c["N"], "VALID": c["VALID"], "truncated": c["truncated"], "banned": c["banned"],
                "L1_valid": c["L1_valid"], "mech_valid": c["mech_valid"], "lex_all": c["lex_all"],
                "mech_all": c["mech_all"], "gap_valid": c["gap_valid"], "paired_cells_abcd": c["paired_cells_abcd"],
                "class_composition": c["class_composition"], "underpowered": c["underpowered"]}
        ex_cells.append({"input": f"{m} | {cell} | banned {c['banned']}", "output": json.dumps(summ, default=str),
                         "predict_lexical_L1_rate": str(c["L1_valid"]["rate"]),
                         "predict_mechanistic_rate": str(c["mech_valid"]["rate"]),
                         "metadata_model": m, "metadata_cell": cell, "metadata_per_template": c.get("per_template"),
                         "metadata_max_agree_banned_hist": c.get("max_agree_banned_hist"),
                         "metadata_quality_among_mech_compliant": c.get("quality_among_mech_compliant")})
    gate = _rj("instrument_gate.json") or {}
    ex_instr = []
    for part, block in [("a_self_agreement", gate.get("a_self_agreement", {})),
                        ("b_renamed", gate.get("b_renamed", {})), ("c_variants", gate.get("c_variants", {})),
                        ("d_planted_different", gate.get("d_planted_different", {})),
                        ("e_rf_matcher", gate.get("e_rf_matcher", {}))]:
        for name, v in block.items():
            ex_instr.append({"input": f"instrument gate {part}: {name}", "output": json.dumps(v, default=str)[:4000],
                             "predict_class": str(v.get("class", v.get("match", v.get("identical_across_runs", "n/a"))))
                             if isinstance(v, dict) else str(v), "metadata_part": part})
    for pair, a in (gate.get("d_catalogue_pairs") or {}).items():
        ex_instr.append({"input": f"instrument gate d_catalogue_pairs: {pair}", "output": str(a),
                         "predict_below_threshold": tri(a < 0.95), "metadata_part": "d_catalogue_pairs"})
    datasets = [{"dataset": "novr_samples", "examples": ex_samples},
                {"dataset": "novr_cells", "examples": ex_cells},
                {"dataset": "novr_instrument", "examples": ex_instr}]
    p3a = _rj("p3_audit.json") or {}
    if p3a.get("candidates"):
        datasets.append({"dataset": "novr_p3_candidates", "examples": [
            {"input": c["row_id"], "output": c.get("code") or "", "predict_novel_confirmed": tri(c.get("novel_confirmed")),
             "metadata_corpus_top3": c.get("corpus_top3"), "metadata_judges": c.get("judges")}
            for c in p3a["candidates"]]})
    # ---------------------------------------------------------------- metadata
    ok, problems, entries = verify_chain()
    commits = {}
    for e in entries:
        p = ROOT / e["payload_path"]
        commits[e["label"]] = {**e, "payload_on_disk_matches": p.exists() and
                               __import__("hashlib").sha256(p.read_bytes()).hexdigest() == e["payload_sha256"]}
    costs = _rj("costs.json") or {}
    raw_cost = 0.0
    for f in sorted(DATA.glob("*raw*.jsonl")):
        raw_cost += sum(float(r.get("cost_usd") or 0.0) for r in read_jsonl(f))
    meta = {
        "method_name": "NOV-R: lexical vs mechanistic compliance with banned online-bin-packing rules (Qwen3)",
        "description": __doc__,
        "plan_id": "gen_plan_experiment_4_idx4",
        "engines": ENGINES,
        "n_samples": len(samples), "n_by_model": dict(Counter(s["model"] for s in samples)),
        "verdicts": {"P1": (_rj("p1.json") or {}).get("verdict"), "P2": (_rj("p2.json") or {}).get("verdict"),
                     "P3": (_rj("p3.json") or {}).get("verdict")},
        "p1": _rj("p1.json"), "p2": _rj("p2.json"), "p3": _rj("p3.json"), "p3_audit": p3a,
        "rename_table": _rj("rename_table.json"), "reasoning": _rj("reasoning.json"),
        "sensitivities": _rj("sensitivities.json"),
        "harness_gate": _rj("harness_gate_v10.json"),
        "instrument_gate_summary": {k: v for k, v in gate.items() if k not in ("reference_vectors",)},
        "probes": _rj("probes.json"),
        "corpus_summary": {k: v for k, v in (_rj("corpus.json") or {}).items() if k != "members"},
        "naming_checks": {m: _rj(f"naming_checks_{m}.json") for m in ("q8", "q14", "q32")},
        "naming_checks_clean_rerun": {m: _rj(f"naming_checks_{m}_clean.json") for m in ("q14", "q32")},
        "orders": {m: {k: o.get(k) for k in ("order", "counts", "other", "n_valid_base", "n_base", "B", "S_desc",
                                             "desc_text")} for m, o in orders.items()},
        "commit3": {m: read_json(PRED / f"commit3_{m}.json") for m in ("q14", "q32")
                    if (PRED / f"commit3_{m}.json").exists()},
        "commits": commits, "hash_chain_ok": ok, "hash_chain_problems": problems,
        "costs_ledger": costs, "cost_from_raw_rows_usd": raw_cost,
        "deviations": _rj("deviations.json"), "figures": _rj("figures.json"),
        "positioning": _rj("positioning.json"), "rederive_summary": {
            k: v for k, v in (_rj("rederive.json") or {}).items()
            if k in ("n_mismatches_total", "mismatches", "verdicts_rederived", "placebos", "hash_chain",
                     "placebos_all_fail_as_required")},
        "tests": _rj("tests.json"),
    }
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out, indent=None)
    logger.info(f"method_out.json: {len(ex_samples)} samples, {len(ex_cells)} cells, {len(ex_instr)} gate rows")
    return {"n_samples": len(ex_samples), "n_cells": len(ex_cells), "n_instr": len(ex_instr)}
