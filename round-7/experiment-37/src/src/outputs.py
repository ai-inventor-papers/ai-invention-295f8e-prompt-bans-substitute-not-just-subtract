#!/usr/bin/env python3
"""STEP 9 - outputs: method_out.json (exp_gen_sol_out), costs.json, throughput.json, figures, audit check.

Datasets of method_out.json:
  search_programs : one example per distinct correct program (task, arm, normalised code): input = task + arm + call
                    index, output = final class (adjudicated) or final label; predict_screen 'OOC|in',
                    predict_judgeA / predict_judgeB (adjudication votes, '' when not adjudicated), predict_final.
  adjudication    : one example per judged candidate (cluster medoids + extras) and per control.
  arm_summary     : one example per task x arm with the counts behind the tests.
metadata = verdicts, every analysis, deviations, commitments, costs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from typing import Any

from loguru import logger

from common import (AUDIT, DATA, PRED, RESULTS, ROOT, read_json, read_jsonl, utc_now, verify_chain, write_json)

ARMS = ("S", "NE", "I0", "EAP", "BINT", "B0", "L")


def _j(p) -> Any:
    return read_json(p) if p.exists() else None


def costs() -> dict[str, Any]:
    led = read_jsonl(RESULTS / "openrouter_ledger.jsonl")
    by = Counter()
    n = Counter()
    for r in led:
        by[r["purpose"]] += float(r.get("cost") or 0)
        n[r["purpose"]] += 1
    tp = read_jsonl(RESULTS / "throughput_run.jsonl")
    samples = read_jsonl(DATA / "samples.jsonl")
    gpu = Counter()
    for r in samples:
        gpu[f"{r['task']}|{r['arm']}"] += float(r.get("gpu_seconds") or 0)
    out = {"utc": utc_now(), "openrouter_usd_by_purpose": {k: round(v, 5) for k, v in by.items()},
           "openrouter_calls_by_purpose": dict(n), "openrouter_usd_total": round(sum(by.values()), 5),
           "artifact_cap_usd": 3.5, "gpu_seconds_by_task_arm": {k: round(v, 1) for k, v in gpu.items()},
           "gpu_hours_total_generation": round(sum(gpu.values()) / 3600, 3),
           "engine_rounds": len(tp), "engine_gen_seconds": round(sum(x["gen_s"] for x in tp), 1)}
    write_json(RESULTS / "costs.json", out)
    write_json(RESULTS / "throughput.json", {"pilot": _j(PRED / "throughput_pilot.json"),
                                             "run_rounds": tp[-400:], "n_rounds": len(tp)})
    return out


def method_out(samples: list[dict[str, Any]]) -> dict[str, Any]:
    adj = _j(RESULTS / "adjudication.json") or {"per_candidate": {}, "judges": []}
    judges = adj.get("judges") or adj.get("advisory_pair") or []   # F5: gated pair empty -> advisory pair votes
    ja = judges[0] if judges else None
    jb = judges[1] if len(judges) > 1 else None
    vkey = "votes" if adj.get("judges") else "advisory_votes"
    progs = []
    seen = set()
    for r in samples:
        if not r.get("correct"):
            continue
        key = (r["task"], r["arm"], r.get("code_sha256"))
        if key in seen:
            continue
        seen.add(key)
        votes = (adj["per_candidate"].get(r.get("distinct_id") or "", {}) or {}).get(vkey, {})
        final = r.get("final_class") or r.get("label") or "unlabelled"
        progs.append({
            "input": f"task={r['task']} arm={r['arm']} call={r['slot']}",
            "output": str(final),
            "predict_screen": "OOC" if r.get("ooc_screen") else "in",
            "predict_judgeA": str(votes.get(ja) or "not_judged") if ja else "not_judged",
            "predict_judgeB": str(votes.get(jb) or "not_judged") if jb else "not_judged",
            "predict_final": str(final),
            "metadata_id": r["id"], "metadata_task": r["task"], "metadata_arm": r["arm"],
            "metadata_label": r.get("label"), "metadata_runtime_label": r.get("runtime_label"),
            "metadata_cell": r.get("cell"), "metadata_novelty": r.get("novelty"),
            "metadata_nearest_known_id": r.get("nearest_known_id"),
            "metadata_nearest_known_sim": r.get("nearest_known_sim"),
            "metadata_nearest_known_dataset": r.get("nearest_known_dataset"),
            "metadata_runtime_ratio": r.get("runtime_ratio"), "metadata_island": r.get("island"),
            "metadata_depth": r.get("depth"), "metadata_parent_ids": r.get("parent_ids"),
            "metadata_distinct_id": r.get("distinct_id"), "metadata_cluster_id": r.get("cluster_id"),
            "metadata_named_algorithm": r.get("named_algorithm"), "metadata_idea": r.get("idea"),
            "metadata_code": r.get("code")})
    cands = []
    rowmap = {r["id"]: r for r in samples}
    manual = {m["id"]: m for m in read_jsonl(RESULTS / "manual_reads.jsonl")}
    for i, rec in adj["per_candidate"].items():
        r = rowmap.get(i, {})
        cands.append({"input": f"task={rec['task']} candidate={i}\n" + (r.get("code") or ""),
                      "output": str(r.get("final_class") or rec.get("majority") or "unresolved"),
                      "predict_judgeA": str(rec.get(vkey, {}).get(ja) or "no_answer") if ja else "not_judged",
                      "predict_judgeB": str(rec.get(vkey, {}).get(jb) or "no_answer") if jb else "not_judged",
                      "predict_final": str(r.get("final_class") or rec.get("majority") or "unresolved"),
                      "metadata_judges_gated": bool(adj.get("judges")),
                      "metadata_third_vote": rec["votes"].get(adj.get("third")) if adj.get("third") else None,
                      "metadata_named": rec.get("named"), "metadata_core_ideas": rec.get("core_ideas"),
                      "metadata_arm": r.get("arm"), "metadata_cluster_id": r.get("cluster_id"),
                      "metadata_nearest_known_id": r.get("nearest_known_id"),
                      "metadata_nearest_known_sim": r.get("nearest_known_sim"),
                      "metadata_manual_read": manual.get(i)})
    for c in _j(DATA / "controls.json") or []:
        gate = _j(RESULTS / "judge_gate.json") or {"judges": {}}
        cands.append({"input": f"control={c['cid']} task={c['task']}\n{c['code']}", "output": c["expect"],
                      "predict_judgeA": str((gate["judges"].get(ja, {}).get("calls") or {}).get(c["cid"]) or "no_answer"),
                      "predict_judgeB": str((gate["judges"].get(jb, {}).get("calls") or {}).get(c["cid"]) or "no_answer"),
                      "predict_final": c["expect"], "metadata_kind": "control", "metadata_verified": c["verified"]})
    ar = _j(RESULTS / "arm_rates.json") or {"level_a": {}}
    summ = []
    for t, arms in ar["level_a"].items():
        for a, v in arms.items():
            if not v["N"]:
                continue
            vb = ar["level_b"][t][a]
            summ.append({"input": f"task={t} arm={a}", "output": json.dumps({k: v[k] for k in (
                "N", "correct", "X_a", "rate_a", "clusters_a")} | {"X_b": vb["X_b"], "rate_b": vb["rate_b"]}),
                "predict_rate_a": f"{v['rate_a']:.5f}" if v["rate_a"] is not None else "",
                "predict_rate_b": f"{vb['rate_b']:.5f}" if vb["rate_b"] is not None else "",
                **{f"metadata_{k}": v[k] for k in v}})
    lrows = [r for r in samples if r["arm"] == "L"]
    if lrows and _j(RESULTS / "L_vs_S.json"):
        lv = _j(RESULTS / "L_vs_S.json")["L"]
        summ.append({"input": "task=T03 arm=L", "output": json.dumps({k: lv[k] for k in ("N", "correct", "X_a", "X_b")}),
                     "predict_rate_a": f"{lv['rate_a']:.5f}" if lv["rate_a"] is not None else "",
                     "predict_rate_b": f"{lv['rate_b']:.5f}" if lv["rate_b"] is not None else "",
                     **{f"metadata_{k}": lv[k] for k in lv}})
    commits = [json.loads(x) for x in (ROOT / "commitments.log").read_text().splitlines() if x.strip()]
    meta = {"method_name": "FunSearch/MAP-Elites program search (Qwen3-8B mutator) vs i.i.d. text-knob baselines",
            "description": "Iteration-7 claim N: does an evolutionary search with an evaluator and a novelty critic "
                           "produce correct out-of-catalogue programs >= 10x more often per call than the best "
                           "iteration-5 text knobs? Arms S, NE, I0, EAP, BINT, B0 (+ L) on T03, T2, A3.",
            "verdict": _j(RESULTS / "verdict.json"), "ratio_tests": _j(RESULTS / "ratio_tests.json"),
            "arm_rates": ar, "matched_effort": _j(RESULTS / "matched_effort.json"),
            "lineage": _j(RESULTS / "lineage.json"), "placebo": _j(RESULTS / "placebo.json"),
            "L_vs_S": _j(RESULTS / "L_vs_S.json"), "adjudication_summary": {
                k: adj.get(k) for k in ("judges", "third", "kappa", "n_pairs", "control_accuracy", "spent_usd")},
            "judge_gate": _j(RESULTS / "judge_gate.json"), "commit1": _j(PRED / "commit1.json"),
            "engine_check": _j(RESULTS / "engine_check.json"), "deviations": _j(RESULTS / "deviations.json"),
            "costs": _j(RESULTS / "costs.json"), "corpus": _j(DATA / "corpus" / "summary.json"),
            "mds": _j(RESULTS / "mds.json"), "levelb_rule_check": _j(RESULTS / "levelb_rule_check.json"),
            "propagation_check": _j(RESULTS / "propagation_check.json"), "a3_regate": _j(RESULTS / "a3_regate.json"),
            "advisory_judges": {k: adj.get(k) for k in ("advisory_pair", "advisory_kappa", "advisory_agreement",
                                                         "advisory_class_counts", "final_class_source")},
            "dynamics_summary": {t: {k: v[k] for k in ("final_cells", "final_qd", "resets")}
                                 for t, v in (_j(RESULTS / "dynamics.json") or {}).items()},
            "commitments": commits, "hash_chain": verify_chain(),
            "kept_artifacts_note": "every path is relative to the repository root; all outputs are small text files"}
    return {"metadata": meta, "datasets": [{"dataset": "search_programs", "examples": progs},
                                           {"dataset": "adjudication", "examples": cands or [
                                               {"input": "none", "output": "no candidates"}]},
                                           {"dataset": "arm_summary", "examples": summ}]}


def write_outputs() -> None:
    from figures import make_all
    samples = read_jsonl(DATA / "samples.jsonl")
    costs()
    try:
        make_all()
    except Exception as e:  # noqa: BLE001 - figures never block the outputs
        logger.error(f"figures failed: {e}")
    mo = method_out(samples)
    write_json(ROOT / "method_out.json", mo, indent=None)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in mo['datasets']]}")
    r = subprocess.run([sys.executable, str(AUDIT / "rederive.py")], capture_output=True, text=True, cwd=str(ROOT))
    (AUDIT / "rederive_stdout.txt").write_text(r.stdout + r.stderr)
    logger.info(f"audit/rederive.py exit {r.returncode}: {r.stdout[-400:]}")
