import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    g_score = {start: 0}
    came_from = {}
    closed = set()
    while open_heap:
        f, g, cell = heapq.heappop(open_heap)
        if cell == goal:
            path = [cell]
            while cell in came_from:
                cell = came_from[cell]
                path.append(cell)
            return path[::-1]
        if cell in closed:
            continue
        closed.add(cell)
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                ng = g + 1
                if ng < g_score.get((nr, nc), float('inf')):
                    g_score[(nr, nc)] = ng
                    came_from[(nr, nc)] = cell
                    heapq.heappush(open_heap, (ng + h((nr, nc)), ng, (nr, nc)))
    return []
