#!/usr/bin/env python3
"""S8: method_out.json in the exp_gen_sol_out schema.

Datasets (one example per CRN slot; output = the neutral twin's label at that slot, predict_<arm> = 'label|pass'):
  c2a_population   per (task, direction, slot) of the 6 movable tasks: predict_pop_a1, predict_pop_a2
  escape_9task     per (task, direction, slot) of the 9 other tasks: predict_pop_a1, predict_pop_a2
  decomposition    per (task, direction, slot k 0-3): predict_orig, predict_uperp, predict_up, predict_clamp
  targeted         per (task, slot): predict_c2c_r_s0_25 ... predict_sweep_a8 (C2c and sweep arms)
  c3b_events       per gated iteration-3 ban event: output = realised landing; predict_<family> = forecast (JSON)
metadata: every headline analysis, deviations, timing, costs, not-run list and the commitment-chain check.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "src"))

import cfg4  # noqa: E402,F401
from cfg4 import (COMMIT_LOG, DEFAULT4, MOVABLE, OTHER9, PRED_DIR, RESULTS_DIR, SEEDS_C2C, read_json,  # noqa: E402
                  read_jsonl, write_json)
from run_all import load_rows  # noqa: E402


def lp(r: dict[str, Any] | None) -> str:
    return "unsampled" if r is None else f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


def main() -> None:
    rows = load_rows()
    from prompts4 import load_prompts4
    pr = load_prompts4()
    slot = {(r["task"], r["arm"], r["template"], int(r["sample_id"])): r for r in rows}
    twin = {(t, w, k): r for (t, a, w, k), r in slot.items() if a == "TWIN"}

    def inp(t: str, w: str, extra: str) -> str:
        return (f"[{t} | template {w} | {extra}] " + pr[f"{t}|twin|-|{w}|-"]["user_text"])

    datasets = []
    for name, tasks in (("c2a_population", MOVABLE), ("escape_9task", OTHER9)):
        ex = []
        keys = sorted({(r["task"], r["direction_seed"], r["template"], int(r["sample_id"])) for r in rows
                       if r["family"] == "POP" and r["task"] in tasks})
        for (t, s, w, k) in keys:
            tw = twin.get((t, w, k))
            ex.append({"input": inp(t, w, f"random direction {s}, task-spec positions, blocks 12-23, slot k={k}"),
                       "output": lp(tw) if tw else "twin_slot_unsampled",
                       "predict_pop_a1": lp(slot.get((t, f"POP_d{s}_a1.0", w, k))),
                       "predict_pop_a2": lp(slot.get((t, f"POP_d{s}_a2.0", w, k))),
                       "metadata_task": t, "metadata_direction_seed": s, "metadata_template": w, "metadata_slot": k,
                       "metadata_default": DEFAULT4[t]})
        if ex:
            datasets.append({"dataset": name, "examples": ex})
    dl = read_json(PRED_DIR / "decomp_list.json")["list"] if (PRED_DIR / "decomp_list.json").exists() else {}
    ex = []
    for t, lst in dl.items():
        for c in lst:
            s, a = c["seed"], c["alpha"]
            for w in ("W1", "W2", "W3", "W4", "W5"):
                for k in range(4):
                    tw = twin.get((t, w, k))
                    ex.append({"input": inp(t, w, f"decomposition of direction {s} at alpha {a}, slot k={k}"),
                               "output": lp(tw) if tw else "twin_slot_unsampled",
                               "predict_orig": lp(slot.get((t, f"POP_d{s}_a{a}", w, k))),
                               "predict_uperp": lp(slot.get((t, f"UPERP_d{s}_a{a}", w, k))),
                               "predict_up": lp(slot.get((t, f"UP_d{s}_a{a}", w, k))),
                               "predict_clamp": lp(slot.get((t, f"CLAMP_d{s}_a{a}", w, k))),
                               "metadata_task": t, "metadata_direction_seed": s, "metadata_alpha": a,
                               "metadata_template": w, "metadata_slot": k})
    if ex:
        datasets.append({"dataset": "decomposition", "examples": ex})
    ex = []
    for t in MOVABLE:
        arms = {"predict_c2c_r_s0_25": "C2C_r_s0.25", "predict_c2c_r_s0_5": "C2C_r_s0.5",
                "predict_c2c_r_s1_0": "C2C_r_s1.0", "predict_c2c_random_s0_5": f"C2C_rand{SEEDS_C2C[t]}_s0.5",
                "predict_c2c_masked_s0_5": "C2C_rm_s0.5", "predict_c2c_r2_s0_5": "C2C_r2_s0.5",
                "predict_sweep_a4": "SWEEP_r_a4.0", "predict_sweep_a8": "SWEEP_r_a8.0"}
        for w in ("W1", "W2", "W3", "W4", "W5"):
            for k in range(10):
                if not any((t, a, w, k) in slot for a in arms.values()):
                    continue
                tw = twin.get((t, w, k))
                e = {"input": inp(t, w, f"targeted default->runner-up pushes, slot k={k}"),
                     "output": lp(tw) if tw else "twin_slot_unsampled", "metadata_task": t, "metadata_template": w,
                     "metadata_slot": k}
                for pk, a in arms.items():
                    e[pk] = lp(slot.get((t, a, w, k)))
                ex.append(e)
    if ex:
        datasets.append({"dataset": "targeted", "examples": ex})
    c3b = read_json(RESULTS_DIR / "c3b.json") if (RESULTS_DIR / "c3b.json").exists() else None
    if c3b:
        ex = []
        ev13 = {e["task"]: e for e in read_jsonl(ROOT / "inputs/exp13/results/c1_events.jsonl")}
        for t, r in c3b["events"].items():
            e = {"input": f"Iteration-3 modal ban of {r['banned']} on {t}: where do the non-banned attempts land?",
                 "output": json.dumps(ev13[t]["landing_counts"]), "metadata_task": t,
                 "metadata_gate_pass": r["gate_pass"], "metadata_logscore": r["logscore"]}
            for fam, top in r["forecast_top1"].items():
                e[f"predict_{fam.lower()}"] = str(top)
            ex.append(e)
        datasets.append({"dataset": "c3b_events", "examples": ex})
    meta: dict[str, Any] = {"method_name": "plan-subspace projection vs random plan-site pushes (Qwen3-8B)",
                            "model": "Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218, FP8 W8A8",
                            "description": "See README.md; every number here is recomputed by audit/rederive.py."}
    for name in ("c2a", "escape", "decomposition", "c2c", "c2b", "c3b", "geometry", "novelty", "engine_check",
                 "unit_tests_gpu", "tests_cpu", "labeller_recheck", "units", "deviations", "phase2_log",
                 "budget_decision", "rederive", "rederive_extra", "costs"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            v = read_json(p)
            if name == "c2a":
                v = {"verdict": v.get("verdict"), "pooled_within_task_rho": v.get("pooled_within_task_rho"),
                     "predictor_summary": v.get("predictor_summary"),
                     "per_task": {t: {k: x for k, x in r.items() if k != "direction_table"}
                                  for t, r in v.get("per_task", {}).items()}}
            if name == "geometry":
                v = {t: {b: {k: x for k, x in g.get(b, {}).items() if k != "embedding_k10"} for b in ("18", "23")}
                     | {"implemented_counts": g.get("implemented_counts")} for t, g in v.get("tasks", {}).items()}
            if name == "novelty":
                v = {k: x for k, x in v.items() if k != "items"}
            if name == "c2b":
                v = {k: x for k, x in v.items() if k != "table"}
            meta[name] = v
    if COMMIT_LOG.exists():
        from commit4 import verify
        meta["commitments"] = verify()
    write_json(ROOT / "method_out.json", {"metadata": meta, "datasets": datasets})
    print({d["dataset"]: len(d["examples"]) for d in datasets})


if __name__ == "__main__":
    main()
