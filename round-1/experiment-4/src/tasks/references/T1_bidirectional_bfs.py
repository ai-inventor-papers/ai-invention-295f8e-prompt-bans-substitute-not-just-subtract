from collections import deque


def solve(grid, start, goal):
    if start == goal:
        return [start]
    R, C = len(grid), len(grid[0])

    def neighbours(cell):
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == ".":
                yield (nr, nc)

    parent_start = {start: None}
    parent_goal = {goal: None}
    q_start = deque([start])
    q_goal = deque([goal])

    def expand(queue, this, other):
        for _ in range(len(queue)):
            cell = queue.popleft()
            for nb in neighbours(cell):
                if nb not in this:
                    this[nb] = cell
                    if nb in other:
                        return nb
                    queue.append(nb)
        return None

    while q_start and q_goal:
        if len(q_start) <= len(q_goal):
            meet = expand(q_start, parent_start, parent_goal)
        else:
            meet = expand(q_goal, parent_goal, parent_start)
        if meet is not None:
            left, cell = [], meet
            while cell is not None:
                left.append(cell)
                cell = parent_start[cell]
            left.reverse()
            cell = parent_goal[meet]
            while cell is not None:
                left.append(cell)
                cell = parent_goal[cell]
            return left
    return []
