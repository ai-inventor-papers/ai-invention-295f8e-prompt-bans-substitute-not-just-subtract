#!/usr/bin/env python3
"""AST-rule fixture check on TheAlgorithms/Python hand-labelled bench-mode implementations (dependency dataset).
The fixtures are library-style code (no solve()), so each task's rule function is applied to the parsed feature bag
directly.  Writes results/ast_fixture_check.json."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bench.common.astrules import RULES, F  # noqa: E402
from bench.common.build import FIXTURE_MAP  # noqa: E402

ta = json.loads((ROOT / "data" / "extract" / "thealgorithms.json").read_text())["labelled"]
rows = []
for r in ta:
    key = tuple(r["task_mode"])
    if key not in FIXTURE_MAP:
        continue
    task, mode = FIXTURE_MAP[key]
    try:
        lab = RULES[task](F(r["code"]))
    except (SyntaxError, ValueError, RecursionError):
        lab = "parse_error"
    rows.append({"path": r["path"], "task": task, "expected": mode, "ast_label": lab,
                 "match": (mode is None) or lab == mode})
out = {"n_fixtures_mapped": len(rows), "n_match": sum(r["match"] for r in rows),
       "n_unknown": sum(r["ast_label"] == "unknown" for r in rows), "rows": rows}
(ROOT / "results" / "ast_fixture_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "rows"}))
for r in rows:
    if not r["match"]:
        print("  miss:", r["path"], r["expected"], "->", r["ast_label"])
