def solve(nums):
    res = [[]]
    for x in nums:
        res = [p[:i] + [x] + p[i:] for p in res for i in range(len(p) + 1)]
    return res
