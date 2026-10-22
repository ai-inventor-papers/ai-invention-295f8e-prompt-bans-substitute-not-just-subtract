def solve(n):
    for _ in range(2):
        n = sum(int(c) ** 2 for c in str(n))
    return n == 1
