#!/usr/bin/env python3
"""Final labels (dispute judge), OOC screen, sample assembly, analysis and outputs.

stage_label   : for every labelled row (correct programs + the 10% QA sample of incorrect ones) combine runtime and
                AST labels; disputes go to the blind label judge (google/gemini-2.5-flash-lite, cap USD 0.5); then
                OOC_screen = correct AND (label == 'other' OR s < s*_task) -> data/labels_final.jsonl.
build_samples : rows + final labels + adjudication fields -> data/samples.jsonl (protocol fields).
stage_analyse : src/analysis.py (committed at #0) over data/samples.jsonl -> results/*.json, verdict.json.
stage_outputs : figures, method_out.json (exp_gen_sol_out), audit/rederive.py check.
"""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from typing import Any

from loguru import logger

from common import (CAP_USD, DATA, PRED, RESULTS, TASKS, read_json, read_jsonl, utc_now, write_json, write_jsonl)

LABELS_FINAL = DATA / "labels_final.jsonl"


def all_rows(include_l: bool = True) -> list[dict[str, Any]]:
    rows = []
    for t in TASKS:
        rows += read_jsonl(DATA / f"rows_{t}.jsonl")
    if include_l:
        rows += read_jsonl(DATA / "rows_L.jsonl")
    return rows


def stage_label() -> None:
    from inputs import load_task
    from labels import combine, needs_judge
    from orclient import ORClient, label_disputes
    plan = read_json(PRED / "commit1.json")
    sstar = {t: v["s_star"] for t, v in plan["s_star"].items()}
    rows = all_rows()
    prev = {r["id"]: r for r in read_jsonl(LABELS_FINAL)}
    objs = {t: load_task(t) for t in TASKS}
    disputes: dict[str, dict[str, str]] = defaultdict(dict)
    for r in rows:
        if r.get("runtime_label") is None or r["id"] in prev and prev[r["id"]].get("judge_label") is not None:
            continue
        if needs_judge(r["runtime_label"], r.get("ast_label") or "unknown") and r.get("code"):
            disputes[r["task"]][r["code_sha256"]] = r["code"]
    judged: dict[str, dict[str, str | None]] = {t: {} for t in TASKS}
    for p in prev.values():
        if p.get("judge_label") is not None:
            judged[p["task"]][p["code_sha256"]] = p["judge_label"]
    client = ORClient("label_disputes", CAP_USD["label_disputes"], concurrency=16)
    for t, items in disputes.items():
        todo = [(sha, code) for sha, code in items.items() if sha not in judged[t]]
        if not todo:
            continue
        logger.info(f"label disputes {t}: {len(todo)} programs to judge (spent so far ${client.spent:.3f})")
        res = asyncio.run(label_disputes(objs[t], todo, client))
        judged[t].update(res)
        if client.stop:
            logger.warning(f"label judge stopped: {client.stop_reason}; remaining disputes fall back to runtime label")
            break
    out = []
    for r in rows:
        if r.get("runtime_label") is None:
            lab, src, jl = ("invalid" if not r.get("valid") else None), ("not_labelled" if r.get("valid") else
                                                                         "invalid"), None
        else:
            jl = judged[r["task"]].get(r["code_sha256"]) if needs_judge(r["runtime_label"], r.get("ast_label")
                                                                        or "unknown") else None
            lab, src = combine(r["runtime_label"], r.get("ast_label") or "unknown", jl)
        ooc = bool(r.get("correct")) and (lab == "other" or (r.get("nearest_known_sim") is not None and
                                                            r["nearest_known_sim"] < sstar[r["task"]]))
        out.append({"id": r["id"], "task": r["task"], "arm": r["arm"], "code_sha256": r.get("code_sha256"),
                    "label": lab, "labeller_source": src, "judge_label": jl, "ooc_screen": ooc,
                    "ooc_reason": ("label_other" if lab == "other" else "s_below_sstar") if ooc else None})
    write_jsonl(LABELS_FINAL, out)
    c = Counter((x["task"], x["arm"], x["ooc_screen"]) for x in out)
    logger.info(f"labels: {len(out)} rows; label judge spent ${client.spent:.3f}; OOC per task/arm: " +
                ", ".join(f"{t}/{a}:{c[(t, a, True)]}" for t in TASKS for a in ("S", "NE", "I0", "EAP", "BINT", "B0", "L")
                          if c[(t, a, True)] or c[(t, a, False)]))
    write_json(RESULTS / "label_judge_cost.json", {"usd": client.spent, "stop": client.stop_reason,
                                                   "n_disputes": {t: len(v) for t, v in disputes.items()}})


PROTOCOL_KEYS = ("model", "task", "arm", "site", "layer", "rank_k", "lambda", "alpha", "direction_seed", "template",
                 "noun", "slot", "temperature", "top_k", "precision", "gpu", "prompt_sha256", "label",
                 "labeller_source", "passed", "n_new_tokens", "realised_disp", "code_sha256", "code")
EXTRA_KEYS = ("id", "island", "round", "parent_ids", "depth", "cell", "ds_signature", "valid", "stage1", "stage2",
              "stress_pass", "correct", "runtime_label", "ast_label", "judge_label", "runtime_ratio", "median_case_ms",
              "nearest_known_id", "nearest_known_sim", "nearest_known_dataset", "ast_dist", "novelty", "ooc_screen",
              "ooc_reason", "distinct_id", "is_first_of_distinct", "cluster_id", "merged_cluster_id", "final_class",
              "named_algorithm", "gpu_seconds", "usd", "idea", "intent", "eap_item", "finish_reason", "first_fail",
              "prompt_source", "seed", "default_label", "utc")


