def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        return rec(lo, mid)
    return rec(0, len(nums) - 1)
