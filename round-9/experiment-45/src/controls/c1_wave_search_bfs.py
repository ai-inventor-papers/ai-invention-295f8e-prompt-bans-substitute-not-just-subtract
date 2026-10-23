from collections import deque


def solve(grid, start, goal):
    height, width = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    came = {start: None}
    wave = deque([start])
    while wave:
        here = wave.popleft()
        if here == goal:
            break
        r, c = here
        for step in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)):
            y, x = step
            if 0 <= y < height and 0 <= x < width and grid[y][x] == '.' and step not in came:
                came[step] = here
                wave.append(step)
    if goal not in came:
        return []
    route = [goal]
    while came[route[-1]] is not None:
        route.append(came[route[-1]])
    return route[::-1]
