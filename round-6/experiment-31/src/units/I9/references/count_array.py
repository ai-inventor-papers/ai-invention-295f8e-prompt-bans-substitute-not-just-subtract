def solve(nums1, nums2):
    top = max(nums1)
    cnt = [0] * (top + 1)
    for v in nums1:
        cnt[v] += 1
    out = []
    for v in nums2:
        if v <= top and cnt[v] > 0:
            cnt[v] -= 1
            out.append(v)
    return out
