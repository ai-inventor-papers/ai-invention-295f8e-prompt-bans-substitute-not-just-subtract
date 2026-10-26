"""extract + build: dependency extraction, hidden tests, references, per-case limits, mutant checks."""

from __future__ import annotations

import gc
import inspect
import json
import os
from collections import Counter
from pathlib import Path

from loguru import logger

from . import checkers
from .catalogue import TASK_ORDER, TASKS
from .harness import _limit_mem, run_many, run_tests
from .refs import MUTANTS, REFS
from .testgen import build_tests, write_tests

# Dependency artifact art_j3Rm_lr2nzR6 (dataset "Source data for an algorithm-choice coding bench", workspace folder
# gen_art_dataset_1).  The published repository holds it as a sibling folder of this one; DEP_DATASET_DIR overrides.
DEP = Path(os.environ.get("DEP_DATASET_DIR", str(Path(__file__).resolve().parents[2].parent / "gen_art_dataset_1")))
QID2TASK = {215: "T03", 28: "T04", 1: "T05", 287: "T06", 509: "T08", 547: "T10", 323: "T10", 300: "T11",
            56: "T13", 347: "T14", 435: "R1", 684: "R2", 210: "R3", 34: "R6"}
# thealgorithms / kodcode / xlcost lexicon names -> (task, mode) for AST-rule fixtures
FIXTURE_MAP = {
    ("T03_kth_smallest", "quickselect"): ("T03", "quickselect"),
    ("T03_kth_smallest", "median_of_medians"): ("T03", "median_of_medians"),
    ("T03_kth_smallest", "counting_sort"): ("T03", "counting_sort"),
    ("T04_substring_search", "kmp"): ("T04", "kmp"),
    ("T04_substring_search", "boyer_moore"): ("T04", "bmh"),
    ("T04_substring_search", "naive_string_search"): ("T04", "naive"),
    ("T04_substring_search", "rabin_karp"): ("T04", "rabin_karp"),
    ("T04_substring_search", "z_algorithm"): ("T04", "z_algorithm"),
    ("T05_two_sum", "two_sum_hash_map"): ("T05", "hash_map"),
    ("T06_find_duplicate", "floyd_cycle_detection"): ("T06", "floyd"),
    ("T08_fibonacci", "fibonacci_fast_doubling"): ("T08", "fast_doubling"),
    ("T08_fibonacci", "fibonacci_iteration_table"): ("T08", "iteration"),
    ("T08_fibonacci", "fibonacci_matrix_power"): ("T08", "matrix_power"),
    ("T10_connected_components", "dfs"): ("T10", "dfs"),
    ("T10_connected_components", "bfs"): ("T10", "bfs"),
    ("T10_connected_components", "union_find"): ("T10", "union_find"),
    ("T11_longest_increasing_subsequence", "lis_dp_quadratic"): ("T11", "quadratic_dp"),
    ("T11_longest_increasing_subsequence", "lis_n_log_n"): ("T11", "patience_bisect"),
    ("T13_merge_intervals", "sort_and_sweep"): ("T13", "sort_sweep"),
    ("R1_interval_scheduling", "activity_selection"): ("R1", "greedy_end"),
    ("R3_course_schedule", "topological_sort"): ("R3", None),
    ("R6_first_occurrence", "binary_search"): ("R6", "binary_search"),
    ("R6_first_occurrence", "exponential_search"): ("R6", "exponential_search"),
}


