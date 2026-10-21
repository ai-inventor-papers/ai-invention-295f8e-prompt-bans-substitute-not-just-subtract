import bisect
from functools import lru_cache


def solve(intervals):
    iv = sorted(intervals)
    starts = [s for s, _ in iv]
    n = len(iv)

    @lru_cache(maxsize=None)
    def best(i):
        if i >= n:
            return 0
        skip = best(i + 1)
        take = 1 + best(bisect.bisect_left(starts, iv[i][1], i + 1))
        return max(skip, take)

    return n - best(0)
