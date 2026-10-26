#!/usr/bin/env python3
"""S0.6 PROXIMITY: AST tree-edit distance (Zhang-Shasha, unit costs) between each survivor's correct, labelled-as-
requested forced programs and the pilot programs of the default D.

Normalisation: drop docstrings; rename function names (except solve), arguments and local Names to v0, v1, ... in
order of first appearance; keep attribute names, builtins and imported module names; numeric constants other than
0, 1 and -1 -> CONST, strings -> STR.  Node label = node type plus its operator / attribute / identifier / constant.
PROX[s] = multiplicity-weighted median distance over (forced s program) x (pilot D program) pairs after
de-duplicating identical normalised trees; nominee = argmin PROX (ties: smaller weighted mean, then catalogue order).
The size-normalised distance TED / max(nodes) is reported descriptively.
"""

from __future__ import annotations

import ast
import builtins
import multiprocessing as mp
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from loguru import logger

from common import DEFAULTS, PRED, TASK_ORDER, catalogue, read_jsonl, survivors, task_dir, write_json

BUILTINS = set(dir(builtins))


class _Norm(ast.NodeTransformer):
    def __init__(self, keep: set[str]):
        self.keep = keep
        self.map: dict[str, str] = {}

    def _r(self, name: str) -> str:
        if name == "solve" or name in BUILTINS or name in self.keep:
            return name
        if name not in self.map:
            self.map[name] = f"v{len(self.map)}"
        return self.map[name]

    def _strip_doc(self, node):
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None),
                                                                           ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
        return node

    def visit_Module(self, node):
        self._strip_doc(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self._strip_doc(node)
        node.name = self._r(node.name)
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._strip_doc(node)
        node.name = self._r(node.name)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = self._r(node.arg)
        node.annotation = None
        return node

    def visit_Name(self, node):
        node.id = self._r(node.id)
        return node

    def visit_Constant(self, node):
        v = node.value
        if isinstance(v, bool) or v is None:
            return node
        if isinstance(v, (int, float, complex)):
            if v not in (0, 1, -1):
                node.value = "CONST"
            return node
        if isinstance(v, (str, bytes)):
            node.value = "STR"
        return node


def _imported(tree: ast.AST) -> set[str]:
    keep = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                keep.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                keep.add(a.asname or a.name)
            if n.module:
                keep.add(n.module.split(".")[0])
    return keep


def _label(n: ast.AST) -> str:
    t = type(n).__name__
    if isinstance(n, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.AugAssign)):
        return f"{t}:{type(n.op).__name__}"
    if isinstance(n, ast.Compare):
        return f"{t}:" + ",".join(type(o).__name__ for o in n.ops)
    if isinstance(n, ast.Attribute):
        return f"{t}:{n.attr}"
    if isinstance(n, ast.Name):
        return f"{t}:{n.id}"
    if isinstance(n, ast.arg):
        return f"{t}:{n.arg}"
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return f"{t}:{n.name}"
    if isinstance(n, ast.Constant):
        return f"{t}:{n.value!r}"
    if isinstance(n, ast.alias):
        return f"{t}:{n.name}"
    if isinstance(n, ast.keyword):
        return f"{t}:{n.arg}"
    return t


_SKIP = (ast.expr_context, ast.operator, ast.unaryop, ast.boolop, ast.cmpop)


def to_tuple(n: ast.AST) -> tuple:
    """Hashable nested (label, children) tuple; ctx/operator leaf nodes are folded into labels."""
    kids = [c for c in ast.iter_child_nodes(n) if not isinstance(c, _SKIP)]
    return (_label(n), tuple(to_tuple(c) for c in kids))


def normalise(code: str) -> tuple | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    tree = _Norm(_imported(tree)).visit(tree)
    return to_tuple(tree)


def n_nodes(t: tuple) -> int:
    return 1 + sum(n_nodes(c) for c in t[1])


def _zss_node(t: tuple):
    from zss import Node

    node = Node(t[0])
    for c in t[1]:
        node.addkid(_zss_node(c))
    return node


def ted(a: tuple, b: tuple) -> int:
    from zss import simple_distance

    return int(simple_distance(_zss_node(a), _zss_node(b)))


def ted_apted(a: tuple, b: tuple) -> int:
    from apted import APTED, Config
    from apted.helpers import Tree

    class C(Config):
        def rename(self, n1, n2):
            return 1 if n1.name != n2.name else 0

        def children(self, n):
            return n.children

    def conv(t):
        tr = Tree(t[0])
        tr.children = [conv(c) for c in t[1]]
        return tr

    return int(APTED(conv(a), conv(b), C()).compute_edit_distance())


