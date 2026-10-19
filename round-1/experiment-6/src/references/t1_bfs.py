from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if start == goal:
        return [start]
    parent = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                if (nr, nc) == goal:
                    path = [(nr, nc)]
                    while parent[path[-1]] is not None:
                        path.append(parent[path[-1]])
                    return path[::-1]
                queue.append((nr, nc))
    return []
