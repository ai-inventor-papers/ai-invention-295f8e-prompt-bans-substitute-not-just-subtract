#!/usr/bin/env python3
"""Runtime-signature labeller: run a program on crafted inputs under instrumentation, derive features, apply rules.

T1 crafted inputs: G1 open 15x15 (start (7,1), goal (7,13)); G2 a U-shaped trap opening away from the goal;
G3 a 15x15 maze. T2: W1 sparse n=20/E=40, W2 n=30/E=60 (same generator, weights 40..100), W3 n=6 with a negative
edge (informational). Rules are applied in a fixed order, first match wins (see t1_rules / t2_rules).
"""

from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tasks.t1_grid import bfs_dist, maze  # noqa: E402

DRIVER = Path(__file__).resolve().parent / "_trace_driver.py"
CONST_FILE = Path(__file__).resolve().parent / "constants.json"


def _g1():
    return dict(grid=["." * 15 for _ in range(15)], start=[7, 1], goal=[7, 13])


def _g2():
    g = [list("." * 15) for _ in range(15)]
    for r in range(3, 12):
        g[r][9] = "#"          # wall between the cup and the goal
    for c in range(3, 10):
        g[3][c] = "#"
        g[11][c] = "#"          # cup opens to the left, away from the goal
    return dict(grid=["".join(r) for r in g], start=[7, 7], goal=[7, 13])


def _g3():
    return dict(grid=maze(15, 15, random.Random(77)), start=[1, 1], goal=[13, 13])


def _w(n: int, m: int, seed: int):
    """Strongly connected sparse graph (a Hamiltonian cycle plus random edges, weights 40..100) with a FIFO
    re-relaxation gadget next to s: s->a (100) is listed before s->b (40) and b->a (40), so a queue-based
    relaxation pops a, then improves it through b and pops it again."""
    rng = random.Random(seed)
    s, t = 0, n - 1
    a, b = 1, 2
    edges = [(s, a, 100), (s, b, 40), (b, a, 40)]
    order = [s] + rng.sample(range(1, n), n - 1)
    edges += [(u, v, rng.randint(40, 100)) for u, v in zip(order, order[1:] + order[:1])]
    while len(edges) < m:
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            edges.append((u, v, rng.randint(40, 100)))
    return dict(n=n, edges=edges, s=s, t=t)


def _w3():
    return dict(n=6, edges=[(0, 1, 50), (1, 2, 50), (0, 3, 60), (3, 2, -30), (2, 5, 40), (3, 4, 45), (4, 5, 70)],
                s=0, t=5)


CRAFTED = {"T1": {"G1": _g1(), "G2": _g2(), "G3": _g3()},
           "T2": {"W1": _w(20, 40, 5), "W2": _w(30, 60, 5), "W3": _w3()}}


def run_trace(code: str, task: str, name: str, timeout: float = 6.0) -> dict:
    inp = dict(CRAFTED[task][name], timeout=timeout)
    with tempfile.TemporaryDirectory(prefix="tr_") as td:
        td = Path(td)
        prog, ip, op = td / "solution.py", td / "input.json", td / "out.json"
        prog.write_text(code)
        ip.write_text(json.dumps(inp))
        try:
            subprocess.run([sys.executable, "-I", str(DRIVER), str(prog), task, str(ip), str(op)], cwd=td,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=timeout + 6)
        except subprocess.TimeoutExpired:
            return {"res": {"status": "driver_timeout"}, "events": [], "calls": [], "state": {}}
        if not op.exists():
            return {"res": {"status": "driver_crash"}, "events": [], "calls": [], "state": {}}
        try:
            return json.loads(op.read_text())
        except json.JSONDecodeError:
            return {"res": {"status": "bad_output"}, "events": [], "calls": [], "state": {}}


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 4:
        return None
    from scipy.stats import spearmanr
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    r = spearmanr(a, b).statistic
    return None if r is None or math.isnan(r) else float(r)


FIFO = {("deque", "popleft"), ("list", "pop0"), ("queue_fifo", "get")}
LIFO = {("deque", "pop"), ("list", "pop"), ("queue_lifo", "get")}


