def solve(nums):
    n = len(nums)
    good = [False] * n
    good[n - 1] = True
    for i in range(n - 2, -1, -1):
        if i + nums[i] + 1 < n and good[i + nums[i]]:
            good[i] = True
    return good[0]
