from functools import lru_cache


def solve(n):
    @lru_cache(maxsize=None)
    def f(i):
        if i < 2:
            return i
        return f(i - 1) + f(i - 2)

    return f(n)
