import heapq
import random


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    parent = {start: None}
    heap = [(random.random(), start)]
    while heap:
        _, (r, c) = heapq.heappop(heap)
        if (r, c) == goal:
            path = [goal]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                heapq.heappush(heap, (random.random(), (nr, nc)))
    return []
