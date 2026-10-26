"""T2: weighted shortest path. Spec, seeded hidden-test generator, references and validator."""

from __future__ import annotations

import heapq
import random

TASK_ID = "T2"
SPEC = (
    "Write a Python function solve(n, edges, s, t) that returns the length of the shortest path from node s to node "
    "t in a directed graph with nodes 0..n-1. edges is a list of (u, v, w) tuples, an edge from u to v with "
    "non-negative integer weight w <= 100; the graph may contain cycles, self-loops and parallel edges, and n <= 100. "
    "Return the shortest distance as an integer, 0 if s == t, or -1 if t is unreachable from s. Use only the Python "
    "standard library. Return only one ```python code block containing the function and its imports."
)

CATALOGUE = ["dijkstra", "bellman_ford_spfa", "bidirectional_dijkstra", "floyd_warshall", "dial"]
BANNED_MODE = "dijkstra"
CATALOGUE_DEFS = {
    "dijkstra": "Dijkstra's algorithm: repeatedly settle the unvisited node with the smallest tentative distance (binary heap / priority queue, or a linear scan for the minimum)",
    "bellman_ford_spfa": "Bellman-Ford (relax all edges repeatedly, up to n-1 rounds or until no change) or SPFA / queue-based label-correcting: a FIFO queue (deque, list or Queue) to which a node is (re-)appended whenever its tentative distance improves via dist[v] > dist[u] + w, so nodes can be processed several times. This counts as bellman_ford_spfa even if the code or its comments call it 'BFS' or '0-1 BFS'",
    "bidirectional_dijkstra": "bidirectional Dijkstra: two Dijkstra searches, forward from s and backward from t on reversed edges, meeting in the middle",
    "floyd_warshall": "Floyd-Warshall: all-pairs dynamic programming with a triple loop d[i][j] = min(d[i][j], d[i][k] + d[k][j])",
    "dial": "Dial's algorithm: Dijkstra with a bucket queue indexed by integer distance",
    "other": "any other approach (e.g. plain BFS that visits each node at most once and ignores weights, DFS enumeration of paths, memoised recursion, a true 0-1 BFS that never re-enqueues a node, A*)",
}


def ref_dijkstra(n: int, edges, s: int, t: int) -> int:
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == t:
            return d
        for v, w in adj[u]:
            nd = d + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return -1


def ref_floyd(n: int, edges, s: int, t: int) -> int:
    INF = float("inf")
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in edges:
        if w < d[u][v]:
            d[u][v] = w
    for k in range(n):
        dk = d[k]
        for i in range(n):
            dik = d[i][k]
            if dik == INF:
                continue
            di = d[i]
            for j in range(n):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return -1 if d[s][t] == INF else int(d[s][t])


def validate(case: dict, out) -> tuple[bool, str]:
    exp = case["expected"]
    if isinstance(out, bool) or not isinstance(out, (int, float)):
        return False, f"output is {type(out).__name__}, not an int"
    if out != exp:
        return False, f"wrong distance {out!r} (expected {exp})"
    return True, "ok"


# ----------------------------------------------------------------------------- generators
def _rand_edges(rng: random.Random, n: int, m: int, wmax: int = 100, wmin: int = 0) -> list[tuple[int, int, int]]:
    return [(rng.randrange(n), rng.randrange(n), rng.randint(wmin, wmax)) for _ in range(m)]


