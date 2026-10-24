#!/usr/bin/env python3
"""TP-G2 factorial cell table (plan Stage 0.4): 6 expansion disciplines x 6 storage containers, 24 implementable
cells, each with three wording paraphrases of the same mechanics (storage + selection rule + marking + extra
constraint) followed by the frozen T1 SPEC. No algorithm name appears in any factorial prompt (lint below).
Top-up classes (BIBFS, IDDFS, JPS, BIASTAR) alternate a mechanics-only prompt (TU-DESC) and a named prompt
(TU-NAMED); names are allowed there because every program is name-scrubbed and teacher-forced under the neutral
twin, so the generating prompt never enters a state (deviation D-topup-names).
"""

from __future__ import annotations

import re
from typing import Any

from common import ALIAS_TABLE, SHORT_FORMS, alias_regex, CANON_ORDER, sha256_text

DISCIPLINES = ["BFSO", "DFSO", "HEUR", "COST", "RELAX", "RAND"]
CONTAINERS = ["DEQUE", "LIST", "CALL", "HEAP", "GRID2D", "SET"]
DISC_LONG = {"BFSO": "FIFO / level order", "DFSO": "LIFO / depth order", "HEUR": "goal-heuristic order",
             "COST": "path-cost order (relaxation)", "RELAX": "full-sweep relaxation rounds",
             "RAND": "random frontier order"}
CORE_DISC = ["BFSO", "HEUR", "COST"]
CORE_CONT = ["LIST", "HEAP", "GRID2D", "SET"]
TOPUP_CLASSES = ["bibfs", "iddfs", "jps", "biastar"]
EXTRA_BANNED = [r"dijkstra", r"bellman", r"a\*", r"best[- ]?first", r"breadth", r"depth[- ]?first", r"flood"]

NO_FRONTIER = "do not use any queue, deque, heap, set or list of frontier cells"
PATH_BACK = "Rebuild the returned path by following parent links back from the goal to the start."

