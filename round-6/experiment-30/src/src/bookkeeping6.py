#!/usr/bin/env python3
"""Bookkeeping (CPU): STEP 0 availability gate (results/inputs_available.json), CPU tests (results/tests_cpu.json:
statistics, prompt-pair id asserts, seed determinism, log-score rule, labeller re-check on reference programs), seed
collisions with every earlier seed list (results/seed_collisions.json), dependency usage, timing and costs."""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, sha256_file, utc_now, write_json
from cfg6 import DEFAULT6, EXP, EXP_ORIG, PROMPTS6, SAMPLES, SLOT_MAP, TASKS6, dir_seed
import stats6 as S

BUILDS_ON = {
    "ITER4/exp19/src": EXP_ORIG[19] / "src", "ITER4/exp20/src": EXP_ORIG[20] / "src",
    "ITER4/exp20/directions/u_top5.npz": EXP_ORIG[20] / "directions" / "u_top5.npz",
    "ITER4/exp20/directions/plan_geometry_T1.npz": EXP_ORIG[20] / "directions" / "plan_geometry_T1.npz",
    "ITER4/exp20/results/pooled_model.json": EXP_ORIG[20] / "results" / "pooled_model.json",
    "ITER4/exp20/units/units_sha256.json": EXP_ORIG[20] / "units" / "units_sha256.json",
    "ITER4/exp22/results/escape.json": EXP_ORIG[22] / "results" / "escape.json",
    "ITER4/exp22/predictions/c2_commit.json": EXP_ORIG[22] / "predictions" / "c2_commit.json",
    "ITER4/exp23/results/qwen_ratio.json": EXP_ORIG[23] / "results" / "qwen_ratio.json",
    "ITER5/exp25/newbench/A3_trapping_rain_water": EXP_ORIG[25] / "newbench" / "A3_trapping_rain_water",
    "ITER5/exp25/results/extra_arm_a.json": EXP_ORIG[25] / "results" / "extra_arm_a.json",
    "ITER5/exp25/pooled_inputs.json": EXP_ORIG[25] / "pooled_inputs.json",
    "ITER5/exp26/units/B3": EXP_ORIG[26] / "units" / "B3", "ITER5/exp26/pooled_inputs.json": EXP_ORIG[26] / "pooled_inputs.json",
    "ITER5/exp27/src": EXP_ORIG[27] / "src", "ITER5/exp27/results/cells.json": EXP_ORIG[27] / "results" / "cells.json",
    "ITER5/exp27/results/defaults.json": EXP_ORIG[27] / "results" / "defaults.json",
    "ITER5/exp27/results/unit_ratio.json": EXP_ORIG[27] / "results" / "unit_ratio.json",
    "ITER5/exp27/results/pn_vs_dmd.json": EXP_ORIG[27] / "results" / "pn_vs_dmd.json",
    "ITER5/exp27/predictions/dmd_temperatures.json": EXP_ORIG[27] / "predictions" / "dmd_temperatures.json",
    "ITER5/exp28/results/predictors.json": EXP_ORIG[28] / "results" / "predictors.json",
    "ITER5/exp28/results/e_a2.json": EXP_ORIG[28] / "results" / "e_a2.json",
    "ITER5/exp28/src/regate_rules.py": EXP_ORIG[28] / "src" / "regate_rules.py",
    "ITER2/exp8/engine.py": EXP_ORIG[8] / "engine.py", "ITER2/exp8/suite": EXP_ORIG[8] / "suite",
    "ITER2/exp11/bench": EXP_ORIG[11] / "bench", "ITER2/exp7/frozen/templates_nouns_padding.json":
        EXP_ORIG[7] / "frozen" / "templates_nouns_padding.json",
    "ITER3/exp13/src": EXP_ORIG[13] / "src", "ITER3/exp16/src": EXP_ORIG[16] / "src",
    "ITER3/exp18/results/known_solutions_summary.json": EXP_ORIG[18] / "results" / "known_solutions_summary.json",
}


def inputs_available() -> dict[str, Any]:
    out = {k: {"exists": p.exists()} for k, p in BUILDS_ON.items()}
    out["_copies"] = {"inputs/ (byte copy of exp27 inputs/, SHA256SUMS)": sha256_file(INPUTS / "SHA256SUMS"),
                      "inputs_extra/": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                                        sorted((ROOT / "inputs_extra").rglob("*")) if p.is_file()}}
    out["_missing"] = [k for k, v in out.items() if isinstance(v, dict) and v.get("exists") is False]
    out["_bench_commitment_check"] = bench_commitment()
    write_json(RESULTS_DIR / "inputs_available.json", out)
    return out


