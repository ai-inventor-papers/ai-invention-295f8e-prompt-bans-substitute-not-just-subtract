#!/usr/bin/env python3
"""Stage 7 outputs: data/samples.jsonl, pooled_inputs.json (schema iter5_panel_v1), results/units_gate.json,
results/unit_<u>_summary.json, results/timing_summary.json, results/timing_extrapolation.json, results/costs.json,
results/sensitivities.json (pre-specified sensitivities: plain-completion beta, beta_other; descriptive) and
method_out.json (exp_gen_sol_out). Reads only files written by the frozen analysis and the pipeline."""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import (ALPHAS, DATA, ESC_SEEDS, EXISTING, EXISTING_DEFAULT, ITER4_E, LAB_DIR, LOGS, MODELS, NEW_UNITS,  # noqa
                  PRED, RESERVE_UNITS, RESULTS, ROOT, UNIT_DIRS, read_json, read_jsonl, setup_logging, sha256_file,
                  unit_dir, utc_now, write_json, write_jsonl)
from metrics import perm_p_spearman, spearman  # noqa: E402

SAMPLE_FIELDS = ("model", "arm", "site", "lambda", "alpha", "direction_seed", "template", "slot", "temperature",
                 "top_k", "thinking", "precision", "prompt_sha256", "label", "labeller_source", "passed",
                 "finish_reason", "n_new_tokens", "realised_disp", "code_sha256", "code", "runtime_label",
                 "ast_label", "judge_label", "valid", "sample_id")


def unit_kind(t: str) -> str:
    if t in RESERVE_UNITS:
        return "new_reserve_extension"
    if t in UNIT_DIRS:
        return "new"
    return "existing"


def samples() -> int:
    rows = []
    for f in sorted(LAB_DIR.glob("*.jsonl")):
        for r in read_jsonl(f):
            o = {"unit": r["task"], "unit_kind": "engine_check" if f.stem.startswith("enginecheck") else
                 unit_kind(r["task"])}
            o.update({k: r.get(k) for k in SAMPLE_FIELDS})
            if o["precision"] is None:
                o["precision"] = "bf16"
            if o["site"] is None and o["alpha"] is not None:
                o["site"] = "spec_b12_23"
            rows.append(o)
    write_jsonl(DATA / "samples.jsonl", rows)
    return len(rows)


def gates() -> dict:
    out = {}
    for u in NEW_UNITS + RESERVE_UNITS:
        p = unit_dir(u) / "gate.json"
        if p.exists():
            g = read_json(p)
            fin = g.get("holdout") or g.get("round0") or {}
            out[u] = {"status": g["status"], "revision_rounds": g.get("revision_rounds"),
                      "kappa_runtime_ast": fin.get("kappa_runtime_ast"),
                      "runtime_vs_adjudicated": fin.get("runtime_vs_adjudicated"),
                      "ref_acc_runtime": fin.get("ref_acc_runtime"), "ref_acc_ast": fin.get("ref_acc_ast"),
                      "kappa_base": fin.get("kappa_base"), "kappa_instruct": fin.get("kappa_instruct"),
                      "n_valid": fin.get("n_valid"), "round0": {k: (g.get("round0") or {}).get(k) for k in
                                                                ("kappa_runtime_ast", "runtime_vs_adjudicated",
                                                                 "gate_pass")}}
        else:
            out[u] = {"status": "NOT_BUILT"}
    write_json(RESULTS / "units_gate.json", out)
    return out


