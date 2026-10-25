#!/usr/bin/env python3
"""S6 prompts (exact texts committed in commit #1): the task specification, the condition segments of every cell,
the rule descriptions with two rewrites, the naming-check prompt and the slot / template / seed rules."""
from __future__ import annotations

from typing import Any

from common import sha256_text

DOCSTRING = ('    """Returns priority with which we want to add item to each bin.\n\n'
             '    Args:\n'
             '        item: Size of item to be added to the bin.\n'
             '        bins: Array of capacity for each bin.\n\n'
             '    Return:\n'
             '        Array of same size as bins with priority score of each bin.\n'
             '    """\n')

TASK_SPEC = (
    "Online bin packing. Items arrive one at a time and each must be placed immediately, without knowledge of future "
    "items, into a bin of fixed integer capacity; the goal is to use as few bins as possible. You will write the "
    "scoring heuristic that decides where each item goes. For every arriving item the packer calls "
    "priority(item, bins), where item is the item size (an integer) and bins is a numpy array with the remaining "
    "capacity of every bin in which the item fits, listed in the order in which the bins were created; bins that are "
    "still unused appear in this array with their full capacity. The item is placed into the bin with the highest "
    "score (the first such bin on ties). Use only numpy (imported as np) and the math module.\n\n"
    "```python\nimport numpy as np\n\n\ndef priority(item: float, bins: np.ndarray) -> np.ndarray:\n"
    + DOCSTRING + "```\n\nWrite the complete function in one Python code block.")

W_TEMPLATES = {"W1": "Do not use {X} for this task.", "W2": "Your solution must not rely on {X}.",
               "W3": "Avoid {X} entirely.", "W4": "{X} is not allowed here.",
               "W5": "Write a correct solution that does not use {X}."}
W_ROT = {"W1": 0, "W2": 1, "W3": 2, "W4": 3, "W5": 4}
DW_TEMPLATES = {"DW1": "Do not use any of the following rules for this task: {D}.",
                "DW2": "Your solution must not rely on any of the following rules: {D}.",
                "DW3": "Avoid each of the following rules entirely: {D}."}
DW_ROT = {"DW1": 0, "DW2": 1, "DW3": 2}
INSTR = {"INSTR_NEW": "Make a new algorithm.",
         "INSTR_LONG": "Make a fully novel algorithm never seen before. First explain your idea in about 2,000 words, "
                       "then give the complete function."}
DISPLAY = {"BF": "Best Fit", "FF": "First Fit", "WF": "Worst Fit", "AWF": "Almost Worst Fit", "LF": "Last Fit",
           "RF": "Random Fit"}

DESCRIPTIONS: dict[str, list[str]] = {
    "BF": ["putting each item into the bin that it would leave with the least spare room",
           "choosing, among the bins the item fits into, the one whose remaining capacity after placing the item is "
           "smallest",
           "placing each item where the leftover space in the chosen bin is minimised"],
    "FF": ["putting each item into the earliest-created bin that has room for it",
           "scanning the bins in the order they were created and placing the item into the first one it fits into",
           "always preferring the oldest bin that can still take the item"],
    "WF": ["putting each item into the already-used bin with the most spare room, and opening a new bin only when no "
           "used bin has room",
           "choosing, among the partly filled bins the item fits into, the one with the largest remaining capacity",
           "placing each item into the emptiest partly filled bin that can take it"],
    "AWF": ["putting each item into the already-used bin with the second-most spare room (or into the only used bin "
            "that has room), and opening a new bin only when no used bin has room",
            "choosing, among the partly filled bins the item fits into, the one with the second-largest remaining "
            "capacity",
            "placing each item into the second-emptiest partly filled bin that can take it"],
    "LF": ["putting each item into the most recently created bin that already holds items and has room for it",
           "scanning the partly filled bins from the newest to the oldest and placing the item into the first one it "
           "fits into",
           "always preferring the newest partly filled bin that can still take the item"],
    "RF": ["putting each item into a partly filled bin chosen uniformly at random among those that have room for it, "
           "and opening a new bin only when none has room",
           "choosing at random, with equal probability, one of the partly filled bins the item fits into",
           "placing each item into a randomly picked partly filled bin that can take it"],
}
NAMING_PROMPT = ("In online bin packing, which standard heuristic places each arriving item by the following rule: "
                 "{description}? Reply with the name of the heuristic only.")
NAMING_N = 20
NAMING_PASS = 16

# cells: index (for seeds), kind, k
CELLS = {"BASE": (0, "base", 0), "NAME_1": (1, "name", 1), "NAME_2": (2, "name", 2), "NAME_3": (3, "name", 3),
         "NAME_4": (4, "name", 4), "NAME_5": (5, "name", 5), "DESC_5": (6, "desc", 5), "HOLD_5": (7, "hold", 5),
         "INSTR_NEW": (8, "instr", 0), "INSTR_LONG": (9, "instr", 0)}