def bench_commitment() -> dict[str, Any]:
    c = INPUTS / "exp11" / "bench" / "commitment.json"
    if not c.exists():
        return {"error": "no commitment.json"}
    com = read_json(c)
    files = com.get("files") or com.get("sha256") or {}
    bad, n = [], 0
    if isinstance(files, dict):
        for rel, h in files.items():
            p = INPUTS / "exp11" / "bench" / rel
            if p.exists() and isinstance(h, str):
                n += 1
                if sha256_file(p) != h:
                    bad.append(rel)
    return {"n_checked": n, "mismatches": bad[:20], "n_mismatch": len(bad)}


def labeller_recheck() -> dict[str, Any]:
    """Run the frozen labellers on each bench task's reference programs: each reference must get its own mode."""
    import label_worker_v4 as LW

    rows = []
    for t in ("T03", "T10", "T05", "T06"):
        d = next(x for x in (INPUTS / "exp11" / "bench").iterdir() if x.name.startswith(t + "_"))
        for f in sorted((d / "references").glob("*.py")):
            rows.append({"task": t, "arm": "REFCHECK", "template": "W1", "slot": 0,
                         "sample_id": f"{t}|REF|{f.stem}", "text": f"```python\n{f.read_text()}\n```",
                         "finish_reason": "stop", "u_seed": 0, "ref_mode": f.stem})
    for t, dname in (("T1", "t1_grid"), ("T2", "t2_wsp")):
        for f in sorted((INPUTS / "exp8" / "suite" / "tasks" / dname / "references").glob("*.py")):
            rows.append({"task": t, "arm": "REFCHECK", "template": "W1", "slot": 0, "sample_id": f"{t}|REF|{f.stem}",
                         "text": f"```python\n{f.read_text()}\n```", "finish_reason": "stop", "u_seed": 0,
                         "ref_mode": f.stem})
    labs = {l["sample_id"]: l for l in LW.label_rows(rows, use_judge=False)}
    out = {}
    for r in rows:
        l = labs[r["sample_id"]]
        out[r["sample_id"]] = {"label": l["label"], "passed": l.get("passed"), "ref_mode": r["ref_mode"],
                               "runtime_label": l.get("runtime_label"), "ast_label": l.get("ast_label")}
    ok_b = [v for k, v in out.items() if not k.startswith("T1|") and not k.startswith("T2|")]
    agree = sum(v["label"] == v["ref_mode"] for v in ok_b)
    return {"rows": out, "bench_reference_label_agreement": [agree, len(ok_b)],
            "all_pass_tests": all(v["passed"] for v in out.values()),
            "note": "path references carry implementation suffixes (e.g. bfs_deque_parent); their labels are listed"}


def prompt_asserts() -> dict[str, Any]:
    P = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(PROMPTS6)}
    bad = []
    for (t, w, k), r in P.items():
        if k in ("ban", "placebo"):
            tw = P[(t, w, "twin")]
            if not (len(r["ids"]) == len(tw["ids"]) and r["ids"][r["p1"]:] == tw["ids"][tw["p1"]:]):
                bad.append(f"{t}|{w}|{k}")
    return {"n_pairs": sum(1 for k in P if k[2] in ("ban", "placebo")), "violations": bad, "pass": not bad}


def seed_collisions() -> dict[str, Any]:
    mine = set()
    for r in read_jsonl(SAMPLES):
        if r.get("dir_seed") is not None:
            mine.add(int(r["dir_seed"]))
        rec = r.get("realised") or {}
        if rec.get("dir_seed") is not None:
            mine.add(int(rec["dir_seed"]))
    earlier = set()
    srcs = [EXP[22] / "predictions" / "c2_commit.json", EXP[20] / "results" / "c1_site.json",
            EXP[27] / "results" / "seed_collisions.json", EXP[28] / "predictions" / "commit_E1.json"]
    for p in srcs:
        if p.exists():
            for m in re.finditer(r"\b(\d{4,12})\b", p.read_text()):
                earlier.add(int(m.group(1)))
    earlier |= set(range(52001, 52017)) | set(range(9101, 9141)) | set(range(95101, 95109))
    col = sorted(mine & earlier)
    d2 = dir_seed("T03", "S0", 1.0, 0)
    out = {"n_dir_seeds": len(mine), "n_earlier_numbers": len(earlier), "collisions": col[:50],
           "n_collisions": len(col), "deterministic": d2 == dir_seed("T03", "S0", 1.0, 0),
           "sources": [str(p.relative_to(p.parents[3])) for p in srcs if p.exists()]}
    write_json(RESULTS_DIR / "seed_collisions.json", out)
    return out


