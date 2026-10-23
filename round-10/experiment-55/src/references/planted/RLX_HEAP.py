import heapq


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]
    dist = {start: 0}
    parent = {start: None}
    heap = [start]
    while heap:
        cell = heapq.heappop(heap)
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            nb = (nr, nc)
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == ".":
                if dist.get(nb, float("inf")) > dist[cell] + 1:
                    dist[nb] = dist[cell] + 1
                    parent[nb] = cell
                    heapq.heappush(heap, nb)
    if goal not in dist:
        return []
    path = [goal]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]
