#!/usr/bin/env python3
"""STEP 13 - method_out.json (exp_gen_sol_out schema).

Datasets (one example per CRN slot; predict_* = '<label>|pass' or '<label>|fail'):
- site_grid: slots (task, template, k 0-5); output = twin label|pass; predict_<site>_a<alpha> for S0-S5 at alpha
  1/2/4 and S1E/S2E at alpha 1.
- boundary_alpha8: slots (task, template, k 0-9); output = twin; predict_S0_a8 (+ S0 alpha 1/2/4 where sampled).
- top5_plan: T1 slots k 0-9; output = twin (exp9 K=7 label); predict_TOP5_a<alpha> and predict_PN_S0_a<alpha>.
- engine_check: T03 and T2 slots k 0-9; output = the exp17 screen's label for the same slot and direction;
  predict_ENG_rerun = this artifact's label under the same uniforms, units and direction.
"""

from __future__ import annotations

from typing import Any

from cfg import (DEFAULT, E17, MODEL_ID, MODEL_REVISION, N50_K, N_GRID_K, QUANT, RESULTS_DIR, ROOT, TASKS,
                 TEMPLATE_IDS, read_json, read_jsonl, utc_now, write_json)
from prompts import PROMPTS_FILE


def _lp(r: dict[str, Any] | None, key: str = "label", pkey: str = "passed") -> str:
    if r is None:
        return "not_sampled"
    return f"{r.get(key)}|{'pass' if r.get(pkey) else 'fail'}"


def build(meta: dict[str, Any]) -> dict[str, Any]:
    from analysis import load_rows

    rows = load_rows()
    idx = {(r["task"], r["w"], r["k"], r["arm"]): r for r in rows}
    prompts = {}
    for r in read_jsonl(PROMPTS_FILE):
        if r["kind"] == "twin":
            prompts[(r["task"], r["w"])] = r["user_text"]
    grid = []
    arms = [f"{s}_a{a:g}" for s in ("S0", "S1", "S2", "S3", "S4", "S5") for a in (1, 2, 4)] + ["S1E_a1", "S2E_a1"]
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for k in N_GRID_K:
                tw = idx.get((t, w, k, "TWIN"))
                ex = {"input": f"task={t} template={w} slot k={k} (neutral twin prompt; every arm edits this "
                               f"prompt's states with the slot's shared random direction):\n{prompts[(t, w)]}",
                      "output": _lp(tw), "metadata_task": t, "metadata_template": w, "metadata_k": k,
                      "metadata_default": DEFAULT[t]}
                for a in arms:
                    ex[f"predict_{a.replace('.', 'p')}"] = _lp(idx.get((t, w, k, a)))
                grid.append(ex)
    bnd = []
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for k in N50_K:
                tw = idx.get((t, w, k, "TWIN"))
                ex = {"input": f"task={t} template={w} slot k={k}: S0 (task-spec states, blocks 12-23) pushed at "
                               f"alpha 8 along the slot's random direction", "output": _lp(tw),
                      "metadata_task": t, "metadata_template": w, "metadata_k": k, "metadata_default": DEFAULT[t]}
                for a in ("1", "2", "4", "8"):
                    r = idx.get((t, w, k, f"S0_a{a}"))
                    if r is not None:
                        ex[f"predict_S0_a{a}"] = _lp(r)
                bnd.append(ex)
    top = []
    for w in TEMPLATE_IDS:
        for k in N50_K:
            tw = idx.get(("T1", w, k, "TWIN"))
            ex = {"input": f"task=T1 template={w} slot k={k}: plan-site push along normalise(mean survivor centroid - "
                           f"mean TOP5 centroid) vs fresh random plan noise at the same per-position norm",
                  "output": _lp(tw, "label_k7"), "metadata_task": "T1", "metadata_template": w, "metadata_k": k,
                  "metadata_label_scheme": "exp9 K=7 analysis labeller (dijkstra_unit, jps, biastar -> other)"}
            for a in ("1", "2", "4"):
                ex[f"predict_TOP5_a{a}"] = _lp(idx.get(("T1", w, k, f"TOP5_a{a}")), "label_k7")
                ex[f"predict_PN_S0_a{a}"] = _lp(idx.get(("T1", w, k, f"S0_a{a}")), "label_k7")
                r = idx.get(("T1", w, k, f"TOP5_a{a}"))
                ex[f"metadata_TOP5_a{a}_label_ext"] = r.get("label_ext") if r else None
            top.append(ex)
    scr = {(r["task"], r["template"], r["arm"], int(r["sample_id"])): r for r in read_jsonl(E17 / "data" /
                                                                                         "labels.jsonl")}
    eng = []
    for t, arm, sarm in (("T03", "ENG_r9002_a1", "RAND9002_a1.0"), ("T2", "ENG_r9004_a1", "RAND9004_a1.0")):
        for w in TEMPLATE_IDS:
            for k in N50_K:
                s = scr.get((t, w, sarm, k))
                ex = {"input": f"task={t} template={w} slot k={k}: exp17 fixed random direction {sarm} at alpha 1 "
                               f"(exp17 units, exp17 uniforms), re-run in this artifact's engine",
                      "output": _lp(s), "predict_ENG_rerun": _lp(idx.get((t, w, k, arm))),
                      "predict_TWIN_rerun": _lp(idx.get((t, w, k, "TWIN"))),
                      "metadata_screen_code_sha256": s.get("code_sha256") if s else None,
                      "metadata_rerun_code_sha256": (idx.get((t, w, k, arm)) or {}).get("code_sha256"),
                      "metadata_task": t, "metadata_template": w, "metadata_k": k}
                eng.append(ex)
    return {"metadata": meta, "datasets": [{"dataset": "site_grid", "examples": grid},
                                           {"dataset": "boundary_alpha8", "examples": bnd},
                                           {"dataset": "top5_plan", "examples": top},
                                           {"dataset": "engine_check", "examples": eng}]}


