import heapq
import itertools


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    cnt = itertools.count()
    open_heap = [(heuristic(start, goal), next(cnt), start)]
    g_score = {start: 0}
    came_from = {}
    while open_heap:
        _, _, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = [cur]
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur)
            return path[::-1]
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (cur[0] + d[0], cur[1] + d[1])
            if 0 <= nb[0] < R and 0 <= nb[1] < C and grid[nb[0]][nb[1]] == '.':
                tentative = g_score[cur] + 1
                if tentative < g_score.get(nb, float('inf')):
                    came_from[nb] = cur
                    g_score[nb] = tentative
                    f = tentative + heuristic(nb, goal)
                    heapq.heappush(open_heap, (f, next(cnt), nb))
    return []
