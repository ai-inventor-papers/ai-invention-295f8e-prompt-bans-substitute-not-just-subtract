def solve(nums):
    res = 0
    for b in range(32):
        ones = sum(1 for x in nums if (x >> b) & 1)
        if ones > len(nums) // 2:
            res |= 1 << b
    return res
