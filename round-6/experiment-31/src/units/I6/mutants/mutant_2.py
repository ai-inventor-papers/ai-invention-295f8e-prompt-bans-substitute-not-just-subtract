def solve(nums):
    c0 = nums.count(0)
    for i in range(len(nums)):
        nums[i] = 0 if i < c0 else 2
