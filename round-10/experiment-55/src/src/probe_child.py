#!/usr/bin/env python3
"""Runtime probe CHILD (stdlib only; run as `python -I -S probe_child.py` with a JSON job on stdin).

For each (grid, seed) it execs the candidate in a fresh module, with
  * heapq replaced in sys.modules by a counting proxy (heappush / heappop / heapify counts),
  * grid rows wrapped in a str subclass that logs (row, col) reads (first 4,000 reads),
  * random.seed(seed) called before solve(),
  * optionally sys.settrace counting executions of the given line numbers of '<candidate>'.
It prints one JSON line {"results": [...]} with, per run: valid path flag, path length, heap counts, a sha256 of
the read sequence, the number of reads, the counted line hits and an exception string if any.
"""

import hashlib
import heapq as _real_heapq
import json
import random
import resource
import sys
import threading
import types


class Count:
    push = 0
    pop = 0
    reads = []
    lines = {}


def _proxy():
    m = types.ModuleType("heapq")
    for k in dir(_real_heapq):
        if not k.startswith("__"):
            setattr(m, k, getattr(_real_heapq, k))

    def heappush(h, x):
        Count.push += 1
        return _real_heapq.heappush(h, x)

    def heappop(h):
        Count.pop += 1
        return _real_heapq.heappop(h)

    def heappushpop(h, x):
        Count.push += 1
        Count.pop += 1
        return _real_heapq.heappushpop(h, x)

    def heapreplace(h, x):
        Count.push += 1
        Count.pop += 1
        return _real_heapq.heapreplace(h, x)

    m.heappush, m.heappop, m.heappushpop, m.heapreplace = heappush, heappop, heappushpop, heapreplace
    return m


class TRow(str):
    def __new__(cls, s, r):
        o = str.__new__(cls, s)
        o._r = r
        return o

    def __getitem__(self, c):
        if isinstance(c, int) and len(Count.reads) < 4000:
            Count.reads.append((self._r, c))
        return str.__getitem__(self, c)


def valid_path(grid, start, goal, path):
    try:
        path = [tuple(p) for p in path]
    except TypeError:
        return False
    if not path or path[0] != tuple(start) or path[-1] != tuple(goal):
        return False
    H, W = len(grid), len(grid[0])
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False
    for r, c in path:
        if not (0 <= r < H and 0 <= c < W) or grid[r][c] != ".":
            return False
    return True


def main():
    job = json.loads(sys.stdin.read())
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 ** 2, 1536 * 1024 ** 2))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    sys.modules["heapq"] = _proxy()
    want_lines = set(job.get("lines") or [])
    results = []
    for run in job["runs"]:
        Count.push = Count.pop = 0
        Count.reads = []
        Count.lines = {}
        grid = [TRow(s, r) for r, s in enumerate(run["grid"])]
        start, goal = tuple(run["start"]), tuple(run["goal"])
        box = {}

        def tracer(frame, event, arg):
            if frame.f_code.co_filename != "<candidate>":
                return None
            if event == "line" and frame.f_lineno in want_lines:
                Count.lines[frame.f_lineno] = Count.lines.get(frame.f_lineno, 0) + 1
            return tracer

        def target():
            try:
                mod = types.ModuleType("cand")
                mod.__file__ = "<candidate>"
                exec(compile(job["code"], "<candidate>", "exec"), mod.__dict__)
                random.seed(run.get("seed", 0))
                if want_lines:
                    sys.settrace(tracer)
                try:
                    box["out"] = mod.__dict__["solve"](grid, start, goal)
                finally:
                    sys.settrace(None)
            except BaseException as e:  # noqa: BLE001 - candidate code may raise anything
                box["exc"] = type(e).__name__ + ": " + str(e)[:160]

        th = threading.Thread(target=target, daemon=True)
        th.start()
        th.join(float(job.get("timeout_s", 4.0)))
        rec = {"name": run.get("name"), "seed": run.get("seed", 0), "timeout": th.is_alive()}
        out = box.get("out")
        plain = [str(s) for s in run["grid"]]
        rec["valid"] = bool(out is not None and not th.is_alive() and valid_path(plain, start, goal, out))
        rec["path_len"] = len(out) if isinstance(out, list) else None
        rec["heappush"] = Count.push
        rec["heappop"] = Count.pop
        rec["n_reads"] = len(Count.reads)
        rec["reads_sha"] = hashlib.sha256(json.dumps(Count.reads).encode()).hexdigest()[:16]
        rec["path_sha"] = hashlib.sha256(json.dumps([list(p) for p in out] if isinstance(out, list) else None,
                                                    default=str).encode()).hexdigest()[:16]
        rec["line_hits"] = {str(k): v for k, v in Count.lines.items()}
        rec["exc"] = box.get("exc")
        results.append(rec)
        if th.is_alive():
            break
    sys.stdout.write(json.dumps({"results": results}) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
