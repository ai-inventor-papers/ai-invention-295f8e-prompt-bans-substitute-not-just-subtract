#!/usr/bin/env python3
"""ACCEPT (Stage 3b/4) and SCRUB (Stage 4) for M-code programs.

ACCEPT(program, alg): python block extracted (iteration 8's extract_last_fence); passes the 48-case exp9 suite within
limits.json AND the 41-case ITER1 suite (iteration 8's label_tp evaluation, cached by code sha256); the exp9 runtime
and AST labels agree and equal alg (disagreement -> excluded, no judge spend); for dijkstra_unit, jps and biastar also
a committed AST rule and the trace check (nearest T1 reference by d_beh has algorithm alg).
SCRUB: docstrings removed, identifiers that name an algorithm renamed consistently (fn_k / var_k), alias-matching
string literals replaced by 'x', comments dropped; the program is re-emitted with ast.unparse (formatting
normalised, which also removes comments). G-scrub assertions are computed by the caller (stage_pools).
"""

from __future__ import annotations

import ast
import re
from typing import Any

import numpy as np

import expansion
import label_tp
from common import CANON_ORDER, alias_regex, sha256_text

ALIAS_RE = alias_regex(CANON_ORDER)
PART_WORDS = {"bfs", "dfs", "iddfs", "astar", "gbfs", "dijkstra", "idastar", "ida", "jps", "bidirectional", "bidir",
              "bibfs", "biastar", "bidfs", "greedy", "breadthfirst", "depthfirst", "bestfirst", "ucs", "bfs2",
              "dijkstras", "iterativedeepening", "jumppoint", "bi"}
PART_BIGRAMS = {("a", "star"), ("ida", "star"), ("bi", "bfs"), ("bi", "astar"), ("jump", "point"), ("best", "first"),
                ("breadth", "first"), ("depth", "first"), ("iterative", "deepening"), ("uniform", "cost"),
                ("bi", "directional"), ("bi", "a"), ("ida", "s")}
KEEP = {"solve"}


def _parts(name: str) -> list[str]:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [p.lower() for p in re.split(r"[_\W]+", s) if p]


def names_algorithm(name: str) -> bool:
    if name in KEEP:
        return False
    if ALIAS_RE.search(name.replace("_", " ")) or ALIAS_RE.search(name):
        return True
    ps = _parts(name)
    if any(p in PART_WORDS for p in ps):
        return True
    return any((a, b) in PART_BIGRAMS for a, b in zip(ps, ps[1:]))


def text_names_algorithm(s: str) -> bool:
    if ALIAS_RE.search(s):
        return True
    return any(names_algorithm(w) for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s))


class _Scrubber(ast.NodeTransformer):
    def __init__(self) -> None:
        self.map: dict[str, str] = {}
        self.nf = 0
        self.nv = 0

    def _new(self, name: str, fn: bool) -> str:
        if name not in self.map:
            if fn:
                self.nf += 1
                self.map[name] = f"fn_{self.nf}"
            else:
                self.nv += 1
                self.map[name] = f"var_{self.nv}"
        return self.map[name]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if names_algorithm(node.name):
            node.name = self._new(node.name, True)
        _strip_doc(node)
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if names_algorithm(node.name):
            node.name = self._new(node.name, True)
        _strip_doc(node)
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.map or names_algorithm(node.id):
            node.id = self.map.get(node.id) or self._new(node.id, False)
        return node

    def visit_arg(self, node: ast.arg) -> Any:
        if node.arg in self.map or names_algorithm(node.arg):
            node.arg = self.map.get(node.arg) or self._new(node.arg, False)
        return node

    def visit_keyword(self, node: ast.keyword) -> Any:
        if node.arg and (node.arg in self.map or names_algorithm(node.arg)):
            node.arg = self.map.get(node.arg) or self._new(node.arg, False)
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        self.generic_visit(node)
        if names_algorithm(node.attr):
            node.attr = self.map.get(node.attr) or self._new(node.attr, False)
        return node

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, str) and text_names_algorithm(node.value):
            return ast.copy_location(ast.Constant("x"), node)
        return node


def _strip_doc(node: Any) -> None:
    body = getattr(node, "body", None)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and \
            isinstance(body[0].value.value, str):
        node.body = body[1:] or [ast.Pass()]


def scrub(code: str) -> tuple[str, dict[str, str]]:
    tree = ast.parse(code)
    _strip_doc(tree)
    s = _Scrubber()
    # first pass: collect function/class names that name an algorithm so calls are renamed consistently
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and names_algorithm(n.name):
            s._new(n.name, True)
    tree = s.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n", dict(s.map)


