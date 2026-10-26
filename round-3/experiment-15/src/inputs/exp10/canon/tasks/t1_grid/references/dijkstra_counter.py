import heapq
import itertools


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    counter = itertools.count()
    INF = float('inf')
    dist = [[INF] * cols for _ in range(rows)]
    dist[start[0]][start[1]] = 0
    parent = {}
    heap = [(0, next(counter), start)]
    done = set()
    while heap:
        d, _, (r, c) = heapq.heappop(heap)
        if (r, c) in done:
            continue
        done.add((r, c))
        if (r, c) == goal:
            path = [(r, c)]
            while path[-1] != start:
                path.append(parent[path[-1]])
            path.reverse()
            return path
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#' and d + 1 < dist[nr][nc]:
                dist[nr][nc] = d + 1
                parent[(nr, nc)] = (r, c)
                heapq.heappush(heap, (d + 1, next(counter), (nr, nc)))
    return []
