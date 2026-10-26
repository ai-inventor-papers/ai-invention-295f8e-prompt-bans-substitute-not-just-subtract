"""B3 mst_weight (LeetCode 1135 source, 0-based cities, n <= 500, len(roads) <= 10000, parallel roads allowed)."""

from __future__ import annotations

import ast
import random

from unitlib import ast_tree, calls_named, ccount, names_used, opcount, pcount, probe

CHECKER = "exact"
ARGS = ["n", "roads"]

ORACLE_A = '''
def solve(n, roads):
    p = list(range(n))
    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    ans = 0
    comps = n
    for x, y, c in sorted(roads, key=lambda r: r[2]):
        a, b = find(x), find(y)
        if a != b:
            p[a] = b
            ans += c
            comps -= 1
    return ans if comps == 1 else -1
'''  # dataset reference (LeetCode 1135 row: Kruskal + path-compressed find), adapted to 0-based cities
ORACLE_B = '''
def solve(n, roads):
    INF = float("inf")
    w = [[INF] * n for _ in range(n)]
    for u, v, c in roads:
        if c < w[u][v]:
            w[u][v] = w[v][u] = c
    dist = [INF] * n
    vis = [False] * n
    dist[0] = 0
    total = 0
    for _ in range(n):
        i = -1
        for j in range(n):
            if not vis[j] and (i == -1 or dist[j] < dist[i]):
                i = j
        if dist[i] == INF:
            return -1
        vis[i] = True
        total += dist[i]
        row = w[i]
        for j in range(n):
            if not vis[j] and row[j] < dist[j]:
                dist[j] = row[j]
    return total
'''  # dataset alternate row (LeetCode 1584 dense Prim), adapted to roads

REFERENCES = {
    "kruskal": ORACLE_A,
    "prim_heap": '''
import heapq

def solve(n, roads):
    adj = [[] for _ in range(n)]
    for u, v, w in roads:
        adj[u].append((w, v))
        adj[v].append((w, u))
    seen = [False] * n
    heap = [(0, 0)]
    total = 0
    count = 0
    while heap and count < n:
        w, u = heapq.heappop(heap)
        if seen[u]:
            continue
        seen[u] = True
        total += w
        count += 1
        for e in adj[u]:
            if not seen[e[1]]:
                heapq.heappush(heap, e)
    return total if count == n else -1
''',
    "prim_array": ORACLE_B,
    "boruvka": '''
def solve(n, roads):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    comps = n
    total = 0
    while comps > 1:
        cheapest = [-1] * n
        for idx, (u, v, w) in enumerate(roads):
            a, b = find(u), find(v)
            if a == b:
                continue
            if cheapest[a] == -1 or w < roads[cheapest[a]][2]:
                cheapest[a] = idx
            if cheapest[b] == -1 or w < roads[cheapest[b]][2]:
                cheapest[b] = idx
        merged = False
        for c in range(n):
            if cheapest[c] != -1:
                u, v, w = roads[cheapest[c]]
                a, b = find(u), find(v)
                if a != b:
                    parent[a] = b
                    total += w
                    comps -= 1
                    merged = True
        if not merged:
            return -1
    return total
''',
}
MUTANTS = [
    '''
def solve(n, roads):
    ws = sorted(r[2] for r in roads)
    return sum(ws[:n - 1]) if len(ws) >= n - 1 else -1
''',
    '''
def solve(n, roads):
    p = list(range(n))
    def find(x):
        while p[x] != x:
            x = p[x]
        return x
    ans = 0
    for x, y, c in sorted(roads, key=lambda r: r[2]):
        a, b = find(x), find(y)
        if a != b:
            p[a] = b
            ans += c
    return ans
''',
    '''
def solve(n, roads):
    p = list(range(n))
    def find(x):
        while p[x] != x:
            x = p[x]
        return x
    ans = 0
    comps = n
    for x, y, c in sorted(roads, key=lambda r: -r[2]):
        a, b = find(x), find(y)
        if a != b:
            p[a] = b
            ans += c
            comps -= 1
    return ans if comps == 1 else -1
''',
]
EXCLUDED: dict[str, str] = {}


