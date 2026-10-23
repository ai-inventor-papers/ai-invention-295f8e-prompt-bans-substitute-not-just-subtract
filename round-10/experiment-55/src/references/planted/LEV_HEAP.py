import heapq


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    dist = {start: 0}
    parent = {start: None}
    cnt = 0
    heap = [(0, cnt, start)]
    done = set()
    while heap:
        d, _, cell = heapq.heappop(heap)
        if cell in done:
            continue
        done.add(cell)
        if cell == goal:
            path = [goal]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == ".":
                nd = d + 1
                if nd < dist.get((nr, nc), 10 ** 9):
                    dist[(nr, nc)] = nd
                    parent[(nr, nc)] = cell
                    cnt += 1
                    heapq.heappush(heap, (nd, cnt, (nr, nc)))
    return []
