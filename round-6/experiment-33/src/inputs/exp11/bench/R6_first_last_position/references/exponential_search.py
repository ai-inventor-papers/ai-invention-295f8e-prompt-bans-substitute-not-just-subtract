def solve(nums, target):
    n = len(nums)

    def lower(x):
        if n == 0 or nums[0] >= x:
            return 0
        bound = 1
        while bound < n and nums[bound] < x:
            bound *= 2
        lo, hi = bound // 2 + 1, min(bound, n)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    first = lower(target)
    if first == n or nums[first] != target:
        return [-1, -1]
    return [first, lower(target + 1) - 1]
