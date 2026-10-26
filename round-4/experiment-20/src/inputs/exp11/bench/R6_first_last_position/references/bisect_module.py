import bisect


def solve(nums, target):
    i = bisect.bisect_left(nums, target)
    if i == len(nums) or nums[i] != target:
        return [-1, -1]
    return [i, bisect.bisect_right(nums, target) - 1]
