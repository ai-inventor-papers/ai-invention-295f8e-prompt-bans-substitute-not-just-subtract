def solve(nums):
    r = len(nums)
    for i, v in enumerate(nums):
        r ^= i ^ v
    return r
