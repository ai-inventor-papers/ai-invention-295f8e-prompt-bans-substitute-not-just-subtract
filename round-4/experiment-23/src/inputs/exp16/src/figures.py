#!/usr/bin/env python3
"""Figures from results/*.json via the aii-data-fig-gen generator (JSON spec -> PDF + PNG, deterministic).
Error bars show the LARGER side of each (possibly asymmetric) 95% interval, so they never understate it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import FIG_DIR, PATH_TASKS, RESULTS_DIR, STAGE_A, read_json

GEN = Path(os.environ.get("AII_FIG_GEN") or (Path(os.environ.get("AII_SKILLS_DIR", ".")) / "aii-data-fig-gen" / "scripts"
                                                / "chart_gen.py"))  # set AII_SKILLS_DIR to the aii skills folder


def _half(pt: float, ci: list[float]) -> float:
    if pt is None or ci is None or any(c is None or not np.isfinite(c) for c in ci) or not np.isfinite(pt):
        return 0.0
    return float(max(abs(pt - ci[0]), abs(ci[1] - pt)))


def _num(x: Any) -> float:
    return float(x) if x is not None and np.isfinite(x) else 0.0


def render(name: str, spec: dict[str, Any]) -> bool:
    p = FIG_DIR / f"{name}.json"
    p.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([sys.executable, str(GEN), "--spec", str(p), "--out", str(FIG_DIR / name)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f"figure {name} failed: {r.stderr[-600:]}")
        return False
    logger.info(f"figure {name} written")
    return True


def make_figures() -> dict[str, bool]:
    an = read_json(RESULTS_DIR / "analysis.json")
    shares = an["shares"]
    ok = {}
    # (1) per-task banned (default) share by arm with Wilson CIs
    tasks = [t for t in STAGE_A if "a" in shares.get(t, {})]
    # an arm is drawn only if every task has it: a missing arm must never be drawn as a measured zero
    arms = [a for a in ("a", "b", "c", "d", "K0") if all(a in shares.get(t, {}) for t in tasks)]
    series = []
    names = {"a": "a: full ban", "b": "b: neutral twin", "c": "c: prompt route", "d": "d: direct route",
             "K0": "K0: span knocked out"}
    for a in arms:
        vals, errs = [], []
        for t in tasks:
            s = shares[t].get(a)
            vals.append(_num(s["s"]) if s else 0.0)
            errs.append(_half(s["s"], s["ci95"]) if s else 0.0)
        series.append({"label": names[a], "values": vals, "errors": errs})
    ok["fig1_arm_shares"] = render("fig1_arm_shares", {
        "type": "bar", "title": "Default-mechanism share per arm (Wilson 95% CI)", "xlabel": "Bench task",
        "ylabel": "Default share", "aspect": "2:1", "categories": tasks, "series": series})
    # (2) pooled route fractions with the three intervals
    rt = an["route"]
    if rt.get("n_tasks"):
        cats, vals, errs = [], [], []
        prim = rt.get("primary_interval", "percentile")
        for k, kind, lab in (("F_prompt", prim, f"F_prompt ({prim}, primary)"), ("F_prompt", "percentile", "F_prompt (percentile)"),
                             ("F_direct", prim, f"F_direct ({prim}, primary)"), ("F_direct", "percentile", "F_direct (percentile)"),
                             ("I", prim, f"Interaction I ({prim})"), ("F_K0", prim, f"F_K0 ({prim})")):
            if k in rt["point"]:
                cats.append(lab)
                vals.append(_num(rt["point"][k]))
                errs.append(_half(rt["point"][k], rt["intervals"][k][kind]))
        ok["fig2_route_fractions"] = render("fig2_route_fractions", {
            "type": "forest", "null_line": 0.0, "title": f"Pooled route fractions over {rt['n_tasks']} gated tasks",
            "xlabel": "Fraction of the ban's effect (ratio of sums)", "aspect": "4:3", "categories": cats,
            "series": [{"values": vals, "errors": errs}]})
    # (3) V_t against F_direct, coloured by the committed class
    c2c = an["c2c"]
    by_cls: dict[str, list] = {}
    for r in c2c.get("rows", []):
        if r["gated"] and r["V"] is not None and r["F_direct"] is not None and np.isfinite(r["V"]) and np.isfinite(r["F_direct"]):
            by_cls.setdefault(r["class"] or "UNDEFINED", []).append((r["V"], r["F_direct"]))
    if by_cls:
        ser = [{"label": f"committed {c}", "x": [p[0] for p in v], "values": [p[1] for p in v]} for c, v in sorted(by_cls.items())]
        ok["fig3_veto_vs_direct"] = render("fig3_veto_vs_direct", {
            "type": "scatter", "title": "Veto sufficiency V_t vs F_direct, gated tasks (all committed HIGH_DIRECT: F_direct >= 0.25)",
            "xlabel": "V_t = share of V1 attempts off the default", "ylabel": "F_direct", "aspect": "4:3",
            "series": ser})
    # (4) first divergence from arm b (CRN), pooled over tasks
    ser = []
    for X, lab in (("a", "a: full ban"), ("c", "c: prompt route"), ("d", "d: direct route"), ("V1", "V1: one-shot veto")):
        vals = []
        for t in STAGE_A:
            fd = an["crn"].get(t, {}).get("first_divergence", {}).get(X)
            if fd:
                vals += fd["values"]
        if len(vals) >= 5:
            ser.append({"label": lab, "values": [float(v) for v in vals]})
    if ser:
        ok["fig4_first_divergence"] = render("fig4_first_divergence", {
            "type": "ecdf", "title": "First generated token where an arm departs from arm b (same slot)",
            "xlabel": "Token index of first divergence", "ylabel": "Cumulative fraction of slots", "aspect": "16:9",
            "series": ser})
    # (5) prefill P_open per gated task
    pre = an["prefill"]
    if pre:
        tasks5 = [t for t in pre if "SIG" in pre[t] or "NEU" in pre[t]]
        ser = []
        for pf, lab in (("SIG", "signature opening"), ("NEU", "neutral def line")):
            ser.append({"label": lab, "values": [_num(pre[t].get(pf, {}).get("P_open")) for t in tasks5]})
        ok["fig5_prefill_popen"] = render("fig5_prefill_popen", {
            "type": "bar", "title": "Prefill: share of the ban undone by a forced opening (P_open)",
            "xlabel": "Gated bench task", "ylabel": "P_open", "aspect": "16:9", "categories": tasks5, "series": ser})
    # (6) path screen: off-default share per veto round
    scr = an["screen"]
    if scr.get("rounds"):
        rounds = [r for r in ("b", "V1", "OPEN", "VP", "R2", "R3") if any(r in scr["rounds"].get(t, {}) for t in PATH_TASKS)]
        ser = []
        for t in PATH_TASKS:
            ser.append({"label": {"t1": "T1 grid path (default BFS)", "t2": "T2 weighted path (default Dijkstra)"}[t],
                        "values": [_num(scr["rounds"].get(t, {}).get(r, {}).get("off_default")) for r in rounds]})
        ok["fig6_screen_rounds"] = render("fig6_screen_rounds", {
            "type": "bar", "title": "Path screen: share off the default per veto round (max 0.01)",
            "xlabel": "Arm / veto round", "ylabel": "Share off the default", "aspect": "16:9", "ylim": [0, 1],
            "categories": rounds, "series": ser})
    return ok


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("figures")
    print(make_figures())
