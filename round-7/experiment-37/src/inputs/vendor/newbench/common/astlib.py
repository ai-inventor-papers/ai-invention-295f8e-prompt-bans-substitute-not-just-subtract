"""AST feature bag (copy of the iteration-2 bench astrules.F) plus helpers shared by the new units' AST rules."""

from __future__ import annotations

import ast
import re
from collections import Counter


class F:
    """AST feature bag of one program."""

    def __init__(self, code: str):
        self.code = code
        self.tree = ast.parse(code)
        self.calls = Counter()
        self.attr_calls = Counter()
        self.imports = set()
        self.names = Counter()
        self.funcs = {}
        self.recursive = set()
        self.max_loop_depth = 0
        self.n_loops = 0
        self.classes = 0
        self.decorators = Counter()
        self.bitand_neg = False
        self.pop0 = 0
        self.pop_noarg = 0
        self.popleft = 0
        self.subscript_nested = 0
        self.consts = Counter()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module.split(".")[0])
                for a in node.names:
                    self.imports.add(a.name)
            elif isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name):
                    self.calls[fn.id] += 1
                elif isinstance(fn, ast.Attribute):
                    self.attr_calls[fn.attr] += 1
                    if isinstance(fn.value, ast.Name):
                        self.calls[f"{fn.value.id}.{fn.attr}"] += 1
                    if fn.attr == "pop":
                        if not node.args:
                            self.pop_noarg += 1
                        elif isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                            self.pop0 += 1
                    if fn.attr == "popleft":
                        self.popleft += 1
            elif isinstance(node, ast.Name):
                self.names[node.id] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs[node.name] = node
                for d in node.decorator_list:
                    dn = d.func if isinstance(d, ast.Call) else d
                    nm = dn.attr if isinstance(dn, ast.Attribute) else (dn.id if isinstance(dn, ast.Name) else "?")
                    self.decorators[nm] += 1
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == node.name:
                        self.recursive.add(node.name)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == node.name:
                        self.recursive.add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.classes += 1
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd):
                for side in (node.left, node.right):
                    if isinstance(side, ast.UnaryOp) and isinstance(side.op, ast.USub):
                        self.bitand_neg = True
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Subscript):
                self.subscript_nested += 1
            elif isinstance(node, ast.Constant) and isinstance(node.value, (int, str)):
                self.consts[node.value] += 1
        self._loop_depth(self.tree, 0)
        self.low = code.lower()
        self.idents = {n.lower() for n in self.names} | {f.lower() for f in self.funcs}

    def _loop_depth(self, node, d):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.For, ast.While)):
                self.n_loops += 1
                self.max_loop_depth = max(self.max_loop_depth, d + 1)
                self._loop_depth(ch, d + 1)
            elif isinstance(ch, (ast.FunctionDef, ast.Lambda, ast.AsyncFunctionDef, ast.ClassDef)):
                self._loop_depth(ch, 0)
            else:
                self._loop_depth(ch, d)

    def has(self, *names):
        return any(self.calls.get(n) or self.attr_calls.get(n) for n in names)

    def ident(self, *subs):
        return any(any(s in i for s in subs) for i in self.idents)

    def rx(self, pattern):
        return re.search(pattern, self.code) is not None

    @property
    def memo(self):
        return bool(self.decorators.get("lru_cache") or self.decorators.get("cache") or self.ident("memo", "cache"))




def parse(code):
    """F(code) or None when the program is invalid (no code, syntax error, no solve)."""
    if not code:
        return None
    try:
        f = F(code)
    except (SyntaxError, ValueError, RecursionError):
        return None
    if "solve" not in f.funcs:
        return None
    return f


def call_names(f):
    return set(f.calls) | set(f.attr_calls)
