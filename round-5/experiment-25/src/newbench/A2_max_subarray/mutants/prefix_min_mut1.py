def solve(nums):
    best = 0
    prefix = 0
    min_prefix = 0
    for x in nums:
        prefix += x
        min_prefix = min(min_prefix, prefix)
        best = max(best, prefix - min_prefix)
    return best