def timing() -> None:
    rows = read_jsonl(RESULTS / "timing.jsonl")
    by = defaultdict(lambda: {"batches": 0, "rows": 0, "seconds": 0.0, "tokens": 0})
    for r in rows:
        arm = r["arms"][0]
        kind = ("ESC" if arm.startswith("ESC") else "PN" if arm.startswith("PN") else
                "ECBAN" if arm.startswith("ECBAN") else arm)
        k = f"{r['model']}:{kind}:{'path' if r['task'] in ('T1', 'T2') else 'bench'}"
        by[k]["batches"] += 1
        by[k]["rows"] += r["B"]
        by[k]["seconds"] += r["seconds"]
        by[k]["tokens"] += r.get("tokens", 0)
    summ = {k: {**v, "s_per_row": round(v["seconds"] / max(v["rows"], 1), 3)} for k, v in by.items()}
    tot_s = sum(v["seconds"] for v in by.values())
    tot_rows = sum(v["rows"] for v in by.values())
    sw = read_jsonl(RESULTS / "model_switches.jsonl")
    write_json(RESULTS / "timing_summary.json", {"by_arm_kind": summ, "total_gpu_batch_seconds": round(tot_s, 1),
                                                 "total_rows": tot_rows, "gpu_hours": round(tot_s / 3600, 3),
                                                 "model_switches": sw, "n_switches": len(sw)})
    first = {}
    for r in rows:
        k = r["arms"][0].split("_d")[0].split("_a")[0]
        if k not in first:
            first[k] = {"first_batch_seconds": r["seconds"], "B": r["B"], "s_per_row": round(r["seconds"] / r["B"], 3),
                        "utc": r["utc"]}
    write_json(RESULTS / "timing_extrapolation.json",
               {"note": "first batch of every arm type with its per-row cost; the extrapolated total for the full "
                        "queue (all pre-registered arms at their planned N) fitted the remaining budget at every check, "
                        "so no N was cut and no arm was dropped (plan drop order never triggered)",
                "first_batch_by_arm": first, "planned_rows_run": tot_rows,
                "observed_gpu_hours": round(tot_s / 3600, 3)})


def costs() -> dict:
    tot = {}
    for f in glob.glob(str(LOGS / "openrouter_spend*.jsonl")):
        s = 0.0
        n = 0
        for l in Path(f).read_text().splitlines():
            try:
                s += float(json.loads(l).get("cost") or 0)
                n += 1
            except (json.JSONDecodeError, ValueError):
                continue
        tot[Path(f).name] = {"usd": round(s, 5), "n_calls": n}
    p = RESULTS / "openrouter_cost_paths.json"
    if p.exists():
        j = read_json(p)
        tot["path_judge (exp8 suite)"] = {"usd": j.get("total_usd"), "n_calls": j.get("n_calls")}
    out = {"by_source": tot, "total_usd": round(sum(v["usd"] or 0 for v in tot.values()), 4), "cap_usd": 2.0,
           "utc": utc_now()}
    write_json(RESULTS / "costs.json", out)
    return out


def sensitivities(summ: dict, preds: dict) -> dict:
    out = {"label": "pre-specified sensitivities (descriptive; the A1 decision is pooled next round)"}
    for name, units in (("primary", NEW_UNITS), ("with_extension", NEW_UNITS + RESERVE_UNITS)):
        us = [u for u in units if u in preds and preds[u].get("status") == "OK" and u in summ and
              "outcome" in summ[u]]
        E = [summ[u]["outcome"]["E"] for u in us]
        res = {"units": us}
        for key, get in (("beta_plain", lambda p: (p.get("base_plain") or {}).get("beta")),
                         ("beta_other", lambda p: p.get("beta_other")),
                         ("base_hill1", lambda p: (p.get("base_chat") or {}).get("hill1", {}).get("hill1"))):
            xs = [get(preds[u]) for u in us]
            ok = [i for i, x in enumerate(xs) if x is not None]
            if len(ok) >= 3:
                pr = perm_p_spearman([xs[i] for i in ok], [E[i] for i in ok])
                res[key] = {"values": dict(zip(us, xs)), "rho_E": pr["rho"], "perm_p_one_sided": pr["p"],
                            "n": len(ok)}
        out[name] = res
    write_json(RESULTS / "sensitivities.json", out)
    return out


