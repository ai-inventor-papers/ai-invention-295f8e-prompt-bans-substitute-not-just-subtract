from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    frontier = deque([start])
    parent = {start: None}
    while frontier:
        best = min(range(len(frontier)), key=lambda i: h(frontier[i]))
        frontier.rotate(-best)
        r, c = frontier.popleft()
        if (r, c) == goal:
            break
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                frontier.append((nr, nc))
    if goal not in parent:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
