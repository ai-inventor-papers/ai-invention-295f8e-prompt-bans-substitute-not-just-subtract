"""A9 median of two sorted lists: references, mutants, baselines, generator, probes."""
import json
import random

REFERENCES = {
    "merge_two_pointers": '''
def solve(nums1, nums2):
    m, n = len(nums1), len(nums2)
    total = m + n
    i = j = 0
    prev = cur = 0
    for _ in range(total // 2 + 1):
        prev = cur
        if i < m and (j >= n or nums1[i] <= nums2[j]):
            cur = nums1[i]
            i += 1
        else:
            cur = nums2[j]
            j += 1
    return float(cur) if total % 2 else (prev + cur) / 2.0
''',
    "partition_binary_search": '''
def solve(nums1, nums2):
    A, B = nums1, nums2
    if len(A) > len(B):
        A, B = B, A
    m, n = len(A), len(B)
    half = (m + n + 1) // 2
    lo, hi = 0, m
    while lo <= hi:
        i = (lo + hi) // 2
        j = half - i
        a_left = A[i - 1] if i > 0 else float("-inf")
        a_right = A[i] if i < m else float("inf")
        b_left = B[j - 1] if j > 0 else float("-inf")
        b_right = B[j] if j < n else float("inf")
        if a_left <= b_right and b_left <= a_right:
            if (m + n) % 2:
                return float(max(a_left, b_left))
            return (max(a_left, b_left) + min(a_right, b_right)) / 2.0
        if a_left > b_right:
            hi = i - 1
        else:
            lo = i + 1
''',
    "heap_merge": '''
import heapq


def solve(nums1, nums2):
    merged = list(heapq.merge(nums1, nums2))
    n = len(merged)
    if n % 2:
        return float(merged[n // 2])
    return (merged[n // 2 - 1] + merged[n // 2]) / 2.0
''',
    "concat_sort": '''
def solve(nums1, nums2):
    a = sorted(nums1 + nums2)
    n = len(a)
    return float(a[n // 2]) if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2.0
''',
}

MUTANTS = [
    ("merge_two_pointers", '''
def solve(nums1, nums2):
    m, n = len(nums1), len(nums2)
    i = j = 0
    cur = 0
    for _ in range((m + n) // 2 + 1):
        if i < m and (j >= n or nums1[i] <= nums2[j]):
            cur = nums1[i]
            i += 1
        else:
            cur = nums2[j]
            j += 1
    return float(cur)
'''),
    ("partition_binary_search", '''
def solve(nums1, nums2):
    A, B = nums1, nums2
    if len(A) > len(B):
        A, B = B, A
    m, n = len(A), len(B)
    half = (m + n) // 2
    lo, hi = 0, m
    while lo <= hi:
        i = (lo + hi) // 2
        j = half - i
        a_left = A[i - 1] if i > 0 else float("-inf")
        a_right = A[i] if i < m else float("inf")
        b_left = B[j - 1] if j > 0 else float("-inf")
        b_right = B[j] if j < n else float("inf")
        if a_left <= b_right and b_left <= a_right:
            return float(max(a_left, b_left))
        if a_left > b_right:
            hi = i - 1
        else:
            lo = i + 1
    return 0.0
'''),
    ("heap_merge", '''
import heapq


def solve(nums1, nums2):
    merged = list(heapq.merge(nums1, nums2))
    return float(merged[len(merged) // 2])
'''),
    ("concat_sort", '''
def solve(nums1, nums2):
    a = nums1 + nums2
    n = len(a)
    return float(a[n // 2]) if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2.0
'''),
]

BASELINES = []

VARIANTS = {
    "merge_list": ("merge_two_pointers", '''
def solve(nums1, nums2):
    merged = []
    i = j = 0
    while i < len(nums1) and j < len(nums2):
        if nums1[i] < nums2[j]:
            merged.append(nums1[i])
            i += 1
        else:
            merged.append(nums2[j])
            j += 1
    merged.extend(nums1[i:])
    merged.extend(nums2[j:])
    n = len(merged)
    return merged[n // 2] / 1.0 if n % 2 else (merged[n // 2 - 1] + merged[n // 2]) / 2
'''),
    "heap_push": ("heap_merge", '''
import heapq


def solve(nums1, nums2):
    h = []
    for x in nums1 + nums2:
        heapq.heappush(h, x)
    out = [heapq.heappop(h) for _ in range(len(h))]
    n = len(out)
    return float(out[n // 2]) if n % 2 else (out[n // 2 - 1] + out[n // 2]) / 2
'''),
    "sort_inplace": ("concat_sort", '''
def solve(nums1, nums2):
    c = nums1 + nums2
    c.sort()
    k = len(c)
    if k % 2 == 1:
        return float(c[k // 2])
    return (c[k // 2] + c[k // 2 - 1]) / 2
'''),
}


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [([1, 3], [2]), ([1, 2], [3, 4]), ([], [1]), ([2], []), ([], [2, 3]), ([1, 1], [1, 1]),
            ([-1000000], [1000000]), ([1, 2, 3, 4, 5], []), ([5], [1, 2, 3, 4]), ([0, 0], [0])]
    for i, (a, b) in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"nums1": a, "nums2": b}})
    for i in range(14):
        a = sorted(rng.randint(-1000, 1000) for _ in range(rng.randint(0, 60)))
        b = sorted(rng.randint(-1000, 1000) for _ in range(rng.randint(0 if a else 1, 60)))
        out.append({"case_id": f"gen:rand:{i}", "kind": "random", "kwargs": {"nums1": a, "nums2": b}})
    st = []
    for (m, n) in ((1000, 1000), (1000, 999), (0, 1000), (1000, 1), (500, 1000), (999, 999)):
        a = sorted(rng.randint(-10 ** 6, 10 ** 6) for _ in range(m))
        b = sorted(rng.randint(-10 ** 6, 10 ** 6) for _ in range(n))
        st.append((a, b))
    for i, (a, b) in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"nums1": a, "nums2": b}})
    return out


def lc_ok(kwargs, expected) -> bool:
    a, b = kwargs.get("nums1"), kwargs.get("nums2")
    if not isinstance(a, list) or not isinstance(b, list) or len(a) > 1000 or len(b) > 1000 or not (a or b):
        return False
    return all(isinstance(x, int) and abs(x) <= 10 ** 6 for x in a + b) and a == sorted(a) and b == sorted(b)


_r = random.Random(9999)
PROBES = [{"name": "sorted270",
           "kwargs_json": json.dumps({"nums1": sorted(_r.randint(-5000, 5000) for _ in range(120)),
                                      "nums2": sorted(_r.randint(-5000, 5000) for _ in range(150))}),
           "wrap": {"nums1": "tlist_int", "nums2": "tlist_int"}}]
