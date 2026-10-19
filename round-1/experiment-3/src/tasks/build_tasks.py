"""S1: build hidden-test JSON files, time every reference 3x under pool load, derive per-case limits, run the gate.

Usage: .venv/bin/python -m tasks.build_tasks
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tasks import t1_grid, t2_wsp  # noqa: E402

MODS = {"T1": t1_grid, "T2": t2_wsp}


def _time_ref(args: tuple) -> tuple[str, str, list[float], list[bool], list[str]]:
    task, name, code, cases = args
    T = MODS[task]
    ns: dict = {"__name__": "ref"}
    exec(compile(code, f"<{name}>", "exec"), ns)  # noqa: S102 - trusted reference code
    sys.setrecursionlimit(20000)
    times, oks, whys = [], [], []
    for case in cases:
        best = 0.0
        ok_all, why = True, "ok"
        for _ in range(3):
            a = T.case_args(case)
            t0 = time.perf_counter()
            out = ns["solve"](*a)
            el = time.perf_counter() - t0
            best = max(best, el)
            ok, w = T.validate(case, out)
            if not ok:
                ok_all, why = False, w
        times.append(best)
        oks.append(ok_all)
        whys.append(why)
    return task, name, times, oks, whys


def main() -> None:
    out_summary: dict = {}
    jobs = []
    all_cases = {}
    for task, T in MODS.items():
        cases = T.make_cases()
        all_cases[task] = cases
        for name, (_, code) in T.REFERENCES.items():
            jobs.append((task, name, code, cases))
    with ProcessPoolExecutor(max_workers=5, mp_context=mp.get_context("spawn")) as ex:
        results = list(ex.map(_time_ref, jobs))
    for task, T in MODS.items():
        cases = all_cases[task]
        per = {name: (times, oks, whys) for (tk, name, times, oks, whys) in results if tk == task}
        slowest = [max(per[n][0][i] for n in per) for i in range(len(cases))]
        limits = [max(1.0, 10.0 * s) for s in slowest]
        gate = {}
        for name, (times, oks, whys) in per.items():
            fails = [(cases[i]["name"], whys[i]) for i in range(len(cases)) if not oks[i] or times[i] > limits[i]]
            gate[name] = {"pass": not fails, "fails": fails[:5], "total_s": round(sum(times), 3),
                          "max_frac_of_limit": round(max(t / l for t, l in zip(times, limits)), 3)}
        (ROOT / "tasks" / f"{task}_cases.json").write_text(json.dumps({"cases": cases, "limits": limits}))
        out_summary[task] = {"n_cases": len(cases), "sum_limits_s": round(sum(limits), 2),
                             "n_reachable_or_expected": sum(1 for c in cases if c.get("reachable", c.get("expected", -1) != -1)),
                             "gate": gate, "limits": [round(x, 3) for x in limits],
                             "case_names": [c["name"] for c in cases]}
        print(task, "cases", len(cases), "sum limits", round(sum(limits), 1))
        for name, g in gate.items():
            print(f"  {name:28s} pass={g['pass']} total={g['total_s']}s maxfrac={g['max_frac_of_limit']} {g['fails'][:2]}")
    (ROOT / "tasks" / "limits.json").write_text(json.dumps({t: out_summary[t]["limits"] for t in out_summary}, indent=1))
    (ROOT / "tasks" / "build_summary.json").write_text(json.dumps(out_summary, indent=1))


if __name__ == "__main__":
    main()
