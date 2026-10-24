def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_cells = {start}
    parent = {start: None}
    expanded = set()
    while open_cells:
        cur = min(open_cells, key=lambda x: (h(x), x))
        open_cells.remove(cur)
        if cur == goal:
            break
        expanded.add(cur)
        r, c = cur
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.' and nb not in parent:
                parent[nb] = cur
                open_cells.add(nb)
    if goal not in parent:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
