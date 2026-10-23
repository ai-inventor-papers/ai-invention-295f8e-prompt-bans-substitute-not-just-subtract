#!/usr/bin/env python3
"""Placebo 4 (testing plan 7 / plan 6.1): a tracer run on ORDER-SHUFFLED event streams must lose the BFS classes.
For each BFS-order reference / planted control, the child's raw events are recorded, the expansion candidates are
shuffled (the event multiset is unchanged, only its order), and the class is recomputed with the committed rules.
Usage: .venv/bin/python audit/placebo_shuffled_events.py -> results/placebo_shuffled_events.json"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import orderclass as O  # noqa: E402

CASES = ["inputs/exp9/tasks/t1_grid/references/bfs_deque_parent.py", "inputs/exp9/tasks/t1_grid/references/bfs_listpop_pathcarry.py",
         "inputs/exp9/tasks/t1_grid/references/dijkstra_counter.py", "inputs/exp9/tasks/t1_grid/references/dijkstra_lazy.py",
         "controls/c1_wave_search_bfs.py", "controls/c7_fifo_spfa_relax.py", "controls/c9_wavefront_from_goal.py"]


def shuffled_class(code: str, seed: int) -> tuple[str, str]:
    run = O.run_child(code)
    rng = random.Random(seed)
    stats = []
    for i in range(len(O.probes())):
        rec = run["probes"].get(i)
        if rec is None:
            continue
        ev = list(rec["events"])
        # shuffle the positions of the expansion candidates (POP/ITER/CALL) among themselves
        idx = [k for k, e in enumerate(ev) if e[0] in (1, 3, 4)]
        vals = [ev[k] for k in idx]
        rng.shuffle(vals)
        for k, v in zip(idx, vals):
            ev[k] = v
        stats.append(O.probe_stats({**rec, "events": ev}, i))
    orig = O.trace_program(code)["order_class"]
    return orig, O.classify(stats)["order_class"]


def main() -> None:
    out = {"cases": []}
    for c in CASES:
        code = (ROOT / c).read_text()
        orig, sh = shuffled_class(code, 0)
        out["cases"].append({"program": c, "original_class": orig, "shuffled_class": sh})
    out["n_bfs_original"] = sum(1 for x in out["cases"] if x["original_class"] == "BFS")
    out["n_bfs_after_shuffle"] = sum(1 for x in out["cases"] if x["shuffled_class"] == "BFS")
    out["fails_as_required"] = out["n_bfs_after_shuffle"] == 0
    (ROOT / "results" / "placebo_shuffled_events.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
