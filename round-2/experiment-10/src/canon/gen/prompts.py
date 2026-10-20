#!/usr/bin/env python3
"""Builds prompts/conditions.json: every paraphrase of every condition, the name table and the
elicitation templates. Frozen (sha256 + commitments.log) before any generation."""

from __future__ import annotations

import random
from typing import Any

from common import (CATALOGUE, DESCRIPTION, MODES, PROMPT_DIR, TASKS, cap_first, join_names_and, join_names_or,
                    spec_text)

BASELINE_SEGMENTS = [
    "Please solve the following programming task.",
    "Here is a programming task for you.",
    "Solve the task described below.",
    "Below is a coding problem to solve.",
    "Please write code for the following task.",
    "The following task needs a Python solution.",
    "Complete the programming task below.",
    "Your job is to solve this coding task.",
    "Implement a solution to the following problem.",
    "Read the task below and solve it.",
]
BAN_TEMPLATES = [
    "Do not use {X}.",
    "Your solution must not use {X}.",
    "Avoid using {X} in your solution.",
    "{X} is not allowed for this task.",
    "Do not implement {X}.",
    "You may use any approach except {X}.",
    "Please refrain from using {X}.",
    "The solution must not rely on {X}.",
    "Using {X} is forbidden here.",
    "Don't use {X}.",
]
MENTION_TEMPLATES = [
    "{X} is one well-known approach to this task; implement any correct algorithm.",
    "{X} is a known way to solve this task; any correct algorithm is fine.",
    "{X} is one common approach here; implement any correct algorithm.",
    "{X} is one of the standard approaches to this task; use any correct algorithm.",
    "One well-known approach to this task is {X}; implement any correct algorithm.",
    "{X} is a familiar technique for this task; any correct solution is acceptable.",
    "{X} is one established method for this task; implement any correct algorithm.",
    "People often solve this task with {X}; implement any correct algorithm.",
    "{X} is one possible approach; implement any correct algorithm.",
    "{X} is one textbook approach to this task; any correct algorithm will do.",
]
LISTALL_TEMPLATES = [
    "Known approaches include {L}; implement any correct algorithm.",
    "Approaches to this task include {L}; any correct algorithm is fine.",
    "This task can be solved with {L}; implement any correct algorithm.",
    "Standard approaches here are {L}; use any correct algorithm.",
    "Well-known methods for this task include {L}; implement any correct algorithm.",
    "Possible approaches include {L}; any correct solution is acceptable.",
    "Common techniques for this task are {L}; implement any correct algorithm.",
    "Among the known approaches are {L}; implement any correct algorithm.",
    "You could use {L}; any correct algorithm will do.",
    "Textbook approaches include {L}; implement any correct algorithm.",
]
FORCED_TEMPLATES = [
    "Implement {X} for this task.",
    "Use {X} to solve this task.",
    "Solve this task with {X}.",
    "Your solution should use {X}.",
    "Write an implementation based on {X}.",
]
RANK_TEMPLATE = (
    "Consider the approach {X}. Rank the following approaches by how standard an alternative to {X} each one is "
    "for this task, from the most standard alternative to the least standard."
)
RANK_ANSWER = "Answer with only a JSON list of the option letters, most standard first, using every letter exactly once."
FREE_TEMPLATE = "What is the standard alternative to {X} for this task? Answer with the name of one algorithm only."
N_RANK_SAMPLES = 20
N_FREE_SAMPLES = 20


def make_prompt(task: str, segment: str | None) -> str:
    """Shared prompt = [condition segment] + blank line + [SPEC]; no segment for baseline_empty."""
    if segment is None:
        return spec_text(task)
    return cap_first(segment) + "\n\n" + spec_text(task)


def fill(template: str, **kw: str) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{" + k + "}", v)
    return cap_first(out)


def listall_order(task: str, pid: int) -> list[str]:
    modes = list(MODES[task])
    random.Random(f"listall|{task}|{pid}").shuffle(modes)
    return modes


def rank_option_order(task: str, x: str, i: int) -> list[str]:
    others = [m for m in MODES[task] if m != x]
    random.Random(f"rank|{task}|{x}|{i}").shuffle(others)
    return others


