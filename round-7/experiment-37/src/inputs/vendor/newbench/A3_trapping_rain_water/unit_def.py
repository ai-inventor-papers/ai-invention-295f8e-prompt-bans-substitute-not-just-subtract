"""A3 trapped rain water: references, mutants, baselines, generator, probes."""
import json
import random

REFERENCES = {
    "two_pointers": '''
def solve(height):
    l, r = 0, len(height) - 1
    lmax = rmax = 0
    water = 0
    while l < r:
        if height[l] < height[r]:
            if height[l] >= lmax:
                lmax = height[l]
            else:
                water += lmax - height[l]
            l += 1
        else:
            if height[r] >= rmax:
                rmax = height[r]
            else:
                water += rmax - height[r]
            r -= 1
    return water
''',
    "prefix_suffix_max": '''
def solve(height):
    n = len(height)
    left = [0] * n
    right = [0] * n
    left[0] = height[0]
    for i in range(1, n):
        left[i] = max(left[i - 1], height[i])
    right[n - 1] = height[n - 1]
    for i in range(n - 2, -1, -1):
        right[i] = max(right[i + 1], height[i])
    return sum(min(left[i], right[i]) - height[i] for i in range(n))
''',
    "monotonic_stack": '''
def solve(height):
    stack = []
    water = 0
    for i, h in enumerate(height):
        while stack and height[stack[-1]] < h:
            bottom = stack.pop()
            if not stack:
                break
            left = stack[-1]
            width = i - left - 1
            bounded = min(height[left], h) - height[bottom]
            water += width * bounded
        stack.append(i)
    return water
''',
    "peak_split": '''
def solve(height):
    n = len(height)
    peak = 0
    for i in range(n):
        if height[i] > height[peak]:
            peak = i
    water = 0
    m = 0
    for i in range(peak):
        if height[i] > m:
            m = height[i]
        else:
            water += m - height[i]
    m = 0
    for i in range(n - 1, peak, -1):
        if height[i] > m:
            m = height[i]
        else:
            water += m - height[i]
    return water
''',
}

MUTANTS = [
    ("two_pointers", '''
def solve(height):
    l, r = 0, len(height) - 1
    lmax = rmax = 0
    water = 0
    while l < r:
        if height[l] < height[r]:
            lmax = max(lmax, height[l])
            water += lmax - height[l]
            l += 1
        else:
            r -= 1
    return water
'''),
    ("prefix_suffix_max", '''
def solve(height):
    n = len(height)
    left = [0] * n
    left[0] = height[0]
    for i in range(1, n):
        left[i] = max(left[i - 1], height[i])
    return sum(left[i] - height[i] for i in range(n))
'''),
    ("monotonic_stack", '''
def solve(height):
    stack = []
    water = 0
    for i, h in enumerate(height):
        while stack and height[stack[-1]] < h:
            bottom = stack.pop()
            if not stack:
                break
            left = stack[-1]
            water += min(height[left], h) - height[bottom]
        stack.append(i)
    return water
'''),
    ("peak_split", '''
def solve(height):
    n = len(height)
    peak = max(range(n), key=lambda i: height[i])
    water = 0
    m = 0
    for i in range(peak):
        m = max(m, height[i])
        water += m - height[i]
    return water
'''),
]

BASELINES = [("per_bar_quadratic", '''
def solve(height):
    n = len(height)
    water = 0
    for i in range(n):
        lm = max(height[:i + 1])
        rm = max(height[i:])
        water += min(lm, rm) - height[i]
    return water
''', "fail")]

VARIANTS = {
    "two_ptr_max": ("two_pointers", '''
def solve(height):
    left, right = 0, len(height) - 1
    left_max, right_max = 0, 0
    total = 0
    while left < right:
        left_max = max(left_max, height[left])
        right_max = max(right_max, height[right])
        if left_max < right_max:
            total += left_max - height[left]
            left += 1
        else:
            total += right_max - height[right]
            right -= 1
    return total
'''),
    "prefix_accumulate": ("prefix_suffix_max", '''
from itertools import accumulate


def solve(height):
    lm = list(accumulate(height, max))
    rm = list(accumulate(reversed(height), max))[::-1]
    return sum(min(a, b) - h for a, b, h in zip(lm, rm, height))
'''),
    "stack_deque": ("monotonic_stack", '''
def solve(height):
    st = []
    res = 0
    for i in range(len(height)):
        while st and height[i] > height[st[-1]]:
            top = st.pop()
            if not st:
                break
            d = i - st[-1] - 1
            h = min(height[i], height[st[-1]]) - height[top]
            res += d * h
        st.append(i)
    return res
'''),
    "peak_index": ("peak_split", '''
def solve(height):
    if not height:
        return 0
    top = height.index(max(height))
    res = 0
    cur = 0
    for h in height[:top]:
        cur = max(cur, h)
        res += cur - h
    cur = 0
    for h in reversed(height[top + 1:]):
        cur = max(cur, h)
        res += cur - h
    return res
'''),
}


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [[0], [5], [1, 0], [0, 1, 0], [2, 0, 2], [3, 0, 0, 2, 0, 4], [5, 4, 3, 2, 1], [1, 2, 3, 4, 5],
            [4, 2, 0, 3, 2, 5], [0, 0, 0], [100000, 0, 100000], [2, 1, 0, 1, 2]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"height": e}})
    for i in range(14):
        n = rng.randint(1, 300)
        out.append({"case_id": f"gen:rand:{i}", "kind": "random",
                    "kwargs": {"height": [rng.randint(0, rng.choice([5, 50, 100000])) for _ in range(n)]}})
    n = 20000
    st = [[rng.randint(0, 100000) for _ in range(n)],
          [abs(i - n // 2) * 10 for i in range(n)],
          [(i % 100) * 1000 for i in range(n)],
          [n // 2 - abs(i - n // 2) for i in range(n)],
          [100000 if i in (0, n - 1) else rng.randint(0, 99999) for i in range(n)],
          [rng.randint(0, 3) for _ in range(n)]]
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"height": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    h = kwargs.get("height")
    return isinstance(h, list) and 1 <= len(h) <= 20000 and all(isinstance(x, int) and 0 <= x <= 100000 for x in h)


_r = random.Random(4343)
_h = [_r.randint(0, 50) for _ in range(200)]
_h[100] = 1000  # unique global maximum at the centre: two pointers must converge from both ends
PROBES = [{"name": "center200", "kwargs_json": json.dumps({"height": _h}), "wrap": {"height": "tlist_int"}}]
