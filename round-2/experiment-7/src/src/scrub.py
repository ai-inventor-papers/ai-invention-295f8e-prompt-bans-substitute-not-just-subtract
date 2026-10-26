#!/usr/bin/env python3
"""Step 2.2: name-scrub generated programs so that likelihoods measure mechanism, not algorithm names.

(a) comments and docstrings: matched name spans deleted, spaces collapsed, emptied comments dropped;
(b) identifiers with a lexicon stem as an underscore/camelCase part are renamed consistently by first appearance
    (functions -> find_path, find_path_2, ...; other names -> search_state, search_state_2, ...);
    `solve`, keywords, builtins and imported (stdlib) names are never renamed.
(c) verification (ast.parse, hidden-test pass status and canonical label unchanged) happens in select_programs.py.
"""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import re
import tokenize

from config import SCRUB_PHRASES, SCRUB_STEMS

_PHRASE_RE = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(SCRUB_PHRASES) + r")(?![A-Za-z0-9])", re.IGNORECASE)
_PROTECTED = set(dir(builtins)) | set(keyword.kwlist) | {"solve", "self", "cls"}


def _scrub_text(s: str) -> str:
    out = _PHRASE_RE.sub("", s)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out


def _parts(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [p for p in spaced.lower().split("_") if p]


def has_stem(name: str) -> bool:
    parts = _parts(name)
    joined = "_".join(parts)
    for st in SCRUB_STEMS:
        if "_" in st:
            if re.search(r"(^|_)" + re.escape(st) + r"($|_)", joined):
                return True
        elif st in parts:
            return True
    return False


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


def _docstring_spans(tree: ast.AST) -> set[tuple[int, int]]:
    spans = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                spans.add((first.value.lineno, first.value.col_offset))
    return spans


def scrub(code: str) -> tuple[str, dict]:
    """Returns (scrubbed code, info). Raises SyntaxError/tokenize.TokenError on unparsable input."""
    tree = ast.parse(code)
    imported = _imported_names(tree)
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    all_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | func_names | {
        a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.args + n.kwonlyargs}
    doc_spans = _docstring_spans(tree)
    toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    rename: dict[str, str] = {}
    used = set(all_names)
    counters = {"find_path": 0, "search_state": 0}

    def new_name(base: str) -> str:
        while True:
            counters[base] += 1
            cand = base if counters[base] == 1 else f"{base}_{counters[base]}"
            if cand not in used:
                used.add(cand)
                return cand

    lines = code.splitlines(keepends=True)
    edits: list[tuple[int, int, int, int, str]] = []  # (srow, scol, erow, ecol, replacement)
    n_comment, n_doc = 0, 0
    for t in toks:
        if t.type == tokenize.NAME and t.string not in _PROTECTED and t.string not in imported and has_stem(t.string):
            if t.string not in rename:
                rename[t.string] = new_name("find_path" if t.string in func_names else "search_state")
            edits.append((t.start[0], t.start[1], t.end[0], t.end[1], rename[t.string]))
        elif t.type == tokenize.COMMENT and _PHRASE_RE.search(t.string):
            body = _scrub_text(t.string[1:]).rstrip()
            n_comment += 1
            if re.fullmatch(r"[\s\W_]*", body):
                edits.append((t.start[0], t.start[1], t.end[0], t.end[1], "\x00DROP"))
            else:
                edits.append((t.start[0], t.start[1], t.end[0], t.end[1], "#" + body))
        elif t.type == tokenize.STRING and (t.start[0], t.start[1]) in doc_spans and _PHRASE_RE.search(t.string):
            n_doc += 1
            edits.append((t.start[0], t.start[1], t.end[0], t.end[1], _scrub_text(t.string)))
    # apply edits from the end (positions are 1-based rows, 0-based cols)
    for srow, scol, erow, ecol, rep in sorted(edits, reverse=True):
        if rep == "\x00DROP":
            line = lines[srow - 1]
            before = line[:scol].rstrip()
            nl = "\n" if line.endswith("\n") else ""
            lines[srow - 1] = (before + nl) if before.strip() else "\x00DELETE"
            continue
        if srow == erow:
            line = lines[srow - 1]
            lines[srow - 1] = line[:scol] + rep + line[ecol:]
        else:
            first, last = lines[srow - 1], lines[erow - 1]
            lines[srow - 1] = first[:scol] + rep + last[ecol:]
            for r in range(srow, erow):
                lines[r] = ""
    out = "".join(ln for ln in lines if ln != "\x00DELETE")
    if not out.endswith("\n"):
        out += "\n"
    ast.parse(out)
    return out, {"renamed": rename, "n_comments_scrubbed": n_comment, "n_docstrings_scrubbed": n_doc}


def residual_names(code: str) -> list[str]:
    """Lexicon names still present in comments, docstrings or identifiers (should be empty after scrub)."""
    found = []
    tree = ast.parse(code)
    imported = _imported_names(tree)
    doc_spans = _docstring_spans(tree)
    for t in tokenize.generate_tokens(io.StringIO(code).readline):
        if t.type == tokenize.COMMENT and _PHRASE_RE.search(t.string):
            found.append(t.string)
        elif t.type == tokenize.NAME and t.string not in _PROTECTED and t.string not in imported and has_stem(t.string):
            found.append(t.string)
        elif t.type == tokenize.STRING and (t.start[0], t.start[1]) in doc_spans and _PHRASE_RE.search(t.string):
            found.append(t.string[:40])
    return found


if __name__ == "__main__":
    demo = ('import heapq\nfrom collections import deque\n\ndef bfs_search(grid, start):\n    """Breadth-first search '
            '(BFS) over the grid."""\n    # BFS search\n    bfs_queue = deque([start])  # use a BFS queue\n    # BFS\n'
            '    return bfs_queue\n\ndef solve(grid, start, goal):\n    return bfs_search(grid, start)\n')
    s, info = scrub(demo)
    print(s)
    print(info, residual_names(s))
