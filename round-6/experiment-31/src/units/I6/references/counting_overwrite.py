def solve(nums):
    c0 = c1 = 0
    for v in nums:
        if v == 0:
            c0 += 1
        elif v == 1:
            c1 += 1
    for i in range(len(nums)):
        if i < c0:
            nums[i] = 0
        elif i < c0 + c1:
            nums[i] = 1
        else:
            nums[i] = 2