def t1_features(payload: dict, inp: dict) -> dict:
    grid = inp["grid"]
    start, goal = tuple(inp["start"]), tuple(inp["goal"])
    dist = bfs_dist(grid, start)

    def h(c):
        return abs(c[0] - goal[0]) + abs(c[1] - goal[1])

    ev = payload.get("events", [])
    calls = payload.get("calls", [])
    pops = [e for e in ev if e[0] == "pop" and e[4] is not None]
    heap_pops = [e for e in pops if e[1] == "heap"]
    fifo = [e for e in pops if (e[1], e[3]) in FIFO]
    lifo = [e for e in pops if (e[1], e[3]) in LIFO]
    max_self = {}
    for c in calls:
        max_self[c[0]] = max(max_self.get(c[0], 0), c[1])
    rec_funcs = {nm for nm, d in max_self.items() if d >= 2}
    call_exp = [c for c in calls if c[0] in rec_funcs and c[2] is not None]
    # expansion sequence: container pops with a cell, plus calls of recursive user functions, in event order
    seq = [(e[6], tuple(e[4]), "pop") for e in pops if e[1] in ("heap", "deque", "list", "queue_fifo", "queue_lifo")]
    seq += [(c[3], tuple(c[2]), "call", c[1]) for c in call_exp]
    seq.sort(key=lambda x: x[0])
    exp_cells = [x[1] for x in seq]
    n_exp = len(exp_cells)
    # start expansions: pops of start, and top-level (self-depth 1) calls on start
    start_idx = [i for i, x in enumerate(seq) if x[1] == start and (x[2] == "pop" or x[3] == 1)]
    segments = []
    for j, i0 in enumerate(start_idx):
        i1 = start_idx[j + 1] if j + 1 < len(start_idx) else len(seq)
        seg = [dist.get(seq[k][1], 0) for k in range(i0, i1)]
        segments.append(dict(size=len(seg), maxd=max(seg) if seg else 0,
                             first_next=dist.get(seq[i0 + 1][1], None) if i0 + 1 < i1 else None))
    iddfs_sig = False
    if len(start_idx) >= 3:
        maxds = [s["maxd"] for s in segments]
        nondec = sum(b >= a for a, b in zip(maxds, maxds[1:])) / max(len(maxds) - 1, 1)
        restart = sum(1 for s in segments[1:] if s["first_next"] is not None and s["first_next"] <= 1) / \
            max(len(segments) - 1, 1)
        iddfs_sig = nondec >= 0.8 and restart >= 0.6 and maxds[-1] >= maxds[0] + 2
    early_k = max(1, int(0.25 * n_exp))
    goal_side_early = any(h(c) <= 2 for c in exp_cells[:early_k]) and n_exp >= 8
    # revision 1: stale/duplicate pops (a cell popped again after its first pop) are excluded, and monotonicity
    # tolerates <= 3% decreasing steps (a start cell re-pushed by a neighbour no longer breaks BFS detection)
    seen_f = set()
    fifo_first = []
    for e in fifo:
        c = tuple(e[4])
        if c not in seen_f:
            seen_f.add(c)
            fifo_first.append(e)
    fifo_dists = [dist.get(tuple(e[4]), 10 ** 6) for e in fifo_first]
    steps = list(zip(fifo_dists, fifo_dists[1:]))
    bfs_monotone = len(fifo_dists) >= 5 and sum(b >= a for a, b in steps) >= 0.97 * len(steps)
    fifo_containers = Counter(e[2] for e in fifo)
    n_fifo_containers = sum(1 for v in fifo_containers.values() if v >= 2)
    seen_h = set()
    keyed = []
    for e in heap_pops:
        c = tuple(e[4])
        if e[5] is not None and c not in seen_h:
            seen_h.add(c)
            keyed.append((e[5], c))
    eq_gh = sum(1 for k, c in keyed if c in dist and (abs(k - (dist[c] + h(c))) < 1e-9 or abs(k - h(c)) < 1e-9))
    eq_g = sum(1 for k, c in keyed if c in dist and abs(k - dist[c]) < 1e-9)
    ks = [k for k, c in keyed if c in dist]
    gh = [dist[c] + h(c) for k, c in keyed if c in dist]
    g_only = [dist[c] for k, c in keyed if c in dist]
    h_only = [h(c) for k, c in keyed if c in dist]
    pushes = [e for e in ev if e[0] == "push" and e[1] == "list" and e[3] == "append" and e[4] is not None]
    app_d = [dist.get(tuple(e[4]), 10 ** 6) for e in pushes]
    res = payload.get("res", {})
    shortest = dist.get(goal)
    return dict(
        status=res.get("status"), heap_pops=len(heap_pops), fifo_pops=len(fifo), lifo_pops=len(lifo),
        n_pops_total=len(pops), max_recursion_depth=max(max_self.values(), default=0),
        n_rec_funcs=len(rec_funcs), n_expansions=n_exp, n_distinct=len(set(exp_cells)),
        start_expansions=len(start_idx), iddfs_signature=iddfs_sig, goal_side_early=goal_side_early,
        bfs_monotone=bfs_monotone, n_fifo_containers=n_fifo_containers,
        frac_key_gh_or_h=(eq_gh / len(keyed)) if keyed else None, frac_key_g=(eq_g / len(keyed)) if keyed else None,
        spearman_key_g=spearman(ks, g_only), spearman_key_gh=spearman(ks, gh), spearman_key_h=spearman(ks, h_only),
        n_appends=len(pushes), appends_monotone=len(app_d) >= 5 and all(b >= a for a, b in zip(app_d, app_d[1:])),
        out_len=res.get("out_len"), shortest_len=None if shortest is None else shortest + 1,
        truncated=payload.get("truncated", False), lines=payload.get("state", {}).get("lines", 0))


