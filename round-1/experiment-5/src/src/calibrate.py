"""Time-limit calibration (STEP 1.5) + harness gate (testing plan item 1).

limit_case = max(1.0 s, 10 x median-of-5 time of the primary reference (bfs on T1, dijkstra_heap on T2)).
Every catalogue reference must take <= 0.5 x limit_case on every case and pass every case through the harness.
  .venv/bin/python src/calibrate.py
"""
from __future__ import annotations

import copy
import json
import statistics
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REFS, RESULTS, TESTS, WS, setup_logging  # noqa: E402
from harness import _args_for, score_many  # noqa: E402
from tasks import check_t1, check_t2  # noqa: E402

PRIMARY = {"t1": "bfs", "t2": "dijkstra_heap"}
REF_LABEL = {"t1": {"bfs": "bfs", "dfs_iter": "dfs", "dfs_rec": "dfs", "bidir_bfs": "bidir_bfs", "iddfs": "iddfs",
                    "astar": "astar_greedy", "greedy": "astar_greedy", "dijkstra_unit": "dijkstra_unit"},
             "t2": {"dijkstra_heap": "dijkstra", "dijkstra_array": "dijkstra", "bellman_ford": "bellman_ford_spfa",
                    "spfa": "bellman_ford_spfa", "bidir_dijkstra": "bidir_dijkstra", "floyd_warshall": "floyd_warshall",
                    "dial": "dial"}}


def load_fn(path: Path):
    ns: dict = {"__name__": "ref"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns["solve"]


def time_case(fn, task: str, case: dict, reps: int) -> tuple[float, bool]:
    ts = []
    ok = True
    for _ in range(reps):
        args = copy.deepcopy(_args_for(task, case))
        t0 = time.perf_counter()
        r = fn(*args)
        ts.append(time.perf_counter() - t0)
        ok = ok and (check_t1 if task == "t1" else check_t2)(case, r)[0]
    return statistics.median(ts), ok


HARNESS_PROBES = {
    "t1": {
        "infinite_loop": ("def solve(grid, start, goal):\n    while True:\n        pass\n", "timeout"),
        "alloc_4gb": ("def solve(grid, start, goal):\n    x = bytearray(4 * 1024**3)\n    return []\n", "exception:MemoryError"),
        "non_adjacent_step": ("def solve(grid, start, goal):\n    return [tuple(start), tuple(goal)]\n", "wrong"),
        "sys_exit": ("import sys\ndef solve(grid, start, goal):\n    sys.exit(3)\n", "exception:SystemExit"),
    },
    "t2": {
        "ignores_weights_bfs": ("from collections import deque\ndef solve(n, edges, s, t):\n    adj=[[] for _ in range(n)]\n"
                                "    for u,v,w in edges: adj[u].append(v)\n    d={s:0}\n    q=deque([s])\n"
                                "    while q:\n        u=q.popleft()\n        for v in adj[u]:\n"
                                "            if v not in d: d[v]=d[u]+1; q.append(v)\n    return d.get(t,-1)\n", "wrong"),
    },
}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("calibrate")
    report: dict = {"shrinks": [], "per_ref": {}, "probes": {}}
    for task in ("t1", "t2"):
        tpath = TESTS / f"{task}.json"
        tests = json.loads(tpath.read_text())
        cases = tests["cases"]
        prim = load_fn(REFS / task / f"{PRIMARY[task]}.py")
        for c in cases:
            med, ok = time_case(prim, task, c, 5)
            assert ok, f"primary ref fails {c['id']}"
            c["ref_median_s"] = med
            c["limit_s"] = max(1.0, 10 * med)
        worst: dict = {}
        for name in REF_LABEL[task]:
            fn = load_fn(REFS / task / f"{name}.py")
            for c in cases:
                med, ok = time_case(fn, task, c, 3)
                assert ok, f"ref {name} fails {c['id']}"
                worst.setdefault(name, []).append(med / c["limit_s"])
                if med > 0.5 * c["limit_s"]:
                    logger.warning(f"{task} {name} on {c['id']}: {med:.3f}s > 0.5 x limit {c['limit_s']:.2f}s")
                    report["shrinks"].append({"task": task, "ref": name, "case": c["id"], "t": med, "limit": c["limit_s"]})
        report["per_ref"][task] = {k: {"max_frac_of_limit": max(v), "median_frac": statistics.median(v)}
                                   for k, v in worst.items()}
        logger.info(f"{task}: per-ref worst fraction of limit: "
                    f"{ {k: round(v['max_frac_of_limit'], 3) for k, v in report['per_ref'][task].items()} }")
        if report["shrinks"]:
            logger.error("margin violated; shrink the listed cases (see report) and rerun")
        tests["limits_rule"] = "limit_s = max(1.0, 10 x median-of-5 time of primary reference); calibrated on this pod"
        tpath.write_text(json.dumps(tests))
    # harness gate: every reference passes every case through the real subprocess harness
    jobs = []
    for task in ("t1", "t2"):
        for name in REF_LABEL[task]:
            jobs.append((task, (REFS / task / f"{name}.py").read_text(), str(TESTS / f"{task}.json"),
                         str(WS / "scratch_harness"), f"{task}/{name}"))
        for pname, (code, _) in HARNESS_PROBES[task].items():
            jobs.append((task, code, str(TESTS / f"{task}.json"), str(WS / "scratch_harness"), f"{task}/probe:{pname}"))
    res = score_many(jobs, n_workers=4)
    gate_ok = True
    for r in res:
        task, name = r["key"].split("/")
        if name.startswith("probe:"):
            exp = HARNESS_PROBES[task][name[6:]][1]
            good = (not r["passed"]) and str(r.get("error", "")).startswith(exp)
            report["probes"][r["key"]] = {"expected": exp, "got": r.get("error"), "ok": good}
            logger.info(f"probe {r['key']}: expected {exp}, got {r.get('error')} -> {'OK' if good else 'BAD'}")
            gate_ok &= good
        else:
            report["per_ref"][task].setdefault(name, {})["harness_passed"] = r["passed"]
            report["per_ref"][task][name]["harness_wall_s"] = r.get("wall_s")
            if not r["passed"]:
                logger.error(f"REFERENCE FAILS HARNESS: {r}")
                gate_ok = False
    report["gate_ok"] = gate_ok and not report["shrinks"]
    (RESULTS / "harness_calibration.json").write_text(json.dumps(report, indent=1))
    logger.info(f"harness gate ok: {report['gate_ok']}")


if __name__ == "__main__":
    main()
