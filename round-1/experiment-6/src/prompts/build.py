#!/usr/bin/env python3
"""Prompt scaffold (paired design): user message = condition segment + blank line + shared task text.

segment(c, p) = P_p + ' ' + insert(c, p); no system prompt; the tokens of the shared task text and the chat-template
tail are identical across all conditions of a task, so every condition differs only before the task text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (ALIAS_LEXICON, CATALOGUE, MODES, PROMPTS_DIR, TASK_TEXT, TASK_TEXT_NO_FORMAT,  # noqa: E402
                    TASKS, write_json)

PREAMBLES = [
    "Here is a programming task.",
    "Please solve the task below.",
    "Below is a coding problem.",
    "Consider the following task.",
    "The task is described below.",
    "Here is a problem to solve in Python.",
    "Please complete the following assignment.",
    "Read the task below and solve it.",
    "This is a coding exercise.",
    "The following is a programming problem.",
]

SEED_ENTROPY = "seed=d32qxk4nt43"
SEED_WORD = "seed=(horse chair roof love)"

SEMANTIC_SEEDS = {
    # T1: implies a two-frontier search without naming it
    "T1": [
        "Two hikers set out at dawn from opposite ends of a long canyon, each carrying a pouch of chalk. Every hour, "
        "each hiker steps one stride further into every passage they can reach and chalks the ground they have "
        "covered. Neither hiker knows the canyon, but the moment one of them steps onto a chalk mark left by the "
        "other, they know a route exists, and they trace it back along both trails of marks.",
        "Picture two rescue teams digging toward each other through a collapsed mine, one starting at the entrance "
        "and one at the trapped miners. Each team widens its tunnels evenly, one ring of rock at a time, painting "
        "every chamber it clears. When a digger breaks into a chamber already painted by the other team, the two "
        "tunnel systems join, and the escape route is read off by following the paint back to each starting point.",
        "In an old story, two villages separated by a dense forest each send out scouts at the same moment. The "
        "scouts spread outward step by step, tying ribbons on every tree they pass, a red ribbon from the east "
        "village and a blue ribbon from the west. As soon as any scout spots a ribbon of the other colour, the "
        "villages have found each other, and the road between them follows the ribbons in both directions.",
        "Two ink drops fall onto opposite corners of a sheet of wet paper. Each stain spreads outward at the same "
        "steady pace, one ring at a time, never crossing the dry folds. The instant the two stains touch, the "
        "paper has revealed a channel connecting the two corners, and anyone can follow the blot from the point "
        "where they touched back to where each drop first landed.",
        "A lighthouse keeper and a ship's captain search for each other in a fog-filled harbour. Each lowers a "
        "lantern into every neighbouring channel in turn, widening the circle of lit water evenly after every "
        "round, and leaves a buoy in each channel already lit. When the captain's boat bumps into one of the "
        "keeper's buoys, the two lit regions have joined, and the safe passage is the chain of buoys from there.",
        "Two gardeners tend a hedge maze from opposite gates. Each morning, each gardener walks one more step into "
        "every open lane next to the ground already walked, scattering seeds of a different colour. On the morning "
        "a gardener finds a seed of the other colour underfoot, the paths have joined; the full walk from gate to "
        "gate is recovered by retracing each colour of seed back to its own gate.",
        "Imagine two search parties, one leaving the castle and one leaving the harbour, both looking for the same "
        "hidden road. Each party advances in waves: after every wave, every reachable courtyard next to the "
        "explored ground gets a flag with that party's crest. The search ends at the first courtyard flying both "
        "crests, and the road is assembled by walking from that courtyard back to the castle and to the harbour.",
        "Two friends lost in a city agree to look for each other in the same way. Each one checks every street "
        "corner one block further out from where they started, marking each visited corner on a shared map in "
        "their own colour. The first corner coloured by both friends is where their walks connect, and the route "
        "between their starting points follows one colour to that corner and the other colour away from it.",
        "Water is poured at the same time into two ends of a channel network carved into a stone courtyard, red "
        "dye at one end and blue dye at the other. The two dyed fronts creep forward through every open groove at "
        "the same rate. Where red first touches blue, the channels connect, and the course of the water from the "
        "red end to the blue end is traced by following each colour back to its spring.",
        "A tunnel crew and a mountain crew drill through the same range from opposite valleys. Each crew extends "
        "every open shaft by one length per shift and logs every chamber it reaches in its own ledger. When either "
        "crew enters a chamber already listed in the other crew's ledger, the passage is complete, and the route "
        "is the chain of chambers from one ledger joined to the reversed chain from the other.",
    ],
    # T2: implies relaxing every edge in rounds until a round brings no change, without naming it
    "T2": [
        "News spreads through a kingdom in rounds. In each round, every road carries a message from its source "
        "town to its destination town announcing how long the trip took so far plus the road's own travel time. "
        "Each town keeps only the shortest total it has ever heard. Once a whole round passes in which no town "
        "hears anything better, every town knows its true travel time.",
        "Every evening, each post office in a region sends a letter along every road leaving it, stating the best "
        "delivery time it currently knows plus that road's time. Each receiving office compares the letter with "
        "its own record and keeps whichever is smaller. The postmaster general waits until an evening goes by in "
        "which not a single office changes its record; at that point the records are final.",
        "Imagine a set of water towers connected by one-way pipes of different lengths. Repeatedly, someone walks "
        "along every pipe in the list and checks whether the level at the far tower could be improved by the near "
        "tower's level plus the pipe length. Whenever it can, the far tower is updated. When a complete walk over "
        "all the pipes changes nothing, the levels have settled.",
        "Rumours travel between market towns along one-way trade routes, each route with its own delay. On each "
        "market day every route is used once, and a town that hears a faster rumour about the capital than it "
        "knew before updates its note. Merchants say that after at most as many market days as there are towns, "
        "or as soon as one market day changes no note, the notes stop changing.",
        "A cartographer improves a map of travel times by sweeping through her entire list of one-way roads again "
        "and again. For each road she asks: would reaching the end town through this road be quicker than the "
        "time already written there? If so she rewrites it. She keeps sweeping the whole list until a full sweep "
        "produces no rewrite, and then she knows the map is exact.",
        "In a relay of messengers, every messenger carries the best-known time from the starting town to the town "
        "at the near end of a road, plus the time of the road itself. All roads are used in every round, and each "
        "town remembers only its smallest heard time. Rounds continue, again and again over the whole list of "
        "roads, until one passes in which no town's remembered time shrinks.",
        "Think of a group of accountants, each responsible for one office. In each pass, every accountant looks at "
        "every one-way transfer channel feeding their office and asks whether the cost recorded at the channel's "
        "source plus the channel fee beats their own recorded cost. They adopt any improvement. The passes repeat "
        "over all channels until a pass ends with no improvement anywhere.",
        "A rumour mill works in waves. In every wave, each one-way road is considered once: if the town at its "
        "start has a known travel time, the town at its end may lower its own known time to that value plus the "
        "road's length. The wave repeats over the full list of roads, and the process stops as soon as one "
        "complete wave lowers nothing at all.",
        "Picture beacons on hills linked by one-way signal paths, each path with its own delay. In every cycle, "
        "all paths are checked, and a hill updates its earliest signal time if the hill feeding it plus the path "
        "delay is earlier. Cycles repeat over every path in the list; after a cycle in which no hill updates, the "
        "earliest times are known for all hills.",
        "Shopkeepers in a network of towns compare delivery times along one-way routes. Each week every route is "
        "examined once, and a shop lowers its quoted delivery time whenever the shop at the route's start can "
        "offer a quicker total through that route. Weeks go by until one week passes in which no shop lowers its "
        "quote, and then the quotes are settled.",
    ],
}
SEMANTIC_IMPLIED = {"T1": "bidirectional_bfs", "T2": "bellman_ford_spfa"}

INSTRUCTIONS = {
    "instr_creative": [
        "Be creative.", "Be inventive.", "Show some creativity.", "Take a creative approach.",
        "Feel free to be creative.", "Approach this creatively.", "Use your creativity.", "Be imaginative.",
        "Get creative with it.", "Let your creativity show.",
    ],
    "instr_new_algo": [
        "Make a new algorithm.", "Design a new algorithm.", "Invent a new algorithm for this.",
        "Come up with a new algorithm.", "Create a new algorithm.", "Devise a new algorithm.",
        "Build a new algorithm for it.", "Write a new algorithm.", "Develop a new algorithm.",
        "Use a new algorithm of your own.",
    ],
    "instr_fully_novel": [
        "Make a fully novel algorithm never seen before.",
        "Invent a completely novel algorithm that has never been seen before.",
        "Design an entirely new algorithm nobody has seen before.",
        "Create a fully original algorithm that does not exist yet.",
        "Come up with a totally novel algorithm never used before.",
        "Devise a brand-new algorithm unlike anything seen before.",
        "Build a fully novel algorithm that no one has ever written.",
        "Write a completely original algorithm never seen before.",
        "Develop an algorithm so novel that it has never appeared before.",
        "Make an algorithm that is fully novel and never seen before.",
    ],
    "instr_enumerate": [
        "First list 10 different approaches to this task, one line each, then implement one of them.",
        "Begin by listing 10 different approaches to this task, one per line, and then implement one of them.",
        "Start with a list of 10 different ways to solve this task, one line each; then implement one.",
        "List 10 different approaches to this task first, one line each, and then implement one of them.",
        "Before coding, write down 10 different approaches to this task, one per line, then implement one.",
        "First enumerate 10 different approaches to this task, one line each, then pick one and implement it.",
        "Name 10 different approaches to this task first, one line each, then implement one of them.",
        "Give a list of 10 different approaches to this task, one per line, then implement one of them.",
        "First write 10 different approaches to this task as a one-line-each list, then implement one.",
        "Start by listing 10 distinct approaches to this task, one line each, then implement one of them.",
    ],
}

NEUTRAL_INSERTS = [
    "Note: the repository uses four-space indentation.",
    "Note: the project follows standard naming conventions.",
    "Note: the codebase is formatted with four spaces.",
    "Note: files in this repository use UTF-8 encoding.",
    "Note: the team reviews code on weekdays.",
    "Note: the repository uses Unix line endings.",
    "Note: the project is kept under version control.",
    "Note: the code style guide prefers short lines.",
    "Note: this file belongs to a larger project.",
    "Note: the team prefers descriptive commit messages.",
]

FRESH_WORDS = [
    "apple", "river", "candle", "window", "garden", "pencil", "mountain", "basket", "silver", "rabbit", "ladder",
    "orange", "violin", "blanket", "mirror", "pocket", "thunder", "meadow", "button", "kettle", "harbor", "lemon",
    "feather", "tunnel", "marble", "anchor", "cotton", "planet", "saddle", "copper", "jungle", "pillow", "turtle",
    "wagon", "zipper", "falcon", "carpet", "island", "rocket", "puzzle",
]

FORCED_TEMPLATES = ["Implement {X} to solve the task below.", "Solve the task below using {X}."]

DESCRIPTIONS = {
    "T1": {
        "bfs": [
            "explore cells in rings of increasing distance from the start using a first-in first-out line of "
            "cells, remembering where each cell was reached from.",
            "keep a waiting line of cells; always take the cell that has waited longest, add its unvisited open "
            "neighbours to the back of the line, and record each cell's parent.",
        ],
        "dfs": [
            "follow one corridor as far as it goes, and only when stuck step back to the most recent cell that "
            "still has an unexplored neighbour.",
            "keep a pile of cells; always take the most recently added cell, put its unvisited open neighbours on "
            "top of the pile, and record each cell's parent.",
        ],
        "bidirectional_bfs": [
            "grow two explored regions in rings at the same time, one from the start and one from the goal, and "
            "stop as soon as a cell is reached by both; join the two partial routes there.",
            "run two level-by-level explorations, one outward from each endpoint, alternating between them, and "
            "finish at the first cell both have touched.",
        ],
        "iddfs": [
            "repeatedly follow branches as deep as possible but never deeper than a maximum number of steps; start "
            "with a small maximum and raise it by one after each unsuccessful full attempt.",
            "run a series of complete searches that each go deep along one branch at a time with a step cap, "
            "increasing the cap by one each round until the goal is found.",
        ],
        "astar_greedy": [
            "keep a priority list of cells ordered by steps taken so far plus the grid distance (rows apart plus "
            "columns apart) to the goal, always expanding the cell with the smallest total.",
            "always expand the open cell whose estimated total route length, steps so far plus the remaining row "
            "and column difference to the goal, is smallest, using a heap.",
        ],
        "dijkstra_unit": [
            "keep a priority list of cells ordered only by the number of steps taken from the start, always "
            "expanding the cell with the smallest step count and never estimating the remaining distance.",
            "use a min-heap keyed by the cost so far, pop the cheapest cell, settle it, and push its neighbours "
            "with that cost plus one.",
        ],
    },
    "T2": {
        "dijkstra": [
            "repeatedly settle the not-yet-settled node with the smallest tentative distance, taken from a "
            "min-heap, and update the distances of its out-neighbours.",
            "grow a set of nodes whose distance is final, always adding the closest remaining node and lowering "
            "its neighbours' tentative distances.",
        ],
        "bellman_ford_spfa": [
            "sweep over the whole edge list again and again, lowering the distance of each edge's head whenever "
            "the tail's distance plus the weight is smaller, until a sweep changes nothing.",
            "repeat n-1 rounds; in each round try to improve every edge's end node using its start node's current "
            "distance plus the edge weight.",
        ],
        "bidirectional_dijkstra": [
            "run two cheapest-first searches at once, one forward from s along the edges and one backward from t "
            "along reversed edges, and stop when the two settled regions together certify the best total.",
            "alternate between expanding the cheapest node of a forward search from s and the cheapest node of a "
            "backward search from t over reversed edges, tracking the best route through any node seen by both.",
        ],
        "floyd_warshall": [
            "fill an n by n table of distances, then for every intermediate node k, every i and every j, replace "
            "the i-to-j entry with the i-to-k plus k-to-j entry when that is smaller.",
            "compute the distance between every pair of nodes with three nested loops over an intermediate node "
            "and two endpoints, then read off the s-to-t entry.",
        ],
        "dial": [
            "keep an array of lists indexed by integer distance; scan the lists in increasing index, take nodes "
            "from the current list, and put each improved neighbour into the list at its new distance.",
            "use one container per possible distance value instead of a heap, and process the containers in order "
            "of increasing distance, settling the nodes found in each.",
        ],
    },
}

GTS_STAGE1 = ("List 10 distinct algorithmic approaches to the following task, one per line, numbered 1-10, a name "
              "and one sentence each, no code.")
GTS_STAGE2 = "Implement the following approach: {item}"

GEN_CONDITIONS = ["baseline", "seed_entropy", "seed_word", "seed_semantic", "instr_creative", "instr_new_algo",
                  "instr_fully_novel", "instr_enumerate"]
STATE_ONLY_CONDITIONS = ["neutral_insert", "seed_entropy_fresh", "seed_word_fresh"]


def fresh_seeds() -> tuple[list[str], list[str]]:
    rng = np.random.default_rng(20261019)
    alphabet = list("abcdefghijklmnopqrstuvwxyz0123456789")
    ent = ["seed=" + "".join(rng.choice(alphabet, 11)) for _ in range(10)]
    words = ["seed=(" + " ".join(rng.choice(FRESH_WORDS, 4, replace=False)) + ")" for _ in range(10)]
    return ent, words


def insert(task: str, condition: str, p: int) -> str:
    if condition == "baseline":
        return ""
    if condition == "seed_entropy":
        return SEED_ENTROPY
    if condition == "seed_word":
        return SEED_WORD
    if condition == "seed_semantic":
        return SEMANTIC_SEEDS[task][p]
    if condition in INSTRUCTIONS:
        return INSTRUCTIONS[condition][p]
    if condition == "neutral_insert":
        return NEUTRAL_INSERTS[p]
    if condition == "seed_entropy_fresh":
        return fresh_seeds()[0][p]
    if condition == "seed_word_fresh":
        return fresh_seeds()[1][p]
    raise ValueError(condition)


def segment(task: str, condition: str, p: int) -> str:
    ins = insert(task, condition, p)
    return PREAMBLES[p] + (" " + ins if ins else "")


def user_message(seg: str, task: str, task_text: str | None = None) -> str:
    return seg + "\n\n" + (task_text if task_text is not None else TASK_TEXT[task])


def forced_segment(task: str, mode: str, frame: int) -> str:
    X = CATALOGUE[task][mode][0]
    return PREAMBLES[frame % 10] + " " + FORCED_TEMPLATES[frame // 10].format(X=X)


def described_segment(task: str, mode: str, j: int) -> str:
    desc = DESCRIPTIONS[task][mode][j // 5]
    return PREAMBLES[j % 5] + " Implement the approach described as: " + desc


def build_all() -> list[dict]:
    """Every prompt used anywhere in the artifact (generation and R-state collection)."""
    rows: list[dict] = []
    for task in TASKS:
        for cond in GEN_CONDITIONS + STATE_ONLY_CONDITIONS:
            for p in range(10):
                seg = segment(task, cond, p)
                rows.append(dict(prompt_id=f"{task}|{cond}|p{p}", task=task, condition=cond, paraphrase_id=p,
                                 segment=seg, user_message=user_message(seg, task),
                                 generated=cond in GEN_CONDITIONS))
        for mode in MODES[task]:
            for f in range(20):
                seg = forced_segment(task, mode, f)
                rows.append(dict(prompt_id=f"{task}|forced:{mode}|f{f}", task=task, condition=f"forced:{mode}",
                                 paraphrase_id=f, segment=seg, user_message=user_message(seg, task), generated=True))
            for j in range(10):
                seg = described_segment(task, mode, j)
                rows.append(dict(prompt_id=f"{task}|described:{mode}|d{j}", task=task,
                                 condition=f"described:{mode}", paraphrase_id=j, segment=seg,
                                 user_message=user_message(seg, task), generated=False))
        rows.append(dict(prompt_id=f"{task}|gts_stage1", task=task, condition="gts_stage1", paraphrase_id=-1,
                         segment=GTS_STAGE1, user_message=user_message(GTS_STAGE1, task, TASK_TEXT_NO_FORMAT[task]),
                         generated=True))
    return rows


def chat_text(tokenizer, message: str, thinking: bool) -> str:
    return tokenizer.apply_chat_template([{"role": "user", "content": message}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=thinking)


def chat_ids(tokenizer, message: str, thinking: bool) -> list[int]:
    return tokenizer(chat_text(tokenizer, message, thinking), add_special_tokens=False)["input_ids"]


def lexicon_hits(text: str) -> list[str]:
    low = text.lower()
    return [f"{mode}:{pat}" for mode, pats in ALIAS_LEXICON.items() for pat in pats if re.search(pat, low)]


def run_assertions(tokenizer) -> dict:
    """Unit-test assertions on the scaffold; raises AssertionError on any violation."""
    rows = build_all()
    report: dict = {"tail_tokens": {}, "token_counts": {}, "semantic_word_counts": {}}
    for task in ("T1", "T2"):
        # L = tokens of the shared task text + template tail (thinking off)
        tail_text = TASK_TEXT[task] + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        L = len(tokenizer(tail_text, add_special_tokens=False)["input_ids"])
        assert L >= 50, f"tail too short: {L}"
        gen_rows = [r for r in rows if r["task"] == task and r["condition"] != "gts_stage1"]
        tails = set()
        for r in gen_rows:
            ids = chat_ids(tokenizer, r["user_message"], thinking=False)
            tails.add(tuple(ids[-L:]))
            report["token_counts"].setdefault(task, {}).setdefault(r["condition"].split(":")[0], []).append(len(ids))
        assert len(tails) == 1, f"{task}: last {L} tokens differ across conditions ({len(tails)} variants)"
        report["tail_tokens"][task] = L
        for c, v in report["token_counts"][task].items():
            report["token_counts"][task][c] = {"min": min(v), "max": max(v), "mean": round(float(np.mean(v)), 1)}
        report["semantic_word_counts"][task] = [len(s.split()) for s in SEMANTIC_SEEDS[task]]
        for s in SEMANTIC_SEEDS[task]:
            assert 55 <= len(s.split()) <= 95, f"semantic seed length {len(s.split())} out of range"
    bad = []
    for task in ("T1", "T2"):
        for s in SEMANTIC_SEEDS[task]:
            if lexicon_hits(s):
                bad.append(("semantic", task, lexicon_hits(s), s[:60]))
        for mode, ds in DESCRIPTIONS[task].items():
            for d in ds:
                if lexicon_hits(d):
                    bad.append(("described", task, mode, lexicon_hits(d), d[:60]))
    assert not bad, f"catalogue names found in seeds/descriptions: {bad}"
    report["lexicon_violations"] = 0
    report["n_prompts"] = len(rows)
    return report


if __name__ == "__main__":
    from transformers import AutoTokenizer
    from common import model_id
    tok = AutoTokenizer.from_pretrained(model_id())
    rep = run_assertions(tok)
    rows = build_all()
    write_json(PROMPTS_DIR / "prompts.json", rows)
    write_json(PROMPTS_DIR / "assertions.json", rep)
    print(json.dumps(rep, indent=1)[:3000])
