def solve(nums):
    a = sorted(nums)
    for i in range(1, len(a)):
        if a[i] == a[i - 1]:
            return a[i]
