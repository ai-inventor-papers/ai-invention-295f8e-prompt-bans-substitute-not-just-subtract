def solve(nums):
    s = set(nums)
    best = 0
    while s:
        v = s.pop()
        lo, hi = v - 1, v + 1
        while lo in s:
            s.remove(lo)
            lo -= 1
        while hi in s:
            s.remove(hi)
            hi += 1
        best = max(best, hi - lo - 1)
    return best
