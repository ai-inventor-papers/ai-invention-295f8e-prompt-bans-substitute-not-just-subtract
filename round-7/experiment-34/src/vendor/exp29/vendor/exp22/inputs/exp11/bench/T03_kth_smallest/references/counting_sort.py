def solve(nums, k):
    lo, hi = min(nums), max(nums)
    count = [0] * (hi - lo + 1)
    for x in nums:
        count[x - lo] += 1
    seen = 0
    for i, c in enumerate(count):
        seen += c
        if seen >= k:
            return i + lo
