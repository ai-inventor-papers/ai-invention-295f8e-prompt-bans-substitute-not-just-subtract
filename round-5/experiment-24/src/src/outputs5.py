#!/usr/bin/env python3
"""Final outputs: data/samples.jsonl (one row per labelled program) and method_out.json (exp_gen_sol_out).

method_out.json datasets (one example per CRN slot; input = the rendered user prompt; output = the reference arm's
'label|pass'; predict_<arm> = that arm's 'label|pass' on the same slot):
  base_repertoire          BASE_CHAT (output) and BASE_PLAIN (predict_base_plain), Qwen3-8B-Base
  transplant_selection     S1 slots j 0-9: TWIN (output) vs T(0.25/0.5/1), MR(0.25/0.5/1), READ(1), EARLY(1), LATE(1)
  transplant_confirmation  fresh S2 slots: TWIN_S2 (output) vs T(lambda*), MR(lambda*), XT(lambda*), MRP / ISO
  desharpen                slots j 10-15: TWIN (output) vs DS / ISO at alpha 0.5 / 1 / 2
  reverse                  base slots j 0-9: BTWIN (output) vs RT(1), BMR(1)
  engine_check             exp17 screen rows (output) vs this engine (predict_this_engine)
metadata: every analysis file of results/, the commits and the deviations.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (DATA_DIR, DS_SLOTS, E17, PATH_TASKS, PRED_DIR, RESULTS_DIR, ROOT, S1_SLOTS, read_json,  # noqa: E402
                 read_jsonl, setup_logging, utc_now, write_json, write_jsonl)
from prompts5 import load_prompts  # noqa: E402

KEEP = ["sample_id", "model", "task", "unit_kind", "arm", "knob_class", "site", "lambda", "alpha", "direction_seed",
        "partner", "template", "slot", "crn_key", "u_seed", "temperature", "top_k", "min_p", "thinking", "precision",
        "engine", "prompt_kind", "prompt_sha256", "max_new", "stop_rule", "block_id", "batch_B", "label",
        "labeller_source", "runtime_label", "ast_label", "judge_label", "passed", "valid", "finish_reason",
        "n_new_tokens", "realised_disp", "extract_info", "code_sha256", "code", "utc"]


def merged_samples() -> list[dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    for f in ("base_raw.jsonl", "instr_raw.jsonl", "basehook_raw.jsonl", "engine_check_raw.jsonl"):
        for r in read_jsonl(DATA_DIR / f):
            raw.setdefault(r["sample_id"], r)
    out, seen = [], set()
    for lab in read_jsonl(DATA_DIR / "labels.jsonl"):
        sid = lab["sample_id"]
        if sid in seen:
            continue
        seen.add(sid)
        r = raw.get(sid, {})
        row = {**r, **lab}
        row["unit_kind"] = "path" if row.get("task") in PATH_TASKS else "bench"
        row["precision"] = "bf16"
        row["engine"] = r.get("engine", lab.get("engine"))
        out.append({k: row.get(k) for k in KEEP})
    return out


def lp(r: dict[str, Any] | None) -> str:
    if r is None:
        return "NA"
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def safe(a: str) -> str:
    return "predict_" + a.replace(".", "_").replace("-", "_")


def build_dataset(samples: list[dict[str, Any]], name: str, ref_arm: str, arms: list[str], slots_ok,
                  prompts: dict, model_sfx: str | None = None, require_pred: bool = True) -> dict[str, Any] | None:
    by: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for s in samples:
        if model_sfx is not None and not str(s.get("model", "")).endswith(model_sfx):
            continue
        if s["arm"] != ref_arm and s["arm"] not in arms:
            continue
        if not slots_ok(s):
            continue
        by[(s["task"], s["template"], int(s["slot"]))][s["arm"]] = s
    ex = []
    for (t, w, j), d in sorted(by.items()):
        if ref_arm not in d:
            continue
        p = prompts.get((t, w))
        e = {"input": p["user_text"] if p else f"{t}|{w}", "output": lp(d[ref_arm]),
             "metadata_task": t, "metadata_template": w, "metadata_slot": j,
             "metadata_crn_key": d[ref_arm].get("crn_key"), "metadata_model": d[ref_arm].get("model")}
        for a in arms:
            if a in d:
                e[safe(a)] = lp(d[a])
        if require_pred and not any(k.startswith("predict_") for k in e):
            continue
        ex.append(e)
    return {"dataset": name, "examples": ex} if ex else None


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("outputs5")
    samples = merged_samples()
    write_jsonl(DATA_DIR / "samples.jsonl", samples)
    logger.info(f"samples.jsonl: {len(samples)} rows")
    prompts = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
    c2p = PRED_DIR / "commit2.json"
    c2 = read_json(c2p) if c2p.exists() else {"stage4_plan": {}}
    s2_arms = sorted({a for cells in c2["stage4_plan"].values() for a, _ in cells if a != "TWIN"})
    sel_arms = ["T0.25", "T0.5", "T1.0", "MR0.25", "MR0.5", "MR1.0", "READ1.0", "EARLY1.0", "LATE1.0"]
    ds = [
        build_dataset(samples, "base_repertoire", "BASE_CHAT", ["BASE_PLAIN"], lambda s: True, prompts, "-Base",
                      require_pred=False),
        build_dataset(samples, "transplant_selection", "TWIN", sel_arms, lambda s: int(s["slot"]) in S1_SLOTS,
                      prompts, "Qwen3-8B"),
        build_dataset(samples, "transplant_confirmation", "TWIN", s2_arms, lambda s: int(s["slot"]) >= 10,
                      prompts, "Qwen3-8B"),
        build_dataset(samples, "desharpen", "TWIN", [f"{k}{a}" for k in ("DS", "ISO") for a in (0.5, 1.0, 2.0)],
                      lambda s: int(s["slot"]) in DS_SLOTS, prompts, "Qwen3-8B"),
        build_dataset(samples, "reverse", "BTWIN", ["RT1.0", "BMR1.0"], lambda s: True, prompts, "-Base"),
    ]
    # the instruct twin on the same (task, template, slot) as a per-slot cross-model prediction of the base row
    tw = {(x["task"], x["template"], int(x["slot"])): x for x in samples
          if x["arm"] == "TWIN" and x.get("model") == "Qwen/Qwen3-8B"}
    if ds[0]:
        for e in ds[0]["examples"]:
            k = (e["metadata_task"], e["metadata_template"], e["metadata_slot"])
            if k in tw:
                e["predict_instruct_twin"] = lp(tw[k])
    # engine check: exp17 screen rows are the reference
    e17 = {}
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        if r["task"] in ("T03", "T2") and r["arm"] in ("NEUTRAL", "RAND9002_a1.0", "RAND9004_a1.0"):
            e17.setdefault((r["task"], r["arm"], r["template"], int(r["sample_id"])), r)
    ex = []
    for s in samples:
        if not s["arm"].startswith("EC_"):
            continue
        their = s["arm"].replace("EC_", "")
        ref = e17.get((s["task"], their, s["template"], int(s["slot"])))
        if ref is None:
            continue
        p = prompts.get((s["task"], s["template"]))
        ex.append({"input": p["user_text"], "output": f"{ref['label']}|{'pass' if str(ref['passed']) == 'True' else 'fail'}",
                   "predict_this_engine": lp(s), "metadata_task": s["task"], "metadata_arm": their,
                   "metadata_template": s["template"], "metadata_slot": int(s["slot"])})
    if ex:
        ds.append({"dataset": "engine_check", "examples": ex})
    ds = [d for d in ds if d]
    meta: dict[str, Any] = {"method_name": "base->instruct plan-state transplant (iteration 5, Step 1)",
                            "description": "Claim B / D / reverse interchange on Qwen3-8B-Base and Qwen3-8B; see "
                                           "README.md", "utc": utc_now()}
    for f in sorted(RESULTS_DIR.glob("*.json")):
        if f.name in ("geometry.json",):
            continue
        try:
            meta[f.stem] = read_json(f)
        except json.JSONDecodeError:
            continue
    for f in ("commit0.json", "commit1.json", "commit2.json", "precision_rule.json"):
        if (PRED_DIR / f).exists():
            meta[f"predictions_{Path(f).stem}"] = read_json(PRED_DIR / f)
    meta["commitments_log"] = (ROOT / "commitments.log").read_text().splitlines()
    write_json(ROOT / "method_out.json", {"metadata": meta, "datasets": ds}, indent=None)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in ds]}")


if __name__ == "__main__":
    main()
