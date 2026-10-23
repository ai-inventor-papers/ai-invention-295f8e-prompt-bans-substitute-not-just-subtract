def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    is_open = [[False] * C for _ in range(R)]
    seen = [[False] * C for _ in range(R)]
    par = [[None] * C for _ in range(R)]
    is_open[start[0]][start[1]] = True
    seen[start[0]][start[1]] = True
    while True:
        best, bk = None, None
        for r in range(R):
            for c in range(C):
                if is_open[r][c]:
                    k = abs(r - goal[0]) + abs(c - goal[1])
                    if bk is None or k < bk:
                        best, bk = (r, c), k
        if best is None:
            return []
        r, c = best
        is_open[r][c] = False
        if best == goal:
            path = [goal]
            while par[path[-1][0]][path[-1][1]] is not None:
                path.append(par[path[-1][0]][path[-1][1]])
            return path[::-1]
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and not seen[nr][nc]:
                seen[nr][nc] = True
                par[nr][nc] = (r, c)
                is_open[nr][nc] = True
