#!/usr/bin/env python3
"""Sandbox harness validation on the dependency's humanevalplus and enamel rows (inputs/sources.json 'harness', the
first 12 rows of each): every canonical solution's docstring examples ('>>> f(args)' followed by the expected value)
become hidden-test cases and run through src/sandbox_tests6.py exactly as model programs do (python -I -S, RLIMIT_AS
2 GiB, per-case time limit, 'exact' checker, the entry point aliased to solve). Known-correct code must pass.
Writes results/harness_check.json and updates the roles in results/dependency_usage.json."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg6 import INPUTS, RESULTS_DIR, read_json, write_json  # noqa: E402
from unitlib6 import run_tests  # noqa: E402


def doctest_cases(code: str, entry: str) -> list[dict]:
    lines = code.splitlines()
    out = []
    for i, l in enumerate(lines[:-1]):
        m = re.match(r"\s*>>>\s*" + re.escape(entry) + r"\((.*)\)\s*$", l)
        if not m:
            continue
        exp_line = lines[i + 1].strip()
        if not exp_line or exp_line.startswith(">>>"):
            continue
        try:
            args = list(ast.literal_eval("(" + m.group(1) + ",)"))
            exp = ast.literal_eval(exp_line)
        except (ValueError, SyntaxError):
            continue
        out.append({"case_id": f"{entry}:{len(out)}", "args": args, "expected": exp, "limit": 2.0})
    return out


def main() -> None:
    rows = read_json(INPUTS / "sources.json")["harness"]
    res = []
    for r in rows:
        entry = (r.get("meta") or {}).get("metadata_entry_point")
        code = r.get("output") or ""
        if not entry or not code:
            continue
        cases = doctest_cases(code, entry)
        if not cases:
            res.append({"source": r["source"], "task": r["meta"].get("metadata_task_id"), "n_cases": 0})
            continue
        tr = run_tests(code + f"\n\nsolve = {entry}\n", cases, "exact", stop_on_fail=False)
        res.append({"source": r["source"], "task": r["meta"].get("metadata_task_id"), "n_cases": len(cases),
                    "n_pass": tr["n_pass"], "statuses": tr["statuses"], "load_error": tr["load_error"]})
    tot = sum(x.get("n_cases", 0) for x in res)
    ok = sum(x.get("n_pass", 0) for x in res)
    out = {"n_programs": len(res), "n_programs_with_cases": sum(1 for x in res if x.get("n_cases")),
           "n_cases": tot, "n_pass": ok, "items": res}
    write_json(RESULTS_DIR / "harness_check.json", out)
    du = read_json(RESULTS_DIR / "dependency_usage.json")
    for name in ("humanevalplus", "enamel"):
        sub = [x for x in res if x["source"] == name]
        du[name]["role"] = (f"sandbox harness validation: docstring examples of {len(sub)} canonical solutions run "
                            f"through src/sandbox_tests6.py ({sum(x.get('n_pass', 0) for x in sub)}/"
                            f"{sum(x.get('n_cases', 0) for x in sub)} cases pass; results/harness_check.json)")
    for name in ("clrs_text", "llm_creativity"):
        du[name]["role"] = ("counted only: no list-I task is covered (clrs_text holds CLRS-30 execution traces of "
                            "other algorithms; llm_creativity holds T02 path-finding labels without program text)")
    write_json(RESULTS_DIR / "dependency_usage.json", du)
    print({k: out[k] for k in ("n_programs", "n_programs_with_cases", "n_cases", "n_pass")})


if __name__ == "__main__":
    main()