def _graph(rng: random.Random, n: int, m: int, connected: bool, wmax: int = 100000) -> list:
    roads = []
    if n >= 2:
        order = list(range(n))
        rng.shuffle(order)
        k = n if connected else max(1, n - 1 - rng.randint(1, max(1, n // 3)))
        for i in range(1, k):
            roads.append([order[i], order[rng.randrange(i)], rng.randint(0, wmax)])
        while len(roads) < m:
            u, v = rng.sample(range(n), 2)
            if not connected and (u >= k or v >= k):
                pass
            if not connected:
                cu = order.index(u) < k
                cv = order.index(v) < k
                if cu != cv:
                    continue
            roads.append([u, v, rng.randint(0, wmax)])
        rng.shuffle(roads)
        for r in roads:
            if rng.random() < 0.5:
                r[0], r[1] = r[1], r[0]
    return [n, roads]


def make_tests() -> list[dict]:
    rng = random.Random(1135)
    cases = [("ex0", [3, [[0, 1, 5], [0, 2, 6], [1, 2, 1]]]), ("ex1", [4, [[0, 1, 3], [2, 3, 4]]]),
             ("edge_n1", [1, []]), ("edge_n2_none", [2, []]), ("edge_parallel", [2, [[0, 1, 7], [1, 0, 3], [0, 1, 9]]]),
             ("edge_zero", [3, [[0, 1, 0], [1, 2, 0], [0, 2, 0]]])]
    specs = [(5, 6), (5, 10), (8, 12), (10, 30), (20, 40), (30, 90), (50, 100), (60, 300), (100, 300),
             (150, 1000), (200, 2000), (300, 3000)]
    i = 0
    while len(cases) < 6 + 48:
        n, m = specs[i % len(specs)]
        conn = (i % 4 != 3)
        cases.append((f"rand{i}", _graph(rng, n, m, conn, wmax=rng.choice([10, 1000, 100000]))))
        i += 1
    for j in range(10):
        n = 500 if j < 7 else 142
        m = 10000
        cases.append((f"stress{j}", _graph(rng, n, m, j != 6)))
    return [{"case_id": f"B3:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe(name: str, n: int, m: int, seed: int) -> dict:
    a = _graph(random.Random(seed), n, m, True)
    ns: dict = {}
    exec(ORACLE_A, ns)
    return {"name": name, "args": a, "wrap": ["raw", "roads"], "expected": ns["solve"](*a)}


PROBES = [_probe("sparse", 200, 400, 5), _probe("dense", 40, 780, 6)]


def _pushes_before_first_pop(seq: list[str]) -> int:
    k = 0
    for s in seq:
        if s == "heappop":
            return k
        if s == "heappush":
            k += 1
    return k


def runtime_rule(tr: dict) -> str | None:
    s, d = probe(tr, "sparse"), probe(tr, "dense")
    if s is None or d is None or s.get("error") or d.get("error"):
        return None
    m = 400
    sorts = ccount(s, "sorted", "list.sort")
    cmp_s = opcount(s, "cmp")
    hp, hpop, hfy = ccount(s, "heappush"), ccount(s, "heappop"), ccount(s, "heapify")
    pre = _pushes_before_first_pop(s.get("seq", []))
    if pcount(s, "itertools.combinations", "itertools.permutations", "itertools.product") >= 1:
        return "other"
    if sorts >= 1 and (cmp_s >= m or s["user_calls"] >= 0.5 * m):
        return "kruskal"
    if hfy >= 1 and hp < 0.1 * m and hpop >= 1:
        return "kruskal"
    if hp >= 0.5 * m and pre >= 0.5 * m:
        return "kruskal"
    if hp >= 1 or hpop >= 1:
        return "prim_heap"
    if s["lines"] == 0 and cmp_s == 0:
        return None
    ratio = s["lines"] / max(d["lines"], 1)
    if ratio >= 4:
        return "prim_array"
    if cmp_s >= 1.5 * m and s["user_calls"] >= m:
        return "boruvka"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if any(c in calls for c in ("combinations", "permutations", "product")):
        return "other"
    names = {x.lower() for x in names_used(t)}
    dsu = any(k in names for k in ("find", "parent", "union", "rank", "dsu", "uf", "par", "root", "unionfind")) or \
        any("find" in x or "union" in x or "parent" in x for x in names)
    sorts = "sorted" in calls or "sort" in calls
    heap = any(c in calls for c in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace"))
    if sorts and dsu:
        return "kruskal"
    if heap:
        if dsu and "heapify" in calls and "heappush" not in calls:
            return "kruskal"
        if dsu and not any("visit" in x or "seen" in x or "in_mst" in x or "inmst" in x for x in names):
            return "kruskal"
        return "prim_heap"
    if any("cheap" in x for x in names) or (dsu and any(isinstance(n, ast.While) for n in ast.walk(t))):
        return "boruvka"
    loops = [n for n in ast.walk(t) if isinstance(n, (ast.For, ast.While))]
    nested = any(isinstance(m, (ast.For, ast.While)) for l in loops for m in ast.walk(l) if m is not l)
    marks = any(any(k in x for k in ("vis", "seen", "used", "in_mst", "inmst", "intree", "in_tree", "added", "done",
                                      "dist", "key", "selected", "taken", "included"))
                for x in names)
    if nested and not dsu and marks:
        return "prim_array"
    return "other"
