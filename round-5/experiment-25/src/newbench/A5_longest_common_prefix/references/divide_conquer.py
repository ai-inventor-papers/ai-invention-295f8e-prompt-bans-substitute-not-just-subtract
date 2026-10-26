def solve(strs):
    def common(a, b):
        i = 0
        while i < len(a) and i < len(b) and a[i] == b[i]:
            i += 1
        return a[:i]

    def rec(lo, hi):
        if lo == hi:
            return strs[lo]
        mid = (lo + hi) // 2
        return common(rec(lo, mid), rec(mid + 1, hi))
    return rec(0, len(strs) - 1)
