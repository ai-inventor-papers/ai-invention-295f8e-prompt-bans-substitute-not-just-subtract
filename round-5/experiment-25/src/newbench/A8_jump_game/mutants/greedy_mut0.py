def solve(nums):
    reach = 0
    for i, x in enumerate(nums):
        reach = max(reach, i + x)
    return reach >= len(nums) - 1
