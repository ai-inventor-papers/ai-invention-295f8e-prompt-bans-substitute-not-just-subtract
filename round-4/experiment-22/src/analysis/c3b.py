#!/usr/bin/env python3
"""C3b (descriptive): forecasting where a ban lands from push landings and from the opening ladder.

Scored set: the 5 gated iteration-3 bench events (exp13 c1_events, gate_pass = True; already seen, so descriptive).
Forecasts over S = catalogue minus the banned default, plus 'other':
  PUSH    excess-weighted off-default composition of this artifact's confirmed escapes (results/escape.json);
  PUSH_SCREEN  the same from the iteration-3 screen (sensitivity);
  LADDER_OPEN  softmax over survivors X of the teacher-forced log-probability of X's modal opening under the 5
               neutral twins (results/opening_lp.json);
  ASSOCIATE, PROXIMITY  the exp13 forecasts on record.
Smoothing and log score: exp13 src/score.py (0.93 raw + 0.05 uniform(S) + 0.02 'other'); score = mean ln p over the
realised non-banned attempts (exp13 landing_counts), with exp16's full-ban arm ('observed') as a replication.
Departure rule: where the realised top-1 is not the PUSH top-1, exp16's F_direct is reported (pooled over its 5
route tasks; prediction >= 0.25). Across 14 tasks: Spearman of movability (v4 E_t) and the opening margin
lp(default) - max_X lp(X) with exp13 avoidance. R2's movability is recorded as a prediction for a future ban.
"""

from __future__ import annotations

import importlib.util
import math
from typing import Any

import numpy as np

from cfg4 import DEFAULT4, E13, E16, PATH_TASKS, RESULTS_DIR, ROOT, TASKS15, read_json, read_jsonl
from common import spearman
from screen import catalogue

_spec = importlib.util.spec_from_file_location("score13", ROOT / "inputs/exp13/src/score.py")
SC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SC)


def softmax(d: dict[str, float]) -> dict[str, float]:
    m = max(d.values())
    e = {k: math.exp(v - m) for k, v in d.items()}
    z = sum(e.values())
    return {k: v / z for k, v in e.items()}