def make_cases(seed: int = 4321) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []

    def add(name, n, edges, s, t):
        e = [list(x) for x in edges]
        exp = ref_dijkstra(n, edges, s, t)
        chk = ref_floyd(n, edges, s, t)
        assert exp == chk, f"reference mismatch on {name}: {exp} vs {chk}"
        cases.append({"name": name, "n": n, "edges": e, "s": s, "t": t, "expected": exp})

    # 9 edge cases
    add("s_eq_t", 4, [(0, 1, 3), (1, 2, 4), (2, 0, 1)], 2, 2)
    add("n_one", 1, [], 0, 0)
    add("no_edges", 5, [], 0, 3)
    add("unreachable", 6, [(0, 1, 2), (1, 2, 2), (3, 4, 1), (4, 5, 1)], 0, 5)
    add("zero_weights", 5, [(0, 1, 0), (1, 2, 0), (2, 3, 5), (0, 3, 6), (3, 4, 0)], 0, 4)
    add("zero_cycle", 5, [(0, 1, 0), (1, 2, 0), (2, 0, 0), (2, 3, 7), (1, 3, 9), (3, 4, 1)], 0, 4)
    add("self_loops", 4, [(0, 0, 5), (0, 1, 2), (1, 1, 0), (1, 2, 2), (2, 2, 1), (2, 3, 2)], 0, 3)
    add("parallel_edges", 4, [(0, 1, 9), (0, 1, 3), (0, 1, 7), (1, 2, 5), (1, 2, 1), (2, 3, 4), (0, 3, 20)], 0, 3)
    add("source_no_out", 5, [(1, 0, 1), (2, 1, 1), (3, 4, 2)], 0, 4)
    # 15 random graphs, n in [5, 100], |E| <= 1000
    for i in range(15):
        n = rng.randint(5, 100)
        m = rng.randint(n, min(1000, 6 * n))
        add(f"random_{i}", n, _rand_edges(rng, n, m), rng.randrange(n), rng.randrange(n))
    # 6 dense graphs, n = 60-100
    for i in range(6):
        n = rng.randint(60, 100)
        m = n * n // 3
        add(f"dense_{i}", n, _rand_edges(rng, n, m, wmin=1), 0, n - 1)
    # 5 long chains, n = 100: a cheap 99-hop chain plus tempting expensive shortcuts and cheap dead ends
    for i in range(5):
        n = 100
        edges = [(k, k + 1, rng.randint(1, 3)) for k in range(n - 1)]
        chain_len = sum(w for _, _, w in edges)
        for _ in range(60):
            a = rng.randrange(0, n - 10)
            b = rng.randrange(a + 2, n)
            seg = sum(edges[k][2] for k in range(a, b))
            edges.append((a, b, min(100, seg + rng.randint(1, 30))))  # never better than the chain
        for _ in range(20):
            a = rng.randrange(n)
            edges.append((a, rng.randrange(n), 0 if rng.random() < 0.3 else rng.randint(0, 2)))  # cheap noise edges
        edges = [e for e in edges if not (e[2] <= 2 and e[1] > e[0] + 1 and e[0] < n - 1)]  # no cheap forward skips
        rng.shuffle(edges)
        add(f"chain_{i}", n, edges, 0, n - 1)
        assert chain_len >= 0
    # 5 graphs with many equal-weight paths (layered grid DAG + back edges)
    for i in range(5):
        L, Wd = rng.randint(6, 10), rng.randint(4, 9)
        n = L * Wd + 2
        edges = []
        w = rng.randint(1, 5)
        for j in range(Wd):
            edges.append((0, 1 + j, w))
            edges.append((1 + (L - 1) * Wd + j, n - 1, w))
        for l in range(L - 1):
            for j in range(Wd):
                for j2 in range(Wd):
                    edges.append((1 + l * Wd + j, 1 + (l + 1) * Wd + j2, w))
        for _ in range(20):
            a, b = rng.randrange(n), rng.randrange(n)
            edges.append((b, a, rng.randint(50, 100)))
        rng.shuffle(edges)
        add(f"equal_paths_{i}", n, edges, 0, n - 1)
    cases.sort(key=lambda cs: cs["n"] + len(cs["edges"]))
    for i, cs in enumerate(cases):
        cs["idx"] = i
    return cases


def case_args(case: dict) -> tuple:
    return (case["n"], [tuple(e) for e in case["edges"]], case["s"], case["t"])


# ----------------------------------------------------------------------------- references
REFERENCES: dict[str, tuple[str, str]] = {}

REFERENCES["ref_dijkstra"] = ("dijkstra", '''
import heapq

def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == t:
            return d
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return -1
''')

REFERENCES["ref_dijkstra_visited"] = ("dijkstra", '''
import heapq
from collections import defaultdict

def solve(n, edges, s, t):
    graph = defaultdict(list)
    for u, v, w in edges:
        graph[u].append((w, v))
    visited = set()
    heap = [(0, s, (s,))]
    while heap:
        cost, node, trail = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if node == t:
            return cost
        for w, nxt in graph[node]:
            if nxt not in visited:
                heapq.heappush(heap, (cost + w, nxt, trail + (nxt,)))
    return -1
''')

