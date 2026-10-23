#!/usr/bin/env python3
"""Stage parsers for the text-level samplers (frozen in commit0C).

parse_intent(text)        the generated intent line (IFG / BINT): text up to the first newline, stripped.
intent_valid(s)           non-empty, at most 40 words, no code fence.
parse_observations(text)  numbered observations '1. ...' / '1) ...' (markdown bold allowed); at most 5 kept.
parse_enum(text)          enumerated algorithms '<n>. <name>: <idea>' (name without description allowed); <= 8 kept.
map_modes(name, aliases)  catalogue modes whose display name or alias occurs in the item name (+ idea) text.
pick_pair(m, seed)        the (i, j) pair (1-based, i < j) of index seed mod C(m, 2) in lexicographic order.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

_NUM = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?\s*<?\s*(\d{1,2})\s*>?\s*[.)]\s*(?:\*\*)?\s*(.+?)\s*$")


def _unbracket(x: str) -> str:
    """The model sometimes copies the template's angle brackets literally ('<Quickselect>')."""
    x = x.strip()
    if x.startswith("<") and x.endswith(">"):
        x = x[1:-1].strip()
    return x.lstrip("<").rstrip(">").strip()


def parse_intent(text: str) -> str:
    return text.split("\n", 1)[0].strip()


def intent_valid(s: str | None) -> bool:
    if not s or not s.strip():
        return False
    if "```" in s:
        return False
    return len(s.split()) <= 40


def _numbered(text: str) -> list[tuple[int, str]]:
    out = []
    for line in text.splitlines():
        m = _NUM.match(line)
        if m:
            body = _unbracket(m.group(2).strip().strip("*").strip())
            if body:
                out.append((int(m.group(1)), body))
    return out


def parse_observations(text: str, max_n: int = 5) -> list[str]:
    items = _numbered(text)
    seen, out = set(), []
    for n, body in items:
        if n in seen:
            continue
        seen.add(n)
        out.append(body)
    return out[:max_n]


def parse_enum(text: str, max_n: int = 8) -> list[dict[str, str]]:
    out, seen = [], set()
    for n, body in _numbered(text):
        if n in seen:
            continue
        seen.add(n)
        b = body.replace("**", "")
        if ":" in b:
            name, idea = b.split(":", 1)
        elif " - " in b:
            name, idea = b.split(" - ", 1)
        elif " — " in b:
            name, idea = b.split(" — ", 1)
        else:
            name, idea = b, ""
        name = _unbracket(name.strip().strip("*").strip())
        if name:
            out.append({"name": name, "idea": _unbracket(idea.strip())})
    return out[:max_n]


def map_modes(name: str, idea: str, aliases: dict[str, list[str]]) -> list[str]:
    txt = f"{name}".lower()
    hits = []
    for mode, al in aliases.items():
        for a in al:
            if a and re.search(rf"(?<![a-z0-9]){re.escape(a.lower())}(?![a-z0-9])", txt):
                hits.append(mode)
                break
    if not hits and idea:
        txt2 = idea.lower()
        for mode, al in aliases.items():
            for a in al:
                if a and re.search(rf"(?<![a-z0-9]){re.escape(a.lower())}(?![a-z0-9])", txt2):
                    hits.append(mode)
                    break
    return hits


def pick_pair(m: int, seed: int) -> tuple[int, int]:
    pairs = list(itertools.combinations(range(1, m + 1), 2))
    return pairs[seed % len(pairs)]


def synthetic_tests() -> dict[str, Any]:
    """CPU unit test (2): 20 synthetic outputs per parser."""
    res: dict[str, Any] = {}
    obs_cases = []
    for i in range(20):
        sep = [".", ")"][i % 2]
        bold = i % 3 == 0
        lines = [f"{'**' if bold else ''}{n}{sep}{'**' if bold else ''} observation number {n} about case {i}"
                 for n in range(1, 6)]
        txt = ("Here are the observations:\n" if i % 4 == 0 else "") + "\n".join(lines) + ("\n\nDone." if i % 5 == 0 else "")
        obs_cases.append(len(parse_observations(txt)) == 5)
    res["observations_ok"] = f"{sum(obs_cases)}/20"
    enum_cases = []
    for i in range(20):
        with_desc = i % 2 == 0
        lines = []
        for n in range(1, 1 + (i % 8) + 1):
            nm = f"Algo{n}"
            if i % 5 == 4:   # the template copied literally: '<1>. <Name>: <idea>'
                lines.append(f"<{n}>. <{nm}>" + (f": <idea {n}>" if with_desc else ""))
            else:
                lines.append(f"{n}. {'**' if i % 3 == 0 else ''}{nm}{'**' if i % 3 == 0 else ''}" +
                             (f": idea {n}" if with_desc else ""))
        got = parse_enum("\n".join(lines))
        enum_cases.append(len(got) == (i % 8) + 1 and got[0]["name"] == "Algo1")
    res["enum_ok"] = f"{sum(enum_cases)}/20"
    int_cases = []
    for i in range(20):
        sent = f" Use a min-heap of size k to track the k smallest values, variant {i}."
        txt = sent + "\n\n```python\ndef solve(nums, k):\n    return 0\n```\n" + ("Trailing prose." if i % 2 else "")
        int_cases.append(parse_intent(txt) == sent.strip() and intent_valid(parse_intent(txt)))
    res["intent_ok"] = f"{sum(int_cases)}/20"
    code_cases = []
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inputs" / "exp11"))
    from bench.common.harness import extract_code
    for i in range(20):
        body = f"def solve(nums, k):\n    return sorted(nums)[k - 1]  # v{i}\n"
        txt = f"Intent: sort.\n\n```python\n{body}```\n" + ("Explanation follows.\n```python\nprint(1)\n```" if i % 2 else "")
        code_cases.append((extract_code(txt) or "").strip() == body.strip())
    res["fenced_code_ok"] = f"{sum(code_cases)}/20"
    res["pass"] = all(v == "20/20" for k, v in res.items() if k.endswith("_ok"))
    return res
