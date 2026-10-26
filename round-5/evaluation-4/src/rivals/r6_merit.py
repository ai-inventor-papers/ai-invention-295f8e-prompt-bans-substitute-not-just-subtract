#!/usr/bin/env python3
"""R6 raw input: CPU timing and size of every catalogue reference on its task's hidden tests.

Bench tasks (13): bench/<task>/references/<mode>.py run through the bench's own sandbox runner
(bench/common/runner.py, payload of tests.jsonl cases, checkers from bench/common/checkers.py).
Path tasks (T1, T2): exp8 suite references run through the suite's own sandbox (tasks/sandbox_tests.py),
which reports per-case times.  Each reference: 1 warm-up run + 5 timed runs, per-case median over the timed
runs, summed over cases.  Size: AST node count and non-blank non-comment lines.

This script reads NO outcome file (no escape fraction, ban row or push landing); it only executes reference
programs.  Output: rivals/r6_merit_raw.json
"""

from __future__ import annotations

import ast
import json
import multiprocessing as mp
import os
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))
from io_util import DEPS  # noqa: E402  (dependency folders: <AII_DEPS_ROOT>/<artifact_id>)

BENCH_ID, BENCH = DEPS["bench"][0], DEPS["bench"][1] / "bench"
SUITE_ID, SUITE = DEPS["exp23"][0], DEPS["exp23"][1] / "inputs" / "exp8" / "suite"
# stdlib-only CPython 3.12 for the sandboxes (run with -I -S): $SANDBOX_PYTHON, else python3.12 on PATH
SYS_PY = os.environ.get("SANDBOX_PYTHON") or shutil.which("python3.12") or sys.executable
N_TIMED = 5
OUT = WS / "rivals" / "r6_merit_raw.json"

PATH_MODE = {  # reference file stem -> catalogue mode used by exp22 / exp23 for the path tasks
    "t1": {"bfs_deque_parent": "bfs", "bfs_listpop_pathcarry": "bfs", "dfs_recursive": "dfs", "dfs_stack": "dfs",
           "bibfs_deques": "bibfs", "bibfs_sets": "bibfs", "iddfs_iterative": "iddfs", "iddfs_recursive": "iddfs",
           "astar_fg": "astar_gbfs", "gbfs_counter": "astar_gbfs", "dijkstra_counter": "dijkstra",
           "dijkstra_lazy": "dijkstra"},
    "t2": {"dijkstra_lazy": "dijkstra", "dijkstra_decreasekey": "dijkstra", "bellman_ford": "bf_spfa",
           "spfa": "bf_spfa", "bidijkstra_alternate": "bidijkstra", "bidijkstra_reverse": "bidijkstra",
           "floyd_bigint": "floyd", "floyd_inf": "floyd", "dial_dict": "dial", "dial_list": "dial"},
}


