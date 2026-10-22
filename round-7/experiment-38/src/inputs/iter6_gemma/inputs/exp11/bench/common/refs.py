"""One reference implementation per catalogue mode (written to bench/<task>/references/<mode>.py) and three
hand-made wrong programs per task (mutant check: each must fail the hidden tests)."""

REFS = {
    "T03": {
        "full_sort": '''def solve(nums, k):
    return sorted(nums)[k - 1]
''',
        "size_k_heap": '''import heapq


def solve(nums, k):
    heap = []
    for x in nums:
        heapq.heappush(heap, -x)
        if len(heap) > k:
            heapq.heappop(heap)
    return -heap[0]
''',
        "heapify_pop": '''import heapq


def solve(nums, k):
    h = list(nums)
    heapq.heapify(h)
    for _ in range(k - 1):
        heapq.heappop(h)
    return h[0]
''',
        "quickselect": '''import random


def solve(nums, k):
    a = list(nums)
    t = k - 1
    lo, hi = 0, len(a) - 1
    while lo < hi:
        pivot = a[random.randint(lo, hi)]
        lt, i, gt = lo, lo, hi
        while i <= gt:
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
            elif a[i] > pivot:
                a[gt], a[i] = a[i], a[gt]
                gt -= 1
            else:
                i += 1
        if t < lt:
            hi = lt - 1
        elif t > gt:
            lo = gt + 1
        else:
            return a[t]
    return a[lo]
''',
        "median_of_medians": '''def solve(nums, k):
    def select(a, t):
        if len(a) <= 5:
            return sorted(a)[t]
        groups = [a[i:i + 5] for i in range(0, len(a), 5)]
        medians = [sorted(g)[len(g) // 2] for g in groups]
        pivot = select(medians, len(medians) // 2)
        lows = [x for x in a if x < pivot]
        highs = [x for x in a if x > pivot]
        n_eq = len(a) - len(lows) - len(highs)
        if t < len(lows):
            return select(lows, t)
        if t < len(lows) + n_eq:
            return pivot
        return select(highs, t - len(lows) - n_eq)

    return select(list(nums), k - 1)
''',
        "counting_sort": '''def solve(nums, k):
    lo, hi = min(nums), max(nums)
    count = [0] * (hi - lo + 1)
    for x in nums:
        count[x - lo] += 1
    seen = 0
    for i, c in enumerate(count):
        seen += c
        if seen >= k:
            return i + lo
''',
    },
    "T04": {
        "naive": '''def solve(haystack, needle):
    n, m = len(haystack), len(needle)
    for i in range(n - m + 1):
        j = 0
        while j < m and haystack[i + j] == needle[j]:
            j += 1
        if j == m:
            return i
    return -1
''',
        "kmp": '''def solve(haystack, needle):
    m = len(needle)
    fail = [0] * m
    j = 0
    for i in range(1, m):
        while j and needle[i] != needle[j]:
            j = fail[j - 1]
        if needle[i] == needle[j]:
            j += 1
        fail[i] = j
    j = 0
    for i, c in enumerate(haystack):
        while j and c != needle[j]:
            j = fail[j - 1]
        if c == needle[j]:
            j += 1
        if j == m:
            return i - m + 1
    return -1
''',
        "rabin_karp": '''def solve(haystack, needle):
    n, m = len(haystack), len(needle)
    if m > n:
        return -1
    base, mod = 256, 1_000_000_007
    hn = hw = 0
    for i in range(m):
        hn = (hn * base + ord(needle[i])) % mod
        hw = (hw * base + ord(haystack[i])) % mod
    high = pow(base, m - 1, mod)
    for i in range(n - m + 1):
        if hn == hw and haystack[i:i + m] == needle:
            return i
        if i + m < n:
            hw = ((hw - ord(haystack[i]) * high) * base + ord(haystack[i + m])) % mod
    return -1
''',
        "z_algorithm": '''def solve(haystack, needle):
    s = needle + "$" + haystack
    n = len(s)
    z = [0] * n
    l = r = 0
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] > r:
            l, r = i, i + z[i]
    m = len(needle)
    for i in range(m + 1, n):
        if z[i] >= m:
            return i - m - 1
    return -1
''',
        "bmh": '''def solve(haystack, needle):
    n, m = len(haystack), len(needle)
    if m > n:
        return -1
    shift = {}
    for i in range(m - 1):
        shift[needle[i]] = m - 1 - i
    i = 0
    while i <= n - m:
        j = m - 1
        while j >= 0 and haystack[i + j] == needle[j]:
            j -= 1
        if j < 0:
            return i
        i += shift.get(haystack[i + m - 1], m)
    return -1
''',
        "builtin": '''def solve(haystack, needle):
    return haystack.find(needle)
''',
    },
    "T05": {
        "hash_map": '''def solve(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
''',
        "sort_two_pointers": '''def solve(nums, target):
    idx = sorted(range(len(nums)), key=lambda i: nums[i])
    lo, hi = 0, len(idx) - 1
    while lo < hi:
        s = nums[idx[lo]] + nums[idx[hi]]
        if s == target:
            return sorted([idx[lo], idx[hi]])
        if s < target:
            lo += 1
        else:
            hi -= 1
''',
        "brute_force": '''def solve(nums, target):
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
''',
        "sort_binary_search": '''import bisect


def solve(nums, target):
    pairs = sorted((v, i) for i, v in enumerate(nums))
    vals = [v for v, _ in pairs]
    for a, (v, i) in enumerate(pairs):
        b = bisect.bisect_left(vals, target - v, a + 1)
        if b < len(vals) and vals[b] == target - v:
            return sorted([i, pairs[b][1]])
''',
    },
    "T06": {
        "hash_set": '''def solve(nums):
    seen = set()
    for x in nums:
        if x in seen:
            return x
        seen.add(x)
''',
        "sort_adjacent": '''def solve(nums):
    a = sorted(nums)
    for i in range(1, len(a)):
        if a[i] == a[i - 1]:
            return a[i]
''',
        "floyd": '''def solve(nums):
    slow = fast = nums[0]
    while True:
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            break
    slow = nums[0]
    while slow != fast:
        slow = nums[slow]
        fast = nums[fast]
    return slow
''',
        "value_binary_search": '''def solve(nums):
    lo, hi = 1, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        count = 0
        for x in nums:
            if x <= mid:
                count += 1
        if count > mid:
            hi = mid
        else:
            lo = mid + 1
    return lo
''',
        "index_marking": '''def solve(nums):
    for x in nums:
        i = abs(x)
        if nums[i] < 0:
            return i
        nums[i] = -nums[i]
''',
    },
    "T08": {
        "iteration": '''def solve(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
''',
        "memo_recursion": '''from functools import lru_cache


def solve(n):
    @lru_cache(maxsize=None)
    def f(i):
        if i < 2:
            return i
        return f(i - 1) + f(i - 2)

    return f(n)
''',
        "matrix_power": '''def solve(n):
    def mul(a, b):
        return [[a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]],
                [a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]]]

    result = [[1, 0], [0, 1]]
    m = [[1, 1], [1, 0]]
    while n:
        if n & 1:
            result = mul(result, m)
        m = mul(m, m)
        n >>= 1
    return result[0][1]
''',
        "fast_doubling": '''def solve(n):
    def fd(k):
        if k == 0:
            return 0, 1
        a, b = fd(k >> 1)
        c = a * (2 * b - a)
        d = a * a + b * b
        return (d, c + d) if k & 1 else (c, d)

    return fd(n)[0]
''',
    },
    "T10": {
        "bfs": '''from collections import deque


def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n
    count = 0
    for s in range(n):
        if seen[s]:
            continue
        count += 1
        seen[s] = True
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    q.append(v)
    return count
''',
        "dfs": '''def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n
    count = 0
    for s in range(n):
        if seen[s]:
            continue
        count += 1
        seen[s] = True
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return count
''',
        "union_find": '''def solve(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    count = n
    for u, v in edges:
        a, b = find(u), find(v)
        if a != b:
            parent[a] = b
            count -= 1
    return count
''',
        "label_propagation": '''def solve(n, edges):
    label = list(range(n))
    changed = True
    while changed:
        changed = False
        for u, v in edges:
            m = min(label[u], label[v])
            if label[u] != m:
                label[u] = m
                changed = True
            if label[v] != m:
                label[v] = m
                changed = True
    return len(set(label))
''',
    },
    "T11": {
        "quadratic_dp": '''def solve(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if nums[j] < nums[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
    return max(dp)
''',
        "patience_bisect": '''import bisect


def solve(nums):
    tails = []
    for x in nums:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)
''',
        "fenwick": '''def solve(nums):
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(nums)))}
    m = len(ranks)
    tree = [0] * (m + 1)
    best = 0
    for x in nums:
        r = ranks[x] - 1
        q = 0
        while r > 0:
            if tree[r] > q:
                q = tree[r]
            r -= r & -r
        cur = q + 1
        if cur > best:
            best = cur
        i = ranks[x]
        while i <= m:
            if tree[i] < cur:
                tree[i] = cur
            i += i & -i
    return best
''',
    },
    "T13": {
        "sort_sweep": '''def solve(intervals):
    merged = []
    for s, e in sorted(intervals):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged
''',
        "interval_tree": '''import random


class Node:
    __slots__ = ("start", "end", "max_end", "left", "right", "alive")

    def __init__(self, start, end):
        self.start, self.end, self.max_end = start, end, end
        self.left = self.right = None
        self.alive = True


def insert(root, node):
    if root is None:
        return node
    cur = root
    while True:
        if node.end > cur.max_end:
            cur.max_end = node.end
        if node.start < cur.start:
            if cur.left is None:
                cur.left = node
                return root
            cur = cur.left
        else:
            if cur.right is None:
                cur.right = node
                return root
            cur = cur.right


def find_overlap(root, s, e):
    stack = [root] if root else []
    while stack:
        node = stack.pop()
        if node is None or node.max_end < s:
            continue
        if node.alive and node.start <= e and node.end >= s:
            return node
        stack.append(node.left)
        if node.start <= e:
            stack.append(node.right)
    return None


def solve(intervals):
    order = [list(iv) for iv in intervals]
    random.shuffle(order)
    root = None
    for s, e in order:
        hit = find_overlap(root, s, e)
        while hit is not None:
            hit.alive = False
            s, e = min(s, hit.start), max(e, hit.end)
            hit = find_overlap(root, s, e)
        root = insert(root, Node(s, e))
    out = []
    stack, node = [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if node.alive:
            out.append([node.start, node.end])
        node = node.right
    return out
''',
        "union_find": '''def solve(intervals):
    n = len(intervals)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        si, ei = intervals[i]
        for j in range(i + 1, n):
            sj, ej = intervals[j]
            if si <= ej and sj <= ei:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups = {}
    for i in range(n):
        r = find(i)
        s, e = intervals[i]
        if r in groups:
            groups[r][0] = min(groups[r][0], s)
            groups[r][1] = max(groups[r][1], e)
        else:
            groups[r] = [s, e]
    return sorted(groups.values())
''',
    },
    "T14": {
        "sort_by_count": '''from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [v for v, _ in items[:k]]
''',
        "heap": '''import heapq
from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    heap = []
    for v, c in counts.items():
        heapq.heappush(heap, (c, v))
        if len(heap) > k:
            heapq.heappop(heap)
    return [v for _, v in heap]
''',
        "bucket_sort": '''from collections import Counter


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
''',
        "quickselect_counts": '''import random
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
''',
    },
    "R1": {
        "greedy_end": '''def solve(intervals):
    kept = 0
    last_end = None
    for s, e in sorted(intervals, key=lambda iv: iv[1]):
        if last_end is None or s >= last_end:
            kept += 1
            last_end = e
    return len(intervals) - kept
''',
        "dp_bisect": '''import bisect


def solve(intervals):
    iv = sorted(intervals, key=lambda x: x[1])
    ends = [e for _, e in iv]
    n = len(iv)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        s, e = iv[i - 1]
        j = bisect.bisect_right(ends, s, 0, i - 1)
        dp[i] = max(dp[i - 1], dp[j] + 1)
    return n - dp[n]
''',
        "memo_recursion": '''import bisect
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
''',
        "dag_longest_path": '''def solve(intervals):
    iv = sorted(intervals)
    n = len(iv)
    longest = [1] * n
    for j in range(n):
        for i in range(j):
            if iv[i][1] <= iv[j][0] and longest[i] + 1 > longest[j]:
                longest[j] = longest[i] + 1
    return n - max(longest)
''',
    },
    "R2": {
        "dfs_parent": '''def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n

    def dfs(u, parent):
        seen[u] = True
        for v in adj[u]:
            if v == parent:
                continue
            if seen[v] or dfs(v, u):
                return True
        return False

    for s in range(n):
        if not seen[s] and dfs(s, -1):
            return True
    return False
''',
        "bfs_parent": '''from collections import deque


def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [-2] * n
    for s in range(n):
        if parent[s] != -2:
            continue
        parent[s] = -1
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v == parent[u]:
                    continue
                if parent[v] != -2:
                    return True
                parent[v] = u
                q.append(v)
    return False
''',
        "union_find": '''def solve(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        a, b = find(u), find(v)
        if a == b:
            return True
        parent[a] = b
    return False
''',
        "edge_count": '''def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    comp = [-1] * n
    c = 0
    for s in range(n):
        if comp[s] != -1:
            continue
        comp[s] = c
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if comp[v] == -1:
                    comp[v] = c
                    stack.append(v)
        c += 1
    nodes = [0] * c
    edge_cnt = [0] * c
    for u in range(n):
        nodes[comp[u]] += 1
    for u, v in edges:
        edge_cnt[comp[u]] += 1
    return any(edge_cnt[i] >= nodes[i] for i in range(c))
''',
    },
    "R3": {
        "kahn": '''from collections import deque


def solve(n, prerequisites):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for a, b in prerequisites:
        adj[b].append(a)
        indeg[a] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return order if len(order) == n else []
''',
        "dfs_postorder": '''def solve(n, prerequisites):
    adj = [[] for _ in range(n)]
    for a, b in prerequisites:
        adj[b].append(a)
    color = [0] * n
    post = []

    def dfs(u):
        color[u] = 1
        for v in adj[u]:
            if color[v] == 1:
                return False
            if color[v] == 0 and not dfs(v):
                return False
        color[u] = 2
        post.append(u)
        return True

    for u in range(n):
        if color[u] == 0 and not dfs(u):
            return []
    return post[::-1]
''',
        "source_removal": '''def solve(n, prerequisites):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for a, b in prerequisites:
        adj[b].append(a)
        indeg[a] += 1
    done = [False] * n
    order = []
    for _ in range(n):
        u = next((v for v in range(n) if not done[v] and indeg[v] == 0), -1)
        if u == -1:
            return []
        done[u] = True
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
    return order
''',
        "layering": '''def solve(n, prerequisites):
    depth = [0] * n
    for _ in range(n):
        changed = False
        for a, b in prerequisites:
            if depth[b] + 1 > depth[a]:
                depth[a] = depth[b] + 1
                changed = True
        if not changed:
            return sorted(range(n), key=lambda u: depth[u])
    return []
''',
    },
    "R6": {
        "binary_search": '''def solve(nums, target):
    def lower(x):
        lo, hi = 0, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    first = lower(target)
    if first == len(nums) or nums[first] != target:
        return [-1, -1]
    return [first, lower(target + 1) - 1]
''',
        "bisect_module": '''import bisect


def solve(nums, target):
    i = bisect.bisect_left(nums, target)
    if i == len(nums) or nums[i] != target:
        return [-1, -1]
    return [i, bisect.bisect_right(nums, target) - 1]
''',
        "exponential_search": '''def solve(nums, target):
    n = len(nums)

    def lower(x):
        if n == 0 or nums[0] >= x:
            return 0
        bound = 1
        while bound < n and nums[bound] < x:
            bound *= 2
        lo, hi = bound // 2 + 1, min(bound, n)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    first = lower(target)
    if first == n or nums[first] != target:
        return [-1, -1]
    return [first, lower(target + 1) - 1]
''',
    },
}

