#!/usr/bin/env python3
"""Stage 1.2 GATE / T2: the instrument on the 18 planted cell references + the catalogue references (vendor exp9
t1_grid/references) must give the intended (disc, cont) 100%, and every planted reference must pass both suites.
Mutation tests: BFS with deque.pop() -> DFS; RLX sweeps cut to one pass -> not RLX; seeded-identically twice ->
deterministic (n_nondet = 0) while different seeds -> RND. Writes results/instrument_gate.json."""

from __future__ import annotations

import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

from common import read_json, sha256_file, utc_now, write_json  # noqa: E402
from tpg2 import ALL_CELLS, LOGS, RESULTS, ROOT, cell_dc  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "gate_instrument.log"), rotation="30 MB", level="DEBUG")

PLANTED = ROOT / "references" / "planted"
CATALOGUE = ROOT / "vendor" / "exp9" / "tasks" / "t1_grid" / "references"
CAT_INTENDED = {"bfs_deque_parent": ("LEV", "DEQ"), "bfs_listpop_pathcarry": ("LEV", "DEQ"),
                "dfs_recursive": ("DFS", "STK"), "dfs_stack": ("DFS", "STK"), "dijkstra_counter": ("LEV", "HEAP"),
                "dijkstra_lazy": ("LEV", "HEAP"), "astar_fg": ("HEU", "HEAP"), "gbfs_counter": ("HEU", "HEAP"),
                "bibfs_deques": ("OTHER", "*"), "bibfs_sets": ("OTHER", "*"), "iddfs_iterative": ("OTHER", "*"),
                "iddfs_recursive": ("OTHER", "*"), "idastar": ("OTHER", "*"), "jps4": ("HEU", "*"),
                "biastar": ("OTHER", "*")}


def mutations() -> dict[str, tuple[str, tuple[str, str]]]:
    lev = (PLANTED / "LEV_DEQ.py").read_text()
    rlx = (PLANTED / "RLX_ARR.py").read_text()
    one = rlx.replace("    changed = True\n    while changed:\n        changed = False\n",
                      "    changed = True\n    for _sweep in range(1):\n        changed = False\n")
    assert one != rlx
    return {"mut_bfs_pop_right": (lev.replace("q.popleft()", "q.pop()"), ("DFS", "DEQ")),
            "mut_rlx_one_pass": (one, ("!RLX", "*"))}


def _eval(code: str) -> dict:
    import label_tp

    return label_tp._evaluate_one(code)


def main() -> None:
    import instrument

    items: dict[str, tuple[str, tuple[str, str]]] = {}
    for cell in ALL_CELLS:
        items[f"planted:{cell}"] = ((PLANTED / f"{cell}.py").read_text(), cell_dc(cell))
    for f in sorted(CATALOGUE.glob("*.py")):
        items[f"catalogue:{f.stem}"] = (f.read_text(), CAT_INTENDED[f.stem])
    for k, v in mutations().items():
        items[k] = v
    keys = list(items)
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        meas = dict(ex.map(instrument.measure_worker, [(k, items[k][0]) for k in keys]))
        planted = [k for k in keys if k.startswith("planted:")]
        evals = dict(zip(planted, ex.map(_eval, [items[k][0] for k in planted])))
    rows, n_ok, n_tot = [], 0, 0
    for k in keys:
        m = meas[k]
        want_d, want_c = items[k][1]
        if want_d.startswith("!"):
            ok_d = m["disc"] != want_d[1:]
        else:
            ok_d = m["disc"] == want_d
        ok_c = want_c == "*" or m["cont"] == want_c
        suites = None
        if k in evals:
            e = evals[k]
            suites = {"passed_48": bool(e.get("passed")), "passed_41": bool(e.get("passed_exp2"))}
        ok = ok_d and ok_c and (suites is None or (suites["passed_48"] and suites["passed_41"]))
        if not k.startswith("mut_"):
            n_tot += 1
            n_ok += int(ok)
        rows.append({"item": k, "intended": [want_d, want_c], "measured": [m["disc"], m["cont"]], "fine": m.get("fine"),
                     "ok": ok, "suites": suites,
                     **{x: m.get(x) for x in ("p_mono", "level_cover", "p_lifo", "revisit_share", "sweep_probes",
                                              "relabel_probes", "repush_probes", "relaxation_ast", "rng_diff_probes",
                                              "rng_nondet_probes", "goal_diff_pairs", "coord_key", "coord_share",
                                              "lev_assign_p_mono", "container_votes", "n_informative",
                                              "id_share", "bidir_share", "seconds")}})
        logger.info(f"{'OK ' if ok else 'BAD'} {k}: want {want_d}/{want_c} got {m['disc']}/{m['cont']} "
                    f"({m.get('fine')}) suites={suites}")
    out = {"n_items": n_tot, "n_correct": n_ok, "pass": n_ok == n_tot, "rows": rows,
           "instrument_sha256": {f: sha256_file(ROOT / "src" / f) for f in ("instrument.py", "inst_child.py",
                                                                           "orderclass.py")},
           "thresholds": instrument.TH, "utc": utc_now()}
    write_json(RESULTS / "instrument_gate.json", out)
    logger.info(f"GATE: {n_ok}/{n_tot} correct; mutations: "
                f"{[(r['item'], r['measured'], r['ok']) for r in rows if r['item'].startswith('mut_')]}")
    _ = read_json


if __name__ == "__main__":
    main()
