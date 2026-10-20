#!/usr/bin/env python3
"""Descriptive additions outside the committed analysis code (results/supplementary.json):
- ban failures per template and the W4 share of arm-a default rows (plan F5: template-level tables are mandatory);
- the 'other' audit sample: up to 10 arm-a programs labelled 'other' per gated task, with their runtime/AST labels,
  for reading (plan S6: re-audit banned-mechanism programs labelled 'other');
- the dependency dataset (art_j3Rm_lr2nzR6): the bench's neutral nouns checked against concreteness_norms (flagged
  neutral candidates, Qwen3 token counts) and the LeetCode source problem of every bench task (leetcodedataset);
- judge spend and label-source mix; pooled CRN flip counts; generation length per arm."""

from __future__ import annotations

import collections
import json
from typing import Any

import numpy as np
from loguru import logger

from cfg import (BENCH, DATASET_DIR, RESULTS_DIR, ROOT, STAGE_A, TASK_DIR, TEMPLATE_IDS, default_of, read_json,
                 read_jsonl, write_json)

EXCL = ("invalid", "no_code", "disputed")


def dataset_checks() -> dict[str, Any]:
    p = DATASET_DIR / "full_data_out.json"
    if not p.exists():
        return {"status": "dataset not reachable"}
    d = json.loads(p.read_text())
    nouns = {}
    for t in STAGE_A:
        nn = read_json(BENCH / TASK_DIR[t] / "neutral_nouns.json")[default_of(t)]["nouns"]
        nouns[t] = [n["word"] for n in nn]
    want = {w for v in nouns.values() for w in v}
    conc, lc = {}, collections.defaultdict(list)
    for ds in d["datasets"]:
        if ds["dataset"] == "concreteness_norms":
            for ex in ds["examples"]:
                w = ex.get("input") or ex.get("metadata_word")
                if w in want:
                    conc[w] = {k: v for k, v in ex.items() if k.startswith("metadata_")}
        if ds["dataset"] == "leetcodedataset":
            for ex in ds["examples"]:
                bt = ex.get("metadata_bench_task")
                if bt and bt != "None":
                    lc[bt].append({"question_id": ex.get("metadata_question_id"), "slug": ex.get("metadata_task_slug"),
                                   "role": ex.get("metadata_bench_role"),
                                   "n_cases_parsed": ex.get("metadata_n_test_cases_parsed")})
    del d
    found = {w: (w in conc) for w in want}
    return {"neutral_nouns": nouns, "found_in_concreteness_norms": found, "norm_rows": conc,
            "all_found": all(found.values()),
            "leetcode_sources": {TASK_DIR[t]: lc.get(TASK_DIR[t], []) for t in STAGE_A}}


def main() -> dict[str, Any]:
    rows = {}
    for r in read_jsonl(ROOT / "data" / "samples.jsonl"):
        rows[r["uid"]] = r
    rows = list(rows.values())
    gate = read_json(RESULTS_DIR / "gate.json") if (RESULTS_DIR / "gate.json").exists() else {}
    gated = [t for t in STAGE_A if gate.get(t, {}).get("gated")]
    out: dict[str, Any] = {}
    # ban failures per template, W4 share
    fail_by_w = collections.Counter()
    att_by_w = collections.Counter()
    per_task = {}
    for t in STAGE_A:
        a = [r for r in rows if r["task"] == t and r["arm"] == "a" and r["label"] not in EXCL]
        per_task[t] = {w: {"n": sum(r["template"] == w for r in a),
                           "default": sum(r["template"] == w and r["label"] == default_of(t) for r in a)} for w in TEMPLATE_IDS}
        for r in a:
            att_by_w[r["template"]] += 1
            fail_by_w[r["template"]] += int(r["label"] == default_of(t))
    tot = sum(fail_by_w.values())
    out["ban_failures"] = {"per_template_pooled": {w: {"default_rows": fail_by_w[w], "attempted": att_by_w[w],
                                                       "avoidance": 1 - fail_by_w[w] / att_by_w[w] if att_by_w[w] else None}
                                                   for w in TEMPLATE_IDS},
                           "W4_share_of_failures": fail_by_w["W4"] / tot if tot else None, "per_task": per_task}
    # 'other' audit sample (arm a, gated tasks)
    audit = {}
    for t in gated:
        oth = [r for r in rows if r["task"] == t and r["arm"] == "a" and r["label"] == "other"][:10]
        audit[t] = [{"uid": r["uid"], "runtime": r.get("runtime_label"), "ast": r.get("ast_label"),
                     "judge": r.get("judge_label"), "passed": r.get("passed"), "code": (r.get("code") or "")[:1500]}
                    for r in oth]
    out["other_audit_sample"] = audit
    # label sources and judge spend
    out["label_sources"] = dict(collections.Counter(r.get("labeller_source") for r in rows))
    out["n_disputed_final"] = sum(r["label"] == "disputed" for r in rows)
    spend = read_jsonl(ROOT / "labelling" / "logs" / "openrouter_spend.jsonl")
    out["bench_judge_spend_usd"] = float(sum(s.get("cost", 0) or 0 for s in spend))
    try:
        cost = json.loads((ROOT / "inputs" / "exp8" / "suite" / "results" / "openrouter_cost.json").read_text())
        out["path_judge_spend_usd"] = float(cost["by_purpose"].get("exp16_bench_route", 0.0))
    except (FileNotFoundError, KeyError, ValueError):
        out["path_judge_spend_usd"] = None
    # generation lengths per arm
    lens = collections.defaultdict(list)
    for r in rows:
        lens[r["arm"]].append(r.get("n_new_tokens") or 0)
    out["n_new_tokens_by_arm"] = {a: {"median": float(np.median(v)), "p90": float(np.quantile(v, 0.9)), "max": int(max(v)),
                                      "n": len(v)} for a, v in lens.items()}
    out["pruned_rows"] = sum(1 for r in rows if r.get("pruned_at"))
    out["finish_reasons"] = dict(collections.Counter(r.get("finish_reason") for r in rows))
    out["dataset_dependency"] = dataset_checks()
    write_json(RESULTS_DIR / "supplementary.json", out)
    logger.info(f"supplementary: W4 share of ban failures {out['ban_failures']['W4_share_of_failures']}; "
                f"disputed {out['n_disputed_final']}; judge spend bench {out['bench_judge_spend_usd']:.4f} "
                f"path {out['path_judge_spend_usd']}; nouns found {out['dataset_dependency'].get('all_found')}")
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("supplementary")
    main()
