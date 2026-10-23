#!/usr/bin/env python3
"""TP-G2 (iteration 10, gen_plan_experiment_5_idx5) shared constants: the discipline x container cell table, the
words-only cell instructions and their 3 paraphrase frames, the forbidden-word audit, the frozen iteration-9 readout
parameters, the budget, and the hash-chained commitment log (genesis = sha256('iter10_tpg2')).

The iteration-9 modules copied into src/ (common, geometry, landing, states, stage_mcode, prompts_tp, programs,
label_tp, expansion, tpg, sample_or) and the iteration-9 tracer (tracer_v9, orderclass, probes_v9) are byte-identical
copies (inputs/SHA256SUMS lists the pristine copies under inputs/e46/src and inputs/e45/src) and are imported
unchanged; their ROOT resolves to this artifact's folder.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from common import (ALIAS_TABLE, CANON_ORDER, DATA, FIGS, LOGS, PRED, RESULTS, ROOT, SHORT_FORMS, STATES,  # noqa: F401
                    read_json, sha256_file, sha256_text, utc_now, write_json)

# ---------------------------------------------------------------------------------------------- prior artifacts
# Prior artifacts are read through ONE relative constant each (overridable by an environment variable): in the published
# repository every artifact is a sibling folder named by its artifact id. They are only needed to RE-RUN Stage 0
# (inputs/ already holds the copies) and Stages 1.6-1.8; the analysis reads inputs/ and cache/ inside this folder.
DEPS_DIR = Path(os.environ.get("TPG2_DEPS_DIR", str(ROOT.parent)))
E46 = Path(os.environ.get("TPG2_E46", str(DEPS_DIR / "art_VVA3P0ocZNA2")))       # iteration 9 TP-G (read only)
E45 = Path(os.environ.get("TPG2_E45", str(DEPS_DIR / "art_8nXdw3_lDAll")))       # iteration 9 TP-B (read only)
E44 = Path(os.environ.get("TPG2_E44", str(DEPS_DIR / "art_R-HSmXq2t97f")))       # iteration 8 (read only)
DS_DIR = Path(os.environ.get("TPG2_DS", str(DEPS_DIR / "art_j3Rm_lr2nzR6")))     # declared dataset dependency
DS_FILE = DS_DIR / "full_data_out.json"
IN46 = ROOT / "inputs" / "e46"
IN45 = ROOT / "inputs" / "e45"
IN44 = ROOT / "inputs" / "e44"
# Iteration 9's cached M-code states: bit-identical reduced copies (PRIMARY + SURV rows, blocks L-2..L+2) ship in
# cache/e46_states/ (the full E46 npz files are > 100 MB and are not published); fall back to E46's own cache/states.
_LOCAL_E46 = ROOT / "cache" / "e46_states"
E46_STATES = _LOCAL_E46 if (_LOCAL_E46 / "mcode_8b.npz").exists() else E46 / "cache" / "states"
AUDIT = ROOT / "audit"
AUDIT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------------------------- frozen readout
L_STAR = {"8b": 17, "32b": 33}                            # asserted against geometry_*_mcode_PRIMARY_R1.json
K_PRIMARY, K_SECOND = 15, 10                             # E46 src/tpg.py K_VERDICT / K_SECOND
READOUT = "R1"
MODELS10 = {
    "8b": {"repo": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218", "precision": "bf16",
           "n_keep": 20, "engine": "hf-bf16", "d": 4096},
    "32b": {"repo": "unsloth/Qwen3-32B-bnb-4bit", "revision": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",
            "precision": "nf4", "n_keep": 36, "engine": "hf-nf4", "d": 5120},
}


def ext_blocks(tag: str) -> list[int]:
    L = L_STAR[tag]
    return [0] + list(range(L - 2, L + 3))


B5 = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NB5 = ["bibfs", "biastar", "idastar", "jps", "dijkstra_unit"]
BANNED_DISC = ["LEV", "DFS", "HEU"]
NONBANNED_DISC = ["RLX", "RND", "CRD"]

# ---------------------------------------------------------------------------------------------- cell table
DISCIPLINES = ["LEV", "DFS", "HEU", "RLX", "RND", "CRD"]
CONTAINERS = ["DEQ", "STK", "HEAP", "ARR", "SET", "SLIST"]
DISC_NAMES = {"LEV": "level (BFS) order", "DFS": "depth-first (LIFO) order", "HEU": "goal-heuristic order",
              "RLX": "relaxation (sweeps / label-correcting re-push)", "RND": "random order",
              "CRD": "goal-independent coordinate-key order"}
CONT_NAMES = {"DEQ": "deque / FIFO queue", "STK": "list stack or recursion", "HEAP": "heapq with tuple keys",
              "ARR": "2-D arrays scanned (no frontier object)", "SET": "set frontier",
              "SLIST": "sorted list (bisect.insort / sort+pop)"}
CELL_INSTR: dict[str, str] = {
    "LEV_DEQ": "Keep the cells that are waiting to be explored in a first-in-first-out queue (collections.deque, "
               "taking cells from the left end) and always take the cell that has been waiting the longest.",
    "LEV_HEAP": "Keep the frontier in a binary heap (heapq) whose priority is the number of steps from the start "
                "cell, with ties broken by an insertion counter, and always pop the cell with the fewest steps.",
    "LEV_SET": "Keep the current ring of cells (all cells the same number of steps from the start) in a Python set; "
               "from it build the next ring as a new set of unvisited free neighbours, then replace the current ring "
               "with the new one, and repeat.",
    "LEV_ARR": "Use no queue, stack or heap: keep a 2-D distance grid, give the start distance 0, and for d = 0, 1, "
               "2, ... scan the whole grid for cells whose distance is d and give each of their unlabelled free "
               "neighbours distance d + 1; stop when the goal gets a distance or a scan labels nothing, then walk "
               "back from the goal along decreasing distances.",
    "DFS_STK": "Use a stack (a Python list with append and pop() from the end) or recursion, always continuing from "
               "the most recently discovered cell so that the search goes as deep as possible before it backs up.",
    "DFS_DEQ": "Keep the frontier in a collections.deque but use only its right end: append new cells on the right "
               "and take the next cell with pop() from the right.",
    "DFS_HEAP": "Keep the frontier in a heapq heap whose priority is the negative of an insertion counter, so the "
                "most recently added cell is always popped first.",
    "HEU_HEAP": "Keep the frontier in a heapq heap whose priority is the Manhattan distance from the cell to the goal "
                "(optionally plus the number of steps taken so far), and always pop the cell with the smallest "
                "priority.",
    "HEU_SLIST": "Keep the frontier as a Python list that stays sorted by the Manhattan distance to the goal (insert "
                 "(key, counter, cell) tuples with bisect.insort) and always take the first element of the list.",
    "HEU_ARR": "Use no queue, stack, heap or sorted list: keep a 2-D grid of open flags; at each step scan the whole "
               "grid for the open cell with the smallest Manhattan distance to the goal (ties by row, then column), "
               "close it, and open its unvisited free neighbours.",
    "RLX_ARR": "Use no queue, stack or heap: keep a 2-D distance grid (0 at the start, infinity elsewhere) and "
               "repeat full sweeps over the grid in row-major order, setting each free cell's distance to one plus "
               "the smallest neighbour distance whenever that is smaller, until a sweep changes nothing; then walk "
               "back from the goal along decreasing distances.",
    "RLX_STK": "Keep a worklist stack (a Python list with append and pop() from the end) and a distance table; "
               "whenever a cell's tentative distance improves, record the new distance and push the cell again, even "
               "if it was processed before; stop when the stack is empty, then rebuild the path from the goal with "
               "parent links.",
    "RLX_HEAP": "Keep a worklist in a heapq heap ordered by the cell's (row, col), not by distance; pop the cell with "
                "the smallest (row, col), and whenever a neighbour's tentative distance improves, record it and push "
                "that neighbour again, even if it was processed before; continue until the heap is empty, then "
                "rebuild the path from parent links.",
    "RND_HEAP": "Keep the frontier in a heapq heap whose priority is a fresh random number (random.random()) drawn "
                "when the cell is added, and always pop the cell with the smallest random key.",
    "RND_SET": "Keep the frontier as a Python set and choose the next cell to explore with random.choice over the "
               "frontier (convert it to a tuple first), removing the chosen cell from the set.",
    "CRD_HEAP": "Keep the frontier in a heapq heap keyed only by the cell's coordinates (row, col), ignoring the goal "
                "and the number of steps, and always pop the cell with the smallest (row, col).",
    "CRD_SLIST": "Keep the frontier as a Python list that stays sorted by the cell's coordinates (row, then column) "
                 "using bisect.insort, ignoring the goal and the number of steps, and always take the first element.",
    "PROBE": "Use a label-correcting method: keep a first-in-first-out queue (collections.deque, taking cells from "
             "the left end) and a distance table; whenever a neighbour's tentative distance improves, update it and "
             "append that neighbour to the queue again, even if it was processed before; when the queue is empty, "
             "rebuild the path from parent links.",
}
# round-3 rewording (used only for cells still short after 2 rounds)
CELL_INSTR_R3: dict[str, str] = {
    "LEV_DEQ": "Process cells strictly in the order they were discovered, using collections.deque with popleft().",
    "LEV_HEAP": "Use heapq with entries (steps_from_start, counter, cell); pop the smallest entry each time.",
    "LEV_SET": "Advance a whole ring of cells at a time: the frontier is a set of cells at distance d, and the next "
               "frontier is the set of their new free neighbours at distance d + 1.",
    "LEV_ARR": "Label distances on a 2-D list: on pass d, look at every cell of the grid and, for each cell labelled "
               "d, label its unlabelled free neighbours d + 1; no frontier container at all.",
    "DFS_STK": "Explore with a last-in-first-out stack held in a Python list (append / pop()), or with a recursive "
               "helper, always extending the newest cell first.",
    "DFS_DEQ": "Use collections.deque as a last-in-first-out structure: append() to add and pop() to remove, never "
               "popleft().",
    "DFS_HEAP": "Use heapq with entries (-counter, cell) where counter increases with every push, so the newest cell "
                "comes out first.",
    "HEU_HEAP": "Use heapq with entries whose first element is the Manhattan distance to the goal (you may add the "
                "steps so far) and pop the smallest entry each time.",
    "HEU_SLIST": "Maintain a Python list in ascending order of the Manhattan distance to the goal using "
                 "bisect.insort, and remove the first element each step.",
    "HEU_ARR": "Without any frontier container, keep 2-D boolean arrays of open and closed cells and, each step, scan "
               "every cell to find the open one nearest to the goal by Manhattan distance.",
    "RLX_ARR": "Compute distances by repeated full passes over a 2-D array (row by row, column by column), lowering "
               "each free cell's value to one more than its smallest neighbour, until a pass makes no change.",
    "RLX_STK": "Use a Python list as a last-in-first-out worklist of cells to re-examine; a cell is pushed every time "
               "its distance label drops, including cells that were already popped before.",
    "RLX_HEAP": "Use heapq as a worklist ordered by the tuple (row, col); every time a cell's distance label drops, "
                "push it again, including cells that were already popped before.",
    "RND_HEAP": "Use heapq with entries (random.random(), cell) so that frontier cells come out in random order.",
    "RND_SET": "Hold the frontier in a set and, each step, take a uniformly random member with "
               "random.choice(tuple(frontier)).",
    "CRD_HEAP": "Use heapq with entries (row, col): the frontier cell with the smallest row (then column) is always "
                "explored next, whatever the goal is.",
    "CRD_SLIST": "Keep the frontier in a list sorted with bisect.insort by (row, col) and always remove the first "
                 "element, whatever the goal is.",
    "PROBE": "Keep a FIFO queue (collections.deque with popleft) of cells whose distance label dropped; re-append a "
             "cell every time its label drops, even after it has been processed.",
}
REQUESTED_CELLS = [c for c in CELL_INSTR if c != "PROBE"]
ALL_CELLS = list(CELL_INSTR)


def cell_dc(cell: str) -> tuple[str, str]:
    """Requested (discipline, container). PROBE is measured LEV x DEQ on unit grids (surface variant)."""
    if cell == "PROBE":
        return "LEV", "DEQ"
    d, c = cell.split("_")
    return d, c


FRAMES = ["Design constraint for the search: {I}",
          "Use exactly this exploration strategy. {I}",
          "{I} Do not combine it with any other search technique."]
TAIL = "Return one Python code block defining solve(grid, start, goal); no explanation."
EXTRA_FORBIDDEN = ["breadth", "depth-first", "depth first", "dijkstra", "bellman", "ford", "spfa", "a-star", "astar",
                   "greedy", "best-first", "best first", "iterative deepening", "jump point", "bidirectional", "flood"]


def forbidden_regex() -> re.Pattern:
    pats: list[str] = []
    for k in CANON_ORDER:
        pats += [re.escape(a.lower()) for a in ALIAS_TABLE[k]]
        pats += SHORT_FORMS[k]
    pats += [r"\b" + re.escape(w) + r"\b" for w in EXTRA_FORBIDDEN]
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)


def spec() -> str:
    import prompts_tp

    return prompts_tp.SPEC()


# Amendment COMMIT0c (before round 1): 61% of round-0 programs failed the frozen suites on ONE edge case (grid ['#'],
# start == goal on a wall -> [] expected; they returned [start]); rounds >= 1 append this reminder for EVERY cell.
EDGE_HINT = "Check whether start or goal is a wall before handling the case start == goal."


# Amendment COMMIT0d (before round 2): the tail reminder was ignored (round-1 failures on the same case); round 2 puts
# the edge-case order inside the instruction paragraph instead, for every cell still below target.
EDGE_HINT2 = ("Handle the edge cases first, in this order: if start or goal is a wall, return []; otherwise, if start "
              "equals goal, return [start].")


def cell_prompt(cell: str, template: int, reworded: bool = False, hint: bool = False, hint2: bool = False) -> str:
    instr = (CELL_INSTR_R3 if reworded else CELL_INSTR)[cell]
    seg = FRAMES[template].replace("{I}", instr) + (" " + EDGE_HINT2 if hint2 else "")
    return seg + "\n\n" + spec() + "\n\n" + TAIL + (" " + EDGE_HINT if hint else "")


# ---------------------------------------------------------------------------------------------- commitments
COMMIT_LOG = ROOT / "commitments.log"
GENESIS = hashlib.sha256(b"iter10_tpg2").hexdigest()


def commit(payload: Path, label: str, note: str = "") -> dict[str, Any]:
    """Append {i, label, utc, prev_line_sha256, payload_sha256, payload_path, note}; line 0 chains on GENESIS."""
    lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    prev = sha256_text(lines[-1]) if lines else GENESIS
    e = {"i": len(lines), "label": label, "utc": utc_now(), "prev_line_sha256": prev,
         "payload_sha256": sha256_file(payload), "payload_path": str(Path(payload).resolve().relative_to(ROOT)),
         "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(e, sort_keys=True) + "\n")
    return e


def verify_chain() -> dict[str, Any]:
    if not COMMIT_LOG.exists():
        return {"ok": False, "problems": ["no commitments.log"], "entries": []}
    prev, problems, entries = GENESIS, [], []
    for i, ln in enumerate(COMMIT_LOG.read_text().splitlines()):
        e = json.loads(ln)
        entries.append(e)
        if e["prev_line_sha256"] != prev:
            problems.append(f"line {i}: chain break")
        p = ROOT / e["payload_path"]
        if not p.exists():
            problems.append(f"line {i}: payload missing")
        elif sha256_file(p) != e["payload_sha256"]:
            problems.append(f"line {i}: payload changed after commit ({e['payload_path']})")
        prev = sha256_text(ln)
    return {"ok": not problems, "problems": problems, "entries": entries}


def commit_utc(label: str) -> str | None:
    if not COMMIT_LOG.exists():
        return None
    for ln in COMMIT_LOG.read_text().splitlines():
        e = json.loads(ln)
        if e["label"] == label:
            return e["utc"]
    return None


def deviation(code: str, text: str) -> None:
    p = RESULTS / "deviations.json"
    devs = read_json(p) if p.exists() else []
    if not any(d["code"] == code for d in devs):
        devs.append({"code": code, "text": text, "utc": utc_now()})
        write_json(p, devs)
