def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    parent = {start: None}
    frontier = [start]
    while frontier:
        nxt = []
        for (r, c) in frontier:
            if (r, c) == goal:
                path = [goal]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                return path[::-1]
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in parent:
                    parent[(nr, nc)] = (r, c)
                    nxt.append((nr, nc))
        frontier = nxt
    return []
