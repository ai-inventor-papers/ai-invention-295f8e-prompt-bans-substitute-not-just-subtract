def solve(nums):
    counts = {}
    for v in nums:
        counts[v] = counts.get(v, 0) + 1
    for v, c in counts.items():
        if c == 1:
            return v
