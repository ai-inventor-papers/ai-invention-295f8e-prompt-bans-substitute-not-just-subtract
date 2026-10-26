#!/usr/bin/env python3
"""Write prompts/paraphrases.json once (deterministic, hand-written templates, no LLM drafting).

Sets: baseline (20), enumerate (10), ban (10 templates with {X}), mention (20 templates with {X}),
listall (10), and the five direction frames LIST / IMPLEMENT / ONE / LONGNAMES / SHORTNAMES (50 each),
which are disjoint from every evaluation segment. No algorithm name appears outside {X}.
"""
from __future__ import annotations

import itertools
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import PROMPTS_DIR  # noqa: E402

BASELINE = [
    "Solve the following programming task.",
    "Please solve the programming task below.",
    "Here is a programming task for you to solve.",
    "Complete the following coding task.",
    "Write a solution to the task below.",
    "Solve this coding problem.",
    "Please complete the following programming exercise.",
    "Your job is to solve the programming task that follows.",
    "Read the task below and solve it.",
    "Here is a coding task; please solve it.",
    "Solve the task described below.",
    "Please write code for the following task.",
    "The following is a programming problem. Solve it.",
    "Tackle the programming task below.",
    "Work out a solution to the following task.",
    "Please handle the coding task below.",
    "Below is a task. Write the code that solves it.",
    "Provide a solution for the following programming task.",
    "Solve the programming problem stated below.",
    "Here is a task to solve in Python.",
]
ENUMERATE = [
    "First list 10 different approaches to this task, then implement one of them.",
    "Begin by listing ten distinct ways to solve this task, then implement one of them.",
    "Start with a list of 10 different approaches to this task; after that, implement one.",
    "List ten different methods for this task first, and then implement one of them.",
    "Before writing code, list 10 alternative approaches to this task, then implement one.",
    "First brainstorm a list of 10 different approaches, then pick one and implement it.",
    "Enumerate ten different approaches to this task, then implement one of them.",
    "First write down 10 distinct strategies for this task, then implement one.",
    "Give a list of ten different approaches to this task first, then implement one of them.",
    "Start by listing 10 different algorithms that could solve this task, then implement one.",
]
BAN = [
    "Do not use {X}.",
    "You must not use {X}.",
    "Avoid {X} in your solution.",
    "Your solution may not use {X}.",
    "Solve this without using {X}.",
    "Do not implement {X}.",
    "Using {X} is not allowed.",
    "Please don't use {X}.",
    "{X} is forbidden for this task.",
    "Write a solution that does not use {X}.",
]
MENTION = [
    "{X} is one well-known approach to this task; implement any correct algorithm.",
    "One standard way to solve this task is {X}; you may implement any correct algorithm.",
    "{X} is a common technique for problems like this; write any correct solution.",
    "For reference, {X} is one possible approach; any correct algorithm is acceptable.",
    "Note that {X} is one known method for this task; implement any correct algorithm you like.",
    "{X} is among the familiar approaches here; feel free to use any correct algorithm.",
    "People often solve this kind of task with {X}; implement whichever correct algorithm you prefer.",
    "{X} is one option for this task; any correct algorithm will do.",
    "A known approach for this task is {X}; implement any correct algorithm.",
    "{X} is one of several approaches that work here; implement any correct one.",
    "{X} can be used for this task; you are free to implement any correct algorithm.",
    "One approach that solves this task is {X}; write any correct solution.",
    "Some programmers would use {X} here; implement any algorithm that is correct.",
    "{X} is a recognised way to handle this task; use any correct algorithm.",
    "This task can be solved with {X}, among other methods; implement any correct one.",
    "{X} is one familiar choice for this task; any correct implementation is fine.",
    "A typical approach to this task is {X}; you may choose any correct algorithm.",
    "{X} is one method people know for this task; implement a correct algorithm of your choice.",
    "Consider that {X} is one valid approach; implement any correct algorithm.",
    "{X} is a standard option here; write a correct solution using any algorithm.",
]
LISTALL = [
    "List all the approaches you can think of for this task. Do not implement any of them.",
    "Write down every approach you know for this task, without implementing any.",
    "Give a complete list of the approaches that could solve this task. Do not write code.",
    "Name all the different ways this task could be solved. Do not implement them.",
    "List as many approaches to this task as you can. No implementation.",
    "Enumerate all the methods you know for this task, but do not implement any.",
    "Make an exhaustive list of approaches to this task. Do not write any code.",
    "Catalogue every strategy you can think of for this task. Do not implement one.",
    "List every possible approach to this task; do not code any of them.",
    "Produce a full list of the approaches to this task, without any implementation.",
]


