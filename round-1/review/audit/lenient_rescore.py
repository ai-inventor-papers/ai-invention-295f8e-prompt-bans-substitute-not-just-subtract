"""Re-score grid-task programs of the association experiment with one change: a None return is read as [].

Everything else follows the artifact's checker (tasks/tests_gen.py:check_t1, copied below) and its per-case limits.
Prints, per condition, the strict and lenient pass counts of programs labelled DFS / BFS.
"""
import json
import multiprocessing as mp
import signal
import sys
from collections import Counter, defaultdict
from common import ART, rows, truthy

TASK = ART / "experiment-1/src/tasks/t1_grid"
TESTS = json.load(open(TASK / "tests.json"))
LIMITS = json.load(open(TASK / "limits.json"))["limits"]


def check_t1(case, out):
    grid = case["grid"]; start = tuple(case["start"]); goal = tuple(case["goal"])
    rows_, cols = len(grid), len(grid[0])
    if not isinstance(out, (list, tuple)):
        return False
    if not case["reachable"]:
        return len(out) == 0
    if len(out) == 0:
        return False
    try:
        path = [(int(p[0]), int(p[1])) for p in out]
        if any(len(p) != 2 for p in out):
            return False
    except (TypeError, ValueError, IndexError):
        return False
    if path[0] != start or path[-1] != goal:
        return False
    for (r, c) in path:
        if not (0 <= r < rows_ and 0 <= c < cols) or grid[r][c] != ".":
            return False
    for (a, b), (c, d) in zip(path, path[1:]):
        if abs(a - c) + abs(b - d) != 1:
            return False
    return True


class TO(Exception):
    pass


def _alarm(*_):
    raise TO()


def run_one(code):
    signal.signal(signal.SIGALRM, _alarm)
    ns = {}
    try:
        exec(code, ns)
        solve = ns["solve"]
    except Exception:
        return (False, False)
    strict_ok = lenient_ok = True
    for case in TESTS:
        lim = LIMITS.get(case["id"], 1.0)
        signal.setitimer(signal.ITIMER_REAL, lim)
        try:
            out = solve([row for row in case["grid"]], tuple(case["start"]), tuple(case["goal"]))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except BaseException:
            signal.setitimer(signal.ITIMER_REAL, 0)
            return (False, False)
        s = check_t1(case, out)
        l = check_t1(case, [] if out is None else out)
        strict_ok &= s
        lenient_ok &= l
    return (strict_ok, lenient_ok)


def worker(code, q):
    try:
        q.put(run_one(code))
    except BaseException:
        q.put((False, False))


def score(code):
    q = mp.Queue()
    p = mp.Process(target=worker, args=(code, q))
    p.start()
    p.join(90)
    if p.is_alive():
        p.kill()
        return (False, False)
    try:
        return q.get_nowait()
    except Exception:
        return (False, False)


if __name__ == "__main__":
    conds = sys.argv[1:] or ["ban:bfs", "succession:2", "mention:dfs"]
    R = [r for r in rows(ART / "experiment-1/src/data/samples.jsonl") if r["task"] == "t1" and r["condition"] in conds]
    res = defaultdict(Counter)
    agree = Counter()
    for r in R:
        s, l = score(r["code"])
        agree[(truthy(r["passed"]), s)] += 1
        res[(r["condition"], r["label"])]["n"] += 1
        res[(r["condition"], r["label"])]["strict"] += s
        res[(r["condition"], r["label"])]["lenient"] += l
    print("agreement (artifact passed, my strict):", dict(agree))
    for k, v in sorted(res.items()):
        print(k, dict(v))