SCREEN_SLOTS = [("W1", 17), ("W2", 17), ("W3", 16)]          # slots 0-16, 17-33, 34-49
HOLD_SLOTS = [("W4", 25), ("W5", 25)]
DESC_SLOTS = [("DW1", 17), ("DW2", 17), ("DW3", 16)]
# reduction ladder (decisive OpenRouter cells): N 50 -> 40 -> 30, keeping every template balanced
LADDER = {50: {"screen": [17, 17, 16], "hold": [25, 25]}, 40: {"screen": [14, 13, 13], "hold": [20, 20]},
          30: {"screen": [10, 10, 10], "hold": [15, 15]}}


def join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def rotate(xs: list[Any], k: int) -> list[Any]:
    if not xs:
        return xs
    k %= len(xs)
    return xs[k:] + xs[:k]


def seed_for(cell: str, slot: int) -> int:
    return 1000 * CELLS[cell][0] + int(slot) + 1


def template_for(cell: str, slot: int, n_cell: int = 50) -> str | None:
    kind = CELLS[cell][1]
    if kind in ("base", "instr"):
        return None
    if kind == "hold":
        sizes = LADDER.get(n_cell, LADDER[50])["hold"]
        names = [w for w, _ in HOLD_SLOTS]
    else:
        sizes = LADDER.get(n_cell, LADDER[50])["screen"]
        names = [w for w, _ in (DESC_SLOTS if kind == "desc" else SCREEN_SLOTS)]
    # slots are numbered within the full 50-slot design; a reduced cell keeps the first sizes[t] slots of template t
    full = [17, 17, 16] if kind != "hold" else [25, 25]
    lo = 0
    for t, sz in enumerate(full):
        if lo <= slot < lo + sz:
            return names[t] if slot - lo < sizes[t] else None
        lo += sz
    return None


def slots_for(cell: str, n_cell: int) -> list[int]:
    kind = CELLS[cell][1]
    if kind in ("base", "instr"):
        return list(range(n_cell))
    return [s for s in range(50) if template_for(cell, s, n_cell) is not None]


def condition_segment(cell: str, slot: int, banned: list[str], s_desc: list[str] | None = None,
                      desc_text: dict[str, str] | None = None, n_cell: int = 50) -> tuple[str, str | None]:
    """Return (segment text, template id)."""
    kind = CELLS[cell][1]
    if kind == "base":
        return "", None
    if kind == "instr":
        return INSTR[cell], None
    w = template_for(cell, slot, n_cell)
    if w is None:
        raise ValueError(f"slot {slot} not in reduced cell {cell} (N {n_cell})")
    if kind == "desc":
        rules = list(s_desc or [])
        rot = rotate(rules, (slot + DW_ROT[w]) % max(1, len(rules)))
        D = "; ".join(desc_text[r] for r in rot)
        return DW_TEMPLATES[w].format(D=D), w
    k = len(banned)
    rot = rotate(list(banned), (slot + W_ROT[w]) % k)
    X = join_names([DISPLAY[r] for r in rot])
    seg = W_TEMPLATES[w].format(X=X)
    return seg[0].upper() + seg[1:], w


def render(cell: str, slot: int, banned: list[str], s_desc: list[str] | None = None,
           desc_text: dict[str, str] | None = None, n_cell: int = 50) -> dict[str, Any]:
    seg, w = condition_segment(cell, slot, banned, s_desc, desc_text, n_cell)
    prompt = (seg + "\n\n" + TASK_SPEC) if seg else TASK_SPEC
    return {"cell": cell, "slot": int(slot), "template": w, "condition": seg, "prompt": prompt,
            "seed": seed_for(cell, slot), "k": CELLS[cell][2], "prompt_sha256": sha256_text(prompt)}


def commitment_block() -> dict[str, Any]:
    return {"task_spec": TASK_SPEC, "task_spec_sha256": sha256_text(TASK_SPEC),
            "templates": W_TEMPLATES, "template_sha256": {k: sha256_text(v) for k, v in W_TEMPLATES.items()},
            "desc_templates": DW_TEMPLATES, "desc_template_sha256": {k: sha256_text(v) for k, v in DW_TEMPLATES.items()},
            "instr": INSTR, "instr_sha256": {k: sha256_text(v) for k, v in INSTR.items()},
            "w_rot": W_ROT, "dw_rot": DW_ROT, "display": DISPLAY, "descriptions": DESCRIPTIONS,
            "naming_prompt": NAMING_PROMPT, "naming_n": NAMING_N, "naming_pass": NAMING_PASS,
            "cells": CELLS, "screen_slots": SCREEN_SLOTS, "hold_slots": HOLD_SLOTS, "desc_slots": DESC_SLOTS,
            "ladder": LADDER, "seed_rule": "seed = 1000*cell_index + slot + 1",
            "rotation_rule": "rotation = (slot + W_ROT[w]) mod k; names joined 'A', 'A or B', 'A, B or C'; the "
                             "first letter of the segment is capitalised",
            "message_rule": "user message = condition segment + blank line + task spec (BASE: task spec only); no "
                            "system message"}
