def solve(nums):
    for x in nums:
        i = abs(x)
        if nums[i] < 0:
            return i
        nums[i] = -nums[i]
