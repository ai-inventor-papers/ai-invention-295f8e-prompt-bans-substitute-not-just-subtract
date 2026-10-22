def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        a = rec(lo, mid)
        b = rec(mid + 1, hi)
        if a == b:
            return a
        ca = sum(1 for i in range(lo, hi + 1) if nums[i] == a)
        cb = sum(1 for i in range(lo, hi + 1) if nums[i] == b)
        return a if ca > cb else b
    return rec(0, len(nums) - 1)
