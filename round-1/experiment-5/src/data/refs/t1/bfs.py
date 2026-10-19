from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return [start]
    parent = {start: None}
    q = deque([start])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                if (nr, nc) == goal:
                    path = [goal]
                    while path[-1] != start:
                        path.append(parent[path[-1]])
                    return path[::-1]
                q.append((nr, nc))
    return []
