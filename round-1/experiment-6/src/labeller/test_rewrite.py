#!/usr/bin/env python3
"""Stage-0 (e): the tracer's AST rewrite (obj.pop/append/add/insert -> _aii_tr) leaves every reference's outputs on
all hidden tests unchanged. Writes results/rewrite_check.json."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import labeller._trace_driver as D  # noqa: E402
from common import REFS_DIR, RESULTS, TESTS_DIR  # noqa: E402

sys.setrecursionlimit(100000)


def load(code, rewrite):
    tree = ast.parse(code)
    if rewrite:
        tree = D.Rewriter().visit(tree)
        ast.fix_missing_locations(tree)
    ns = {"__name__": "solution", "_aii_tr": D._aii_tr}
    exec(compile(tree, "solution.py", "exec"), ns)
    return ns["solve"]


def main():
    out = {}
    for task in ("T1", "T2"):
        cases = json.loads((TESTS_DIR / f"{task.lower()}_hidden.json").read_text())
        for f in sorted(REFS_DIR.glob(f"{task.lower()}_*.py")):
            code = f.read_text()
            a, b = load(code, False), load(code, True)
            same = 0
            for c in cases:
                if task == "T1":
                    D.CTX.update(task="T1", R=len(c["grid"]), C=len(c["grid"][0]))
                    args = lambda: ([str(r) for r in c["grid"]], tuple(c["start"]), tuple(c["goal"]))  # noqa: E731
                else:
                    D.CTX.update(task="T2", n=c["n"])
                    args = lambda: (c["n"], [tuple(e) for e in c["edges"]], c["s"], c["t"])  # noqa: E731
                same += a(*args()) == b(*args())
                D.EVENTS.clear()
                D.CALLS.clear()
            out[f.name] = dict(identical=same, n=len(cases))
    out["all_identical"] = all(v["identical"] == v["n"] for v in out.values() if isinstance(v, dict))
    (RESULTS / "rewrite_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    assert out["all_identical"]


if __name__ == "__main__":
    main()
