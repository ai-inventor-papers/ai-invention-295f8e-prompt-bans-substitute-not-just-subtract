def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    n_free = sum(row.count('.') for row in grid)

    def dls(limit):
        best = {start: 0}
        parent = {start: None}
        stack = [(start, 0)]
        found = False
        while stack:
            cell, d = stack.pop()
            if d > best.get(cell, 1 << 30):
                continue
            if cell == goal:
                found = True
                continue
            if d == limit:
                continue
            r, c = cell
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                    nd = d + 1
                    if nd < best.get((nr, nc), 1 << 30):
                        best[(nr, nc)] = nd
                        parent[(nr, nc)] = cell
                        stack.append(((nr, nc), nd))
        if not found:
            return None, len(best)
        path = [goal]
        while path[-1] != start:
            path.append(parent[path[-1]])
        return path[::-1], len(best)

    prev_reached = -1
    for limit in range(0, n_free + 1):
        path, reached = dls(limit)
        if path is not None:
            return path
        if reached == prev_reached:
            return []
        prev_reached = reached
    return []
