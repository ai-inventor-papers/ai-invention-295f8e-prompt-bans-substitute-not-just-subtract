#!/usr/bin/env python3
"""5c runtime rules (iteration-2 extension of exp1: 10 grid mechanisms; T2 rules unchanged): raw tracer features (labeller/tracer.py) -> runtime label, 'unknown' or 'inconsistent'."""

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


def _heap_scale(src: dict[str, Any], h: dict[str, Any]) -> float | None:
    pr = [x for x in h.get("pops", [])[1:8] if x is not None]
    return min(pr) if pr else None


def _manh(p: dict[str, Any]) -> int:
    return abs(p["start"][0] - p["goal"][0]) + abs(p["start"][1] - p["goal"][1])


def _busiest(p: dict[str, Any]) -> tuple[int, dict[str, Any], dict[str, Any]] | None:
    hs = p.get("heaps", [])
    if not hs:
        return None
    i = max(range(len(hs)), key=lambda k: _pops(hs[k]))
    shares = (p.get("heap_shares") or [{}] * len(hs))
    return i, hs[i], shares[i] if i < len(shares) else {}


def _restarts(p: dict[str, Any]) -> int | None:
    """Entries into a self-recursive search from outside itself (one per IDDFS / IDA* iteration): calls whose arguments
    carry the start cell if any were seen, else all outside calls. None if no self-recursive function ran."""
    best = None
    for v in (p.get("code_calls") or {}).values():
        if v.get("self_calls", 0) <= 0:
            continue
        outside = v.get("calls", 0) - v.get("self_calls", 0)
        r = v.get("start_calls_outside", 0) or outside
        best = r if best is None else max(best, r)
    return best


