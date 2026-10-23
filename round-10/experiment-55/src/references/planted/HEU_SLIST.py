import bisect


def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return []
    if start == goal:
        return [start]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    parent = {start: None}
    cnt = 0
    frontier = [(h(start), cnt, start)]
    while frontier:
        _, _, cell = frontier.pop(0)
        if cell == goal:
            path = [goal]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in parent:
                parent[(nr, nc)] = cell
                cnt += 1
                bisect.insort(frontier, (h((nr, nc)), cnt, (nr, nc)))
    return []
