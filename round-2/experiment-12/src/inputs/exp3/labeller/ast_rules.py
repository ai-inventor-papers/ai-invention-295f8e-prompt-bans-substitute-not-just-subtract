"""AST labeller (secondary): static feature extraction plus ordered rules mapping features to a catalogue label."""

from __future__ import annotations

import ast
import re

HEUR_NAMES = re.compile(r"(heur|manhattan|^h$|^h_|_h$|estimate|astar|a_star)", re.I)
BIDIR_NAMES = re.compile(r"(bidir|backward|_bwd|bwd_|reverse|_rev|rev_|from_goal|from_end|_b$|_t$|goal_|end_)", re.I)
BUCKET_NAMES = re.compile(r"bucket", re.I)
INQ_NAMES = re.compile(r"(in_?q|in_queue|inqueue|queued|in_que)", re.I)


def _name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


ALIASES: dict[str, str] = {}


def _call_name(call: ast.Call) -> str:
    nm = _name(call.func)
    return ALIASES.get(nm, nm)


def _loop_vars(node) -> set[str]:
    out = set()
    if isinstance(node, ast.For):
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name):
                out.add(n.id)
    return out


def extract_features(code: str) -> dict:
    f: dict = {"parse_ok": False}
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return f
    f["parse_ok"] = True
    ALIASES.clear()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for al in n.names:
                if al.asname:
                    ALIASES[al.asname] = al.name
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    f["has_solve"] = "solve" in funcs
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imports.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                imports.add(f"{n.module}.{a.name}")
    f["imports"] = sorted(imports)
    f["imp_heapq"] = any(i.startswith("heapq") for i in imports)
    f["imp_deque"] = any(i in ("collections.deque",) for i in imports) or ("collections" in imports)
    f["imp_queue"] = sorted(i for i in imports if i.startswith("queue"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    cn = [_call_name(c) for c in calls]
    f["heappush"] = sum(1 for c in cn if c in ("heappush", "heappushpop", "heapreplace"))
    f["heappop"] = cn.count("heappop")
    heap_vars = set()
    for c in calls:
        if _call_name(c) in ("heappush", "heappop", "heappushpop", "heapreplace", "heapify") and c.args:
            heap_vars.add(ast.unparse(c.args[0]))
    f["n_heap_vars"] = len(heap_vars)
    f["pq_class"] = any(c in ("PriorityQueue",) for c in cn)
    f["fifo_queue_class"] = any(c == "Queue" for c in cn)
    f["lifo_queue_class"] = any(c == "LifoQueue" for c in cn)
    f["popleft"] = cn.count("popleft")
    f["appendleft"] = cn.count("appendleft")
    pop0 = popn = 0
    for c in calls:
        if isinstance(c.func, ast.Attribute) and c.func.attr == "pop":
            if not c.args:
                popn += 1
            elif isinstance(c.args[0], ast.Constant) and c.args[0].value == 0:
                pop0 += 1
            elif isinstance(c.args[0], ast.UnaryOp) and isinstance(c.args[0].op, ast.USub):
                popn += 1
    f["pop0"], f["pop_end"] = pop0, popn
    n_deque_ctor = sum(1 for c in cn if c == "deque")
    f["n_deque_ctor"] = n_deque_ctor
    # self recursion
    rec_funcs = set()
    for name, fn in funcs.items():
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and _call_name(n) == name and n is not fn:
                rec_funcs.add(name)
    f["recursive_funcs"] = sorted(rec_funcs)
    # IDDFS: an outer loop whose loop var is passed to a recursive (or depth-limited) function
    iddfs = False
    inside_rec = set()
    for name in rec_funcs:
        for n in ast.walk(funcs[name]):
            inside_rec.add(id(n))
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        if id(loop) in inside_rec:
            continue  # a loop inside the recursive function itself is DFS neighbour expansion, not deepening
        lv = _loop_vars(loop)
        for n in ast.walk(loop):
            if isinstance(n, ast.Call) and _call_name(n) in rec_funcs:
                argnames = {a.id for a in ast.walk(n) if isinstance(a, ast.Name)}
                if lv & argnames:
                    iddfs = True
    lower = code.lower()
    if re.search(r"iddfs|iterative[_ ]deepening|depth[_ ]limit(ed)?", lower) and (rec_funcs or "limit" in lower):
        iddfs = True
    f["iddfs"] = iddfs
    # Floyd-Warshall triple loop with d[i][k] + d[k][j]
    fw = False
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            l, r = n.left, n.right
            if (isinstance(l, ast.Subscript) and isinstance(r, ast.Subscript) and isinstance(l.value, ast.Subscript)
                    and isinstance(r.value, ast.Subscript)):
                try:
                    li, lk = ast.unparse(l.value.slice), ast.unparse(l.slice)
                    rk, rj = ast.unparse(r.value.slice), ast.unparse(r.slice)
                except Exception:  # noqa: BLE001
                    continue
                if lk == rk and li != lk and rj != rk:
                    fw = True
    nested3 = False
    for a in ast.walk(tree):
        if isinstance(a, ast.For):
            for b in ast.walk(a):
                if b is not a and isinstance(b, ast.For):
                    for c in ast.walk(b):
                        if c is not b and isinstance(c, ast.For):
                            nested3 = True
    f["floyd"] = fw and nested3
    # Bellman-Ford: loop over range(n-1)/range(n)/while-changed containing a loop over the edges list
    bf = False
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        outer_ok = False
        if isinstance(loop, ast.For) and isinstance(loop.iter, ast.Call) and _call_name(loop.iter) == "range":
            outer_ok = True
        if isinstance(loop, ast.While):
            src = ast.unparse(loop.test)
            if re.search(r"(chang|updat|relax|improv|modif)", src, re.I) or src.strip() == "True":
                outer_ok = True
        if not outer_ok:
            continue
        has_inner_loop = False
        relax = False
        for inner in ast.walk(loop):
            if inner is not loop and isinstance(inner, ast.For):
                has_inner_loop = True
                it = ast.unparse(inner.iter)
                if re.fullmatch(r"(edges|edge_list|E|graph_edges|all_edges)", it.strip()):
                    bf = True
            if isinstance(inner, ast.Compare) and len(inner.comparators) == 1:
                sides = [inner.left, inner.comparators[0]]
                if any(isinstance(sd, ast.BinOp) and isinstance(sd.op, ast.Add) for sd in sides) and \
                        any(isinstance(sd, ast.Subscript) for sd in sides):
                    relax = True
        if has_inner_loop and relax and isinstance(loop, ast.For):
            rng_src = ast.unparse(loop.iter)
            if re.search(r"range\((n|V|num_nodes|len\(\w+\))\s*(-\s*1)?\)", rng_src):
                bf = True
        if has_inner_loop and relax and isinstance(loop, ast.While):
            bf = True
    f["bellman_ford"] = bf
    # SPFA: FIFO queue with in-queue flags or a membership test on the queue
    inq = bool(re.search(r"\b(in_?q\w*|in_queue\w*|inqueue\w*|queued\w*)\b", code, re.I))
    memb_q = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops):
            rhs = ast.unparse(n.comparators[0])
            if re.fullmatch(r"(q|queue|dq|que|deq|fifo)\w*", rhs.strip(), re.I):
                memb_q = True
    f["spfa"] = (f["popleft"] > 0 or pop0 > 0 or f["fifo_queue_class"]) and (inq or memb_q or "spfa" in lower)
    # queue-based label-correcting (SPFA without flags): a while loop with a FIFO pop, a weighted relaxation test
    # and an append of the relaxed node inside it
    relax_fifo = False
    for loop in [n for n in ast.walk(tree) if isinstance(n, ast.While)]:
        sub = list(ast.walk(loop))
        fifo_pop = any(isinstance(n, ast.Call) and (_call_name(n) in ("popleft", "get") or (
            isinstance(n.func, ast.Attribute) and n.func.attr == "pop" and n.args and
            isinstance(n.args[0], ast.Constant) and n.args[0].value == 0)) for n in sub)
        relax = any(isinstance(n, ast.Compare) and len(n.comparators) == 1 and any(
            isinstance(sd, ast.BinOp) and isinstance(sd.op, ast.Add) for sd in (n.left, n.comparators[0]))
            for n in sub)
        app = any(isinstance(n, ast.Call) and _call_name(n) in ("append", "put", "appendleft") for n in sub)
        if fifo_pop and relax and app:
            relax_fifo = True
    f["relax_fifo"] = relax_fifo
    f["bucket"] = bool(BUCKET_NAMES.search(code)) or bool(re.search(r"\bdial\b", lower))
    # bidirectional: two heaps / two FIFO queues / names
    two_q = n_deque_ctor >= 2 and f["popleft"] >= 2
    f["bidirectional"] = (f["n_heap_vars"] >= 2 and f["heappop"] >= 2) or two_q or bool(
        re.search(r"bidirection|bi_direction|bi-direction|meet[_ ]in[_ ]the[_ ]middle", lower))
    # heuristic (Manhattan) in the priority
    manh = False
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            if (isinstance(n.left, ast.Call) and _call_name(n.left) == "abs" and isinstance(n.right, ast.Call)
                    and _call_name(n.right) == "abs"):
                manh = True
    heur_fn = any(HEUR_NAMES.search(nm) for nm in funcs)
    f["heuristic"] = manh or heur_fn or bool(re.search(r"heuristic|manhattan|a\*|astar|a_star|best[-_ ]first|greedy",
                                                          lower))
    # min-scan Dijkstra (no heap)
    f["min_scan"] = any(c == "min" for c in cn) and bool(re.search(r"(visited|unvisited|done|settled|processed|"
                                                                     r"finalized|used)", lower))
    f["dijkstra_word"] = "dijkstra" in lower
    return f


def label_t1(f: dict) -> str:
    if not f.get("parse_ok") or not f.get("has_solve"):
        return "no_code"
    if f["bidirectional"]:
        return "bidirectional_BFS"
    if f["heappush"] or f["pq_class"]:
        return "astar_greedy" if f["heuristic"] else "unit_dijkstra"
    if f["iddfs"]:
        return "IDDFS"
    if f["popleft"] or f["pop0"] or f["fifo_queue_class"]:
        return "BFS"
    if f["recursive_funcs"] or f["pop_end"] or f["lifo_queue_class"]:
        return "DFS"
    return "other"


def label_t2(f: dict) -> str:
    if not f.get("parse_ok") or not f.get("has_solve"):
        return "no_code"
    if f["floyd"]:
        return "floyd_warshall"
    if f["bidirectional"] and (f["heappush"] or f["pq_class"]):
        return "bidirectional_dijkstra"
    if f["heappush"] or f["pq_class"]:
        return "dijkstra"
    if f["bucket"]:
        return "dial"
    if f["bellman_ford"] or f["spfa"] or f.get("relax_fifo"):
        return "bellman_ford_spfa"
    if f["min_scan"]:
        return "dijkstra"
    if (f["popleft"] or f["pop0"] or f["fifo_queue_class"]) and not f["appendleft"]:
        return "other"
    return "other"


def ast_label(task: str, code: str) -> tuple[str, dict]:
    f = extract_features(code)
    return (label_t1(f) if task == "T1" else label_t2(f)), f
