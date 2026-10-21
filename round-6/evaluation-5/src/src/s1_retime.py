#!/usr/bin/env python3
"""S1: re-time every catalogue reference of the 30 iteration-5 units with ONE harness (src/time_child.py).

Per reference: one full pass over every hidden test (correctness; doubles as warm-up), then 5 timed repeats over the
unit's stress cases, each repeat in a fresh `python -I` subprocess with OMP/MKL/OPENBLAS threads = 1 and the same
case order. t = median over repeats of the summed stress-case time; if the coefficient of variation across repeats
exceeds 0.2 the reference gets 4 more repeats (9 in all) and the flag 'unstable'.
Stress cases: tests flagged kind == 'stress'; else (path tasks) the largest 20% by the case's 'size' (ties broken by
a seed-6006 shuffle). Reads NO outcome file. Output: retime/raw_times.json
"""

from __future__ import annotations

import json
import os
import random
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))
from common import EXP25, EXP26, ART  # noqa: E402

CHILD = WS / "src" / "time_child.py"
OUT = WS / "retime" / "raw_times.json"
N_REP, N_REP_UNSTABLE, CV_MAX = 5, 9, 0.2
BENCH = EXP25 / "inputs" / "exp11" / "bench"
BENCH_FALLBACK = EXP26 / "vendor" / "exp11" / "bench"
SUITE = EXP25 / "inputs" / "exp8" / "suite" / "tasks"
PATH_MODE = {  # eval4 rivals/r6_merit.py mapping of exp8 reference stems to catalogue modes
    "t1": {"bfs_deque_parent": "bfs", "bfs_listpop_pathcarry": "bfs", "dfs_recursive": "dfs", "dfs_stack": "dfs",
           "bibfs_deques": "bibfs", "bibfs_sets": "bibfs", "iddfs_iterative": "iddfs", "iddfs_recursive": "iddfs",
           "astar_fg": "astar_gbfs", "gbfs_counter": "astar_gbfs", "dijkstra_counter": "dijkstra",
           "dijkstra_lazy": "dijkstra"},
    "t2": {"dijkstra_lazy": "dijkstra", "dijkstra_decreasekey": "dijkstra", "bellman_ford": "bf_spfa",
           "spfa": "bf_spfa", "bidijkstra_alternate": "bidijkstra", "bidijkstra_reverse": "bidijkstra",
           "floyd_bigint": "floyd", "floyd_inf": "floyd", "dial_dict": "dial", "dial_list": "dial"},
}
PANEL_B_CHECKER = {"B1": "exact", "B2": "exact", "B3": "exact", "B4": "exact", "B5": "subsets", "B6": "bool",
                   "B7": "exact"}  # exp26 src/units/b*.py CHECKER
EXISTING = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6", "T1", "T2"]
PANEL = ["A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9", "B1", "B2", "B3", "B4", "B5", "B6", "B7"]


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def unit_jobs() -> list[dict]:
    """One job per (unit, reference), with the case list, stress index list and checker."""
    jobs: list[dict] = []
    bench = BENCH if BENCH.exists() else BENCH_FALLBACK
    for td in sorted(p for p in bench.iterdir() if p.is_dir() and (p / "spec.json").exists()):
        u = td.name.split("_")[0]
        cases = _jsonl(td / "tests.jsonl")
        stress = [i for i, c in enumerate(cases) if c.get("kind") == "stress"]
        for ref in sorted((td / "references").glob("*.py")):
            jobs.append({"unit": u, "mode": ref.stem, "ref": ref.stem, "code_path": str(ref), "call": "kwargs",
                         "cases": cases, "stress": stress, "checker": {"type": "module", "path": str(td / "checker.py")},
                         "src": f"{ART['exp25']}:inputs/exp11/bench/{td.name}/references/{ref.name}"})
    for t, sub in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        cases = json.loads((SUITE / sub / "tests.json").read_text())
        order = list(range(len(cases)))
        random.Random(6006).shuffle(order)
        rank = {i: r for r, i in enumerate(order)}
        by_size = sorted(range(len(cases)), key=lambda i: (-float(cases[i].get("size", 0)), rank[i]))
        stress = sorted(by_size[: max(1, round(0.2 * len(cases)))])
        for ref in sorted((SUITE / sub / "references").glob("*.py")):
            jobs.append({"unit": t.upper(), "mode": PATH_MODE[t].get(ref.stem, ref.stem), "ref": ref.stem,
                         "code_path": str(ref), "call": t, "cases": cases, "stress": stress,
                         "checker": {"type": "path", "tasks_dir": str(SUITE), "task": t},
                         "src": f"{ART['exp25']}:inputs/exp8/suite/tasks/{sub}/references/{ref.name}"})
    for ud in sorted(p for p in (EXP25 / "newbench").iterdir() if p.is_dir() and p.name[:2] in
                     {"A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9"}):
        u = ud.name.split("_")[0]
        cases = _jsonl(ud / "tests.jsonl")
        stress = [i for i, c in enumerate(cases) if c.get("kind") == "stress"]
        for ref in sorted((ud / "references").glob("*.py")):
            jobs.append({"unit": u, "mode": ref.stem, "ref": ref.stem, "code_path": str(ref), "call": "kwargs",
                         "cases": cases, "stress": stress, "checker": {"type": "module", "path": str(ud / "checker.py")},
                         "src": f"{ART['exp25']}:newbench/{ud.name}/references/{ref.name}"})
    for u in ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]:
        ud = EXP26 / "units" / u
        cases = _jsonl(ud / "tests.jsonl")
        stress = [i for i, c in enumerate(cases) if c.get("kind") == "stress"]
        for ref in sorted((ud / "references").glob("*.py")):
            jobs.append({"unit": u, "mode": ref.stem, "ref": ref.stem, "code_path": str(ref), "call": "args",
                         "cases": cases, "stress": stress, "checker": {"type": "kind", "kind": PANEL_B_CHECKER[u]},
                         "src": f"{ART['exp26']}:units/{u}/references/{ref.name}"})
    return jobs


