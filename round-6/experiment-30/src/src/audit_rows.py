#!/usr/bin/env python3
"""Row loader and AST shingles for the novelty audit (src/audit.py, exp20's module): the merged rows of this artifact
(data/samples.jsonl) in exp20's load_rows() shape, and exp20 analysis._ast_tokens / shingles unchanged."""

from __future__ import annotations

import ast
from typing import Any

from cfg import DATA_DIR, DEFAULT, read_jsonl

INVALID = ("invalid",)
UNRES = ("unresolved", "disputed")


def load_rows() -> list[dict[str, Any]]:
    out = []
    for r in read_jsonl(DATA_DIR / "samples.jsonl"):
        if str(r["arm"]).startswith("SMOKE_"):
            continue
        lab = r["label"]
        att = lab not in INVALID + UNRES
        rec = {"key": r["key"], "task": r["task"], "w": r["template"], "k": int(r["k"]), "arm": r["arm"],
               "site": r["site"], "alpha": float(r["alpha"]), "label": lab, "passed": bool(r["passed"]),
               "attempt": att, "invalid": lab in INVALID, "unresolved": lab in UNRES,
               "correct": bool(r["passed"]) and att, "off": att and lab != DEFAULT[r["task"]],
               "code_sha256": r.get("code_sha256"), "code": r.get("code"), "fallback_label": r.get("fallback_label")}
        out.append(rec)
    return out


def _ast_tokens(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    toks: list[str] = []

    def visit(n: ast.AST) -> None:
        name = type(n).__name__
        if isinstance(n, (ast.Name, ast.arg)):
            toks.append("ID")
        elif isinstance(n, ast.Constant):
            toks.append("C:" + type(n.value).__name__)
        elif isinstance(n, ast.Attribute):
            toks.append("ATTR:" + n.attr)
        elif isinstance(n, ast.FunctionDef):
            toks.append("FUNC")
        else:
            toks.append(name)
        for c in ast.iter_child_nodes(n):
            visit(c)
    visit(tree)
    return toks


def shingles(code: str, n: int = 4) -> frozenset:
    t = _ast_tokens(code or "")
    return frozenset(tuple(t[i:i + n]) for i in range(max(0, len(t) - n + 1)))
