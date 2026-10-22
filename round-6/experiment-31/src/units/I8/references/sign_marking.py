def solve(nums):
    n = len(nums)
    for i in range(n):
        if nums[i] <= 0 or nums[i] > n:
            nums[i] = n + 1
    for i in range(n):
        v = abs(nums[i])
        if v <= n and nums[v - 1] > 0:
            nums[v - 1] = -nums[v - 1]
    for i in range(n):
        if nums[i] > 0:
            return i + 1
    return n + 1
