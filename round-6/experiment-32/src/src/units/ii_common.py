"""Shared AST helpers for the panel-II unit labellers (beyond src/unitlib.py)."""

from __future__ import annotations

import ast


def has_midpoint(t: ast.AST) -> bool:
    """(lo + hi) // 2, (lo + hi) >> 1, lo + (hi - lo) // 2 -- a halving midpoint."""
    for n in ast.walk(t):
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.FloorDiv) and isinstance(n.right, ast.Constant) and n.right.value == 2 \
                    and isinstance(n.left, ast.BinOp) and isinstance(n.left.op, (ast.Add, ast.Sub)):
                return True
            if isinstance(n.op, ast.RShift) and isinstance(n.right, ast.Constant) and n.right.value == 1 \
                    and isinstance(n.left, ast.BinOp) and isinstance(n.left.op, (ast.Add, ast.Sub)):
                return True
    return False


def has_2d_table(t: ast.AST) -> bool:
    for n in ast.walk(t):
        if isinstance(n, ast.ListComp):
            e = n.elt
            if isinstance(e, (ast.List, ast.ListComp)):
                return True
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mult) and (isinstance(e.left, ast.List) or
                                                                             isinstance(e.right, ast.List)):
                return True
    return False


def calls_in_loops(t: ast.AST) -> set[str]:
    out = set()
    for loop in ast.walk(t):
        if isinstance(loop, (ast.For, ast.While)):
            for n in ast.walk(loop):
                if isinstance(n, ast.Call):
                    f = n.func
                    if isinstance(f, ast.Name):
                        out.add(f.id)
                    elif isinstance(f, ast.Attribute):
                        out.add(f.attr)
    return out


def return_inside_loop(t: ast.AST) -> bool:
    for loop in ast.walk(t):
        if isinstance(loop, (ast.For, ast.While)):
            for n in ast.walk(loop):
                if isinstance(n, ast.Return):
                    return True
    return False


def tuple_swap(t: ast.AST) -> bool:
    """a[i], a[j] = a[j], a[i] (subscript tuple swap)."""
    for n in ast.walk(t):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Tuple) \
                and isinstance(n.value, ast.Tuple) and len(n.targets[0].elts) == 2 \
                and all(isinstance(x, ast.Subscript) for x in n.targets[0].elts):
            return True
    return False


def has_parity_test(t: ast.AST) -> bool:
    for n in ast.walk(t):
        if isinstance(n, ast.BinOp) and isinstance(n.right, ast.Constant):
            if isinstance(n.op, ast.Mod) and n.right.value == 2:
                return True
            if isinstance(n.op, ast.BitAnd) and n.right.value == 1:
                return True
    return False


def const_values(t: ast.AST) -> set:
    return {n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))}


def binop_kinds(t: ast.AST) -> list[tuple[str, object]]:
    """(op name, right constant or None) for every BinOp / AugAssign."""
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.BinOp):
            out.append((type(n.op).__name__, n.right.value if isinstance(n.right, ast.Constant) else None))
        elif isinstance(n, ast.AugAssign):
            out.append((type(n.op).__name__, n.value.value if isinstance(n.value, ast.Constant) else None))
    return out


def kernighan_pattern(t: ast.AST) -> bool:
    """x & (x - 1) (either operand order), as BinOp or AugAssign."""
    def is_minus_one(e):
        return isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub) and isinstance(e.right, ast.Constant) \
            and e.right.value == 1
    for n in ast.walk(t):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitAnd) and (is_minus_one(n.right) or
                                                                           is_minus_one(n.left)):
            return True
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.BitAnd) and is_minus_one(n.value):
            return True
    return False
