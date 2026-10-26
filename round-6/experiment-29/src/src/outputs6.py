#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema): one example per CRN slot and cell, predict_<engine> = 'label|pass'.

datasets:
  engine_pop      (task, direction, alpha 2, template, k): output = engine a (iteration-4 FP8 engine) 'label|pass'
  engine_twins    (task, template, k < 10) twin slots
  engine_pn       (task, PN_a1/PN_a2, template, k): exp19 per-sample plan-noise slots
  engine_posctrl  (T2, direction 9004, alpha 1, template, k 0-3)
  engine_summary  one example per task: E per engine (predict_<e> = 'E_confirmed|E_screen'), output = literal verdict
metadata: every analysis table (verdict trace, E, McNemar, PN, REPRO, B-sensitivity, diagnostics, landings, relabel
table), deviations, costs, timing, hardware and the commitment chain.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import COMMIT_LOG, DATA, PRED, RESULTS, ROOT, V22, read_json, read_jsonl, utc_now, write_json  # noqa: E402

ENGS = ("a", "b", "c", "d")


def prompt_text(task: str, w: str, cache: dict) -> str:
    if not cache:
        for p in read_jsonl(V22 / "prompts" / "prompts4.jsonl"):
            if p["kind"] == "twin":
                cache[(p["task"], p["template_id"])] = p["user_text"]
    return cache[(task, w)]


def lab(r: dict[str, Any]) -> str:
    return f"{r['label']}|{'pass' if r['passed'] else 'fail'}"


def build() -> dict[str, Any]:
    rows = read_jsonl(DATA / "samples.jsonl")
    by: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r["engine"] not in ENGS:
            continue
        by[(r["task"], r["arm"], r["template"], int(r["sample_id"]))][r["engine"]] = r
    esc = read_json(RESULTS / "escape_by_engine.json")
    pc: dict = {}
    ds: dict[str, list] = {"engine_pop": [], "engine_twins": [], "engine_pn": [], "engine_posctrl": []}
    for (t, arm, w, k), m in sorted(by.items()):
        ref = m.get("a")
        any_r = ref or next(iter(m.values()))
        fam = any_r["family"]
        if fam == "TWIN" and k >= 10:
            continue
        ex: dict[str, Any] = {
            "input": (f"[{t} | {arm} | template {w} | CRN slot k={k}] Qwen3-8B prompt (thinking off, T=1.0, "
                      f"inverse-CDF CRN draw u_stream({t},{w},{k})): " + prompt_text(t, w, pc)),
            "output": lab(ref) if ref else "n/a (engine a not run on this slot)",
            "metadata_task": t, "metadata_arm": arm, "metadata_template": w, "metadata_k": k,
            "metadata_family": fam, "metadata_alpha": any_r.get("alpha"),
            "metadata_direction_seed": any_r.get("direction_seed"),
            "metadata_phase": ("twin" if fam == "TWIN" else ("pn" if fam == "PN" else
                                                            ("screen" if k in (0, 1) else "confirm"))),
            "metadata_engine_a_source": ref["source"] if ref else None,
        }
        for e in ENGS:
            if e in m:
                ex[f"predict_{e}"] = lab(m[e])
        if fam == "POP" and any_r.get("direction_seed") != 9004:
            s = str(any_r["direction_seed"])
            for e in ENGS:
                c = esc.get(e, {}).get(t, {}).get("alpha", {}).get(str(float(any_r["alpha"])), {}) \
                    .get("per_direction", {}).get(s)
                if c is not None:
                    ex[f"metadata_escape_{e}"] = {"screen": c["screen"], "confirmed": c["confirmed"],
                                                  "share10": c["share10"]}
            ds["engine_pop"].append(ex)
        elif fam == "POP":
            ds["engine_posctrl"].append(ex)
        elif fam == "TWIN":
            ds["engine_twins"].append(ex)
        elif fam == "PN":
            ds["engine_pn"].append(ex)
    ver = read_json(RESULTS / "verdict.json")
    summ = []
    for t in ("T10", "T2"):
        v = ver[t]
        ex = {"input": f"{t}: escape fraction of the 40 fixed random pushes (seeds 9101-9140, alpha 2, absolute unit) "
                       f"per engine under exp22's two-stage rule; which numerics carry iteration 4's escapes?",
              "output": v["literal_verdict"], "metadata_E_iter4_relabelled_a": v["E_iter4_relabelled_a"],
              "metadata_screen_level_verdict": v["screen_level_verdict"],
              "metadata_feasibility_reading": v.get("feasibility_reading")}
        for e in ENGS:
            ex[f"predict_{e}"] = f"E={v['E_alpha2'][e]}|E_screen={v['E_screen_alpha2'][e]}"
        summ.append(ex)
    datasets = [{"dataset": k, "examples": v} for k, v in ds.items() if v]
    datasets.append({"dataset": "engine_summary", "examples": summ})
    meta: dict[str, Any] = {
        "method_name": "FP8 engine factorial for iteration-4 random plan-site pushes (Qwen3-8B)",
        "description": "Iteration 4's 40 fixed random directions, its CRN slots, twin prompts and absolute "
                       "per-block per-position displacement n[l,p], re-run under four numerics from one bf16 "
                       "snapshot: a W8A8 (iteration-4 engine, native torch._scaled_mm, byte-identical to exp22), b W8A16, "
                       "c W16A8, d BF16. Escape fraction per engine under exp22's two-stage rule, each engine against "
                       "its own twin; PN on exp19's slots; teacher-forced diagnostics.",
        "utc": utc_now(), "baseline": "engine d (bf16, the full-precision reference) and engine a (iteration-4 engine)",
        "commitments": [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()],
    }
    for name in ("verdict", "escape_by_engine", "mcnemar", "pn", "repro", "repro_bytes", "bsens", "landings",
                 "diagnostics_summary", "gpu_b2_log", "gpu_q3_log", "validity", "known_solutions", "slot_flips",
                 "relabel_table", "engine_check_exp27", "cpu_gates", "unit_tests_q", "unit_tests_b", "unit_tests_q2",
                 "w8a16_impl", "diagnostics_B", "diagnostics_Q", "rederive", "deviations", "costs", "timing_summary",
                 "gpu_b_log", "gpu_q2_log", "relabel_iter4", "analysis_run"):
        p = RESULTS / f"{name}.json"
        if p.exists():
            d = read_json(p)
            if name == "relabel_iter4":
                d = {k: v for k, v in d.items() if k != "changed_rows"}
            if name == "escape_by_engine":
                d = {e: {t: {"twin": v["twin"], "posctrl_9004_a1": v.get("posctrl_9004_a1"),
                             "alpha": {a: {k: x for k, x in av.items() if k != "per_direction"}
                                       for a, av in v["alpha"].items()}} for t, v in d[e].items()} for e in d}
            meta[name] = d
    for name in ("hardware", "commit0"):
        p = PRED / f"{name}.json"
        if p.exists():
            meta[f"predictions_{name}"] = read_json(p)
    return {"metadata": meta, "datasets": datasets}


def main() -> None:
    out = build()
    write_json(ROOT / "method_out.json", out)
    print({d["dataset"]: len(d["examples"]) for d in out["datasets"]})


if __name__ == "__main__":
    main()
