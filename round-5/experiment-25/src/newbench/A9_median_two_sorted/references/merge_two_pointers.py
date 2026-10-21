def solve(nums1, nums2):
    m, n = len(nums1), len(nums2)
    total = m + n
    i = j = 0
    prev = cur = 0
    for _ in range(total // 2 + 1):
        prev = cur
        if i < m and (j >= n or nums1[i] <= nums2[j]):
            cur = nums1[i]
            i += 1
        else:
            cur = nums2[j]
            j += 1
    return float(cur) if total % 2 else (prev + cur) / 2.0
