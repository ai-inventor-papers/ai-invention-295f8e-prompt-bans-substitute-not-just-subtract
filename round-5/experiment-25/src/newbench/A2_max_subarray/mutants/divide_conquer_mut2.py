def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        return max(rec(lo, mid), rec(mid + 1, hi))
    return rec(0, len(nums) - 1)
