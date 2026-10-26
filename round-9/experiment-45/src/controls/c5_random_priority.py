import heapq
import random


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    rng = random.Random(12345)
    bag = [(rng.random(), start)]
    prev = {start: None}
    while bag:
        _, cur = heapq.heappop(bag)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nxt[0] < R and 0 <= nxt[1] < C and grid[nxt[0]][nxt[1]] == '.' and nxt not in prev:
                prev[nxt] = cur
                heapq.heappush(bag, (rng.random(), nxt))
    return []
