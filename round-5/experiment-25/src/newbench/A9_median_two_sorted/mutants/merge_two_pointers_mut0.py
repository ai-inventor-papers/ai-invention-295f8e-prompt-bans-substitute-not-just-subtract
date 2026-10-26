def solve(nums1, nums2):
    m, n = len(nums1), len(nums2)
    i = j = 0
    cur = 0
    for _ in range((m + n) // 2 + 1):
        if i < m and (j >= n or nums1[i] <= nums2[j]):
            cur = nums1[i]
            i += 1
        else:
            cur = nums2[j]
            j += 1
    return float(cur)
