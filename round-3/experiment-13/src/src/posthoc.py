#!/usr/bin/env python3
"""POST-HOC sensitivity analyses (NOT pre-registered; written after the bans were sampled and the committed analysis
was run).  They do not replace the committed verdicts; they show what drives them.

(1) defined-only advance: a win counts only when the winning family's forecast is defined (the frozen rule scores an
    undefined forecast as uniform, so an undefined family can 'win' an event on which every defined forecast missed);
(2) every family against the UNIFORM reference: events on which each family beats uniform by >= 0.10 nats, and the
    mean log-score difference with a task-cluster bootstrap CI;
(3) the frozen advance rule re-run with UNIFORM as a fifth competitor;
(4) ban-landing overlap with each arm (which ban-free arm's landing is closest to the ban's, by JS) per gated task.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from common import DEFAULTS, FROZEN_CONSTANTS, RESULTS, read_jsonl, survivors, write_json
from score import PRIMARY, advance, js_divergence

ARMS_CMP = ["oneshot", "persistent", "iter1", "iter2", "iter3", "nonce", "novelty", "rand1", "rand2", "rand3", "sham",
            "bandpatch"]


def main() -> dict[str, Any]:
    from vllm_stage import Store

    ev = read_jsonl(RESULTS / "c1_events.jsonl")
    gated = [e for e in ev if e["gate_pass"]]
    dis = [e for e in gated if e["disagreeing"]]
    cfg = FROZEN_CONSTANTS["advance"]
    out: dict[str, Any] = {"note": __doc__}
    # (1) defined-only wins
    wins = {f: 0 for f in PRIMARY}
    per = []
    for e in dis:
        w = None
        for f in PRIMARY:
            oth = [e["logscore"][g] for g in PRIMARY if g != f]
            if e["defined"][f] and e["logscore"][f] - max(oth) >= cfg["margin_nats"]:
                wins[f] += 1
                w = f
        per.append({"task": e["task"], "winner_defined_only": w,
                    "defined": {f: e["defined"][f] for f in PRIMARY}})
    out["defined_only_advance"] = {"wins": wins, "advancing": [f for f in PRIMARY if wins[f] >= cfg["min_wins"]],
                                   "per_event": per}
    # (2) vs uniform
    rng = np.random.default_rng(11)
    vs = {}
    for f in PRIMARY + ["SUBTRACT_1SHOT", "FRLP_FP8"]:
        d = np.array([e["logscore"][f] - e["logscore"]["UNIFORM"] for e in gated])
        boots = [float(np.mean(d[rng.integers(0, len(d), len(d))])) for _ in range(2000)] if len(d) else []
        vs[f] = {"n_events": len(d), "n_beats_uniform_by_0.10": int(np.sum(d >= 0.10)),
                 "n_worse_than_uniform_by_0.10": int(np.sum(d <= -0.10)),
                 "mean_diff_vs_uniform": float(np.mean(d)) if len(d) else None,
                 "task_bootstrap_95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))]
                 if boots else None,
                 "n_defined": sum(1 for e in gated if e["defined"][f])}
    out["vs_uniform_gated"] = vs
    # (3) frozen rule with UNIFORM as a competitor
    out["advance_with_uniform_competitor"] = advance(
        [{"task": e["task"], "logscore": {f: e["logscore"][f] for f in PRIMARY + ["UNIFORM"]}} for e in dis],
        PRIMARY + ["UNIFORM"], cfg["margin_nats"], cfg["min_wins"])
    # (4) closest ban-free arm landing to the ban landing
    st = Store("")
    rand = st.lab_rows("rand")
    labs = {a: st.lab_rows(a) for a in ARMS_CMP if not a.startswith("rand")}
    for k in (1, 2, 3):
        labs[f"rand{k}"] = [r for r in rand if r.get("arm") == f"rand{k}"]
    close = {}
    for e in gated:
        t = e["task"]
        S = survivors(t)
        sp = S + ["other"]
        bl = Counter(e["landing_counts"])
        nb = sum(bl.values())
        pb = {k: bl.get(k, 0) / nb for k in sp}
        rows = {}
        for a, ls in labs.items():
            c = Counter((r["label"] if r["label"] in S else "other") for r in ls
                        if r["task"] == t and r["label"] not in ("invalid", DEFAULTS[t]))
            n = sum(c.values())
            if n >= 5:
                rows[a] = {"n_non_default": n, "js_to_ban": js_divergence({k: c.get(k, 0) / n for k in sp}, pb),
                           "modal": max(sp, key=lambda k: (c.get(k, 0), -sp.index(k)))}
        close[t] = {"ban_modal": e["realised_top1"], "arms": dict(sorted(rows.items(),
                                                                          key=lambda kv: kv[1]["js_to_ban"]))}
    out["closest_arm_to_ban_landing"] = close
    write_json(RESULTS / "posthoc_sensitivity.json", out)
    logger.info(f"post-hoc defined-only wins {wins}; vs uniform: " +
                ", ".join(f"{f}:{v['mean_diff_vs_uniform']:+.2f}" for f, v in vs.items()
                          if v["mean_diff_vs_uniform"] is not None))
    return out


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s3_posthoc")
    main()
