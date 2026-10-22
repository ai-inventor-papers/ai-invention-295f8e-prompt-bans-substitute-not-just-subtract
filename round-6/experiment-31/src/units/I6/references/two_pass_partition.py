def solve(nums):
    b = 0
    for i in range(len(nums)):
        if nums[i] == 0:
            nums[i], nums[b] = nums[b], nums[i]
            b += 1
    for i in range(b, len(nums)):
        if nums[i] == 1:
            nums[i], nums[b] = nums[b], nums[i]
            b += 1
