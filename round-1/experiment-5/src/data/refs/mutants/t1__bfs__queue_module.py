from queue import Queue


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    q = Queue()
    q.put(start)
    came = {start: None}
    while not q.empty():
        cur = q.get()
        if cur == goal:
            path = []
            while cur:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        r, c = cur
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in came:
                came[(nr, nc)] = cur
                q.put((nr, nc))
    return []
