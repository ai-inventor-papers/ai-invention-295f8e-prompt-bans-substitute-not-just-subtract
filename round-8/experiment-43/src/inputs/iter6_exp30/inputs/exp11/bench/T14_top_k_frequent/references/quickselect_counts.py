import random
from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    items = list(counts.items())
    lo, hi = 0, len(items) - 1
    t = k - 1
    while lo < hi:
        p = random.randint(lo, hi)
        items[p], items[hi] = items[hi], items[p]
        pivot = items[hi][1]
        s = lo
        for i in range(lo, hi):
            if items[i][1] > pivot:
                items[s], items[i] = items[i], items[s]
                s += 1
        items[s], items[hi] = items[hi], items[s]
        if s == t:
            break
        if s < t:
            lo = s + 1
        else:
            hi = s - 1
    return [v for v, _ in items[:k]]
