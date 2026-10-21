#!/usr/bin/env python3
"""Use of the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, 10 datasets): every dataset is read and
tabulated; the ones holding program text supply the nearest-known references of the novelty audit for T10
(LeetCode 547/323/1971), T2 (743) and T03 (215).

The dependency folder is found through ONE constant, cfg.DEP_DATASET_DIR (env ART_J3RM_DIR, else the published
sibling folder art_j3Rm_lr2nzR6, else the run layout). Outputs: data/known_solutions_e.jsonl,
results/dependency_usage.json."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import DEP_DATASET_DIR, setup_logging, write_json
from cfg_e import DATA_DIR, RESULTS_DIR

TASK_MAP = {"T10_connected_components": "T10", "T02_weighted_shortest_path": "T2", "T03_kth_smallest": "T03"}
LEETCODE_IDS = {"547": "T10", "323": "T10", "1971": "T10", "743": "T2", "215": "T03"}
MODE_WORDS = {"T10": ("union find", "union-find", "disjoint set", "connected component", "dfs", "bfs"),
              "T2": ("dijkstra", "bellman", "spfa", "shortest path", "floyd"),
              "T03": ("quickselect", "kth smallest", "k-th smallest", "heap", "median of medians")}
TWIN_NOUNS = ("ship", "man", "house")


def _task_of(e: dict[str, Any]) -> str | None:
    bt = e.get("metadata_bench_task")
    if bt in TASK_MAP:
        return TASK_MAP[bt]
    named = e.get("metadata_bench_tasks_named")
    if isinstance(named, str):
        try:
            named = json.loads(named)
        except json.JSONDecodeError:
            named = [named]
    for n in named or []:
        if n in TASK_MAP:
            return TASK_MAP[n]
    return None


def main() -> None:
    setup_logging("dep_usage")
    p = Path(DEP_DATASET_DIR) / "full_data_out.json"
    d = json.loads(p.read_text())
    usage: dict[str, Any] = {"source": "art_j3Rm_lr2nzR6/full_data_out.json", "datasets": {}}
    known: list[dict[str, Any]] = []
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        info: dict[str, Any] = {"n_examples": len(ex)}
        if name in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
            rel = []
            for e in ex:
                t = _task_of(e)
                qid = str(e.get("metadata_question_id") or "")
                if t is None and name == "leetcodedataset" and qid in LEETCODE_IDS:
                    t = LEETCODE_IDS[qid]
                if t is None:
                    continue
                code = (e.get("input") if name == "thealgorithms_python" else e.get("output")) or ""
                if "def " not in code:
                    continue
                rel.append(t)
                known.append({"task": t, "source": name, "id": f"{name}:{e.get('metadata_row_index')}",
                              "mode_hint": e.get("metadata_bench_mode") or e.get("metadata_named_algorithms"),
                              "code": code})
            info["n_relevant_T10_T2_T03"] = dict(Counter(rel))
            info["use"] = "nearest-known references for the novelty audit"
        elif name == "llm_creativity":
            info["t02_mode_distribution"] = dict(Counter(e.get("metadata_t02_mode") for e in ex))
            info["use"] = "external reference composition of LLM T2 programs (labels only; no program text)"
        elif name == "clrs_text":
            algs = Counter(e.get("metadata_algorithm") for e in ex)
            info["algorithms"] = dict(algs.most_common(20))
            info["use"] = "tracer-reference counts only (no code); E reuses exp19's validated labellers unchanged"
        elif name == "concreteness_norms":
            rows = {e.get("input"): e for e in ex if e.get("input") in TWIN_NOUNS}
            info["twin_nouns"] = {w: {"concreteness": rows[w].get("output"),
                                      "qwen3_tokens_with_leading_space": rows[w].get(
                                          "metadata_qwen3_tokens_with_leading_space"),
                                      "subtlex_frequency": rows[w].get("metadata_subtlex_frequency")}
                                  for w in rows}
            info["use"] = "documents the neutral-twin nouns of the frozen exp19 prompts (ship; man and the house)"
        elif name in ("humanevalplus", "enamel"):
            info["use"] = ("harness-validation / time-limit calibration set of the bench build; not needed by E "
                           "(the bench harness is reused unchanged and re-checked on 2,150 rows)")
        usage["datasets"][name] = info
    with open(DATA_DIR / "known_solutions_e.jsonl", "w") as fh:
        for k in known:
            fh.write(json.dumps(k) + "\n")
    usage["n_known_solutions"] = dict(Counter(k["task"] for k in known))
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    logger.info(f"dependency usage: {len(d['datasets'])} datasets; known solutions {usage['n_known_solutions']}")


if __name__ == "__main__":
    main()
