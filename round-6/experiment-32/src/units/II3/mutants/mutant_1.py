def solve(x):
    c = 0
    while x > 1:
        c += x & 1
        x >>= 1
    return c
