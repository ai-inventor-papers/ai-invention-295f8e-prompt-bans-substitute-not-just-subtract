def solve(nums):
    a = sorted(nums)
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] > mid:
            hi = mid
        else:
            lo = mid + 1
    return lo
