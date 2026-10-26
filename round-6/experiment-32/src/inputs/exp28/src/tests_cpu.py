#!/usr/bin/env python3
"""CPU tests (testing plan T1-T8) -> results/tests_cpu.json.
T1 every bench labeller and the exp8 suite reproduce their gate on gold + references (results/labeller_recheck.json);
T2 the re-gate T2 rule labels heap Dijkstra, array Dijkstra (new reference), SPFA and Bellman-Ford references
correctly and every reference passes the hidden tests; R6 linear-scan extended reference labels 'linear_scan' and
passes; T3 the rule labels all of exp23's structural-match programs 'dijkstra' and leaves the 22 suite references
unchanged; T4 code extraction on 20 hand-made pt-style outputs; T5 plain-completion stop rule on 10 synthetic
continuations; T6 the frozen analysis self-test; T7 seed audit; T8 grep audit of every fed prompt."""

from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BENCH, DATA_DIR, E23, EXT_DIR, RESULTS_DIR, SUITE, bench_paths, read_json, read_jsonl,
                 setup_logging, write_json)
from regate_rules import apply_t2, t2_array_dijkstra

bench_paths()

REF_MODE_T2 = {"bellman_ford": "bf_spfa", "spfa": "bf_spfa", "dijkstra_lazy": "dijkstra",
               "dijkstra_decreasekey": "dijkstra", "dijkstra_array": "dijkstra", "bidijkstra_alternate": "bidijkstra",
               "bidijkstra_reverse": "bidijkstra", "dial_dict": "dial", "dial_list": "dial", "floyd_bigint": "floyd",
               "floyd_inf": "floyd"}


def t2_rule_refs() -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    refs = sorted((SUITE / "tasks" / "t2_wsp" / "references").glob("*.py")) + [EXT_DIR / "t2_wsp" / "dijkstra_array.py"]

    def one(p: Path) -> dict[str, Any]:
        code = p.read_text()
        ev = evaluate_program("t2", code)
        rl0 = runtime_rules.label("t2", ev["probes"])[0]
        al0 = ast_rules.label(code, "t2")[0]
        rl, _ = apply_t2(rl0, code)
        al, _ = apply_t2(al0, code)
        exp = REF_MODE_T2[p.stem]
        return {"file": p.name, "expected": exp, "runtime_frozen": rl0, "ast_frozen": al0, "runtime": rl, "ast": al,
                "passed": bool(ev["tests"].get("passed")), "ok": rl == exp and al == exp and bool(ev["tests"].get("passed")),
                "structural_match": t2_array_dijkstra(code)[0]}
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(one, refs))
    four = {k: next((r for r in rows if r["file"].startswith(k)), None) for k in
            ("dijkstra_lazy", "dijkstra_array", "spfa", "bellman_ford")}
    return {"rows": rows, "four_classes_ok": all(v and v["ok"] for v in four.values()),
            "all_references_ok": all(r["ok"] for r in rows), "n": len(rows)}


def r6_linear_scan_ref() -> dict[str, Any]:
    from bench.common.catalogue import TASKS
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    code = (EXT_DIR / "R6" / "linear_scan.py").read_text()
    cases = read_tests(BENCH / TASKS["R6"]["task_id"] / "tests.jsonl")
    lab = label_one({"sample_id": "ext_R6_linear_scan", "task": "R6", "condition": "recheck", "mode": None,
                     "paraphrase_id": None, "round": None, "attempt_idx": None, "seed": 0, "finish_reason": "stop",
                     "text": "```python\n" + code + "\n```"}, cases)
    return {"runtime_label": lab.get("runtime_label"), "ast_label": lab.get("ast_label"), "passed": lab.get("passed"),
            "n_pass": lab.get("n_pass"), "n_cases": lab.get("n_cases"),
            "ok": lab.get("runtime_label") == "linear_scan" and bool(lab.get("passed"))}


def t3_exp23_structural() -> dict[str, Any]:
    rows = [r for r in read_jsonl(E23 / "data" / "samples.jsonl") if r["task"] == "T2" and r.get("code")]
    bf = [r for r in rows if r["label"] == "bf_spfa"]

    def exp23_rule(code: str) -> bool:
        return bool(re.search(r"visited", code)) and bool(re.search(r"dist\[\w+\]\s*<\s*dist\[\w+\]", code)) \
            and "heapq" not in code and "deque" not in code
    m23 = [r for r in bf if exp23_rule(r["code"])]
    ours = [r for r in m23 if t2_array_dijkstra(r["code"])[0]]
    new_any = [r for r in bf if t2_array_dijkstra(r["code"])[0]]
    dij = [r for r in rows if r["label"] == "dijkstra"]
    dij_kept = sum(1 for r in dij if apply_t2("dijkstra", r["code"])[0] == "dijkstra")
    return {"n_t2_bf_spfa": len(bf), "n_exp23_structural_matches": len(m23), "n_labelled_dijkstra_by_rule": len(ours),
            "n_bf_spfa_matched_by_new_rule": len(new_any), "pass": len(ours) == len(m23) and len(m23) > 0,
            "dijkstra_labels_unchanged": dij_kept == len(dij)}


