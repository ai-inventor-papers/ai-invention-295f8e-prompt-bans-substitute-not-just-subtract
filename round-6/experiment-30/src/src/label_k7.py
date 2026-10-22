#!/usr/bin/env python3
"""exp9 extended / K=7 labeller for every T1 row (S-d), exp20 src/label_k7.py unchanged except paths. Runs in its own
process with inputs/exp9 first on sys.path (exp9's `common`, `tasks`, `labeller_ext`, `mb` packages collide by name
with the exp8 suite).

label_ext = exp9 mb/label.label_rows (hidden tests canonical + small tier, tracer probes, runtime/AST rules of
labeller_ext, blind judge openai/gpt-4.1-mini on disagreement, combine) over the 10-algorithm grid catalogue;
label_k7 = label_ext if it is in exp9's final analysis catalogue (bfs, dfs, bibfs, iddfs, astar, gbfs, idastar),
else 'other' (no code -> 'invalid'). Caches start from exp20's and are redirected into this artifact.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E9 = ROOT / "inputs" / "exp9"
sys.path.insert(0, str(E9))

import common as C9  # noqa: E402  (exp9 common.py)

C9.DATA_DIR = ROOT / "data"
import labeller_ext.judge as J9  # noqa: E402
import mb.label as L9  # noqa: E402

for name in ("k7_judge_cache.jsonl", "k7_eval_cache.jsonl"):
    src, dst = ROOT / "inputs" / "exp20" / "data" / name, ROOT / "data" / name
    if src.exists() and not dst.exists():
        shutil.copy(src, dst)
J9.CACHE = ROOT / "data" / "k7_judge_cache.jsonl"
J9.COST_FILE = ROOT / "results" / "openrouter_cost_k7.json"
L9.EVAL_CACHE = ROOT / "data" / "k7_eval_cache.jsonl"
L9.JUDGE_CAP_USD = 0.08

K7 = json.loads((E9 / "results" / "catalogue_keep.json").read_text())["analysis_catalogue_final"]["t1"]


def main() -> None:
    raw = [json.loads(l) for l in (ROOT / "data" / "samples_raw.jsonl").read_text().splitlines() if l.strip()]
    outp = ROOT / "data" / "labels_k7.jsonl"
    done = set()
    if outp.exists():
        done = {json.loads(l)["key"] for l in outp.read_text().splitlines() if l.strip()}
    rows = []
    for r in raw:
        if r["task"] != "T1":
            continue
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
        if key in done:
            continue
        rows.append({"key": key, "task": "t1", "text": r["text"], "finish_reason": r["finish_reason"]})
    if not rows:
        print("nothing to label")
        return
    out = L9.label_rows(rows, use_judge=True, purpose="iter6_k7")
    with outp.open("a") as fh:
        for o in out:
            lab = o["label"]
            k7 = "invalid" if lab == C9.NO_CODE else (lab if lab in K7 else "other")
            fh.write(json.dumps({"key": o["key"], "label_ext": lab, "label_k7": k7, "passed": bool(o.get("passed")),
                                 "runtime_label": o.get("runtime_label"), "ast_label": o.get("ast_label"),
                                 "judge_label": o.get("judge_label"), "labeller_source": o.get("labeller_source"),
                                 "code_sha256": o.get("code_sha256")}) + "\n")
    print(f"labelled {len(out)} T1 rows with the exp9 extended/K7 labeller")


if __name__ == "__main__":
    main()
