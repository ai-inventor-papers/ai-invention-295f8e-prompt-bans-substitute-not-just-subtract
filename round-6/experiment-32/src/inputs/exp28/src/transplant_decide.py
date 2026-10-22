#!/usr/bin/env python3
"""Transplant VALIDITY SWITCH (declared in commit #0): T at lambda 1 on N = 10 per S_T task (slots 0-1 per template);
if pass < 0.8 x twin pass on more than half of S_T, lambda = 0.5 for T, RND and XT on all tasks (selected on validity
only, never on the outcome). Writes results/transplant_lambda.json."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, PRED_DIR, RESULTS_DIR, read_json, read_jsonl, setup_logging, write_json


def main() -> None:
    setup_logging("transplant_decide")
    from loguru import logger

    c1 = read_json(PRED_DIR / "commit_E1.json")
    labs = read_jsonl(DATA_DIR / "labels.jsonl")
    per = {}
    for u in c1["transplant"]["S_T"]:
        tw = [r for r in labs if r.get("stage") == "twin" and r["task"] == u and r["arm"] == "twin"]
        tv = [r for r in labs if r.get("stage") == "transplant_valid" and r["task"] == u and r["arm"] == "T"]
        pt = sum(1 for r in tw if r.get("passed")) / len(tw)
        pv = sum(1 for r in tv if r.get("passed")) / len(tv) if tv else None
        per[u] = {"n_valid_rows": len(tv), "pass_T_lambda1": pv, "pass_twin": pt,
                  "breaks": pv is None or pv < 0.8 * pt,
                  "labels_T_lambda1": dict(__import__("collections").Counter(r["label"] for r in tv))}
    n_break = sum(1 for v in per.values() if v["breaks"])
    lam = 0.5 if n_break > len(per) / 2 else 1.0
    out = {"lambda": lam, "n_S_T": len(per), "n_broken_at_lambda1": n_break, "per_unit": per,
           "rule": "lambda 0.5 if T pass < 0.8 x twin on more than half of S_T (validity only)"}
    write_json(RESULTS_DIR / "transplant_lambda.json", out)
    logger.info(f"transplant lambda = {lam}; broken at 1: {n_break}/{len(per)}; {per}")


if __name__ == "__main__":
    main()
