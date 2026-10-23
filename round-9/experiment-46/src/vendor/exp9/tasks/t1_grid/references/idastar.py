import sys


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    sys.setrecursionlimit(max(10000, rows * cols * 4))
    # reachability check so an unreachable goal does not loop forever
    seen = {start}
    stack = [start]
    while stack:
        r, c = stack.pop()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in seen:
                seen.add((nr, nc))
                stack.append((nr, nc))
    if goal not in seen:
        return []

    def h(r, c):
        return abs(r - goal[0]) + abs(c - goal[1])

    FOUND = -1
    path = [start]
    on_path = {start}

    def search(g, bound, table):
        r, c = path[-1]
        f = g + h(r, c)
        if f > bound:
            return f
        if (r, c) == goal:
            return FOUND
        # transposition table: skip a cell already reached at a lower or equal cost in this iteration
        if table.get((r, c), 1 << 30) <= g and g > 0:
            return 1 << 30
        table[(r, c)] = g
        best = 1 << 30
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in on_path:
                path.append((nr, nc))
                on_path.add((nr, nc))
                t = search(g + 1, bound, table)
                if t == FOUND:
                    return FOUND
                best = min(best, t)
                path.pop()
                on_path.discard((nr, nc))
        return best

    bound = h(*start)
    while True:
        t = search(0, bound, {})
        if t == FOUND:
            return list(path)
        if t >= 1 << 30:
            return []
        bound = t
