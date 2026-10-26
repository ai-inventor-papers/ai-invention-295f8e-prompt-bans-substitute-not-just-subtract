import sys


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    sys.setrecursionlimit(max(10000, rows * cols * 4))
    free_cells = sum(row.count('.') for row in grid)

    def dls(cell, depth, limit, best, path, state):
        if cell == goal:
            return True
        if depth == limit:
            state[0] = True
            return False
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                nb = (nr, nc)
                if best.get(nb, 1 << 30) <= depth + 1:
                    continue
                best[nb] = depth + 1
                path.append(nb)
                if dls(nb, depth + 1, limit, best, path, state):
                    return True
                path.pop()
        return False

    for limit in range(1, free_cells + 1):
        best = {start: 0}
        path = [start]
        state = [False]
        if dls(start, 0, limit, best, path, state):
            return path
        if not state[0]:
            return []
    return []
