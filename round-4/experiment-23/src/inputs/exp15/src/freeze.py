#!/usr/bin/env python3
"""C4-C6: decision set (homogeneity test pilot-FP8 vs bf16), frozen default D per task, present-minor events,
ASSOCIATE targets from Llama's own association answers.  Writes predictions/events.json and
predictions/association_targets.json (later hash-chained with the forecasts)."""

from __future__ import annotations

import collections
from typing import Any

from loguru import logger

from src import prompts_llama as P
from src.commit import utc_now
from src.stats_util import ffh_mc, hill1, wilson
from src.ws import FROZEN_TASKS, PRED, RESULTS, read_json, write_json

NOT_ALG = ("invalid", "other", "unresolved")


def _counts(rows: list[dict], correct: bool = False) -> collections.Counter:
    return collections.Counter(r["label"] for r in rows if r["label"] != "invalid" and (not correct or r.get("passed")))


def decision_sets(labels: list[dict]) -> dict[str, Any]:
    out = {}
    for t in FROZEN_TASKS:
        pil = [r for r in labels if r["task"] == t and r.get("phase") == "pilot"]
        b1 = [r for r in labels if r["task"] == t and r.get("phase") == "B1"]
        b4 = [r for r in labels if r["task"] == t and r.get("phase") == "B4"]
        la = [r["label"] for r in pil if r["label"] != "invalid"]
        lb = [r["label"] for r in b1 if r["label"] != "invalid"]
        test = ffh_mc(la, lb, draws=100_000, seed=0)
        use_bf16 = test["p"] < 0.01
        dec = (b1 + b4) if use_bf16 else (pil + b1)
        out[t] = {"homogeneity": test, "decision_set": "bf16_B1+B4" if use_bf16 else "pooled_pilot+B1",
                  "rows": dec, "alt_rows": (pil + b1) if use_bf16 else (b1 + b4)}
    return out


def freeze_default(t: str, rows: list[dict]) -> dict[str, Any]:
    modes = P.modes(t)
    att = [r for r in rows if r["label"] != "invalid"]
    ca = _counts(rows)
    cc = _counts(rows, correct=True)
    cc_alg = {m: cc.get(m, 0) for m in modes}
    n_correct = sum(cc.values())
    ranked = sorted(modes, key=lambda m: (-cc_alg[m], modes.index(m)))
    att_alg = {m: ca.get(m, 0) for m in modes}
    att_mode = sorted(modes, key=lambda m: (-att_alg[m], modes.index(m)))[0]
    lead = cc_alg[ranked[0]] - (cc_alg[ranked[1]] if len(ranked) > 1 else 0)
    if n_correct >= 10 and lead >= 2:
        D, flag = ranked[0], False
    else:
        D, flag = att_mode, True
    n_att = len(att)
    sD = att_alg[D] / max(n_att, 1)
    return {"D": D, "D_from_attempts": flag, "attempted_mode": att_mode, "n_valid": n_att, "n_rows": len(rows),
            "n_invalid": len(rows) - n_att, "s_D_attempted": sD, "s_D_wilson": wilson(att_alg[D], n_att),
            "n_correct": n_correct, "correct_counts": dict(cc), "attempted_counts": dict(ca),
            "hill_cc": hill1(cc.values()), "lead_correct": lead}


def present_minor(t: str, rows: list[dict], D: str) -> list[dict[str, Any]]:
    cc = _counts(rows, correct=True)
    n_correct = sum(cc.values())
    out = []
    if n_correct < 10:
        return out
    for m in P.modes(t):
        if m == D:
            continue
        k = cc.get(m, 0)
        if k >= 3 and k / n_correct >= 0.10:
            out.append({"task": t, "A": m, "correct_count": k, "correct_share": k / n_correct, "n_correct": n_correct})
    return out


def associate_targets(assoc: list[dict]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for t in FROZEN_TASKS:
        modes = P.modes(t)
        for x in modes:
            rs = [a for a in assoc if a["task"] == t and a["X"] == x]
            cnt = collections.Counter(a["mapped"] for a in rs if a["category"] == "survivor")
            dist = dict(collections.Counter(a["mapped"] for a in rs))
            if cnt:
                best = sorted(cnt, key=lambda m: (-cnt[m], modes.index(m)))[0]
            else:
                best = None
            out[f"{t}|{x}"] = {"task": t, "X": x, "target": best, "defined": best is not None,
                               "survivor_counts": dict(cnt), "mapped_distribution": dict(dist), "n_answers": len(rs)}
    return out


def run(labels: list[dict], assoc: list[dict]) -> dict[str, Any]:
    ds = decision_sets(labels)
    x0 = read_json(PRED / "x0.json")["x0"]
    tasks, minors, decision_meta = {}, [], {}
    for t in FROZEN_TASKS:
        dec = ds[t]["rows"]
        fd = freeze_default(t, dec)
        alt = freeze_default(t, ds[t]["alt_rows"])
        fd["X0"] = x0[t]
        fd["D_equals_X0"] = fd["D"] == x0[t]
        fd["decision_set"] = ds[t]["decision_set"]
        fd["homogeneity_p"] = ds[t]["homogeneity"]["p"]
        fd["alt_decision_set_D"] = alt["D"]
        fd["excluded_from_C1"] = fd["n_valid"] < 20
        tasks[t] = fd
        minors += present_minor(t, dec, fd["D"])
        decision_meta[t] = {"homogeneity": ds[t]["homogeneity"], "decision_set": ds[t]["decision_set"],
                            "decision_row_ids": [r["row_id"] for r in dec],
                            "alt_row_ids": [r["row_id"] for r in ds[t]["alt_rows"]], "alt": alt}
    minors = sorted(minors, key=lambda e: (-e["correct_share"], FROZEN_TASKS.index(e["task"]), e["A"]))[:6]
    events = []
    for t in FROZEN_TASKS:
        events.append({"event_id": f"{t}|modal|{tasks[t]['D']}", "task": t, "event_type": "modal",
                       "banned": tasks[t]["D"], "D": tasks[t]["D"]})
    for e in minors:
        events.append({"event_id": f"{e['task']}|present_minor|{e['A']}", "task": e["task"],
                       "event_type": "present_minor", "banned": e["A"], "D": tasks[e["task"]]["D"], "minor": e})
    at = associate_targets(assoc)
    out = {"utc": utc_now(), "tasks": tasks, "present_minor": minors, "events": events,
           "rule": {"D": ">=10 correct and lead >= 2 -> modal correct label, else modal attempted (D_from_attempts)",
                    "present_minor": "A != D, >=10% of correct, >=3 correct, task >=10 correct; at most 6 by share",
                    "homogeneity": "FFH Monte Carlo 100k seed 0; p<0.01 -> decision set = 100 bf16 free samples"}}
    write_json(PRED / "events.json", out)
    write_json(PRED / "association_targets.json", at)
    write_json(RESULTS / "decision_sets.json", decision_meta)
    logger.info(f"frozen D: { {t: v['D'] for t, v in tasks.items()} }; present-minor: "
                f"{[(e['task'], e['A']) for e in minors]}")
    return out