def run(rows, commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    screen = read_json(RESULTS_DIR / "screen.json")
    olp = read_json(RESULTS_DIR / "opening_lp.json")["by_task"] if (RESULTS_DIR / "opening_lp.json").exists() else {}
    ev13 = {e["task"]: e for e in read_jsonl(E13 / "results" / "c1_events.jsonl")}
    ev16 = {e["task"]: e for e in read_jsonl(E16 / "results" / "c1_events.jsonl")}
    route = read_json(E16 / "results" / "route.json")["route"]
    events = {}
    for t, e in ev13.items():
        d = e["banned"]
        S = [m for m in catalogue(t) if m != d]
        labels = [k for k, v in e["landing_counts"].items() for _ in range(v)]
        fc: dict[str, Any] = {}
        pv = esc.get(t, {}).get("push_landing_v4") or {}
        fc["PUSH"] = SC.p_from_counts(pv, S) if pv else None
        ps = screen["tasks"].get(t, {}).get("push_landing") or {}
        fc["PUSH_SCREEN"] = SC.p_from_counts(ps, S) if ps else None
        margin = None
        if t in olp:
            lp = {m: v["lp"] for m, v in olp[t].items() if v.get("lp") is not None}
            surv = {m: v for m, v in lp.items() if m in S}
            if surv:
                fc["LADDER_OPEN"] = {**softmax(surv), "other": 0.0}
                for m in S:
                    fc["LADDER_OPEN"].setdefault(m, 0.0)
            if d in lp and surv:
                margin = lp[d] - max(surv.values())
        fc["ASSOCIATE"] = e["forecasts"].get("ASSOCIATE")
        fc["PROXIMITY"] = e["forecasts"].get("PROXIMITY")
        sc, top = {}, {}
        rep = {}
        obs16 = ev16.get(t, {}).get("observed")
        lab16 = [k for k, v in (obs16 or {}).items() for _ in range(v)]
        for fam, p in fc.items():
            ps_ = SC.smooth(p, S)
            sc[fam] = SC.logscore(ps_, labels) if labels else None
            top[fam] = SC.top1(p, S)[0]
            rep[fam] = SC.logscore(ps_, [l if l in S or l == "other" else "other" for l in lab16]) if lab16 else None
        real = SC.realised_top1(labels, S)
        rec = {"task": t, "banned": d, "gate_pass": e["gate_pass"], "n_non_banned": len(labels),
               "realised_top1": real, "forecast_top1": top, "logscore": sc, "logscore_exp16_replication": rep,
               "defined": {k: v is not None for k, v in fc.items()}, "opening_margin": margin,
               "avoidance_exp13": e.get("avoidance")}
        if sc.get("PUSH") is not None:
            rec["diff_PUSH_minus"] = {f: (sc["PUSH"] - sc[f]) if sc.get(f) is not None else None
                                      for f in ("ASSOCIATE", "PROXIMITY", "LADDER_OPEN", "PUSH_SCREEN")}
        if top.get("PUSH") and real and top["PUSH"] not in real:
            rec["departure"] = {"exp16_F_direct_pooled": route["point"]["F_direct"], "prediction": ">= 0.25",
                                "note": "exp16 reports F_direct pooled over its 5 route tasks, not per task"}
        events[t] = rec
    gated = [t for t, r in events.items() if r["gate_pass"]]
    summary = {}
    for fam in ("PUSH", "PUSH_SCREEN", "LADDER_OPEN", "ASSOCIATE", "PROXIMITY"):
        v = [events[t]["logscore"].get(fam) for t in gated if events[t]["logscore"].get(fam) is not None
             and events[t]["defined"].get(fam)]
        hits = [events[t]["forecast_top1"].get(fam) in events[t]["realised_top1"] for t in gated
                if events[t]["forecast_top1"].get(fam)]
        vu = [events[t]["logscore"].get(fam) for t in gated if events[t]["logscore"].get(fam) is not None]
        summary[fam] = {"mean_logscore": float(np.mean(v)) if v else None, "n_defined": len(v),
                        "mean_logscore_incl_undefined_as_uniform": float(np.mean(vu)) if vu else None,
                        "top1_hits": int(sum(hits)), "n_top1": len(hits)}
    # 14-task screen-rule check
    mov, marg, av = [], [], []
    tabl = {}
    from cfg4 import E17
    l17 = read_jsonl(E17 / "data" / "labels.jsonl")
    av17 = {}
    for tt in PATH_TASKS:
        b = [r for r in l17 if r["task"] == tt and r["arm"] == "BAN" and r["label"] not in ("invalid", "disputed")]
        if b:
            av17[tt] = sum(r["label"] != DEFAULT4[tt] for r in b) / len(b)
    for t in TASKS15:
        if t == "R2":
            continue
        et = esc.get(t, {}).get("E_t", {})
        e_any = max([(et.get(a) or {}).get("E_t") or 0.0 for a in ("1.0", "2.0")] or [0.0])
        a = (ev13.get(t) or {}).get("avoidance")
        if a is None:
            a = av17.get(t)
        m = events.get(t, {}).get("opening_margin")
        tabl[t] = {"E_t_max_alpha_le2": e_any, "opening_margin": m, "avoidance_exp13": a}
        if a is not None:
            mov.append(e_any)
            av.append(a)
            marg.append(m if m is not None else np.nan)
    ok = [i for i, x in enumerate(marg) if np.isfinite(x)]
    out = {"events": events, "gated_events": gated, "summary_gated": summary, "screen_rule_table": tabl,
           "spearman_movability_vs_avoidance": spearman(np.array(mov), np.array(av)) if len(mov) > 2 else None,
           "spearman_opening_margin_vs_avoidance": spearman(np.array([marg[i] for i in ok]),
                                                            np.array([av[i] for i in ok])) if len(ok) > 2 else None,
           "R2_prediction": {"movable": bool(esc.get("R2", {}).get("movable")),
                             "E_t": esc.get("R2", {}).get("E_t"),
                             "push_landing": esc.get("R2", {}).get("push_landing_v4"),
                             "note": "committed prediction for a future R2 ban (no R2 ban was rendered)"}}
    return out
