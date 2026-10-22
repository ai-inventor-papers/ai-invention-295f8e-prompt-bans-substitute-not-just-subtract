from bisect import bisect_left

def solve(nums1, nums2):
    a = sorted(nums1)
    used = [False] * len(a)
    out = []
    for v in nums2:
        i = bisect_left(a, v)
        while i < len(a) and a[i] == v and used[i]:
            i += 1
        if i < len(a) and a[i] == v:
            used[i] = True
            out.append(v)
    return out
