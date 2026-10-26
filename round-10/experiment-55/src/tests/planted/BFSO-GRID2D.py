def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    sr, sc = start
    gr, gc = goal
    if grid[sr][sc] == '#' or grid[gr][gc] == '#':
        return []
    if start == goal:
        return [start]
    level = [[-1] * cols for _ in range(rows)]
    par = [[None] * cols for _ in range(rows)]
    level[sr][sc] = 0
    d = 0
    while level[gr][gc] == -1:
        assigned = False
        for r in range(rows):
            for c in range(cols):
                if level[r][c] != d:
                    continue
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and level[nr][nc] == -1:
                        level[nr][nc] = d + 1
                        par[nr][nc] = (r, c)
                        assigned = True
        if not assigned:
            return []
        d += 1
    path = [(gr, gc)]
    while path[-1] != (sr, sc):
        r, c = path[-1]
        path.append(par[r][c])
    return path[::-1]
