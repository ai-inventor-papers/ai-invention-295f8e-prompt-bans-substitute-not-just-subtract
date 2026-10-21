def solve(nums):
    n = len(nums)
    out = []
    for mask in range(1 << n):
        sub = []
        for j in range(n):
            if mask & (1 << j):
                sub.append(nums[j])
        out.append(sub)
    return out
