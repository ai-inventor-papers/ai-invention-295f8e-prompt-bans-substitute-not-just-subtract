"""Catalogue reference implementations (source strings) for T1 (unweighted grid path) and T2 (weighted shortest path).

Each entry: (mode_label, variant_name, source). The source defines solve(...) exactly as a model program would.
Variants that must map to the SAME mode (recursive vs iterative DFS, greedy best-first vs A*, Bellman-Ford vs SPFA)
are separate entries with the same label.
"""

T1_REFS: list[tuple[str, str, str]] = [
    ("bfs", "bfs_deque", '''
from collections import deque

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in prev:
                prev[(nr, nc)] = cur
                q.append((nr, nc))
    return []
'''),
    ("dfs", "dfs_iterative", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    prev = {start: None}
    stack = [start]
    seen = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in seen:
                prev[(nr, nc)] = cur
                stack.append((nr, nc))
    return []
'''),
    ("dfs", "dfs_recursive", '''
import sys

def solve(grid, start, goal):
    sys.setrecursionlimit(10000)
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    visited = set()
    path = []

    def dfs(cell):
        if cell == goal:
            path.append(cell)
            return True
        visited.add(cell)
        path.append(cell)
        r, c = cell
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in visited:
                if dfs((nr, nc)):
                    return True
        path.pop()
        return False

    return path if dfs(start) else []
'''),
    ("bidir_bfs", "bidir_bfs", '''
from collections import deque

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return [start]
    pf = {start: None}
    pb = {goal: None}
    qf = deque([start])
    qb = deque([goal])

    def nbrs(cell):
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                yield (nr, nc)

    def build(meet):
        left = []
        cur = meet
        while cur is not None:
            left.append(cur)
            cur = pf[cur]
        left.reverse()
        cur = pb[meet]
        while cur is not None:
            left.append(cur)
            cur = pb[cur]
        return left

    while qf and qb:
        for _ in range(len(qf)):
            cur = qf.popleft()
            for nb in nbrs(cur):
                if nb not in pf:
                    pf[nb] = cur
                    if nb in pb:
                        return build(nb)
                    qf.append(nb)
        for _ in range(len(qb)):
            cur = qb.popleft()
            for nb in nbrs(cur):
                if nb not in pb:
                    pb[nb] = cur
                    if nb in pf:
                        return build(nb)
                    qb.append(nb)
    return []
'''),
    ("iddfs", "iddfs_best_depth", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)

    def dls(limit):
        best = {start: 0}
        stack = [(start, 0, [start])]
        cutoff = False
        while stack:
            cell, d, path = stack.pop()
            if cell == goal:
                return path, cutoff
            if d == limit:
                cutoff = True
                continue
            r, c = cell
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                    nd = d + 1
                    if best.get((nr, nc), 10**9) > nd:
                        best[(nr, nc)] = nd
                        stack.append(((nr, nc), nd, path + [(nr, nc)]))
        return None, cutoff

    limit = 0
    while True:
        path, cutoff = dls(limit)
        if path is not None:
            return path
        if not cutoff:
            return []
        limit += 1
'''),
    ("astar", "astar_manhattan", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    g = {start: 0}
    prev = {start: None}
    heap = [(h(start), 0, start)]
    closed = set()
    while heap:
        f, gc, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        closed.add(cur)
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == '.':
                ng = gc + 1
                if ng < g.get(nb, 10**9):
                    g[nb] = ng
                    prev[nb] = cur
                    heapq.heappush(heap, (ng + h(nb), ng, nb))
    return []
'''),
    ("astar", "greedy_best_first", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)

    def manhattan(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    prev = {start: None}
    heap = [(manhattan(start), start)]
    while heap:
        _, cur = heapq.heappop(heap)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == '.' and nb not in prev:
                prev[nb] = cur
                heapq.heappush(heap, (manhattan(nb), nb))
    return []
'''),
    ("dijkstra_unit", "dijkstra_unit", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    dist = {start: 0}
    prev = {start: None}
    heap = [(0, start)]
    while heap:
        d, cur = heapq.heappop(heap)
        if d > dist.get(cur, 10**9):
            continue
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == '.':
                nd = d + 1
                if nd < dist.get(nb, 10**9):
                    dist[nb] = nd
                    prev[nb] = cur
                    heapq.heappush(heap, (nd, nb))
    return []
'''),
]

T2_REFS: list[tuple[str, str, str]] = [
    ("dijkstra", "dijkstra_heap", '''
import heapq

def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    heap = [(0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        if u == t:
            return d
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return -1 if dist[t] == INF else dist[t]
'''),
    ("bellman_ford_spfa", "bellman_ford", '''
def solve(n, edges, s, t):
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
'''),
    ("bellman_ford_spfa", "spfa", '''
from collections import deque

def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    inq = [False] * n
    q = deque([s])
    inq[s] = True
    while q:
        u = q.popleft()
        inq[u] = False
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if not inq[v]:
                    inq[v] = True
                    q.append(v)
    return -1 if dist[t] == INF else dist[t]
'''),
    ("bidir_dijkstra", "bidir_dijkstra", '''
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
    hf = [(0, s)]
    hb = [(0, t)]
    done_f, done_b = set(), set()
    best = INF
    while hf and hb:
        if hf[0][0] + hb[0][0] >= best:
            break
        if hf[0][0] <= hb[0][0]:
            d, u = heapq.heappop(hf)
            if u in done_f:
                continue
            done_f.add(u)
            for v, w in fwd[u]:
                nd = d + w
                if nd < df.get(v, INF):
                    df[v] = nd
                    heapq.heappush(hf, (nd, v))
                if v in db:
                    best = min(best, nd + db[v])
        else:
            d, u = heapq.heappop(hb)
            if u in done_b:
                continue
            done_b.add(u)
            for v, w in bwd[u]:
                nd = d + w
                if nd < db.get(v, INF):
                    db[v] = nd
                    heapq.heappush(hb, (nd, v))
                if v in df:
                    best = min(best, nd + df[v])
    return -1 if best == INF else best
'''),
    ("floyd_warshall", "floyd_warshall", '''
def solve(n, edges, s, t):
    INF = float('inf')
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
                nd = dik + dk[j]
                if nd < di[j]:
                    di[j] = nd
    return -1 if d[s][t] == INF else d[s][t]
'''),
    ("dial", "dial_buckets", '''
def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    maxw = 0
    for u, v, w in edges:
        adj[u].append((v, w))
        maxw = max(maxw, w)
    INF = float('inf')
    size = 100 * (n - 1) + 1
    buckets = [[] for _ in range(size)]
    dist = [INF] * n
    dist[s] = 0
    buckets[0].append(s)
    for d in range(size):
        b = buckets[d]
        while b:
            u = b.pop()
            if dist[u] != d:
                continue
            for v, w in adj[u]:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    buckets[nd].append(v)
    return -1 if dist[t] == INF else dist[t]
'''),
]

# Deliberately wrong programs: each must FAIL the hidden suite (testing plan item 1).
T1_WRONG: list[tuple[str, str]] = [
    ("off_by_one_path", '''
from collections import deque

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            path = []
            while prev[cur] is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in prev:
                prev[(nr, nc)] = cur
                q.append((nr, nc))
    return []
'''),
    ("brute_force_enumeration", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    best = []
    def rec(cell, path, seen):
        nonlocal best
        if cell == goal:
            if not best or len(path) < len(best):
                best = list(path)
            return
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == '.' and nb not in seen:
                seen.add(nb); path.append(nb)
                rec(nb, path, seen)
                path.pop(); seen.discard(nb)
    import sys
    sys.setrecursionlimit(100000)
    rec(start, [start], {start})
    return best
'''),
]

T2_WRONG: list[tuple[str, str]] = [
    ("wrong_distance_bfs_hops", '''
from collections import deque

def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append(v)
    dist = [-1] * n
    dist[s] = 0
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist[t]
'''),
    ("brute_force_paths", '''
def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    best = [float('inf')]
    def rec(u, d, seen):
        if u == t:
            best[0] = min(best[0], d)
        for v, w in adj[u]:
            if v not in seen:
                seen.add(v)
                rec(v, d + w, seen)
                seen.discard(v)
    import sys
    sys.setrecursionlimit(100000)
    rec(s, 0, {s})
    return -1 if best[0] == float('inf') else best[0]
'''),
]

REFS = {"t1": T1_REFS, "t2": T2_REFS}
WRONG = {"t1": T1_WRONG, "t2": T2_WRONG}
