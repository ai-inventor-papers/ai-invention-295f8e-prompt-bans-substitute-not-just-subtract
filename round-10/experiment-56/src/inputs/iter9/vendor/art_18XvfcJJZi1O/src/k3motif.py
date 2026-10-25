#!/usr/bin/env python3
"""Committed motif function (CPU): class shares of |mean noising effect| over the exact-patched node list, validated on
Gemma's g1_pathpatch.json before any Qwen value is computed. Class correspondence Gemma -> Qwen: FORK -> DEC,
CSTAR -> OPEN, SPEC -> SPEC, COND -> COND."""

from __future__ import annotations

from typing import Any

import numpy as np

G2Q = {"FORK": "DEC", "CSTAR": "OPEN", "SPEC": "SPEC", "COND": "COND"}
QCL = ("COND", "SPEC", "OPEN", "DEC")


def motif(exact: list[dict[str, Any]], idx: list[int], signed: bool = False, exclude=None,
          class_map: dict[str, str] | None = None) -> dict[str, float]:
    """exact rows: {'node': 'kind|L|H|CLASS', 'noise_per_pair': [...]}. Share of class c = sum over nodes in c of
    |mean noising effect over pairs idx| / total (signed: signed sums over the signed total)."""
    tot = {c: 0.0 for c in QCL}
    for e in exact:
        kind, L, H, cl = e["node"].split("|")
        cl = (class_map or {}).get(cl, cl)
        if exclude is not None and exclude(kind, int(L[1:]), cl):
            continue
        v = float(np.mean(np.asarray(e["noise_per_pair"], dtype=float)[idx]))
        tot[cl] += v if signed else abs(v)
    s = sum(tot.values()) if signed else sum(abs(x) for x in tot.values())
    s = s if abs(s) > 1e-12 else 1e-12
    out = {c: tot[c] / s for c in QCL}
    out["COND+SPEC"] = out["COND"] + out["SPEC"]
    return out


def dec_stack_depth(exact: list[dict[str, Any]], idx: list[int], top: int, n_layers: int,
                    class_map: dict[str, str] | None = None, dec: str = "DEC") -> dict[str, Any]:
    """DEC-position nodes among the top `top` by |mean effect| with positive mean effect: effect-weighted mean of
    l / (n_layers - 1) and its [min, max]."""
    rows = []
    for e in exact:
        kind, L, H, cl = e["node"].split("|")
        cl = (class_map or {}).get(cl, cl)
        rows.append((abs(float(np.mean(np.asarray(e["noise_per_pair"], dtype=float)[idx]))),
                     float(np.mean(np.asarray(e["noise_per_pair"], dtype=float)[idx])), kind, int(L[1:]), cl))
    rows.sort(key=lambda r: -r[0])
    sel = [r for r in rows[:top] if r[4] == dec and r[1] > 0]
    if not sel:
        return {"n": 0, "depth": None, "min": None, "max": None, "nodes": []}
    w = np.array([r[1] for r in sel])
    d = np.array([r[3] / (n_layers - 1) for r in sel])
    return {"n": len(sel), "depth": float((w * d).sum() / w.sum()), "min": float(d.min()), "max": float(d.max()),
            "nodes": [f"{r[2]}|L{r[3]}|{r[4]}" for r in sel]}


BANDS = {"DEC": (0.38, 0.68), "COND": (0.21, 0.51), "depth": (0.45, 0.80)}


def label(shares: dict[str, float], depth: float | None) -> dict[str, Any]:
    checks = {"DEC_share_in_band": BANDS["DEC"][0] <= shares["DEC"] <= BANDS["DEC"][1],
              "COND_share_in_band": BANDS["COND"][0] <= shares["COND"] <= BANDS["COND"][1],
              "DEC_stack_depth_in_band": depth is not None and BANDS["depth"][0] <= depth <= BANDS["depth"][1]}
    differ = [k for k, v in checks.items() if not v]
    return {"checks": checks, "label": "MOTIF MATCH" if not differ else "DIFFERENT MOTIF", "differs_on": differ}