def tests_cpu() -> dict[str, Any]:
    out = {"stats": S.run_tests(), "prompt_pairs": prompt_asserts()}
    from lcontest import logscore, mix
    q = mix({"a": 3, "b": 1}, ["a", "b"])
    # hand computation: p = (0.75, 0.25, 0) -> 0.95 * p + 0.05 / 3; other floored at 0.02, renormalised
    raw = {"a": 0.95 * 0.75 + 0.05 / 3, "b": 0.95 * 0.25 + 0.05 / 3, "other": max(0.05 / 3, 0.02)}
    s = sum(raw.values())
    ref = {k: v / s for k, v in raw.items()}
    out["logscore_rule"] = {"q": q, "ref": ref, "pass": all(abs(q[k] - ref[k]) < 1e-12 for k in ref),
                            "logscore_a": logscore(q, {"a": 1}), "ref_logscore_a": math.log(ref["a"])}
    try:
        out["labeller_recheck"] = labeller_recheck()
    except Exception as e:  # noqa: BLE001 - reported, not hidden
        out["labeller_recheck"] = {"error": str(e)[:300]}
    out["all_pass"] = bool(out["stats"]["all_pass"] and out["prompt_pairs"]["pass"] and out["logscore_rule"]["pass"])
    write_json(RESULTS_DIR / "tests_cpu.json", out)
    return out


def timing_costs() -> None:
    tb = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    by = Counter()
    rows = Counter()
    for b in tb:
        by[b["tag"].split(":")[0]] += b["seconds"]
        rows[b["tag"].split(":")[0]] += b.get("n_real", 0)
    write_json(RESULTS_DIR / "timing_summary.json", {"gpu_seconds_by_stage": dict(by), "rows_by_stage": dict(rows),
                                                     "gpu_seconds_total": sum(by.values()),
                                                     "seconds_per_row": {k: by[k] / rows[k] for k in by if rows[k]},
                                                     "n_batches": len(tb), "utc": utc_now()})
    cost = {}
    for name in ("openrouter_cost_paths.json",):
        p = RESULTS_DIR / name
        if p.exists():
            cost[name] = read_json(p)
    na = RESULTS_DIR / "novelty_audit.json"
    if na.exists():
        cost["novelty_audit_usd"] = read_json(na).get("cost_usd")
    jc = ROOT / "logs"
    cost["note"] = "bench judge spend is logged by bench.common.judge in logs/; path judge spend in the file above"
    write_json(RESULTS_DIR / "costs.json", cost)


def dependency_usage() -> None:
    d = read_json(ROOT / "data" / "dep_extract.json")
    write_json(RESULTS_DIR / "dependency_usage.json", {"dataset": "art_j3Rm_lr2nzR6", "counts": d["counts"],
                                                       "usage": d["usage"],
                                                       "n_single_token_nouns": d["n_noun_bank_single_token"],
                                                       "n_known_solution_corpus": len(d["known_solution_corpus"]),
                                                       "llm_creativity_T02_labels": d["llm_creativity_T02_labels"]})


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("bookkeeping6")
    which = sys.argv[1].split(",") if len(sys.argv) > 1 else ["inputs", "tests", "seeds", "timing", "deps"]
    if "inputs" in which:
        logger.info(f"inputs missing: {inputs_available()['_missing']}")
    if "tests" in which:
        t = tests_cpu()
        logger.info(f"tests_cpu all_pass={t['all_pass']}; labeller {t['labeller_recheck'].get('bench_reference_label_agreement')}")
    if "seeds" in which:
        logger.info(f"seed collisions: {seed_collisions()['n_collisions']}")
    if "timing" in which:
        timing_costs()
    if "deps" in which:
        dependency_usage()


if __name__ == "__main__":
    main()
