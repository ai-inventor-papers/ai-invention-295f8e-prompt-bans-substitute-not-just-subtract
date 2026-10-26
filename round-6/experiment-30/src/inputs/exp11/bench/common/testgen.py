"""Hidden tests per task: parsed LeetCodeDataset cases (status 'ok', converted to the solve() signature,
filtered to the spec bounds) + generated edge cases + stress cases at the bounds, all with oracle outputs.
"""

from __future__ import annotations

import bisect
import json
import random
from collections import Counter, deque
from pathlib import Path

MAX_PARSED = 45  # parsed cases kept per task (all in-bound ones up to this cap, in dataset order)


# ----------------------------------------------------------------------------- oracles
def fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def n_components(n, edges):
    p = list(range(n))

    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    c = n
    for u, v in edges:
        a, b = f(u), f(v)
        if a != b:
            p[a] = b
            c -= 1
    return c


def has_cycle(n, edges):
    p = list(range(n))

    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    for u, v in edges:
        a, b = f(u), f(v)
        if a == b:
            return True
        p[a] = b
    return False


def lis_len(nums):
    t = []
    for x in nums:
        i = bisect.bisect_left(t, x)
        if i == len(t):
            t.append(x)
        else:
            t[i] = x
    return len(t)


def merge_iv(iv):
    out = []
    for s, e in sorted(iv):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def min_removals(iv):
    kept, last = 0, None
    for s, e in sorted(iv, key=lambda x: x[1]):
        if last is None or s >= last:
            kept += 1
            last = e
    return len(iv) - kept


def topo(n, pre):
    adj = [[] for _ in range(n)]
    ind = [0] * n
    for a, b in pre:
        adj[b].append(a)
        ind[a] += 1
    q = deque(i for i in range(n) if ind[i] == 0)
    out = []
    while q:
        u = q.popleft()
        out.append(u)
        for v in adj[u]:
            ind[v] -= 1
            if ind[v] == 0:
                q.append(v)
    return out if len(out) == n else []


def first_last(nums, t):
    i = bisect.bisect_left(nums, t)
    if i == len(nums) or nums[i] != t:
        return [-1, -1]
    return [i, bisect.bisect_right(nums, t) - 1]


def two_sum_pairs(nums, target):
    seen = Counter()
    cnt = 0
    for x in nums:
        cnt += seen[target - x]
        seen[x] += 1
    return cnt


def two_sum_ans(nums, target):
    pos = {}
    for j, x in enumerate(nums):
        if target - x in pos:
            return [pos[target - x], j]
        pos.setdefault(x, j)
    return None


def topk_unique(nums, k):
    c = Counter(nums)
    vals = sorted(c.values(), reverse=True)
    if k < len(vals) and vals[k - 1] == vals[k]:
        return None
    return sorted(v for v, _ in sorted(c.items(), key=lambda x: -x[1])[:k])


ORACLE = {
    "T03": lambda kw: sorted(kw["nums"])[kw["k"] - 1],
    "T04": lambda kw: kw["haystack"].find(kw["needle"]),
    "T05": lambda kw: two_sum_ans(kw["nums"], kw["target"]),
    "T06": lambda kw: [v for v, c in Counter(kw["nums"]).items() if c > 1][0],
    "T08": lambda kw: fib(kw["n"]),
    "T10": lambda kw: n_components(kw["n"], kw["edges"]),
    "T11": lambda kw: lis_len(kw["nums"]),
    "T13": lambda kw: merge_iv(kw["intervals"]),
    "T14": lambda kw: topk_unique(kw["nums"], kw["k"]),
    "R1": lambda kw: min_removals(kw["intervals"]),
    "R2": lambda kw: has_cycle(kw["n"], kw["edges"]),
    "R3": lambda kw: topo(kw["n"], kw["prerequisites"]),
    "R6": lambda kw: first_last(kw["nums"], kw["target"]),
}


