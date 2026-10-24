#!/usr/bin/env python3
"""T5 verifier unit tests (must pass 100% before commit #1): the T1 references map to their expected cells /
classes, the 12 planted hard-cell programs are accepted (ACCEPT, or HAND with every automatic check passing for the
hand-read cells), and the 4 negative controls are rejected. Writes results/verifier_unit_tests.json."""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

REF = ROOT / "vendor/exp9/tasks/t1_grid/references"
REF_EXPECT = {"bfs_deque_parent": "BFSO-DEQUE", "bfs_listpop_pathcarry": "BFSO-LIST", "dfs_stack": "DFSO-LIST",
              "dfs_recursive": "DFSO-CALL", "astar_fg": "HEUR-HEAP", "gbfs_counter": "HEUR-HEAP",
              "dijkstra_lazy": "COST-HEAP", "dijkstra_counter": "COST-HEAP", "iddfs_recursive": "iddfs",
              "iddfs_iterative": "iddfs", "bibfs_deques": "bibfs", "bibfs_sets": "bibfs", "jps4": "jps",
              "biastar": "biastar"}
FACTORIAL_CELLS = None


def _one(item: tuple[str, str, str, str]) -> dict:
    kind, name, code, cell = item
    import verify

    t0 = time.time()
    r = verify.verify_program(code, cell)
    auto_ok = r["verdict"] in ("ACCEPT", "HAND") and not r["reasons"]
    if kind == "negative":
        ok = r["verdict"] == "REJECT"
    elif kind == "idastar_any_cell":
        ok = r["verdict"] == "REJECT"
    else:
        ok = auto_ok
    return {"kind": kind, "name": name, "cell": cell, "verdict": r["verdict"], "reasons": r["reasons"], "pass": ok,
            "seconds": round(time.time() - t0, 1),
            "tracer": (r.get("tracer") or {}).get("order_class_fine"),
            "container": (r.get("container_check") or {}).get("why"),
            "discipline": {k: v for k, v in (r.get("discipline_check") or {}).items() if k in (
                "pass", "tracer_class", "ast_signature", "disagree", "rand_seed_check", "relax_pass_check")},
            "topup": {k: v for k, v in (r.get("topup_check") or {}).items() if k != "jps_check"} |
            ({"jps": {k: v for k, v in r["topup_check"]["jps_check"].items() if k in ("pass", "ratio")}}
             if (r.get("topup_check") or {}).get("jps_check") else {})}


def main() -> None:
    import cells

    items = []
    for name, cell in REF_EXPECT.items():
        items.append(("reference", name, (REF / f"{name}.py").read_text(), cell))
    ida = (REF / "idastar.py").read_text()
    for cell in ("HEUR-HEAP", "DFSO-CALL", "DFSO-LIST", "COST-HEAP"):
        items.append(("idastar_any_cell", f"idastar@{cell}", ida, cell))
    for p in sorted((ROOT / "tests/planted").glob("*.py")):
        items.append(("planted", p.stem, p.read_text(), p.stem))
    for p in sorted((ROOT / "tests/negative").glob("*.py")):
        items.append(("negative", p.stem, p.read_text(), p.stem.split("_")[-1]))
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_one, items))
    n_pass = sum(r["pass"] for r in res)
    out = {"n": len(res), "n_pass": n_pass, "all_pass": n_pass == len(res), "results": res,
           "lint": cells.lint_all()}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/verifier_unit_tests.json").write_text(json.dumps(out, indent=1, default=str))
    for r in res:
        print(("PASS " if r["pass"] else "FAIL ") + f"{r['kind']:16s} {r['name']:28s} {r['cell']:12s} {r['verdict']:6s} "
              f"{r['reasons']} tracer={r['tracer']} disc={r['discipline']} topup={r['topup']}")
    print(f"{n_pass}/{len(res)} pass; lint {out['lint']['pass']}")


if __name__ == "__main__":
    main()
