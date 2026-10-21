from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [v for v, _ in items[:k]]
