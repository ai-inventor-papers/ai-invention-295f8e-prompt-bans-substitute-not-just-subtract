#!/usr/bin/env python3
"""5c runtime rules: raw tracer features (labeller/tracer.py) -> runtime label, 'unknown' or 'inconsistent'."""

from __future__ import annotations

import math
from typing import Any


def _pops(h: dict[str, Any]) -> int:
    return int(h.get("pop", 0))


def _fifo_list(p: dict[str, Any], min_pops: int = 5) -> list[dict[str, Any]]:
    out = [d for d in p.get("deques", []) if d.get("popleft", 0) >= min_pops and d.get("popleft", 0) >= d.get("pop", 0)]
    out += [q for q in p.get("queues", []) if q.get("kind") == "fifo" and q.get("get", 0) >= min_pops]
    return out


def _fifo_containers(p: dict[str, Any], min_pops: int = 5) -> int:
    return len(_fifo_list(p, min_pops))


def _interleaved(recs: list[dict[str, Any]]) -> bool:
    """True if at least two containers were popped in interleaved fashion (not one after the other)."""
    spans = [(r.get("first"), r.get("last")) for r in recs if r.get("first") is not None]
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            (a1, a2), (b1, b2) = spans[i], spans[j]
            if a1 < b2 and b1 < a2:
                return True
    return False


def _fifo_evidence(p: dict[str, Any]) -> bool:
    lp = p.get("list_pop", {})
    if lp.get("fifo", 0) >= 5:
        return True
    if lp.get("lifo", 0) >= 5 and p.get("list_insert", 0) >= 5:  # insert(0, x) + pop() is a FIFO queue
        return True
    return _fifo_containers(p) >= 1


def _lifo_evidence(p: dict[str, Any]) -> bool:
    lp = p.get("list_pop", {})
    if lp.get("lifo", 0) >= 5 and lp.get("lifo", 0) > lp.get("fifo", 0) and p.get("list_insert", 0) < 5:
        return True
    if any(d.get("pop", 0) >= 5 and d.get("pop", 0) > d.get("popleft", 0) for d in p.get("deques", [])):
        return True
    if any(q.get("kind") == "lifo" and q.get("get", 0) >= 5 for q in p.get("queues", [])):
        return True
    return bool(p.get("recursion")) and p.get("max_depth", 0) >= 10


def _work(p: dict[str, Any]) -> int:
    lp = p.get("list_pop", {})
    return (int(p.get("calls", 0)) + sum(int(v) for v in lp.values())
            + sum(d.get("pop", 0) + d.get("popleft", 0) for d in p.get("deques", []))
            + sum(q.get("get", 0) for q in p.get("queues", [])) + sum(_pops(h) for h in p.get("heaps", [])))


