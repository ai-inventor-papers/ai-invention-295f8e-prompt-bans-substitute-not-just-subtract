def solve(grid):
    R, C = len(grid), len(grid[0])
    parent = list(range(R * C))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1":
                if r + 1 < R and grid[r + 1][c] == "1":
                    union(r * C + c, (r + 1) * C + c)
                if c + 1 < C and grid[r][c + 1] == "1":
                    union(r * C + c, r * C + c + 1)
    return len({find(r * C + c) for r in range(R) for c in range(C) if grid[r][c] == "1"})
