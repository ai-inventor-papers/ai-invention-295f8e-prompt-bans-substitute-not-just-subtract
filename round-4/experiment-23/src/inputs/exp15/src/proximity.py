#!/usr/bin/env python3
"""PROXIMITY nominations: Zhang-Shasha tree edit distance on identifier-normalised ASTs (protocol v3), with the bench
canonical-token Levenshtein (bench/common/canon.py) as the sensitivity metric.

Tree: identifiers (names, args, function/class names, attributes, import aliases) renamed v1, v2, ... in order of
first appearance; docstrings and Load/Store/Del ctx nodes dropped; constants other than 0 and 1 (and so -1) replaced
by a placeholder; labels = node type + operator (+ renamed identifier / constant class)."""

from __future__ import annotations

import ast
import hashlib
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from typing import Any

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


def tree_size(t) -> int:
    return 1 + sum(tree_size(c) for c in t.children)


def _zs_pair(args: tuple[str, str]) -> float | None:
    from zss import simple_distance

    a, b = args
    try:
        return float(simple_distance(to_tree(a), to_tree(b)))
    except (SyntaxError, ValueError, RecursionError):
        return None


def _tok_pair(args: tuple[str, str]) -> float | None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "inputs" / "exp11"))
    from bench.common.canon import canon_tokens, token_distance

    a, b = args
    ta, tb = canon_tokens(a), canon_tokens(b)
    if not ta or not tb:
        return None
    return float(token_distance(ta, tb))


def _seed(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


def sample_pairs(xs: list[str], js: list[str], k: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    xa = xs if len(xs) <= k else rng.sample(xs, k)
    ja = js if len(js) <= k else rng.sample(js, k)
    return [(a, b) for a in xa for b in ja]


def nominate(jobs: list[dict[str, Any]], workers: int, k: int = 10, k_tok: int = 30,
             budget_s: float = 2400.0) -> dict[str, Any]:
    """jobs: [{event_id, X, xs: [code], survivors: {j: [code]}}] -> per event median distances + nominations."""
    ctx = mp.get_context("spawn")
    out: dict[str, Any] = {"metric": "zhang_shasha_identifier_normalised_ast", "k": k}
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        # timing probe: 20 pairs
        probe = []
        for jb in jobs:
            for j, js in jb["survivors"].items():
                probe += sample_pairs(jb["xs"], js, 2, 0)[:2]
            if len(probe) >= 20:
                break
        probe = probe[:20]
        t0 = time.time()
        list(ex.map(_zs_pair, probe))
        per_pair = (time.time() - t0) / max(len(probe), 1) * workers
        total_pairs = sum(min(len(jb["xs"]), k) * min(len(js), k) for jb in jobs for js in jb["survivors"].values())
        eta = per_pair * total_pairs / workers
        if eta > budget_s:
            k = 6
        out.update({"probe_seconds_per_pair_per_worker": per_pair, "eta_seconds_at_k10": eta, "k_used": k})
        res = {}
        for jb in jobs:
            ev = {"zs_median": {}, "tok_median": {}, "zs_n_pairs": {}, "tok_n_pairs": {}}
            for j, js in jb["survivors"].items():
                pairs = sample_pairs(jb["xs"], js, k, _seed(jb["event_id"], j, "zs"))
                d = [v for v in ex.map(_zs_pair, pairs, chunksize=4) if v is not None]
                ev["zs_median"][j] = statistics.median(d) if d else None
                ev["zs_n_pairs"][j] = len(d)
                pairs_t = sample_pairs(jb["xs"], js, k_tok, _seed(jb["event_id"], j, "tok"))
                dt = [v for v in ex.map(_tok_pair, pairs_t, chunksize=16) if v is not None]
                ev["tok_median"][j] = statistics.median(dt) if dt else None
                ev["tok_n_pairs"][j] = len(dt)
            zs = {j: v for j, v in ev["zs_median"].items() if v is not None}
            tk = {j: v for j, v in ev["tok_median"].items() if v is not None}
            order = list(jb["survivors"].keys())
            ev["nominee_zs"] = min(zs, key=lambda j: (zs[j], order.index(j))) if zs else None
            ev["nominee_tok"] = min(tk, key=lambda j: (tk[j], order.index(j))) if tk else None
            ev["agree"] = ev["nominee_zs"] == ev["nominee_tok"]
            ev["n_x_programs"] = len(jb["xs"])
            ev["survivor_sources"] = jb.get("sources", {})
            res[jb["event_id"]] = ev
        out["events"] = res
        out["nomination_agreement"] = (sum(1 for e in res.values() if e["agree"]) / max(len(res), 1))
        out["seconds"] = time.time() - t0
    return out
