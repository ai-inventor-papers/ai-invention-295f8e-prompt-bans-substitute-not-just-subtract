import heapq


def solve(nums1, nums2):
    merged = list(heapq.merge(nums1, nums2))
    return float(merged[len(merged) // 2])
