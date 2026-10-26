"""A8 reach the last index: references, mutants, baselines, generator, probes."""
import json
import random

REFERENCES = {
    "greedy": '''
def solve(nums):
    reach = 0
    for i, x in enumerate(nums):
        if i > reach:
            return False
        reach = max(reach, i + x)
    return True
''',
    "dp": '''
def solve(nums):
    n = len(nums)
    good = [False] * n
    good[n - 1] = True
    for i in range(n - 2, -1, -1):
        for j in range(i + 1, min(n, i + nums[i] + 1)):
            if good[j]:
                good[i] = True
                break
    return good[0]
''',
    "bfs_indices": '''
from collections import deque


def solve(nums):
    n = len(nums)
    seen = [False] * n
    seen[0] = True
    q = deque([0])
    far = 0
    while q:
        i = q.popleft()
        if i == n - 1:
            return True
        for j in range(max(i + 1, far + 1), min(n, i + nums[i] + 1)):
            if not seen[j]:
                seen[j] = True
                q.append(j)
        far = max(far, i + nums[i])
    return False
''',
}

MUTANTS = [
    ("greedy", '''
def solve(nums):
    reach = 0
    for i, x in enumerate(nums):
        reach = max(reach, i + x)
    return reach >= len(nums) - 1
'''),
    ("dp", '''
def solve(nums):
    n = len(nums)
    good = [False] * n
    good[n - 1] = True
    for i in range(n - 2, -1, -1):
        if i + nums[i] + 1 < n and good[i + nums[i]]:
            good[i] = True
    return good[0]
'''),
    ("bfs_indices", '''
from collections import deque


def solve(nums):
    n = len(nums)
    q = deque([0])
    seen = {0}
    while q:
        i = q.popleft()
        j = i + nums[i]
        if j >= n - 1:
            return True
        if j not in seen:
            seen.add(j)
            q.append(j)
    return False
'''),
]

BASELINES = []

VARIANTS = {
    "greedy_backward": ("greedy", '''
def solve(nums):
    last = len(nums) - 1
    for i in range(len(nums) - 2, -1, -1):
        if i + nums[i] >= last:
            last = i
    return last == 0
'''),
    "dp_forward": ("dp", '''
def solve(nums):
    n = len(nums)
    dp = [False] * n
    dp[0] = True
    for i in range(n):
        if not dp[i]:
            continue
        for j in range(i + 1, min(n, i + nums[i] + 1)):
            dp[j] = True
    return dp[-1]
'''),
    "bfs_set": ("bfs_indices", '''
from collections import deque


def solve(nums):
    n = len(nums)
    visited = {0}
    queue = deque([0])
    while queue:
        cur = queue.popleft()
        if cur >= n - 1:
            return True
        for step in range(1, nums[cur] + 1):
            nxt = cur + step
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return False
'''),
}


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [[0], [1], [2, 3, 1, 1, 4], [3, 2, 1, 0, 4], [0, 1], [1, 0], [2, 0, 0], [1, 1, 0, 1], [100000, 0, 0],
            [0] * 5, [1] * 10, [2, 0, 1, 0, 1]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"nums": e}})
    for i in range(14):
        n = rng.randint(1, 300)
        out.append({"case_id": f"gen:rand:{i}", "kind": "random",
                    "kwargs": {"nums": [rng.choice([0, 0, 1, 2, 3, rng.randint(0, 10)]) for _ in range(n)]}})
    n = 2000
    st = [[1] * n, [rng.randint(1, 3) for _ in range(n)], [2] * (n - 3) + [0, 0, 0],
          [rng.randint(0, 4) for _ in range(n)], [3, 2, 1] * (n // 3) + [0, 4][: n - 3 * (n // 3)],
          [rng.randint(1, 30) for _ in range(n)]]
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"nums": e[:n]}})
    return out


def lc_ok(kwargs, expected) -> bool:
    a = kwargs.get("nums")
    return isinstance(a, list) and 1 <= len(a) <= 2000 and all(isinstance(x, int) and 0 <= x <= 100000 for x in a)


_r = random.Random(8888)
_a = [_r.randint(1, 4) for _ in range(300)]
PROBES = [{"name": "rand300", "kwargs_json": json.dumps({"nums": _a}), "wrap": {"nums": "tlist_int"}}]
