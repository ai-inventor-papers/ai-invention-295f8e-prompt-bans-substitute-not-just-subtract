#!/usr/bin/env python3
"""Expansion tracer, parent side (Stage 2b/2c): runs expansion_child.py on the 40 probe grids, derives the expansion
sequence E per grid, the 6-flag data-structure signature, and behavioural distances between programs.

E per grid, by source priority: (1) container pops (heap / deque / queue / list.pop; first extraction of each cell)
when >= 3 distinct cells were popped, using the main phase (overlapping container activity; a sequential pre-check
phase such as a reachability DFS is split off) unless the program recursed after its last pop (IDA*, recursive IDDFS
with a pre-check), in which case recursion is the search; (2) cell arguments of self-recursive candidate functions (recursive DFS, IDDFS,
IDA*) when >= 3 distinct cells; (3) grid-read bursts (runs of >= 2 consecutive reads that are 4-neighbours of one
cell). The source used is recorded per grid.
DS flags (per program, aggregated over the probe grids):
  fifo               FIFO pops >= 30% of all pops
  lifo_or_recursion  LIFO pops >= 30% of all pops, or self-recursion depth >= 3 on >= half of the grids
  heap               heap pops >= 30% of all pops
  two_frontiers      >= 2 containers with >= 3 pops each in the main phase on >= half of the grids, or the goal cell
                     among the first 4 expansions on >= half of the grids with BFS distance >= 4
  restarts           the start cell expanded >= 2 times on >= half of the grids with BFS distance >= 3
  heuristic_key      abs() calls >= 0.5 x expansions on >= half of the grids, or median partial Spearman of extraction
                     rank with the Manhattan distance to the goal given the BFS distance from the start >= 0.4
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import kendalltau, rankdata

from common import DATA, ROOT

CHILD = ROOT / "src" / "expansion_child.py"
FLAGS = ["fifo", "lifo_or_recursion", "heap", "two_frontiers", "restarts", "heuristic_key"]
SYS_PY = os.environ.get("SANDBOX_PYTHON", "/usr/local/bin/python3.12")


def bfs_dist(rows: list[str], src: tuple[int, int]) -> dict[tuple[int, int], int]:
    H, W = len(rows), len(rows[0])
    d = {src: 0}
    q = deque([src])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and rows[nr][nc] == "." and (nr, nc) not in d:
                d[(nr, nc)] = d[(r, c)] + 1
                q.append((nr, nc))
    return d


def run_child(code: str, grids: list[dict[str, Any]], timeout_s: float = 3.0) -> dict[str, Any]:
    job = {"code": code, "grids": grids, "timeout_s": timeout_s}
    with tempfile.TemporaryDirectory(dir=str(DATA)) as d:
        jp, op = Path(d) / "job.json", Path(d) / "out.json"
        jp.write_text(json.dumps(job))
        try:
            subprocess.run([SYS_PY, "-I", "-S", str(CHILD), str(jp), str(op)], cwd=d, stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, timeout=timeout_s * len(grids) + 30, start_new_session=True)
            return json.loads(op.read_text()) if op.exists() else {"grids": [], "load_error": "no_output"}
        except subprocess.TimeoutExpired:
            return {"grids": [], "load_error": "hard_timeout"}
        except (OSError, json.JSONDecodeError) as e:
            return {"grids": [], "load_error": f"{type(e).__name__}"}


def _first_order(seq: list[tuple[int, int]]) -> list[tuple[int, int]]:
    seen, out = set(), []
    for c in seq:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _partial_spearman(rank: np.ndarray, h: np.ndarray, ds: np.ndarray) -> float | None:
    if len(rank) < 8:
        return None
    r1, r2, r3 = rankdata(rank), rankdata(h), rankdata(ds)
    A = np.c_[np.ones(len(r3)), r3]
    e1 = r1 - A @ np.linalg.lstsq(A, r1, rcond=None)[0]
    e2 = r2 - A @ np.linalg.lstsq(A, r2, rcond=None)[0]
    den = np.sqrt((e1 ** 2).sum() * (e2 ** 2).sum())
    return float((e1 * e2).sum() / den) if den > 1e-12 else None


def _main_phase(pops: list[tuple[str, int, tuple[int, int]]]) -> list[tuple[str, int, tuple[int, int]]]:
    """Containers whose pop intervals overlap form one phase (a bidirectional search interleaves two); sequential
    phases (e.g. a reachability pre-check before the search) are split and the phase with the most pops is kept."""
    if not pops:
        return pops, -1
    span: dict[int, list[int]] = {}
    for i, (_, cid, _) in enumerate(pops):
        span.setdefault(cid, [i, i])[1] = i
    iv = sorted(span.values())
    phases, cur = [], [iv[0][0], iv[0][1]]
    for a, b in iv[1:]:
        if a <= cur[1]:
            cur[1] = max(cur[1], b)
        else:
            phases.append(cur)
            cur = [a, b]
    phases.append(cur)
    lo, hi = max(phases, key=lambda ab: ab[1] - ab[0])
    return pops[lo:hi + 1], hi


def analyse(raw: dict[str, Any], grids: list[dict[str, Any]]) -> dict[str, Any]:
    """Raw child output -> per-grid E (+ source) and the program's DS signature."""
    per = []
    kinds = Counter()
    for gi, (g, pg) in enumerate(zip(raw.get("grids", []), grids)):
        rows, start, goal = pg["rows"], tuple(pg["start"]), tuple(pg["goal"])
        pops = [(p[0], p[1], (p[2], p[3])) for p in g.get("pops", [])]
        stamps = [p[4] if len(p) > 4 else 0 for p in g.get("pops", [])]
        calls = [(c[1], c[2]) for c in g.get("calls", [])]
        bursts = [tuple(b) for b in g.get("bursts", [])]
        for k, _, _ in pops:
            kinds[k] += 1
        main_pops, last_i = _main_phase(pops)
        pop_cells = [c for _, _, c in main_pops]
        n_reads = max(int(g.get("n_reads", 0)), 1)
        frac_after = (n_reads - (stamps[last_i] if main_pops else 0)) / n_reads
        b_after = [tuple(b) for b in g.get("bursts_after_pops", [])]
        pre_phase = (bool(main_pops) and g.get("max_rec_depth", 0) >= 3 and
                     (len(set(calls)) >= 3 or len(set(b_after)) >= 3))
        if pre_phase:
            bursts = b_after
        if len(set(pop_cells)) >= 3 and not pre_phase:
            full, src = pop_cells, "pops"
        elif len(set(calls)) >= 3:
            full, src = calls, "recursive_calls"
        elif len(set(bursts)) >= 3:
            full, src = bursts, "bursts"
        else:
            full, src = (pop_cells or calls or bursts), "none"
        pops = main_pops
        E = _first_order(full)
        conts = Counter(cid for _, cid, _ in pops)
        big = [c for c, n in conts.items() if n >= 3]
        dist_s = bfs_dist(rows, start)
        dsg = dist_s.get(goal, -1)
        h = np.array([abs(r - goal[0]) + abs(c - goal[1]) for r, c in E], dtype=float)
        ds = np.array([dist_s.get(c, 10 ** 4) for c in E], dtype=float)
        ps = _partial_spearman(np.arange(len(E)), h, ds) if len(E) else None
        nondec = None
        if len(E) >= 3:
            dd = [dist_s.get(c, 10 ** 4) for c in E]
            nondec = float(np.mean([b >= a for a, b in zip(dd, dd[1:])]))
        adj = None
        if len(E) >= 3:
            adj = float(np.mean([abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(E, E[1:])]))
        per.append({"E": [list(c) for c in E], "source": src, "n_full": len(full),
                    "start_count": sum(1 for c in full if c == start), "goal_rank": (E.index(goal) if goal in E else None),
                    "two_containers": len(big) >= 2, "abs_rate": g.get("abs_calls", 0) / max(len(E), 1),
                    "partial_spearman_h": ps, "bfs_nondecreasing": nondec, "adjacency": adj,
                    "max_rec_depth": g.get("max_rec_depth", 0), "ok": g.get("ok"), "err": g.get("err"),
                    "bfs_dist_goal": dsg, "copied": g.get("copied")})
    n_pops = sum(kinds.values())
    share = {k: (kinds[k] / n_pops if n_pops else 0.0) for k in ("F", "L", "H", "M")}
    ng = max(len(per), 1)
    far3 = [p for p in per if p["bfs_dist_goal"] >= 3]
    far4 = [p for p in per if p["bfs_dist_goal"] >= 4]
    pss = [p["partial_spearman_h"] for p in per if p["partial_spearman_h"] is not None]
    flags = {
        "fifo": share["F"] >= 0.3,
        "lifo_or_recursion": share["L"] >= 0.3 or sum(p["max_rec_depth"] >= 3 for p in per) >= 0.5 * ng,
        "heap": share["H"] >= 0.3,
        "two_frontiers": (sum(p["two_containers"] for p in per) >= 0.5 * ng) or
                         (len(far4) > 0 and sum((p["goal_rank"] is not None and p["goal_rank"] < 4) for p in far4)
                          >= 0.5 * len(far4)),
        "restarts": len(far3) > 0 and sum(p["start_count"] >= 2 for p in far3) >= 0.5 * len(far3),
        "heuristic_key": False,
    }
    flags["heuristic_key"] = bool((sum(p["abs_rate"] >= 0.5 for p in per) >= 0.5 * ng) or
                                  (not flags["two_frontiers"] and len(pss) > 0 and float(np.median(pss)) >= 0.4))
    return {"per_grid": per, "flags": flags, "pop_share": share, "n_pops": n_pops,
            "median_partial_spearman_h": float(np.median(pss)) if pss else None,
            "sources": dict(Counter(p["source"] for p in per)), "n_ok": sum(bool(p["ok"]) for p in per),
            "load_error": raw.get("load_error")}


