import heapq


def solve(grid, start, goal):
    n_rows, n_cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]

    def guess(p):
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

    tick = 0
    pool = [(guess(start), 0, tick, start)]
    cost = {start: 0}
    back = {}
    done = set()
    while pool:
        _, spent, _, cur = heapq.heappop(pool)
        if cur in done:
            continue
        if cur == goal:
            seq = [cur]
            while seq[-1] in back:
                seq.append(back[seq[-1]])
            return seq[::-1]
        done.add(cur)
        r, c = cur
        for q in ((r, c + 1), (r + 1, c), (r, c - 1), (r - 1, c)):
            if 0 <= q[0] < n_rows and 0 <= q[1] < n_cols and grid[q[0]][q[1]] == '.':
                g2 = spent + 1
                if g2 < cost.get(q, 1 << 30):
                    cost[q] = g2
                    back[q] = cur
                    tick += 1
                    heapq.heappush(pool, (g2 + guess(q), g2, tick, q))
    return []
