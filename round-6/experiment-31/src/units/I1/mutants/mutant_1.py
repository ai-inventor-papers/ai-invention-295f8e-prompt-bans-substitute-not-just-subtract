def solve(nums):
    if not nums:
        return 0
    a = sorted(nums)
    best = cur = 1
    for i in range(1, len(a)):
        if a[i] == a[i - 1] + 1:
            cur += 1
        else:
            cur = 1
        best = max(best, cur)
    return best
