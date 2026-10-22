#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema): one example per CRN slot and cell family, with predict_<arm> =
'<label>|<passed>' for every arm that ran on that slot; input = the slot's twin prompt (user text), output = the
clean twin's own 'label|passed' on the same slot (the unpushed reference). Metadata = every analysis, gate, commit
and deviation of the artifact.

Datasets: k_2x2 (S1: D1-D5 per task x alpha x slot), k_profile (S2: D1, P_top, P_rest, P_shuf), k_prices (S3: PN* at
D* = D1 and the five knobs, with the source of each knob's rows), engine_check (S0 twins vs exp30), e1_sweep
(exploratory dose sweep of the ban-free unit).

usage: .venv/bin/python src/outputs_k.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import LABELS, RESULTS, read_json, read_jsonl  # noqa: E402

OUT = K.ROOT / "method_out.json"


def prompts() -> dict[tuple[str, str], str]:
    out = {}
    for line in open(K.V22 / "prompts" / "prompts4.jsonl"):
        r = json.loads(line)
        if r["kind"] == "twin":
            out[(r["task"], r["template_id"])] = r["user_text"]
    return out


def lab_index() -> dict[tuple[str, str, str, int], str]:
    labs = {l["key"]: l for l in read_jsonl(LABELS)}
    idx = {}
    for name in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl"):
        for r in read_jsonl(K.RAW_DIR / name):
            l = labs.get(K.row_key(r))
            if l is not None:
                idx[(r["task"], r["template"], r["arm"], int(r["sample_id"]))] = f"{l['label']}|{bool(l['passed'])}"
    return idx


def safe(arm: str) -> str:
    return arm.replace("E27:", "E27_").replace(".", "_").replace("*", "star")


def ex(pr: dict, idx: dict, task: str, w: str, k: int, arms: dict[str, str], meta: dict[str, Any]) -> dict | None:
    preds = {f"predict_{name}": idx[(task, w, arm, k)] for name, arm in arms.items() if (task, w, arm, k) in idx}
    if not preds:
        return None
    e = {"input": f"[task {task} | template {w} | CRN slot k={k}]\n{pr[(task, w)]}",
         "output": idx.get((task, w, "TWIN", k), "unlabelled"), **preds,
         "metadata_task": task, "metadata_template": w, "metadata_k": k,
         "metadata_uniform_seed": K.stable_seed(task, w, k)}
    e.update({f"metadata_{k_}": v for k_, v in meta.items()})
    return e


def build() -> dict[str, Any]:
    pr = prompts()
    idx = lab_index()
    ds: dict[str, list] = {"k_2x2": [], "k_profile": [], "k_prices": [], "engine_check": [], "e1_sweep": [],
                           "e3_replicate": []}
    for task in K.S1_TASKS:
        for alpha in (1, 2):
            ks = K.K20 if (task == "T2" and alpha == 2) else K.K10
            for w in K.TEMPLATES:
                for k in ks:
                    e = ex(pr, idx, task, w, k, {d: f"{d}_a{alpha}" for d in ("D1", "D2", "D3", "D4", "D5")},
                           {"alpha": alpha, "family": "S1",
                            "designs": "D1=U_abs x S4, D2=U_abs x S5, D3=U_bf x S4, D4=U_bf x S5, D5=U_bf* x S4"})
                    if e:
                        ds["k_2x2"].append(e)
        for w in K.TEMPLATES:
            for k in K.K10:
                e = ex(pr, idx, task, w, k, {"D1": "D1_a2", "PTOP": "PTOP_a2", "PREST": "PREST_a2",
                                             "PSHUF": "PSHUF_a2"}, {"alpha": 2, "family": "S2"})
                if e:
                    ds["k_profile"].append(e)
                e = ex(pr, idx, task, w, k, {f"D3_a{a}": f"D3_a{a}" for a in (1, 2, 3, 4, 6)} |
                       {"D1_a1": "D1_a1", "D1_a2": "D1_a2"}, {"family": "E1 (exploratory)"})
                if e:
                    ds["e1_sweep"].append(e)
    for w in K.TEMPLATES:
        for k in range(10, 20):
            e = ex(pr, idx, "T10", w, k, {d: f"{d}_a2" for d in ("D1", "D2", "D3", "D4", "D5", "PTOP", "PREST",
                                                                  "PSHUF")}, {"alpha": 2, "family": "E3 fresh slots"})
            if e:
                ds["e3_replicate"].append(e)
        for k in K.K10:
            e = ex(pr, idx, "T03", w, k, {d: f"{d}_a2" for d in ("D1", "D2", "D3", "D4")},
                   {"alpha": 2, "family": "E3 T03 2x2"})
            if e:
                ds["e3_replicate"].append(e)
    s3 = read_json(RESULTS / "s3_prices.json")
    dstar = s3["D_star"]
    for task in K.D5_TASKS:
        src = s3["knob_sources"][task]
        for w in K.TEMPLATES:
            for k in K.K10:
                arms = {"PNstar_a1": f"{dstar}_a1", "PNstar_a2": f"{dstar}_a2"}
                arms.update({safe(knob): arm for knob, arm in src.items()})
                e = ex(pr, idx, task, w, k, arms, {"family": "S3", "D_star": dstar,
                                                   "knob_row_sources": json.dumps(src)})
                if e:
                    ds["k_prices"].append(e)
    e30 = {}
    for l in read_jsonl(K.E30 / "data" / "labels.jsonl"):
        if l.get("arm") == "TWIN":
            e30[(l["task"], l["template"], int(l["slot"]))] = f"{l['label']}|{bool(l['passed'])}"
    for task in K.D5_TASKS:
        for w in K.TEMPLATES:
            for k in K.K10:
                if (task, w, "TWIN", k) in idx and (task, w, k) in e30:
                    ds["engine_check"].append({
                        "input": f"[task {task} | template {w} | CRN slot k={k}]\n{pr[(task, w)]}",
                        "output": e30[(task, w, k)], "predict_TWIN_this_engine": idx[(task, w, "TWIN", k)],
                        "metadata_task": task, "metadata_template": w, "metadata_k": k,
                        "metadata_reference": "exp30 bf16 TWIN label|passed (max_new 384)"})
    meta: dict[str, Any] = {
        "method_name": "Plan-noise crosswalk: dose unit x direction seeds, profile split and prices at D* (step K)",
        "description": ("Qwen/Qwen3-8B b968826d, bf16 HF transformers 4.57.6 (exp29 engine d numerics), thinking off. "
                        "Per-sample isotropic random direction u at the task-spec positions of blocks 12-23, prefill "
                        "only, displacement-targeted to alpha * unit[l, p]. The 2x2 crosses the dose unit (U_abs = the "
                        "ban's own per-cell displacement norm; U_bf = ||h_twin|| x r_Q(l)) with the direction seeds "
                        "(S4 exp29/exp19, S5 exp27) on shared CRN slots and one decoding path; U_bf* splits per-block "
                        "energy from within-block profile; S2 restricts U_abs to its top-quartile cells; S3 prices PN "
                        "at D* against iteration 5's knobs on full-simplex randomisation hulls."),
        "model": K.MODEL_ID, "model_revision": K.MODEL_REVISION, "precision": K.PRECISION,
        "prediction_format": "'<label>|<passed>' per arm; output = the clean twin's own label|passed on the slot",
    }
    for name in ("anchors", "s1_2x2", "s2_profile", "s3_prices", "retag", "e1_sweep", "e2_geometry", "e3_replicate",
                 "novelty_audit",
                 "cpu_gates", "unit_tests_gpu", "engine_check", "knob_check", "bint_intent_identity", "commit_audit",
                 "timing", "costs", "rederive", "memory_probe", "unit_profiles", "g5_hull_gate"):
        p = RESULTS / f"{name}.json"
        if p.exists():
            v = read_json(p)
            if name == "novelty_audit":
                v = {k: x for k, x in v.items() if k != "items"} | {"items": [
                    {k: x for k, x in it.items() if k in ("kind", "sha", "task", "arm", "label", "judge_class",
                                                          "manual_class", "final_class", "nearest")}
                    for it in v.get("items", [])]}
            if name == "s3_prices":
                v = {k: x for k, x in v.items() if k != "per_task"} | {"per_task_H5": {
                    t: {c: {"H5": d["H5"], "P15": d["P15"], "P20": d["P20"], "H5_mixture": d.get("H5_mixture"),
                            "arms": d.get("arms"), "hill_q_at_H5": d.get("hill_q_at_H5")} for c, d in pt.items()}
                    for t, pt in v["per_task"].items()}}
            meta[name] = v
    meta["deviations"] = read_json(RESULTS / "deviations.json") if (RESULTS / "deviations.json").exists() else []
    meta["commit1"] = read_json(K.PRED / "commit1.json")
    meta["commit2"] = {k: v for k, v in read_json(K.PRED / "commit2.json").items() if k != "anchors"}
    meta["hardware"] = read_json(K.PRED / "hardware.json")
    return {"metadata": meta, "datasets": [{"dataset": n, "examples": e} for n, e in ds.items() if e]}


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("outputs_k")
    obj = build()
    OUT.write_text(json.dumps(obj, indent=1, default=K._json_default))
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in obj['datasets']]}; "
                f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
