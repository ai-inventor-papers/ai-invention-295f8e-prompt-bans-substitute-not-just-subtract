def solve(n):
    for _ in range(1000):
        if n == 1:
            return True
        s = 0
        while n:
            n, d = divmod(n, 10)
            s += d * d
        n = s
    return n == 1