def pooled_inputs(summ: dict, preds: dict, xa: dict, gate: dict) -> dict:
    units = []
    for u in NEW_UNITS + RESERVE_UNITS:
        pr = preds.get(u)
        g = gate.get(u, {})
        rec = {"unit_id": u, "unit_kind": unit_kind(u), "parent_cluster": "T10" if u == "A6" else u, "gate": g}
        if pr:
            s = summ.get(u, {})
            esc = s.get("escape_cells", [])
            rec.update({
                "catalogue": pr.get("catalogue"), "default": pr.get("default"), "default_share": pr.get("twin_share"),
                "twin": {"n": pr.get("twin_n_twin"), "n_correct": pr.get("twin_n_correct"),
                         "comp_correct": pr.get("twin_comp_correct"), "comp_valid": pr.get("twin_comp_valid"),
                         "pass": pr.get("twin_pass")},
                "base": {"chat": {k: (pr.get("base_chat") or {}).get(k) for k in
                                  ("n_rows", "n_valid", "n_correct", "comp_correct", "comp_valid", "pass_rate")},
                         "plain": ({k: (pr.get("base_plain") or {}).get(k) for k in
                                    ("n_rows", "n_valid", "n_correct", "comp_correct", "comp_valid", "pass_rate",
                                     "beta")} if pr.get("base_plain") else None),
                         "beta": pr.get("beta"), "beta_ci": pr.get("beta_ci"), "beta_other": pr.get("beta_other"),
                         "r": pr.get("r"), "hill1": (pr.get("base_chat") or {}).get("hill1"),
                         "flags": (pr.get("base_chat") or {}).get("flag"), "audit": pr.get("base_audit")},
                "rivals": pr.get("rivals"),
                "escape": {"cells": esc, "E1": s.get("outcome", {}).get("E1"), "E2": s.get("outcome", {}).get("E2"),
                           "E": s.get("outcome", {}).get("E"), "movable_obs": s.get("outcome", {}).get("movable_obs"),
                           "landing": s.get("outcome", {}).get("landing")},
                "pn": s.get("pn"), "S": s.get("outcome", {}).get("S"),
                "t13": (s.get("knob_rows") or {}).get("T1.3"),
                "predicted_class": pr.get("predicted_class"), "predicted_landing": pr.get("predicted_landing"),
                "commitment": {"file": f"predictions/unit_{u}.json",
                               "sha256": sha256_file(PRED / f"unit_{u}.json"),
                               "utc": pr.get("committed_utc")}})
        units.append(rec)
    for t in EXISTING:
        v = xa.get(t)
        if not v:
            continue
        units.append({"unit_id": t, "unit_kind": "existing", "parent_cluster": t, "default": v["default"],
                      "twin": v["twin"], "escape": {"cells": v["cells"], "E1": v["E1"], "E2": v["E2"], "E": v["E"],
                                                     "movable_obs": v["movable_banfree"], "landing": v["landing"]},
                      "iteration4_E": v["iter4_E1_E2"], "frozen_screen": {"E1": v["screen_E1"], "E2": v["screen_E2"],
                                                                           "movable": v["screen_movable"]},
                      "verdict_change": v["verdict_change"]})
    pc = read_json(PRED / "precision_rule.json")
    out = {"schema": "iter5_panel_v1", "panel": "A", "engine": "HF transformers 4.57.6, exp19 CRN sampler",
           "precision": pc.get("engine"), "models": MODELS, "esc_seeds": ESC_SEEDS, "alphas": list(ALPHAS),
           "units": units, "utc": utc_now(),
           "notes": "raw ingredients per unit so the pooled step can recompute any variant; unit_kind "
                    "new_reserve_extension marks the logged extension units A8/A9"}
    write_json(ROOT / "pooled_inputs.json", out)
    return out


def assoc_top(pr: dict) -> str:
    """Association top-1 from the corrected mapping (POST HOC, D-assoc-mapping); the committed counts are all 0."""
    cor = RESULTS / "assoc_corrected.json"
    ac = None
    if cor.exists():
        ac = (read_json(cor)["units"].get(pr["unit"]) or {}).get("corrected_counts")
    ac = ac or (pr.get("rivals") or {}).get("assoc_counts") or {}
    if not ac or max(ac.values()) == 0:
        return "none"
    cat = pr["catalogue"]
    return sorted(ac, key=lambda m: (-ac[m], cat.index(m)))[0]


