"""Identifier-normalised Python ASTs and Zhang-Shasha tree edit distance (zss.simple_distance, unit costs).

Normalisation (plan step 0.9): docstrings dropped; user-defined names, arguments, functions and assigned attributes
renamed v0, v1, ... in order of first appearance (pre-order, source-field order); builtins, imported module names,
their attributes and every other attribute / keyword name (API names such as heapq.heappush, bisect_left, Counter,
append) kept verbatim; the entry point `solve` kept; constant values replaced by their type tag; expression-context
nodes (Load/Store/Del) dropped.  Node label = node type, plus the operator type(s), plus the (kept or normalised) name.
"""

from __future__ import annotations

import ast
import builtins

import zss

_BUILTINS = set(dir(builtins))
_SKIP = (ast.expr_context,)


def _strip_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            f = node.body[0]
            if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]


def _imported(tree: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                out.add(a.asname or a.name)
            if node.module:
                out.add(node.module.split(".")[0])
    return out


def _user_attrs(tree: ast.AST) -> set[str]:
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)}


class _Normaliser:
    def __init__(self, tree: ast.AST):
        self.kept = _BUILTINS | _imported(tree) | {"solve"}
        self.user_attrs = _user_attrs(tree)
        self.names: dict[str, str] = {}

    def name(self, s: str) -> str:
        if s in self.kept:
            return s
        if s not in self.names:
            self.names[s] = f"v{len(self.names)}"
        return self.names[s]

    def label(self, node: ast.AST) -> str:
        t = type(node).__name__
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.AugAssign)):
            return f"{t}:{type(node.op).__name__}"
        if isinstance(node, ast.Compare):
            return f"{t}:{','.join(type(o).__name__ for o in node.ops)}"
        if isinstance(node, ast.Name):
            return f"{t}:{self.name(node.id)}"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return f"{t}:{self.name(node.name)}"
        if isinstance(node, ast.arg):
            return f"{t}:{self.name(node.arg)}"
        if isinstance(node, ast.Attribute):
            return f"{t}:{self.name(node.attr) if node.attr in self.user_attrs else node.attr}"
        if isinstance(node, ast.Constant):
            return f"{t}:{type(node.value).__name__}"
        if isinstance(node, ast.keyword):
            return f"{t}:{node.arg}"
        if isinstance(node, ast.alias):
            return f"{t}:{node.name}"
        if isinstance(node, ast.ImportFrom):
            return f"{t}:{node.module}"
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return f"{t}:{','.join(self.name(n) for n in node.names)}"
        if isinstance(node, ast.ExceptHandler) and node.name:
            return f"{t}:{self.name(node.name)}"
        return t

    def build(self, node: ast.AST) -> zss.Node:
        z = zss.Node(self.label(node))
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, _SKIP):
                continue
            z.addkid(self.build(ch))
        return z


def normalised_tree(code: str) -> zss.Node | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    _strip_docstrings(tree)
    return _Normaliser(tree).build(tree)


def tree_size(z: zss.Node) -> int:
    return 1 + sum(tree_size(c) for c in z.children)


def distance(a: zss.Node, b: zss.Node) -> float:
    return float(zss.simple_distance(a, b))


def pair_distance(args: tuple[str, str, str]) -> tuple[str, float | None]:
    """Process-pool worker: (key, code_a, code_b) -> (key, Zhang-Shasha distance or None if unparsable)."""
    key, code_a, code_b = args
    ta, tb = normalised_tree(code_a), normalised_tree(code_b)
    if ta is None or tb is None:
        return key, None
    return key, distance(ta, tb)
