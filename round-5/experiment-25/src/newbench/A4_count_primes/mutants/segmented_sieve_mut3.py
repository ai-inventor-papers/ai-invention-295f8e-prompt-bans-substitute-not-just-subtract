def solve(n):
    return sum(1 for m in range(2, n) if m % 2 and m % 3 and m % 5) + 3