# ----------------------------------------------------------------------------- bounds
def in_bounds(task: str, kw: dict) -> bool:
    if task == "T03":
        n = len(kw["nums"])
        return 1 <= n <= 2000 and all(-10**4 <= v <= 10**4 for v in kw["nums"]) and 1 <= kw["k"] <= n
    if task == "T04":
        h, nd = kw["haystack"], kw["needle"]
        return 1 <= len(h) <= 2000 and 1 <= len(nd) <= 200 and (h + nd).isalpha() and (h + nd).islower()
    if task == "T05":
        n = len(kw["nums"])
        return 2 <= n <= 2000 and all(-10**9 <= v <= 10**9 for v in kw["nums"]) and \
            two_sum_pairs(kw["nums"], kw["target"]) == 1
    if task == "T06":
        a = kw["nums"]
        n = len(a) - 1
        c = Counter(a)
        return 1 <= n <= 10**4 and all(1 <= v <= n for v in a) and sum(1 for v in c.values() if v > 1) == 1
    if task == "T08":
        return 0 <= kw["n"] <= 500
    if task == "T10":
        n, e = kw["n"], kw["edges"]
        s = {tuple(sorted(x)) for x in e}
        return 1 <= n <= 300 and 0 <= len(e) <= 1500 and len(s) == len(e) and all(
            0 <= u < n and 0 <= v < n and u != v for u, v in e)
    if task == "T11":
        return 1 <= len(kw["nums"]) <= 1000 and all(-10**4 <= v <= 10**4 for v in kw["nums"])
    if task == "T13":
        iv = kw["intervals"]
        return 1 <= len(iv) <= 1500 and all(0 <= s <= e <= 10**4 for s, e in iv)
    if task == "T14":
        a = kw["nums"]
        return 1 <= len(a) <= 10**4 and all(-10**4 <= v <= 10**4 for v in a) and \
            1 <= kw["k"] <= len(set(a)) and topk_unique(a, kw["k"]) is not None
    if task == "R1":
        iv = kw["intervals"]
        return 1 <= len(iv) <= 1000 and all(-5 * 10**4 <= s < e <= 5 * 10**4 for s, e in iv)
    if task == "R2":
        n, e = kw["n"], kw["edges"]
        s = {tuple(sorted(x)) for x in e}
        return 1 <= n <= 1000 and 0 <= len(e) <= 2000 and len(s) == len(e) and all(
            0 <= u < n and 0 <= v < n and u != v for u, v in e)
    if task == "R3":
        n, e = kw["n"], kw["prerequisites"]
        return 1 <= n <= 500 and 0 <= len(e) <= 2000 and len({tuple(x) for x in e}) == len(e) and all(
            0 <= a < n and 0 <= b < n and a != b for a, b in e)
    if task == "R6":
        a = kw["nums"]
        return 0 <= len(a) <= 10**5 and all(a[i] <= a[i + 1] for i in range(len(a) - 1)) and \
            all(-10**9 <= v <= 10**9 for v in a) and -10**9 <= kw["target"] <= 10**9
    raise KeyError(task)


# ----------------------------------------------------------------------------- conversion of parsed cases
def convert(task: str, qid: int, kw: dict) -> dict | None:
    if task == "T03":
        n = len(kw["nums"])
        return {"nums": kw["nums"], "k": n - kw["k"] + 1}
    if task == "T04":
        return {"haystack": kw["haystack"], "needle": kw["needle"]}
    if task in ("T05", "R6"):
        return {"nums": kw["nums"], "target": kw["target"]}
    if task in ("T06", "T11"):
        return {"nums": kw["nums"]}
    if task == "T08":
        return {"n": kw["n"]}
    if task == "T10":
        if qid == 547:
            m = kw["isConnected"]
            n = len(m)
            return {"n": n, "edges": [[i, j] for i in range(n) for j in range(i + 1, n) if m[i][j] == 1]}
        return {"n": kw["n"], "edges": kw["edges"]}
    if task in ("T13", "R1"):
        return {"intervals": kw["intervals"]}
    if task == "T14":
        return {"nums": kw["nums"], "k": kw["k"]}
    if task == "R2":  # LC684: n edges on nodes 1..n, always exactly one redundant edge -> a cycle
        e = kw["edges"]
        return {"n": len(e), "edges": [[u - 1, v - 1] for u, v in e]}
    if task == "R3":
        return {"n": kw["numCourses"], "prerequisites": kw["prerequisites"]}
    raise KeyError(task)


# ----------------------------------------------------------------------------- generators
def _rand_graph(rng, n, m, connected_tree=False):
    s = set()
    edges = []
    if connected_tree:
        for v in range(1, n):
            u = rng.randrange(v)
            s.add((u, v))
            edges.append([u, v])
    tries = 0
    while len(edges) < m and tries < 50 * m + 100:
        tries += 1
        u, v = rng.randrange(n), rng.randrange(n)
        if u == v:
            continue
        a, b = min(u, v), max(u, v)
        if (a, b) in s:
            continue
        s.add((a, b))
        edges.append([u, v])
    return edges