def t1_rules(f: dict, bfs_ref_distinct: int | None) -> tuple[str | None, str]:
    if f["status"] not in ("ok", "timeout") or f["n_expansions"] + f["n_pops_total"] == 0:
        if f["n_appends"] == 0 and f["max_recursion_depth"] <= 1:
            return None, "no_events"
    heap_used = f["heap_pops"] >= 3
    if heap_used and f["frac_key_gh_or_h"] is not None and f["frac_key_gh_or_h"] >= 0.9:
        return "astar_greedy", "R1:key==g+h|h"
    heur_corr = max([x for x in (f["spearman_key_gh"], f.get("spearman_key_h")) if x is not None], default=None)
    if heap_used and heur_corr is not None and heur_corr >= 0.9 and bfs_ref_distinct and \
            f["n_distinct"] < 0.5 * bfs_ref_distinct and not (f["frac_key_g"] or 0) >= 0.9:
        return "astar_greedy", "R1b:spearman(key,g+h|h)>=0.9&few_expansions (rev1: h added)"
    if heap_used and f["frac_key_g"] is not None and f["frac_key_g"] >= 0.9:
        return "dijkstra_unit", "R2:key==g"
    if f["iddfs_signature"]:
        return "iddfs", "R3:start re-expanded under growing limits"
    fifo_dom = f["fifo_pops"] >= 5 and f["fifo_pops"] > f["lifo_pops"]
    if fifo_dom and f["goal_side_early"] and f["n_fifo_containers"] >= 2:
        return "bidirectional_bfs", "R4:two FIFO frontiers, goal side early"
    if fifo_dom and f["bfs_monotone"]:
        return "bfs", "R5:FIFO & monotone distance"
    if f["n_pops_total"] == 0 and f["n_appends"] >= 5 and f["appends_monotone"] and f["max_recursion_depth"] <= 10:
        return "bfs", "R5b:level lists, monotone appends"
    lifo_dom = f["lifo_pops"] >= 3 and f["lifo_pops"] > f["fifo_pops"]
    if lifo_dom or f["max_recursion_depth"] > 10:
        return "dfs", "R6:LIFO or deep recursion"
    return None, "R7:no rule"


def t2_features(p1: dict, p2: dict, inp1: dict, inp2: dict) -> dict:
    ev = p1.get("events", [])
    pops = [e for e in ev if e[0] == "pop" and e[4] is not None]
    heap_pops = [e for e in pops if e[1] == "heap"]
    t = inp1["t"]
    heap_cont = Counter(e[2] for e in heap_pops)
    early = max(2, int(0.25 * len(heap_pops)))
    t_early = any(e[4] == t for e in heap_pops[:early])
    first_pop = {}
    for e in heap_pops:
        first_pop.setdefault(e[2], e[4])
    s_node = inp1["s"]
    # revision 2: the two searches must be interleaved (pops alternate between heaps at least twice); two Dijkstra
    # runs executed one after the other are plain Dijkstra, not a bidirectional search
    seq_c = [e[2] for e in heap_pops]
    switches = sum(1 for a, b in zip(seq_c, seq_c[1:]) if a != b)
    two_sided = len(heap_cont) >= 2 and t in first_pop.values() and s_node in first_pop.values() and \
        (switches >= 2 or len(heap_pops) <= 3)
    fifo = [e for e in pops if (e[1], e[3]) in FIFO]
    fifo_nodes = Counter(e[4] for e in fifo)
    fifo2 = [e for e in p2.get("events", []) if e[0] == "pop" and e[4] is not None and (e[1], e[3]) in FIFO]
    fifo_repops = any(v >= 2 for v in fifo_nodes.values()) or any(v >= 2 for v in Counter(e[4] for e in fifo2).values())
    nonheap_cont = Counter(e[2] for e in pops if e[1] in ("list", "deque", "set"))
    l1 = p1.get("state", {}).get("lines", 0)
    l2 = p2.get("state", {}).get("lines", 0)
    growth = math.log(l2 / l1) / math.log(inp2["n"] / inp1["n"]) if l1 > 0 and l2 > 0 else None
    res = p1.get("res", {})
    return dict(status=res.get("status"), status_w2=p2.get("res", {}).get("status"), heap_pops=len(heap_pops),
                n_heaps=len(heap_cont), two_sided=two_sided, t_popped_early=t_early,
                n_full_edge_list_passes=p1.get("state", {}).get("edge_iters", 0),
                edge_getitem=p1.get("state", {}).get("edge_getitem", 0), fifo_pops=len(fifo),
                fifo_repops=fifo_repops, n_nonheap_containers_popped=len(nonheap_cont),
                growth_exponent=None if growth is None else round(growth, 3), lines_w1=l1, lines_w2=l2,
                out=res.get("out"), max_recursion_depth=p1.get("state", {}).get("max_depth", 0))


