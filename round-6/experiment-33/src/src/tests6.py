#!/usr/bin/env python3
"""CPU tests -> results/tests_cpu6.json: exp28's T1-T8 (labeller re-check, T2 rule, R6 extended label, extraction,
stop rule, analysis self-test, seed audit, grep audit; reused unchanged) + T9 few-shot builder, T10 plain_ended on
few-shot continuations, T11 q_lik token alignment, T12 the frozen L analysis self-test."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BOS_ID, DATA_DIR, FAMILY_GROUP, RESULTS_DIR, TEMPLATE_IDS, read_json, read_jsonl,
                 setup_logging, write_json)
import prompts as PG
import prompts6 as P6

T10_CASES = [  # (continuation after 'def solve(...):\n', expected plain_ended)
    ("    return sorted(nums)[k - 1]\n\n\n\"\"\"Task: write a Python function\n", True),
    # the frozen rule ignores an incomplete last line: it stops one line later, once the line is complete
    ("    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\n\n\"\"\"Given", False),
    ("    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\n\n\"\"\"Given x\n", True),
    ("    return 1\n", False),
    ("    x = 1\n    return x\n\ndef helper(y):\n    return y\n", False),
    ("    x = 1\n    return x\n\nprint(solve(3))\n", True),
    ("    x = 1\n    return x\n\nif __name__ == '__main__':\n    pass\n", True),
    ("    for i in range(3):\n        pass\n", False),
    ("    return [i for i in nums]\n\n\n# next\n", False),
    ("    return 0\n\n\nclass Foo:\n    pass\n", False),
    ("    return 0\n\n\nimport os\n", False),
    ("    seen = set()\n    return seen\n\n\n'''docstring style'''\n", True),
    ("    return -1\n\n\n\n\n\"\"\"", False),
    ("    return -1\n\n\n\n\n\"\"\"Next\n", True),
    ("    i = 0\n    while i < 3:\n        i += 1\n    return i\nsolve(1)\n", True),
    ("    pass\n@decorator\n", False),
    ("    return x\n\nfrom math import inf\n", False),
    ("    return x\nresult = solve(2)\n", True),
    ("    return x\n\n\n\n", False),
    ("    lo, hi = 0, len(nums)\n", False),
    ("    return x\n\nTask: next\n", True),
]


def t9_fewshot() -> dict[str, Any]:
    rows = []
    for t in ALL_TASKS:
        for fam in ("F_bench", "F_he"):
            p = P6.p_fewshot(t, fam)
            ex = P6.f_bench_exemplars(t) if fam == "F_bench" else []
            ok = (p["ids"][0] == BOS_ID and p["ids"].count(BOS_ID) == 1 and t not in ex
                  and all(FAMILY_GROUP[e] != FAMILY_GROUP[t] for e in ex)
                  and p["text"].endswith("def " + PG.signature(t) + ":\n"))
            rows.append({"task": t, "family": fam, "exemplars": p["exemplars"], "P": p["P"], "ok": ok})
    audit = PG.grep_audit(P6.all_fed_texts_fewshot(list(ALL_TASKS)), list(ALL_TASKS))
    return {"rows": rows, "grep_audit_hits": audit["n_hits"], "max_P": max(r["P"] for r in rows),
            "pass": all(r["ok"] for r in rows) and audit["pass"]}


def t10_plain_stop() -> dict[str, Any]:
    from engine import plain_ended

    rows = [{"i": i, "expected": e, "got": plain_ended(c), "ok": plain_ended(c) == e} for i, (c, e) in enumerate(T10_CASES)]
    return {"n": len(rows), "n_ok": sum(r["ok"] for r in rows), "rows": rows, "pass": all(r["ok"] for r in rows)}


def t11_alignment() -> dict[str, Any]:
    from qlik6 import window_ids

    tok = PG.tokenizer()
    codes = [P6.bench_reference_body("T04", "naive"), P6.bench_reference_body("T08", "iteration")]
    out = []
    for t, (sig, body) in zip(("T04", "T08"), codes):
        code = "def " + sig + ":\n" + body
        for w in TEMPLATE_IDS[:2]:
            tw = PG.p_twin(t, w)
            ids, tg, win = window_ids(tok, tw["ids"], "```python\n", code)
            ok = ids[:tw["P"]] == tw["ids"] and len(tg) == min(48, len(tok(code, add_special_tokens=False)["input_ids"])) \
                and code.startswith(win) and tg[0] == tw["P"] + len(tok("```python\n", add_special_tokens=False)["input_ids"])
            out.append({"task": t, "w": w, "window_text_head": win[:60], "ok": ok})
    return {"rows": out, "pass": all(r["ok"] for r in out)}


def main() -> None:
    setup_logging("tests6")
    import analysis_L as AL
    import tests_cpu as T28

    res: dict[str, Any] = {}
    lr = read_json(RESULTS_DIR / "labeller_recheck.json")
    pre = read_json(RESULTS_DIR / "preflight_inputs.json")
    res["T1_labeller_recheck"] = {
        "bench_all_reproduce_gate": all(v["reproduces_gate"] for v in lr["bench"].values()),
        "bench_all_references_pass": all(v["references_pass"] for v in lr["bench"].values()),
        "suite_references": f"{lr['exp8_suite']['references_ok']}/{lr['exp8_suite']['n_references']}",
        "exp28_300_rows_relabel_agreement": lr["exp28_rows_relabel"]["agreement"],
        "exp28_relabel_mismatches_excluding_exp28_disputed": lr["exp28_rows_relabel"]["n_mismatch_excluding_exp28_disputed"],
        "pass": all(v["reproduces_gate"] and v["references_pass"] for v in lr["bench"].values())
        and lr["exp8_suite"]["references_ok"] == lr["exp8_suite"]["n_references"]
        and lr["exp28_rows_relabel"]["pass"]}
    res["T2_t2_rule_references"] = T28.t2_rule_refs()
    res["T2_t2_rule_references"]["pass"] = res["T2_t2_rule_references"]["four_classes_ok"]
    res["T2b_r6_linear_scan_reference"] = T28.r6_linear_scan_ref()
    res["T2b_r6_linear_scan_reference"]["pass"] = res["T2b_r6_linear_scan_reference"]["ok"]
    res["T3_exp23_structural_matches"] = T28.t3_exp23_structural()
    res["T4_extraction"] = T28.t4_extraction()
    res["T5_plain_stop"] = T28.t5_plain_stop()
    res["T7_seed_audit"] = pre["seed_audit"]
    reg = read_jsonl(DATA_DIR / "prompts_fed.jsonl")
    g = PG.grep_audit([(r["kind"], r["text"]) for r in reg], list(ALL_TASKS))
    res["T8_grep_audit_fed_prompts"] = {**g, "n_registered": len(reg)}
    res["T9_fewshot_builder"] = t9_fewshot()
    res["T10_plain_stop_fewshot"] = t10_plain_stop()
    res["T11_qlik_alignment"] = t11_alignment()
    st = AL.self_test()
    res["T12_frozen_analysis_selftest"] = {**st, "pass": st["all_ok"]}
    res["summary"] = {k: v.get("pass") for k, v in res.items() if isinstance(v, dict)}
    write_json(RESULTS_DIR / "tests_cpu6.json", res)
    print(res["summary"])


if __name__ == "__main__":
    main()
