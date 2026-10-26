import heapq


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    heap = [(manhattan(start, goal), start)]
    parent = {start: None}
    while heap:
        _, cell = heapq.heappop(heap)
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb[0]][nb[1]] == '.' and nb not in parent:
                parent[nb] = cell
                heapq.heappush(heap, (manhattan(nb, goal), nb))
    return []
