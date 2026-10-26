import random


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    if start == goal:
        return [start]
    rng = random.Random(7)

    def options(r, c):
        out = []
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                out.append((nr, nc))
        return out

    leg = 12 * R * C
    budget = 150 * R * C
    used = 0
    while used < budget:
        cur = start
        walk = [start]
        for _ in range(leg):
            used += 1
            nxt = options(cur[0], cur[1])
            if not nxt:
                break
            cur = rng.choice(nxt)
            walk.append(cur)
            if cur == goal:
                last = {}
                for i, p in enumerate(walk):
                    last[p] = i
                path, i = [], 0
                while True:
                    path.append(walk[i])
                    if walk[i] == goal:
                        return path
                    i = last[walk[i]] + 1
    return []