def build_samples() -> list[dict[str, Any]]:
    from inputs import load_task
    rows = all_rows()
    labs = {x["id"]: x for x in read_jsonl(LABELS_FINAL)}
    adj = read_json(RESULTS / "program_classes.json") if (RESULTS / "program_classes.json").exists() else {}
    defaults = {t: load_task(t)["default"] for t in TASKS}
    out = []
    for r in rows:
        l = labs.get(r["id"], {})
        a = adj.get(r["id"], {})
        rec = {k: r.get(k) for k in PROTOCOL_KEYS + EXTRA_KEYS}
        rec.update({"label": l.get("label"), "labeller_source": l.get("labeller_source"),
                    "judge_label": l.get("judge_label"), "ooc_screen": bool(l.get("ooc_screen")),
                    "ooc_reason": l.get("ooc_reason"), "distinct_id": a.get("distinct_id"),
                    "is_first_of_distinct": a.get("is_first_of_distinct", False), "cluster_id": a.get("cluster_id"),
                    "merged_cluster_id": a.get("merged_cluster_id"), "final_class": a.get("final_class"),
                    "named_algorithm": a.get("named_algorithm"), "default_label": defaults[r["task"]],
                    "passed": bool(r.get("correct"))})
        out.append(rec)
    write_jsonl(DATA / "samples.jsonl", out)
    return out


def stage_analyse() -> None:
    import analysis as A
    samples = build_samples()
    decisive = [r for r in samples if r["arm"] in A.ARMS]
    tasks = [t for t in TASKS if any(r["task"] == t and r["arm"] == "S" for r in decisive)]
    archives = {t: read_json(RESULTS / f"archive_{t}.json") for t in tasks if (RESULTS / f"archive_{t}.json").exists()}
    seed_shas = {}
    from common import sha256_text
    for t in tasks:
        sp = DATA / f"seeds_{t}.json"
        seed_shas[t] = {sha256_text(x["code"]) for x in read_json(sp)} if sp.exists() else set()
    res = A.run_all(decisive, tasks, archives, seed_shas)
    # L arm (optional) vs S over its first N_L calls on T03
    l_rows = [r for r in samples if r["arm"] == "L"]
    if l_rows:
        nl = len(l_rows)
        s_first = A.arm_counts(decisive, "T03", "S", max_calls=nl)
        lc = A.arm_counts(samples, "T03", "L")
        res["L_vs_S"] = {"L": lc, "S_first_nl": s_first,
                         "test_a": A.rate_ratio_test(lc["X_a"], lc["N"], s_first["X_a"], s_first["N"]),
                         "test_b": A.rate_ratio_test(lc["X_b"], lc["N"], s_first["X_b"], s_first["N"])}
    curves = {t: {a: A.discovery_curve(decisive, t, a) for a in A.ARMS} for t in tasks}
    curves_c = {t: {a: A.discovery_curve(decisive, t, a, key="cluster_id") for a in A.ARMS} for t in tasks}
    write_json(RESULTS / "arm_rates.json", {"level_a": res["arm_rates"], "level_b": res["arm_rates_b"]})
    write_json(RESULTS / "ratio_tests.json", res["ratio_tests"])
    write_json(RESULTS / "matched_effort.json", res["matched_effort"])
    write_json(RESULTS / "lineage.json", res["lineage"])
    write_json(RESULTS / "dynamics.json", res["dynamics"])
    write_json(RESULTS / "placebo.json", {"arm_shuffle": res["placebo"], "seeds_as_children": res["seeds_check"]})
    write_json(RESULTS / "discovery_curves.json", {"distinct": curves, "clusters": curves_c}, indent=None)
    if "L_vs_S" in res:
        write_json(RESULTS / "L_vs_S.json", res["L_vs_S"])
    # novelty claim
    nov = [r for r in decisive if r.get("final_class") == "NOVEL ALGORITHM"]
    adj_clusters = {(r["task"], r.get("merged_cluster_id") or r.get("cluster_id")) for r in decisive
                    if r.get("final_class")}
    n_corr = Counter((r["task"], r["arm"]) for r in decisive if r.get("correct"))
    claim = {"n_novel_programs": len(nov), "novel_ids": [r["id"] for r in nov],
             "n_adjudicated_clusters": len(adj_clusters),
             "rule_of_three_over_clusters": A.rule_of_three(len(adj_clusters)) if not nov else None,
             "rule_of_three_over_correct_per_arm": {f"{t}|{a}": A.rule_of_three(n) for (t, a), n in n_corr.items()}
             if not nov else None,
             "statement": ("no correct novel algorithm found (0 NOVEL after judges, manual read and dated web check)"
                           if not nov else f"{len(nov)} program(s) with final class NOVEL ALGORITHM: no known "
                                           f"counterpart found by judges, corpus or dated search (not proven novelty)")}
    verdict = {"utc": utc_now(), "prediction": "S >= 10x K on >= 2 tasks (level a)",
               "level_a": {t: {k: v for k, v in res["ratio_tests"]["levels"]["a"]["per_task"][t].items()
                               if k != "secondary"} for t in res["ratio_tests"]["levels"]["a"]["per_task"]},
               "overall_level_a": res["ratio_tests"]["levels"]["a"]["overall"],
               "level_b": {t: {k: v for k, v in res["ratio_tests"]["levels"]["b"]["per_task"][t].items()
                               if k != "secondary"} for t in res["ratio_tests"]["levels"]["b"]["per_task"]},
               "overall_level_b": res["ratio_tests"]["levels"]["b"]["overall"], "novelty_claim": claim}
    write_json(RESULTS / "verdict.json", verdict)
    logger.info(f"verdict: level a {verdict['overall_level_a']}, level b {verdict['overall_level_b']}; "
                f"novel programs {len(nov)}")


def stage_outputs() -> None:
    from outputs import write_outputs
    write_outputs()
