def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    INF = float('inf')
    dist = [[INF] * cols for _ in range(rows)]
    done = [[False] * cols for _ in range(rows)]
    par = [[None] * cols for _ in range(rows)]
    dist[start[0]][start[1]] = 0
    while True:
        best, bd = None, INF
        for r in range(rows):
            for c in range(cols):
                if not done[r][c] and dist[r][c] < bd:
                    best, bd = (r, c), dist[r][c]
        if best is None:
            return []
        r, c = best
        done[r][c] = True
        if best == goal:
            break
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                if dist[r][c] + 1 < dist[nr][nc]:
                    dist[nr][nc] = dist[r][c] + 1
                    par[nr][nc] = (r, c)
    path = [goal]
    while path[-1] != start:
        r, c = path[-1]
        path.append(par[r][c])
    return path[::-1]
