#!/usr/bin/env python3
"""Post-hoc checks that feed no forecast: AST-shingle similarity of forced versus natural programs (FRLP proposal
coverage), FRLP sanity checks (T4), ESS distribution (F8), the commit-order audit (T8) and a re-hash of the chain."""

from __future__ import annotations

import ast
import collections
import itertools
import json
import math
from typing import Any

import numpy as np
from loguru import logger

from common import (COMMIT_LOG, DATA_DIR, LOG_DIR, RESULTS_DIR, read_json, read_jsonl, verify_chain, write_json)


def node_seq(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    out: list[str] = []

    def rec(n: ast.AST) -> None:
        out.append(type(n).__name__)
        for ch in ast.iter_child_nodes(n):
            rec(ch)

    rec(tree)
    return out


def shingles(code: str, k: int = 4) -> set[tuple[str, ...]]:
    s = node_seq(code)
    return {tuple(s[i:i + k]) for i in range(max(0, len(s) - k + 1))}


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def mean_pairs(A: list[set], B: list[set] | None = None, cap: int = 4000) -> float | None:
    rng = np.random.default_rng(0)
    pairs = list(itertools.combinations(range(len(A)), 2)) if B is None else \
        [(i, j) for i in range(len(A)) for j in range(len(B))]
    if not pairs:
        return None
    if len(pairs) > cap:
        pairs = [pairs[i] for i in rng.choice(len(pairs), cap, replace=False)]
    return float(np.mean([jacc(A[i], (A if B is None else B)[j]) for i, j in pairs]))


def shingle_check() -> dict[str, Any]:
    forced = read_jsonl(DATA_DIR / "labelled_forced_all.jsonl")
    s1 = read_jsonl(DATA_DIR / "labelled_session1.jsonl")
    s2 = read_jsonl(DATA_DIR / "labelled_session2.jsonl") if (DATA_DIR / "labelled_session2.jsonl").exists() else []
    nat = s1 + s2
    out = {}
    groups = [("t1", "baseline", "bfs"), ("t2", "baseline", "dijkstra"), ("t1", "single:bfs", "dfs"),
              ("t2", "single:dijkstra", "bf_spfa")] + [("t2", f"los:{s}", s) for s in ("dijkstra", "bf_spfa")] + \
             [("t1", c, lab) for c in sorted({r["condition"] for r in s2}) for lab in
              sorted({r["label"] for r in s2 if r["condition"] == c})]
    for task, cond, lab in groups:
        F = [shingles(r["code"]) for r in forced if r["task"] == task and r["algorithm"] == lab and r["label"] == lab
             and r.get("code")]
        N = [shingles(r["code"]) for r in nat if r["task"] == task and r["condition"] == cond and r["label"] == lab
             and r.get("code")]
        if len(F) < 2 or len(N) < 2:
            continue
        ff, nn, fn = mean_pairs(F), mean_pairs(N), mean_pairs(N, F)
        out[f"{task}|{cond}|{lab}"] = {"n_forced": len(F), "n_natural": len(N), "within_forced": ff,
                                       "within_natural": nn, "forced_vs_natural": fn,
                                       "ratio_cross_to_within_forced": fn / ff if ff else None}
    return out


def frlp_sanity() -> dict[str, Any]:
    cells = [r for r in read_jsonl(RESULTS_DIR / "frlp_cells.jsonl") if "variant" not in r]
    base = {(r["task"], r["algorithm"]): r for r in cells if r["condition"] == "base" and r["half"] == "all"}
    out: dict[str, Any] = {}
    for task, top in (("t1", "bfs"), ("t2", "dijkstra")):
        Ls = {a: r["L"] for (t, a), r in base.items() if t == task}
        out[f"{task}_largest_is_default"] = max(Ls, key=Ls.get) == top
        out[f"{task}_sum_exp_L_base"] = float(sum(math.exp(v) for v in Ls.values()))
        out[f"{task}_sum_in_0.3_3"] = 0.3 <= out[f"{task}_sum_exp_L_base"] <= 3
    idx = {(r["task"], r["condition"], r["template"], r.get("twin"), r["algorithm"], r["half"]): r for r in cells}
    b = idx.get(("t1", "single:bfs", "W1", "ban", "bfs", "h1"))
    n = idx.get(("t1", "single:bfs", "W1", "neutral", "bfs", "h1"))
    out["ban_bfs_W1_drop"] = (b["L"] - n["L"]) if b and n else None
    out["ban_bfs_W1_drop_gt_1nat"] = bool(b and n and (n["L"] - b["L"]) > 1)
    pl = RESULTS_DIR / "placebo.json"
    out["placebo"] = read_json(pl) if pl.exists() else None
    ess = np.array([r["ess"] for r in cells])
    by = collections.defaultdict(list)
    for r in cells:
        by[r["condition"].split(":")[0] + "|" + str(r.get("twin"))].append(r["ess"])
    out["ess"] = {"n_cells": int(len(ess)), "share_lt_5": float((ess < 5).mean()), "median": float(np.median(ess)),
                  "by_kind": {k: {"n": len(v), "median": float(np.median(v)), "share_lt_5": float(np.mean(np.array(v) < 5))}
                              for k, v in by.items()}}
    return out


def commit_audit() -> dict[str, Any]:
    ok, probs = verify_chain()
    lines = [json.loads(x) for x in COMMIT_LOG.read_text().splitlines()]
    last_commit = max(e["utc_time"] for e in lines if "forecasts_" in e["payload_path"] or "landing.py" in e["payload_path"])
    raw2 = read_jsonl(DATA_DIR / "raw_session2.jsonl")
    first_s2 = min((r["gen_start_utc"] for r in raw2), default=None)
    return {"chain_ok": ok, "problems": probs, "n_lines": len(lines), "last_forecast_commit_utc": last_commit,
            "first_session2_request_utc": first_s2,
            "commit_precedes_sampling": bool(first_s2 and last_commit < first_s2)}


def run_extra() -> None:
    out = {"shingles": shingle_check(), "frlp_sanity": frlp_sanity(), "commit_audit": commit_audit()}
    t = LOG_DIR / "timing.json"
    out["timing"] = read_json(t) if t.exists() else {}
    write_json(RESULTS_DIR / "checks.json", out)
    logger.info(f"checks: sanity {json.dumps({k: v for k, v in out['frlp_sanity'].items() if k not in ('ess', 'placebo')})}")
    logger.info(f"commit audit: {out['commit_audit']}")