def label_t1(tr: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    probes = tr.get("probes", [])
    done = [p for p in probes if not p.get("timeout") and not p.get("exc")]
    info: dict[str, Any] = {"n_probes_done": len(done), "tracer_error": tr.get("error")}
    if not done:
        return "unknown", f"no probe completed ({tr.get('error')})", info
    by = {}
    for p in probes:
        by.setdefault(p["name"], []).append(p)
    diag = next((p for p in by.get("P_diag", []) if not p.get("timeout") and not p.get("exc")), None)
    maze = next((p for p in by.get("P_maze", []) if not p.get("timeout") and not p.get("exc")), None)
    opens = [p for p in by.get("P_open", []) if not p.get("timeout") and not p.get("exc")]
    valid_done = [p for p in done if p.get("valid")]
    nonopt = [p for p in valid_done if not p.get("optimal")]
    all_opt = bool(valid_done) and not nonopt and len(valid_done) == len(done)
    diag_timeout = any(p.get("timeout") for p in by.get("P_diag", [])) or (tr.get("error") == "probe_timeout")
    ref = diag or maze or done[-1]
    info.update({"all_optimal": all_opt, "n_nonoptimal": len(nonopt), "diag_timeout": diag_timeout,
                 "rho_s": ref.get("rho_s"), "goal_side_share": ref.get("goal_side_share"),
                 "reaccess": ref.get("reaccess_ratio")})
    heaps = [h for h in ref.get("heaps", []) if _pops(h) >= 5]
    if not heaps:
        heaps = [h for p in done for h in p.get("heaps", []) if _pops(h) >= 5]
    # 1) bidirectional
    big_heaps = [h for h in ref.get("heaps", []) if _pops(h) >= 5]
    two_heaps = len(big_heaps) >= 2 and _interleaved(big_heaps)
    pr0 = [x for x in (max(ref.get("heaps", []), key=_pops).get("pops", [])[:2] if ref.get("heaps") else [])]
    one_heap_two_roots = len(pr0) == 2 and pr0[0] == 0 and pr0[1] == 0 and len(big_heaps) == 1
    two_heaps = two_heaps or one_heap_two_roots
    fl = _fifo_list(ref)
    two_fifo = len(fl) >= 2 and _interleaved(fl)
    goal_side = (diag is not None and (diag.get("goal_side_share") or 0) >= 0.25 and all_opt)
    if two_heaps or two_fifo or goal_side:
        why = "two heaps" if two_heaps else ("two FIFO frontiers" if two_fifo else "early goal-side accesses")
        if heaps:
            return "other", f"bidirectional with heap ({why})", info
        return _consistency("bibfs", f"bidirectional ({why})", nonopt, info)
    # 2) heap: Dijkstra vs A*/GBFS by the priorities of the first pops after the start
    if heaps:
        src = diag if diag is not None and any(_pops(h) >= 5 for h in diag.get("heaps", [])) else None
        if src is None:
            return "unknown", "heap but no P_diag heap trace", info
        h = max(src["heaps"], key=_pops)
        pr = [x for x in h.get("pops", [])[1:8] if x is not None]
        info["heap_q"] = min(pr) if pr else None
        manh = abs(src["start"][0] - src["goal"][0]) + abs(src["start"][1] - src["goal"][1])
        if not pr:
            return "unknown", "heap priorities not numeric", info
        q = min(pr)
        if q <= 0.25 * manh:
            return _consistency("dijkstra", f"heap, early pops at distance-from-start priority {q:g}", nonopt, info)
        if q >= 0.5 * manh:
            return "astar_gbfs", f"heap, early pops at heuristic-scale priority {q:g} (Manhattan {manh})", info
        return "unknown", f"heap with ambiguous priority scale {q:g}", info
    # 3) IDDFS: heavy re-exploration with optimal (shortest) paths
    re_acc = [p.get("reaccess_ratio") for p in probes if p.get("reaccess_ratio") is not None]
    work_open = [_work(p) for p in opens]
    heavy = (re_acc and max(re_acc) >= 8) or (work_open and min(work_open) >= 8 * 113)
    if heavy and not nonopt and (any(p.get("recursion") for p in probes) or any(_lifo_evidence(p) for p in probes)
                                 or diag_timeout or all(p.get("optimal") for p in opens)):
        return "iddfs", "repeated depth-limited exploration, no non-shortest valid path", info
    # 4) DFS: non-shortest valid paths or LIFO/recursive exploration
    if nonopt:
        return "dfs", f"non-shortest paths on {len(nonopt)} probe(s)", info
    if _lifo_evidence(ref) and not _fifo_evidence(ref):
        return "dfs", "LIFO stack / deep recursion", info
    # 5) BFS: FIFO queue or distance-ordered first accesses
    rho = ref.get("rho_s")
    if _fifo_evidence(ref) or (rho is not None and rho >= 0.8):
        return "bfs", "FIFO frontier / distance-ordered exploration", info
    return "unknown", "no runtime rule fired", info


def _consistency(lbl: str, why: str, nonopt: list[dict[str, Any]], info: dict[str, Any]):
    if nonopt and lbl in ("bfs", "bibfs", "iddfs", "dijkstra"):
        return "inconsistent", f"{lbl} signature but non-shortest path on {len(nonopt)} probe(s)", info
    return lbl, why, info


def _nondecreasing_share(xs: list[float]) -> float:
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 1.0
    return sum(1 for a, b in zip(xs, xs[1:]) if b >= a - 1e-9) / (len(xs) - 1)


def label_t2(tr: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    probes = tr.get("probes", [])
    done = [p for p in probes if not p.get("timeout") and not p.get("exc")]
    info: dict[str, Any] = {"n_probes_done": len(done), "tracer_error": tr.get("error")}
    if not done:
        return "unknown", f"no probe completed ({tr.get('error')})", info
    g24 = next((p for p in done if p["name"] == "G24"), None)
    g48 = next((p for p in done if p["name"] == "G48"), None)
    ref = g24 or g48
    expo = None
    if g24 and g48 and g24.get("lines", 0) > 0 and g48.get("lines", 0) > 0:
        expo = math.log2(g48["lines"] / g24["lines"])
    info.update({"exponent": expo, "lines24": g24.get("lines") if g24 else None,
                 "edges_full": ref.get("edges_full"), "correct": [p.get("correct") for p in done]})
    best = max(done, key=lambda p: sum(_pops(h) for h in p.get("heaps", [])))
    two = [h for h in best.get("heaps", []) if _pops(h) >= 1 and h.get("push", 0) >= 2]
    heaps = [h for h in best.get("heaps", []) if _pops(h) >= 3]
    if len(two) >= 2 and _interleaved(two):
        return "bidijkstra", "two heaps popped in interleaved order", info
    if len(heaps) == 1 and heaps[0].get("pops", [None, None])[:2] == [0.0, 0.0]:
        return "bidijkstra", "one heap seeded with both s and t at priority 0 (positive probe weights)", info
    if len(two) >= 2:
        heaps = [max(two, key=_pops)]  # sequential runs: judge by the busiest heap
    if len(heaps) == 1:
        share = _nondecreasing_share(heaps[0].get("pops", []))
        info["nondecreasing_share"] = share
        if share >= 0.9:
            return "dijkstra", f"one heap, {share:.0%} non-decreasing pops", info
        return "unknown", f"one heap with {share:.0%} non-decreasing pops", info
    if expo is not None and expo >= 2.6:
        return "floyd", f"line-count scaling exponent {expo:.2f}", info
    if g24 and g24.get("lines", 0) >= 24 ** 3 and (g24.get("edges_full", 0) <= 1):
        return "floyd", "n^3 line events on the n=24 probe", info
    fifo_d = [d for d in ref.get("deques", []) if d.get("popleft", 0) >= 1]
    fifo_pops = (sum(d.get("popleft", 0) for d in fifo_d) + ref.get("list_pop", {}).get("fifo", 0)
                 + sum(q.get("get", 0) for q in ref.get("queues", []) if q.get("kind") == "fifo"))
    n_lists = max(p.get("n_pop_lists", 0) for p in done)
    n_deq = max(p.get("n_deques_popped", 0) for p in done)
    info["n_pop_lists"] = n_lists
    if n_lists >= 3 or n_deq >= 3:
        return "dial", f"pops from {max(n_lists, n_deq)} distinct bucket containers", info
    if fifo_pops >= 5:
        return "bf_spfa", "FIFO label-correcting queue", info
    if ref.get("edges_full", 0) >= 2 or ref.get("edges_index", 0) >= 2 * max(1, ref.get("n_edges", 1)):
        return "bf_spfa", f"{ref.get('edges_full')} full passes over the edge list", info
    return "unknown", "no runtime rule fired", info


def label(task: str, tr: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    if tr.get("error") in ("forbidden_import", "syntax_error", "exec_failed", "exec_timeout", "crash",
                           "harness_timeout", "bad_output") and not tr.get("probes"):
        return "unknown", f"tracer: {tr.get('error')}", {"tracer_error": tr.get("error")}
    return label_t1(tr) if task == "t1" else label_t2(tr)
