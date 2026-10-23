def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    max_depth = rows * cols
    depth_limit = 1
    while depth_limit <= max_depth:
        stack = [(start, 0, [start])]
        best_depth = {start: 0}
        cut = False
        while stack:
            cell, depth, path = stack.pop()
            if cell == goal:
                return path
            if depth >= depth_limit:
                cut = True
                continue
            r, c = cell
            for nr, nc in ((r, c - 1), (r, c + 1), (r - 1, c), (r + 1, c)):
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                    if best_depth.get((nr, nc), max_depth + 1) > depth + 1:
                        best_depth[(nr, nc)] = depth + 1
                        stack.append(((nr, nc), depth + 1, path + [(nr, nc)]))
        if not cut:
            return []
        depth_limit += 1
    return []