def combos(parts: list[list[str]], n: int, seed: int, fmt) -> list[str]:
    rng = random.Random(seed)
    allc = list(itertools.product(*parts))
    rng.shuffle(allc)
    out, seen = [], set()
    for c in allc:
        s = fmt(*c)
        s = re.sub(r"\s+", " ", s).strip()
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) == n:
            break
    assert len(out) == n, (len(out), n)
    return out


TARGETS = ["to this task", "for this task", "for solving this task", "for the task below", "for the following task"]


def frames() -> dict[str, list[str]]:
    lst = combos(
        [["List", "Enumerate", "Write down", "Give", "Name", "Brainstorm", "Outline", "Propose", "Suggest", "Describe"],
         ["ten", "10"], ["different", "distinct", "alternative", "varied", "diverse"],
         ["approaches", "methods", "strategies", "ways", "techniques"], TARGETS,
         ["Do not implement any of them.", "Do not write any code.", "Do not implement them.",
          "Don't implement any of them.", "Only list them; do not implement any."]],
        50, 11, lambda v, k, a, n, t, c: f"{v} {k} {a} {n} {t}. {c}")
    imp = combos(
        [["Implement", "Write", "Code up", "Provide", "Give", "Produce", "Develop", "Create", "Program", "Build"],
         ["one correct", "a single correct", "a correct", "one working", "a single working"],
         ["algorithm", "solution", "implementation", "program", "function"], TARGETS,
         ["", "Just implement it.", "Write the code.", "Implement it fully.", "Provide the code."]],
        50, 12, lambda v, a, n, t, c: f"{v} {a} {n} {t}. {c}")
    one = combos(
        [["Name", "State", "Identify", "Tell me", "Give", "Pick", "Choose", "Point out", "Suggest", "Mention"],
         ["the single best", "the one best", "the best", "the single most suitable", "the most appropriate"],
         ["approach", "method", "strategy", "technique", "algorithm"], TARGETS,
         ["Do not implement it.", "Do not write any code.", "Don't implement it.", "No implementation needed.",
          "Do not write code for it."]],
        50, 13, lambda v, a, n, t, c: f"{v} {a} {n} {t}. {c}")
    longn = combos(
        [["Use", "Choose", "Pick", "Prefer", "Write the code with"],
         ["long, descriptive", "long and descriptive", "verbose, self-explanatory", "fully spelled-out, descriptive",
          "long, meaningful"],
         ["variable names", "names for all variables", "identifiers", "names for every variable"],
         ["", " throughout", " everywhere in the code", " in your code", " for clarity"]],
        50, 14, lambda v, a, n, e: f"{v} {a} {n}{e}.")
    shortn = combos(
        [["Use", "Choose", "Pick", "Prefer", "Write the code with"],
         ["short", "very short", "single-letter or very short", "brief, compact", "short, terse"],
         ["variable names", "names for all variables", "identifiers", "names for every variable"],
         ["", " throughout", " everywhere in the code", " in your code", " for brevity"]],
        50, 15, lambda v, a, n, e: f"{v} {a} {n}{e}.")
    return {"LIST": lst, "IMPLEMENT": imp, "ONE": one, "LONGNAMES": longn, "SHORTNAMES": shortn}


def main() -> None:
    fr = frames()
    out = {"baseline": BASELINE, "enumerate": ENUMERATE, "ban": BAN, "mention": MENTION, "listall": LISTALL, **fr}
    # disjointness of direction frames from every evaluation segment
    evals = set(BASELINE) | set(ENUMERATE) | set(LISTALL)
    for k in fr:
        assert not (set(fr[k]) & evals), k
        assert len(set(fr[k])) == 50, k
    banned_words = re.compile(r"bfs|dfs|dijkstra|bellman|floyd|warshall|a\*|breadth|depth|heap|queue|stack|bucket",
                              re.I)
    for k, v in out.items():
        for s in v:
            assert not banned_words.search(s.replace("{X}", "")), (k, s)
    assert len(BASELINE) == 20 and len(ENUMERATE) == 10 and len(BAN) == 10 and len(MENTION) == 20
    assert len(LISTALL) == 10
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROMPTS_DIR / "paraphrases.json").write_text(json.dumps(out, indent=1))
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
