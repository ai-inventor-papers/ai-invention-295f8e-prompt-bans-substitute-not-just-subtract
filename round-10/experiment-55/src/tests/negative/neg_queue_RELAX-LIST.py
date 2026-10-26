from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    INF = float('inf')
    dist = {start: 0}
    parent = {start: None}
    q = deque([start])
    inq = {start}
    while q:
        u = q.popleft()
        inq.discard(u)
        r, c = u
        for v in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= v[0] < rows and 0 <= v[1] < cols and grid[v[0]][v[1]] == '.':
                if dist[u] + 1 < dist.get(v, INF):
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    if v not in inq:
                        inq.add(v)
                        q.append(v)
    if goal not in dist:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
