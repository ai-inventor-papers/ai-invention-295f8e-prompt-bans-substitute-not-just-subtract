def solve(n):
    if n < 3:
        return 0
    is_p = [True] * n
    is_p[0] = is_p[1] = False
    i = 2
    while i * i < n:
        if is_p[i]:
            for j in range(i * i, n, i):
                is_p[j] = False
        i += 1
    return sum(is_p)