def t2_rules(f: dict) -> tuple[str | None, str]:
    if f["status"] not in ("ok", "timeout"):
        return None, f"status:{f['status']}"
    heap_used = f["heap_pops"] >= 2
    if heap_used and f["two_sided"]:
        return "bidirectional_dijkstra", "R1:two heaps, t popped early"
    if heap_used:
        return "dijkstra", "R2:heap"
    # revision 1 (on references, before the gate): growth >= 2.5 missed a Floyd-Warshall with an INF-skip; a cubic
    # program also runs >= n^3/2 line events on W2 (n=30), which no quadratic relaxation does
    if f["growth_exponent"] is not None and (f["growth_exponent"] >= 2.5 or (
            f["growth_exponent"] >= 2.2 and f["lines_w2"] >= 0.5 * 30 ** 3)):
        return "floyd_warshall", "R3:cubic growth"
    if f["n_full_edge_list_passes"] >= 2 or (f["fifo_repops"] and not heap_used):
        return "bellman_ford_spfa", "R4:repeated edge passes or FIFO re-pops"
    if f["n_nonheap_containers_popped"] >= 3:
        return "dial", "R5:distance-indexed buckets"
    # revision 1: Bellman-Ford rounds over adjacency lists never re-iterate the edge list; their line count still
    # grows quadratically (rounds x edges) without any heap, FIFO queue or buckets
    if f["growth_exponent"] is not None and f["growth_exponent"] >= 1.6 and f["fifo_pops"] == 0:
        return "bellman_ford_spfa", "R4c:quadratic relaxation sweeps (rev1)"
    return None, "R6:no rule"


def _constants() -> dict:
    if CONST_FILE.exists():
        return json.loads(CONST_FILE.read_text())
    from common import REFS_DIR
    p = run_trace((REFS_DIR / "t1_bfs.py").read_text(), "T1", "G1")
    c = {"bfs_ref_distinct_G1": t1_features(p, CRAFTED["T1"]["G1"])["n_distinct"]}
    CONST_FILE.write_text(json.dumps(c))
    return c


def runtime_label(code: str, task: str) -> dict:
    """Return {label, rule, features} for one program."""
    try:
        if task == "T1":
            c = _constants()
            p1 = run_trace(code, "T1", "G1")
            f1 = t1_features(p1, CRAFTED["T1"]["G1"])
            lab, rule = t1_rules(f1, c["bfs_ref_distinct_G1"])
            feats = {"G1": f1}
            if lab is None:
                p3 = run_trace(code, "T1", "G3")
                f3 = t1_features(p3, CRAFTED["T1"]["G3"])
                feats["G3"] = f3
                lab3, rule3 = t1_rules(f3, None)
                if lab3 is not None:
                    lab, rule = lab3, "G3:" + rule3
            p2 = run_trace(code, "T1", "G2")
            f2 = t1_features(p2, CRAFTED["T1"]["G2"])
            feats["G2"] = {k: f2[k] for k in ("status", "n_expansions", "n_distinct", "out_len", "shortest_len")}
            return dict(label=lab, rule=rule, features=feats)
        p1 = run_trace(code, "T2", "W1")
        p2 = run_trace(code, "T2", "W2")
        f = t2_features(p1, p2, CRAFTED["T2"]["W1"], CRAFTED["T2"]["W2"])
        lab, rule = t2_rules(f)
        p3 = run_trace(code, "T2", "W3", timeout=3.0)
        f["w3_status"] = p3.get("res", {}).get("status")
        f["w3_out"] = p3.get("res", {}).get("out")
        return dict(label=lab, rule=rule, features=f)
    except Exception as e:  # noqa: BLE001 - the tracer must never kill a labelling worker
        return dict(label=None, rule=f"tracer_error:{type(e).__name__}:{str(e)[:100]}", features={})


if __name__ == "__main__":
    from common import REFS_DIR
    for f in sorted(REFS_DIR.glob("t*.py")):
        task = "T1" if f.name.startswith("t1") else "T2"
        r = runtime_label(f.read_text(), task)
        print(f.name, "->", r["label"], "|", r["rule"])
