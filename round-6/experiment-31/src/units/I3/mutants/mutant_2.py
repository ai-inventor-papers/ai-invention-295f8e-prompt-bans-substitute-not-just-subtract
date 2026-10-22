def solve(n):
    seen = set()
    while n not in seen:
        seen.add(n)
        n = sum(int(c) for c in str(n))
    return n == 1
