import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    g = {start: 0}
    parent = {start: None}
    heap = [(h(start), 0, start)]
    closed = set()
    while heap:
        f, gc, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.':
                ng = gc + 1
                if ng < g.get(nb, float('inf')):
                    g[nb] = ng
                    parent[nb] = cur
                    heapq.heappush(heap, (ng + h(nb), ng, nb))
    return []
