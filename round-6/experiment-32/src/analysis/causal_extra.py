#!/usr/bin/env python3
"""EXPLORATORY causal dose extension analysis (not pre-registered; see src/causal_extra.py).

Per task and cell: Y-share and default share (correct programs), pass rate, and exact McNemar on the 30 CRN pairs
against C0 (the S3 twin rows of the same slots) and against the matched random push of the same site and dose.
Writes results/causal_exploratory.json."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from stats import mcnemar_exact, rate  # noqa: E402


def jl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def main() -> dict[str, Any]:
    c3 = json.loads((ROOT / "predictions" / "commit3_causal.json").read_text())
    lab = jl(ROOT / "data" / "labels_causal_extra.jsonl")
    beh = jl(ROOT / "data" / "labels.jsonl")
    run = json.loads((ROOT / "results" / "causal_extra_run.json").read_text())
    out: dict[str, Any] = {"note": "exploratory, not pre-registered", "dimfull_norms": run.get("dimfull_norms"),
                           "tasks": {}}
    key = lambda r: (r["template"], int(r["slot"]))
    for ct in c3["causal_plan"]:
        t, D, Y = ct["task"], ct["default"], ct["Y"]
        C0 = {key(r): r for r in beh if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 6}
        cells = sorted({r["cell"] for r in lab if r["task"] == t})
        T: dict[str, Any] = {"default": D, "Y": Y, "C0": {"Y_share": rate([int(bool(r.get("passed")) and r["label"] == Y)
                                                                            for r in C0.values()])["rate"],
                                                           "default_share": rate([int(bool(r.get("passed")) and r["label"] == D)
                                                                                  for r in C0.values()])["rate"]},
                             "cells": {}}
        rows = {c: {key(r): r for r in lab if r["task"] == t and r["cell"] == c} for c in cells}
        for c in cells:
            R = rows[c]
            ks = sorted(set(R) & set(C0))
            yv = [int(bool(R[k].get("passed")) and R[k]["label"] == Y) for k in ks]
            y0 = [int(bool(C0[k].get("passed")) and C0[k]["label"] == Y) for k in ks]
            dv = [int(bool(R[k].get("passed")) and R[k]["label"] == D) for k in ks]
            d0 = [int(bool(C0[k].get("passed")) and C0[k]["label"] == D) for k in ks]
            cell = {"n": len(R), "Y_share": rate(yv)["rate"], "default_share": rate(dv)["rate"],
                    "pass_rate": rate([int(bool(r.get("passed"))) for r in R.values()])["rate"],
                    "labels": dict(Counter(r["label"] for r in R.values()).most_common()),
                    "vs_C0_Y": mcnemar_exact(yv, y0), "vs_C0_default": mcnemar_exact(dv, d0),
                    "delta_norm": float(next(iter(R.values())).get("delta_norm_ratio") or 0) if R else None}
            parts = c.split("_")
            if parts[2] in ("EDIT", "DIM", "DIMFULL"):
                rc = f"EXP_{parts[1]}_RAND_{parts[3]}"
                if rc in rows and parts[2] != "DIMFULL":
                    RR = rows[rc]
                    kk = sorted(set(R) & set(RR))
                    cell["vs_RAND_Y"] = mcnemar_exact([int(bool(R[k].get("passed")) and R[k]["label"] == Y) for k in kk],
                                                      [int(bool(RR[k].get("passed")) and RR[k]["label"] == Y) for k in kk])
            T["cells"][c] = cell
        out["tasks"][t] = T
    (ROOT / "results" / "causal_exploratory.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    r = main()
    for t, T in r["tasks"].items():
        print(t, T["default"], "->", T["Y"], "C0", T["C0"])
        for c, v in T["cells"].items():
            print("   ", c, "Y", round(v["Y_share"] or 0, 3), "D", round(v["default_share"] or 0, 3), "pass",
                  round(v["pass_rate"] or 0, 3), "vsC0 Y (b,c,p)", (v["vs_C0_Y"]["b"], v["vs_C0_Y"]["c"],
                                                                     round(v["vs_C0_Y"]["p"], 4)), "labels", v["labels"])


def follow_up() -> dict[str, Any]:
    """EXP2 cells (src/causal_extra2.py): GEN-site dose response, unrelated edit, matched-norm round trip, and the
    replication of GEN EDIT/RAND x8 on fresh slots 6-9 (pooled with slots 0-5 -> N = 50 CRN pairs)."""
    c3 = json.loads((ROOT / "predictions" / "commit3_causal.json").read_text())
    lab = jl(ROOT / "data" / "labels_causal_extra2.jsonl") + jl(ROOT / "data" / "labels_causal_extra.jsonl")
    beh = jl(ROOT / "data" / "labels.jsonl")
    key = lambda r: (r["template"], int(r["slot"]))
    out: dict[str, Any] = {"note": "exploratory follow-up, not pre-registered", "tasks": {}}
    for ct in c3["causal_plan"]:
        t, D, Y = ct["task"], ct["default"], ct["Y"]
        C0 = {key(r): r for r in beh if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 10}
        cells = {}
        for r in lab:
            if r["task"] == t:
                cells.setdefault(r["cell"], {})[key(r)] = r
        y = lambda r: int(bool(r.get("passed")) and r["label"] == Y)
        T: dict[str, Any] = {"default": D, "Y": Y, "cells": {}}
        for c, R in sorted(cells.items()):
            if not c.startswith(("EXP2_", "REP_", "EXP_GEN")):
                continue
            ks = sorted(set(R) & set(C0))
            T["cells"][c] = {"n": len(R), "Y_share": rate([y(R[k]) for k in R])["rate"],
                             "pass_rate": rate([int(bool(r.get("passed"))) for r in R.values()])["rate"],
                             "vs_C0": mcnemar_exact([y(R[k]) for k in ks], [y(C0[k]) for k in ks]),
                             "labels": dict(Counter(r["label"] for r in R.values()).most_common())}
        # pooled replication: slots 0-5 (EXP_GEN_*_x8) + slots 6-9 (REP_GEN_*_x8)
        for kind in ("EDIT", "RAND"):
            A = dict(cells.get(f"EXP_GEN_{kind}_x8", {}))
            A.update(cells.get(f"REP_GEN_{kind}_x8", {}))
            ks = sorted(set(A) & set(C0))
            T[f"pooled_GEN_{kind}_x8_vs_C0"] = mcnemar_exact([y(A[k]) for k in ks], [y(C0[k]) for k in ks]) | {
                "Y_share": rate([y(A[k]) for k in ks])["rate"], "C0_Y_share": rate([y(C0[k]) for k in ks])["rate"]}
        E = dict(cells.get("EXP_GEN_EDIT_x8", {}))
        E.update(cells.get("REP_GEN_EDIT_x8", {}))
        Rr = dict(cells.get("EXP_GEN_RAND_x8", {}))
        Rr.update(cells.get("REP_GEN_RAND_x8", {}))
        ks = sorted(set(E) & set(Rr))
        T["pooled_GEN_EDIT_vs_RAND_x8"] = mcnemar_exact([y(E[k]) for k in ks], [y(Rr[k]) for k in ks])
        for cmp in ("EXP2_GEN_UNREL_x8", "EXP2_GEN_RTM_x8"):
            X = cells.get(cmp, {})
            E6 = cells.get("EXP_GEN_EDIT_x8", {})
            kk = sorted(set(E6) & set(X))
            if kk:
                T[f"EDIT_x8_vs_{cmp}"] = mcnemar_exact([y(E6[k]) for k in kk], [y(X[k]) for k in kk])
        out["tasks"][t] = T
    (ROOT / "results" / "causal_exploratory_followup.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__" and (ROOT / "data" / "labels_causal_extra2.jsonl").exists():
    f = follow_up()
    for t, T in f["tasks"].items():
        print("FOLLOW-UP", t, T["default"], "->", T["Y"])
        for c, v in T["cells"].items():
            print("   ", c, "Y", round(v["Y_share"] or 0, 3), "pass", round(v["pass_rate"] or 0, 3),
                  "vsC0 (b,c,p)", (v["vs_C0"]["b"], v["vs_C0"]["c"], round(v["vs_C0"]["p"], 4)))
        for k in ("pooled_GEN_EDIT_x8_vs_C0", "pooled_GEN_RAND_x8_vs_C0", "pooled_GEN_EDIT_vs_RAND_x8",
                  "EDIT_x8_vs_EXP2_GEN_UNREL_x8", "EDIT_x8_vs_EXP2_GEN_RTM_x8"):
            if k in T:
                v = T[k]
                print("   ", k, {kk: (round(v[kk], 4) if isinstance(v.get(kk), float) else v.get(kk))
                                  for kk in ("n", "b", "c", "p", "effect", "Y_share", "C0_Y_share") if kk in v})