MUTANTS = {
    "T03": ["def solve(nums, k):\n    return sorted(nums)[k]\n",
            "def solve(nums, k):\n    return sorted(set(nums))[min(k, len(set(nums))) - 1]\n",
            "def solve(nums, k):\n    return sorted(nums)[-k]\n"],
    "T04": ["def solve(haystack, needle):\n    for i in range(len(haystack) - len(needle)):\n        if haystack[i:i+len(needle)] == needle:\n            return i\n    return -1\n",
            "def solve(haystack, needle):\n    return haystack.rfind(needle)\n",
            "def solve(haystack, needle):\n    return haystack.find(needle) if len(needle) > 1 else -1\n"],
    "T05": ["def solve(nums, target):\n    for i in range(len(nums)):\n        for j in range(i, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n",
            "def solve(nums, target):\n    seen = {x: i for i, x in enumerate(nums)}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [i, seen[target - x]]\n",
            "def solve(nums, target):\n    for i in range(len(nums) - 1):\n        if nums[i] + nums[i + 1] == target:\n            return [i, i + 1]\n    return [0, 1]\n"],
    "T06": ["def solve(nums):\n    return sum(nums) - (len(nums) - 1) * len(nums) // 2\n",
            "def solve(nums):\n    a = sorted(nums)\n    for i in range(1, len(a) - 1):\n        if a[i] == a[i + 1]:\n            return a[i]\n    return a[-1]\n",
            "def solve(nums):\n    x = 0\n    for i, v in enumerate(nums):\n        x ^= i ^ v\n    return x\n"],
    "T08": ["import math\ndef solve(n):\n    p = (1 + 5 ** 0.5) / 2\n    return round(p ** n / 5 ** 0.5)\n",
            "def solve(n):\n    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
            "def solve(n):\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b if n else 1\n"],
    "T10": ["def solve(n, edges):\n    return n - len(edges)\n",
            "def solve(n, edges):\n    nodes = set()\n    for u, v in edges:\n        nodes.add(u); nodes.add(v)\n    parent = {x: x for x in nodes}\n    def f(x):\n        while parent[x] != x:\n            x = parent[x]\n        return x\n    c = len(nodes)\n    for u, v in edges:\n        a, b = f(u), f(v)\n        if a != b:\n            parent[a] = b; c -= 1\n    return c\n",
            "def solve(n, edges):\n    label = list(range(n))\n    for u, v in edges:\n        m = min(label[u], label[v]); label[u] = label[v] = m\n    return len(set(label))\n"],
    "T11": ["import bisect\ndef solve(nums):\n    t = []\n    for x in nums:\n        i = bisect.bisect_right(t, x)\n        if i == len(t): t.append(x)\n        else: t[i] = x\n    return len(t)\n",
            "def solve(nums):\n    best = cur = 1\n    for i in range(1, len(nums)):\n        cur = cur + 1 if nums[i] > nums[i-1] else 1\n        best = max(best, cur)\n    return best\n",
            "def solve(nums):\n    return len(set(nums))\n"],
    "T13": ["def solve(intervals):\n    out = []\n    for s, e in sorted(intervals):\n        if out and s < out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n        else:\n            out.append([s, e])\n    return out\n",
            "def solve(intervals):\n    out = []\n    for s, e in sorted(intervals):\n        if out and s <= out[-1][1]:\n            out[-1][1] = e\n        else:\n            out.append([s, e])\n    return out\n",
            "def solve(intervals):\n    out = []\n    for s, e in intervals:\n        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n        else:\n            out.append([s, e])\n    return out\n"],
    "T14": ["from collections import Counter\ndef solve(nums, k):\n    return [v for v, _ in Counter(nums).most_common(k + 1)][:k][::-1][:max(k - 1, 1)] if k > 1 else [nums[0]]\n",
            "def solve(nums, k):\n    return sorted(set(nums))[:k]\n",
            "from collections import Counter\ndef solve(nums, k):\n    c = Counter(nums)\n    return sorted(c, key=lambda v: c[v])[:k]\n"],
    "R1": ["def solve(intervals):\n    kept, last = 0, None\n    for s, e in sorted(intervals):\n        if last is None or s >= last:\n            kept += 1; last = e\n    return len(intervals) - kept\n",
           "def solve(intervals):\n    kept, last = 0, None\n    for s, e in sorted(intervals, key=lambda x: x[1]):\n        if last is None or s > last:\n            kept += 1; last = e\n    return len(intervals) - kept\n",
           "def solve(intervals):\n    iv = sorted(intervals)\n    return sum(1 for i in range(1, len(iv)) if iv[i][0] < iv[i-1][1])\n"],
    "R2": ["def solve(n, edges):\n    return len(edges) >= n\n",
           "def solve(n, edges):\n    seen = set()\n    for u, v in edges:\n        if u in seen and v in seen:\n            return True\n        seen.add(u); seen.add(v)\n    return False\n",
           "def solve(n, edges):\n    deg = [0] * n\n    for u, v in edges:\n        deg[u] += 1; deg[v] += 1\n    return any(d > 2 for d in deg)\n"],
    "R3": ["def solve(n, prerequisites):\n    return list(range(n))\n",
           "from collections import deque\ndef solve(n, prerequisites):\n    adj=[[] for _ in range(n)]; ind=[0]*n\n    for a,b in prerequisites: adj[b].append(a); ind[a]+=1\n    q=deque(i for i in range(n) if ind[i]==0); out=[]\n    while q:\n        u=q.popleft(); out.append(u)\n        for v in adj[u]:\n            ind[v]-=1\n            if ind[v]==0: q.append(v)\n    return out\n",
           "def solve(n, prerequisites):\n    adj=[[] for _ in range(n)]\n    for a,b in prerequisites: adj[b].append(a)\n    seen=[False]*n; post=[]\n    def dfs(u):\n        seen[u]=True\n        for v in adj[u]:\n            if not seen[v]: dfs(v)\n        post.append(u)\n    for u in range(n):\n        if not seen[u]: dfs(u)\n    return post[::-1]\n"],
    "R6": ["import bisect\ndef solve(nums, target):\n    i = bisect.bisect_left(nums, target)\n    if i == len(nums) or nums[i] != target:\n        return [-1, -1]\n    return [i, bisect.bisect_right(nums, target)]\n",
           "def solve(nums, target):\n    if target in nums:\n        i = nums.index(target)\n        return [i, i]\n    return [-1, -1]\n",
           "import bisect\ndef solve(nums, target):\n    i = bisect.bisect_left(nums, target)\n    return [i, bisect.bisect_right(nums, target) - 1]\n"],
}
