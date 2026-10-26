#!/usr/bin/env python3
"""Build method_out.json in the exp_gen_sol_out schema.

datasets: one per task. examples: one per (paraphrase_id, sample_id) common-random-number slot (10 x 10):
  input  = the baseline user prompt of that paraphrase (segment + spec)
  output = algorithm label of the unsteered HF sample in that slot (c = 0, hook attached, same seed)
  predict_<arm> = '<label>|pass' or '<label>|fail' of the same slot under every other arm (steering arms share the
                  seed; vLLM prompt arms use their own seeds and are aligned by slot only)
metadata (top level): model, hardware, versions, protocol, deviations, gates, direction, conditions, buy_table,
predict_row, commitment_test summary, screen_verdict, openrouter cost, timing.
"""
from __future__ import annotations

import json
import platform
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, DATA_DIR, LOGS_DIR, MODEL_ID, RESULTS_DIR, SPEC, TASKS, WS, read_jsonl  # noqa: E402


def slug(cond: str) -> str:
    s = cond.replace("steer:", "steer_").replace(":", "_").replace("=", "").replace(".", "p").replace("@", "_at")
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def jl(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def versions() -> dict:
    out = {"python": platform.python_version()}
    for m in ("torch", "transformers", "vllm", "numpy", "scipy", "statsmodels"):
        try:
            mod = __import__(m)
            out[m] = getattr(mod, "__version__", "?")
        except ImportError:
            out[m] = None
    try:
        import torch
        out["cuda"] = torch.version.cuda
    except ImportError:
        pass
    return out


def main() -> None:
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    cst = jl(RESULTS_DIR / "cstar.json")
    L = cst["layer"]
    datasets = []
    for t in TASKS:
        rows = [r for r in samples if r["task"] == t]
        conds = sorted({r["condition"] for r in rows})
        ref_c = f"steer:dc:c=0:L={L}"
        slot = {}
        for r in rows:
            if r["sample_id"] >= 10:
                continue
            slot.setdefault((r["paraphrase_id"], r["sample_id"]), {})[r["condition"]] = r
        ex = []
        for (p, s), d in sorted(slot.items()):
            if ref_c not in d:
                continue
            ref = d[ref_c]
            e = {"input": (ref.get("segment") or "") + "\n\n" + SPEC[t],
                 "output": ref["label"],
                 "metadata_task": t, "metadata_paraphrase_id": p, "metadata_sample_id": s,
                 "metadata_reference_condition": ref_c, "metadata_reference_passed": ref["passed"],
                 "metadata_catalogue": CATALOGUE[t]}
            for c in conds:
                if c == ref_c or c not in d:
                    continue
                e[f"predict_{slug(c)}"] = f"{d[c]['label']}|{'pass' if d[c]['passed'] else 'fail'}"
            ex.append(e)
        datasets.append({"dataset": f"{t}_{'grid_path_search' if t == 'T1' else 'weighted_shortest_path'}",
                         "examples": ex})
    timing = read_jsonl(LOGS_DIR / "timing.jsonl")
    cost = sum(r.get("cost", 0.0) for r in read_jsonl(LOGS_DIR / "openrouter_cost.jsonl"))
    meta = {
        "method_name": "De-commitment steering screen (list-vs-implement difference-of-means direction)",
        "model": MODEL_ID, "thinking": "off (enable_thinking=False)",
        "hardware": jl(LOGS_DIR / "hardware.json"), "versions": versions(),
        "protocol": jl(RESULTS_DIR / "protocol.json"), "deviations": jl(RESULTS_DIR / "deviations.json"),
        "gates": {"R0": {t: (jl(RESULTS_DIR / "r0_gate.json") or {}).get("R0", {}).get(t, {}).get("pass") for t in TASKS},
                  "labeller_gate": {t: {k: (jl(RESULTS_DIR / "labeller_gate.json") or {}).get(t, {}).get(k)
                                        for k in ("pass", "flag", "kappa_runtime_ast", "runtime_vs_adjudicated",
                                                  "pipeline_vs_adjudicated")} for t in TASKS},
                  "engine_check": {t: (jl(RESULTS_DIR / "engine_check.json") or {}).get(t, {}).get("pass") for t in TASKS},
                  "hook_tests": (jl(RESULTS_DIR / "steer_state.json") or {}).get("hook_tests"),
                  "cpu_unit_tests": jl(RESULTS_DIR / "unit_tests.json"),
                  "vllm_same_seed_determinism": jl(RESULTS_DIR / "vllm_determinism.json"),
                  "hook_layer_test": jl(RESULTS_DIR / "hook_layer_test.json"),
                  "commitment_positive_control": {
                      t: (jl(RESULTS_DIR / "commitment_test.json") or {}).get("per_task", {}).get(t, {}).get(str(L), {})
                      .get("positive_control", {}).get("ok") for t in TASKS}},
        "direction": {"layer_selection": {k: v for k, v in (jl(RESULTS_DIR / "layer_selection.json") or {}).items()
                                          if k != "per_layer"},
                      "diagnostics_at_L": (jl(RESULTS_DIR / "direction_diagnostics.json") or {}).get("per_layer", {}).get(str(L)),
                      "layer_rule": (jl(RESULTS_DIR / "steer_state.json") or {}).get("layer_rule"), "c_star": cst},
        "conditions": jl(RESULTS_DIR / "condition_summaries.json"),
        "buy_table": jl(RESULTS_DIR / "buy_table.json"),
        "predict_row": jl(RESULTS_DIR / "predict_row.json"),
        "commitment_test": {t: (jl(RESULTS_DIR / "commitment_test.json") or {}).get("per_task", {}).get(t, {}).get(str(L))
                            for t in TASKS},
        "engine_check": jl(RESULTS_DIR / "engine_check.json"),
        "flips": jl(RESULTS_DIR / "flips.json"), "dose_response": jl(RESULTS_DIR / "dose_response.json"),
        "move_vs_flatten": jl(RESULTS_DIR / "move_vs_flatten.json"),
        "screen_verdict": jl(RESULTS_DIR / "screen_verdict.json"),
        "preregistration": jl(RESULTS_DIR / "preregistration.json"),
        "audit": {"rederivation": jl(RESULTS_DIR / "audit_rederivation.json"),
                  "commitment_exact_permutation": jl(RESULTS_DIR / "audit_commitment_perm.json"),
                  "note": "headline numbers re-derived from data/raw + label files through a separate code path; "
                          "the pre-registered paraphrase-split null band of the commitment test is anti-conservative "
                          "(exact permutation p = 0.007-0.025 instead of 0.0005); per-sample labels not re-derived"},
        "openrouter_cost_usd": round(cost, 4),
        "timing": {"n_timing_rows": len(timing), "rows": timing[-40:]},
        "example_format": "output = label of the unsteered HF sample in the slot; predict_<arm> = '<label>|pass|fail'",
    }
    out = {"metadata": meta, "datasets": datasets}
    (WS / "method_out.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"method_out.json: {sum(len(d['examples']) for d in datasets)} examples")


if __name__ == "__main__":
    main()
