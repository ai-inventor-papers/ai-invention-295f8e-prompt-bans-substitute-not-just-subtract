#!/usr/bin/env python3
"""S2.2 name scrubber (Python tokenize + ast; edits are applied by source position, so untouched code is byte-identical).

(i) COMMENT tokens: every name-table match (both tasks, case-insensitive, most specific first) -> 'search',
    'search search' collapsed, comments left with no letters dropped.
(ii) the same replacement inside docstrings, all other string literals and f-string text.
(iii) identifiers whose '_'/camelCase pieces name an algorithm (ID_PIECES, or the pairs (a, star) / (depth, first)) are
     renamed consistently: functions and classes -> helper_N, other names -> var_N, never colliding with an existing
     name; 'solve', imported names, attribute names (after '.') and keywords are never renamed.
The conservative variant (rename=False) does (i) and (ii) only.
"""

from __future__ import annotations

import ast
import io
import keyword
import re
import tokenize
from typing import Any

from src.names import find_all, identifier_names_algorithm, neutralise

_FSTRING_MIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)
_LETTER = re.compile(r"[A-Za-z]")


def _offsets(src: str) -> list[int]:
    offs = [0]
    for line in src.splitlines(keepends=True):
        offs.append(offs[-1] + len(line))
    return offs


def _imported_names(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                out.add(a.asname or a.name)
    return out


def scrub(code: str, rename: bool = True) -> tuple[str, dict[str, Any]]:
    """Returns (scrubbed code, info). Raises SyntaxError / tokenize.TokenError on unparsable input."""
    tree = ast.parse(code)
    toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    offs = _offsets(code)

    def pos(rc: tuple[int, int]) -> int:
        return offs[rc[0] - 1] + rc[1]

    edits: list[tuple[int, int, str]] = []
    info: dict[str, Any] = {"comments_changed": 0, "comments_dropped": 0, "strings_changed": 0, "renamed": {}}
    # identifiers to rename
    renames: dict[str, str] = {}
    if rename:
        defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        imported = _imported_names(tree)
        existing = {t.string for t in toks if t.type == tokenize.NAME}
        counters = {"helper": 0, "var": 0}
        prev_sig = None
        for t in toks:
            if t.type == tokenize.NAME:
                s = t.string
                is_attr = prev_sig is not None and prev_sig.type == tokenize.OP and prev_sig.string == "."
                if (s not in renames and not is_attr and not keyword.iskeyword(s) and s != "solve"
                        and s not in imported and identifier_names_algorithm(s)):
                    kind = "helper" if s in defs else "var"
                    while True:
                        counters[kind] += 1
                        cand = f"{kind}_{counters[kind]}"
                        if cand not in existing and cand not in renames.values():
                            break
                    renames[s] = cand
            if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
                prev_sig = t
        prev_sig = None
        for t in toks:
            if t.type == tokenize.NAME and t.string in renames:
                is_attr = prev_sig is not None and prev_sig.type == tokenize.OP and prev_sig.string == "."
                if not is_attr:
                    edits.append((pos(t.start), pos(t.end), renames[t.string]))
            if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
                prev_sig = t
        info["renamed"] = renames
    for t in toks:
        if t.type == tokenize.COMMENT:
            new = neutralise(t.string)
            if not _LETTER.search(new[1:]):
                a, b = pos(t.start), pos(t.end)
                # drop the comment and the whitespace before it on the same line
                line_start = offs[t.start[0] - 1]
                while a > line_start and code[a - 1] in " \t":
                    a -= 1
                edits.append((a, b, ""))
                info["comments_dropped"] += 1
            elif new != t.string:
                edits.append((pos(t.start), pos(t.end), new))
                info["comments_changed"] += 1
        elif t.type == tokenize.STRING or (_FSTRING_MIDDLE is not None and t.type == _FSTRING_MIDDLE):
            a, b = pos(t.start), pos(t.end)
            if code[a:b] != t.string:  # f-string middle with escaped braces: positions unreliable -> skip
                continue
            new = neutralise(t.string)
            if new != t.string:
                edits.append((a, b, new))
                info["strings_changed"] += 1
    edits.sort(key=lambda e: e[0], reverse=True)
    out = code
    last_start = None
    for a, b, new in edits:
        if last_start is not None and b > last_start:
            raise ValueError("overlapping scrub edits")
        out = out[:a] + new + out[b:]
        last_start = a
    ast.parse(out)
    info["n_edits"] = len(edits)
    return out, info


def residual_names(code: str) -> list[str]:
    """Name-table matches left in comments, string literals and identifiers (imported names excluded). Code tokens
    are not text-matched, so multiplication such as `a * b` is not mistaken for 'A*'."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
        imported = _imported_names(ast.parse(code))
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError):
        return ["<untokenizable>"]
    hits: list[str] = []
    for t in toks:
        if t.type in (tokenize.COMMENT, tokenize.STRING) or (_FSTRING_MIDDLE is not None and t.type == _FSTRING_MIDDLE):
            hits += [t.string[a:b] for a, b, _ in find_all(t.string, None)]
        elif t.type == tokenize.NAME and t.string not in imported and identifier_names_algorithm(t.string):
            hits.append(t.string)
    return hits


def scored_text(code: str) -> str:
    """S2.4: '```python' + newline + code with trailing newlines stripped + newline + '```'."""
    return "```python\n" + code.rstrip("\n") + "\n```"
