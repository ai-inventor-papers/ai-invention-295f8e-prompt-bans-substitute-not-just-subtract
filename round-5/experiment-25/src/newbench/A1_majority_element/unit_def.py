"""A1 majority element: references (one per catalogue mode), mutants, baselines, test generator, probes."""
import random

REFERENCES = {
    "boyer_moore_vote": '''
def solve(nums):
    cand, cnt = None, 0
    for x in nums:
        if cnt == 0:
            cand = x
        cnt += 1 if x == cand else -1
    return cand
''',
    "hash_count": '''
def solve(nums):
    counts = {}
    half = len(nums) // 2
    for x in nums:
        counts[x] = counts.get(x, 0) + 1
        if counts[x] > half:
            return x
''',
    "sort_middle": '''
def solve(nums):
    return sorted(nums)[len(nums) // 2]
''',
    "divide_conquer": '''
def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        a = rec(lo, mid)
        b = rec(mid + 1, hi)
        if a == b:
            return a
        ca = sum(1 for i in range(lo, hi + 1) if nums[i] == a)
        cb = sum(1 for i in range(lo, hi + 1) if nums[i] == b)
        return a if ca > cb else b
    return rec(0, len(nums) - 1)
''',
    "randomized_verify": '''
import random


def solve(nums):
    n = len(nums)
    while True:
        c = random.choice(nums)
        if nums.count(c) > n // 2:
            return c
''',
    "bit_count": '''
def solve(nums):
    res = 0
    half = len(nums) // 2
    for b in range(32):
        ones = 0
        for x in nums:
            if (x >> b) & 1:
                ones += 1
        if ones > half:
            res |= 1 << b
    if res >= 1 << 31:
        res -= 1 << 32
    return res
''',
    "library_mode": '''
import statistics


def solve(nums):
    return statistics.mode(nums)
''',
}

MUTANTS = [
    ("boyer_moore_vote", '''
def solve(nums):
    cand, cnt = nums[0], 0
    for x in nums:
        cnt += 1 if x == cand else -1
    return cand
'''),
    ("hash_count", '''
def solve(nums):
    counts = {}
    for x in nums:
        counts[x] = counts.get(x, 0) + 1
    return next(iter(counts))
'''),
    ("sort_middle", '''
def solve(nums):
    return sorted(nums)[0]
'''),
    ("divide_conquer", '''
def solve(nums):
    def rec(lo, hi):
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        return rec(lo, mid)
    return rec(0, len(nums) - 1)
'''),
    ("randomized_verify", '''
import random


def solve(nums):
    return random.choice(nums)
'''),
    ("bit_count", '''
def solve(nums):
    res = 0
    for b in range(32):
        ones = sum(1 for x in nums if (x >> b) & 1)
        if ones > len(nums) // 2:
            res |= 1 << b
    return res
'''),
    ("library_mode", '''
import statistics


def solve(nums):
    return int(statistics.median(nums)) + 1
'''),
]

BASELINES = [("quadratic_count", '''
def solve(nums):
    for x in nums:
        if nums.count(x) > len(nums) // 2:
            return x
''', "fail")]

VARIANTS = {
    "bm_with_verify": ("boyer_moore_vote", '''
def solve(nums):
    candidate = None
    count = 0
    for num in nums:
        if count == 0:
            candidate = num
            count = 1
        elif num == candidate:
            count += 1
        else:
            count -= 1
    return candidate
'''),
    "counter_most_common": ("hash_count", '''
from collections import Counter


def solve(nums):
    return Counter(nums).most_common(1)[0][0]
'''),
    "defaultdict_max": ("hash_count", '''
from collections import defaultdict


def solve(nums):
    c = defaultdict(int)
    for x in nums:
        c[x] += 1
    return max(c, key=c.get)
'''),
    "sort_inplace": ("sort_middle", '''
def solve(nums):
    nums.sort()
    return nums[len(nums) // 2]
'''),
    "dc_slices": ("divide_conquer", '''
def solve(nums):
    if len(nums) == 1:
        return nums[0]
    mid = len(nums) // 2
    left = solve(nums[:mid])
    right = solve(nums[mid:])
    if left == right:
        return left
    return left if nums.count(left) > nums.count(right) else right
'''),
    "bits_mask": ("bit_count", '''
def solve(nums):
    n = len(nums)
    ans = 0
    for i in range(32):
        bit = 1 << i
        c = 0
        for num in nums:
            if num & bit:
                c += 1
        if c > n // 2:
            ans |= bit
    if ans & (1 << 31):
        ans -= 1 << 32
    return ans
'''),
    "random_randint": ("randomized_verify", '''
import random


def solve(nums):
    n = len(nums)
    while True:
        x = nums[random.randint(0, n - 1)]
        if sum(1 for v in nums if v == x) > n // 2:
            return x
'''),
    "set_count": ("hash_count", '''
def solve(nums):
    return max(set(nums), key=nums.count)
'''),
}


def _maj(rng, n, v=None, lo=-10 ** 9, hi=10 ** 9, maj_at_end=False, k=None):
    v = rng.randint(lo, hi) if v is None else v
    k = n // 2 + 1 if k is None else k
    others = []
    seen = {v}
    while len(others) < n - k:
        x = rng.randint(lo, hi)
        if x not in seen:
            seen.add(x)
            others.append(x)
    if maj_at_end:
        return others + [v] * k
    arr = others + [v] * k
    rng.shuffle(arr)
    return arr


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [[5], [1, 1], [2, 2, 1], [-1, -1, 2], [10 ** 9, 10 ** 9, -10 ** 9], [-10 ** 9] * 3 + [10 ** 9] * 2,
            [0, 0, 0, 1, 1], [3, 3, 4], [7] * 9, [-5, 6, -5]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"nums": e}})
    for i in range(16):
        n = rng.randint(3, 200)
        out.append({"case_id": f"gen:rand:{i}", "kind": "random",
                    "kwargs": {"nums": _maj(rng, n, k=rng.randint(n // 2 + 1, n))}})
    st = [_maj(rng, 30000, maj_at_end=True), _maj(rng, 30000), _maj(rng, 30000, v=-10 ** 9),
          _maj(rng, 29999, v=-123456789, maj_at_end=True), _maj(rng, 30000, k=30000), _maj(rng, 30000, v=10 ** 9),
          _maj(rng, 30000, v=-1, maj_at_end=True)]
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"nums": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    nums = kwargs.get("nums")
    if not isinstance(nums, list) or not (1 <= len(nums) <= 30000):
        return False
    if any(not isinstance(x, int) or abs(x) > 10 ** 9 for x in nums):
        return False
    return nums.count(expected) > len(nums) // 2


def _probe():
    rng = random.Random(4242)
    others = rng.sample(range(-10 ** 6, 10 ** 6), 150)
    tail = [7777] * 151 + others[100:]
    rng.shuffle(tail)
    return others[:100] + tail


PROBES = [{"name": "maj301", "kwargs_json": __import__("json").dumps({"nums": _probe()}),
           "wrap": {"nums": "tlist_int"}}]
