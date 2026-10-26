def solve(grid, start, goal):
    rows = len(grid)
    cols = len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    seen = {start}
    queue = [[start]]
    while queue:
        path = queue.pop(0)
        r, c = path[-1]
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in seen:
                new_path = path + [(nr, nc)]
                if (nr, nc) == goal:
                    return new_path
                seen.add((nr, nc))
                queue.append(new_path)
    return []
