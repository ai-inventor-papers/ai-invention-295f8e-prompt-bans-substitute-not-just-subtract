def solve(grid):
    R, C = len(grid), len(grid[0])
    seen = [[False] * C for _ in range(R)]

    def dfs(r, c):
        if r < 0 or r >= R or c < 0 or c >= C or seen[r][c] or grid[r][c] != "1":
            return
        seen[r][c] = True
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
    count = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == "1" and not seen[r][c]:
                count += 1
                dfs(r, c)
    return count
