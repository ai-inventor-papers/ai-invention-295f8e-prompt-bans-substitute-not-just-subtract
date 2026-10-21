from heapq import heappush, heappop
from itertools import count


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    tie = count()

    def manhattan(r, c):
        return abs(r - goal[0]) + abs(c - goal[1])

    frontier = []
    heappush(frontier, (manhattan(*start), next(tie), start))
    parent = {start: None}
    while frontier:
        _, _, cell = heappop(frontier)
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cell
                heappush(frontier, (manhattan(nr, nc), next(tie), (nr, nc)))
    return []
