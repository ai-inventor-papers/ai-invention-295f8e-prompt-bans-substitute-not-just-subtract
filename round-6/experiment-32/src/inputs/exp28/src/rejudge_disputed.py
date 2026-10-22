#!/usr/bin/env python3
"""SENSITIVITY (after commit #1): rows left 'disputed' because the inline judge was unavailable (HTTP 429 rate limits
during the pt plain-completion burst) are re-judged with the SAME frozen judges (bench j1, suite gpt-4.1-mini).
The committed predictor table is NOT changed; results/rejudge_disputed.json feeds the 'beta with re-judged disputed
rows' sensitivity of E-A1."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, EXP8_TASK, RESULTS_DIR, ROOT, bench_paths, read_jsonl, setup_logging, write_json

bench_paths()


def main() -> None:
    setup_logging("rejudge_disputed")
    from loguru import logger
    import bench.common.judge as BJ
    import labeller.judge as J

    labs = [r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r["label"] == "disputed"
            and r.get("labeller_source") == "judge_unavailable" and r.get("code")]
    bench = [r for r in labs if r["task"] not in EXP8_TASK]
    path = [r for r in labs if r["task"] in EXP8_TASK]
    out = {}
    if bench:
        BJ.PERSONAL_CAP = 0.80
        recs = BJ.Judge(ROOT).label_many([("j1", r["task"], r["code"]) for r in bench])
        for r, rec in zip(bench, recs):
            out[r["row_id"]] = (rec or {}).get("label")
    if path:
        J.CACHE = DATA_DIR / "judge_cache_paths.jsonl"
        J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths.json"
        res, _ = J.judge_many([{"task": EXP8_TASK[r["task"]], "code": r["code"]} for r in path], "openai/gpt-4.1-mini",
                              "iter5_rejudge_disputed", 0.10, concurrency=4)
        for r, rec in zip(path, res):
            out[r["row_id"]] = (rec or {}).get("label")
    n_ok = sum(1 for v in out.values() if v)
    write_json(RESULTS_DIR / "rejudge_disputed.json", {"n_disputed_unavailable": len(labs), "n_rejudged": n_ok,
                                                        "labels": out,
                                                        "note": "sensitivity only; the committed labels are unchanged"})
    logger.info(f"re-judged {n_ok}/{len(labs)} disputed rows")


if __name__ == "__main__":
    main()
