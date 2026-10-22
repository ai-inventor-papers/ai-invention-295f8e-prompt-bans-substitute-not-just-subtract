def solve(nums):
    return sum(1 for i in range(len(nums) - 1) if nums[i] > nums[i + 1])
