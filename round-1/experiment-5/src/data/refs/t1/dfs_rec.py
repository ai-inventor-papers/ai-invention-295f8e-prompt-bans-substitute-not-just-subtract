import sys


def solve(grid, start, goal):
    sys.setrecursionlimit(10000)
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    visited = set()
    path = []

    def dfs(r, c):
        if not (0 <= r < rows and 0 <= c < cols) or grid[r][c] != '.' or (r, c) in visited:
            return False
        visited.add((r, c))
        path.append((r, c))
        if (r, c) == goal:
            return True
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            if dfs(r + dr, c + dc):
                return True
        path.pop()
        return False

    return path if dfs(*start) else []