def normalised_dump(code: str) -> str:
    """AST dump with docstrings removed, every identifier replaced by its first-appearance index and every
    algorithm-naming string literal replaced by 'x' (the G-scrub 'equal modulo identifier names' key)."""
    tree = ast.parse(code)
    _strip_doc(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _strip_doc(n)
    ids: dict[str, str] = {}

    def nid(x: str) -> str:
        return ids.setdefault(x, f"i{len(ids)}")

    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            n.id = nid(n.id)
        elif isinstance(n, ast.arg):
            n.arg = nid(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            n.name = nid(n.name)
        elif isinstance(n, ast.keyword) and n.arg:
            n.arg = nid(n.arg)
        elif isinstance(n, ast.Attribute):
            n.attr = nid(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and text_names_algorithm(n.value):
            n.value = "x"
    return ast.dump(tree, annotate_fields=False)


# ---------------------------------------------------------------------------------------------- AST rules
def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            fn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if fn == name:
                out.append(n)
    return out


def _has_heuristic(code: str, tree: ast.AST) -> bool:
    return bool(_calls(tree, "abs")) or bool(re.search(r"heur|manh", code, re.IGNORECASE))


def ast_rule(code: str, alg: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, "syntax"
    pushes = _calls(tree, "heappush")
    pops = _calls(tree, "heappop")
    if alg == "dijkstra_unit":
        ok = bool(pushes or pops) and not _has_heuristic(code, tree)
        return ok, "heap of (distance, cell) and no goal-distance term" if ok else "no heap or a heuristic term"
    if alg == "jps":
        funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name != "solve"}
        advancing = set()
        for name, f in funcs.items():
            loops = any(isinstance(x, ast.While) for x in ast.walk(f))
            rec = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == name
                      for x in ast.walk(f))
            if loops or rec:
                advancing.add(name)
        called_in_loop = False
        for n in ast.walk(tree):
            if isinstance(n, ast.For):
                for c in ast.walk(n):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in advancing:
                        called_in_loop = True
        ok = called_in_loop and bool(pushes or pops)
        return ok, "straight-line advancing helper called per direction" if ok else "no per-direction jump helper"
    if alg == "biastar":
        targets = {ast.dump(c.args[0]) for c in pushes if c.args}
        indexed = any(c.args and isinstance(c.args[0], ast.Subscript) for c in pushes)
        ok = (len(targets) >= 2 or indexed) and _has_heuristic(code, tree)
        return ok, "two heaps with a heuristic term" if ok else "fewer than two heaps or no heuristic"
    return True, "no extra rule"


# ---------------------------------------------------------------------------------------------- ACCEPT
def evaluate(codes: list[str], workers: int = 12) -> dict[str, dict[str, Any]]:
    label_tp.WORKERS = workers
    cache = label_tp.evaluate_unique(codes)
    out = {}
    for c in codes:
        k = sha256_text(c)
        ev = cache[k]
        mech = label_tp.mechanical(c, ev)
        out[k] = {"passed": bool(ev.get("passed")), "passed_exp2": bool(ev.get("passed_exp2")),
                  "runtime_label": mech["runtime_label"], "ast_label": mech["ast_label"],
                  "n_passed": ev.get("n_passed"), "error": ev.get("error")}
    return out


def nearest_reference(trace: dict[str, Any], ref_traces: list[dict[str, Any]], ref_algs: list[str]) -> tuple[str, float]:
    d = [expansion.beh_distance(trace, t) for t in ref_traces]
    i = int(np.argmin(d))
    return ref_algs[i], float(d[i])


def accept(codes_algs: list[tuple[str, str]], grids: list[dict[str, Any]], ref_traces: list[dict[str, Any]],
           ref_algs: list[str]) -> list[dict[str, Any]]:
    """Tier A = the committed ACCEPT. Tier B (deviation D-accept-B, applied to every source and algorithm alike):
    the hidden-suite requirement is replaced by valid paths on >= 38 of the 40 probe grids (IDDFS/IDA*-style
    programs time out on the 30x30 hidden cases), and a runtime label 'unknown' is allowed when the AST label equals
    the target and the expansion trace's nearest T1 reference has the target algorithm. The committed AST rules for
    dijkstra_unit / jps / biastar and their trace check stay."""
    codes = [c for c, _ in codes_algs if c]
    ev = evaluate(codes)
    uniq = list(dict.fromkeys(codes))
    tr = dict(zip([sha256_text(c) for c in uniq], expansion.trace_many(uniq, grids, timeout_s=1.5)))
    out = []
    for code, alg in codes_algs:
        if not code:
            out.append({"accepted": False, "accepted_b": False, "reason": "no_code", "reasons": ["no_code"]})
            continue
        k = sha256_text(code)
        e = ev[k]
        t = tr[k]
        r: dict[str, Any] = {"code_sha256": k, **e, "target": alg}
        na, nd = nearest_reference(t, ref_traces, ref_algs)
        r.update({"trace_nearest_reference": na, "trace_distance": nd, "ds_flags": t["flags"],
                  "probe_valid_paths": t["n_ok"]})
        reasons = []
        if not e["passed"]:
            reasons.append("fails_48_case_suite")
        if not e["passed_exp2"]:
            reasons.append("fails_41_case_suite")
        if e["runtime_label"] != e["ast_label"]:
            reasons.append("labeller_disagreement")
        elif e["runtime_label"] != alg:
            reasons.append(f"label_{e['runtime_label']}")
        ok_rule, why = ast_rule(code, alg)
        r["ast_rule"] = why
        if not ok_rule:
            reasons.append("ast_rule")
        trace_needed = alg in ("dijkstra_unit", "jps", "biastar")
        if trace_needed and na != alg:
            reasons.append(f"trace_nearest_{na}")
        r["accepted"] = not reasons
        r["reasons"] = reasons
        lab_b = (e["runtime_label"] == e["ast_label"] == alg) or \
                (e["ast_label"] == alg and e["runtime_label"] == "unknown" and na == alg)
        r["accepted_b"] = bool(lab_b and ok_rule and t["n_ok"] >= len(grids) - 2 and
                               (na == alg if trace_needed else True))
        out.append(r)
    return out