# Each cell: S (storage), R (selection rule; HEUR cells use {KEY}), V (marking / bookkeeping), E (extra constraint).
CELLS: dict[str, dict[str, str]] = {
    "BFSO-DEQUE": {
        "S": "Keep the frontier in a collections.deque.",
        "R": "Add every newly discovered cell at the right end with append() and always take the next cell to "
             "expand from the left end with popleft(), so cells are expanded strictly in first-in first-out order.",
        "V": "Mark a cell as seen at the moment it is added to the deque and record its parent then.",
        "E": "Do not use heapq, a set as the frontier, or recursion."},
    "BFSO-LIST": {
        "S": "Keep the frontier in a plain Python list; do not import collections or heapq.",
        "R": "Append every newly discovered cell to the end of the list and take the next cell from the front, "
             "either with list.pop(0) or by advancing an integer head index into the list, so cells are expanded "
             "in first-in first-out order.",
        "V": "Mark a cell as seen at the moment it is appended and record its parent then.",
        "E": "Do not use a deque, heapq or recursion."},
    "BFSO-HEAP": {
        "S": "Keep the frontier in a heapq heap of tuples (counter, row, col), where counter is an integer that "
             "increases by one every time any cell is pushed.",
        "R": "Always pop the entry with the smallest counter, so cells come out in exactly the order in which they "
             "were inserted (first-in first-out); the counter is the only key, with no distances and no estimates.",
        "V": "Mark a cell as seen when it is pushed, never push a seen cell again, and record its parent then.",
        "E": "Do not use a deque or recursion, and do not compare or update distances."},
    "BFSO-GRID2D": {
        "S": "Store the search state only in 2-D lists the size of the grid: a level array initialised to -1 and a "
             "parent array; " + NO_FRONTIER + ".",
        "R": "Set the level of the start cell to 0. Then for d = 0, 1, 2, ... scan every cell of the grid row by "
             "row, and for every cell whose level equals d give each free neighbour whose level is still -1 the "
             "level d + 1 and record its parent. Stop when the goal has a level or when a whole scan assigns "
             "nothing.",
        "V": "A cell counts as visited once its level is no longer -1.",
        "E": PATH_BACK},
    "BFSO-SET": {
        "S": "Keep the current frontier as a Python set and build the next frontier as a new set; keep a set of "
             "visited cells and a parent dict.",
        "R": "Work level by level: expand every cell of the current frontier set, put each free unvisited "
             "neighbour into the next-frontier set, then replace the frontier by the next-frontier set. Stop as "
             "soon as the goal is reached or the frontier is empty.",
        "V": "Mark a cell visited when it is added to the next frontier and record its parent then.",
        "E": "Do not use a deque, heapq, a list used as a queue, or recursion."},
    "DFSO-DEQUE": {
        "S": "Keep the frontier in a collections.deque that is used as a stack.",
        "R": "Push every newly discovered cell at the right end with append() and always take the next cell from "
             "the same right end with pop(), so the most recently discovered cell is expanded first (last-in "
             "first-out) and the search goes as deep as possible before it backs up.",
        "V": "Mark a cell visited when it is pushed and record its parent then; never push a visited cell.",
        "E": "Do not use popleft(), heapq or recursion."},
    "DFSO-LIST": {
        "S": "Keep the frontier in a plain Python list used as a stack; do not import collections or heapq.",
        "R": "Append every newly discovered cell to the end of the list and always take the next cell from the "
             "end with list.pop(), so the most recently discovered cell is expanded first (last-in first-out) and "
             "the search goes as deep as possible before it backs up.",
        "V": "Mark a cell visited when it is pushed and record its parent then; never push a visited cell.",
        "E": "Do not use pop(0), a deque or recursion."},
    "DFSO-CALL": {
        "S": "Use a recursive helper function and the call stack only; do not use any explicit stack, queue, "
             "deque, heap or list of frontier cells.",
        "R": "The helper is called on a cell, marks it visited and, for each free unvisited neighbour in turn, "
             "calls itself recursively on that neighbour before trying the next neighbour; it returns as soon as "
             "the goal is reached.",
        "V": "Keep visited cells in a set or a 2-D boolean array and build the path from the recursion (keep a "
             "path list that is extended before each call and shortened after it, or prepend cells on the way "
             "back).",
        "E": "Grids can be 30x30, so raise the recursion limit with sys.setrecursionlimit."},
    "DFSO-HEAP": {
        "S": "Keep the frontier in a heapq heap of tuples (key, row, col), where key = -counter and counter is an "
             "integer that increases by one at every push.",
        "R": "Always pop the entry with the smallest key, that is the most recently pushed cell, so the heap "
             "behaves as a last-in first-out stack and the search goes as deep as possible first.",
        "V": "Mark a cell visited when it is pushed and record its parent then; never push a visited cell.",
        "E": "Use no distances, no estimates, no relaxation and no recursion."},
    "HEUR-HEAP": {
        "S": "Keep the frontier in a heapq heap of tuples (key, counter, row, col), where counter is only a "
             "tie-breaker that increases at every push.",
        "R": "Always pop the frontier cell with the smallest key, where {KEY}",
        "V": "{VMARK}",
        "E": "Do not use a deque or recursion."},
    "HEUR-LIST": {
        "S": "Keep the frontier in a plain Python list; do not import heapq or collections.",
        "R": "At every step select the frontier cell with the smallest key, either by keeping the list sorted with "
             "bisect.insort on (key, counter, row, col) tuples and taking its first element, or by scanning the "
             "whole list for the minimum key and removing it with pop(i); here {KEY}",
        "V": "{VMARK}",
        "E": "Do not use heapq, a deque or recursion."},
    "HEUR-GRID2D": {
        "S": "Store the search state only in 2-D lists the size of the grid: an open-flag array, a closed-flag "
             "array, a steps array and a parent array; " + NO_FRONTIER + ".",
        "R": "At every step scan the whole grid row by row for the open cell with the smallest key, close it, and "
             "open each free neighbour that is not closed (updating its steps and parent when it is new or its "
             "steps improve); here {KEY}",
        "V": "Stop when the goal is closed or no open cell remains.",
        "E": PATH_BACK},
    "HEUR-SET": {
        "S": "Keep the open (frontier) cells in a Python set, with dicts for parents and step counts.",
        "R": "At every step take the open cell with the smallest key using min(open_cells, key=...), remove it "
             "from the set and add its free neighbours that were not expanded yet (updating steps and parent when "
             "they are new or improve); here {KEY}",
        "V": "Keep a set of expanded cells and never expand a cell twice.",
        "E": "Do not use heapq, a deque or recursion."},
    "COST-HEAP": {
        "S": "Keep a dict (or 2-D list) dist with the best known number of steps from the start, and a heapq heap "
             "of (dist, row, col) tuples.",
        "R": "Repeatedly pop the entry with the smallest distance; if its distance is larger than the recorded "
             "dist of that cell it is a stale entry and is skipped. For each free neighbour compute new = d + 1, "
             "and if new < dist[neighbour] (unknown cells count as infinity) set dist[neighbour] = new, record the "
             "parent and push (new, neighbour). The key is the step count from the start only: there is no "
             "estimate toward the goal.",
        "V": "Stop when the goal is popped.",
        "E": PATH_BACK},
    "COST-LIST": {
        "S": "Keep dist (best known steps from the start) in a dict or 2-D list and the frontier in a plain "
             "Python list of cells; do not import heapq or collections.",
        "R": "At every step scan the frontier list for the cell with the smallest dist, remove it with pop(i) and "
             "skip it if it was already finalised; for each free neighbour, if dist[cell] + 1 < dist[neighbour] "
             "(unknown cells count as infinity), update dist and parent and append the neighbour to the list. No "
             "estimate toward the goal is used.",
        "V": "Stop when the goal is finalised.",
        "E": PATH_BACK},
    "COST-GRID2D": {
        "S": "Store dist (initialised to infinity, start = 0), a done flag and the parent in 2-D lists the size of "
             "the grid; " + NO_FRONTIER + ".",
        "R": "At every step scan the whole grid row by row for the not-done cell with the smallest finite dist, "
             "mark it done, and for each free neighbour, if dist[cell] + 1 < dist[neighbour], update dist and "
             "parent. No estimate toward the goal is used.",
        "V": "Stop when the goal is done or no not-done cell with a finite dist remains.",
        "E": PATH_BACK},
    "COST-SET": {
        "S": "Keep the open cells in a Python set and the best known distances from the start in a dict.",
        "R": "At every step take u = min(open_cells, key=lambda c: dist[c]), remove it from the set, and for each "
             "free neighbour v, if dist[u] + 1 < dist.get(v, infinity), set dist[v] and parent[v] and add v to the "
             "open set. No estimate toward the goal is used.",
        "V": "Stop when the goal is removed from the open set.",
        "E": "Do not use heapq, a deque or recursion."},
    "RELAX-GRID2D": {
        "S": "Store dist (initialised to infinity, start = 0) and the parent only in 2-D lists the size of the "
             "grid; " + NO_FRONTIER + ", and no recursion.",
        "R": "Repeat full passes over the grid: in each pass visit every cell row by row and, for every free cell "
             "with a finite dist, try each free neighbour: if dist[cell] + 1 < dist[neighbour], set "
             "dist[neighbour] = dist[cell] + 1 and record the parent. Stop when a complete pass changes nothing "
             "(or after rows*cols passes).",
        "V": "Every pass processes all cells; there is no frontier.",
        "E": PATH_BACK},
    "RELAX-LIST": {
        "S": "Build once, at the start, an explicit Python list of directed edges (u, v) between adjacent free "
             "cells, and keep dist (start = 0, others infinity) and parent in a dict or 2-D list.",
        "R": "Then repeat rounds: in each round loop over the entire edge list and, whenever dist[u] + 1 < "
             "dist[v], set dist[v] = dist[u] + 1 and parent[v] = u. Stop when a whole round changes nothing (or "
             "after number-of-cells - 1 rounds).",
        "V": "Every round processes all edges; there is no frontier, queue or heap.",
        "E": PATH_BACK},
    "RELAX-SET": {
        "S": "Keep the set of all free cells in a Python set and the distances in a dict (start = 0, a missing "
             "cell counts as infinity).",
        "R": "Repeat full sweeps: in each sweep iterate over every cell of the set of free cells and, for every "
             "neighbour of a cell with a known distance, if dist[cell] + 1 < dist.get(neighbour, infinity), "
             "update dist and parent. Stop when a whole sweep changes nothing.",
        "V": "Every sweep visits all free cells; there is no frontier, queue or heap.",
        "E": PATH_BACK},
    "RAND-LIST": {
        "S": "Keep the frontier in a plain Python list; do not import heapq or collections.",
        "R": "At every step remove a uniformly random element of the list (i = random.randrange(len(frontier)), "
             "then pop(i), or swap it with the last element and pop) and expand it; there is no ordering rule "
             "other than chance.",
        "V": "Mark a cell as seen when it is added and record its parent then.",
        "E": "Use the random module and never call random.seed."},
    "RAND-HEAP": {
        "S": "Keep the frontier in a heapq heap of tuples (random_key, row, col), where random_key = "
             "random.random() is drawn fresh when the cell is pushed.",
        "R": "Always pop the smallest random key, so the expansion order is random.",
        "V": "Mark a cell as seen when it is pushed and record its parent then.",
        "E": "Never call random.seed; use no distances and no estimates."},
    "RAND-SET": {
        "S": "Keep the frontier in a Python set.",
        "R": "At every step pick c = random.choice(tuple(frontier)), a uniformly random member, remove it from the "
             "set and expand it.",
        "V": "Mark a cell as seen when it is added and record its parent then.",
        "E": "Never call random.seed; do not use heapq or a deque."},
    "RAND-DEQUE": {
        "S": "Keep the frontier in a collections.deque.",
        "R": "At every step rotate the deque by a random amount, frontier.rotate(random.randrange(len(frontier))), "
             "and then take the cell at the left end with popleft().",
        "V": "Mark a cell as seen when it is added and record its parent then.",
        "E": "Never call random.seed; do not use heapq."},
}
HEUR_KEYS = {
    "h": ("the key is the Manhattan distance from the cell to the goal, |row - goal_row| + |col - goal_col|, and "
          "nothing else: always expand the frontier cell that looks closest to the goal.",
          "Mark a cell as seen when it is first added to the frontier and record its parent then; never add a "
          "seen cell again."),
    "gh": ("the key is steps + Manhattan distance, where steps is the number of moves from the start to the cell "
           "along the best path found so far and the Manhattan distance to the goal is |row - goal_row| + "
           "|col - goal_col|.",
           "Keep the best known steps of every cell; add or update a neighbour when its new steps value is "
           "smaller than the recorded one, record its parent then, and skip popped entries of cells that were "
           "already expanded."),
}
FRAMES = ["W0", "W1", "W2"]


