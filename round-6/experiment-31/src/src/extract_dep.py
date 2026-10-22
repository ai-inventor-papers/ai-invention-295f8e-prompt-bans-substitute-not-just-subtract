#!/usr/bin/env python3
"""Extract what claim S reads from the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, 10 datasets) into
inputs/dep_extract/ (small JSON files, hashed into inputs/MANIFEST.sha256 on the next S0 re-check):

- leetcode_nonbench.json  100 non-bench, non-duplicate LeetCode statements (seeded) -> S2 gate corpus B
- leetcode_bench_crosscheck.json  problems 28 (T04), 34 (R6), 1091 (T1-related) with parsed tests (cross-check)
- noun_candidates.json    the 718 flagged neutral-noun candidates of concreteness_norms -> S5 new nouns
- human_code.json         human-written Python: TheAlgorithms files naming BFS/DFS, HumanEval+ canonical solutions,
                          ENAMEL references -> descriptive gate corpus C; KodCode/XLCoST BFS/DFS programs -> partial
                          labeller sanity set and novelty-audit neighbours
- mercury_t04_r6.json     Mercury human solutions of problems 28 and 34 -> T04/R6 labeller sanity check
- clrs_bfs_dfs.json       CLRS-30 BFS/DFS execution-trace texts (descriptive gate corpus C)
- llm_creativity_t02.json the inspiration repository's judge-label composition (context only; no program text)
- dataset_usage.json      what was used from each of the 10 datasets
Usage: .venv/bin/python src/extract_dep.py <path to full_data_out.json>
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "inputs" / "dep_extract"


def _s(x) -> str:
    if isinstance(x, list):
        return " ".join(map(str, x))
    return "" if x is None else str(x)


def main(full: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = json.loads(Path(full).read_text())
    ds = {x["dataset"]: x["examples"] for x in d["datasets"]}
    usage = {}
    # ---------------- leetcodedataset
    lc = ds["leetcodedataset"]
    nonbench = [e for e in lc if e.get("metadata_bench_task") in (None, "None", "") and
                e.get("metadata_duplicate_of") in (None, "None", "") and 300 < len(e["input"]) < 2500]
    rng = random.Random(20261022)
    pick = sorted(rng.sample(nonbench, 100), key=lambda e: int(e["metadata_question_id"]))
    (OUT / "leetcode_nonbench.json").write_text(json.dumps(
        [{"qid": e["metadata_question_id"], "slug": e["metadata_task_slug"], "input": e["input"]} for e in pick], indent=1))
    cross = [e for e in lc if str(e["metadata_question_id"]) in ("28", "34", "1091")]
    (OUT / "leetcode_bench_crosscheck.json").write_text(json.dumps(
        [{"qid": e["metadata_question_id"], "bench_task": e.get("metadata_bench_task"), "input": e["input"],
          "tests": (json.loads(e.get("metadata_test_cases_json")) if isinstance(e.get("metadata_test_cases_json"), str) and e.get("metadata_test_cases_json") not in ("", "None") else [])[:200]} for e in cross], indent=1))
    usage["leetcodedataset"] = f"{len(pick)} non-bench statements (gate corpus B, greedy answers); problems 28/34/1091 cross-check"
    # ---------------- concreteness_norms
    cn = ds["concreteness_norms"]
    cand = [{"word": e["input"], "concreteness": float(e["output"]) if e["output"] not in (None, "None") else None,
             "subtlex": float(e["metadata_subtlex_frequency"]) if e["metadata_subtlex_frequency"] not in (None, "None", "") else 0.0,
             "lexfiles": e.get("metadata_oewn_noun_lexfiles")}
            for e in cn if str(e.get("metadata_noun_bank_candidate")) == "True"]
    (OUT / "noun_candidates.json").write_text(json.dumps(cand, indent=1))
    usage["concreteness_norms"] = f"{len(cand)} flagged neutral-noun candidates -> 12 new S5 nouns"
    # ---------------- human code
    human = []
    alg = ds["thealgorithms_python"]
    for e in alg:
        na = _s(e.get("metadata_named_algorithms")).lower()
        if re.search(r"\b(bfs|dfs|breadth|depth)", na + " " + _s(e.get("metadata_path")).lower()):
            human.append({"src": "thealgorithms:" + (e.get("metadata_path") or ""), "code": e["output"] or e["input"]})
    he = ds["humanevalplus"]
    human += [{"src": "humanevalplus:" + str(e.get("metadata_task_id")), "code": (e["input"] or "") + (e["output"] or "")}
              for e in he[:20]]
    en = ds["enamel"]
    human += [{"src": "enamel:" + str(e.get("metadata_task_id")), "code": (e["input"] or "") + (e.get("metadata_reference_body") or "")}
              for e in en[:10]]
    usage["thealgorithms_python"] = f"{sum(h['src'].startswith('thealgorithms') for h in human)} BFS/DFS-named files (gate corpus C)"
    usage["humanevalplus"] = "20 prompts + canonical solutions (gate corpus C)"
    usage["enamel"] = "10 expert-efficient references (gate corpus C)"
    rng.shuffle(human)
    (OUT / "human_code.json").write_text(json.dumps(human, indent=1))
    kx = []
    for name in ("kodcode_algorithmic", "xlcost_python"):
        n0 = 0
        for e in ds[name]:
            na = _s(e.get("metadata_named_algorithms")).lower()
            if re.search(r"\b(bfs|dfs|breadth[- ]first|depth[- ]first)", na):
                kx.append({"src": name, "named": na, "code": e["output"]})
                n0 += 1
        usage[name] = f"{n0} BFS/DFS-named programs (partial-labeller sanity set, novelty-audit neighbours)"
    (OUT / "kodcode_xlcost_bfs_dfs.json").write_text(json.dumps(kx, indent=1))
    # ---------------- mercury
    me = [{"qid": e["metadata_question_id"], "code": e["output"]} for e in ds["mercury"]
          if str(e["metadata_question_id"]) in ("28", "34")]
    (OUT / "mercury_t04_r6.json").write_text(json.dumps(me, indent=1))
    usage["mercury"] = f"{len(me)} human solutions of problems 28/34 (T04/R6 labeller sanity check)"
    # ---------------- clrs
    cl = [{"algorithm": e.get("metadata_algorithm"), "text": (e["input"] or "") + "\n" + (e["output"] or "")}
          for e in ds["clrs_text"] if _s(e.get("metadata_algorithm")).lower() in ("bfs", "dfs")][:20]
    (OUT / "clrs_bfs_dfs.json").write_text(json.dumps(cl, indent=1))
    usage["clrs_text"] = f"{len(cl)} BFS/DFS execution traces (descriptive gate corpus C)"
    # ---------------- llm_creativity
    lcr = Counter(e["output"] for e in ds["llm_creativity"])
    (OUT / "llm_creativity_t02.json").write_text(json.dumps(dict(lcr), indent=1))
    usage["llm_creativity"] = "judge-label composition only (the inspiration repository's T02 baseline; no program text)"
    (OUT / "dataset_usage.json").write_text(json.dumps(usage, indent=1))
    print(json.dumps(usage, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
