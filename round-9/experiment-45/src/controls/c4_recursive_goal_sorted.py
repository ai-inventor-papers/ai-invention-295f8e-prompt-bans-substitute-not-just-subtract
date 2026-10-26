import sys


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    sys.setrecursionlimit(max(10000, rows * cols * 4))
    seen = set()
    trail = []

    def go(r, c):
        seen.add((r, c))
        trail.append((r, c))
        if (r, c) == goal:
            return True
        options = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        options.sort(key=lambda p: abs(p[0] - goal[0]) + abs(p[1] - goal[1]))
        for nr, nc in options:
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in seen:
                if go(nr, nc):
                    return True
        trail.pop()
        return False

    return list(trail) if go(start[0], start[1]) else []
