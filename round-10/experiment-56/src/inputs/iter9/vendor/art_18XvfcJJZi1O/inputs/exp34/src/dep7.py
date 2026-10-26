#!/usr/bin/env python3
"""Declared dependency art_j3Rm_lr2nzR6 (iteration-1 dataset, full_data_out.json, 10 datasets): every dataset is
read; the code-bearing ones form the known-solution corpus of the novelty audit (cache/known_corpus.jsonl, plus
exp18's 472 known solutions), the others are summarised (llm_creativity T02 blind-judge modes as the external
reference for which shortest-path algorithm LLM runs choose; clrs_text trace counts; concreteness_norms neutral-noun
candidates behind the twin prompts). Writes results/dependency_usage.json."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from c7 import CACHE, INPUTS, RESULTS, ROOT, append_jsonl, read_jsonl, write_json  # noqa: E402

# Declared dependency art_j3Rm_lr2nzR6 (iteration-1 dataset). The published repository holds it as a sibling folder
# named after the artifact id; override with the environment variable AII_DEP_ART_J3RM.
DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
TASK_MAP = {"T02": "T2", "T03": "T03", "T10": "T10", "T01": "T1"}
CORPUS = CACHE / "known_corpus.jsonl"


def main() -> None:
    data = json.loads((DEP / "full_data_out.json").read_text())
    summary = {"source": "art_j3Rm_lr2nzR6 full_data_out.json", "datasets": {}}
    if CORPUS.exists():
        CORPUS.unlink()
    n_code = Counter()
    for d in data["datasets"]:
        name, ex = d["dataset"], d["examples"]
        info = {"n_examples": len(ex)}
        rows = []
        for e in ex:
            out = e.get("output") or ""
            bt = e.get("metadata_bench_task")
            is_code = ("def " in out or "class " in out) and name not in ("llm_creativity", "clrs_text",
                                                                          "concreteness_norms")
            if is_code and not e.get("metadata_duplicate_of"):
                rows.append({"dataset": name, "bench_task": bt, "task": TASK_MAP.get(str(bt)), "code": out,
                             "named": e.get("metadata_named_algorithms")})
        if rows:
            append_jsonl(CORPUS, rows)
            n_code[name] = len(rows)
            info["n_code_in_corpus"] = len(rows)
            info["n_tagged_bench_task"] = sum(1 for r in rows if r["bench_task"])
        if name == "llm_creativity":
            info["T02_blind_judge_modes"] = dict(Counter(e.get("output") for e in ex))
        if name == "clrs_text":
            info["algorithms"] = dict(Counter(str(e.get("metadata_algorithm") or e.get("metadata_bench_mode"))
                                              for e in ex).most_common(15))
        if name == "concreteness_norms":
            info["neutral_noun_candidates"] = sum(1 for e in ex if e.get("metadata_neutral_noun_candidate")
                                                  or e.get("metadata_is_neutral_candidate"))
        summary["datasets"][name] = info
    n18 = 0
    for r in read_jsonl(INPUTS / "known" / "exp18_known_solutions.jsonl"):
        append_jsonl(CORPUS, [{"dataset": "exp18_known", "bench_task": r.get("task"), "task": r.get("task"),
                               "code": r.get("code")}])
        n18 += 1
    summary["exp18_known_solutions"] = n18
    summary["corpus_size"] = sum(n_code.values()) + n18
    write_json(RESULTS / "dependency_usage.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "datasets"}), list(summary["datasets"]))


if __name__ == "__main__":
    main()