def cell_parts(cell: str, heur_key: str | None) -> dict[str, str]:
    p = dict(CELLS[cell])
    if cell.startswith("HEUR"):
        key, vmark = HEUR_KEYS[heur_key or "h"]
        p["R"] = p["R"].replace("{KEY}", key)
        p["V"] = p["V"].replace("{VMARK}", vmark)
    return p


def mechanics(cell: str, frame: str, heur_key: str | None = None) -> str:
    p = cell_parts(cell, heur_key)
    if frame == "W0":
        return "Write the search as follows. " + " ".join([p["S"], p["R"], p["V"], p["E"]])
    if frame == "W1":
        return ("Required search procedure, step by step:\n1. " + p["S"] + "\n2. " + p["R"] + "\n3. " + p["V"] +
                "\n4. " + p["E"])
    return ("Implementation constraints (all of them must hold):\n- Selection rule: " + p["R"] + "\n- Storage: " +
            p["S"] + "\n- Bookkeeping: " + p["V"] + "\n- Also: " + p["E"])


def spec_text() -> str:
    import prompts_tp

    return prompts_tp.SPEC()


def cell_prompt(cell: str, slot: int) -> dict[str, Any]:
    """slot = attempt index within the cell; wording = slot mod 3; HEUR key alternates by slot parity."""
    disc, cont = cell.split("-")
    frame = FRAMES[slot % 3]
    hk = ("h" if slot % 2 == 0 else "gh") if disc == "HEUR" else None
    mech = mechanics(cell, frame, hk)
    prompt = mech + "\n\n" + spec_text()
    return {"kind": "factorial", "cell": cell, "discipline": disc, "container": cont, "slot": slot,
            "wording": frame, "heur_key": hk, "prompt_id": f"{cell}|{frame}|{hk or '-'}",
            "prompt": prompt, "prompt_sha256": sha256_text(prompt)}