def extract(root: Path) -> dict:
    out = root / "data" / "extract"
    out.mkdir(parents=True, exist_ok=True)
    logger.info("loading dependency full_data_out.json (96 MB)")
    doc = json.loads((DEP / "full_data_out.json").read_text())
    ds = {d["dataset"]: d["examples"] for d in doc["datasets"]}
    summary = {"datasets": {k: len(v) for k, v in ds.items()}}
    # 1 leetcodedataset: parsed cases per task
    cases = {t: [] for t in TASK_ORDER}
    lc_meta = {}
    for e in ds["leetcodedataset"]:
        q = e["metadata_question_id"]
        if q not in QID2TASK or not e.get("metadata_bench_task"):
            continue
        t = QID2TASK[q]
        tc = json.loads(e["metadata_test_cases_json"])
        ok = [c for c in tc if c["status"] == "ok" and c.get("expected") is not None]
        cases[t] += [(c["case_id"], q, c["kwargs"]) for c in ok]
        lc_meta[q] = {"task": t, "entry_point": e["metadata_entry_point"], "n_cases": len(tc), "n_ok": len(ok),
                      "n_expected_null": e["metadata_n_expected_null"],
                      "answer_semantics": e["metadata_leetcode_answer_semantics"],
                      "reference_passes_check": e["metadata_reference_passes_check"],
                      "starter_code": e["metadata_starter_code"]}
    (out / "leetcode_cases.json").write_text(json.dumps(cases))
    summary["leetcode"] = lc_meta
    # 2 mercury human solutions for the bench problems
    merc = [{"qid": e["metadata_question_id"], "task": QID2TASK[e["metadata_question_id"]], "code": e["output"],
             "markers": e["metadata_structural_markers"], "io_hack": e["metadata_io_hack"],
             "runtime_ms": e["metadata_runtime_ms"], "entry": e["metadata_prompt_skeleton"]}
            for e in ds["mercury"] if e["metadata_question_id"] in QID2TASK and e["metadata_parses_py312"]]
    (out / "mercury.json").write_text(json.dumps(merc))
    summary["mercury"] = dict(Counter(m["task"] for m in merc))
    # 3 llm_creativity: T02 only, no program text -> external collapse prior
    lab = Counter(e["metadata_t02_mode"] for e in ds["llm_creativity"])
    base = Counter(e["metadata_t02_mode"] for e in ds["llm_creativity"] if e["metadata_strategy"] == "baseline")
    summary["llm_creativity_t02_prior"] = {"all": dict(lab), "baseline_strategy": dict(base),
                                           "note": "T02 (not in this bench); labels only, used as an external collapse prior"}
    # 4 thealgorithms: labelled fixtures + negatives
    # thealgorithms_python: input = source code, output = algorithm name (file stem)
    ta = [{"task_mode": [e["metadata_bench_task"], e["metadata_bench_mode"]], "code": e["input"],
           "name": e["output"], "path": e["metadata_path"]} for e in ds["thealgorithms_python"]
          if e.get("metadata_bench_task") and e["metadata_parses_py312"]]
    neg = [{"code": e["input"], "name": e["output"], "path": e["metadata_path"]} for e in ds["thealgorithms_python"]
           if not e.get("metadata_bench_task") and e["metadata_parses_py312"]][:400]
    (out / "thealgorithms.json").write_text(json.dumps({"labelled": ta, "negatives": neg}))
    # 5 clrs_text traces for overlapping algorithms
    keep_alg = {"quickselect", "binary_search", "bfs", "dfs", "topological_sort", "kmp_matcher", "naive_string_matcher"}
    clrs = [{"algorithm": e["metadata_algorithm"], "length": e["metadata_length"], "input": e["input"],
             "output": e["output"]} for e in ds["clrs_text"] if e["metadata_algorithm"] in keep_alg]
    (out / "clrs.json").write_text(json.dumps(clrs))
    summary["clrs_kept"] = dict(Counter(c["algorithm"] for c in clrs))
    # 6 humanevalplus: harness smoke test
    hep = [{"task_id": e["metadata_task_id"], "prompt": e["input"], "solution": e["output"],
            "entry_point": e["metadata_entry_point"], "test": e["metadata_test"]} for e in ds["humanevalplus"]][:5]
    (out / "humanevalplus5.json").write_text(json.dumps(hep))
    # 7 enamel: size-levelled generators (timing calibration template) + fib reference
    en = [{"task_id": e["metadata_task_id"], "reference": e["output"], "input_generator": e["metadata_input_generator"],
           "levels": e["metadata_input_levels"], "fib": e["metadata_fibonacci_family"]} for e in ds["enamel"]]
    (out / "enamel.json").write_text(json.dumps(en))
    # 8 concreteness norms: 718 neutral-noun candidates
    nouns = [{"word": e["input"], "freq": e["metadata_subtlex_frequency"],
              "tok_bare": e["metadata_qwen3_tokens_bare"], "tok_space": e["metadata_qwen3_tokens_with_leading_space"]}
             for e in ds["concreteness_norms"] if e.get("metadata_noun_bank_candidate")]
    (out / "neutral_nouns.json").write_text(json.dumps(nouns))
    summary["neutral_noun_candidates"] = len(nouns)
    # 9/10 kodcode + xlcost rows naming a bench mode (AST-rule checks on LLM-style / human code)
    named = []
    for name in ("kodcode_algorithmic", "xlcost_python"):
        for e in ds[name]:
            if e.get("metadata_named_algorithms"):
                named.append({"source": name, "named": e["metadata_named_algorithms"], "code": e["output"]})
    (out / "named_code.json").write_text(json.dumps(named))
    summary["named_code"] = dict(Counter(n["source"] for n in named))
    (out / "extract_summary.json").write_text(json.dumps(summary, indent=1))
    del doc, ds
    gc.collect()
    logger.info(f"extract done: {summary['datasets']}")
    return summary


