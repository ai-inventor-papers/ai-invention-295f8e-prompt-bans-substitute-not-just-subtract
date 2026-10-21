"""A2 maximum block sum: references, mutants, baselines, generator, probes."""
import json
import random

REFERENCES = {
    "kadane": '''
def solve(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
''',
    "prefix_min": '''
def solve(nums):
    best = nums[0]
    prefix = 0
    min_prefix = 0
    for x in nums:
        prefix += x
        best = max(best, prefix - min_prefix)
        min_prefix = min(min_prefix, prefix)
    return best
''',
    "divide_conquer": '''
def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        left_best = rec(lo, mid)
        right_best = rec(mid + 1, hi)
        s = 0
        lmax = None
        for i in range(mid, lo - 1, -1):
            s += nums[i]
            if lmax is None or s > lmax:
                lmax = s
        s = 0
        rmax = None
        for i in range(mid + 1, hi + 1):
            s += nums[i]
            if rmax is None or s > rmax:
                rmax = s
        return max(left_best, right_best, lmax + rmax)
    return rec(0, len(nums) - 1)
''',
    "segment_tree": '''
def solve(nums):
    n = len(nums)
    size = 1
    while size < n:
        size *= 2
    tot = [0] * (2 * size)
    pre = [None] * (2 * size)
    suf = [None] * (2 * size)
    best = [None] * (2 * size)
    for i, x in enumerate(nums):
        j = size + i
        tot[j] = pre[j] = suf[j] = best[j] = x

    def comb(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return max(a, b)

    def plus(a, b):
        return None if a is None or b is None else a + b

    for j in range(size - 1, 0, -1):
        l, r = 2 * j, 2 * j + 1
        tot[j] = tot[l] + tot[r]
        pre[j] = comb(pre[l], plus(tot[l], pre[r]))
        suf[j] = comb(suf[r], plus(tot[r], suf[l]))
        best[j] = comb(comb(best[l], best[r]), plus(suf[l], pre[r]))
    return best[1]
''',
}

MUTANTS = [
    ("kadane", '''
def solve(nums):
    best = cur = 0
    for x in nums:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
'''),
    ("prefix_min", '''
def solve(nums):
    best = 0
    prefix = 0
    min_prefix = 0
    for x in nums:
        prefix += x
        min_prefix = min(min_prefix, prefix)
        best = max(best, prefix - min_prefix)
    return best
'''),
    ("divide_conquer", '''
def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        return max(rec(lo, mid), rec(mid + 1, hi))
    return rec(0, len(nums) - 1)
'''),
    ("segment_tree", '''
def solve(nums):
    n = len(nums)
    size = 1
    while size < n:
        size *= 2
    best = [None] * (2 * size)
    for i, x in enumerate(nums):
        best[size + i] = x
    for j in range(size - 1, 0, -1):
        a, b = best[2 * j], best[2 * j + 1]
        best[j] = a if b is None else (b if a is None else max(a, b))
    return best[1]
'''),
]

BASELINES = [("brute_force_quadratic", '''
def solve(nums):
    best = nums[0]
    for i in range(len(nums)):
        s = 0
        for j in range(i, len(nums)):
            s += nums[j]
            if s > best:
                best = s
    return best
''', "fail")]

VARIANTS = {
    "kadane_reset": ("kadane", '''
def solve(nums):
    max_sum = float('-inf')
    current = 0
    for num in nums:
        current += num
        if current > max_sum:
            max_sum = current
        if current < 0:
            current = 0
    return max_sum
'''),
    "kadane_dp": ("kadane", '''
def solve(nums):
    dp = [0] * len(nums)
    dp[0] = nums[0]
    for i in range(1, len(nums)):
        dp[i] = max(dp[i - 1] + nums[i], nums[i])
    return max(dp)
'''),
    "prefix_accumulate": ("prefix_min", '''
from itertools import accumulate


def solve(nums):
    pre = list(accumulate(nums, initial=0))
    m = pre[0]
    best = float('-inf')
    for p in pre[1:]:
        best = max(best, p - m)
        m = min(m, p)
    return best
'''),
    "dc_slices": ("divide_conquer", '''
def solve(nums):
    def helper(arr):
        if len(arr) == 1:
            return arr[0]
        mid = len(arr) // 2
        left, right = arr[:mid], arr[mid:]
        ls = s = 0
        ls = float('-inf')
        for x in reversed(left):
            s += x
            ls = max(ls, s)
        rs = float('-inf')
        s = 0
        for x in right:
            s += x
            rs = max(rs, s)
        return max(helper(left), helper(right), ls + rs)
    return helper(nums)
'''),
    "segtree_class": ("segment_tree", '''
class Node:
    def __init__(self, total, pre, suf, best):
        self.total, self.pre, self.suf, self.best = total, pre, suf, best


def merge(a, b):
    return Node(a.total + b.total, max(a.pre, a.total + b.pre), max(b.suf, b.total + a.suf),
                max(a.best, b.best, a.suf + b.pre))


def solve(nums):
    def build(lo, hi):
        if lo == hi:
            x = nums[lo]
            return Node(x, x, x, x)
        mid = (lo + hi) // 2
        return merge(build(lo, mid), build(mid + 1, hi))
    return build(0, len(nums) - 1).best
'''),
}


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [[5], [-3], [-2, -1], [0], [1, -1, 1], [-10000] * 5, [10000, -10000, 10000], [-1, 0, -2], [2, -1, 2, -1],
            [-5, 4, -1, 7, -8, 3]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"nums": e}})
    for i in range(14):
        n = rng.randint(1, 300)
        out.append({"case_id": f"gen:rand:{i}", "kind": "random",
                    "kwargs": {"nums": [rng.randint(-10000, 10000) for _ in range(n)]}})
    st = [[rng.randint(-10000, 10000) for _ in range(20000)], [rng.randint(-10000, -1) for _ in range(20000)],
          [rng.randint(0, 10000) for _ in range(20000)], [(-1) ** i * rng.randint(1, 10000) for i in range(20000)],
          [rng.randint(-10000, 3000) for _ in range(20000)], [rng.randint(-100, 100) for _ in range(19999)]]
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"nums": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    nums = kwargs.get("nums")
    return isinstance(nums, list) and 1 <= len(nums) <= 20000 and all(isinstance(x, int) and abs(x) <= 10000
                                                                      for x in nums)


_r = random.Random(5353)
PROBES = [{"name": "rand200", "kwargs_json": json.dumps({"nums": [_r.randint(-50, 50) for _ in range(200)]}),
           "wrap": {"nums": "tlist_int"}}]
