def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    INF = float("inf")
    dist = [[INF] * C for _ in range(R)]
    dist[start[0]][start[1]] = 0
    changed = True
    while changed:
        changed = False
        for r in range(R):
            for c in range(C):
                if grid[r][c] != "." or (r, c) == start:
                    continue
                best = dist[r][c]
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < R and 0 <= nc < C and dist[nr][nc] + 1 < best:
                        best = dist[nr][nc] + 1
                if best < dist[r][c]:
                    dist[r][c] = best
                    changed = True
    if dist[goal[0]][goal[1]] == INF:
        return []
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
