def solve(nums):
    a = sorted(nums)
    for i, v in enumerate(a):
        if v != i:
            return i
    return len(a)
