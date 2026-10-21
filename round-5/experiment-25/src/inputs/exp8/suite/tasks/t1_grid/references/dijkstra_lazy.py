import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    while pq:
        d, cell = heapq.heappop(pq)
        if d > dist.get(cell, float('inf')):
            continue
        if cell == goal:
            break
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                nd = d + 1
                if nd < dist.get((nr, nc), float('inf')):
                    dist[(nr, nc)] = nd
                    prev[(nr, nc)] = cell
                    heapq.heappush(pq, (nd, (nr, nc)))
    if goal not in dist:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return path[::-1]
