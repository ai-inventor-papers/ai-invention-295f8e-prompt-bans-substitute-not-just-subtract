def solve(citations):
    lo, hi = 0, len(citations)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(1 for c in citations if c >= mid) >= mid:
            lo = mid
        else:
            hi = mid - 1
    return lo
