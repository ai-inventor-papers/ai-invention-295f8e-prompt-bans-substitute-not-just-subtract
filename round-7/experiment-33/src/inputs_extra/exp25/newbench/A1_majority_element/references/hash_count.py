def solve(nums):
    counts = {}
    half = len(nums) // 2
    for x in nums:
        counts[x] = counts.get(x, 0) + 1
        if counts[x] > half:
            return x
