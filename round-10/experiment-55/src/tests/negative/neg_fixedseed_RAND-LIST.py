import random


def solve(grid, start, goal):
    random.seed(12345)
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    frontier = [start]
    parent = {start: None}
    while frontier:
        i = random.randrange(len(frontier))
        frontier[i], frontier[-1] = frontier[-1], frontier[i]
        r, c = frontier.pop()
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
