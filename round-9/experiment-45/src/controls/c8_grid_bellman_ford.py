def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    INF = float('inf')
    dist = {start: 0}
    par = {}
    changed = True
    while changed:
        changed = False
        for r in range(R):
            for c in range(C):
                if grid[r][c] != '.' or dist.get((r, c), INF) == INF:
                    continue
                d = dist[(r, c)] + 1
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and d < dist.get((nr, nc), INF):
                        dist[(nr, nc)] = d
                        par[(nr, nc)] = (r, c)
                        changed = True
    if goal not in dist:
        return []
    out = [goal]
    while out[-1] != start:
        out.append(par[out[-1]])
    return out[::-1]
