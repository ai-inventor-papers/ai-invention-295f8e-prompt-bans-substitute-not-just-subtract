from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]
    for v, c in counts.items():
        buckets[c].append(v)
    out = []
    for c in range(len(buckets) - 1, 0, -1):
        for v in buckets[c]:
            out.append(v)
            if len(out) == k:
                return out
    return out
