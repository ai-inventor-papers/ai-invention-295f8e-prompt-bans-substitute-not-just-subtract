#!/usr/bin/env python3
"""Replication of the route fractions in the independent second CRN draw (extras E2: slots k = 20-39, arms
'a@r2'..'d@r2') and the extended controls (E1). Same estimators as the committed analysis (ratio of sums, hierarchical
bootstrap), applied to the new slots; compared with the confirmatory draw (k = 0-19). Writes results/replication.json."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent / "analysis"))
import analysis as an  # noqa: E402

from cfg import RESULTS_DIR, STAGE_A, THRESHOLDS, read_json, write_json  # noqa: E402


def main() -> dict[str, Any]:
    rows = an.load_rows()
    gate = read_json(RESULTS_DIR / "gate.json")
    gated = [t for t in STAGE_A if gate[t]["gated"]]
    r2 = []
    for r in rows:
        if r["arm"].endswith("@r2"):
            q = dict(r)
            q["arm"] = r["arm"].split("@")[0]
            q["k"] = r["k"] - 20
            r2.append(q)
    tasks = [t for t in gated if all(any(x["task"] == t and x["arm"] == a for x in r2) for a in an.ROUTE_ARMS)]
    out: dict[str, Any] = {"tasks": tasks}
    if tasks:
        arr = an.slot_arrays(r2, tasks)
        pt = an.point_fractions(arr)
        boot = an.hier_boot(arr, n_boot=4000, seed=an.RNG_SEED + 50)
        out["pooled_r2"] = {k: {"point": v, "ci95": an.pct_ci(boot[k])} for k, v in pt.items()}
        out["per_task_r2"] = an.per_task_route(arr)
        main_rt = read_json(RESULTS_DIR / "route.json")["route"]
        out["pooled_main"] = main_rt.get("point")
        pairs = []
        for t in tasks:
            m = main_rt.get("per_task", {}).get(t)
            if m:
                pairs.append((t, m["F_prompt"]["point"], out["per_task_r2"][t]["F_prompt"]["point"],
                              m["F_direct"]["point"], out["per_task_r2"][t]["F_direct"]["point"]))
        out["per_task_main_vs_r2"] = [{"task": p[0], "F_prompt_main": p[1], "F_prompt_r2": p[2], "F_direct_main": p[3],
                                       "F_direct_r2": p[4]} for p in pairs]
        fp = [(p[1], p[2]) for p in pairs if np.isfinite(p[1]) and np.isfinite(p[2])]
        fd = [(p[3], p[4]) for p in pairs if np.isfinite(p[3]) and np.isfinite(p[4])]
        out["spearman_main_vs_r2"] = {
            "F_prompt": float(stats.spearmanr(*zip(*fp)).statistic) if len(fp) >= 3 else None,
            "F_direct": float(stats.spearmanr(*zip(*fd)).statistic) if len(fd) >= 3 else None}
        lo = out["pooled_r2"]["F_prompt"]["ci95"][0]
        sup = pt["F_prompt"] >= THRESHOLDS["F_confirm"] and lo > THRESHOLDS["F_ci_lower"]
        dis = pt["F_direct"] >= THRESHOLDS["F_direct_disconfirm"]
        out["verdict_r2_same_rule"] = "SUPPORTED" if sup and not dis else ("DISCONFIRMED" if dis and not sup else "MIXED")
        pooled = {}
        both = [x for x in rows if x["task"] in tasks and x["arm"] in an.ROUTE_ARMS] + r2
        for x in both:
            pass
        out["note"] = "independent uniforms; same prompts, engine, batch shape classes and labeller"
        _ = pooled
    # extended controls (E1 + Q9)
    sh = an.shares_table([r for r in rows if r["task"] in STAGE_A])
    ctrl = {}
    for t in STAGE_A:
        s = sh.get(t, {})
        if "pl" in s and "bB" in s:
            ctrl[t] = {"s_pl": s["pl"]["s"], "s_b_nounB": s["bB"]["s"], "diff": s["pl"]["s"] - s["bB"]["s"],
                       "placebo_pass": bool(abs(s["pl"]["s"] - s["bB"]["s"]) <= THRESHOLDS["placebo_tol"]),
                       "gated": t in gated}
        if "K0b" in s and "b" in s:
            ctrl.setdefault(t, {}).update({"s_K0b": s["K0b"]["s"], "s_b": s["b"]["s"],
                                           "K0b_pass": bool(s["b"]["s"] and s["K0b"]["s"] / s["b"]["s"] >= 0.9)})
    out["controls_all"] = ctrl
    out["placebo_pass_fraction"] = float(np.mean([v["placebo_pass"] for v in ctrl.values() if "placebo_pass" in v])) if ctrl else None
    # E3 prefill depth curve: P_open(depth) = (s_ban+D - s_a) / (s_twin+D - s_a); the SIG depth and NEU from Q4 beside it
    depth = {}
    dfile = Path(__file__).resolve().parents[1] / "predictions" / "prefill_depths.json"
    dd = read_json(dfile) if dfile.exists() else {}
    for t in gated:
        s = sh.get(t, {})
        if "a" not in s:
            continue
        sa = s["a"]["s"]
        cur = {}
        for pf in ("NEU", "D25", "SIG", "D50", "D75"):
            ban, twin = s.get(f"BAN+{pf}"), s.get(f"TWIN+{pf}")
            if ban is None or twin is None:
                continue
            den = twin["s"] - sa
            cur[pf] = {"s_ban": ban["s"], "s_twin": twin["s"], "P_open": (ban["s"] - sa) / den if den else float("nan"),
                       "n_prefix_tokens": (dd.get(t, {}).get(pf, {}) or {}).get("n"), "n_ban": ban["n_attempted"],
                       "ban_ci95": ban["ci95"]}
        depth[t] = cur
    out["prefill_depth_curve"] = depth
    write_json(RESULTS_DIR / "replication.json", out)
    logger.info(f"replication: pooled r2 {out.get('pooled_r2', {}).get('F_prompt')} / {out.get('pooled_r2', {}).get('F_direct')}; "
                f"verdict {out.get('verdict_r2_same_rule')}; placebo pass fraction {out['placebo_pass_fraction']}")
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("replication")
    main()