def size_metrics(code: str) -> dict[str, int]:
    tree = ast.parse(code)
    sloc = sum(1 for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#"))
    return {"ast_nodes": sum(1 for _ in ast.walk(tree)), "sloc": sloc}


def run_bench_once(task_dir: str, code: str) -> list[dict]:
    td = Path(task_dir)
    task = td.name.split("_")[0]
    cases = [json.loads(ln) for ln in (td / "tests.jsonl").read_text().splitlines() if ln.strip()]
    payload = {"code": code, "task": task, "checkers_path": str(BENCH / "common" / "checkers.py"),
               "cases": [{"kwargs_json": json.dumps(c["kwargs"]), "expected_json": json.dumps(c["expected"]),
                          "limit": max(3.0, 3 * float(c["limit"]))} for c in cases]}
    proc = subprocess.run([SYS_PY, "-I", "-S", str(BENCH / "common" / "runner.py")], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=600)
    rows = [json.loads(ln) for ln in proc.stdout.splitlines() if ln.startswith("{")]
    return rows


def run_path_once(task: str, code: str) -> dict:
    job = {"task": task, "code": code, "tasks_dir": str(SUITE / "tasks"), "limits": None, "max_case_s": 30.0}
    proc = subprocess.run([SYS_PY, "-I", "-S", str(SUITE / "tasks" / "sandbox_tests.py")], input=json.dumps(job),
                          capture_output=True, text=True, timeout=900)
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    return json.loads(lines[-1]) if lines else {"error": "crash", "stderr": proc.stderr[-300:]}


def time_reference(job: dict) -> dict:
    code = Path(job["abs"]).read_text()
    out = {"task": job["task"], "ref": Path(job["abs"]).stem, "mode": job["mode"], "path": job["src"],
           **size_metrics(code)}
    t0 = time.time()
    per_case: dict[str, list[float]] = {}
    ok_all = True
    n_cases = 0
    for rep in range(N_TIMED + 1):
        if job["kind"] == "bench":
            rows = run_bench_once(job["task_dir"], code)
            n_cases = len(rows)
            ok_all = ok_all and bool(rows) and all(r["status"] in ("ok", "slow") for r in rows)
            if rep == 0:
                continue
            for r in rows:
                per_case.setdefault(str(r["i"]), []).append(float(r["t"]))
        else:
            res = run_path_once(job["task"], code)
            ok_all = ok_all and bool(res.get("passed"))
            n_cases = int(res.get("n_cases") or 0)
            if rep == 0:
                continue
            for cid, t in (res.get("case_times") or {}).items():
                per_case.setdefault(cid, []).append(float(t))
    med = {c: statistics.median(v) for c, v in per_case.items()}
    out.update(passes_all=ok_all, n_cases=n_cases, n_cases_timed=len(med), total_median_s=sum(med.values()),
               wall_s=time.time() - t0)
    return out


def jobs() -> list[dict]:
    js = []
    for td in sorted(p for p in BENCH.iterdir() if p.is_dir() and (p / "spec.json").exists()):
        task = td.name.split("_")[0]
        for ref in sorted((td / "references").glob("*.py")):
            js.append({"kind": "bench", "task": task, "task_dir": str(td), "abs": str(ref), "mode": ref.stem,
                       "src": f"{BENCH_ID}:bench/{td.name}/references/{ref.name}"})
    for t, sub in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        for ref in sorted((SUITE / "tasks" / sub / "references").glob("*.py")):
            js.append({"kind": "path", "task": t, "abs": str(ref), "mode": PATH_MODE[t].get(ref.stem, ref.stem),
                       "src": f"{SUITE_ID}:inputs/exp8/suite/tasks/{sub}/references/{ref.name}"})
    return js


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "r6_merit.log", rotation="30 MB", level="DEBUG")
    js = jobs()
    if len(sys.argv) > 1 and sys.argv[1] == "--mini":
        js = js[:3]
    logger.info(f"R6 timing: {len(js)} references, {N_TIMED} timed repeats + 1 warm-up each")
    res: list[dict | None] = [None] * len(js)
    with ProcessPoolExecutor(max_workers=3, mp_context=mp.get_context("spawn")) as pool:
        futs = {pool.submit(time_reference, j): i for i, j in enumerate(js)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                res[i] = f.result()
                logger.info(f"{res[i]['task']} {res[i]['ref']}: pass={res[i]['passes_all']} "
                            f"t={res[i]['total_median_s']:.4f}s nodes={res[i]['ast_nodes']}")
            except (subprocess.TimeoutExpired, OSError, ValueError) as e:
                logger.error(f"failed {js[i]['src']}: {e}")
                res[i] = {**{k: v for k, v in js[i].items() if k not in ("abs", "task_dir")}, "error": str(e)[:200]}
    OUT.write_text(json.dumps({"n_timed": N_TIMED, "warmup": 1, "rows": res}, indent=1))
    logger.info(f"wrote {OUT.relative_to(WS)}")


if __name__ == "__main__":
    main()
