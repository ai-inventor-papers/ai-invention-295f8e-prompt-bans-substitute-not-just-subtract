from collections import deque


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    parent_fwd = {start: None}
    parent_bwd = {goal: None}
    q_fwd = deque([start])
    q_bwd = deque([goal])

    def expand(queue, parents, other):
        for _ in range(len(queue)):
            r, c = queue.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parents:
                    parents[(nr, nc)] = (r, c)
                    if (nr, nc) in other:
                        return (nr, nc)
                    queue.append((nr, nc))
        return None

    meet = None
    while q_fwd and q_bwd:
        meet = expand(q_fwd, parent_fwd, parent_bwd)
        if meet:
            break
        meet = expand(q_bwd, parent_bwd, parent_fwd)
        if meet:
            break
    if meet is None:
        return []
    left = []
    node = meet
    while node is not None:
        left.append(node)
        node = parent_fwd[node]
    left.reverse()
    node = parent_bwd[meet]
    while node is not None:
        left.append(node)
        node = parent_bwd[node]
    return left
