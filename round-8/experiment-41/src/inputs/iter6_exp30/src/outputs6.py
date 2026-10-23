#!/usr/bin/env python3
"""STEP 11: method_out.json (exp_gen_sol_out schema). Datasets: engine_check, stage_a_exchange, site_grid,
state_vs_token, top5_push, landing_forecast. One example per (task, cell, slot): input = prompt id + cell spec,
output = the neutral twin's 'label|pass' at that CRN slot (the baseline), predict_<cell> = the cell's 'label|pass'
(the method), predict_twin = the baseline again. Metadata holds every analysis, verdict, deviation, cost, timing and
the commit chain."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, utc_now, write_json
from cfg6 import DEFAULT6, SLOT_MAP, Y6
from commit6 import chain, verify
import analysis6 as A


def lp(r: dict[str, Any] | None) -> str:
    if r is None:
        return "missing"
    return f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


def safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def realised_meta(r: dict[str, Any]) -> dict[str, Any]:
    rec = r.get("realised") or {}
    dr = (rec.get("dR") or {})
    dg = rec.get("dG1") or {}
    return {"metadata_D_R_block35": dr.get("35", dr.get(35)), "metadata_D_g1_block35": dg.get("35", dg.get(35)),
            "metadata_first_token_kl": rec.get("first_token_kl"), "metadata_dir_seed": r.get("dir_seed")}


def examples_for(rows: list[dict[str, Any]], cells: list[str] | None, cell_kind: set[str] | None,
                 desc: str) -> list[dict[str, Any]]:
    twins = {(r["task"], r["slot_index"]): r for r in rows if r["arm"] == "TWIN"}
    out = []
    for r in rows:
        if r["arm"] == "TWIN":
            continue
        if cells is not None and r["arm"] not in cells:
            continue
        if cell_kind is not None and r["cell"] not in cell_kind:
            continue
        w, k = SLOT_MAP[r["slot_index"]]
        tw = twins.get((r["task"], r["slot_index"]))
        ex = {"input": f"{desc} | task={r['task']} template={w} stream_k={k} slot={r['slot_index']} cell={r['arm']} "
                       f"prompt_kind={r['prompt_kind']} site={r.get('site')} alpha={r.get('alpha')} "
                       f"band={r.get('band')}",
              "output": lp(tw), f"predict_{safe(r['arm'])}": lp(r), "predict_twin": lp(tw),
              "metadata_task": r["task"], "metadata_cell": r["arm"], "metadata_slot": r["slot_index"],
              "metadata_template": w, "metadata_stream_k": k, "metadata_default": DEFAULT6.get(r["task"]),
              "metadata_Y": Y6.get(r["task"]), "metadata_label": r["label"], "metadata_passed": r["passed"],
              "metadata_labeller_source": r.get("labeller_source"), "metadata_n_new_tokens": r.get("n_new_tokens"),
              "metadata_finish_reason": r.get("finish_reason")}
        ex.update(realised_meta(r))
        if r.get("s3"):
            ex["metadata_s3_kl_mean"] = r["s3"].get("kl_mean_steps1_32")
        if r.get("dmd_T") is not None:
            ex["metadata_dmd_T"] = r["dmd_T"]
        out.append(ex)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("outputs6")
    rows = A.load_rows()
    ds = []
    # engine check: this engine's twin vs exp27's twin at the same CRN slot
    e27 = {}
    for r in read_jsonl(ROOT / "inputs_extra" / "exp27" / "data" / "labels.jsonl"):
        if r.get("arm") == "TWIN":
            e27[(r["task"], r["template"], int(r["slot"]))] = r
    ec = []
    for r in rows:
        if r["arm"] != "TWIN":
            continue
        w, k = SLOT_MAP[r["slot_index"]]
        o = e27.get((r["task"], w, k))
        if o is None:
            continue
        ec.append({"input": f"neutral twin | task={r['task']} template={w} stream_k={k}",
                   "output": f"{o['label']}|{'pass' if o.get('passed') else 'fail'}",
                   "predict_this_engine_bf16_rtx2000ada": lp(r), "predict_exp27_bf16": f"{o['label']}|"
                   f"{'pass' if o.get('passed') else 'fail'}", "metadata_task": r["task"], "metadata_slot": r["slot_index"]})
    if ec:
        ds.append({"dataset": "engine_check", "examples": ec})
    stage = examples_for(rows, None, {"BAN", "X", "COND", "RPOS", "MR", "PLACEBO"},
                         "Stage A exchange of the full ban's residual states into the neutral twin")
    if stage:
        ds.append({"dataset": "stage_a_exchange", "examples": stage})
    st = examples_for(rows, None, {"ST"}, "ST noise-site grid (displacement-targeted isotropic noise)")
    if st:
        ds.append({"dataset": "site_grid", "examples": st})
    svt = examples_for([r for r in rows if r["cell"] in ("DMD", "TWIN") or (r["cell"] == "ST" and r["site"] == "S3")],
                       None, {"DMD", "ST"}, "state noise (S3) vs departure-matched temperature (DMD)")
    if svt:
        ds.append({"dataset": "state_vs_token", "examples": svt})
    t5 = examples_for([r for r in rows if r["task"] == "T1"], None, {"TOP5PUSH", "TOP5BAN"},
                      "T1 top-five plan push / prompt top-five ban")
    if t5:
        ds.append({"dataset": "top5_push", "examples": t5})
    twins_ext = {}
    for r in rows:
        if r["cell"] == "EXT" and r["arm"].endswith("PAD"):
            twins_ext[(r["task"], r["arm"][:-3], r["slot_index"])] = r
        if r["cell"] == "W4" and r["arm"] == "TWIN_W4":
            twins_ext[(r["task"], "W4", r["slot_index"])] = r
    ext = []
    for r in rows:
        if r["cell"] not in ("EXT", "W4") or r["arm"].endswith("PAD") or r["arm"] == "TWIN_W4":
            continue
        key = (r["task"], "W4" if r["cell"] == "W4" else ("FORCED" if r["arm"].startswith("FORCED") else "SEED"),
               r["slot_index"])
        tw = twins_ext.get(key)
        w, k = SLOT_MAP[r["slot_index"]]
        ex = {"input": f"extension | task={r['task']} cell={r['arm']} prompt_kind={r['prompt_kind']} "
                       f"stream=({w},{k}) slot={r['slot_index']}",
              "output": lp(tw), f"predict_{safe(r['arm'])}": lp(r), "predict_padding_or_w4_twin": lp(tw),
              "metadata_task": r["task"], "metadata_cell": r["arm"], "metadata_slot": r["slot_index"],
              "metadata_label": r["label"], "metadata_passed": r["passed"]}
        ext.append(ex)
    if ext:
        ds.append({"dataset": "extensions_forced_seed_w4", "examples": ext})
    lf = RESULTS_DIR / "landing_forecast.json"
    if lf.exists():
        L = read_json(lf)
        ex = []
        for e in L["events"]:
            d = {"input": f"push-landing event {e['event']} ({e['set']}; model {e['model']}, engine {e['engine']})",
                 "output": str(e["landing_top1"]), "metadata_task": e["task"]}
            for nm in ("BASE", "TWINMIN", "OPEN", "OPEN_rank"):
                d[f"predict_{nm}"] = str(e.get(f"{nm}_top1"))
                d[f"metadata_{nm}_logscore"] = e.get(f"{nm}_logscore")
            ex.append(d)
        ds.append({"dataset": "landing_forecast", "examples": ex})
    meta: dict[str, Any] = {"method_name": "Where in the prompt the algorithm is chosen (iteration 6, bf16 Qwen3-8B)",
                            "description": "Stage A full-state exchange (method) against the neutral twin and "
                                           "matched-norm random / placebo exchanges (baselines); bf16 noise-site grid "
                                           "with a Firth indicator model; state noise vs KL-matched temperature; "
                                           "top-five plan push on the forced-prompt geometry; retrospective landing "
                                           "forecast contest", "utc": utc_now(), "n_rows": len(rows)}
    for name in ("engine_check", "stage_a", "site_grid", "state_vs_token", "top5_push", "landing_forecast",
                 "novelty_audit", "unit_tests_gpu", "timing_summary", "costs", "tests_cpu", "seed_collisions",
                 "inputs_available", "dependency_usage", "rederive"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            meta[name] = read_json(p)
    if "novelty_audit" in meta:
        meta["novelty_audit"] = {k: v for k, v in meta["novelty_audit"].items() if k != "rows"}
    meta["deviations"] = read_jsonl(RESULTS_DIR / "deviations.jsonl")
    meta["planned_deviations"] = read_json(ROOT / "predictions" / "commit0.json").get("planned_deviations")
    meta["commit_chain"] = {"commits": chain(), "verify": verify()}
    meta["hardware"] = read_json(ROOT / "predictions" / "hardware.json")
    meta["row_counts"] = dict(Counter(f"{r['task']}|{r['arm']}" for r in rows))
    write_json(ROOT / "method_out.json", {"metadata": meta, "datasets": ds})
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in ds]}")


if __name__ == "__main__":
    main()
