#!/usr/bin/env python3
"""Two-stage escape rule (exp22 analysis/c2a.direction_table + screen.summarise, unchanged), committed at #0.

share = catalogue off-default over VALID attempts ('other' is never off-default; invalid / disputed rows are dropped
from the denominator); pass = passed rows / all rows.
Stage 1 (k 0-1 x W1-W5, 10 rows): screen_pass = share10 - share_twin >= 0.20 and pass10 >= 0.8 * pass_twin.
Top-up (k 2-5, +20 rows) for screen passers; confirmed = share30 - share_twin >= 0.20 and pass30 >= 0.8 * pass_twin
and binomtest(k_off30, n_valid30, p0 = (k_twin + 0.5) / (n_twin_valid + 1), 'greater').p < 0.05.
E(alpha) = #confirmed / #directions; E = mean over alphas; MOVABLE_obs = E > 0; landing = modal catalogue survivor
among CORRECT off-default programs of the confirmed cells (30 rows each).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from cfg5 import ESC_EXCESS, ESC_PASS_FRAC, EXCLUDE, P_BINOM
from metrics import binom_greater_p


def share(rows: list[dict[str, Any]], cat: set[str], default: str) -> dict[str, Any]:
    valid = [r for r in rows if r["label"] not in EXCLUDE]
    off = [r for r in valid if r["label"] in cat and r["label"] != default]
    n = len(valid)
    return {"n": len(rows), "n_valid": n, "k_off": len(off), "share": len(off) / n if n else None,
            "pass": sum(1 for r in rows if r.get("passed")) / len(rows) if rows else None,
            "labels": dict(Counter(r["label"] for r in rows)),
            "landing_correct": dict(Counter(r["label"] for r in off if r.get("passed")))}


def twin_stats(twin_rows: list[dict[str, Any]], cat: set[str], default: str) -> dict[str, Any]:
    return share(twin_rows, cat, default)


def cell_decision(cell_rows: list[dict[str, Any]], tw: dict[str, Any], cat: set[str], default: str) -> dict[str, Any]:
    first = [r for r in cell_rows if int(r["slot"]) in (0, 1)]
    pooled = [r for r in cell_rows if int(r["slot"]) in range(6)]
    f, pl = share(first, cat, default), share(pooled, cat, default)
    p0 = (tw["k_off"] + 0.5) / (tw["n_valid"] + 1)
    ok_tw = tw["share"] is not None and tw["pass"] is not None
    screen_pass = bool(ok_tw and f["n_valid"] > 0 and f["share"] - tw["share"] >= ESC_EXCESS - 1e-12 and
                       f["pass"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12)
    topped = pl["n"] > f["n"]
    conf, pbin = False, None
    if screen_pass and topped and pl["n_valid"] > 0:
        pbin = binom_greater_p(pl["k_off"], pl["n_valid"], p0)
        conf = bool(pl["share"] - tw["share"] >= ESC_EXCESS - 1e-12 and pbin < P_BINOM and
                    pl["pass"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12)
    return {"n10": f["n"], "share10": f["share"], "pass10": f["pass"], "screen_pass": screen_pass,
            "topped_up": topped, "n30": pl["n"], "share30": pl["share"] if topped else None,
            "pass30": pl["pass"] if topped else None, "p_binom": pbin, "p0": p0, "confirmed": conf,
            "excess10": (f["share"] - tw["share"]) if (f["share"] is not None and ok_tw) else None,
            "landing_counts": pl["landing_correct"] if conf else {}, "labels10": f["labels"]}


def escape_table(rows: list[dict[str, Any]], twin_rows: list[dict[str, Any]], seeds: list[int],
                 alphas: tuple[float, ...], cat: set[str], default: str) -> dict[str, Any]:
    """rows: ESC rows of one task (arm ESC_d<s>_a<a>, fields direction_seed, alpha, slot, label, passed)."""
    tw = twin_stats(twin_rows, cat, default)
    cells = []
    for s in seeds:
        for a in alphas:
            cr = [r for r in rows if int(r["direction_seed"]) == s and abs(float(r["alpha"]) - a) < 1e-9]
            d = cell_decision(cr, tw, cat, default)
            d.update({"seed": s, "alpha": a})
            cells.append(d)
    E_by = {}
    for a in alphas:
        cs = [c for c in cells if c["alpha"] == a]
        E_by[a] = sum(c["confirmed"] for c in cs) / len(cs) if cs else None
    vals = [v for v in E_by.values() if v is not None]
    E = sum(vals) / len(vals) if vals else None
    land = Counter()
    for c in cells:
        if c["confirmed"]:
            land.update(c["landing_counts"])
    landing = sorted(land.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if land else None
    return {"twin": tw, "cells": cells, "E_by_alpha": {str(a): v for a, v in E_by.items()}, "E": E,
            "movable_obs": bool(E is not None and E > 0), "landing": landing, "landing_counts": dict(land),
            "passers": [(c["seed"], c["alpha"]) for c in cells if c["screen_pass"]]}