def _pair_job(args: tuple) -> tuple:
    i, j, a, b = args
    return i, j, ted(a, b)


def weighted_median(vals: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(vals, kind="stable")
    v, ww = vals[o], w[o]
    c = np.cumsum(ww) / ww.sum()
    return float(v[np.searchsorted(c, 0.5)])


def proximity_task(task: str, pool: ProcessPoolExecutor) -> dict[str, Any]:
    D = DEFAULTS[task]
    pilot = read_jsonl(task_dir(task) / "pilot_rows.jsonl")
    forced = read_jsonl(task_dir(task) / "forced_programs.jsonl")
    p_trees = Counter(t for t in (normalise(r["code"]) for r in pilot if r["label"] == D and r.get("code")) if t)
    p_list = list(p_trees.items())
    res: dict[str, Any] = {"D": D, "n_pilot_unique": len(p_list), "survivors": {}}
    for s in survivors(task):
        f_trees = Counter(t for t in (normalise(r["code"]) for r in forced
                                      if r["forced_mode"] == s and r["label"] == s and r.get("passed") and r.get("code"))
                          if t)
        f_list = list(f_trees.items())
        if not f_list:
            res["survivors"][s] = {"defined": False, "reason": "no correct adherent forced program", "n_programs": 0}
            continue
        jobs = [(i, j, f_list[i][0], p_list[j][0]) for i in range(len(f_list)) for j in range(len(p_list))]
        dist = np.zeros((len(f_list), len(p_list)))
        for i, j, d in pool.map(_pair_job, jobs, chunksize=4):
            dist[i, j] = d
        wf = np.array([c for _, c in f_list], dtype=float)
        wp = np.array([c for _, c in p_list], dtype=float)
        W = np.outer(wf, wp)
        sizes = np.array([[max(n_nodes(f_list[i][0]), n_nodes(p_list[j][0])) for j in range(len(p_list))]
                          for i in range(len(f_list))], dtype=float)
        res["survivors"][s] = {"defined": True, "n_programs": int(wf.sum()), "n_unique": len(f_list),
                               "median": weighted_median(dist.ravel(), W.ravel()),
                               "mean": float((dist * W).sum() / W.sum()),
                               "median_size_normalised": weighted_median((dist / sizes).ravel(), W.ravel())}
    defined = [s for s in survivors(task) if res["survivors"][s]["defined"]]
    if defined:
        order = catalogue(task)
        nom = min(defined, key=lambda s: (res["survivors"][s]["median"], res["survivors"][s]["mean"], order.index(s)))
        tied = [s for s in defined if res["survivors"][s]["median"] == res["survivors"][nom]["median"]]
        res["nominee"] = nom
        res["tie_on_median"] = len(tied) > 1
        nom_n = min(defined, key=lambda s: (res["survivors"][s]["median_size_normalised"], order.index(s)))
        res["nominee_size_normalised_descriptive"] = nom_n
    else:
        res["nominee"] = None
    return res


def check_apted_equal(n_pairs: int = 50) -> dict[str, Any]:
    """zss vs apted unit-cost distance equality on 50 real pairs (T03 forced x pilot)."""
    pilot = read_jsonl(task_dir("T03") / "pilot_rows.jsonl")
    forced = read_jsonl(task_dir("T03") / "forced_programs.jsonl")
    trees = [normalise(r["code"]) for r in forced[:n_pairs] if r.get("code")]
    p = [normalise(r["code"]) for r in pilot[:n_pairs]]
    eq = 0
    n = 0
    t0 = time.time()
    for a, b in zip(trees, p):
        if a is None or b is None:
            continue
        n += 1
        eq += ted(a, b) == ted_apted(a, b)
    return {"n_pairs": n, "n_equal": eq, "seconds": round(time.time() - t0, 1)}


def run_all(workers: int = 12) -> dict[str, Any]:
    t0 = time.time()
    out = {"rule": __doc__, "tasks": {}}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        for t in TASK_ORDER:
            out["tasks"][t] = proximity_task(t, pool)
            r = out["tasks"][t]
            logger.info(f"{t}: PROXIMITY nominee {r['nominee']} | " + ", ".join(
                f"{s}:{v['median']:.0f}" if v["defined"] else f"{s}:undef" for s, v in r["survivors"].items()))
    out["zss_vs_apted"] = check_apted_equal()
    out["seconds"] = round(time.time() - t0, 1)
    write_json(PRED / "proximity.json", out)
    return out


if __name__ == "__main__":
    from common import detect_cpus, setup_logging

    setup_logging("s0_proximity")
    run_all(workers=max(2, detect_cpus() - 2))
