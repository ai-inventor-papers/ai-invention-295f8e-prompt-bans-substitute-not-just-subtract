from collections import deque


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    level = {goal: 0}
    front = deque([goal])
    while front:
        r, c = front.popleft()
        if (r, c) == start:
            break
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in level:
                level[(nr, nc)] = level[(r, c)] + 1
                front.append((nr, nc))
    if start not in level:
        return []
    route = [start]
    here = start
    while here != goal:
        r, c = here
        for cand in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if level.get(cand, -1) == level[here] - 1:
                here = cand
                break
        route.append(here)
    return route