def build_task(root: Path, t: str, workers: int = 5) -> dict:
    c = TASKS[t]
    d = root / "bench" / c["task_id"]
    (d / "references").mkdir(parents=True, exist_ok=True)
    parsed = json.loads((root / "data" / "extract" / "leetcode_cases.json").read_text())[t]
    cases, prov = build_tests(t, parsed, seed=20261020 + TASK_ORDER.index(t))
    (d / "checker.py").write_text('"""Order-free checker for ' + c["task_id"] + ' (copy of bench/common/checkers.py)."""\n\n'
                                  + inspect.getsource(checkers._is_int) + "\n\n" + inspect.getsource(checkers._pairs)
                                  + "\n\n" + inspect.getsource(checkers.CHECK[t]) + f"\n\ncheck = {checkers.CHECK[t].__name__}\n")
    for m, code in REFS[t].items():
        (d / "references" / f"{m}.py").write_text(code)
    # reference timing with generous limits
    for cc in cases:
        cc["limit"] = 20.0
    res = run_many([(m, code) for m, code in REFS[t].items()], t, cases, workers=workers)
    ref_ok = {m: r["passed"] for m, r in res.items()}
    bad = {m: (r["first_fail"], r["msgs"], r["load_error"]) for m, r in res.items() if not r["passed"]}
    if bad:
        logger.warning(f"{t}: references failing: {bad}")
    limits = []
    for i, cc in enumerate(cases):
        ts = [res[m]["times"][i] for m in REFS[t] if res[m]["times"][i] is not None]
        fastest = min(ts) if ts else 0.1
        cc["limit"] = round(max(1.0, 10 * fastest), 3)
        cc["ref_times"] = {m: (round(res[m]["times"][i], 5) if res[m]["times"][i] is not None else None) for m in REFS[t]}
        limits.append(cc["limit"])
    margin = {}
    for m in REFS[t]:
        worst = max((res[m]["times"][i] or 99) / cases[i]["limit"] for i in range(len(cases)))
        margin[m] = round(worst, 3)
    write_tests(d / "tests.jsonl", cases)
    mres = run_many([(f"mutant{i}", code) for i, code in enumerate(MUTANTS[t])], t, cases, workers=workers)
    mut = {k: not v["passed"] for k, v in mres.items()}
    rep = {"task": t, "n_cases": len(cases), "provenance": prov, "ref_passed": ref_ok, "ref_fail_detail": bad,
           "worst_time_over_limit": margin, "margin_rule_ok": all(v <= 0.25 for v in margin.values()),
           "mutants_fail": mut, "all_mutants_fail": all(mut.values()),
           "limits_summary": {"min": min(limits), "max": max(limits), "n_above_1s": sum(1 for x in limits if x > 1.0)}}
    (d / "build_report.json").write_text(json.dumps(rep, indent=1))
    logger.info(f"{t}: {len(cases)} cases {prov}; refs ok={sum(ref_ok.values())}/{len(ref_ok)}; "
                f"worst ref time/limit={max(margin.values()):.3f} {margin}; mutants fail={mut}")
    return rep


def smoke_humanevalplus(root: Path) -> dict:
    """Run 5 HumanEval+ canonical solutions through the same sandbox (python -I -S) with their EvalPlus tests."""
    import subprocess
    import sys
    hep = json.loads((root / "data" / "extract" / "humanevalplus5.json").read_text())
    out = {}
    for h in hep:
        prog = h["solution"] + "\n\n" + h["test"] + f"\n\ncheck({h['entry_point']})\nprint('SMOKE_OK')\n"
        try:
            # EvalPlus tests import numpy, so the smoke test uses the venv interpreter (isolated mode, same limits)
            pr = subprocess.run([sys.executable, "-I", "-c", prog], capture_output=True, text=True, timeout=120,
                                preexec_fn=_limit_mem)
            out[h["task_id"]] = "SMOKE_OK" in pr.stdout
        except subprocess.TimeoutExpired:
            out[h["task_id"]] = False
    return out


def exp_bruteforce_check(root: Path) -> dict:
    """Exponential brute force must time out: subset enumeration for LIS, naive recursion for Fibonacci."""
    from .testgen import read_tests
    lis = '''from itertools import combinations
def solve(nums):
    n = len(nums)
    for r in range(n, 0, -1):
        for comb in combinations(nums, r):
            if all(comb[i] < comb[i + 1] for i in range(r - 1)):
                return r
'''
    fib = '''def solve(n):
    return n if n < 2 else solve(n - 1) + solve(n - 2)
'''
    r1 = run_tests(lis, "T11", read_tests(root / "bench" / TASKS["T11"]["task_id"] / "tests.jsonl"))
    r2 = run_tests(fib, "T08", read_tests(root / "bench" / TASKS["T08"]["task_id"] / "tests.jsonl"))
    return {"lis_subsets_fails": not r1["passed"], "lis_first_fail": r1["first_fail"],
            "fib_naive_fails": not r2["passed"], "fib_first_fail": r2["first_fail"]}
