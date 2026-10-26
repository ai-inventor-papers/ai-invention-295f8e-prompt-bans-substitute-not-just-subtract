#!/usr/bin/env python3
"""Name scrub so that an algorithm's name cannot drive its likelihood score.

(i) comments naming a catalogue algorithm are removed (tokenize) and such docstrings replaced by `pass` (ast);
(ii) identifiers containing a catalogue name have the matched substring replaced by the neutral stem 'search'
     (bfs -> search, dijkstra_helper -> search_helper), with a collision check appending _1, _2, ...;
(iii) the caller re-runs tests + labeller and keeps the scrub only if pass vector and label are unchanged.
Edits are applied as text spans (not untokenize), so the rest of the program is byte-identical.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from typing import Any

from cfg import SCRUB_REGEX

NAME_RE = re.compile(SCRUB_REGEX, re.IGNORECASE)
FENCE_RE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)(```|\Z)", re.DOTALL)


def _line_offsets(code: str) -> list[int]:
    offs, pos = [0], 0
    for line in code.splitlines(keepends=True):
        pos += len(line)
        offs.append(pos)
    return offs


def scrub_code(code: str) -> tuple[str, dict[str, Any]]:
    info: dict[str, Any] = {"comments_removed": 0, "docstrings_removed": 0, "renamed": {}, "ok": True}
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
        tree = ast.parse(code)
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError) as e:
        info.update(ok=False, error=f"parse: {type(e).__name__}")
        return code, info
    offs = _line_offsets(code)

    def absol(rc: tuple[int, int]) -> int:
        return offs[rc[0] - 1] + rc[1]

    edits: list[tuple[int, int, str]] = []
    comment_lines: set[int] = set()
    # docstrings
    doc_spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str) and NAME_RE.search(first.value.value)):
                s = absol((first.lineno, first.col_offset))
                e = absol((first.end_lineno, first.end_col_offset))
                doc_spans.append((s, e))
                edits.append((s, e, "pass"))
                info["docstrings_removed"] += 1

    def in_doc(pos: int) -> bool:
        return any(s <= pos < e for s, e in doc_spans)

    # identifiers
    names = {t.string for t in toks if t.type == tokenize.NAME}
    mapping: dict[str, str] = {}
    used = set(n for n in names if not NAME_RE.search(n))
    for n in sorted(names):
        if NAME_RE.search(n):
            new = NAME_RE.sub("search", n)
            cand, k = new, 0
            while cand in used or cand in mapping.values():
                k += 1
                cand = f"{new}_{k}"
            mapping[n] = cand
            used.add(cand)
    for t in toks:
        s = absol(t.start)
        if in_doc(s):
            continue
        if t.type == tokenize.COMMENT and NAME_RE.search(t.string):
            edits.append((s, absol(t.end), ""))
            comment_lines.add(t.start[0])
            info["comments_removed"] += 1
        elif t.type == tokenize.NAME and t.string in mapping:
            edits.append((s, absol(t.end), mapping[t.string]))
    info["renamed"] = mapping
    out = code
    for s, e, rep in sorted(edits, key=lambda x: -x[0]):
        out = out[:s] + rep + out[e:]
    if comment_lines:
        # drop lines that became whitespace-only after a comment was removed; strip trailing spaces elsewhere
        new_lines = []
        old_lines = code.splitlines(keepends=True)
        out_lines = out.splitlines(keepends=True)
        if len(old_lines) == len(out_lines):
            for i, (ol, nl) in enumerate(zip(old_lines, out_lines), start=1):
                if i in comment_lines:
                    if nl.strip() == "":
                        continue
                    nl = nl.rstrip() + ("\n" if nl.endswith("\n") else "")
                new_lines.append(nl)
            out = "".join(new_lines)
    try:
        ast.parse(out)
    except SyntaxError as e:
        info.update(ok=False, error=f"post-scrub syntax: {e.msg}")
        return code, info
    info["changed"] = out != code
    return out, info


def scrub_response(text: str) -> tuple[str | None, str | None, dict[str, Any]]:
    """Returns (scored_text, scrubbed_inner_code, info). scored_text keeps the response formatting but replaces the
    fenced code by its scrubbed version; text outside the single fence is dropped and flagged."""
    m = FENCE_RE.search(text)
    if not m:
        return None, None, {"ok": False, "error": "no_fence"}
    inner = m.group(1)
    scrubbed, info = scrub_code(inner)
    outside = (text[:m.start()] + text[m.end():]).strip()
    info["outside_fence"] = bool(outside)
    if outside:
        scored = text[m.start():m.start(1)] + scrubbed + text[m.end(1):m.end()]
    else:
        scored = text[:m.start(1)] + scrubbed + text[m.end(1):]
    info["fence_closed"] = m.group(2) == "```"
    return scored, scrubbed, info
