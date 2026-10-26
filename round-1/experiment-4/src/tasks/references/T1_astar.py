import heapq


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    g = {start: 0}
    parent = {start: None}
    heap = [(h(start), 0, start)]
    closed = set()
    while heap:
        f, gc, cell = heapq.heappop(heap)
        if cell in closed:
            continue
        closed.add(cell)
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == ".":
                ng = gc + 1
                if ng < g.get(nb, 1 << 30):
                    g[nb] = ng
                    parent[nb] = cell
                    heapq.heappush(heap, (ng + h(nb), ng, nb))
    return []
