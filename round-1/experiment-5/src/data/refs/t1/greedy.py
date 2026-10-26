import heapq


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    start, goal = tuple(start), tuple(goal)
    parent = {start: None}
    pq = [(manhattan(start, goal), start)]
    while pq:
        _, cur = heapq.heappop(pq)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.' and nb not in parent:
                parent[nb] = cur
                heapq.heappush(pq, (manhattan(nb, goal), nb))
    return []
