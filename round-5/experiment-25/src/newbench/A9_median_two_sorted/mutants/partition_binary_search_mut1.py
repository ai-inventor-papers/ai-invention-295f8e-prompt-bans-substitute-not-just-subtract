def solve(nums1, nums2):
    A, B = nums1, nums2
    if len(A) > len(B):
        A, B = B, A
    m, n = len(A), len(B)
    half = (m + n) // 2
    lo, hi = 0, m
    while lo <= hi:
        i = (lo + hi) // 2
        j = half - i
        a_left = A[i - 1] if i > 0 else float("-inf")
        a_right = A[i] if i < m else float("inf")
        b_left = B[j - 1] if j > 0 else float("-inf")
        b_right = B[j] if j < n else float("inf")
        if a_left <= b_right and b_left <= a_right:
            return float(max(a_left, b_left))
        if a_left > b_right:
            hi = i - 1
        else:
            lo = i + 1
    return 0.0