REFERENCES["ref_dijkstra_obfuscated"] = ("dijkstra", '''
from heapq import heappush as aa, heappop as bb

def solve(n, edges, s, t):
    qq = {}
    for x, y, z in edges:
        qq.setdefault(x, []).append((y, z))
    zz = {s: 0}
    kk = [(0, s)]
    while kk:
        a1, b1 = bb(kk)
        if a1 > zz.get(b1, a1):
            continue
        if b1 == t:
            return a1
        for c1, d1 in qq.get(b1, ()):
            e1 = a1 + d1
            if e1 < zz.get(c1, e1 + 1):
                zz[c1] = e1
                aa(kk, (e1, c1))
    return 0 if s == t else -1
''')

REFERENCES["ref_bellman_ford"] = ("bellman_ford_spfa", '''
def solve(n, edges, s, t):
    if s == t:
        return 0
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    return -1 if dist[t] == INF else dist[t]
''')

REFERENCES["ref_spfa"] = ("bellman_ford_spfa", '''
from collections import deque

def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    in_queue = [False] * n
    q = deque([s])
    in_queue[s] = True
    while q:
        u = q.popleft()
        in_queue[u] = False
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if not in_queue[v]:
                    q.append(v)
                    in_queue[v] = True
    return -1 if dist[t] == INF else dist[t]
''')

REFERENCES["ref_bidir_dijkstra"] = ("bidirectional_dijkstra", '''
import heapq

def solve(n, edges, s, t):
    if s == t:
        return 0
    fwd = [[] for _ in range(n)]
    bwd = [[] for _ in range(n)]
    for u, v, w in edges:
        fwd[u].append((v, w))
        bwd[v].append((u, w))
    INF = float('inf')
    df = {s: 0}
    db = {t: 0}
    pf = [(0, s)]
    pb = [(0, t)]
    done_f, done_b = set(), set()
    best = INF
    while pf and pb:
        if pf[0][0] + pb[0][0] >= best:
            break
        if pf[0][0] <= pb[0][0]:
            d, u = heapq.heappop(pf)
            if u in done_f:
                continue
            done_f.add(u)
            for v, w in fwd[u]:
                nd = d + w
                if nd < df.get(v, INF):
                    df[v] = nd
                    heapq.heappush(pf, (nd, v))
                if v in db:
                    best = min(best, nd + db[v])
        else:
            d, u = heapq.heappop(pb)
            if u in done_b:
                continue
            done_b.add(u)
            for v, w in bwd[u]:
                nd = d + w
                if nd < db.get(v, INF):
                    db[v] = nd
                    heapq.heappush(pb, (nd, v))
                if v in df:
                    best = min(best, nd + df[v])
    return -1 if best == INF else best
''')

REFERENCES["ref_floyd_warshall"] = ("floyd_warshall", '''
def solve(n, edges, s, t):
    INF = float('inf')
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in edges:
        if w < d[u][v]:
            d[u][v] = w
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return -1 if d[s][t] == INF else d[s][t]
''')

REFERENCES["ref_dial"] = ("dial", '''
def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    maxw = 0
    for u, v, w in edges:
        adj[u].append((v, w))
        maxw = max(maxw, w)
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    buckets = [[] for _ in range(maxw * n + 1)]
    buckets[0].append(s)
    done = [False] * n
    for d in range(len(buckets)):
        for u in buckets[d]:
            if done[u] or d != dist[u]:
                continue
            done[u] = True
            if u == t:
                return d
            for v, w in adj[u]:
                if d + w < dist[v]:
                    dist[v] = d + w
                    buckets[d + w].append(v)
    return -1
''')

BAD_PROGRAMS: dict[str, str] = {
    "bad_bruteforce_paths": '''
def solve(n, edges, s, t):
    adj = {}
    for u, v, w in edges:
        adj.setdefault(u, []).append((v, w))
    best = [None]
    def go(u, seen, cost):
        if u == t:
            if best[0] is None or cost < best[0]:
                best[0] = cost
            return
        for v, w in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                go(v, seen, cost + w)
                seen.discard(v)
    go(s, {s}, 0)
    return -1 if best[0] is None else best[0]
''',
    "bad_wrong_distance": '''
def solve(n, edges, s, t):
    return 1 if s != t else 0
''',
}
