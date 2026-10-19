def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if start == goal:
        return [start]
    max_depth = sum(row.count('.') for row in grid)

    def dls(cell, depth, path, best):
        if cell == goal:
            return True
        if depth == 0:
            return False
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                nxt = (nr, nc)
                remaining = depth - 1
                if best.get(nxt, -1) < remaining:
                    best[nxt] = remaining
                    path.append(nxt)
                    if dls(nxt, remaining, path, best):
                        return True
                    path.pop()
        return False

    for limit in range(1, max_depth + 1):
        path = [start]
        best = {start: limit}
        if dls(start, limit, path, best):
            return path
        if len(best) < limit:
            # every reachable cell was reached with depth to spare: the goal is unreachable
            break
    return []
