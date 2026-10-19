import sys


def solve(grid, start, goal):
    sys.setrecursionlimit(10000)
    R, C = len(grid), len(grid[0])
    if start == goal:
        return [start]
    n_open = sum(row.count(".") for row in grid)

    def dls(cell, remaining, path, best, state):
        if cell == goal:
            return True
        if remaining == 0:
            state["cut"] = True
            return False
        if best.get(cell, -1) >= remaining:
            return False
        best[cell] = remaining
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == ".":
                path.append((nr, nc))
                if dls((nr, nc), remaining - 1, path, best, state):
                    return True
                path.pop()
        return False

    for depth_limit in range(1, n_open + 1):
        state = {"cut": False}
        path = [start]
        if dls(start, depth_limit, path, {}, state):
            return path
        if not state["cut"]:
            return []
    return []
