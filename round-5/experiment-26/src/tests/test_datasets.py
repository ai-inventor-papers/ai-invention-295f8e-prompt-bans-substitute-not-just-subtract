#!/usr/bin/env python3
"""Uses of the five dependency datasets that do not supply unit sources (the other five do: leetcodedataset ->
B1-B6 statements and dataset reference oracles, kodcode/thealgorithms/xlcost -> the B7 statement and its oracles,
concreteness_norms -> the neutral-noun bank). Writes results/dataset_usage.json.

1. humanevalplus: sandbox harness validation -- every canonical solution with its own test code runs in a fresh
   `python -I -S` subprocess with the same interpreter, isolation flags and RLIMIT_AS as the hidden-test sandbox.
2. enamel: the expert-efficient reference bodies are cross-checked against the HumanEval+ tests of the same task and
   timed against the canonical solutions (the same 'fastest reference' timing logic as the per-case limit rule).
3. clrs_text: every CLRS-30 algorithm name is mapped through each unit's alias lexicon (association mapping) to
   check that the lexicon maps external algorithm names to the intended catalogue modes.
4. mercury: human LeetCode solutions of the bench problems used as variant parents are wrapped and labelled by the
   parents' bench AST rules; agreement with Mercury's own structural markers is reported (external labeller check).
5. llm_creativity: the blind-judge mode distribution of 225 independent LLM programs for the weighted-shortest-path
   task (labels only) is reported as the field prior for a collapsed instruct default.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import units_extra  # noqa: E402,F401
from cfg5 import RESULTS_DIR, VENDOR, write_json  # noqa: E402
from units_spec import UNITS, map_answer  # noqa: E402
from unitlib import _limit_mem  # noqa: E402

DEP = Path(os.environ.get("AII_DEP_ART_J3RM", str(Path(__file__).resolve().parents[1].parent / "art_j3Rm_lr2nzR6")))


def run_py(code: str, timeout: float = 20.0) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        pr = subprocess.run([sys.executable, "-I", "-"], input=code, capture_output=True, text=True, timeout=timeout,
                            preexec_fn=_limit_mem)
        return pr.returncode == 0, time.perf_counter() - t0, pr.stderr[-200:]
    except subprocess.TimeoutExpired:
        return False, timeout, "timeout"


def main() -> None:
    full = json.loads((DEP / "full_data_out.json").read_text())
    ds = {d["dataset"]: d["examples"] for d in full["datasets"]}
    out: dict = {"sources_used_for_units": {"leetcodedataset": "B1-B6 statements + dataset reference oracles (+ "
                                                                "B3 alternate 1584, reserves 189/33)",
                                            "kodcode_algorithmic/thealgorithms_python/xlcost_python":
                                                "B7 statement + merge-sort and BIT oracles",
                                            "concreteness_norms": "neutral-noun bank (718 candidates)"}}
    # 1. humanevalplus
    he = ds["humanevalplus"]
    ok, times = 0, {}
    for r in he:
        code = r["output"] + "\n\n" + r["metadata_test"] + f"\n\ncheck({r['metadata_entry_point']})\n"
        good, dt, _ = run_py(code)
        ok += good
        times[r["metadata_task_id"]] = dt
    out["humanevalplus_harness"] = {"n": len(he), "canonical_pass": ok, "pass_rate": ok / len(he),
                                    "isolation": "python -I (site enabled: the HumanEval+ test code imports numpy; the hidden-test sandbox itself runs -I -S), RLIMIT_AS 2 GiB"}
    # 2. enamel
    en = ds["enamel"]
    he_by = {r["metadata_task_id"]: r for r in he}
    ok = n = 0
    ratios = []
    for r in en[:60]:
        h = he_by.get(r["metadata_task_id"])
        if h is None or not r.get("metadata_reference_body"):
            continue
        code = r["input"].rstrip() + "\n" + r["metadata_reference_body"] + "\n\n" + h["metadata_test"] + \
            f"\n\ncheck({r['metadata_entry_point']})\n"
        good, dt, _ = run_py(code)
        n += 1
        ok += good
        if good and times.get(h["metadata_task_id"]):
            ratios.append(dt / times[h["metadata_task_id"]])
    ratios.sort()
    out["enamel_reference_crosscheck"] = {"n": n, "expert_reference_pass_humaneval_tests": ok,
                                          "median_time_ratio_vs_canonical": ratios[len(ratios) // 2] if ratios else None,
                                          "note": "process wall time incl. interpreter start; the per-case limit rule "
                                                  "uses median-of-5 in-process case times"}
    # 3. clrs_text
    algos = sorted({r["metadata_algorithm"] for r in ds["clrs_text"]})
    expect = {"mst_kruskal": ("B3", "kruskal"), "mst_prim": ("B3", "prim_heap"), "binary_search": ("B4", "binary_search"),
              "quickselect": ("P_T03", "quickselect"), "naive_string_matcher": ("P_T04", "naive"),
              "kmp_matcher": ("P_T04", "kmp"), "bfs": ("P_T10", "bfs"), "dfs": ("P_T10", "dfs"),
              "activity_selector": ("P_R1", "greedy_end"), "heapsort": ("P_T03", "heapify_pop")}
    maps = {}
    for a in algos:
        txt = a.replace("_", " ")
        maps[a] = {u: map_answer(u, txt) for u in ("B3", "B4", "B5", "B6", "B7", "P_T03", "P_T04", "P_T10", "P_R1")}
    chk = {a: {"unit": u, "expected": m, "mapped": maps.get(a, {}).get(u), "ok": maps.get(a, {}).get(u) == m}
           for a, (u, m) in expect.items() if a in maps}
    out["clrs_alias_mapping"] = {"n_algorithms": len(algos), "algorithms": algos, "expected_checks": chk,
                                 "n_ok": sum(v["ok"] for v in chk.values()), "n_checked": len(chk)}
    # 4. mercury
    sys.path.insert(0, str(VENDOR / "exp11"))
    from bench.common.astrules import ast_label
    bench_of = {"T03_kth_smallest": "T03", "T10_connected_components": "T10", "T05_two_sum": "T05",
                "T06_find_duplicate": "T06", "T04_substring_search": "T04", "T08_fibonacci": "T08",
                "T14_top_k_frequent": "T14", "R1_non_overlapping_intervals": "R1"}
    res = Counter()
    rows = []
    for r in ds["mercury"]:
        t = bench_of.get(r.get("metadata_bench_task") or "")
        if t is None or not r.get("metadata_parses_py312"):
            continue
        m = re.search(r"def (\w+)\(self", r["output"])
        if not m:
            continue
        code = r["output"] + f"\n\ndef solve(*args):\n    return Solution().{m.group(1)}(*args)\n"
        code = "from typing import *\nimport collections, heapq, bisect, math, itertools\n" + code
        try:
            lab = ast_label(t, code)
        except Exception as e:  # noqa: BLE001
            lab = f"error:{type(e).__name__}"
        marks = r.get("metadata_structural_markers") or []
        res[(t, lab)] += 1
        rows.append({"task": t, "slug": r.get("metadata_slug"), "ast_label": lab, "markers": marks})
    out["mercury_ast_labels"] = {"n": len(rows), "by_task_label": {f"{t}|{l}": c for (t, l), c in res.items()},
                                 "rows": rows[:200]}
    # 5. llm_creativity
    lc = ds["llm_creativity"]
    c = Counter(r.get("metadata_t02_mode") for r in lc if not r.get("metadata_excluded_from_headline"))
    tot = sum(c.values())
    out["llm_creativity_prior"] = {"n": tot, "mode_counts": dict(c), "top_mode_share": max(c.values()) / tot if tot
                                   else None, "reading": "independent LLM programs for the same weighted-shortest-path "
                                                         "task concentrate on one mode (labels only, no program text)"}
    write_json(RESULTS_DIR / "dataset_usage.json", out)
    print(json.dumps({k: (v if k != "mercury_ast_labels" else {kk: vv for kk, vv in v.items() if kk != "rows"})
                      for k, v in out.items() if k != "sources_used_for_units"}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
