#!/usr/bin/env python3
"""Declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, 10 datasets): load every dataset, record its size and
role, and extract the nearest-known reference pool for the novelty audit -> inputs/dep_dataset/known_subset.jsonl.

Roles: mercury and leetcodedataset (human solutions of the bench-mapped LeetCode problems) are the plan's nearest-known
references; thealgorithms_python, kodcode_algorithmic and xlcost_python programs whose metadata names a bench task or
mode are added to the same pool; metadata_test_cases_json is the fallback rebuild source for hidden tests (not needed:
the bench is intact); the other datasets (llm_creativity labels without program text, clrs_text traces, humanevalplus,
enamel, concreteness_norms) are summarised only (no program text for this artifact's tasks).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import DEP, DEP_DATASET_DIR, RESULTS_DIR, TASKS15, setup_logging, sha256_file, write_json, write_jsonl  # noqa

DEP_TASK = {"T02": "T2"}  # iteration-1 bench naming -> this artifact's task ids (T02 weighted shortest path = T2)


def map_task(bt: str | None) -> str | None:
    if not bt or bt == "None":
        return None
    m = re.match(r"^([TR]\d+)", str(bt))
    if not m:
        return None
    k = m.group(1)
    k = DEP_TASK.get(k, k)
    return k if k in TASKS15 else None


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("dep_usage")
    f = DEP_DATASET_DIR / "full_data_out.json"
    data = json.loads(f.read_text())
    summary, pool = {}, []
    for ds in data["datasets"]:
        name = ds["dataset"]
        ex = ds["examples"]
        n_map = 0
        for e in ex:
            t = map_task(e.get("metadata_bench_task"))
            code = e.get("output") or ""
            if t is None or name not in ("mercury", "leetcodedataset", "thealgorithms_python", "kodcode_algorithmic",
                                         "xlcost_python"):
                continue
            if "def " not in code:
                continue
            n_map += 1
            pool.append({"source": f"art_j3Rm:{name}", "task": t, "code": code,
                         "mode_hint": e.get("metadata_bench_mode") or e.get("metadata_named_algorithms")
                         or e.get("metadata_slug") or e.get("metadata_task_slug")})
        summary[name] = {"n_examples": len(ex), "n_programs_mapped_to_this_artifacts_tasks": n_map,
                         "bench_tasks": dict(Counter(map_task(e.get("metadata_bench_task")) for e in ex
                                                     if map_task(e.get("metadata_bench_task"))))}
    DEP.mkdir(parents=True, exist_ok=True)
    write_jsonl(DEP / "known_subset.jsonl", pool)
    write_json(RESULTS_DIR / "dependency_usage.json",
               {"dependency": "art_j3Rm_lr2nzR6", "file": "full_data_out.json", "sha256": sha256_file(f),
                "datasets": summary, "n_pool": len(pool), "pool_by_task": dict(Counter(p["task"] for p in pool)),
                "roles": __doc__})
    logger.info(f"dependency: {len(data['datasets'])} datasets; pool {len(pool)} programs")


if __name__ == "__main__":
    main()