_TRACE_CACHE: dict[tuple[str, float], dict[str, Any]] = {}


def trace_program(code: str, grids: list[dict[str, Any]], timeout_s: float = 3.0) -> dict[str, Any]:
    import hashlib

    key = (hashlib.sha256(code.encode()).hexdigest(), timeout_s)
    if key not in _TRACE_CACHE:
        f = DATA / "trace_cache" / f"{key[0]}_{timeout_s}.json"
        if f.exists():
            try:
                _TRACE_CACHE[key] = json.loads(f.read_text())
                return _TRACE_CACHE[key]
            except json.JSONDecodeError:
                pass
        _TRACE_CACHE[key] = analyse(run_child(code, grids, timeout_s), grids)
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(_TRACE_CACHE[key]))
    return _TRACE_CACHE[key]


def trace_many(codes: list[str], grids: list[dict[str, Any]], workers: int = 12,
               timeout_s: float = 3.0) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda c: trace_program(c, grids, timeout_s), codes))


def pair_order_distance(ta: dict[str, Any], tb: dict[str, Any]) -> float:
    """d_order = 1 - mean over grids of J*(1+tau_b)/2 (grids where both programs expanded something)."""
    ss = []
    for pa, pb in zip(ta["per_grid"], tb["per_grid"]):
        Ea, Eb = [tuple(c) for c in pa["E"]], [tuple(c) for c in pb["E"]]
        if not Ea or not Eb:
            continue
        sa, sb = set(Ea), set(Eb)
        J = len(sa & sb) / len(sa | sb)
        common = [c for c in Ea if c in sb]
        tau = 0.0
        if len(common) >= 3:
            ra = {c: i for i, c in enumerate(Ea)}
            rb = {c: i for i, c in enumerate(Eb)}
            t = kendalltau([ra[c] for c in common], [rb[c] for c in common]).statistic
            tau = 0.0 if t is None or not np.isfinite(t) else float(t)
        ss.append(J * (1 + tau) / 2)
    return 1.0 - float(np.mean(ss)) if ss else 1.0


def ds_distance(ta: dict[str, Any], tb: dict[str, Any]) -> float:
    return sum(ta["flags"][f] != tb["flags"][f] for f in FLAGS) / len(FLAGS)


def beh_distance(ta: dict[str, Any], tb: dict[str, Any], lam: float = 0.5) -> float:
    return pair_order_distance(ta, tb) + lam * ds_distance(ta, tb)


def expansion_signature(t: dict[str, Any]) -> str:
    """Byte-level identity key of the expansion sequences (G-scrub)."""
    return json.dumps([p["E"] for p in t["per_grid"]], separators=(",", ":"))
