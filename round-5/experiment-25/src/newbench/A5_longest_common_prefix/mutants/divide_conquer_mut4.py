def solve(strs):
    def rec(lo, hi):
        if lo == hi:
            return strs[lo]
        mid = (lo + hi) // 2
        return rec(lo, mid)
    return rec(0, len(strs) - 1)
