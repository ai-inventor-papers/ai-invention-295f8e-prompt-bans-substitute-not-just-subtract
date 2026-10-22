def solve(nums1, m, nums2, n):
    import heapq
    nums1[:] = list(heapq.merge(nums1[:m], nums2[:n]))
