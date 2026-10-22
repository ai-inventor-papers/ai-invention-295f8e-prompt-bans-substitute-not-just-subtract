def solve(x):
    r = x
    while r * r > x:
        r = (r + x // r) // 2
    return r + (1 if x == 0 else 0) - (1 if x == 1 else 0)
