def solve(grid):
    return sum(row.count("1") for row in grid)
