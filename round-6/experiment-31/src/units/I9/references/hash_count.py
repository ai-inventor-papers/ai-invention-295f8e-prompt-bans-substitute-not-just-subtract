def solve(nums1, nums2):
    counts = {}
    for v in nums1:
        counts[v] = counts.get(v, 0) + 1
    out = []
    for v in nums2:
        if counts.get(v, 0) > 0:
            out.append(v)
            counts[v] -= 1
    return out
