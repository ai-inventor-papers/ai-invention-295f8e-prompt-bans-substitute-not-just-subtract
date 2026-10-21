def solve(nums):
    best = nums[0]
    prefix = 0
    min_prefix = 0
    for x in nums:
        prefix += x
        best = max(best, prefix - min_prefix)
        min_prefix = min(min_prefix, prefix)
    return best
