#!/usr/bin/env python3
"""Text-level harness: code extraction, format / enumeration flags and catalogue names mentioned."""
from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, LEXICON, LEXICON_TO_MODE  # noqa: E402

FENCE = re.compile(r"^[ \t]*```[ \t]*([A-Za-z0-9_+-]*)[^\n]*$", re.M)
LIST_LINE = re.compile(r"^\s*(?:\d+[.)]|[-*•]|\(\d+\))\s+\S", re.M)


def code_blocks(text: str) -> list[tuple[str, str]]:
    """All fenced blocks as (language, body); an unclosed final block runs to the end of the text."""
    blocks, pos, open_lang, open_start = [], 0, None, None
    for m in FENCE.finditer(text):
        if open_lang is None:
            open_lang, open_start = m.group(1).lower(), m.end()
        else:
            blocks.append((open_lang, text[open_start:m.start()]))
            open_lang, open_start = None, None
        pos = m.end()
    if open_lang is not None:
        blocks.append((open_lang, text[open_start:]))
    return blocks


def prose_of(text: str) -> str:
    """Text outside fenced blocks."""
    out, inside, last = [], False, 0
    for m in FENCE.finditer(text):
        if not inside:
            out.append(text[last:m.start()])
        inside = not inside
        last = m.end()
    if not inside:
        out.append(text[last:])
    return "\n".join(out)


def comments_of(code: str) -> str:
    parts = []
    try:
        for tk in tokenize.generate_tokens(io.StringIO(code).readline):
            if tk.type == tokenize.COMMENT:
                parts.append(tk.string)
            elif tk.type == tokenize.STRING and tk.string.lstrip("rbuRBU").startswith(('"""', "'''")):
                parts.append(tk.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        parts = re.findall(r"#[^\n]*", code)
    return "\n".join(parts)


def names_in(task: str, text: str) -> list[str]:
    low = text.lower()
    found = set()
    for key, pats in LEXICON.items():
        mode = LEXICON_TO_MODE[task].get(key)
        if mode is None:
            continue
        if any(re.search(p, low) for p in pats):
            found.add(mode)
    return sorted(found)


def analyse_text(task: str, text: str) -> dict:
    blocks = code_blocks(text)
    py = [(lang, body) for lang, body in blocks if lang in ("python", "py", "python3")]
    solve_py = [body for _, body in py if re.search(r"^\s*def\s+solve\s*\(", body, re.M)]
    code, fallback = None, False
    if solve_py:
        code = solve_py[-1]
    else:  # bare or other-language fences that still define solve
        alt = [body for _, body in blocks if re.search(r"^\s*def\s+solve\s*\(", body, re.M)]
        if alt:
            code, fallback = alt[-1], True
    format_ok = (len(py) == 1 and bool(solve_py)) and not fallback
    prose = prose_of(text)
    n_list = len(LIST_LINE.findall(prose))
    names_prose = names_in(task, prose)
    enumerated = (code is None) and (n_list >= 3 or len(names_prose) >= 3)
    names = set(names_prose)
    if code is not None:
        names |= set(names_in(task, comments_of(code)))
    return {"code": code, "format_ok": bool(format_ok), "enumerated": bool(enumerated), "n_python_blocks": len(py),
            "code_from_bare_fence": fallback, "names_mentioned": sorted(names),
            "n_list_lines": n_list, "n_catalogue_names_prose": len(names_prose),
            "catalogue": CATALOGUE[task]}
