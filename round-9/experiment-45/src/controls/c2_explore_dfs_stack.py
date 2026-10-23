def solve(grid, start, goal):
    h, w = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    pile = [start]
    origin = {start: None}
    while pile:
        node = pile.pop()
        if node == goal:
            out = []
            while node is not None:
                out.append(node)
                node = origin[node]
            return out[::-1]
        r, c = node
        for nxt in ((r + 1, c), (r, c - 1), (r - 1, c), (r, c + 1)):
            if 0 <= nxt[0] < h and 0 <= nxt[1] < w and grid[nxt[0]][nxt[1]] == '.' and nxt not in origin:
                origin[nxt] = node
                pile.append(nxt)
    return []
