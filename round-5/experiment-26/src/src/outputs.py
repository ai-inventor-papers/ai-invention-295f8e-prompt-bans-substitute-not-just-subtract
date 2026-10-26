#!/usr/bin/env python3
"""Final outputs (plan section 13), run after analysis/a1a2.py and analysis/variants.py:
- pooled_inputs.json   one record per unit (schema iter5_panel_v1, validated against predictions/pooled_inputs_schema.json)
- data/samples.jsonl   one row per program (labels joined to sampling metadata; raw text + token ids stay in
                       data/samples_raw.jsonl)
- method_out.json      exp_gen_sol_out: datasets panelB_units (one example per unit) and panelB_cells (one example per
                       (unit, arm, cell))
- results/costs.json, results/timing_summary.json, results/deviations.json, results/label_audit.json,
  results/realised_displacement.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import units_extra  # noqa: E402,F401
from cfg5 import (COSTS, DATA_DIR, DEVIATIONS, LABELS, PRECISION, PRED_DIR, RAW, REALISED, RESULTS_DIR, ROOT,  # noqa: E402
                  TIMING, UNITS_DIR, read_json, read_jsonl, setup_logging, sha256_file, utc_now, write_json,
                  write_jsonl)
from commit5 import entries  # noqa: E402
from labels_view import final_rows  # noqa: E402
from units_spec import UNITS, spec_text  # noqa: E402

SCHEMA_PATH = PRED_DIR / "pooled_inputs_schema.json"

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#", "title": "iter5 pooled inputs (panel A/B)", "type": "object",
    "required": ["schema_version", "panel", "generated_utc", "records"],
    "properties": {
        "schema_version": {"const": "iter5_panel_v1"}, "panel": {"enum": ["A", "B"]},
        "generated_utc": {"type": "string"},
        "records": {"type": "array", "items": {
            "type": "object",
            "required": ["schema_version", "panel", "unit_id", "unit_kind", "parent_id", "cluster_id", "source_ids",
                         "unit_facts", "twin", "base", "rivals", "forecasts", "commit", "outcomes", "audit_engine"],
            "properties": {
                "schema_version": {"const": "iter5_panel_v1"}, "panel": {"enum": ["A", "B"]},
                "unit_id": {"type": "string"},
                "unit_kind": {"enum": ["new_task", "disguised_variant", "parent_remeasure"]},
                "parent_id": {"type": ["string", "null"]}, "cluster_id": {"type": "string"},
                "source_ids": {"type": "array", "items": {"type": "string"}},
                "unit_facts": {"type": "object", "required": ["K_u", "excluded_by_limit", "catalogue_sha256",
                                                              "default"]},
                "twin": {"type": "object", "required": ["correct_composition", "attempted_composition", "pass"]},
                "base": {"type": "object", "required": ["beta_u", "beta_attempt", "beta_plain", "r_u",
                                                        "correct_composition", "n_correct_base", "hill1",
                                                        "goods_coverage", "P_beta_ge_0.05", "P_beta_ge_0.2"]},
                "rivals": {"type": "object", "required": ["R_margin", "R_merit_runtime", "R_merit_length", "R_modal",
                                                          "R_novel"]},
                "forecasts": {"type": "object"},
                "commit": {"type": "object", "required": ["sha256", "utc", "chain_index"]},
                "outcomes": {"type": "object", "required": ["E_alpha1", "E_alpha2", "E_u", "per_direction",
                                                            "push_landing_composition", "pn_cells", "t13_cell"]},
                "audit_engine": {"type": "object", "required": ["engine", "precision", "unit_scale"]},
            }}},
    },
}


def unit_kind(u: str) -> str:
    return "parent_remeasure" if u.startswith("P_") else ("disguised_variant" if u.startswith("V_") else "new_task")


def realised_summary() -> dict[str, Any]:
    by: dict[tuple, list] = defaultdict(list)
    for r in read_jsonl(REALISED):
        a = "PN" if r["arm"].startswith("PN") else "ESC"
        alpha = float(r["arm"].split("_a")[-1]) if "_a" in r["arm"] else None
        by[(r["unit"], a, alpha)].append(r)
    out = {}
    for (u, a, alpha), rr in by.items():
        out.setdefault(u, {})[f"{a}_a{alpha}"] = {
            "n_prefills": len(rr), "rel_err_max_median": float(np.median([x["rel_err_max"] for x in rr])),
            "rel_err_max_max": float(np.max([x["rel_err_max"] for x in rr])),
            "disp_R_norm_block23_mean": float(np.mean([x["disp_R_norm"]["23"] for x in rr])),
            "disp_R_norm_block35_mean": float(np.mean([x["disp_R_norm"]["35"] for x in rr])),
            "target_mean": float(np.mean([x["target_mean"] for x in rr]))}
    return out


def pooled(outcomes: dict[str, Any], novelty: dict[str, Any], realised: dict[str, Any]) -> dict[str, Any]:
    chain = {e["path"]: e for e in entries()}
    recs = []
    for p in sorted((PRED_DIR / "units").glob("*.json")):
        u = p.stem
        pr = read_json(p)
        o = outcomes.get(u, {})
        e = chain.get(f"predictions/units/{u}.json", {})
        b = pr["base"]
        cat_p = UNITS_DIR / u / "catalogue_frozen.json"
        nov = {k: v for k, v in (novelty.get("by_unit_family") or {}).items() if k.split("|")[0] == u}
        recs.append({
            "schema_version": "iter5_panel_v1", "panel": "B", "unit_id": u, "unit_kind": unit_kind(u),
            "parent_id": units_extra.parent_of(u), "cluster_id": units_extra.parent_of(u) or u,
            "source_ids": list(UNITS[u].get("source_ids", [])),
            "unit_facts": {"K_u": pr["K_u"], "excluded_by_limit": pr.get("excluded_by_limit", []),
                           "catalogue_sha256": sha256_file(cat_p) if cat_p.exists() else None,
                           "catalogue": pr["catalogue"], "default": pr["default"], "flags": pr["flags"]},
            "twin": {"correct_composition": pr["twin"]["correct_composition"],
                     "attempted_composition": pr["twin"]["attempted_composition"], "pass": pr["twin"]["pass"],
                     "n": pr["twin"]["n"]},
            "base": {"beta_u": b["beta_u"], "beta_attempt": b["beta_attempt"], "beta_plain": b.get("beta_plain"),
                     "beta_correct": b.get("beta_correct"), "beta_source": b.get("beta_source"), "r_u": b["r_u"],
                     "r_u_ties": b.get("r_u_ties"), "correct_composition": b["correct_composition"],
                     "attempted_composition": b["attempted_composition"], "n_correct_base": b["n_correct"],
                     "n_base": b["n"], "hill1": b.get("hill1_rarefied"), "goods_coverage": b.get("goods_coverage"),
                     "P_beta_ge_0.05": b.get("P_beta_ge_0.05"), "P_beta_ge_0.2": b.get("P_beta_ge_0.2")},
            "rivals": {k: pr["rivals"].get(k) for k in ("R_margin", "R_merit_runtime", "R_merit_length", "R_modal",
                                                        "R_novel", "R_novel_correct", "K_u")},
            "forecasts": {k: v for k, v in pr.get("forecasts", {}).items() if k in ("BASE", "ASSOC", "PROX")},
            "predicted_class": pr["predicted_class"], "predicted_landing": pr["predicted_landing"],
            "commit": {"sha256": e.get("sha256"), "utc": e.get("utc"), "chain_index": e.get("index"),
                       "chain": e.get("chain")},
            "outcomes": {"E_alpha1": o.get("E_by_alpha", {}).get("1.0"), "E_alpha2": o.get("E_by_alpha", {}).get("2.0"),
                         "E_u": o.get("E_u"), "movable": o.get("movable"), "per_direction": o.get("per_direction", []),
                         "push_landing": o.get("push_landing"),
                         "push_landing_composition": o.get("push_landing_composition", {}),
                         "pn_cells": o.get("pn_cells", {}), "PN_excess_u": o.get("PN_excess_u"),
                         "t13_cell": o.get("t13_cell"), "twin_cell": o.get("twin_cell"),
                         "repertoire": o.get("repertoire")},
            "audit_engine": {"novelty_audit_counts": nov, "engine": "bf16_hf", "precision": PRECISION,
                             "gpu": "NVIDIA GeForce RTX 4090", "unit_scale": "ban_free_rQ_plain",
                             "realised_displacement": realised.get(u),
                             "base_label_audit_agreement": (pr.get("base_label_audit") or {}).get("agreement")}})
    return {"schema_version": "iter5_panel_v1", "panel": "B", "generated_utc": utc_now(), "records": recs}


def samples_jsonl() -> int:
    raw = {f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}": r for r in read_jsonl(RAW)
           if not r.get("engine_check")}
    real = {}
    for r in read_jsonl(REALISED):
        k = (r["unit"], r["template"], r["arm"], r.get("slot"))
        real[k] = {"rel_err_max": r["rel_err_max"], "disp_R_norm_35": r["disp_R_norm"]["35"],
                   "disp_R_norm_23": r["disp_R_norm"]["23"]}
    fin = {}
    for u in sorted({r["unit"] for r in raw.values()}):
        if u in UNITS:
            for f in final_rows(u):
                fin[f["key"]] = f
    labs = {l["key"]: l for l in read_jsonl(LABELS)}
    rows = []
    for k, r in raw.items():
        l = labs.get(k, {})
        f = fin.get(k, {})
        rd = real.get((r["unit"], r["template"], r["arm"], r["slot"])) or real.get((r["unit"], r["template"], r["arm"],
                                                                                     None))
        rows.append({"key": k, "model": r["model"], "model_tag": r["model_tag"], "unit": r["unit"],
                     "unit_kind": unit_kind(r["unit"]), "arm": r["arm"], "family": r["family"], "site": r.get("site"),
                     "lambda": None, "alpha": r.get("alpha"), "direction_seed": r.get("direction_seed"),
                     "template": r["template"], "slot": r["slot"], "temperature": r["temperature"],
                     "top_k": r.get("top_k"), "thinking": r.get("thinking"), "precision": r.get("precision"),
                     "prompt_sha256": r["prompt_sha256"], "stage": r.get("stage"),
                     "label": f.get("label") if f else (l.get("assoc_mapped_all") if r["family"] == "ASSOC" else None),
                     "labeller_source": f.get("label_source") if f else l.get("labeller_source"),
                     "runtime_label": l.get("runtime_label"), "ast_label": l.get("ast_label"),
                     "passed": l.get("passed"), "valid": l.get("valid"), "finish_reason": r.get("finish_reason"),
                     "n_new_tokens": r.get("n_tokens"), "realised_disp": rd, "code_sha256": l.get("code_sha256"),
                     "code": l.get("code") if r["family"] != "ASSOC" else None,
                     "assoc_answer": l.get("assoc_answer") if r["family"] == "ASSOC" else None, "utc": r["utc"]})
    write_jsonl(DATA_DIR / "samples.jsonl", rows)
    return len(rows)


def method_out(outcomes: dict[str, Any], a1: dict[str, Any], a2: dict[str, Any], variants: dict[str, Any]) -> dict:
    ex_units, ex_cells = [], []
    for p in sorted((PRED_DIR / "units").glob("*.json")):
        u = p.stem
        pr = read_json(p)
        o = outcomes.get(u, {})
        fc = pr.get("forecasts", {})

        def top(dist):
            if not dist:
                return "undefined"
            return max(((k, v) for k, v in dist.items() if k != "other"), key=lambda kv: kv[1])[0]
        spec = spec_text(u) if not u[:2] in ("P_", "V_") else (UNITS[u]["description"])
        ex_units.append({
            "input": spec, "output": str(pr["default"]),
            "predict_movable_base": str(pr["predicted_class"]),
            "predict_landing_base": str(pr["predicted_landing"]),
            "predict_landing_assoc": top(fc.get("ASSOC")), "predict_landing_prox": top(fc.get("PROX")),
            "metadata_unit": u, "metadata_unit_id": pr["unit_id"], "metadata_unit_kind": unit_kind(u),
            "metadata_parent_id": units_extra.parent_of(u), "metadata_catalogue": pr["catalogue"],
            "metadata_K_u": pr["K_u"], "metadata_flags": pr["flags"], "metadata_beta_u": pr["base"]["beta_u"],
            "metadata_beta_attempt": pr["base"]["beta_attempt"], "metadata_beta_plain": pr["base"].get("beta_plain"),
            "metadata_r_u": pr["base"]["r_u"], "metadata_base_correct_composition": pr["base"]["correct_composition"],
            "metadata_n_correct_base": pr["base"]["n_correct"], "metadata_hill1": pr["base"].get("hill1_rarefied"),
            "metadata_goods_coverage": pr["base"].get("goods_coverage"),
            "metadata_P_beta_ge_0_05": pr["base"].get("P_beta_ge_0.05"),
            "metadata_twin_correct_composition": pr["twin"]["correct_composition"],
            "metadata_twin_pass": pr["twin"]["pass"], "metadata_rivals": pr["rivals"], "metadata_forecasts": fc,
            "metadata_E_alpha1": o.get("E_by_alpha", {}).get("1.0"),
            "metadata_E_alpha2": o.get("E_by_alpha", {}).get("2.0"), "metadata_E_u": o.get("E_u"),
            "metadata_movable_observed": o.get("movable"), "metadata_push_landing": o.get("push_landing"),
            "metadata_push_landing_composition": o.get("push_landing_composition"),
            "metadata_PN_excess_u": o.get("PN_excess_u"), "metadata_pn_cells": o.get("pn_cells"),
            "metadata_t13_cell": o.get("t13_cell"), "metadata_repertoire": o.get("repertoire"),
            "metadata_per_direction": o.get("per_direction")})
        for c in o.get("per_direction", []):
            ex_cells.append({"input": f"unit={u} arm={c['arm']} (isotropic push, seed {c['seed']}, alpha {c['alpha']}, "
                                      f"task-spec positions, blocks 12-23, prefill only)",
                             "output": f"stage1_share={c['stage1_share']} stage1_pass={c['stage1_pass']} "
                                       f"confirmed={c['confirmed']}",
                             "predict_escape_base": str(pr["predicted_class"] == "MOVABLE"),
                             "metadata_unit": u, "metadata_cell": c})
        for name, cell in [("TWIN", o.get("twin_cell")), ("T13", o.get("t13_cell"))] + \
                [(f"PN_a{a}", v) for a, v in (o.get("pn_cells") or {}).items()]:
            if cell:
                ex_cells.append({"input": f"unit={u} arm={name}", "output": json.dumps(cell.get("labels_correct", {})),
                                 "metadata_unit": u, "metadata_cell": cell})
    md = {"method_name": "base-model repertoire (beta_u, r_u) as a ban-free predictor of push movability (panel B)",
          "description": "Qwen3-8B (instruct) vs Qwen3-8B-Base on 7 new coding units + 8 disguised-variant/parent "
                         "pairs; isotropic random pushes (8 directions x alpha 1, 2) at task-spec positions, blocks "
                         "12-23; predictions hash-committed before outcomes.",
          "A1": a1.get("primary"), "A1_secondary_PN": a1.get("secondary_PN"), "A2_top1": a2.get("top1"),
          "A2_paired_log_score": a2.get("paired_log_score"), "rivals": a1.get("rivals"),
          "sensitivities": a1.get("sensitivities"), "placebo": a1.get("placebo_shuffled_beta"),
          "table_2x3": a1.get("table_2x3"), "variants": {k: v for k, v in variants.items() if k != "pairs"},
          "baselines": "rival predictors R_modal, R_margin, R_merit (runtime, length), R_novel, K_u for A1; ASSOC "
                       "and PROX forecasts for A2"}
    return {"metadata": md, "datasets": [{"dataset": "panelB_units", "examples": ex_units},
                                         {"dataset": "panelB_cells", "examples": ex_cells}]}


def main() -> None:
    setup_logging("outputs")
    uo = read_json(RESULTS_DIR / "unit_outcomes.json")
    outcomes = {x["unit"]: x for x in uo["units"]}
    if (RESULTS_DIR / "unit_outcomes_extra.json").exists():
        outcomes.update({x["unit"]: x for x in read_json(RESULTS_DIR / "unit_outcomes_extra.json")["units"]})
    a1 = read_json(RESULTS_DIR / "a1_panel.json")
    a2 = read_json(RESULTS_DIR / "a2_panel.json")
    variants = read_json(RESULTS_DIR / "variants.json") if (RESULTS_DIR / "variants.json").exists() else {}
    novelty = read_json(RESULTS_DIR / "novelty_audit.json") if (RESULTS_DIR / "novelty_audit.json").exists() else {}
    realised = realised_summary()
    write_json(RESULTS_DIR / "realised_displacement.json", realised)
    P = pooled(outcomes, novelty, realised)
    import jsonschema
    write_json(SCHEMA_PATH, SCHEMA)
    jsonschema.validate(P, SCHEMA)
    write_json(ROOT / "pooled_inputs.json", P)
    logger.info(f"pooled_inputs.json: {len(P['records'])} records, schema-valid")
    n = samples_jsonl()
    logger.info(f"data/samples.jsonl: {n} rows")
    mo = method_out(outcomes, a1, a2, variants)
    write_json(ROOT / "method_out.json", mo)
    logger.info(f"method_out.json: {[len(d['examples']) for d in mo['datasets']]}")
    costs = read_jsonl(COSTS)
    by = Counter()
    for c in costs:
        by[c.get("purpose", "?").split(":")[0]] += float(c.get("cost") or 0)
    write_json(RESULTS_DIR / "costs.json", {"total_usd": sum(by.values()), "by_purpose": dict(by),
                                            "n_calls": len(costs), "cap_usd": 2.0})
    tm = read_jsonl(TIMING)
    st = defaultdict(lambda: {"batches": 0, "seconds": 0.0})
    for t in tm:
        s = st[(t["stage"], t["model_tag"])]
        s["batches"] += 1
        s["seconds"] += t["seconds"]
    write_json(RESULTS_DIR / "timing_summary.json",
               {"by_stage": {f"{k[0]}|{k[1]}": {**v, "programs": v["batches"] * 20,
                                                "programs_per_hour": v["batches"] * 20 / max(v["seconds"], 1) * 3600}
                             for k, v in st.items()},
                "total_gpu_seconds": sum(t["seconds"] for t in tm), "n_batches": len(tm)})
    write_json(RESULTS_DIR / "deviations.json", {"deviations": read_jsonl(DEVIATIONS)})
    la = {}
    for p in sorted(UNITS_DIR.glob("*/gate*.json")):
        g = read_json(p)
        la[f"{p.parent.name}/{p.name}"] = {k: v for k, v in g.items() if k not in ("items",)}
    for p in sorted((PRED_DIR / "units").glob("*.json")):
        pr = read_json(p)
        if pr.get("base_label_audit"):
            la[f"{p.stem}/base_label_audit"] = {k: v for k, v in pr["base_label_audit"].items() if k != "items"}
    write_json(RESULTS_DIR / "label_audit.json", la)


if __name__ == "__main__":
    main()
