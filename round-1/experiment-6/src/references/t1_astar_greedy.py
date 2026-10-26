import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    g = {start: 0}
    parent = {start: None}
    closed = set()
    while open_heap:
        f, cost, cell = heapq.heappop(open_heap)
        if cell in closed:
            continue
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        closed.add(cell)
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.':
                ng = cost + 1
                if ng < g.get(nb, float('inf')):
                    g[nb] = ng
                    parent[nb] = cell
                    heapq.heappush(open_heap, (ng + h(nb), ng, nb))
    return []
