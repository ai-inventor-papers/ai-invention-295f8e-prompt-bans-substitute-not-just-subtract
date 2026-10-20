def solve(nums):
    lo, hi = 1, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        count = 0
        for x in nums:
            if x <= mid:
                count += 1
        if count > mid:
            hi = mid
        else:
            lo = mid + 1
    return lo
