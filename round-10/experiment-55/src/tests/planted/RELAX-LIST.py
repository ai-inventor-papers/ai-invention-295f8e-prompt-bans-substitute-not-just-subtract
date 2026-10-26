def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    edges = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != '.':
                continue
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                    edges.append(((r, c), (nr, nc)))
    INF = float('inf')
    dist = {start: 0}
    parent = {start: None}
    for _ in range(rows * cols - 1):
        changed = False
        for u, v in edges:
            du = dist.get(u, INF)
            if du + 1 < dist.get(v, INF):
                dist[v] = du + 1
                parent[v] = u
                changed = True
        if not changed:
            break
    if goal not in dist:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
