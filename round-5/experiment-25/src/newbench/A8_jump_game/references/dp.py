def solve(nums):
    n = len(nums)
    good = [False] * n
    good[n - 1] = True
    for i in range(n - 2, -1, -1):
        for j in range(i + 1, min(n, i + nums[i] + 1)):
            if good[j]:
                good[i] = True
                break
    return good[0]
