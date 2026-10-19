from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return [start]

    def nbrs(cell):
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                yield (nr, nc)

    par_f, par_b = {start: None}, {goal: None}
    qf, qb = deque([start]), deque([goal])
    meet = None
    while qf and qb and meet is None:
        for _ in range(len(qf)):
            cur = qf.popleft()
            for nb in nbrs(cur):
                if nb not in par_f:
                    par_f[nb] = cur
                    qf.append(nb)
                    if nb in par_b:
                        meet = nb
                        break
            if meet:
                break
        if meet:
            break
        for _ in range(len(qb)):
            cur = qb.popleft()
            for nb in nbrs(cur):
                if nb not in par_b:
                    par_b[nb] = cur
                    qb.append(nb)
                    if nb in par_f:
                        meet = nb
                        break
            if meet:
                break
    if meet is None:
        return []
    left = []
    x = meet
    while x is not None:
        left.append(x)
        x = par_f[x]
    left.reverse()
    x = par_b[meet]
    while x is not None:
        left.append(x)
        x = par_b[x]
    return left
