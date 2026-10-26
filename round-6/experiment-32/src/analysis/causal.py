#!/usr/bin/env python3
"""S9 causal analysis (committed: its sha256 is in commit #2, before any causal sample).

Per (task, Y) and dose d: Y-share (correct and labelled Y, out of 30 CRN slots W1-W5 x 0-5) of EDIT_d against RT_d
(the unedited round trip at the same dose), exact McNemar on the CRN pairs; C0 (twin + identity hook = the S3 twin
rows of the same slots) reported beside it. PASS(task) iff for some d the EDIT-RT excess >= 0.20 with Holm(3 doses)
p < 0.05 AND the excess over max(UNREL_d, RAND_d) >= 0.10. The causal claim PASSES iff >= 2 tasks pass.
Reported beside it: DIM (difference in means at matched norm), the prompting ceiling (forced adherence), GEN, REV,
pass rate and default share per cell, per-slot flip matrices, breakage (invalid / length).

Usage: python analysis/causal.py   (writes results/causal.json)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from stats import holm, mcnemar_exact, rate  # noqa: E402

DOSE_TAGS = ("x1", "x2", "x4")


def jl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def slot_key(r: dict[str, Any]) -> tuple[str, int]:
    return (r["template"], int(r["slot"]))


def outcome(r: dict[str, Any] | None, Y: str) -> int | None:
    if r is None:
        return None
    return int(bool(r.get("passed")) and r.get("label") == Y)


def cell_rows(labels: list[dict[str, Any]], task: str, cell: str) -> dict[tuple[str, int], dict[str, Any]]:
    return {slot_key(r): r for r in labels if r["task"] == task and r.get("cell") == cell}


def cell_summary(rows: dict[tuple[str, int], dict[str, Any]], Y: str, D: str) -> dict[str, Any]:
    rs = list(rows.values())
    return {"n": len(rs), "Y_share": rate([outcome(r, Y) for r in rs]),
            "default_share": rate([int(bool(r.get("passed")) and r.get("label") == D) for r in rs]),
            "pass_rate": rate([int(bool(r.get("passed"))) for r in rs]),
            "invalid": sum(r.get("label") == "invalid" for r in rs),
            "length_capped": sum(r.get("finish_reason") == "length" for r in rs),
            "labels": dict(Counter(r.get("label") for r in rs).most_common())}


def paired_test(a: dict, b: dict, Y: str) -> dict[str, Any]:
    keys = sorted(set(a) & set(b))
    return mcnemar_exact([outcome(a[k], Y) for k in keys], [outcome(b[k], Y) for k in keys])


def flips(a: dict, b: dict) -> dict[str, int]:
    keys = sorted(set(a) & set(b))
    return dict(Counter(f"{b[k]['label']}->{a[k]['label']}" for k in keys).most_common(12))


def main() -> dict[str, Any]:
    c3p = ROOT / "predictions" / "commit3_causal.json"
    if not c3p.exists():
        return {}
    c3 = json.loads(c3p.read_text())
    labels = jl(ROOT / "data" / "labels_causal.jsonl")
    beh = jl(ROOT / "data" / "labels.jsonl")
    behaviour = json.loads((ROOT / "results" / "behaviour.json").read_text())
    out: dict[str, Any] = {"tasks": {}, "rule": "PASS(task) iff for some dose EDIT-RT >= 0.20, Holm(3) p < 0.05, "
                                                "and EDIT - max(UNREL, RAND) >= 0.10; claim iff >= 2 tasks"}
    n_pass = 0
    for ct in c3["causal_plan"]:
        t, D, Y = ct["task"], ct["default"], ct["Y"]
        C0 = {slot_key(r): r for r in beh if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 6}
        C0b = {slot_key(r): r for r in beh if r["task"] == t and r["arm"] == "BAN" and int(r["slot"]) < 6}
        T: dict[str, Any] = {"default": D, "Y": Y, "Y_source": ct.get("Y_source"), "C0": cell_summary(C0, Y, D),
                             "cells": {}, "tests": {}}
        cells = sorted({r["cell"] for r in labels if r["task"] == t})
        for c in cells:
            T["cells"][c] = cell_summary(cell_rows(labels, t, c), Y, D)
        ps, excess_ok = {}, {}
        for dt in DOSE_TAGS:
            E, RT = cell_rows(labels, t, f"PRE_EDIT_{dt}"), cell_rows(labels, t, f"PRE_RT_{dt}")
            if not E or not RT:
                continue
            m = paired_test(E, RT, Y)
            U, R = cell_rows(labels, t, f"PRE_UNREL_{dt}"), cell_rows(labels, t, f"PRE_RAND_{dt}")
            yE = np.mean([outcome(r, Y) for r in E.values()])
            ctrl = max([np.mean([outcome(r, Y) for r in X.values()]) for X in (U, R) if X] or [0.0])
            m["edit_minus_max_unrel_rand"] = float(yE - ctrl)
            m["vs_C0"] = paired_test(E, C0, Y)
            m["vs_DIM"] = paired_test(E, cell_rows(labels, t, f"PRE_DIM_{dt}"), Y) if cell_rows(labels, t, f"PRE_DIM_{dt}") else None
            m["flips_vs_RT"] = flips(E, RT)
            T["tests"][dt] = m
            ps[dt] = m["p"]
            excess_ok[dt] = bool(m["effect"] >= 0.20 and m["edit_minus_max_unrel_rand"] >= 0.10)
        hp = holm(ps) if ps else {}
        for dt in hp:
            T["tests"][dt]["p_holm"] = hp[dt]
        T["pass"] = any(excess_ok.get(dt) and hp.get(dt, 1) < 0.05 for dt in hp)
        n_pass += T["pass"]
        # GEN site and DIM vs RAND, REV
        for dt in ("x1", "x2"):
            G, GR = cell_rows(labels, t, f"GEN_EDIT_{dt}"), cell_rows(labels, t, f"GEN_RAND_{dt}")
            if G and GR:
                T["tests"][f"GEN_{dt}_vs_RAND"] = paired_test(G, GR, Y)
                T["tests"][f"GEN_{dt}_vs_C0"] = paired_test(G, C0, Y)
        for dt in DOSE_TAGS:
            DM, R = cell_rows(labels, t, f"PRE_DIM_{dt}"), cell_rows(labels, t, f"PRE_RAND_{dt}")
            if DM and R:
                T["tests"][f"DIM_{dt}_vs_RAND"] = paired_test(DM, R, Y)
        for dt in ("x2", "x4"):
            RV, RR = cell_rows(labels, t, f"REV_EDIT_{dt}"), cell_rows(labels, t, f"REV_RAND_{dt}")
            if RV and RR:
                T["tests"][f"REV_{dt}_vs_RAND_default"] = mcnemar_exact(
                    [int(bool(RV[k].get("passed")) and RV[k]["label"] == D) for k in sorted(set(RV) & set(RR))],
                    [int(bool(RR[k].get("passed")) and RR[k]["label"] == D) for k in sorted(set(RV) & set(RR))])
                T["tests"][f"REV_{dt}_vs_C0ban_default"] = mcnemar_exact(
                    [int(bool(RV[k].get("passed")) and RV[k]["label"] == D) for k in sorted(set(RV) & set(C0b))],
                    [int(bool(C0b[k].get("passed")) and C0b[k]["label"] == D) for k in sorted(set(RV) & set(C0b))])
        T["C0_ban"] = cell_summary(C0b, Y, D) if C0b else None
        T["prompting_ceiling_forced_adherence"] = behaviour["tasks"][t]["forced"].get(Y, {}).get("adherence")
        out["tasks"][t] = T
    out["n_tasks_pass"] = n_pass
    out["claim_pass"] = n_pass >= 2
    (ROOT / "results" / "causal.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    r = main()
    print({t: (v["pass"], {d: (round(x["effect"], 3), round(x["p"], 4)) for d, x in v["tests"].items() if d in DOSE_TAGS})
           for t, v in r.get("tasks", {}).items()}, "claim", r.get("claim_pass"))