TOPUP_DESC = {
    "bibfs": "Run two first-in first-out searches at the same time, one growing from the start and one growing "
             "from the goal, each with its own collections.deque and its own parent dict. Alternate between the "
             "two sides, expanding one whole level of one side and then one whole level of the other. As soon as a "
             "cell discovered by one side has already been reached by the other side, stop and join the two half "
             "paths at that meeting cell (start ... meeting cell ... goal).",
    "iddfs": "Use repeated depth-limited searches: for limit = 0, 1, 2, ... run a deep-first walk from the start "
             "(recursive or with an explicit stack) that never goes more than limit moves away from the start, "
             "restarting from scratch every time the limit grows, and return the path as soon as one run reaches "
             "the goal. Inside one run keep a dict best_depth of the smallest depth at which each cell was reached "
             "in that run and do not continue from a cell again at the same or a larger depth, so that each run "
             "stays fast on 30x30 grids. Stop growing the limit once it exceeds rows*cols.",
    "jps": "Search with a heapq heap ordered by f = g + Manhattan distance to the goal, but do not push every "
           "neighbour. From a popped cell, call two jump helpers for the 4 directions. A horizontal jump steps "
           "repeatedly left or right inside a loop and returns None at a wall or the grid edge, or returns the "
           "cell when it is the goal or when it has a forced vertical neighbour (a free cell above or below it "
           "whose cell one step back is a wall). A vertical jump steps repeatedly up or down inside a loop and "
           "returns None at a wall or the edge, or returns the cell when it is the goal or when a horizontal jump "
           "from it (in either direction) finds a jump point. Only the returned jump points are pushed into the "
           "heap, with g increased by the number of steps jumped and their parent recorded. At the end, fill in "
           "the straight-line cells between consecutive jump points so that the returned path moves one cell at "
           "a time.",
    "biastar": "Run two heuristic searches at once: a forward search from the start whose heapq heap is ordered by "
               "g + Manhattan distance to the goal, and a backward search from the goal whose own heapq heap is "
               "ordered by g + Manhattan distance to the start. Alternate one expansion on each side, keeping "
               "separate g dicts and parent dicts. Stop when a cell expanded by one side has been reached by the "
               "other side (or when the best f on either heap is no smaller than the best meeting cost found), and "
               "join the two half paths at the best meeting cell.",
}
TOPUP_NAMES = {"bibfs": "bidirectional breadth-first search (BFS from both ends)",
               "iddfs": "iterative deepening depth-first search (IDDFS)",
               "jps": "jump point search (JPS) on the 4-connected grid",
               "biastar": "bidirectional A* search"}


