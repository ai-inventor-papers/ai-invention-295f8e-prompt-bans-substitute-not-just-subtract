"""S0 labeller re-check on this machine: references (both labellers must recover the mode) and the adjudicated gold
sets (runtime label vs adjudicated label).  Bench: 4 tasks; path suite: 22 references + the exp1 gold set."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from config import BENCH_DIR, BENCH_TASKS, RESULTS, SUITE_DIR, TASKS, read_jsonl, setup_logging, utc_now, write_json
from label import _mech_bench, _mech_path

PATH_REF_MODE = {"astar": "astar_gbfs", "gbfs": "astar_gbfs", "bfs": "bfs", "bibfs": "bibfs", "dfs": "dfs",
                 "dijkstra": "dijkstra", "iddfs": "iddfs", "bellman": "bf_spfa", "spfa": "bf_spfa",
                 "bidijkstra": "bidijkstra", "dial": "dial", "floyd": "floyd"}


def main() -> None:
    setup_logging("recheck")
    jobs = []
    for t in BENCH_TASKS:
        for f in sorted((BENCH_DIR / TASKS[t]["task_id"] / "references").glob("*.py")):
            jobs.append(("ref", t, f.stem, f.read_text()))
        for g in read_jsonl(BENCH_DIR / TASKS[t]["task_id"] / "gold_set.jsonl"):
            jobs.append(("gold", t, g["adjudicated"], g["code"]))
    for t, sub in (("T1", "t1_grid"), ("T2", "t2_wsp")):
        for f in sorted((SUITE_DIR / "tasks" / sub / "references").glob("*.py")):
            jobs.append(("ref", t, PATH_REF_MODE[f.stem.split("_")[0]], f.read_text()))
    for g in read_jsonl(SUITE_DIR / "labeller" / "gold_set.jsonl"):
        jobs.append(("gold", {"t1": "T1", "t2": "T2"}[g["task"]], g["adjudicated"], g["code"]))

    def work(j):
        kind, t, lab, code = j
        m = _mech_bench(t, code) if TASKS[t]["family"] == "bench" else _mech_path(t, code)
        return kind, t, lab, m.get("runtime_label"), m.get("ast_label")

    with ThreadPoolExecutor(5) as ex:
        res = list(ex.map(work, jobs))
    out = {}
    for t in TASKS:
        refs = [r for r in res if r[0] == "ref" and r[1] == t]
        gold = [r for r in res if r[0] == "gold" and r[1] == t]
        out[t] = {"n_refs": len(refs), "refs_runtime_correct": sum(r[3] == r[2] for r in refs),
                  "refs_ast_correct": sum(r[4] == r[2] for r in refs),
                  "ref_misses": [{"mode": r[2], "runtime": r[3], "ast": r[4]} for r in refs if r[3] != r[2] or
                                 r[4] != r[2]],
                  "n_gold": len(gold), "gold_runtime_vs_adjudicated": (sum(r[3] == r[2] for r in gold) / len(gold))
                  if gold else None}
        out[t]["flag_below_0.85"] = (out[t]["gold_runtime_vs_adjudicated"] or 1.0) < 0.85
    write_json(RESULTS / "labeller_recheck.json", {"utc": utc_now(), "tasks": out})
    print(json.dumps({t: {k: v for k, v in o.items() if k != "ref_misses"} for t, o in out.items()}, indent=0))


if __name__ == "__main__":
    main()
