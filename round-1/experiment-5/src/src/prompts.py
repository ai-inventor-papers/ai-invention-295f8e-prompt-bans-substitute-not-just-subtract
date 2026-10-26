"""Frozen prompt set (STEP 2): task specs, neutral lead-ins P0..P49, ban lead-ins B0..B9,
chat prompts (instruct chat template, thinking off) and template-free docstring prompts.

Run:  .venv/bin/python src/prompts.py   -> data/prompts.json (+ token-identity checks)
"""
from __future__ import annotations

import json
import re
import sys

from loguru import logger

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import DATA, MB, MI, setup_logging, sha256_text  # noqa: E402

SPEC = {
    "t1": ("Task: write a Python function solve(grid, start, goal). grid is a list of equal-length strings in which . "
           "is a free cell and # is a wall. start and goal are (row, col) tuples of free cells. A move goes up, down, "
           "left or right to a free cell inside the grid. Return a list of (row, col) tuples forming a valid path from "
           "start to goal, including both ends; any valid path is accepted. If goal cannot be reached, return an empty "
           "list. The grid has at most 30 rows and 30 columns. Use only the Python standard library."),
    "t2": ("Task: write a Python function solve(n, edges, s, t). The graph is directed with nodes 0..n-1 (n <= 100). "
           "edges is a list of (u, v, w) tuples, each an edge from u to v with integer weight 0 <= w <= 100; there may "
           "be cycles, self-loops and parallel edges. Return the length of the shortest path from s to t as an int, or "
           "-1 if t is unreachable from s. If s == t return 0. Use only the Python standard library."),
}
FORMAT = " Return only one ```python code block containing the complete function and any imports or helpers it needs."
SIG = {
    "t1": "def solve(grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:",
    "t2": "def solve(n: int, edges: list[tuple[int, int, int]], s: int, t: int) -> int:",
}

# P0..P9 are the sampling paraphrases (verbatim from the plan); P10..P49 complete the 50 for the direction.
P_FIRST10 = [
    "Solve the following programming task.",
    "Please complete the coding task below.",
    "Here is a programming problem for you.",
    "Write a solution to the task described below.",
    "Complete the following Python exercise.",
    "Your job is to implement the function described below.",
    "The task below needs a working implementation.",
    "Please write code for the following problem.",
    "Read the task and implement it.",
    "Below is a small coding assignment.",
]
_OPENERS = [
    "Solve the following {o}.",
    "Please complete the {o} below.",
    "Here is a {o} for you.",
    "Write a solution to the {o} described below.",
    "Complete the following {o}.",
    "Your job is to finish the {o} described below.",
    "The {o} below needs a working implementation.",
    "Please write code for the following {o}.",
    "Read the {o} and implement it.",
    "Below is a {o}.",
]
_OBJECTS = ["programming task", "coding task", "Python exercise", "coding assignment", "programming problem",
            "Python task", "coding problem", "small programming exercise"]

BAN = {
    "t1": [
        "Do not use BFS.",
        "Do not use breadth-first search.",
        "You must not use BFS (breadth-first search).",
        "Avoid breadth-first search entirely.",
        "Your solution must not be a BFS.",
        "Do not implement breadth-first search (BFS).",
        "BFS is not allowed.",
        "Do not solve this with breadth-first search.",
        "Using BFS is forbidden.",
        "Do not use a breadth-first search (BFS) approach.",
    ],
    "t2": [
        "Do not use Dijkstra.",
        "Do not use Dijkstra's algorithm.",
        "You must not use Dijkstra (Dijkstra's algorithm).",
        "Avoid Dijkstra's algorithm entirely.",
        "Your solution must not be a Dijkstra.",
        "Do not implement Dijkstra's algorithm (Dijkstra).",
        "Dijkstra is not allowed.",
        "Do not solve this with Dijkstra's algorithm.",
        "Using Dijkstra is forbidden.",
        "Do not use a Dijkstra's algorithm (Dijkstra) approach.",
    ],
}
LEXICON = ["search", "queue", "stack", "heap", "graph", "bfs", "dfs", "dijkstra", "fast", "efficient", "optimal",
           "shortest", "creative", "novel"]


