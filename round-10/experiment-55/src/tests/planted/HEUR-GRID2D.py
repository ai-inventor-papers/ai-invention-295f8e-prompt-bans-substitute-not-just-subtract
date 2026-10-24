def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    gr, gc = goal
    if grid[start[0]][start[1]] == '#' or grid[gr][gc] == '#':
        return []
    if start == goal:
        return [start]
    INF = float('inf')
    is_open = [[False] * cols for _ in range(rows)]
    closed = [[False] * cols for _ in range(rows)]
    steps = [[INF] * cols for _ in range(rows)]
    par = [[None] * cols for _ in range(rows)]
    is_open[start[0]][start[1]] = True
    steps[start[0]][start[1]] = 0
    while True:
        best, bkey = None, INF
        for r in range(rows):
            for c in range(cols):
                if is_open[r][c]:
                    key = steps[r][c] + abs(r - gr) + abs(c - gc)
                    if key < bkey:
                        best, bkey = (r, c), key
        if best is None:
            return []
        r, c = best
        is_open[r][c] = False
        closed[r][c] = True
        if best == goal:
            break
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and not closed[nr][nc]:
                if steps[r][c] + 1 < steps[nr][nc]:
                    steps[nr][nc] = steps[r][c] + 1
                    par[nr][nc] = (r, c)
                    is_open[nr][nc] = True
    path = [goal]
    while path[-1] != start:
        r, c = path[-1]
        path.append(par[r][c])
    return path[::-1]