def prox_top(pr: dict) -> str:
    pdist = (pr.get("rivals") or {}).get("prox_dist") or {}
    ok = {m: d for m, d in pdist.items() if d is not None}
    if not ok:
        return "none"
    return sorted(ok, key=lambda m: (ok[m], m))[0]


def method_out(summ: dict, preds: dict, xa: dict, gate: dict, meta: dict) -> dict:
    ex_units, ex_cells, ex_exist = [], [], []
    for u in NEW_UNITS + RESERVE_UNITS:
        pr = preds.get(u)
        spec = read_json(unit_dir(u) / "spec.json") if (unit_dir(u) / "spec.json").exists() else None
        if not spec:
            continue
        g = gate.get(u, {})
        if not pr:
            ex_units.append({"input": spec["spec_text"], "output": f"excluded: {g.get('status')}",
                             "predict_base_repertoire": "none", "predict_association": "none",
                             "predict_proximity": "none", "metadata_unit": u, "metadata_unit_kind": unit_kind(u),
                             "metadata_gate": g})
            continue
        s = summ.get(u, {})
        oc = s.get("outcome", {})
        obs = ("MOVABLE" if oc.get("movable_obs") else "IMMOVABLE") + f"; landing={oc.get('landing')}"
        ex_units.append({"input": spec["spec_text"], "output": obs,
                         "predict_base_repertoire": f"{pr.get('predicted_class')}; landing={pr.get('predicted_landing')}",
                         "predict_association": f"landing={assoc_top(pr)}",
                         "metadata_predict_association_note": "corrected mapping, POST HOC (D-assoc-mapping); the "
                                                              "committed association forecast was uniform",
                         "predict_proximity": f"landing={prox_top(pr)}",
                         "metadata_unit": u, "metadata_unit_kind": unit_kind(u), "metadata_default": pr.get("default"),
                         "metadata_beta": pr.get("beta"), "metadata_beta_ci": pr.get("beta_ci"),
                         "metadata_E": oc.get("E"), "metadata_E1": oc.get("E1"), "metadata_E2": oc.get("E2"),
                         "metadata_S": oc.get("S"), "metadata_twin_share": pr.get("twin_share"),
                         "metadata_gate": g, "metadata_rivals": {k: v for k, v in (pr.get("rivals") or {}).items()
                                                                 if k != "merit_per_mode"}})
        for c in s.get("escape_cells", []):
            ex_cells.append({"input": f"unit {u} ({spec['task_id']}); direction seed {c['seed']}; alpha {c['alpha']}; "
                                      "ban-free push at spec positions, blocks 12-23, prefill only",
                             "output": ("CONFIRMED escape" if c["confirmed"] else
                                        ("screen pass, not confirmed" if c["screen_pass"] else "no escape")),
                             "predict_base_repertoire": pr.get("predicted_class"),
                             "metadata_unit": u, "metadata_unit_kind": unit_kind(u), "metadata_seed": c["seed"],
                             "metadata_alpha": c["alpha"], "metadata_share10": c["share10"],
                             "metadata_pass10": c["pass10"], "metadata_share30": c.get("share30"),
                             "metadata_pass30": c.get("pass30"), "metadata_p_binom": c.get("p_binom"),
                             "metadata_landing_counts": c.get("landing_counts")})
    for t in EXISTING:
        v = xa.get(t)
        if not v:
            continue
        sv = v["screen_movable"]
        ex_exist.append({"input": f"existing task {t} (default {EXISTING_DEFAULT[t]}): fresh twin + 8 fixed isotropic "
                                  "directions x alpha {1, 2}, ban-free unit, two-stage confirmation",
                         "output": ("MOVABLE" if v["movable_banfree"] else "IMMOVABLE") +
                                   f"; E={v['E']}; landing={v['landing']}",
                         "predict_frozen_screen": "none" if sv is None else ("MOVABLE" if sv else "IMMOVABLE"),
                         "predict_iteration4": "MOVABLE" if max(ITER4_E.get(t, (0, 0))) > 0 else "IMMOVABLE",
                         "metadata_task": t, "metadata_E1": v["E1"], "metadata_E2": v["E2"],
                         "metadata_iter4_E": v["iter4_E1_E2"], "metadata_screen_E": [v["screen_E1"], v["screen_E2"]],
                         "metadata_verdict_change": v["verdict_change"], "metadata_twin": v["twin"]})
    out = {"metadata": meta,
           "datasets": [{"dataset": "panelA_units", "examples": ex_units},
                        {"dataset": "panelA_cells", "examples": ex_cells},
                        {"dataset": "existing_remeasure", "examples": ex_exist}]}
    write_json(ROOT / "method_out.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("outputs5")
    n = samples()
    logger.info(f"samples.jsonl: {n} rows")
    gate = gates()
    timing()
    cst = costs()
    preds = {read_json(p)["unit"]: read_json(p) for p in sorted(PRED.glob("unit_*.json"))}
    summ = read_json(RESULTS / "unit_summaries_with_extension.json")
    for u, s in summ.items():
        write_json(RESULTS / f"unit_{u}_summary.json", {"unit": u, "prediction_file": f"predictions/unit_{u}.json",
                                                         **s})
    xa = read_json(RESULTS / "extra_arm_a.json")
    sens = sensitivities(summ, preds)
    pooled_inputs(summ, preds, xa, gate)
    meta = {"method_name": "Panel A: base-model repertoire as a forecast of nudgeable coding tasks (Qwen3-8B)",
            "description": "Per unit: instruct neutral twin (N=50, CRN), base repertoire on identical chat-templated "
                           "ids (N=100) + plain completion (N=50), rivals, sha256-committed forecast (beta_u, r_u), then "
                           "8 fixed isotropic directions x alpha {1,2} with two-stage confirmation, plan noise (alpha "
                           "1, 2), T 1.3; Extra arm A re-measures the 15 existing tasks under the same ban-free unit.",
            "a1_primary": read_json(RESULTS / "a1.json"), "a2_primary": read_json(RESULTS / "a2.json"),
            "a1_with_extension": read_json(RESULTS / "a1_with_extension.json"),
            "a2_with_extension": read_json(RESULTS / "a2_with_extension.json"),
            "a2_assoc_corrected_posthoc": read_json(RESULTS / "a2_assoc_corrected.json"),
            "assoc_corrected_posthoc": read_json(RESULTS / "assoc_corrected.json"),
            "half_screen": read_json(RESULTS / "half_screen.json"),
            "extra_arm_a": {t: {k: v[k] for k in ("E1", "E2", "E", "movable_banfree", "landing", "iter4_E1_E2",
                                                  "screen_E1", "screen_E2", "screen_movable", "verdict_change")}
                            for t, v in xa.items()},
            "engine_check": read_json(RESULTS / "engine_check.json"),
            "labeller_recheck": {k: v for k, v in read_json(RESULTS / "labeller_recheck.json").items()
                                 if k in ("bench_all_refs_100", "bench_all_within_0.02", "path")},
            "units_gate": gate, "sensitivities": sens,
            "novelty_audit": {k: v for k, v in read_json(RESULTS / "novelty_audit.json").items() if k != "items"},
            "external_reference_check": read_json(RESULTS / "external_reference_check.json"),
            "dependency_usage": read_json(RESULTS / "dependency_usage.json"),
            "guard_check": {k: v for k, v in read_json(RESULTS / "guard_check.json").items() if k != "per_unit"},
            "repertoire_check": read_json(RESULTS / "repertoire_check_with_extension.json"),
            "knob_rows": read_json(RESULTS / "knob_rows_with_extension.json"),
            "deviations": read_jsonl(RESULTS / "deviations.jsonl"), "costs": cst,
            "timing": read_json(RESULTS / "timing_summary.json"),
            "gpu_tests": read_jsonl(RESULTS / "gpu_tests.jsonl"),
            "positive_control": read_jsonl(RESULTS / "positive_control.jsonl")}
    mo = method_out(summ, preds, xa, gate, meta)
    logger.info(f"method_out.json: {[len(d['examples']) for d in mo['datasets']]} examples")


if __name__ == "__main__":
    main()
