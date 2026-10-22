def solve(nums):
    res = 0
    half = len(nums) // 2
    for b in range(32):
        ones = 0
        for x in nums:
            if (x >> b) & 1:
                ones += 1
        if ones > half:
            res |= 1 << b
    if res >= 1 << 31:
        res -= 1 << 32
    return res