def _forest(rng, n, n_trees):
    order = list(range(n))
    rng.shuffle(order)
    roots = set(order[:n_trees])
    edges = []
    placed = []
    for v in order:
        if v in roots or not placed:
            placed.append(v)
            continue
        u = rng.choice(placed)
        edges.append([u, v] if rng.random() < 0.5 else [v, u])
        placed.append(v)
    return edges


def gen_cases(task: str, rng: random.Random) -> list[tuple[str, dict]]:
    """Return [(kind, kwargs)] with kind in {edge, stress}."""
    out = []
    E, S = "edge", "stress"
    if task == "T03":
        out += [(E, {"nums": [5], "k": 1}), (E, {"nums": [2, 2, 2, 2], "k": 3}), (E, {"nums": [3, 1, 3], "k": 3}),
                (E, {"nums": [-10000, 10000], "k": 2}), (E, {"nums": [1, 2], "k": 1})]
        asc = sorted(rng.randint(-10**4, 10**4) for _ in range(2000))
        out += [(S, {"nums": asc, "k": 1}), (S, {"nums": asc, "k": 2000}), (S, {"nums": asc, "k": 1000}),
                (S, {"nums": asc[::-1], "k": 1}), (S, {"nums": asc[::-1], "k": 1500}),
                (S, {"nums": [7] * 2000, "k": 999}),
                (S, {"nums": [rng.randint(-3, 3) for _ in range(2000)], "k": 1234}),
                (S, {"nums": [rng.randint(-10**4, 10**4) for _ in range(2000)], "k": 17}),
                (S, {"nums": [rng.randint(-10**4, 10**4) for _ in range(2000)], "k": 1999}),
                (S, {"nums": [rng.choice([-10**4, 10**4]) for _ in range(2000)], "k": 1000})]
    elif task == "T04":
        a = lambda n, al="ab": "".join(rng.choice(al) for _ in range(n))  # noqa: E731
        out += [(E, {"haystack": "a", "needle": "a"}), (E, {"haystack": "a", "needle": "b"}),
                (E, {"haystack": "abc", "needle": "abcd"}), (E, {"haystack": "abcabd", "needle": "abd"}),
                (E, {"haystack": "aaaaa", "needle": "aa"}), (E, {"haystack": "mississippi", "needle": "issip"}),
                (E, {"haystack": "abababc", "needle": "ababc"}), (E, {"haystack": "xyz", "needle": "z"})]
        out += [(S, {"haystack": "a" * 1999 + "b", "needle": "a" * 199 + "b"}),
                (S, {"haystack": "a" * 2000, "needle": "a" * 199 + "b"}),
                (S, {"haystack": "ab" * 1000, "needle": "ab" * 99 + "bb"}),
                (S, {"haystack": a(2000), "needle": a(12)}),
                (S, {"haystack": a(2000, "abcdefghijklmnopqrstuvwxyz"), "needle": a(200, "abcdefghijklmnopqrstuvwxyz")}),
                (S, {"haystack": "a" * 1800 + "b" * 200, "needle": "a" * 100 + "b" * 100})]
        h = a(2000, "abc")
        out.append((S, {"haystack": h, "needle": h[1700:1900]}))
    elif task == "T05":
        out += [(E, {"nums": [3, 3], "target": 6}), (E, {"nums": [1, 2], "target": 3}),
                (E, {"nums": [-1, -2, -3, -4, -5], "target": -8}), (E, {"nums": [0, 4, 3, 0], "target": 0}),
                (E, {"nums": [10**9, -10**9, 5], "target": 0}), (E, {"nums": [10**9, 10**9 - 1, 1], "target": 2 * 10**9 - 1})]
        for n, where in [(2000, "end"), (2000, "start"), (2000, "mid"), (1500, "end"), (2000, "split")]:
            for _ in range(50):
                vals = rng.sample(range(-10**9, 10**9, 7), n)
                if where == "end":
                    i, j = n - 2, n - 1
                elif where == "start":
                    i, j = 0, 1
                elif where == "mid":
                    i, j = n // 2, n // 2 + 1
                else:
                    i, j = 0, n - 1
                target = vals[i] + vals[j]
                if two_sum_pairs(vals, target) == 1:
                    out.append((S, {"nums": vals, "target": target}))
                    break
        dup = [rng.randint(-50, 50) * 2 for _ in range(1998)]
        # one odd-sum pair among even values -> unique by parity
        cand = dup + [3, 10**5 + 1]
        rng.shuffle(cand)
        if two_sum_pairs(cand, 10**5 + 4) == 1:
            out.append((S, {"nums": cand, "target": 10**5 + 4}))
    elif task == "T06":
        out += [(E, {"nums": [1, 1]}), (E, {"nums": [2, 2, 2]}), (E, {"nums": [1, 3, 4, 2, 2]}),
                (E, {"nums": [3, 1, 3, 4, 2]}), (E, {"nums": [2, 2, 2, 2, 2]}), (E, {"nums": [1, 4, 4, 2, 4]})]
        for n, reps, d in [(10**4, 2, 1), (10**4, 2, 10**4), (10**4, 5000, 777), (10**4, 2, 5000), (9999, 3, 1234),
                           (10**4, 10001, 42)]:
            vals = list(range(1, n + 1))
            vals.remove(d)
            rng.shuffle(vals)
            keep = vals[: n + 1 - reps]
            arr = keep + [d] * reps
            rng.shuffle(arr)
            out.append((S, {"nums": arr}))
    elif task == "T08":
        for n in [0, 1, 2, 3, 10, 30, 50, 70, 71, 72, 75, 79, 80, 90, 93, 100, 128, 150, 200, 255, 256, 300, 400,
                  499, 500]:
            out.append((E if n <= 30 else S, {"n": n}))
    elif task == "T10":
        out += [(E, {"n": 1, "edges": []}), (E, {"n": 5, "edges": []}), (E, {"n": 2, "edges": [[0, 1]]}),
                (E, {"n": 4, "edges": [[0, 1], [2, 3]]}), (E, {"n": 3, "edges": [[0, 1], [1, 2], [0, 2]]})]
        out += [(S, {"n": 300, "edges": [[i, i + 1] for i in range(299)]}),
                (S, {"n": 300, "edges": [[i + 1, i] for i in range(298, -1, -1)]}),
                (S, {"n": 300, "edges": [[0, i] for i in range(1, 300)]}),
                (S, {"n": 300, "edges": _rand_graph(rng, 300, 1500)}),
                (S, {"n": 300, "edges": _rand_graph(rng, 300, 150)}),
                (S, {"n": 300, "edges": _forest(rng, 300, 37)}),
                (S, {"n": 300, "edges": _rand_graph(rng, 60, 1200)}),
                (S, {"n": 299, "edges": _forest(rng, 299, 1)})]
    elif task == "T11":
        out += [(E, {"nums": [5]}), (E, {"nums": [2, 2, 2]}), (E, {"nums": [1, 2]}), (E, {"nums": [2, 1]}),
                (E, {"nums": [-10000, 10000, -10000, 10000]}), (E, {"nums": [10, 9, 2, 5, 3, 7, 101, 18]})]
        out += [(S, {"nums": list(range(-500, 500))}), (S, {"nums": list(range(500, -500, -1))}),
                (S, {"nums": [rng.randint(-10**4, 10**4) for _ in range(1000)]}),
                (S, {"nums": [rng.randint(0, 5) for _ in range(1000)]}),
                (S, {"nums": [i // 2 for i in range(1000)]}),
                (S, {"nums": [rng.randint(-10**4, 10**4) for _ in range(200)]}),
                (S, {"nums": [(i * 7919) % 1000 for i in range(1000)]})]
    elif task == "T13":
        out += [(E, {"intervals": [[1, 3]]}), (E, {"intervals": [[1, 3], [3, 5]]}), (E, {"intervals": [[5, 5], [5, 5]]}),
                (E, {"intervals": [[4, 7], [1, 4]]}), (E, {"intervals": [[1, 10], [2, 3], [4, 5]]}),
                (E, {"intervals": [[0, 0], [1, 1], [2, 2]]}), (E, {"intervals": [[2, 3], [0, 1], [1, 2], [5, 6]]})]
        def rnd_iv(n, w):
            r = []
            for _ in range(n):
                s = rng.randint(0, 10**4)
                r.append([s, min(10**4, s + rng.randint(0, w))])
            return r
        out += [(S, {"intervals": [[i, i + 1] for i in range(0, 1500)]}),
                (S, {"intervals": [[2 * i, 2 * i] for i in range(1500)][::-1]}),
                (S, {"intervals": rnd_iv(1500, 3)}), (S, {"intervals": rnd_iv(1500, 30)}),
                (S, {"intervals": rnd_iv(800, 2000)}), (S, {"intervals": rnd_iv(1000, 8)}),
                (S, {"intervals": [[0, 10**4]] + rnd_iv(1499, 5)})]
    elif task == "T14":
        out += [(E, {"nums": [1], "k": 1}), (E, {"nums": [1, 1, 1, 2, 2, 3], "k": 2}), (E, {"nums": [-1, -1, 4], "k": 1}),
                (E, {"nums": [5, 6, 7, 5, 6, 5], "k": 3})]
        for n_distinct, k in [(140, 10), (140, 1), (140, 139), (1000, 7), (60, 30)]:
            vals = rng.sample(range(-10**4, 10**4 + 1), n_distinct)
            counts = rng.sample(range(1, 145), n_distinct) if n_distinct <= 144 else None
            if counts is None:
                counts = [rng.randint(1, 9) for _ in range(n_distinct)]
                for i in range(k):
                    counts[i] = 10 + i
            arr = []
            for v, c in zip(vals, counts):
                arr += [v] * c
            arr = arr[:10**4]
            rng.shuffle(arr)
            kw = {"nums": arr, "k": k}
            if topk_unique(arr, k) is not None:
                out.append((S, kw))
        out += [(E, {"nums": [5] * 10, "k": 1}), (E, {"nums": [-10000, 10000, 10000], "k": 1}),
                (E, {"nums": [3, 1, 1, 2, 2, 2], "k": 3}), (E, {"nums": [0, -1, -1, -2, -2, -2, 7], "k": 2}),
                (E, {"nums": [4, 4, 4, 4, 9], "k": 2})]
        for n_distinct, k in [(100, 1), (100, 50), (100, 100), (30, 29), (12, 6)]:
            vals = rng.sample(range(-10**4, 10**4 + 1), n_distinct)
            counts = rng.sample(range(1, n_distinct + 1), n_distinct)
            arr = []
            for v, c in zip(vals, counts):
                arr += [v] * c
            rng.shuffle(arr)
            out.append((S, {"nums": arr, "k": k}))
        for n_top, k in [(20, 20), (5, 5), (60, 30)]:
            top = rng.sample(range(-10**4, 10**4 + 1), 1000)
            arr = []
            for i, v in enumerate(top):
                arr += [v] * ((40 + i) if i < n_top else rng.randint(1, 5))
            arr = arr[:10**4]
            rng.shuffle(arr)
            out.append((S, {"nums": arr, "k": k}))
    elif task == "R1":
        out += [(E, {"intervals": [[1, 2]]}), (E, {"intervals": [[1, 2], [2, 3]]}), (E, {"intervals": [[1, 2], [1, 2], [1, 2]]}),
                (E, {"intervals": [[1, 100], [11, 22], [1, 11], [2, 12]]}), (E, {"intervals": [[-50000, 50000], [0, 1]]}),
                (E, {"intervals": [[1, 2], [2, 3], [3, 4], [1, 3]]})]
        def rnd(n, w):
            r = []
            for _ in range(n):
                s = rng.randint(-5 * 10**4, 5 * 10**4 - 1)
                r.append([s, min(5 * 10**4, s + rng.randint(1, w))])
            return r
        out += [(S, {"intervals": [[i, i + 1] for i in range(1000)]}), (S, {"intervals": [[0, 5]] * 1000}),
                (S, {"intervals": rnd(1000, 100)}), (S, {"intervals": rnd(1000, 5000)}), (S, {"intervals": rnd(1000, 50)}),
                (S, {"intervals": [[i, 2000 - i] for i in range(1000)]})]
    elif task == "R2":
        out += [(E, {"n": 1, "edges": []}), (E, {"n": 2, "edges": [[0, 1]]}), (E, {"n": 3, "edges": [[0, 1], [1, 2], [2, 0]]}),
                (E, {"n": 4, "edges": [[0, 1], [2, 3]]}), (E, {"n": 5, "edges": [[0, 1], [3, 4], [4, 2], [2, 3]]}),
                (E, {"n": 6, "edges": [[0, 1], [1, 2], [3, 4]]})]
        tree = _forest(rng, 1000, 1)
        shuffled_tree = _forest(rng, 1000, 1)
        rng.shuffle(shuffled_tree)
        out += [(E, {"n": 4, "edges": [[0, 1], [2, 3], [1, 2]]}), (S, {"n": 1000, "edges": shuffled_tree}),(S, {"n": 1000, "edges": [[i, i + 1] for i in range(999)]}),
                (S, {"n": 1000, "edges": [[i, i + 1] for i in range(999)] + [[999, 0]]}),
                (S, {"n": 1000, "edges": tree}), (S, {"n": 1000, "edges": _forest(rng, 1000, 17)}),
                (S, {"n": 1000, "edges": _rand_graph(rng, 1000, 2000)}),
                (S, {"n": 1000, "edges": _forest(rng, 900, 3) + [[900, 901], [901, 902], [902, 900]]}),
                (S, {"n": 1000, "edges": [[i, i + 1] for i in range(500)] + [[600 + i, 601 + i] for i in range(398)] + [[998, 600]]})]
    elif task == "R3":
        out += [(E, {"n": 1, "prerequisites": []}), (E, {"n": 2, "prerequisites": [[1, 0]]}),
                (E, {"n": 2, "prerequisites": [[1, 0], [0, 1]]}), (E, {"n": 3, "prerequisites": []}),
                (E, {"n": 4, "prerequisites": [[1, 0], [2, 0], [3, 1], [3, 2]]}),
                (E, {"n": 3, "prerequisites": [[0, 1], [1, 2], [2, 0]]})]
        perm = list(range(500))
        rng.shuffle(perm)
        def dag(m):
            s, e = set(), []
            while len(e) < m:
                i, j = sorted(rng.sample(range(500), 2))
                if (i, j) not in s:
                    s.add((i, j))
                    e.append([perm[j], perm[i]])
            return e
        chain = [[perm[i + 1], perm[i]] for i in range(499)]
        d = dag(2000)
        out += [(S, {"n": 500, "prerequisites": chain}), (S, {"n": 500, "prerequisites": chain[::-1]}),
                (S, {"n": 500, "prerequisites": d}), (S, {"n": 500, "prerequisites": d[:-1] + [[d[0][1], d[0][0]]]}),
                (S, {"n": 500, "prerequisites": dag(600)}), (S, {"n": 500, "prerequisites": chain + [[perm[0], perm[499]]]})]
    elif task == "R6":
        out += [(E, {"nums": [], "target": 0}), (E, {"nums": [1], "target": 1}), (E, {"nums": [1], "target": 2}),
                (E, {"nums": [2, 2], "target": 2}), (E, {"nums": [1, 2, 3], "target": 0}), (E, {"nums": [1, 2, 3], "target": 4}),
                (E, {"nums": [5, 7, 7, 8, 8, 10], "target": 8})]
        big = sorted(rng.randint(-10**9, 10**9) for _ in range(10**5))
        runs = sorted(rng.randint(-50, 50) for _ in range(10**5))
        out += [(S, {"nums": [3] * 10**5, "target": 3}), (S, {"nums": big, "target": big[0]}),
                (S, {"nums": big, "target": big[-1]}), (S, {"nums": big, "target": big[54321] + 1}),
                (S, {"nums": runs, "target": 0}), (S, {"nums": runs, "target": 51}), (S, {"nums": runs, "target": -50}),
                (S, {"nums": list(range(10**5)), "target": 99999})]
    return out


def build_tests(task: str, parsed: list[tuple[str, int, dict]], seed: int) -> tuple[list[dict], dict]:
    """parsed: [(case_id, qid, raw kwargs)].  Returns (cases, provenance counts)."""
    rng = random.Random(seed)
    cases, prov = [], Counter()
    seen = set()
    for cid, qid, kw in parsed:
        ck = convert(task, qid, kw)
        if ck is None or not in_bounds(task, ck):
            prov["parsed_dropped_out_of_bounds"] += 1
            continue
        key = json.dumps(ck, sort_keys=True)
        if key in seen:
            prov["parsed_dropped_duplicate"] += 1
            continue
        if sum(1 for c in cases if c["kind"] == "parsed") >= MAX_PARSED:
            prov["parsed_dropped_cap"] += 1
            continue
        seen.add(key)
        cases.append({"case_id": cid, "kind": "parsed", "kwargs": ck})
    for i, (kind, kw) in enumerate(gen_cases(task, rng)):
        if not in_bounds(task, kw):
            prov[f"generated_{kind}_dropped_out_of_bounds"] += 1
            continue
        key = json.dumps(kw, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        cases.append({"case_id": f"gen:{task}:{kind}:{i}", "kind": kind, "kwargs": kw})
    for c in cases:
        c["expected"] = ORACLE[task](c["kwargs"])
        prov[c["kind"]] += 1
    return cases, dict(prov)


def write_tests(path: Path, cases: list[dict]) -> None:
    with path.open("w") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")


def read_tests(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open()]
