#!/usr/bin/env python3
"""STEP 12: data/samples.jsonl (every generated row with its label) and method_out.json (exp_gen_sol_out schema) with
datasets heldout_ban_samples, heldout_banfree_samples and heldout_task_events, plus mini/preview variants."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, write_json, write_jsonl)

SAMPLE_KEYS = ("row_id", "model", "task", "arm", "stage", "site", "alpha", "direction_seed", "dir_kind", "template",
               "slot", "temperature", "top_k", "thinking", "prompt_sha256", "prompt_kind", "mode", "label",
               "labeller_source", "passed", "valid", "runtime_label", "ast_label", "judge_label", "fallback_label",
               "finish_reason", "n_new_tokens", "realised_disp", "code_sha256", "code", "pad", "flag", "batch_id")


def build_samples() -> list[dict[str, Any]]:
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    for f in sorted(DATA_DIR.glob("raw_*.jsonl")):
        for r in read_jsonl(f):
            l = labs.get(r["row_id"], {})
            row = {k: (l.get(k) if k in l and l.get(k) is not None else r.get(k)) for k in SAMPLE_KEYS}
            row["raw_file"] = f.name
            out.append(row)
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    return out


def _s(x: Any) -> str:
    return x if isinstance(x, str) else json.dumps(x)


def main() -> None:
    samples = build_samples()
    prompts = {r["sha256"]: r["text"] for r in read_jsonl(DATA_DIR / "prompts_fed.jsonl")}
    pre = read_json(PRED_DIR / "commit_preban.json")
    bans = read_json(RESULTS_DIR / "bans.json")

    def top(t: str, nm: str) -> str:
        f = pre["tasks"][t]["forecasts"][nm]
        return str(f.get("top1")) if f.get("defined") else "undefined"
    ban_ex, bf_ex = [], []
    for r in samples:
        t = r["task"]
        base = {"input": prompts.get(r["prompt_sha256"], ""), "output": f"{r['label']}|passed={bool(r['passed'])}"}
        meta = {f"metadata_{k}": (_s(r[k]) if k in ("realised_disp",) else r[k]) for k in
                ("row_id", "task", "arm", "stage", "template", "slot", "alpha", "direction_seed", "temperature",
                 "labeller_source", "finish_reason", "n_new_tokens", "pad", "flag", "code", "realised_disp")}
        if r["stage"] == "BAN":
            ex = {**base, **meta,
                  "predict_movability_class": pre["tasks"][t]["predicted_class"],
                  "predict_push_landing": top(t, "push_landing"), "predict_opening_ladder": top(t, "opening_ladder"),
                  "predict_association": top(t, "association"), "predict_proximity": top(t, "proximity"),
                  "metadata_primary": r["arm"] == "ban", "metadata_D": pre["tasks"][t]["D"]}
            ban_ex.append(ex)
        else:
            bf_ex.append({**base, **meta, "predict_movability_class": pre["tasks"][t]["predicted_class"]})
    ev = []
    for t in ALL_TASKS:
        p = pre["tasks"][t]
        b = bans.get(t, {})
        ev.append({"input": f"{t}: modal ban of '{p['D_display']}' ({p['D']}); 5 templates x 20 CRN slots",
                   "output": f"A_t={b.get('A_t')}|C_t={b.get('C_t')}",
                   "predict_movability_class": p["predicted_class"], "predict_E_t": str(p["E_t"]),
                   "predict_push_landing": top(t, "push_landing"), "predict_opening_ladder": top(t, "opening_ladder"),
                   "predict_association": top(t, "association"), "predict_proximity": top(t, "proximity"),
                   "metadata_E_t_1": p["E_t_1"], "metadata_E_t_2": p["E_t_2"], "metadata_confirmed": _s(p["confirmed"]),
                   "metadata_opening_margin": p["opening_margin"], "metadata_rivals": _s(p["rivals"]),
                   "metadata_outcome": _s(b)})
    meta = {"method_name": "Held-out-family (gemma-3-4b-it) confirmation of push-movability as a predictor of ban "
                           "compliance (C3a), ban-free landing forecasts (C3b) and a descriptive C1 price replication",
            "model": pre["model"], "revision": pre["revision"], "weights": pre["weights"]}
    for name in ("c3a", "rivals", "c3b", "c1_prices", "unit_sensitivity", "grep_audit", "label_audit", "novelty_audit",
                 "tests_gpu", "tests_cpu", "pilot", "qwen_ratio", "screen", "labeller_recheck", "timing_summary",
                 "deviations", "costs", "crn_flips", "phrasing", "escape", "dependency_usage", "unit_probe",
                 "posthoc_t2_relabel", "rederive", "commit_chain_verify_final", "opening_ladder", "bans",
                 "banfree_predictors"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name == "novelty_audit":
                d = {k: v for k, v in d.items() if k != "rows"} | {"n_rows": len(d.get("rows", []))}
            if name == "unit_probe":
                d = {t: {"nonmassive_norm_fraction_by_block": v["nonmassive_norm_fraction_by_block"],
                         "first_rows": [x["text"][:160] for x in v["rows"][8:12]]} for t, v in d.items()}
            if name == "tests_gpu":
                d = {k: v for k, v in d.items() if k != "model_info"}
            meta[name] = d
    out = {"metadata": meta, "datasets": [{"dataset": "heldout_ban_samples", "examples": ban_ex},
                                          {"dataset": "heldout_banfree_samples", "examples": bf_ex},
                                          {"dataset": "heldout_task_events", "examples": ev}]}
    write_json(ROOT / "method_out.json", out, indent=None)
    write_json(ROOT / "full_method_out.json", out, indent=None)
    mini = {"metadata": {"method_name": meta["method_name"], "model": meta["model"], "note": "first 3 examples per dataset"},
            "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in out["datasets"]]}
    write_json(ROOT / "mini_method_out.json", mini)

    def trunc(o: Any) -> Any:
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        if isinstance(o, list):
            return [trunc(v) for v in o]
        return o
    write_json(ROOT / "preview_method_out.json", trunc(mini))
    print(f"method_out: {len(ban_ex)} ban, {len(bf_ex)} ban-free, {len(ev)} task events")


if __name__ == "__main__":
    main()
