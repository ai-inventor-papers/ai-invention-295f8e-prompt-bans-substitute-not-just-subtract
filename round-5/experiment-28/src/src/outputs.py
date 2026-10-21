#!/usr/bin/env python3
"""data/samples.jsonl (one row per generated program, with its label) and method_out.json (exp_gen_sol_out schema):
datasets gemma_twins, gemma_pt_repertoire, gemma_novelty, gemma_escape_population, gemma_plan_noise,
gemma_transplant (one example per program; input = task + template + arm; output = label|pass; predict_<arm> =
label|pass of the CRN-coupled slot in the coupled arms), plus metadata = every analysis, verdict, deviation, cost,
GPU-hour and commit hash."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, IT_ID, IT_REV, PRED_DIR, PT_ID, PT_REV, RESULTS_DIR, ROOT, read_json,
                 read_jsonl, write_json, write_jsonl)

SAMPLE_KEYS = ("row_id", "model", "model_kind", "task", "arm", "stage", "site", "lambda", "alpha", "direction_seed",
               "dir_kind", "tkind", "template", "slot", "temperature", "top_k", "thinking", "precision",
               "prompt_sha256", "prompt_kind", "label", "labeller_source", "passed", "valid", "runtime_label",
               "ast_label", "runtime_label_frozen", "ast_label_frozen", "regate_t2_applied", "judge_label",
               "fallback_label", "extract_how", "finish_reason", "n_new_tokens", "realised_disp", "code_sha256", "code",
               "pad", "batch_id", "utc")


def build_samples(c1: dict[str, Any] | None) -> list[dict[str, Any]]:
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    for f in sorted(DATA_DIR.glob("raw_*.jsonl")):
        for r in read_jsonl(f):
            l = labs.get(r["row_id"], {})
            row = {k: (l.get(k) if l.get(k) is not None else r.get(k)) for k in SAMPLE_KEYS}
            row["unit"] = r["task"]
            if c1:
                u = c1["units"][r["task"]]
                row["unit_kind"] = (u["class"] or "NO_CLASS") if u["defaulted"] else "NO_DEFAULT"
                row["unit_D"] = u["D"]
            row["labelled"] = bool(l)
            row["raw_file"] = f.name
            out.append(row)
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    return out


def _s(x: Any) -> str:
    return x if isinstance(x, str) else json.dumps(x)


def lp(r: dict[str, Any] | None) -> str:
    if not r:
        return "missing"
    return f"{r.get('label')}|pass={bool(r.get('passed'))}"


def main() -> None:
    c1 = read_json(PRED_DIR / "commit_E1.json") if (PRED_DIR / "commit_E1.json").exists() else None
    samples = build_samples(c1)
    prompts = {r["sha256"]: r["text"] for r in read_jsonl(DATA_DIR / "prompts_fed.jsonl")}
    from cfg import E23

    e23 = {(r["task"], r["arm"], r.get("template"), r.get("slot")): r for r in read_jsonl(E23 / "data" / "samples.jsonl")
           if r["task"] in ("T1", "T2") and r.get("stage") in ("A", "B") and r["arm"] in ("twin", "esc9003_a1")}
    by_key = {}
    for r in samples:
        by_key[(r["stage"], r["arm"], r["task"], r.get("template"), r.get("slot"))] = r

    def ex(r: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        # input = task + template + arm (+ the fed prompt's sha256; the prompt texts are in data/prompts_fed.jsonl)
        inp = f"prompt_sha256={r['prompt_sha256']}"
        head = (f"task {r['task']} | template {r.get('template')} | slot {r.get('slot')} | arm {r['arm']} | "
                f"model {r.get('model_kind')} | stage {r['stage']}\n")
        meta = {f"metadata_{k}": (_s(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in
                ("row_id", "task", "arm", "stage", "model_kind", "template", "slot", "alpha", "direction_seed", "lambda",
                 "site", "labeller_source", "finish_reason", "n_new_tokens", "unit_kind", "unit_D", "realised_disp")}
        meta["metadata_code"] = (r.get("code") or "")[:1500]
        return {"input": head + inp, "output": lp(r), **meta, **extra}

    ds: dict[str, list[dict[str, Any]]] = {k: [] for k in ("gemma_twins", "gemma_pt_repertoire", "gemma_novelty",
                                                            "gemma_escape_population", "gemma_plan_noise",
                                                            "gemma_transplant", "gemma_engine_check")}
    for r in samples:
        st = r["stage"]
        twin = by_key.get(("twin", "twin", r["task"], r.get("template"), r.get("slot")))
        if st == "twin":
            pt = by_key.get(("ptchat", "pt_chat", r["task"], r.get("template"), r.get("slot")))
            ds["gemma_twins"].append(ex(r, {"predict_pt_chat_same_slot": lp(pt)}))
        elif st in ("ptchat", "ptplain"):
            ds["gemma_pt_repertoire"].append(ex(r, {"predict_it_twin_same_slot": lp(twin) if st == "ptchat" else "n/a"}))
        elif st == "novelty":
            D = c1["units"][r["task"]]["D"] if c1 else None
            ds["gemma_novelty"].append(ex(r, {"predict_twin_default": f"{D}|pass=True"}))
        elif st in ("push", "confirm"):
            key = "gemma_plan_noise" if str(r["arm"]).startswith("pn_") else "gemma_escape_population"
            ds[key].append(ex(r, {"predict_twin_same_slot": lp(twin)}))
        elif st in ("transplant", "transplant_valid"):
            extra = {"predict_twin_same_slot": lp(twin)}
            for a in ("T", "RND", "XT", "RP"):
                extra[f"predict_{a}_same_slot"] = lp(by_key.get(("transplant", a, r["task"], r.get("template"),
                                                                 r.get("slot"))))
            ds["gemma_transplant"].append(ex(r, extra))
        elif st == "engine_check":
            k23 = (r["task"], r["arm"].replace("e23_", ""), r.get("template"), r.get("slot"))
            ds["gemma_engine_check"].append(ex(r, {"predict_exp23_same_slot": lp(e23.get(k23))}))
    meta: dict[str, Any] = {
        "method_name": "Claim E: Gemma-3-4B base-model (pt) repertoire as a predictor of ban-free nudge effects in the "
                       "instruction-tuned model (it), with a pt->it transplant and matched controls",
        "models": {"it": [IT_ID, IT_REV], "pt": [PT_ID, PT_REV]},
        "commitments_log": [json.loads(l) for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()],
    }
    for name in ("e_a1", "e_a2", "escape", "pn", "transplant", "transplant_norms", "regate", "structural_audit",
                 "engine_check", "labeller_recheck", "iter4_rescored", "novelty_audit", "pt_label_audit",
                 "tests_cpu", "tests_gpu_it", "tests_gpu_pt", "tests_gpu_transplant", "transplant_lambda",
                 "opening_ladder", "deviations", "costs", "timing_summary", "preflight_inputs", "dependency_usage",
                 "rederive", "rederive_headlines", "verdicts", "rejudge_disputed"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name in ("regate", "structural_audit", "novelty_audit", "pt_label_audit"):
                d = {k: v for k, v in d.items() if k not in ("rows", "sample")}
            meta[name] = d
    if c1:
        meta["predictors_commit_E1"] = {k: v for k, v in c1.items() if k not in ("transplant_norms",)}
    out = {"metadata": meta, "datasets": [{"dataset": k, "examples": v} for k, v in ds.items() if v]}
    write_json(ROOT / "method_out.json", out, indent=None)
    print({k: len(v) for k, v in ds.items()})


if __name__ == "__main__":
    main()