T4_CASES = [
    ("Here is my solution:\n```python\ndef solve(nums, k):\n    return sorted(nums)[k-1]\n```\nThis sorts.", "fenced_solve"),
    ("```python\nimport heapq\n\ndef solve(nums, k):\n    return heapq.nsmallest(k, nums)[-1]\n```", "fenced_solve"),
    ("Sure! Let me think.\n\n```\ndef solve(nums, k):\n    nums.sort()\n    return nums[k-1]\n```", "fenced_solve"),
    ("```python\nprint('hello')\n```\n\n```python\ndef solve(nums, k):\n    return sorted(nums)[k-1]\n```", "fenced_solve"),
    ("```python\ndef solve(nums, k):\n    nums.sort()\n    return nums[k-1]", "fenced_solve"),
    ("def solve(nums, k):\n    return sorted(nums)[k-1]\n", "suite_raw_text"),
    ("I cannot solve this task.", "no_code"),
    ("```python\ndef helper(x):\n    return x\n```", "bench_python_block"),
    ("```python\n'''docstring only'''\n```", "bench_python_block"),
    ("The answer is 42.\n\nExplanation: ...", "no_code"),
    ("```Python\ndef solve(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```", "fenced_solve"),
    ("```py\ndef solve(n):\n    return n\n```", "fenced_solve"),
    ("Step 1: read.\nStep 2:\n```python\nclass S:\n    pass\n```\n```python\ndef solve(x):\n    return x\n```", "fenced_solve"),
    ("```python\ndef solve(grid, start, goal):\n    return []\n```\n<end_of_turn>", "fenced_solve"),
    ("```\n```", "no_code"),
    ("```python\ndef solve_task(nums):\n    return nums\n```", "bench_python_block"),
    ("def solve(nums):\n    return 1\nprint(solve([1]))\n", "suite_raw_text"),
    ("```python\n# comment\ndef solve(nums, target):\n    seen = {}\n    return []\n```\nExample usage below", "fenced_solve"),
    ("```text\nnot code\n```\n```python\ndef solve(nums):\n    return 0\n```", "fenced_solve"),
    ("", "no_code"),
]


def t4_extraction() -> dict[str, Any]:
    from label_worker import extract5

    rows = []
    for text, exp in T4_CASES:
        code, how = extract5({"arm": "pt_chat", "text": text})
        rows.append({"expected": exp, "got": how, "ok": how == exp})
    return {"n": len(rows), "n_ok": sum(r["ok"] for r in rows), "rows": rows, "pass": all(r["ok"] for r in rows)}


T5_CASES = [
    ("    return sorted(nums)[k-1]\n\nprint(solve([3,1,2], 2))\n", True),
    ("    return sorted(nums)[k-1]\n", False),
    ("    x = 1\n    return x\n\ndef helper(y):\n    return y\n\n", False),
    ("    return 0\n\nif __name__ == '__main__':\n    pass\n", True),
    ("    return 0\n# a comment\n", False),
    ("    return 0\n\nclass A:\n    pass\n", False),
    ("    return 0\n\nsolve(1)\n", True),
    ("    a = [\n1, 2]\n    return a\n", True),
    ("    return 0\n\n@decorator\ndef f():\n    pass\n", False),
    ("    return 0\n\nimport os\n", False),
]


def t5_plain_stop() -> dict[str, Any]:
    from engine import plain_ended

    rows = [{"expected": e, "got": plain_ended(t), "ok": plain_ended(t) == e} for t, e in T5_CASES]
    return {"n": len(rows), "n_ok": sum(r["ok"] for r in rows), "rows": rows, "pass": all(r["ok"] for r in rows)}


def t8_grep() -> dict[str, Any]:
    import prompts as PG

    reg = read_jsonl(DATA_DIR / "prompts_fed.jsonl")
    texts = [(r["kind"], r["text"]) for r in reg]
    audit = PG.grep_audit(texts, list(ALL_TASKS))
    planted = PG.grep_audit([("ban", "Do not use a full sort for this task.\n\n" + PG.spec_text("T03"))], list(ALL_TASKS))
    return {**audit, "planted_positive_hits": planted["n_hits"], "pass": audit["pass"] and planted["n_hits"] >= 1}


def main() -> None:
    setup_logging("tests_cpu")
    import analysis_E as A

    lr = read_json(RESULTS_DIR / "labeller_recheck.json")
    pre = read_json(RESULTS_DIR / "preflight_inputs.json")
    res = {"T1_labeller_recheck": {
        "bench_all_reproduce_gate": all(v["reproduces_gate"] for v in lr["bench"].values()),
        "bench_all_references_pass": all(v["references_pass"] for v in lr["bench"].values()),
        "suite_references": f"{lr['exp8_suite']['references_ok']}/{lr['exp8_suite']['n_references']}",
        "suite_gold_runtime_acc": lr["exp8_suite"].get("acc_runtime_vs_adjudicated"),
        "suite_gate_runtime_acc": lr["exp8_suite"].get("gate_acc_runtime"),
        "suite_reproduces_exp23_value_0.804": abs((lr["exp8_suite"].get("acc_runtime_vs_adjudicated") or 0) - 0.8043) < 1e-3,
        "pass": all(v["reproduces_gate"] and v["references_pass"] for v in lr["bench"].values())
        and lr["exp8_suite"]["references_ok"] == lr["exp8_suite"]["n_references"]},
        "T2_t2_rule_references": t2_rule_refs(), "T2b_r6_linear_scan_reference": r6_linear_scan_ref(),
        "T3_exp23_structural_matches": t3_exp23_structural(), "T4_extraction": t4_extraction(),
        "T5_plain_stop": t5_plain_stop(), "T6_analysis_selftest": A.self_test(),
        "T7_seed_audit": pre["seed_audit"], "T8_grep_audit": t8_grep()}
    res["T2_t2_rule_references"]["pass"] = res["T2_t2_rule_references"]["four_classes_ok"]
    res["T2b_r6_linear_scan_reference"]["pass"] = res["T2b_r6_linear_scan_reference"]["ok"]
    res["T6_analysis_selftest"]["pass"] = res["T6_analysis_selftest"]["all_ok"]
    res["summary"] = {k: v.get("pass") for k, v in res.items() if isinstance(v, dict)}
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    print(res["summary"])


if __name__ == "__main__":
    main()
