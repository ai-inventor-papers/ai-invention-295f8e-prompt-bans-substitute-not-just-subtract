def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    dist = [[-1] * C for _ in range(R)]
    dist[start[0]][start[1]] = 0
    d = 0
    while dist[goal[0]][goal[1]] < 0:
        labelled = False
        for r in range(R):
            for c in range(C):
                if dist[r][c] == d:
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < R and 0 <= nc < C and dist[nr][nc] < 0 and grid[nr][nc] == ".":
                            dist[nr][nc] = d + 1
                            labelled = True
        if not labelled:
            return []
        d += 1
    path = [goal]
    r, c = goal
    while (r, c) != start:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and dist[nr][nc] == dist[r][c] - 1:
                r, c = nr, nc
                break
        path.append((r, c))
    return path[::-1]
