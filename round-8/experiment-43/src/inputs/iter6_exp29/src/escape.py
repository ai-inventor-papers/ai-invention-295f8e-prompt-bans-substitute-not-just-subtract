#!/usr/bin/env python3
"""exp22's two-stage escape rule, re-implemented from the text in predictions/c2_commit.json (committed here before
any decisive sample; gate C3 checks it reproduces exp22 results/escape.json exactly from exp22's own labels).

Rule text (c2_commit.json 'escape_confirmation'):
  Screen pass at N = 10: excess >= 0.20 over the twin (N = 50, k 0-9) and pass >= 0.8 x twin.
  CONFIRMED if the pooled 30 (k 0-5) keeps excess >= 0.20 with one-sided exact binomial p < 0.05 against
  p0 = (k_twin + 0.5) / (n_twin + 1), and pass >= 0.8 x twin. E_t(alpha) = confirmed / run.
Shares (exp22 analysis/common.py docstring): off-default share = #(catalogue label != default) / #valid, with
'invalid' and 'disputed' excluded from the denominator and 'other' counted as NOT off-default. Pass = passed the
hidden tests over all attempts. Screen rows = k in {0, 1}; pooled rows = k in 0..5; a cell is 'confirmed' only if it
passed the screen and has rows beyond the screen (topped up).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from scipy import stats

EXCLUDE = ("invalid", "disputed")
TOL = 1e-12


def share(rows: Iterable[dict[str, Any]], cat: set[str], default: str) -> dict[str, Any]:
    rows = list(rows)
    valid = [r for r in rows if r["label"] not in EXCLUDE]
    off = sum(1 for r in valid if r["label"] in cat and r["label"] != default)
    n = len(valid)
    npass = sum(1 for r in rows if r["passed"])
    return {"n": len(rows), "n_valid": n, "k_off": off, "share": off / n if n else float("nan"),
            "pass": npass / len(rows) if rows else float("nan"), "k_pass": npass,
            "n_other": sum(1 for r in rows if r["label"] == "other"),
            "n_invalid": sum(1 for r in rows if r["label"] == "invalid"),
            "n_disputed": sum(1 for r in rows if r["label"] == "disputed")}


def binom_greater(k: int, n: int, p0: float) -> float:
    return float(stats.binomtest(k, n, p0, alternative="greater").pvalue) if n > 0 else 1.0


def twin_rows(rows: list[dict[str, Any]], kmax: int = 10) -> list[dict[str, Any]]:
    return [r for r in rows if r["arm"] == "TWIN" and int(r["sample_id"]) < kmax]


def cell_eval(cell_rows: list[dict[str, Any]], tw: dict[str, Any], cat: set[str], default: str) -> dict[str, Any]:
    p0 = (tw["k_off"] + 0.5) / (tw["n_valid"] + 1)
    first = [r for r in cell_rows if int(r["sample_id"]) in (0, 1)]
    pooled = [r for r in cell_rows if 0 <= int(r["sample_id"]) <= 5]
    f, pl = share(first, cat, default), share(pooled, cat, default)
    screen = bool(f["n_valid"] > 0 and f["share"] - tw["share"] >= ESC() - TOL
                  and f["pass"] >= PASSF() * tw["pass"] - TOL)
    topped = pl["n"] > f["n"]
    conf, pbin = False, None
    if screen and topped:
        pbin = binom_greater(pl["k_off"], pl["n_valid"], p0)
        conf = bool(pl["share"] - tw["share"] >= ESC() - TOL and pbin < 0.05
                    and pl["pass"] >= PASSF() * tw["pass"] - TOL)
    return {"first10": f, "pooled": pl, "screen_pass": screen, "topped_up": topped, "binom_p": pbin,
            "confirmed": conf, "excess_first10": f["share"] - tw["share"] if f["n_valid"] else None,
            "excess_pooled": pl["share"] - tw["share"] if pl["n_valid"] else None, "p0": p0}


def ESC() -> float:
    return 0.20


def PASSF() -> float:
    return 0.8


def escape_table(rows: list[dict[str, Any]], seeds: list[int], cat: set[str], default: str,
                 alphas: tuple[float, ...] = (1.0, 2.0), family: str = "POP") -> dict[str, Any]:
    """rows: joined label rows of ONE engine and task (TWIN + POP arms). Returns twin stats, per-direction cells and
    E_t per alpha (confirmed / n_run, n_run = directions with any screen row at that alpha)."""
    tw = share(twin_rows(rows), cat, default)
    pop = defaultdict(list)
    for r in rows:
        if r.get("family") == family and r.get("direction_seed") is not None:
            pop[(int(r["direction_seed"]), float(r["alpha"]))].append(r)
    cells: dict[str, dict[str, Any]] = {}
    E: dict[str, dict[str, Any]] = {}
    for a in alphas:
        n_run = n_screen = n_conf = 0
        for s in seeds:
            rr = pop.get((s, float(a)), [])
            if not any(int(r["sample_id"]) in (0, 1) for r in rr):
                continue
            n_run += 1
            c = cell_eval(rr, tw, cat, default)
            cells[f"{s}|{a}"] = c
            n_screen += c["screen_pass"]
            n_conf += c["confirmed"]
        E[str(a)] = {"n_run": n_run, "n_screen_pass": n_screen, "n_confirmed": n_conf,
                     "E_t": n_conf / n_run if n_run else float("nan"),
                     "E_screen": n_screen / n_run if n_run else float("nan")}
    return {"twin": tw, "cells": cells, "E_t": E}


def needs_confirmation(rows: list[dict[str, Any]], seeds: list[int], cat: set[str], default: str,
                       alpha: float) -> list[int]:
    """Directions whose screen passes at `alpha` and that are not yet topped up."""
    t = escape_table(rows, seeds, cat, default, alphas=(alpha,))
    out = []
    for s in seeds:
        c = t["cells"].get(f"{s}|{alpha}")
        if c and c["screen_pass"] and not c["topped_up"]:
            out.append(s)
    return out
