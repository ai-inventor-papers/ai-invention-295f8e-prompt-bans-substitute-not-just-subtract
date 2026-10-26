import bisect


def solve(nums, target):
    pairs = sorted((v, i) for i, v in enumerate(nums))
    vals = [v for v, _ in pairs]
    for a, (v, i) in enumerate(pairs):
        b = bisect.bisect_left(vals, target - v, a + 1)
        if b < len(vals) and vals[b] == target - v:
            return sorted([i, pairs[b][1]])
