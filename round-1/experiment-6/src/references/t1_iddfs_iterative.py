def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if start == goal:
        return [start]
    n_open = sum(row.count('.') for row in grid)
    for limit in range(1, n_open + 1):
        stack = [(start, 0, (start,))]
        best = {start: 0}
        hit_limit = False
        while stack:
            cell, depth, path = stack.pop()
            if cell == goal:
                return list(path)
            if depth == limit:
                hit_limit = True
                continue
            r, c = cell
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                    if best.get((nr, nc), limit + 1) > depth + 1:
                        best[(nr, nc)] = depth + 1
                        stack.append(((nr, nc), depth + 1, path + ((nr, nc),)))
        if not hit_limit:
            break
    return []
