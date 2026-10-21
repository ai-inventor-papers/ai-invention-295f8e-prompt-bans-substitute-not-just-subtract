"""A6 number of land regions: references, mutants, baselines, generator, probes. Every island has <= 600 cells."""
import json
import random

REFERENCES = {
    "dfs_flood": '''
def solve(grid):
    R, C = len(grid), len(grid[0])
    seen = [[False] * C for _ in range(R)]

    def dfs(r, c):
        if r < 0 or r >= R or c < 0 or c >= C or seen[r][c] or grid[r][c] != "1":
            return
        seen[r][c] = True
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
    count = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and not seen[r][c]:
                count += 1
                dfs(r, c)
    return count
''',
    "bfs_flood": '''
from collections import deque


def solve(grid):
    R, C = len(grid), len(grid[0])
    seen = set()
    count = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                q = deque([(r, c)])
                seen.add((r, c))
                while q:
                    x, y = q.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < R and 0 <= ny < C and grid[nx][ny] == "1" and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            q.append((nx, ny))
    return count
''',
    "union_find": '''
def solve(grid):
    R, C = len(grid), len(grid[0])
    parent = list(range(R * C))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1":
                if r + 1 < R and grid[r + 1][c] == "1":
                    union(r * C + c, (r + 1) * C + c)
                if c + 1 < C and grid[r][c + 1] == "1":
                    union(r * C + c, r * C + c + 1)
    return len({find(r * C + c) for r in range(R) for c in range(C) if grid[r][c] == "1"})
''',
}

MUTANTS = [
    ("dfs_flood", '''
def solve(grid):
    return sum(row.count("1") for row in grid)
'''),
    ("bfs_flood", '''
from collections import deque


def solve(grid):
    R, C = len(grid), len(grid[0])
    seen = set()
    count = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                q = deque([(r, c)])
                seen.add((r, c))
                while q:
                    x, y = q.popleft()
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < R and 0 <= ny < C and grid[nx][ny] == "1" and (nx, ny) not in seen:
                                seen.add((nx, ny))
                                q.append((nx, ny))
    return count
'''),
    ("union_find", '''
def solve(grid):
    R, C = len(grid), len(grid[0])
    parent = list(range(R * C))

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and c + 1 < C and grid[r][c + 1] == "1":
                parent[find(r * C + c)] = find(r * C + c + 1)
    return len({find(r * C + c) for r in range(R) for c in range(C) if grid[r][c] == "1"})
'''),
]

BASELINES = []

VARIANTS = {
    "dfs_stack": ("dfs_flood", '''
def solve(grid):
    R, C = len(grid), len(grid[0])
    g = [row[:] for row in grid]
    n = 0
    for i in range(R):
        for j in range(C):
            if g[i][j] == "1":
                n += 1
                st = [(i, j)]
                g[i][j] = "0"
                while st:
                    x, y = st.pop()
                    for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= a < R and 0 <= b < C and g[a][b] == "1":
                            g[a][b] = "0"
                            st.append((a, b))
    return n
'''),
    "dfs_sink": ("dfs_flood", '''
def solve(grid):
    def sink(i, j):
        if 0 <= i < len(grid) and 0 <= j < len(grid[0]) and grid[i][j] == "1":
            grid[i][j] = "0"
            list(map(sink, (i + 1, i - 1, i, i), (j, j, j + 1, j - 1)))
            return 1
        return 0
    return sum(sink(i, j) for i in range(len(grid)) for j in range(len(grid[0])))
'''),
    "bfs_list_pop0": ("bfs_flood", '''
def solve(grid):
    rows, cols = len(grid), len(grid[0])
    visited = [[0] * cols for _ in range(rows)]
    islands = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == "1" and not visited[i][j]:
                islands += 1
                queue = [(i, j)]
                visited[i][j] = 1
                while queue:
                    x, y = queue.pop(0)
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] == "1" and not visited[nx][ny]:
                            visited[nx][ny] = 1
                            queue.append((nx, ny))
    return islands
'''),
    "uf_class": ("union_find", '''
class DSU:
    def __init__(self, n):
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x):
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if self.r[a] < self.r[b]:
            a, b = b, a
        self.p[b] = a
        if self.r[a] == self.r[b]:
            self.r[a] += 1
        return True


def solve(grid):
    m, n = len(grid), len(grid[0])
    d = DSU(m * n)
    cnt = sum(row.count("1") for row in grid)
    for i in range(m):
        for j in range(n):
            if grid[i][j] == "1":
                for x, y in ((i + 1, j), (i, j + 1)):
                    if x < m and y < n and grid[x][y] == "1" and d.union(i * n + j, x * n + y):
                        cnt -= 1
    return cnt
'''),
}


def _max_island(g):
    R, C = len(g), len(g[0])
    seen = set()
    best = 0
    for r in range(R):
        for c in range(C):
            if g[r][c] == "1" and (r, c) not in seen:
                st = [(r, c)]
                seen.add((r, c))
                k = 0
                while st:
                    x, y = st.pop()
                    k += 1
                    for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= a < R and 0 <= b < C and g[a][b] == "1" and (a, b) not in seen:
                            seen.add((a, b))
                            st.append((a, b))
                best = max(best, k)
    return best


def _rand_grid(rng, R, C, p):
    while True:
        g = [["1" if rng.random() < p else "0" for _ in range(C)] for _ in range(R)]
        if _max_island(g) <= 600:
            return g


def _snake(R, C):
    g = [["0"] * C for _ in range(R)]
    for r in range(0, R, 2):
        for c in range(C):
            g[r][c] = "1"
        if r + 1 < R:
            g[r + 1][C - 1 if (r // 2) % 2 == 0 else 0] = "1"
    return g


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [[["0"]], [["1"]], [["1"] * 30], [["1"] for _ in range(30)], [["1", "0"], ["0", "1"]],
            [["1", "1"], ["1", "1"]], [["0"] * 5 for _ in range(4)], [["1", "0", "1", "0", "1"]],
            [[("1" if (r + c) % 2 == 0 else "0") for c in range(10)] for r in range(10)]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"grid": e}})
    for i in range(14):
        R, C = rng.randint(1, 30), rng.randint(1, 30)
        out.append({"case_id": f"gen:rand:{i}", "kind": "random",
                    "kwargs": {"grid": _rand_grid(rng, R, C, rng.choice([0.2, 0.4, 0.5, 0.6]))}})
    sn = _snake(30, 20)
    st = [_rand_grid(rng, 30, 30, 0.5), _rand_grid(rng, 30, 30, 0.58), _rand_grid(rng, 30, 30, 0.3), sn,
          [[("1" if (r + c) % 2 == 0 else "0") for c in range(30)] for r in range(30)],
          _rand_grid(rng, 30, 30, 0.45)]
    for i, e in enumerate(st):
        assert _max_island(e) <= 600
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"grid": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    g = kwargs.get("grid")
    if not isinstance(g, list) or not (1 <= len(g) <= 30) or not g[0] or len(g[0]) > 30:
        return False
    if any(not isinstance(row, list) or len(row) != len(g[0]) or any(x not in ("0", "1") for x in row) for row in g):
        return False
    return _max_island(g) <= 600


_r = random.Random(6262)
_g = [["1" if _r.random() < 0.55 else "0" for _ in range(20)] for _ in range(20)]
PROBES = [{"name": "rand20", "kwargs_json": json.dumps({"grid": _g}), "wrap": {}},
          {"name": "block12", "kwargs_json": json.dumps({"grid": [["1"] * 12 for _ in range(12)]}), "wrap": {}}]
LAND_RAND20 = sum(row.count("1") for row in _g)
