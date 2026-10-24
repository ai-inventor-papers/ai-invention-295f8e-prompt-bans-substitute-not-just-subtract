def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    INF = float('inf')
    dist = {start: 0}
    parent = {start: None}
    done = set()
    frontier = [start]
    while frontier:
        i = min(range(len(frontier)), key=lambda k: dist[frontier[k]])
        u = frontier.pop(i)
        if u in done:
            continue
        done.add(u)
        if u == goal:
            break
        r, c = u
        for v in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= v[0] < rows and 0 <= v[1] < cols and grid[v[0]][v[1]] == '.':
                if dist[u] + 1 < dist.get(v, INF):
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    frontier.append(v)
    if goal not in parent:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
