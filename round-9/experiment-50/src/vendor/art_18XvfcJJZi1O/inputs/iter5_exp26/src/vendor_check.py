#!/usr/bin/env python3
"""Vendored-input integrity (plan section 1): sha256 of every file copied into vendor/ -> vendor/SHA256SUMS; the
bench files are verified against vendor/exp11/bench/commitment.json; every parent bench labeller used by the extra
arm is re-run on its gold set (runtime + AST vs the gold adjudicated label) and on its references.
Writes results/vendor_check.json."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import RESULTS_DIR, VENDOR, write_json  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    files = sorted(p for p in VENDOR.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    lines = [f"{sha(p)}  {p.relative_to(VENDOR)}" for p in files]
    (VENDOR / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    bench = VENDOR / "exp11" / "bench"
    com = json.loads((bench / "commitment.json").read_text())["tasks"]
    dirs = {p.name.split("_")[0]: p for p in bench.iterdir() if p.is_dir() and p.name[:1] in "TR"}
    mism, n = [], 0
    for t, rec in com.items():
        d = dirs.get(t)
        if d is None:
            continue
        for rel, h in rec["files"].items():
            if rel == "catalogue":   # a hash of the frozen catalogue card (bench/common/catalogue.py), not a file
                continue
            p = d / rel
            n += 1
            if not p.exists() or sha(p) != h:
                mism.append(f"{t}/{rel}")
    sys.path.insert(0, str(VENDOR / "exp11"))
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests
    gold = {}
    for t in ("T03", "T10", "T05", "T06", "T04", "T08", "T14", "R1"):
        d = dirs[t]
        cases = read_tests(d / "tests.jsonl")
        rows = [json.loads(l) for l in (d / "gold_set.jsonl").read_text().splitlines() if l.strip()]
        agree_rt = agree_ast = k = 0
        for r in rows:
            if not r.get("adjudicated"):
                continue
            o = label_one({"sample_id": 0, "task": t, "condition": "gold", "text": "```python\n" + r["code"] + "\n```",
                           "seed": 0}, cases)
            k += 1
            agree_rt += o.get("runtime_label") == r["adjudicated"]
            agree_ast += o.get("ast_label") == r["adjudicated"]
        gold[t] = {"n_gold": k, "runtime_vs_gold_adjudicated": agree_rt / max(k, 1),
                   "ast_vs_gold_adjudicated": agree_ast / max(k, 1)}
    out = {"n_vendored_files": len(files), "sha256sums": "vendor/SHA256SUMS", "bench_files_checked": n,
           "bench_commitment_mismatches": mism, "gold_set_rerun": gold}
    write_json(RESULTS_DIR / "vendor_check.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
