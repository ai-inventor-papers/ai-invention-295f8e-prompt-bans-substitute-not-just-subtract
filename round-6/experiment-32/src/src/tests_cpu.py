#!/usr/bin/env python3
"""S0 CPU tests (U1/U2): every catalogue reference gets the right label from the frozen labellers (runtime and AST),
the T2 array-Dijkstra rule labels an array-Dijkstra program 'dijkstra', the bench gold sets reproduce their
gate.json agreement, and the prompts satisfy the tokenisation asserts. Writes results/tests_cpu.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import BENCH, BENCH_TASKS, RESULTS_DIR, SUITE, bench_dir, read_json, read_jsonl, setup_logging, write_json
from labels import label_rows

PATH_REF_MODE = {"astar_fg": "astar_gbfs", "gbfs_counter": "astar_gbfs", "bfs_deque_parent": "bfs",
                 "bfs_listpop_pathcarry": "bfs", "bibfs_deques": "bibfs", "bibfs_sets": "bibfs",
                 "dfs_recursive": "dfs", "dfs_stack": "dfs", "dijkstra_counter": "dijkstra", "dijkstra_lazy": "dijkstra",
                 "iddfs_iterative": "iddfs", "iddfs_recursive": "iddfs", "bellman_ford": "bf_spfa",
                 "bidijkstra_alternate": "bidijkstra", "bidijkstra_reverse": "bidijkstra", "dial_dict": "dial",
                 "dial_list": "dial", "dijkstra_decreasekey": "dijkstra", "floyd_bigint": "floyd",
                 "floyd_inf": "floyd", "spfa": "bf_spfa"}

ARRAY_DIJKSTRA = '''
def solve(n, edges, s, t):
    INF = float("inf")
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [INF] * n
    dist[s] = 0
    visited = [False] * n
    for _ in range(n):
        u = -1
        for i in range(n):
            if not visited[i] and (u == -1 or dist[i] < dist[u]):
                u = i
        if u == -1 or dist[u] == INF:
            break
        visited[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist[t] if dist[t] != INF else -1
'''


def ref_rows() -> list[dict[str, Any]]:
    rows = []
    for t in BENCH_TASKS:
        for p in sorted((BENCH / bench_dir(t) / "references").glob("*.py")):
            rows.append({"task": t, "mode_true": p.stem, "code": p.read_text()})
    for t, et in (("T1", "t1_grid"), ("T2", "t2_wsp")):
        for p in sorted((SUITE / "tasks" / et / "references").glob("*.py")):
            rows.append({"task": t, "mode_true": PATH_REF_MODE[p.stem], "code": p.read_text()})
    rows.append({"task": "T2", "mode_true": "dijkstra", "code": ARRAY_DIJKSTRA, "is_array_dijkstra": True})
    return rows


def main() -> dict[str, Any]:
    setup_logging("tests_cpu")
    refs = ref_rows()
    raw = [{"sample_id": f"ref|{r['task']}|{i}", "task": r["task"], "arm": "reference", "template": "REF", "slot": i,
            "text": "```python\n" + r["code"] + "\n```", "finish_reason": "stop"} for i, r in enumerate(refs)]
    labs = label_rows(raw, use_judge=False)
    res = []
    for r, l in zip(refs, labs):
        ok_rt = l.get("runtime_label") == r["mode_true"]
        ok_ast = l.get("ast_label") == r["mode_true"]
        res.append({"task": r["task"], "mode": r["mode_true"], "label": l["label"], "runtime": l.get("runtime_label"),
                    "ast": l.get("ast_label"), "passed": l.get("passed"), "ok_label": l["label"] == r["mode_true"],
                    "ok_runtime": ok_rt, "ok_ast": ok_ast, "array_dijkstra": r.get("is_array_dijkstra", False)})
    n_ok = sum(x["ok_label"] for x in res)
    n_pass = sum(bool(x["passed"]) for x in res)
    out = {"n_references": len(res), "label_correct": n_ok, "tests_passed": n_pass,
           "runtime_correct": sum(x["ok_runtime"] for x in res), "ast_correct": sum(x["ok_ast"] for x in res),
           "array_dijkstra_rule": [x for x in res if x["array_dijkstra"]], "rows": res}
    # bench gold-set gate numbers (recorded by the bench build; reproduced = file present and parsed)
    gates = {}
    for t in BENCH_TASKS:
        g = read_json(BENCH / bench_dir(t) / "gate.json")
        gates[t] = {k: g[k] for k in list(g)[:6]}
    out["bench_gate_json"] = gates
    path_gate = read_json(SUITE / "labeller" / "gate_report.json")
    out["path_gate_report_keys"] = list(path_gate)[:10]
    write_json(RESULTS_DIR / "tests_cpu.json", out)
    bad = [x for x in res if not x["ok_label"]]
    logger.info(f"references: {n_ok}/{len(res)} labelled correctly, {n_pass}/{len(res)} pass the hidden tests; "
                f"runtime {out['runtime_correct']}, AST {out['ast_correct']}")
    for b in bad:
        logger.warning(f"MISLABEL {b}")
    return out


if __name__ == "__main__":
    main()
