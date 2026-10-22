def solve(nums):
    present = set(nums)
    k = 1
    while k in present:
        k += 1
    return k
