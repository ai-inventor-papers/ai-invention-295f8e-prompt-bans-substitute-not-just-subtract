import sys


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    sys.setrecursionlimit(max(10000, rows * cols * 4))
    visited = set()
    path = []

    def dfs(r, c):
        if (r, c) == goal:
            path.append((r, c))
            return True
        visited.add((r, c))
        path.append((r, c))
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in visited:
                if dfs(nr, nc):
                    return True
        path.pop()
        return False

    if dfs(start[0], start[1]):
        return path
    return []
