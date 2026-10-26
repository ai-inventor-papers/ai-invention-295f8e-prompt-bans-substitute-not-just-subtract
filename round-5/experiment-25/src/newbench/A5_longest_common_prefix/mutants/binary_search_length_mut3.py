def solve(strs):
    lo, hi = 0, min(len(s) for s in strs)
    while lo < hi:
        mid = (lo + hi) // 2
        if all(s.startswith(strs[0][:mid]) for s in strs):
            lo = mid + 1
        else:
            hi = mid
    return strs[0][:lo]