def metadata() -> dict[str, Any]:
    def rj(name: str) -> Any:
        p = RESULTS_DIR / name
        return read_json(p) if p.exists() else None

    from commit import verify

    c1 = rj("c1_site.json") or {}
    return {
        "method_name": "Matched-dose site sweep of isotropic random displacements (C1-site), alpha-8 boundary with "
                       "novelty audit (C3c), top-five plan-site push (C3d)",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "quant": QUANT, "thinking": False,
                  "temperature": 1.0, "top_p": 1.0, "top_k": None, "max_new_tokens": 1024, "stop": "end of turn or "
                  "closing code fence"},
        "conventions": "block l = hidden_states[l+1]; S = [first 'Task:' token, last user token); R = P-1; COND = "
                       "condition sentence; CRN slot = (task, template, k); direction u(t,w,k) shared by all arms",
        "hardware": rj("hardware.json"), "unit_tests_gpu": rj("unit_tests_gpu.json"),
        "unit_tests_cpu": rj("unit_tests_cpu.json"), "engine_check": rj("engine_check.json"),
        "units_crosscheck": rj("units_crosscheck.json"), "screen_sha256": (RESULTS_DIR / "screen.sha256").read_text()
        .strip() if (RESULTS_DIR / "screen.sha256").exists() else None,
        "c1_site": c1, "failure_modes": (rj("failure_modes.json") or {}).get("summary_by_site"),
        "boundary": {k: v for k, v in (rj("boundary.json") or {}).items() if k != "per_task"},
        "c3d": {k: v for k, v in (rj("c3d.json") or {}).items()},
        "novelty_audit": {k: v for k, v in (rj("novelty_audit.json") or {}).items() if k != "records"},
        "transmission": rj("transmission.json"), "pooled_model": rj("pooled_model.json"),
        "overlap_check": rj("overlap_check.json"), "rederive": rj("rederive.json"),
        "deviations": rj("deviations.json"), "timing": rj("timing_summary.json"),
        "costs": {"labeller_paths": rj("openrouter_cost_paths.json"), "k7": rj("openrouter_cost_k7.json"),
                  "audit": rj("openrouter_cost_audit.json")},
        "hash_chain": verify(), "dependency_usage": rj("dependency_usage.json"),
        "figures": sorted(p.name for p in (ROOT / "figures").glob("*.png")), "created_utc": utc_now()}


def main() -> None:
    out = build(metadata())
    write_json(ROOT / "method_out.json", out, indent=None)
    print({d["dataset"]: len(d["examples"]) for d in out["datasets"]})


if __name__ == "__main__":
    main()
