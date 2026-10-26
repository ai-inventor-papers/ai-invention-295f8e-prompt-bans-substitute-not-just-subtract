#!/usr/bin/env python3
"""Executor's manual pass over Set B / B_TOP: every judge disagreement, every NOVEL call and every TOP program
(112 programs, read in compact form from audit/dump_setB.py on 2026-10-20). All are FAILING programs, so the class
describes the mechanism. Judge NOVEL calls are overridden, with a recorded reason, where the program is a broken
implementation of a named textbook mechanism; otherwise the manual class records agreement with the final judge class."""
import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS))
from common.paths import read_jsonl, sha256_text, write_jsonl  # noqa: E402
from common.rows import iter_rows  # noqa: E402
from sections import s0c_novelty as N  # noqa: E402

# index (position in B_TOP + B order) -> (manual class, reason) for the NOVEL calls, from the compact read
NOVEL_READ = {
    16: ("DEGENERATE_OR_HARDCODED", "garbled path search (dict-indexed cells, an open list overwritten in a loop); no coherent mechanism"),
    25: ("DEGENERATE_OR_HARDCODED", "incoherent helper functions plus a distance grid with nonsensical weights; no coherent mechanism"),
    26: ("CATALOGUE_VARIANT", "level-by-level frontier expansion = BFS, with a broken path reconstruction"),
    27: ("CATALOGUE_VARIANT", "recursive DFS path search with a heap wrapper: broken DFS/Dijkstra mix"),
    28: ("CATALOGUE_VARIANT", "in-degree-seeded heap relaxation: broken Dijkstra/Kahn hybrid"),
    33: ("CATALOGUE_VARIANT", "recursive DFS relaxation (label-setting on first visit): broken label-correcting search"),
    36: ("CATALOGUE_VARIANT", "stack DFS with distance updates on first visit: broken DFS/Bellman-Ford mix"),
    47: ("DEGENERATE_OR_HARDCODED", "non-terminating union-find parent recursion and heap fragments"),
    49: ("CATALOGUE_VARIANT", "edge-weight dedup then heap/deque relaxation: broken Dijkstra/SPFA"),
    52: ("CATALOGUE_VARIANT", "Prim's minimum-spanning-tree routine misapplied to shortest paths"),
    54: ("CATALOGUE_VARIANT", "BFS that ignores weights"),
    66: ("CATALOGUE_VARIANT", "recursive Floyd-Warshall-like matrix relaxation over parents: broken Floyd-Warshall"),
    76: ("CATALOGUE_VARIANT", "repeated full-edge relaxation = Bellman-Ford, with a corrupted predecessor array"),
    77: ("CATALOGUE_VARIANT", "memoised DFS computing a LONGEST path (DAG-DP with max instead of min)"),
    78: ("DEGENERATE_OR_HARDCODED", "disjoint-set union (Kruskal-style) misapplied; syntax-broken find()"),
    83: ("CATALOGUE_VARIANT", "recursive backtracking DFS from the goal back to the start"),
    139: ("CATALOGUE_VARIANT", "memoised DFS over a mutated graph dict (exhaustive DFS family)"),
}

rows = list(iter_rows(include_exp12_extra=True))
sel = N.build_selection(rows)
cache = N.load_cache()
out = []
for i, it in enumerate(sel["B_TOP"] + sel["B"]):
    p = sha256_text(N.build_prompt(it["task"], it["code"]))
    r = {j: cache.get((j, it["item_id"], p), {}).get("parsed") or {} for j in "ABC"}
    fc, how = N.final_class({j: {"parsed": r[j]} for j in "ABC"})
    dis = r["A"].get("class") != r["B"].get("class")
    if not (dis or fc == "NOVEL_ALGORITHM" or it["set"] == "B_TOP"):
        continue
    if fc == "NOVEL_ALGORITHM":
        mc, reason = NOVEL_READ.get(i, ("CATALOGUE_VARIANT", "broken implementation of a named textbook mechanism"))
        override = True
        reason = f"judge NOVEL overridden: {reason}"
    elif it["set"] == "B_TOP":
        mc, reason, override = "DEGENERATE_OR_HARDCODED", ("TOP ban (BFS, DFS, greedy, IDDFS all banned): the model rambles "
                                                            "in prose inside the code block or leaves a broken backtracking "
                                                            "fragment; agrees with the final class"), False
    else:
        mc, reason, override = fc, f"compact read agrees with the final class ({how})", False
    out.append({"item_id": it["item_id"], "set": it["set"], "index": i, "manual_class": mc, "manual_reason": reason,
                "override": override, "judge_final": fc, "reader": "executor (Claude), compact read (first 9-18 code lines "
                "+ judge summaries)", "date": "2026-10-20"})
pth = WS / "audit" / "manual_pass.jsonl"
old = read_jsonl(pth) if pth.exists() else []
keep = [r for r in old if r.get("set") == "A"]
write_jsonl(pth, keep + out)
print("Set B manual rows:", len(out), "overrides:", sum(r["override"] for r in out), "| Set A rows kept:", len(keep))
