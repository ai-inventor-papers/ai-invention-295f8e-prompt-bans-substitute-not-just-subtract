#!/usr/bin/env python3
"""Canonical exp1 labeller (extract -> hidden tests -> tracer + runtime rules -> AST rules -> judge on disagreement
-> combine), wrapped so that this workspace keeps its own evaluation cache. Also the step-0.2 labeller re-check."""

from __future__ import annotations

import collections
import functools
from pathlib import Path
from typing import Any

from loguru import logger

from config import DATA, JUDGE_CAP_USD, RESULTS, SUITE, add_suite_to_path, read_jsonl, setup_logging, write_json

add_suite_to_path()
import pipeline  # noqa: E402  (exp1 stage code, copied read-only into suite/)

pipeline.EVAL_CACHE = DATA / "program_eval_cache.jsonl"
_orig_eval = pipeline.evaluate_unique
pipeline.evaluate_unique = functools.partial(_orig_eval, workers=24)


def label_texts(rows: list[dict[str, Any]], use_judge: bool = True,
                judge_cap: float = JUDGE_CAP_USD) -> list[dict[str, Any]]:
    """rows need 'task' and 'text'; returns the rows with code, tests, runtime/AST/judge labels and 'label'."""
    return pipeline.label_rows(rows, judge_cap=judge_cap, use_judge=use_judge)


def judge_spent() -> float:
    from labeller.judge import load_cost

    return float(load_cost().get("total_usd", 0.0))


def recheck() -> dict[str, Any]:
    """Step 0.2: canonical labeller on the adjudicated gold set and the 22 references."""
    gold = read_jsonl(SUITE / "labeller" / "gold_set.jsonl")
    rows = [{"task": g["task"], "text": "```python\n" + g["code"] + "```", "gold_key": g["key"],
             "adjudicated": g["adjudicated"], "split": g["split"], "gold_runtime": g["runtime_label"],
             "gold_ast": g["ast_label"]} for g in gold]
    refs = []
    for t in ("t1", "t2"):
        for r in pipeline.references(t):
            refs.append({"task": t, "text": "```python\n" + r["code"] + "```", "ref_file": r["file"],
                         "ref_mode": r["mode"]})
    lab = label_texts(rows + refs)
    g_lab = [r for r in lab if "gold_key" in r]
    r_lab = [r for r in lab if "ref_file" in r]
    res: dict[str, Any] = {}
    for split in ("all", "eval", "dev"):
        sub = [r for r in g_lab if r["adjudicated"] != "unresolved" and (split == "all" or r["split"] == split)]
        n = len(sub)
        res[f"gold_{split}"] = {
            "n": n,
            "combined_vs_adjudicated": sum(r["label"] == r["adjudicated"] for r in sub) / max(1, n),
            "runtime_vs_adjudicated": sum(r["runtime_label"] == r["adjudicated"] for r in sub) / max(1, n),
            "ast_vs_adjudicated": sum(r["ast_label"] == r["adjudicated"] for r in sub) / max(1, n),
            "runtime_eq_exp1_runtime": sum(r["runtime_label"] == r["gold_runtime"] for r in sub) / max(1, n),
            "ast_eq_exp1_ast": sum(r["ast_label"] == r["gold_ast"] for r in sub) / max(1, n),
            "labeller_sources": dict(collections.Counter(r["labeller_source"] for r in sub)),
        }
    res["references"] = {
        "n": len(r_lab),
        "combined_correct": sum(r["label"] == r["ref_mode"] for r in r_lab),
        "runtime_correct": sum(r["runtime_label"] == r["ref_mode"] for r in r_lab),
        "ast_correct": sum(r["ast_label"] == r["ref_mode"] for r in r_lab),
        "all_pass_tests": all(bool(r["passed"]) for r in r_lab),
        "detail": [{"file": r["ref_file"], "mode": r["ref_mode"], "label": r["label"], "runtime": r["runtime_label"],
                    "ast": r["ast_label"], "passed": r["passed"]} for r in r_lab],
    }
    res["confusion_combined_vs_adjudicated"] = dict(collections.Counter(
        f"{r['label']}->{r['adjudicated']}" for r in g_lab if r["label"] != r["adjudicated"]))
    res["target"] = {"combined_vs_adjudicated": 0.9, "references": "22/22", "exp1_reported": 0.966}
    res["passes"] = bool(res["gold_all"]["combined_vs_adjudicated"] >= 0.9
                         and res["references"]["combined_correct"] == len(r_lab))
    res["judge_spent_usd_total"] = judge_spent()
    return res


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("labeller_recheck")
    res = recheck()
    write_json(RESULTS / "labeller_recheck.json", res)
    logger.info(f"labeller recheck: gold all={res['gold_all']['combined_vs_adjudicated']:.3f} "
                f"eval={res['gold_eval']['combined_vs_adjudicated']:.3f} refs={res['references']['combined_correct']}"
                f"/{res['references']['n']} passes={res['passes']}")


if __name__ == "__main__":
    main()