def label_t1(tr: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Iteration-2 grid rules (10 mechanisms). Order: JPS (push-sparse straight jumps) -> bidirectional (bidirectional
    A* if both heaps are heuristic-scale) -> heap (greedy vs A* vs unit-weight Dijkstra by pop-priority identities
    h / d + h / d, exp1 scale rule as an ambiguous fallback sent to the judge) -> IDA* vs IDDFS (restarts at the start
    cell, Manhattan evaluations) -> DFS -> BFS."""
    probes = tr.get("probes", [])
    done = [p for p in probes if not p.get("timeout") and not p.get("exc")]
    info: dict[str, Any] = {"n_probes_done": len(done), "tracer_error": tr.get("error")}
    if not done:
        return "unknown", f"no probe completed ({tr.get('error')})", info
    by: dict[str, list[dict[str, Any]]] = {}
    for p in probes:
        by.setdefault(p["name"], []).append(p)

    def first_done(name: str) -> dict[str, Any] | None:
        return next((p for p in by.get(name, []) if not p.get("timeout") and not p.get("exc")), None)

    diag, maze, trap = first_done("P_diag"), first_done("P_maze"), first_done("P_trap")
    opens = [p for p in by.get("P_open", []) if not p.get("timeout") and not p.get("exc")]
    valid_done = [p for p in done if p.get("valid")]
    nonopt = [p for p in valid_done if not p.get("optimal")]
    all_opt = bool(valid_done) and not nonopt and len(valid_done) == len(done)
    diag_timeout = any(p.get("timeout") for p in by.get("P_diag", [])) or (tr.get("error") == "probe_timeout")
    ref = diag or maze or done[-1]
    info.update({"all_optimal": all_opt, "n_nonoptimal": len(nonopt), "nonopt_probes": [p["name"] for p in nonopt],
                 "diag_timeout": diag_timeout, "rho_s": ref.get("rho_s"), "goal_side_share": ref.get("goal_side_share"),
                 "reaccess": ref.get("reaccess_ratio"), "trap_optimal": trap.get("optimal") if trap else None})
    heaps = [h for h in ref.get("heaps", []) if _pops(h) >= 5]
    if not heaps:
        heaps = [h for p in done for h in p.get("heaps", []) if _pops(h) >= 5]

    # 0) jump point search: on P_open, a frontier that receives few pushes relative to the cells read, and straight
    #    runs of >= 3 reads in one direction with no push in between
    jps_open = [p for p in opens if (p.get("n_pushes") or 0) > 0 and (p.get("push_ratio") is not None)
                and p["push_ratio"] <= 0.3 and (p.get("max_straight_run") or 0) >= 3]
    info["jps_open_hits"] = len(jps_open)
    info["push_ratio_open"] = [round(p.get("push_ratio") or 0, 3) for p in opens]
    info["straight_run_open"] = [p.get("max_straight_run") for p in opens]
    if opens and len(jps_open) >= max(2, (len(opens) + 1) // 2):
        return "jps", f"push-sparse straight jumps on {len(jps_open)}/{len(opens)} P_open probes", info

    # 1) bidirectional (two interleaved heaps are looked for on every completed probe: a bidirectional A* with tied
    #    f values may expand only one side on the open P_diag grid)
    big_heaps = [h for h in ref.get("heaps", []) if _pops(h) >= 5]
    bprobe = None
    for p in [ref] + [q for q in done if q is not ref]:
        bh = [h for h in p.get("heaps", []) if _pops(h) >= 5]
        if len(bh) >= 2 and _interleaved(bh):
            bprobe = p
            break
    two_heaps = bprobe is not None
    pr0 = [x for x in (max(ref.get("heaps", []), key=_pops).get("pops", [])[:2] if ref.get("heaps") else [])]
    one_heap_two_roots = len(pr0) == 2 and pr0[0] == 0 and pr0[1] == 0 and len(big_heaps) == 1
    fl = _fifo_list(ref)
    two_fifo = len(fl) >= 2 and _interleaved(fl)
    goal_side = (diag is not None and (diag.get("goal_side_share") or 0) >= 0.25 and all_opt)
    if two_heaps:
        manh = _manh(bprobe)
        hs = bprobe.get("heaps", [])
        shares = bprobe.get("heap_shares") or []
        info["bidir_probe"] = bprobe["name"]
        idx = sorted([i for i in range(len(hs)) if _pops(hs[i]) >= 5], key=lambda i: -_pops(hs[i]))[:2]
        heur = []
        for i in idx:
            q = _heap_scale(bprobe, hs[i])
            sh = shares[i] if i < len(shares) else {}
            hscale = (q is not None and q >= 0.5 * manh) or max(sh.get("share_f") or 0, sh.get("share_frev") or 0,
                                                                  sh.get("share_h") or 0, sh.get("share_hrev") or 0) >= 0.8
            heur.append(bool(hscale))
        info["bidir_heap_heuristic"] = heur
        if len(heur) == 2 and all(heur):
            return "biastar", "two interleaved heaps, both with heuristic-scale priorities", info
        return "other", "bidirectional with distance-scale heap(s) (bidirectional Dijkstra on the grid)", info
    if one_heap_two_roots:
        return "other", "one heap seeded with both start and goal at priority 0 (bidirectional Dijkstra)", info
    if two_fifo or goal_side:
        why = "two FIFO frontiers" if two_fifo else "early goal-side accesses"
        if heaps:
            return "other", f"bidirectional with heap ({why})", info
        return _consistency("bibfs", f"bidirectional ({why})", nonopt, info)

    # 2) heap: priority identities on P_diag and P_trap (pops 2..30): h -> greedy, d + h -> A*, d -> Dijkstra
    if heaps:
        cands = [p for p in (diag, trap) if p is not None and any(_pops(h) >= 5 for h in p.get("heaps", []))]
        if not cands:
            return "unknown", "heap but no P_diag / P_trap heap trace", info
        sh_list = []
        for p in cands:
            b = _busiest(p)
            if b is not None:
                sh_list.append((p["name"], b[2] or {}))
        info["heap_shares"] = {n: s for n, s in sh_list}

        def best(key: str) -> float:
            vals = [s.get(key) for _, s in sh_list if s.get(key) is not None]
            return max(vals) if vals else 0.0

        sh_h, sh_f, sh_d = best("share_h"), best("share_f"), best("share_d")
        if sh_h >= 0.8 and sh_h >= sh_f:
            return "gbfs", f"heap pops have priority == h (Manhattan to goal), share {sh_h:.2f}", info
        if sh_f >= 0.8:
            return _consistency("astar", f"heap pops have priority == d + h, share {sh_f:.2f}", nonopt, info)
        if sh_d >= 0.8:
            return _consistency("dijkstra_unit", f"heap pops have priority == d (distance from start), share "
                                                 f"{sh_d:.2f}", nonopt, info)
        src = cands[0]
        h = max(src["heaps"], key=_pops)
        q = _heap_scale(src, h)
        manh = _manh(src)
        info["heap_q"] = q
        if q is None:
            return "unknown", "heap priorities not numeric", info
        if q <= 0.25 * manh:
            return _consistency("dijkstra_unit", f"heap, early pops at distance-from-start priority {q:g}", nonopt,
                                info)
        if q >= 0.5 * manh:
            info["force_judge"] = True
            if info.get("trap_optimal") is False:
                return "gbfs", f"heap, heuristic-scale priority {q:g}, non-shortest path on P_trap (ambiguous)", info
            return "astar", f"heap, heuristic-scale priority {q:g}, shortest paths (ambiguous)", info
        return "unknown", f"heap with ambiguous priority scale {q:g}", info

    # 3) IDA* vs IDDFS: restarts at the start cell (calls whose arguments carry the start, from outside the
    #    recursive search) and Manhattan evaluations (builtin abs calls)
    re_acc = [p.get("reaccess_ratio") for p in probes if p.get("reaccess_ratio") is not None]
    work_open = [_work(p) for p in opens]
    heavy = bool((re_acc and max(re_acc) >= 8) or (work_open and min(work_open) >= 8 * 113))
    abs_max = max((p.get("abs_calls") or 0) for p in done)
    r_open = [x for x in (_restarts(p) for p in opens) if x is not None]
    r_maze = _restarts(maze) if maze else None
    d_open = min((_manh(p) for p in opens), default=7)
    info.update({"abs_calls_max": abs_max, "restarts_open": r_open, "restarts_maze": r_maze, "heavy": heavy})
    manh_traced = abs_max >= 20
    if manh_traced and not nonopt:
        if r_open and max(r_open) <= 2 and (r_maze or 0) >= 2:
            return "idastar", f"Manhattan evaluated ({abs_max} abs calls); {max(r_open)} restart(s) on P_open, " \
                              f"{r_maze} on P_maze", info
        if not r_open and heavy and (maze is not None and (maze.get("reaccess_ratio") or 0) >= 2):
            return "idastar", f"Manhattan evaluated ({abs_max} abs calls); heavy bounded re-exploration", info
    if r_open and min(r_open) >= d_open / 2 and not nonopt:
        return "iddfs", f"{min(r_open)} restarts at the start cell on P_open (D = {d_open})", info
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
    if nonopt and lbl in ("bfs", "bibfs", "iddfs", "dijkstra_unit", "dijkstra"):
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
