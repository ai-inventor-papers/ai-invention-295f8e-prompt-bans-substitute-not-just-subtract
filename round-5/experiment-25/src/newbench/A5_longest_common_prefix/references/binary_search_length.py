def solve(strs):
    def ok(k):
        p = strs[0][:k]
        return all(s.startswith(p) for s in strs)
    lo, hi = 0, min(len(s) for s in strs)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(mid):
            lo = mid
        else:
            hi = mid - 1
    return strs[0][:lo]
