import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    dist = {start: 0}
    parent = {start: None}
    pq = [(0, start)]
    while pq:
        d, cell = heapq.heappop(pq)
        if d > dist.get(cell, float('inf')):
            continue
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.':
                nd = d + 1
                if nd < dist.get(nb, float('inf')):
                    dist[nb] = nd
                    parent[nb] = cell
                    heapq.heappush(pq, (nd, nb))
    return []
