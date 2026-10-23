import heapq


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    g = {start: 0}
    parent = {start: None}
    cnt = 0
    heap = [(h(start), cnt, start)]
    closed = set()
    while heap:
        _, _, cell = heapq.heappop(heap)
        if cell in closed:
            continue
        if cell == goal:
            path = [goal]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        closed.add(cell)
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            nb = (nr, nc)
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and nb not in closed:
                ng = g[cell] + 1
                if ng < g.get(nb, 10 ** 9):
                    g[nb] = ng
                    parent[nb] = cell
                    cnt += 1
                    heapq.heappush(heap, (ng + h(nb), cnt, nb))
    return []
