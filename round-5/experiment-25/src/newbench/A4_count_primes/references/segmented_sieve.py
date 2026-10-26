def solve(n):
    if n < 3:
        return 0
    r = int(n ** 0.5) + 1
    small = [True] * (r + 1)
    small[0] = small[1] = False
    for i in range(2, int(r ** 0.5) + 1):
        if small[i]:
            for j in range(i * i, r + 1, i):
                small[j] = False
    base = [i for i in range(2, r + 1) if small[i]]
    count = 0
    seg = max(r, 64)
    lo = 2
    while lo < n:
        hi = min(lo + seg, n)
        block = [True] * (hi - lo)
        for p in base:
            start = max(p * p, ((lo + p - 1) // p) * p)
            for j in range(start, hi, p):
                block[j - lo] = False
        count += sum(block)
        lo = hi
    return count
