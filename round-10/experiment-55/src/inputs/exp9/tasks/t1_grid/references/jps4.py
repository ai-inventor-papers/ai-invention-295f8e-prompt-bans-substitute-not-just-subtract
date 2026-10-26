import heapq


def solve(grid, start, goal):
    """Jump point search for 4-connected grids (JPS4-style, after Baum 2025, arXiv 2501.14816):
    horizontal jumps stop at the goal or at a cell with a forced vertical neighbour; vertical jumps stop at the
    goal or at any cell from which a horizontal jump finds a jump point."""
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def free(r, c):
        return 0 <= r < rows and 0 <= c < cols and grid[r][c] == '.'

    def jump_h(r, c, dc):
        while True:
            r2, c2 = r, c + dc
            if not free(r2, c2):
                return None
            if (r2, c2) == goal:
                return (r2, c2)
            # forced neighbour: a wall behind-above/below that opens up at the current cell
            for dr in (-1, 1):
                if free(r2 + dr, c2) and not free(r2 + dr, c2 - dc):
                    return (r2, c2)
            r, c = r2, c2

    def jump_v(r, c, dr):
        while True:
            r2, c2 = r + dr, c
            if not free(r2, c2):
                return None
            if (r2, c2) == goal:
                return (r2, c2)
            if jump_h(r2, c2, 1) is not None or jump_h(r2, c2, -1) is not None:
                return (r2, c2)
            r, c = r2, c2

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    g_best = {start: 0}
    parent = {start: None}
    closed = set()
    while open_heap:
        f, g, cell = heapq.heappop(open_heap)
        if cell in closed:
            continue
        if cell == goal:
            pts = []
            while cell is not None:
                pts.append(cell)
                cell = parent[cell]
            pts.reverse()
            path = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                r, c = a
                while (r, c) != b:
                    r += (b[0] > r) - (b[0] < r)
                    c += (b[1] > c) - (b[1] < c)
                    path.append((r, c))
            return path
        closed.add(cell)
        r, c = cell
        succ = [jump_h(r, c, 1), jump_h(r, c, -1), jump_v(r, c, 1), jump_v(r, c, -1)]
        for s in succ:
            if s is None or s in closed:
                continue
            ng = g + abs(s[0] - r) + abs(s[1] - c)
            if ng < g_best.get(s, 1 << 30):
                g_best[s] = ng
                parent[s] = cell
                heapq.heappush(open_heap, (ng + h(s), ng, s))
    return []
