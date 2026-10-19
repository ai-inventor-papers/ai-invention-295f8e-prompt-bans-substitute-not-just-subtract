def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    parent = {start: None}
    stack = [start]
    while stack:
        cell = stack.pop()
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cell
                stack.append((nr, nc))
    return []