def rank_prompt(task: str, x: str, order: list[str]) -> str:
    names = CATALOGUE[task]
    lines = [f"{chr(ord('A') + j)}. {names[m]}" for j, m in enumerate(order)]
    return (DESCRIPTION[task] + "\n\n" + RANK_TEMPLATE.replace("{X}", names[x]) + "\n" + "\n".join(lines) + "\n"
            + RANK_ANSWER)


def free_prompt(task: str, x: str) -> str:
    return DESCRIPTION[task] + "\n\n" + FREE_TEMPLATE.replace("{X}", CATALOGUE[task][x])


def succession_segments(task: str, banned_in_order: list[str]) -> list[str]:
    names = join_names_or([CATALOGUE[task][m] for m in banned_in_order])
    return [fill(t, X=names) for t in BAN_TEMPLATES]


def build_conditions() -> dict[str, Any]:
    out: dict[str, Any] = {
        "templates": {
            "baseline": BASELINE_SEGMENTS, "ban": BAN_TEMPLATES, "mention": MENTION_TEMPLATES,
            "listall": LISTALL_TEMPLATES, "forced": FORCED_TEMPLATES, "rank": RANK_TEMPLATE,
            "rank_answer": RANK_ANSWER, "free": FREE_TEMPLATE,
            "succession": "ban templates with {X} = cumulative banned display names joined 'A, B or C' in ban order",
        },
        "rules": {
            "prompt": "[condition segment] + blank line + [SPEC]; SPEC = DESCRIPTION + blank line + FORMAT",
            "capitalisation": "first character of every condition segment is upper-cased (templates that start "
                              "with {X} would otherwise begin a sentence in lower case)",
            "listall_join": "all catalogue display names, seeded random order per paraphrase, joined 'A, B and C'",
        },
        "name_table": CATALOGUE,
        "spec": {t: spec_text(t) for t in TASKS},
        "tasks": {},
    }
    for task in TASKS:
        names = CATALOGUE[task]
        conds: dict[str, list[dict[str, Any]]] = {}
        conds["baseline"] = [{"paraphrase_id": i, "segment": s, "prompt": make_prompt(task, s)}
                             for i, s in enumerate(BASELINE_SEGMENTS)]
        conds["baseline_empty"] = [{"paraphrase_id": 0, "segment": None, "prompt": make_prompt(task, None)}]
        for m in MODES[task]:
            conds[f"ban:{m}"] = [{"paraphrase_id": i, "segment": fill(t, X=names[m]),
                                  "prompt": make_prompt(task, fill(t, X=names[m]))} for i, t in enumerate(BAN_TEMPLATES)]
            conds[f"mention:{m}"] = [{"paraphrase_id": i, "segment": fill(t, X=names[m]),
                                      "prompt": make_prompt(task, fill(t, X=names[m]))}
                                     for i, t in enumerate(MENTION_TEMPLATES)]
            conds[f"forced:{m}"] = [{"paraphrase_id": i, "segment": fill(t, X=names[m]),
                                     "prompt": make_prompt(task, fill(t, X=names[m]))}
                                    for i, t in enumerate(FORCED_TEMPLATES)]
        conds["listall"] = []
        for i, t in enumerate(LISTALL_TEMPLATES):
            order = listall_order(task, i)
            seg = fill(t, L=join_names_and([names[m] for m in order]))
            conds["listall"].append({"paraphrase_id": i, "segment": seg, "order": order,
                                     "prompt": make_prompt(task, seg)})
        elicit_rank = {}
        elicit_free = {}
        for m in MODES[task]:
            elicit_rank[m] = []
            for i in range(N_RANK_SAMPLES):
                order = rank_option_order(task, m, i)
                elicit_rank[m].append({"sample_id": i, "option_order": order, "prompt": rank_prompt(task, m, order)})
            elicit_free[m] = {"prompt": free_prompt(task, m), "n": N_FREE_SAMPLES}
        out["tasks"][task] = {"conditions": conds, "elicit_rank": elicit_rank, "elicit_free": elicit_free}
    return out


def conditions_path():
    return PROMPT_DIR / "conditions.json"