def run_child(job: dict, case_idx: list[int], check: bool) -> dict:
    env = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
           "PYTHONHASHSEED": "0"}
    payload = {"code_path": job["code_path"], "mode": job["call"], "cases": [job["cases"][i] for i in case_idx],
               "checker": job["checker"], "check": check}
    proc = subprocess.run([sys.executable, "-I", str(CHILD)], input=json.dumps(payload), capture_output=True,
                          text=True, timeout=600, env=env)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    if not lines:
        return {"load_error": f"crash: {proc.stderr[-300:]}", "cases": []}
    return json.loads(lines[-1])


def time_reference(job: dict) -> dict:
    t0 = time.time()
    row = {k: job[k] for k in ("unit", "mode", "ref", "src")}
    row["n_cases"], row["n_stress"] = len(job["cases"]), len(job["stress"])
    full = run_child(job, list(range(len(job["cases"]))), check=True)
    fails = [c for c in full["cases"] if not c["ok"]]
    row["passes_all"] = full["load_error"] is None and len(full["cases"]) == len(job["cases"]) and not fails
    row["n_failed"] = len(fails) + (len(job["cases"]) - len(full["cases"]))
    row["load_error"] = full["load_error"]
    reps: list[float] = []
    if row["passes_all"]:
        for _ in range(N_REP):
            r = run_child(job, job["stress"], check=False)
            reps.append(sum(c["t"] for c in r["cases"]))
        mean = statistics.fmean(reps)
        cv = statistics.stdev(reps) / mean if mean > 0 and len(reps) > 1 else 0.0
        row["unstable"] = bool(cv > CV_MAX)
        if row["unstable"]:
            for _ in range(N_REP_UNSTABLE - N_REP):
                r = run_child(job, job["stress"], check=False)
                reps.append(sum(c["t"] for c in r["cases"]))
            mean = statistics.fmean(reps)
            cv = statistics.stdev(reps) / mean if mean > 0 else 0.0
        q = statistics.quantiles(reps, n=4, method="inclusive")
        row.update(t_median=statistics.median(reps), t_iqr=q[2] - q[0], cv=cv, n_repeats=len(reps), repeats=reps)
    row["wall_s"] = time.time() - t0
    return row


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "s1_retime.log", rotation="30 MB", level="DEBUG")
    jobs = unit_jobs()
    if len(sys.argv) > 1 and sys.argv[1] == "--mini":
        jobs = [j for j in jobs if j["unit"] in ("T03", "B3", "T1")][:6]
    units = sorted({j["unit"] for j in jobs})
    logger.info(f"S1 re-timing: {len(jobs)} references over {len(units)} units: {units}")
    res: list[dict | None] = [None] * len(jobs)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(time_reference, j): i for i, j in enumerate(jobs)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                res[i] = f.result()
                r = res[i]
                logger.info(f"{r['unit']} {r['ref']} ({r['mode']}): pass={r['passes_all']} "
                            f"t={r.get('t_median', float('nan')):.5f}s cv={r.get('cv', float('nan')):.3f} "
                            f"n={r.get('n_repeats', 0)} wall={r['wall_s']:.1f}s")
            except (subprocess.TimeoutExpired, OSError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"failed {jobs[i]['src']}: {e}")
                res[i] = {k: jobs[i][k] for k in ("unit", "mode", "ref", "src")} | {"error": str(e)[:200],
                                                                                     "passes_all": False}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"harness": "src/time_child.py", "n_rep": N_REP, "n_rep_unstable": N_REP_UNSTABLE,
                               "cv_max": CV_MAX, "python": sys.version, "threads_env": "OMP/MKL/OPENBLAS=1",
                               "utc_end": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "wall_s": time.time() - t0, "rows": res}, indent=1))
    logger.info(f"wrote {OUT.relative_to(WS)} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
