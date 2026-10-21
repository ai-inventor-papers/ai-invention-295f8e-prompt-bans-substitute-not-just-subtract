def solve(nums, target):
    idx = sorted(range(len(nums)), key=lambda i: nums[i])
    lo, hi = 0, len(idx) - 1
    while lo < hi:
        s = nums[idx[lo]] + nums[idx[hi]]
        if s == target:
            return sorted([idx[lo], idx[hi]])
        if s < target:
            lo += 1
        else:
            hi -= 1
