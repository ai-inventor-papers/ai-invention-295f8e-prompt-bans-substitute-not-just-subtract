#!/usr/bin/env python3
"""Zhang-Shasha tree edit distance on identifier-normalised ASTs (port of iteration-3 exp15 proximity.py):
identifiers renamed v1, v2, ... in order of first appearance; docstrings and ctx/operator nodes dropped; constants
other than 0 and 1 replaced by a placeholder; labels = node type + operator (+ renamed identifier / constant class)."""

from __future__ import annotations

import ast

SKIP = (ast.expr_context, ast.operator, ast.unaryop, ast.boolop, ast.cmpop)


def _is_doc(n: ast.AST) -> bool:
    return isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant) and isinstance(n.value.value, str)


def to_tree(code: str):
    from zss import Node

    tree = ast.parse(code)
    names: dict[str, str] = {}

    def nm(x: str) -> str:
        if x not in names:
            names[x] = f"v{len(names) + 1}"
        return names[x]

    def label(n: ast.AST) -> str:
        t = type(n).__name__
        if isinstance(n, (ast.BinOp, ast.AugAssign)):
            t += ":" + type(n.op).__name__
        elif isinstance(n, ast.UnaryOp):
            t += ":" + type(n.op).__name__
        elif isinstance(n, ast.BoolOp):
            t += ":" + type(n.op).__name__
        elif isinstance(n, ast.Compare):
            t += ":" + ",".join(type(o).__name__ for o in n.ops)
        elif isinstance(n, ast.Name):
            t += ":" + nm(n.id)
        elif isinstance(n, ast.arg):
            t += ":" + nm(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            t += ":" + nm(n.name)
        elif isinstance(n, ast.Attribute):
            t += ":" + nm(n.attr)
        elif isinstance(n, ast.alias):
            t += ":" + nm(n.name) + (":" + nm(n.asname) if n.asname else "")
        elif isinstance(n, ast.Constant):
            v = n.value
            t += ":" + (repr(v) if (type(v) is int and v in (0, 1)) else "C")
        return t

    def build(n: ast.AST):
        node = Node(label(n))
        for c in ast.iter_child_nodes(n):
            if isinstance(c, SKIP) or _is_doc(c):
                continue
            node.addkid(build(c))
        return node

    return build(tree)


def zs_pair(a: str, b: str) -> float | None:
    from zss import simple_distance

    try:
        return float(simple_distance(to_tree(a), to_tree(b)))
    except (SyntaxError, ValueError, RecursionError):
        return None
