#!/usr/bin/env python3
"""External cross-check with the dependency's thealgorithms_python rows (MIT): independent implementations of the
units' catalogue modes, wrapped as solve(...), are run through each unit's frozen hidden tests and frozen runtime + AST
labellers. Checks the oracle/tests (an independent correct implementation must pass) and the labellers (it should get
its intended mode). Descriptive; written after the unit commitments. -> results/external_reference_check.json"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cfg5 import DEP, RESULTS, utc_now, write_json  # noqa: E402

CASES = [
    ("A2", "dynamic_programming/max_subarray_sum.py", "kadane",
     "\n\ndef solve(nums):\n    return int(max_subarray_sum(nums))\n"),
    ("A2", "divide_and_conquer/max_subarray.py", "divide_conquer",
     "\n\ndef solve(nums):\n    return int(max_subarray(nums, 0, len(nums) - 1)[2])\n"),
    ("A7", "strings/manacher.py", "manacher", "\n\ndef solve(s):\n    return palindromic_string(s)\n"),
    ("A4", "maths/sieve_of_eratosthenes.py", "eratosthenes",
     "\n\ndef solve(n):\n    return 0 if n < 3 else len([p for p in prime_sieve(n) if p < n])\n"),
    ("A4", "maths/prime_sieve_eratosthenes.py", "eratosthenes",
     "\n\ndef solve(n):\n    return 0 if n < 3 else len([p for p in prime_sieve_eratosthenes(n) if p < n])\n"),
    ("A4", "maths/odd_sieve.py", "eratosthenes",
     "\n\ndef solve(n):\n    return 0 if n < 3 else len([p for p in odd_sieve(n) if p < n])\n"),
    ("A4", "maths/segmented_sieve.py", "segmented_sieve",
     "\n\ndef solve(n):\n    return 0 if n < 3 else len([p for p in sieve(n) if p < n])\n"),
    ("A4", "maths/sieve_of_atkin.py", "atkin",
     "\n\ndef solve(n):\n    return 0 if n < 3 else len([p for p in sieve_of_atkin(n) if p < n])\n"),
    ("A1", "other/majority_vote_algorithm.py", "boyer_moore_vote",
     "\n\ndef solve(nums):\n    return majority_vote(nums, 2)[0]\n"),
]


def main() -> None:
    from newbench.common.label5 import mech_labels

    rows = json.loads((DEP / "thealgorithms_python_units.json").read_text())
    src = {(u, r["path"]): r["code"] for u, rs in rows.items() for r in rs}
    out = []
    for u, path, mode, adapter in CASES:
        code = src.get((u, path))
        if code is None:
            out.append({"unit": u, "path": path, "error": "not in the dependency extract"})
            continue
        m = mech_labels(u, code + adapter)
        out.append({"unit": u, "path": f"TheAlgorithms/Python:{path}", "intended_mode": mode, "passed": m.get("passed"),
                    "n_pass": m.get("n_pass"), "n_cases": m.get("n_cases"), "first_fail": m.get("first_fail"),
                    "load_error": m.get("load_error"), "runtime_label": m.get("runtime_label"),
                    "ast_label": m.get("ast_label"),
                    "runtime_matches_intended": m.get("runtime_label") == mode,
                    "ast_matches_intended": m.get("ast_label") == mode})
    res = {"utc": utc_now(), "label": "descriptive external check (dependency thealgorithms_python, MIT)",
           "n": len(out), "n_passed_tests": sum(1 for o in out if o.get("passed")),
           "n_runtime_match": sum(1 for o in out if o.get("runtime_matches_intended")),
           "n_ast_match": sum(1 for o in out if o.get("ast_matches_intended")), "items": out}
    write_json(RESULTS / "external_reference_check.json", res)
    for o in out:
        print(o.get("unit"), o.get("path"), o.get("intended_mode"), "passed", o.get("passed"), o.get("n_pass"),
              "/", o.get("n_cases"), "rt", o.get("runtime_label"), "ast", o.get("ast_label"), o.get("load_error"))
    print({k: v for k, v in res.items() if k != "items"})


if __name__ == "__main__":
    main()
