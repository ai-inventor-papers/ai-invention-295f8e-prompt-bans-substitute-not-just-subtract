#!/usr/bin/env python3
"""Uniform validity correction (deviation D-validity-has-solve): new-unit label rows written before the has_solve fix
with valid == True but an AST label 'invalid' (no parsed solve function, e.g. a fully commented-out program) are
re-marked invalid (label 'invalid', passed False). Originals are kept in data/labels_prefix/. Idempotent."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cfg5 import DATA, LAB_DIR, RESULTS, UNIT_DIRS, read_jsonl, utc_now, write_json, write_jsonl  # noqa: E402
from newbench.common.harness5 import has_solve  # noqa: E402

if __name__ == "__main__":
    bak = DATA / "labels_prefix"
    bak.mkdir(exist_ok=True)
    rep = {"utc": utc_now(), "units": {}}
    for u in UNIT_DIRS:
        p = LAB_DIR / f"{u}.jsonl"
        if not p.exists():
            continue
        rows = read_jsonl(p)
        n = 0
        for r in rows:
            if r.get("valid") and (r.get("ast_label") == "invalid" or not has_solve(r.get("code") or "")):
                r.update({"label": "invalid", "valid": False, "passed": False,
                          "labeller_source": "validity_fix(no parsed solve)"})
                n += 1
        if n:
            if not (bak / p.name).exists():
                shutil.copy(p, bak / p.name)
            write_jsonl(p, rows)
        rep["units"][u] = {"n_rows": len(rows), "n_remarked_invalid": n}
    write_json(RESULTS / "validity_fix.json", rep)
    print(json.dumps(rep, indent=1))
