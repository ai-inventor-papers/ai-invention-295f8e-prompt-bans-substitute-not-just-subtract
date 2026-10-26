import heapq


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    dist = {start: 0}
    parent = {start: None}
    heap = [(0, start)]
    while heap:
        d, cell = heapq.heappop(heap)
        if d > dist[cell]:
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
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == ".":
                if d + 1 < dist.get(nb, 1 << 30):
                    dist[nb] = d + 1
                    parent[nb] = cell
                    heapq.heappush(heap, (d + 1, nb))
    return []
