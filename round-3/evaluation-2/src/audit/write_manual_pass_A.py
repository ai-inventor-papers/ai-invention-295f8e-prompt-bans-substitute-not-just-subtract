#!/usr/bin/env python3
"""Executor's manual pass over every Set A program (read in full on 2026-10-20 from audit/dump_for_manual_pass.py
output). Indices refer to the committed Set A order (audit/selection.jsonl). Writes audit/manual_pass.jsonl (Set A part)."""
import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))
from common.paths import write_jsonl  # noqa: E402
from common.rows import iter_rows  # noqa: E402
from sections import s0c_novelty as N  # noqa: E402

LM, CV = "LABELLER_MISS", "CATALOGUE_VARIANT"
UD = (LM, "unit-weight Dijkstra: heap ordered by path length / cost+1 from start, no heuristic", "dijkstra_unit")
CP = (CV, "heap pushed with a CONSTANT priority 1, so cells pop in (row, col) order: a generic whatever-first graph "
          "search with a visited set, not Dijkstra (both judges called it unit-weight Dijkstra)", "graph_search")
TB = (LM, "unit-weight Dijkstra with a Manhattan tie-break key (g, h); A*-like ordering only on ties", "dijkstra_unit")
manual = {i: (LM, "counting-sort selection: frequency dict, sorted distinct keys, cumulative count to k (the T03 "
                  "catalogue's counting sort, written with a dict)", "counting_sort") for i in range(13)}
manual.update({
    13: (CV, "sort + BST insertion that merges overlapping intervals, in-order traversal (interval-tree-like merge)", "interval_tree"),
    14: (LM, "A* with a list-min priority queue (f = g + Manhattan)", "astar"),
    15: TB, 16: (CV, "bidirectional BFS with per-node BFS restarts from alternating frontier pops", "bibfs"),
    17: UD, 18: CP, 19: UD,
    20: (CV, "generic graph search over a frontier of partial paths with random.choice selection (randomised order)", "graph_search"),
    21: CP, 22: TB, 23: UD, 24: UD, 25: UD, 26: CP, 27: UD, 28: UD, 29: CP, 30: CP, 31: UD, 32: CP,
    33: (CV, "best-first search with an ad-hoc priority cost + row*col of the last cell (list-min queue)", "best_first"),
    34: UD, 35: UD, 36: CP, 37: CP, 38: TB, 39: UD, 40: UD, 41: UD,
    42: (CV, "heap search plus straight-line 'jumps' that push every cell on the line (JPS-like, not true jump points)", "jps"),
    43: UD, 44: UD, 45: UD, 46: CP, 47: UD, 48: UD, 49: CP, 50: UD, 51: UD, 52: UD,
    53: (CV, "'bidirectional' BFS whose forward BFS runs to exhaustion before the backward one: effectively plain BFS", "bfs"),
    54: UD, 55: UD, 56: UD, 57: CP, 58: TB, 59: UD, 60: UD,
    61: (LM, "unit-weight Dijkstra with a g_cost map (named jump point search, no jumps)", "dijkstra_unit"),
    62: UD, 63: (CV, "'bidirectional' BFS whose forward BFS runs to exhaustion first: effectively plain BFS", "bfs"), 64: CP,
    65: (CV, "FIFO list.pop(0) relaxation: label-correcting (SPFA-like), not Dijkstra despite the comments", "bf_spfa"),
    66: (CV, "label-correcting relaxation with a heap of node ids (no distances in the heap): Bellman-Ford/SPFA family", "bf_spfa"),
    67: (CV, "two full Dijkstra runs (forward, reversed graph) + min over meeting nodes: bidirectional Dijkstra without early stop", "bidijkstra"),
    68: (LM, "Dijkstra with a list-min priority queue", "dijkstra"),
    69: (CV, "SPFA with a redundant visited set", "bf_spfa"),
    70: (LM, "SPFA: FIFO queue of improved nodes (no in-queue flag); stray example inputs at module level", "bf_spfa"),
    71: (CV, "label-correcting scan over a once-sorted, growing list (Bellman-Ford/SPFA family)", "bf_spfa"),
    72: (LM, "array Dijkstra with an O(n^2) minimum scan", "dijkstra"),
    73: (LM, "SPFA: FIFO queue relaxation without an in-queue flag (judge A's NOVEL call rejected: textbook SPFA)", "bf_spfa"),
    74: (LM, "Dijkstra with a list-min priority queue", "dijkstra"),
    75: (CV, "SPFA followed by dead Dijkstra-flavoured code that does not affect the result", "bf_spfa"),
    76: (CV, "deque label-correcting with 0-weight edges pushed left (0-1 BFS pattern on general weights; D'Esopo-Pape family)", "zero_one_bfs"),
    77: (CV, "two full Dijkstra runs (forward, reversed graph) + min over meeting nodes: bidirectional Dijkstra without early stop", "bidijkstra"),
})
rows = list(iter_rows(include_exp12_extra=True))
sel = N.build_selection(rows)
assert len(sel["A"]) == 78 and set(manual) == set(range(78)), (len(sel["A"]), sorted(set(range(78)) - set(manual)))
out = [{"item_id": it["item_id"], "set": "A", "index": i, "manual_class": manual[i][0], "manual_reason": manual[i][1],
        "manual_closest": manual[i][2], "reader": "executor (Claude), full program read", "date": "2026-10-20"}
       for i, it in enumerate(sel["A"])]
p = WS / "audit" / "manual_pass.jsonl"
old = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
keep = [r for r in old if r.get("set") != "A"]
write_jsonl(p, out + keep)
print("wrote", len(out), "Set A manual rows;", len(keep), "other rows kept")
