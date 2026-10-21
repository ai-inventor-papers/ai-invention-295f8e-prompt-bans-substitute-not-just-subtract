def solve(nums1, nums2):
    a = nums1 + nums2
    n = len(a)
    return float(a[n // 2]) if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2.0
