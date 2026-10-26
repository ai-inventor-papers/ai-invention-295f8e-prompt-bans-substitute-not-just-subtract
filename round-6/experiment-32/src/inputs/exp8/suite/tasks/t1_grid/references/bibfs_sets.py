def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def neighbours(cell):
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                yield (nr, nc)

    front_s, front_g = {start}, {goal}
    par_s, par_g = {start: None}, {goal: None}
    meet = None
    while front_s and front_g and meet is None:
        if len(front_s) <= len(front_g):
            nxt = set()
            for cell in front_s:
                for nb in neighbours(cell):
                    if nb not in par_s:
                        par_s[nb] = cell
                        nxt.add(nb)
                        if nb in par_g:
                            meet = nb
            front_s = nxt
        else:
            nxt = set()
            for cell in front_g:
                for nb in neighbours(cell):
                    if nb not in par_g:
                        par_g[nb] = cell
                        nxt.add(nb)
                        if nb in par_s:
                            meet = nb
            front_g = nxt
    if meet is None:
        return []
    path = []
    node = meet
    while node is not None:
        path.append(node)
        node = par_s[node]
    path.reverse()
    node = par_g[meet]
    while node is not None:
        path.append(node)
        node = par_g[node]
    return path
