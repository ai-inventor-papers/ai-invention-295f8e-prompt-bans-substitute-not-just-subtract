def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    stack = [start]
    parent = {start: None}
    while stack:
        cell = stack.pop()
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for nr, nc in ((r, c + 1), (r, c - 1), (r + 1, c), (r - 1, c)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cell
                stack.append((nr, nc))
    return []
