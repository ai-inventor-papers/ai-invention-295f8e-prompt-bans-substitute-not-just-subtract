#!/usr/bin/env python3
"""Test harness: run one candidate program on every hidden case of its task in ONE `python -I` subprocess.

Per-case wall-clock limit = max(1.0 s, 10 x the primary reference's median time on that case under this harness);
a timed-out case kills the subprocess and the run resumes at the next case (at most 3 timeouts, then the remaining
cases count as failed). Output: passed, n_cases_passed, first_fail {case_id, reason}, wall_s, lenient_io.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REFS_DIR, TESTS_DIR, write_json  # noqa: E402
from tasks import t1_grid, t2_sssp  # noqa: E402

DRIVER = Path(__file__).resolve().parent / "_driver.py"
CHECK = {"T1": t1_grid.check, "T2": t2_sssp.check}
PRIMARY_REF = {"T1": "t1_bfs.py", "T2": "t2_dijkstra.py"}
MAX_TIMEOUTS = 3
_CASES: dict = {}
_LIMITS: dict = {}


def cases_path(task: str) -> Path:
    return TESTS_DIR / f"{task.lower()}_hidden.json"


def limits_path(task: str) -> Path:
    return TESTS_DIR / f"{task.lower()}_limits.json"


def load_cases(task: str) -> list[dict]:
    if task not in _CASES:
        _CASES[task] = json.loads(cases_path(task).read_text())
    return _CASES[task]


def load_limits(task: str) -> list[float]:
    if task not in _LIMITS:
        p = limits_path(task)
        _LIMITS[task] = json.loads(p.read_text()) if p.exists() else [5.0] * len(load_cases(task))
    return _LIMITS[task]


def from_jsonable(x):
    if isinstance(x, dict):
        if "__seq__" in x:
            items = [from_jsonable(v) for v in x["items"]]
            return tuple(items) if x["__seq__"] == "tuple" else items
        if "__float__" in x:
            return float(x["__float__"])
        return x  # repr of an unsupported object, too-long marker
    if x == "NaN":
        return float("nan")
    return x


def run_program_tests(code: str, task: str, limits: list[float] | None = None,
                      collect_times: bool = False) -> dict:
    cases = load_cases(task)
    limits = list(limits if limits is not None else load_limits(task))
    with tempfile.TemporaryDirectory(prefix="h_") as td:
        td = Path(td)
        prog = td / "solution.py"
        prog.write_text(code)
        lim_p = td / "limits.json"
        lim_p.write_text(json.dumps(limits))
        out_p = td / "out.jsonl"
        start, n_timeouts, status_note = 0, 0, None
        records: dict[int, dict] = {}
        while start < len(cases):
            budget = sum(limits[start:]) + 5.0
            try:
                subprocess.run([sys.executable, "-I", str(DRIVER), str(prog), str(cases_path(task)), str(lim_p),
                                str(start), str(out_p), task], cwd=td, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=budget)
            except subprocess.TimeoutExpired:
                status_note = "subprocess_timeout"
            recs = []
            if out_p.exists():
                for line in out_p.read_text().splitlines():
                    try:
                        recs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            out_p.unlink(missing_ok=True)
            if recs and recs[0].get("i") == -1:
                return dict(passed=False, n_cases_passed=0, n_cases=len(cases),
                            first_fail=dict(case_id=None, reason=recs[0]["status"] + ":" + recs[0].get("err", "")),
                            wall_s=0.0, lenient_io=False, n_timeouts=0)
            for r in recs:
                records[r["i"]] = r
            last = max((r["i"] for r in recs), default=start - 1)
            if recs and recs[-1]["status"] == "timeout":
                n_timeouts += 1
                if n_timeouts >= MAX_TIMEOUTS:
                    break
                start = last + 1
            elif last + 1 >= len(cases):
                break
            else:
                # the process died without a timeout record (crash, memory limit): mark the case and move on
                records[last + 1] = {"i": last + 1, "status": "crash"}
                start = last + 2
    n_pass, first_fail, wall, lenient = 0, None, 0.0, False
    times = []
    for i, c in enumerate(cases):
        r = records.get(i)
        if r is None:
            reason = "not_run_after_timeouts"
            ok = False
        elif r["status"] == "ok":
            ok, reason, len_flag = CHECK[task](c, from_jsonable(r.get("out")))
            lenient = lenient or len_flag
            wall += r.get("t", 0.0)
            times.append(r.get("t", 0.0))
        else:
            ok, reason = False, r["status"] + (":" + r.get("err", "") if r.get("err") else "")
            wall += r.get("t", 0.0) or 0.0
            times.append(r.get("t", None))
        if ok:
            n_pass += 1
        elif first_fail is None:
            first_fail = dict(case_id=c["case_id"], reason=reason[:200])
    res = dict(passed=n_pass == len(cases), n_cases_passed=n_pass, n_cases=len(cases), first_fail=first_fail,
               wall_s=round(wall, 4), lenient_io=lenient, n_timeouts=n_timeouts)
    if status_note:
        res["note"] = status_note
    if collect_times:
        res["times"] = [records.get(i, {}).get("t") for i in range(len(cases))]
    return res


def calibrate_limits(task: str, reps: int = 3) -> list[float]:
    """Per-case limit = max(1.0, 10 x median primary-reference time over `reps` harness runs)."""
    code = (REFS_DIR / PRIMARY_REF[task]).read_text()
    big = [30.0] * len(load_cases(task))
    runs = []
    for _ in range(reps):
        r = run_program_tests(code, task, limits=big, collect_times=True)
        assert r["passed"], f"primary reference failed on {task}: {r['first_fail']}"
        runs.append(r["times"])
    import numpy as np
    med = np.median(np.array(runs, dtype=float), axis=0)
    limits = [round(max(1.0, 10.0 * float(t)), 4) for t in med]
    limits_path(task).write_text(json.dumps(limits))
    _LIMITS[task] = limits
    write_json(TESTS_DIR / f"{task.lower()}_ref_times.json", {"median_s": med.tolist(), "limits": limits})
    return limits


NEG_CONTROLS = {
    "T1": {
        "returns_zero": "def solve(grid, start, goal):\n    return 0\n",
        "infinite_loop": "def solve(grid, start, goal):\n    while True:\n        pass\n",
        "returns_start_only": "def solve(grid, start, goal):\n    return [start]\n",
    },
    "T2": {
        "returns_zero": "def solve(n, edges, s, t):\n    return 0\n",
        "infinite_loop": "def solve(n, edges, s, t):\n    while True:\n        pass\n",
        "all_simple_paths": (
            "def solve(n, edges, s, t):\n"
            "    adj = {}\n"
            "    for u, v, w in edges:\n"
            "        adj.setdefault(u, []).append((v, w))\n"
            "    best = [float('inf')]\n"
            "    def go(u, d, seen):\n"
            "        if u == t:\n"
            "            best[0] = min(best[0], d)\n"
            "            return\n"
            "        for v, w in adj.get(u, []):\n"
            "            if v not in seen:\n"
            "                seen.add(v)\n"
            "                go(v, d + w, seen)\n"
            "                seen.discard(v)\n"
            "    if s == t:\n"
            "        return 0\n"
            "    go(s, 0, {s})\n"
            "    return best[0] if best[0] < float('inf') else -1\n"),
    },
}


def reference_gate() -> dict:
    """Every catalogue reference (and variant) passes every case within limit/3; negative controls fail."""
    report: dict = {}
    for task in ("T1", "T2"):
        limits = load_limits(task)
        third = [x / 3.0 for x in limits]
        for f in sorted(REFS_DIR.glob(f"{task.lower()}_*.py")):
            r = run_program_tests(f.read_text(), task, limits=third, collect_times=True)
            slow = [load_cases(task)[i]["case_id"] for i, t in enumerate(r["times"])
                    if t is None or t > third[i]]
            report[f.name] = dict(passed_within_third=r["passed"], first_fail=r["first_fail"],
                                  max_time=max((t for t in r["times"] if t is not None), default=None), slow=slow)
        for name, code in NEG_CONTROLS[task].items():
            r = run_program_tests(code, task)
            report[f"neg_{task}_{name}"] = dict(passed=r["passed"], first_fail=r["first_fail"],
                                                n_timeouts=r["n_timeouts"])
    return report


if __name__ == "__main__":
    import time
    t0 = time.time()
    for task in ("T1", "T2"):
        print(task, "limits:", calibrate_limits(task)[:10], "...")
    rep = reference_gate()
    write_json(TESTS_DIR / "reference_gate.json", rep)
    print(json.dumps(rep, indent=1))
    print(f"{time.time() - t0:.1f}s")
