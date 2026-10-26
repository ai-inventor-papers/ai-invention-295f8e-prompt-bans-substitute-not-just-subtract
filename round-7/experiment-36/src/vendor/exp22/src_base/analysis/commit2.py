#!/usr/bin/env python3
"""S6 commit #2 (after the S5 labels, before any ban sample): S5 behaviour summaries, the committed ADD-landing forecast
of the named ban's landing, secondary C1 forecasts, and the hash commit of every analysis file."""

from __future__ import annotations

from collections import Counter
from typing import Any

from loguru import logger

from analysis.common import merged, rows_of, shares
from cfg import BENCH, DEFAULT, RESULTS_DIR, SAMPLED_TASKS, read_jsonl, utc_now, write_json
from prereg import write_commit2

S5_ARMS = ["NEUTRAL", "ADD_a1.0", "ADD_a2.0", "ADD_a0.5", "RAND9001_a1.0", "RAND9002_a1.0", "RAND9003_a1.0",
           "RAND9001_a2.0", "RAND9002_a2.0", "RAND9003_a2.0"]


def s5_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in SAMPLED_TASKS:
        out[t] = {}
        for a in S5_ARMS:
            rs = rows_of(rows, t, a)
            if rs:
                out[t][a] = shares(rs, t)
    return out


def best_alpha(summ_t: dict[str, Any]) -> float | None:
    cands = []
    for al in (1.0, 2.0):
        s = summ_t.get(f"ADD_a{al}")
        if s and s["pass_rate"] >= 0.5 and s["n_attempted"] > 0:
            cands.append((s["avoidance"], -al, al))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][2]


def association_forecast(task: str) -> dict[str, Any] | None:
    if task in ("T1", "T2"):
        return None
    d = [p for p in BENCH.iterdir() if p.is_dir() and p.name.startswith(task + "_")]
    if not d:
        return None
    rows = [r for r in read_jsonl(d[0] / "association.jsonl") if r.get("X") == DEFAULT[task]]
    c = Counter(r["mapped"] for r in rows if r.get("mapped") and r["mapped"] != DEFAULT[task])
    return {"n": len(rows), "distribution": dict(c.most_common()), "modal": c.most_common(1)[0][0] if c else None}


def stage_commit2() -> dict[str, Any]:
    rows = merged()
    s5 = [r for r in rows if r.get("block_id", "").startswith("S5")]
    missing = [r["key"] for r in s5 if "label" not in r]
    if missing:
        raise RuntimeError(f"{len(missing)} S5 rows are not labelled yet; commit #2 must wait")
    if any(r.get("block_id", "").startswith("S7") for r in rows):
        raise RuntimeError("ban samples exist before commit #2")
    summ = s5_summary(rows)
    landings: dict[str, Any] = {"created_utc": utc_now(), "rule": "best alpha = alpha in {1,2} with the highest "
                                "avoidance among those with pass rate >= 0.5; ties -> alpha 1", "tasks": {}}
    c1: dict[str, Any] = {"created_utc": utc_now(), "families": {}, "note": "secondary; drop first"}
    for t in SAMPLED_TASKS:
        st = summ[t]
        ba = best_alpha(st)
        add = st.get(f"ADD_a{ba}") if ba else None
        landings["tasks"][t] = {"best_alpha": ba,
                                "forecast_landing": add["landing"] if add else None,
                                "forecast_modal": add["modal_nondefault"] if add else None,
                                "forecast_n_nondefault": add["n_nondefault"] if add else 0,
                                "forecast_testable": bool(add and add["n_nondefault"] >= 10)}
        pooled: Counter = Counter()
        for s in (9001, 9002, 9003):
            a = st.get(f"RAND{s}_a1.0")
            if a and a["n_nondefault"] >= 20:
                pooled.update(a["landing"])
        c1["families"][t] = {"ASSOCIATE": association_forecast(t),
                             "LADDER": {"distribution": dict(pooled.most_common()),
                                        "modal": pooled.most_common(1)[0][0] if pooled else None} if pooled else None,
                             "SUBTRACT": "undefined (no veto here; scored uniform, flagged)",
                             "PROXIMITY": "omitted (flagged)"}
    write_json(RESULTS_DIR / "s5_summary.json", summ)
    res = write_commit2(landings, c1)
    logger.info(f"commit #2: {len(res['chain'])} files; forecasts "
                f"{ {t: (v['best_alpha'], v['forecast_modal']) for t, v in landings['tasks'].items()} }")
    return {"landings": landings, "c1": c1}