def topup_prompt(cls: str, slot: int) -> dict[str, Any]:
    kind = "TU-DESC" if slot % 2 == 0 else "TU-NAMED"
    desc = TOPUP_DESC[cls]
    head = ("Write the search as follows. " if kind == "TU-DESC" else
            f"Implement {TOPUP_NAMES[cls]}. It works as follows. ")
    prompt = head + desc + "\n\n" + spec_text()
    return {"kind": "topup", "cell": cls, "discipline": cls, "container": None, "slot": slot, "wording": kind,
            "heur_key": None, "prompt_id": f"{cls}|{kind}", "prompt": prompt, "prompt_sha256": sha256_text(prompt)}


def lint_regex() -> re.Pattern:
    pats = []
    for k in CANON_ORDER:
        pats += [re.escape(a.lower()) for a in ALIAS_TABLE[k]] + SHORT_FORMS[k]
    pats += EXTRA_BANNED
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)


def lint_all() -> dict[str, Any]:
    rx = lint_regex()
    hits = []
    n = 0
    for cell in CELLS:
        for slot in range(6):
            p = cell_prompt(cell, slot)
            mech = p["prompt"][: p["prompt"].index("Task: write a Python")]
            n += 1
            for m in rx.finditer(mech):
                hits.append({"cell": cell, "slot": slot, "hit": m.group(0)})
    _ = alias_regex
    return {"n_prompts_checked": n, "n_hits": len(hits), "hits": hits[:20], "pass": not hits}


def all_cells() -> list[str]:
    return list(CELLS)


def in_core(cell: str) -> bool:
    d, c = cell.split("-")
    return d in CORE_DISC and c in CORE_CONT
