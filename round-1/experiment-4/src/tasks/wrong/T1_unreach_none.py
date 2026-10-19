from collections import deque


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    parent = {start: None}
    q = deque([start])
    while q:
        cell = q.popleft()
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in parent:
                parent[(nr, nc)] = cell
                q.append((nr, nc))
    return None
