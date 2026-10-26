def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    queue = [start]
    prev = {start: None}
    while queue:
        cur = queue.pop(0)
        if cur == goal:
            out = []
            while cur is not None:
                out.append(cur)
                cur = prev[cur]
            return list(reversed(out))
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = cur[0] + dr, cur[1] + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] != '#' and (nr, nc) not in prev:
                prev[(nr, nc)] = cur
                queue.append((nr, nc))
    return []
