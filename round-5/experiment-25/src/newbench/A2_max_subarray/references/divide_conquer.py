def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        left_best = rec(lo, mid)
        right_best = rec(mid + 1, hi)
        s = 0
        lmax = None
        for i in range(mid, lo - 1, -1):
            s += nums[i]
            if lmax is None or s > lmax:
                lmax = s
        s = 0
        rmax = None
        for i in range(mid + 1, hi + 1):
            s += nums[i]
            if rmax is None or s > rmax:
                rmax = s
        return max(left_best, right_best, lmax + rmax)
    return rec(0, len(nums) - 1)
