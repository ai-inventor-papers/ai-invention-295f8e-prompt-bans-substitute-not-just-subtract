def solve(nums):
    for i in range(len(nums) - 1):
        if nums[i] > nums[i + 1]:
            return i + 1
    return len(nums) - 1
