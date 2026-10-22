"""II2 task_scheduler (LeetCode 621; len(tasks) <= 10000, n <= 100). Simulation references process whole
(n + 1)-cycles so that they stay under 0.25 x the limit; per-time-step simulations may exceed it."""

from __future__ import annotations

import random
import string

from unitlib import ast_tree, calls_named, ccount, names_used, probe
from units.ii_common import calls_in_loops

CHECKER = "exact"
ARGS = ["tasks", "n"]

ORACLE_A = '''
def solve(tasks, n):
    from collections import Counter
    cnt = Counter(tasks)
    x = max(cnt.values())
    s = sum(v == x for v in cnt.values())
    return max(len(tasks), (x - 1) * (n + 1) + s)
'''  # dataset reference (LeetCode 621 row), adapted
ORACLE_B = '''
def solve(tasks, n):
    import heapq
    from collections import Counter, deque
    heap = [-c for c in Counter(tasks).values()]
    heapq.heapify(heap)
    wait = deque()
    time = 0
    while heap or wait:
        if not heap:
            time = wait[0][1]
        else:
            c = heapq.heappop(heap) + 1
            time += 1
            if c < 0:
                wait.append((c, time + n))
        while wait and wait[0][1] <= time:
            heapq.heappush(heap, wait.popleft()[0])
    return time
'''  # event-driven heap + cooldown queue (jumps over idle stretches), independent of the formula

REFERENCES = {
    "counting_formula": ORACLE_A,
    "heap_simulation": '''
def solve(tasks, n):
    import heapq
    from collections import Counter
    heap = [-c for c in Counter(tasks).values()]
    heapq.heapify(heap)
    time = 0
    while heap:
        tmp = []
        for _ in range(n + 1):
            if heap:
                tmp.append(heapq.heappop(heap))
        for c in tmp:
            if c + 1 < 0:
                heapq.heappush(heap, c + 1)
        time += n + 1 if heap else len(tmp)
    return time
''',
    "sorted_count_simulation": '''
def solve(tasks, n):
    counts = [0] * 26
    for t in tasks:
        counts[ord(t) - 65] += 1
    time = 0
    while True:
        counts.sort(reverse=True)
        if counts[0] == 0:
            return time
        used = 0
        for i in range(min(n + 1, 26)):
            if counts[i] == 0:
                break
            counts[i] -= 1
            used += 1
        time += n + 1 if any(counts) else used
''',
}
MUTANTS = [
    '''
def solve(tasks, n):
    from collections import Counter
    cnt = Counter(tasks)
    x = max(cnt.values())
    s = sum(v == x for v in cnt.values())
    return (x - 1) * (n + 1) + s
''',
    '''
def solve(tasks, n):
    from collections import Counter
    cnt = Counter(tasks)
    x = max(cnt.values())
    return max(len(tasks), (x - 1) * (n + 1) + 1)
''',
    '''
def solve(tasks, n):
    return len(tasks)
''',
]
EXCLUDED: dict[str, str] = {}

LETTERS = string.ascii_uppercase


def _tasks(rng: random.Random, m: int, k: int, skew: float) -> list[str]:
    letters = rng.sample(LETTERS, k)
    w = [skew ** i for i in range(k)]
    out = rng.choices(letters, weights=w, k=m)
    rng.shuffle(out)
    return out


def make_tests() -> list[dict]:
    rng = random.Random(621)
    cases = [("ex0", [["A", "A", "A", "B", "B", "B"], 2]), ("ex1", [["A", "A", "A", "B", "B", "B"], 0]),
             ("ex2", [["A", "A", "A", "A", "A", "A", "B", "C", "D", "E", "F", "G"], 2]),
             ("ex3", [["A", "C", "A", "B", "D", "B"], 1]), ("edge0", [["A"], 100]), ("edge1", [["A", "A"], 100]),
             ("edge2", [list(LETTERS), 25]), ("edge3", [list(LETTERS) * 2, 30])]
    i = 0
    while len(cases) < 8 + 60:
        m = rng.choice([1, 2, 5, 10, 30, 100, 500, 2000])
        k = rng.randint(1, 26)
        n = rng.choice([0, 1, 2, 3, 5, 10, 25, 50, 100])
        cases.append((f"rand{i}", [_tasks(rng, m, k, rng.choice([1.0, 0.8, 0.5])), n]))
        i += 1
    for j in range(10):
        k = [1, 2, 5, 26, 26, 13, 3, 26, 1, 7][j]
        n = [100, 100, 50, 0, 100, 7, 99, 25, 0, 60][j]
        cases.append((f"stress{j}", [_tasks(rng, 10000, k, [1.0, 0.9, 0.5][j % 3]), n]))
    return [{"case_id": f"II2:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe(name: str, n: int) -> dict:
    tasks = []
    for ch, c in zip("ABCDEF", (30, 25, 20, 20, 15, 10)):
        tasks += [ch] * c
    random.Random(5).shuffle(tasks)
    from collections import Counter
    cnt = Counter(tasks)
    x = max(cnt.values())
    s = sum(v == x for v in cnt.values())
    return {"name": name, "args": [tasks, n], "wrap": ["plain", "plain"],
            "expected": max(len(tasks), (x - 1) * (n + 1) + s)}


PROBES = [_probe("p_n2", 2), _probe("p_n50", 50)]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "p_n2"), probe(tr, "p_n50")
    if a is None or b is None or a.get("error") or b.get("error"):
        return None
    hp = ccount(a, "heappush", "heappop", "heapify", "heappushpop", "heapreplace", "nlargest") + \
        ccount(b, "heappush", "heappop", "heapify", "heappushpop", "heapreplace", "nlargest")
    so = ccount(a, "sorted", "list.sort") + ccount(b, "sorted", "list.sort")
    if hp >= 20:
        return "heap_simulation"
    if so >= 10:
        return "sorted_count_simulation"
    la, lb = int(a.get("lines") or 0), int(b.get("lines") or 0)
    if lb <= 2 * la + 200:
        return "counting_formula"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = names_used(t)
    if "heapq" in names or any(c in calls for c in ("heappush", "heappop", "heapify", "nlargest")):
        return "heap_simulation"
    loop_calls = calls_in_loops(t)
    if "sort" in loop_calls or "sorted" in loop_calls:
        return "sorted_count_simulation"
    if "max" in calls or "most_common" in calls:
        from unitlib import has_loop
        return "counting_formula"
    return "other"
