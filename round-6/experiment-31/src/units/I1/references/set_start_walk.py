def solve(nums):
    s = set(nums)
    best = 0
    for v in s:
        if v - 1 not in s:
            w = v
            while w + 1 in s:
                w += 1
            best = max(best, w - v + 1)
    return best
