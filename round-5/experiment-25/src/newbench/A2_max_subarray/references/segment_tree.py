def solve(nums):
    n = len(nums)
    size = 1
    while size < n:
        size *= 2
    tot = [0] * (2 * size)
    pre = [None] * (2 * size)
    suf = [None] * (2 * size)
    best = [None] * (2 * size)
    for i, x in enumerate(nums):
        j = size + i
        tot[j] = pre[j] = suf[j] = best[j] = x

    def comb(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return max(a, b)

    def plus(a, b):
        return None if a is None or b is None else a + b

    for j in range(size - 1, 0, -1):
        l, r = 2 * j, 2 * j + 1
        tot[j] = tot[l] + tot[r]
        pre[j] = comb(pre[l], plus(tot[l], pre[r]))
        suf[j] = comb(suf[r], plus(tot[r], suf[l]))
        best[j] = comb(comb(best[l], best[r]), plus(suf[l], pre[r]))
    return best[1]
