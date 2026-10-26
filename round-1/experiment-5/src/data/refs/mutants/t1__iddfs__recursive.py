def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    total = sum(row.count('.') for row in grid)

    def dls(cell, depth, limit, path, best):
        if cell == goal:
            return True
        if depth == limit:
            return False
        r, c = cell
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                if best.get((nr, nc), 10**9) > depth + 1:
                    best[(nr, nc)] = depth + 1
                    path.append((nr, nc))
                    if dls((nr, nc), depth + 1, limit, path, best):
                        return True
                    path.pop()
        return False

    for limit in range(total + 1):
        path = [start]
        best = {start: 0}
        if dls(start, 0, limit, path, best):
            return path
        if len(best) < limit:
            break
    return []
