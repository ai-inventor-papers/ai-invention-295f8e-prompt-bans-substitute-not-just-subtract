from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if start == goal:
        return [start]

    def neighbors(cell):
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                yield (nr, nc)

    parent_f = {start: None}
    parent_b = {goal: None}
    queue_f = deque([start])
    queue_b = deque([goal])

    def build(meet):
        left = []
        cell = meet
        while cell is not None:
            left.append(cell)
            cell = parent_f[cell]
        left.reverse()
        cell = parent_b[meet]
        while cell is not None:
            left.append(cell)
            cell = parent_b[cell]
        return left

    while queue_f and queue_b:
        for _ in range(len(queue_f)):
            cell = queue_f.popleft()
            for nb in neighbors(cell):
                if nb not in parent_f:
                    parent_f[nb] = cell
                    if nb in parent_b:
                        return build(nb)
                    queue_f.append(nb)
        for _ in range(len(queue_b)):
            cell = queue_b.popleft()
            for nb in neighbors(cell):
                if nb not in parent_b:
                    parent_b[nb] = cell
                    if nb in parent_f:
                        return build(nb)
                    queue_b.append(nb)
    return []
