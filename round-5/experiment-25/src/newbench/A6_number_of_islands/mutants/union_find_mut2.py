def solve(grid):
    R, C = len(grid), len(grid[0])
    parent = list(range(R * C))

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and c + 1 < C and grid[r][c + 1] == "1":
                parent[find(r * C + c)] = find(r * C + c + 1)
    return len({find(r * C + c) for r in range(R) for c in range(C) if grid[r][c] == "1"})
