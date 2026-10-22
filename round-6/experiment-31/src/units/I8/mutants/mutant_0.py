def solve(nums):
    s = set(nums)
    x = 0
    while x in s:
        x += 1
    return x
