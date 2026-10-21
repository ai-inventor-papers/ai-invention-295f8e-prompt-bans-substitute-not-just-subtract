#!/usr/bin/env python3
"""Novelty-audit known-solution sets from the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, read in
place): every program whose metadata_bench_task names one of the 15 tasks (LeetCode references, mercury human
solutions, kodcode / xlcost / thealgorithms programs). Written to inputs/dep_art_j3Rm/known_subset.jsonl."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg4 import DEP, DEP_FULL, TASKS15  # noqa: E402

d = json.loads(DEP_FULL.read_text())
out = []
for ds in d["datasets"]:
    for ex in ds["examples"]:
        t = ex.get("metadata_bench_task")
        if not t:
            continue
        ts = t if isinstance(t, list) else [t]
        for tt in ts:
            if not isinstance(tt, str):
                continue
            tt = {"T01": "T1", "T02": "T2"}.get(tt.split("_")[0], tt.split("_")[0])
            if tt in TASKS15 and ex.get("output") and ("def " in ex["output"] or "class " in ex["output"]):
                out.append({"source": ds["dataset"], "task": tt, "code": ex["output"],
                            "mode_hint": ex.get("metadata_t02_mode") or ex.get("metadata_slug") or
                            ex.get("metadata_task_slug") or ex.get("metadata_named_algorithms")})
with open(DEP / "known_subset.jsonl", "w") as fh:
    for r in out:
        fh.write(json.dumps(r) + "\n")
from collections import Counter
print(len(out), Counter((r["source"], r["task"]) for r in out).most_common(60))
