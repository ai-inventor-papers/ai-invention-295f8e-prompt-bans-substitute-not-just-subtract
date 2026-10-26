#!/usr/bin/env python3
"""Stage 0 labeller re-check of the 15 existing tasks (results/labeller_recheck.json).

Bench tasks (13): rerun the frozen runtime + AST labellers (exp11 bench.common) on every gold_set.jsonl program and
every reference; compare with the stored adjudicated labels and with gate.json. Path tasks (T1/T2): rerun the exp8
suite labeller on its gold set. Style re-gate (T2): array-based Dijkstra (a linear min-scan over unvisited nodes)
is labelled dijkstra, never bellman_ford_spfa -- the structural rule label_worker5.array_dijkstra overrides both
labels; it is checked here on three array-Dijkstra programs and on the exp8 gold set (no program may change unless it
is a min-scan Dijkstra).
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import BENCH, RESULTS, SUITE, read_json, setup_logging, utc_now, write_json  # noqa: E402

ARRAY_DIJKSTRA = [
    '''
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
        for v in range(n):
            if not visited[v] and (u == -1 or dist[v] < dist[u]):
                u = v
        if u == -1 or dist[u] == INF:
            break
        visited[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist[t] if dist[t] < INF else -1
''',
    '''
def solve(n, edges, s, t):
    dist = {i: float("inf") for i in range(n)}
    dist[s] = 0
    unvisited = set(range(n))
    while unvisited:
        u = min(unvisited, key=lambda x: dist[x])
        if dist[u] == float("inf"):
            break
        unvisited.remove(u)
        for a, b, w in edges:
            if a == u and dist[u] + w < dist[b]:
                dist[b] = dist[u] + w
    return dist[t] if dist[t] != float("inf") else -1
''',
]


def bench_recheck() -> dict:
    from bench.common.astrules import ast_label
    from bench.common.catalogue import TASKS
    from bench.common.probes import run_trace
    from bench.common.rtrules import runtime_label

    out = {}
    for t, meta in TASKS.items():
        d = BENCH / meta["task_id"]
        gold = [json.loads(l) for l in (d / "gold_set.jsonl").read_text().splitlines() if l.strip()]
        refs = sorted((d / "references").glob("*.py"))

        def lab(code: str) -> tuple[str, str]:
            return runtime_label(t, run_trace(code, t)), ast_label(t, code)
        with ThreadPoolExecutor(10) as ex:
            g = list(ex.map(lambda r: lab(r["code"]), gold))
            rr = list(ex.map(lambda p: lab(p.read_text()), refs))
        adj = [r.get("adjudicated") for r in gold]
        n_adj = sum(1 for a in adj if a)
        rt_vs = sum(1 for (rl, _), a in zip(g, adj) if a and rl == a) / n_adj if n_adj else None
        same_rt = sum(1 for (rl, _), r in zip(g, gold) if rl == r.get("runtime")) / len(gold) if gold else None
        ref_rt = sum(1 for (rl, _), p in zip(rr, refs) if rl == p.stem) / len(refs) if refs else None
        ref_ast = sum(1 for (_, al), p in zip(rr, refs) if al == p.stem) / len(refs) if refs else None
        gate = read_json(d / "gate.json") if (d / "gate.json").exists() else {}
        g_rt = (gate.get("gold") or {}).get("runtime_vs_adjudicated")
        out[t] = {"n_gold": len(gold), "runtime_vs_adjudicated": rt_vs, "gate_runtime_vs_adjudicated": g_rt,
                  "within_0.02_of_gate": (rt_vs is not None and g_rt is not None and abs(rt_vs - g_rt) <= 0.02),
                  "same_runtime_label_as_frozen": same_rt, "ref_acc_runtime": ref_rt, "ref_acc_ast": ref_ast}
        logger.info(f"{t}: {out[t]}")
    return out


def path_recheck() -> dict:
    from label_worker5 import _path_mech, array_dijkstra

    gold = [json.loads(l) for l in (SUITE / "labeller" / "gold_set.jsonl").read_text().splitlines() if l.strip()]
    with ThreadPoolExecutor(10) as ex:
        mech = list(ex.map(lambda r: _path_mech(r["task"], r["code"]), gold))
    out = {}
    for task in ("t1", "t2"):
        idx = [i for i, r in enumerate(gold) if r["task"] == task]
        adj = [(i, gold[i].get("adjudicated")) for i in idx if gold[i].get("adjudicated")]
        rt = sum(1 for i, a in adj if mech[i]["runtime_label"] == a) / len(adj) if adj else None
        changed = [gold[i]["key"] for i in idx if task == "t2" and array_dijkstra(gold[i]["code"])]
        out[task] = {"n_gold": len(idx), "runtime_vs_adjudicated": rt, "n_adjudicated": len(adj),
                     "programs_hit_by_array_dijkstra_rule": changed,
                     "hit_programs_adjudicated": [gold[i].get("adjudicated") for i in idx
                                                  if gold[i]["key"] in set(changed)]}
    arr = [_path_mech("t2", c) for c in ARRAY_DIJKSTRA]
    out["array_dijkstra_style_regate"] = {
        "raw_runtime_labels": [m["runtime_label"] for m in arr], "raw_ast_labels": [m["ast_label"] for m in arr],
        "rule_fires": [array_dijkstra(c) for c in ARRAY_DIJKSTRA], "passed": [m["passed"] for m in arr],
        "final_label": ["dijkstra" if array_dijkstra(c) else m["runtime_label"] for c, m in zip(ARRAY_DIJKSTRA, arr)]}
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("recheck")
    for p in (str(SUITE), str(BENCH.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    res = {"utc": utc_now(), "bench": bench_recheck(), "path": path_recheck()}
    res["bench_all_refs_100"] = all(v["ref_acc_runtime"] == 1.0 and v["ref_acc_ast"] == 1.0
                                    for v in res["bench"].values())
    res["bench_all_within_0.02"] = all(v["within_0.02_of_gate"] for v in res["bench"].values())
    write_json(RESULTS / "labeller_recheck.json", res)
    logger.info(f"labeller recheck: refs 100% {res['bench_all_refs_100']}, within 0.02 {res['bench_all_within_0.02']}; "
                f"style re-gate {res['path']['array_dijkstra_style_regate']}")


if __name__ == "__main__":
    main()