def neutral_segments() -> list[str]:
    segs = list(P_FIRST10)
    for o in _OBJECTS:
        for op in _OPENERS:
            s = op.format(o=o)
            if s not in segs:
                segs.append(s)
            if len(segs) == 50:
                return segs
    raise RuntimeError("not enough neutral segments")


def lexicon_ok(seg: str) -> bool:
    low = seg.lower()
    return not any(re.search(re.escape(w), low) for w in LEXICON)


def user_content(seg: str, task: str) -> str:
    return seg + "\n\n" + SPEC[task] + FORMAT


def tf_prompt(seg: str, task: str) -> str:
    return '"""\n' + seg + "\n\n" + SPEC[task] + '\n"""\n\n' + SIG[task] + "\n"


def build() -> dict:
    from transformers import AutoTokenizer

    tok_i = AutoTokenizer.from_pretrained(MI)
    tok_b = AutoTokenizer.from_pretrained(MB)
    P = neutral_segments()
    assert len(P) == 50 and len(set(P)) == 50
    bad = [s for s in P if not lexicon_ok(s)]
    assert not bad, f"lexicon violation: {bad}"
    out: dict = {"spec": SPEC, "format_sentence": FORMAT, "sig": SIG, "neutral": P, "ban": BAN,
                 "lexicon": LEXICON, "chat": {}, "tf": {}, "checks": {}}
    n_identical = 0
    tails = set()
    for task in ("t1", "t2"):
        out["chat"][task] = {"baseline": [], "ban": []}
        out["tf"][task] = {"baseline": [], "ban": []}
        for kind, segs in (("baseline", P), ("ban", BAN[task])):
            for i, seg in enumerate(segs):
                msgs = [{"role": "user", "content": user_content(seg, task)}]
                s = tok_i.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, tokenize=False)
                ids_i = tok_i(s, add_special_tokens=False)["input_ids"]
                ids_b = tok_b(s, add_special_tokens=False)["input_ids"]
                assert ids_i == ids_b, f"token ids differ for {task}/{kind}/{i}"
                n_identical += 1
                tail = tok_i.decode(ids_i[-8:])
                tails.add(tail)
                out["chat"][task][kind].append({"id": f"{'P' if kind == 'baseline' else 'B'}{i}", "seg": seg,
                                                "text": s, "n_tokens": len(ids_i), "sha256": sha256_text(s),
                                                "token_ids": ids_i})
                tfp = tf_prompt(seg, task)
                ids_tf_b = tok_b(tfp, add_special_tokens=False)["input_ids"]
                ids_tf_i = tok_i(tfp, add_special_tokens=False)["input_ids"]
                assert ids_tf_b == ids_tf_i
                out["tf"][task][kind].append({"id": f"{'P' if kind == 'baseline' else 'B'}{i}", "seg": seg,
                                              "text": tfp, "n_tokens": len(ids_tf_b), "sha256": sha256_text(tfp),
                                              "token_ids": ids_tf_b})
        spec_ntok = len(tok_i(SPEC[task], add_special_tokens=False)["input_ids"])
        assert spec_ntok >= 50, f"spec too short: {spec_ntok}"
        out["checks"][f"spec_tokens_{task}"] = spec_ntok
    out["checks"]["n_chat_prompts_identical_ids"] = n_identical
    out["checks"]["last8_decoded"] = sorted(tails)
    out["checks"]["lexicon_ok_all_neutral"] = True
    out["checks"]["ban_segments_note"] = "ban lead-ins are allowed to name the banned mode; lexicon check applies to neutral segments"
    out["sha256_all"] = sha256_text(json.dumps({k: out[k] for k in ("spec", "format_sentence", "sig", "neutral", "ban")},
                                               sort_keys=True))
    logger.info(f"chat prompts with identical ids across tokenizers: {n_identical}; last-8 tails: {sorted(tails)}")
    return out


def load_prompts() -> dict:
    return json.loads((DATA / "prompts.json").read_text())


if __name__ == "__main__":
    setup_logging("prompts")
    res = build()
    (DATA / "prompts.json").write_text(json.dumps(res, indent=1))
    logger.info(f"wrote {DATA / 'prompts.json'}; sha256_all={res['sha256_all']}")
