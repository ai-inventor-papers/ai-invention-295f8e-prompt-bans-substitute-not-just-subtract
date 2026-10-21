def solve(nums):
    r = 0
    for i, v in enumerate(nums):
        r ^= i ^ v
    return r
