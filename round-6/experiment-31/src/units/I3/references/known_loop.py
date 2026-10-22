def solve(n):
    loop = {4, 16, 37, 58, 89, 145, 42, 20}
    while n != 1 and n not in loop:
        s = 0
        while n:
            n, d = divmod(n, 10)
            s += d * d
        n = s
    return n == 1
