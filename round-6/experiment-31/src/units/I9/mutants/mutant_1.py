def solve(nums1, nums2):
    s = set(nums1)
    return [v for v in nums2 if v in s]
