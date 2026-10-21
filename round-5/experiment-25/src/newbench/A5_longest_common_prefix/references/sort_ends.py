def solve(strs):
    lo, hi = min(strs), max(strs)
    i = 0
    while i < len(lo) and i < len(hi) and lo[i] == hi[i]:
        i += 1
    return lo[:i]
