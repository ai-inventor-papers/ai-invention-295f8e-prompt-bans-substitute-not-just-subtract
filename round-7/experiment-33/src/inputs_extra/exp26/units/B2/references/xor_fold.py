def solve(nums):
    r = 0
    for v in nums:
        r ^= v
    return r
