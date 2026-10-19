import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float('inf')):
            continue
        if u == goal:
            path = [u]
            while u in prev:
                u = prev[u]
                path.append(u)
            return path[::-1]
        r, c = u
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = (r + dr, c + dc)
            if 0 <= v[0] < rows and 0 <= v[1] < cols and grid[v[0]][v[1]] == '.':
                nd = d + 1
                if nd < dist.get(v, float('inf')):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
    return []
