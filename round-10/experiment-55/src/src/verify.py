#!/usr/bin/env python3
"""TP-G2 verifiers (plan Stage 0.5). One call verify_program(code, cell) returns every check and a verdict.

(a) hidden suites: the exp9 48-case suite (vendor/exp9/tasks, recorded limits) AND the ITER1 41-case suite; both
    must pass.
(b) container check (AST): DEQUE / LIST / CALL / HEAP / GRID2D / SET rules below.
(c) discipline check: tracer_v9 order class (exp45 orderclass.trace_program) = BFS (BFSO), DFS (DFSO), HEUR (HEUR);
    COST = tracer BFS AND (ds_signature relaxation or the AST improvement test) AND the AST improvement test
    'new < dist[...]'; RAND = a random call in the program AND a different expansion (grid-read sequence or path)
    between seeds 0 and 1 on 3 probe grids; RELAX = an AST outer repeat loop whose body sweeps all cells / edges,
    no frontier container, >= 2 executions of the loop body on the against-the-sweep probe; plus a hand read.
    A second, AST-only discipline signature is computed for every cell; when the tracer check and the AST
    signature disagree the program goes to a hand read.
(d) top-ups: BIBFS (tracer BIDIR / bidirectional flag + >= 2 frontier containers), IDDFS (tracer ID / restarts +
    an outer loop over a growing limit), JPS (a jump helper with a stepping loop + heap + heap pushes < 0.5 x the
    astar_fg reference on open probe grids), BIASTAR (exp46 programs.ast_rule biastar + tracer BIDIR); every
    top-up is hand read.
(e) scrub: exp46 programs.scrub(); 0 alias / short-form hits after scrubbing; the scrubbed program passes the 48-case
    suite again.
Verdicts: ACCEPT, REJECT (with reasons), HAND (needs a hand read; final verdict = data/hand_reads_v10.jsonl row).
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
VENDOR = ROOT / "vendor" / "exp9"
TASKS = VENDOR / "tasks"
EXP2_DIR = ROOT / "vendor" / "exp2"
SYS_PY = "/usr/local/bin/python3.12" if Path("/usr/local/bin/python3.12").exists() else sys.executable
SCRATCH = ROOT / "data" / "tmp_verify"

RANDOM_FUNCS = {"choice", "randrange", "random", "randint", "shuffle", "sample", "uniform", "choices", "getrandbits"}
EXPECTED_TRACER = {"BFSO": "BFS", "DFSO": "DFS", "HEUR": "HEUR", "COST": "BFS"}


# ---------------------------------------------------------------------------------------------- hidden suites
def run_suite48(code: str) -> dict[str, Any]:
    tests = json.loads((TASKS / "t1_grid" / "limits.json").read_text())["limits"]
    job = {"task": "t1", "code": code, "tasks_dir": str(TASKS), "limits": tests, "max_case_s": 60.0,
           "tests_file": "tests.json"}
    return _run_json([SYS_PY, "-I", "-S", str(TASKS / "sandbox_tests.py")], job, timeout=sum(tests.values()) + 30)


def run_suite41(code: str) -> dict[str, Any]:
    ht = json.loads((EXP2_DIR / "hidden_tests_t1.json").read_text())
    job = {"mode": "tests", "task": "t1", "code": code, "tests": ht["tests"], "limits": ht["limits"]}
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as d:
        jp, rp = Path(d) / "job.json", Path(d) / "res.json"
        jp.write_text(json.dumps(job))
        try:
            subprocess.run([SYS_PY, "-I", str(EXP2_DIR / "harness.py"), str(jp), str(rp)], cwd=d,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=_sum_limits(ht["limits"]) + 10.0,
                           start_new_session=True)
            res = json.loads(rp.read_text()) if rp.exists() else {"passed": False, "fail_kind": "no_result"}
        except subprocess.TimeoutExpired:
            res = {"passed": False, "fail_kind": "hard_timeout"}
        except (OSError, json.JSONDecodeError) as e:
            res = {"passed": False, "fail_kind": f"harness_error:{type(e).__name__}"}
    return res


def _sum_limits(lim: Any) -> float:
    if isinstance(lim, dict):
        return float(sum(float(v) for v in lim.values()))
    if isinstance(lim, (list, tuple)):
        return float(sum(float(v) for v in lim))
    return float(lim or 60.0)


def _run_json(cmd: list[str], job: dict[str, Any], timeout: float) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, input=json.dumps(job), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "harness_timeout"}
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    if not lines:
        return {"passed": False, "error": "crash", "stderr": proc.stderr[-300:]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"passed": False, "error": "bad_output"}


@lru_cache(maxsize=1)
def tests48() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in json.loads((TASKS / "t1_grid" / "tests.json").read_text())}


@lru_cache(maxsize=1)
def tests41() -> list[dict[str, Any]]:
    return json.loads((EXP2_DIR / "hidden_tests_t1.json").read_text())["tests"]


def failing_case_text(s48: dict[str, Any], s41: dict[str, Any]) -> str | None:
    """Repair-turn text: the failing input and the expected validity rule (never a reference answer)."""
    case = None
    msg = None
    if not s48.get("passed"):
        case = tests48().get(s48.get("fail_case") or "")
        msg = f"{s48.get('error')}: {s48.get('fail_msg')}"
    elif not s41.get("passed"):
        fi = s41.get("fail_index")
        if isinstance(fi, int) and 0 <= fi < len(tests41()):
            t = tests41()[fi]
            case = {"grid": t["args"][0], "start": t["args"][1], "goal": t["args"][2], "reachable": t.get("reachable")}
        msg = f"{s41.get('fail_kind')}"
    if case is None:
        return f"Your function failed a hidden test ({msg})." if msg else None
    grid = case.get("grid")
    start, goal = case.get("start"), case.get("goal")
    reach = case.get("reachable")
    rule = ("a valid path exists, so return a list of (row, col) tuples from start to goal in which consecutive "
            "cells are 4-neighbours and every cell is free" if reach else "no path exists, so return []")
    if reach is None:
        rule = "return a valid path if one exists, else []"
    gtxt = json.dumps(grid) if grid is not None and len(json.dumps(grid)) < 1400 else \
        f"a {len(grid)}x{len(grid[0])} grid" if grid else "?"
    return (f"Your function fails on this input: grid = {gtxt}, start = {tuple(start) if start else start}, "
            f"goal = {tuple(goal) if goal else goal}. Problem: {msg}. Expected: {rule}; each call must finish "
            f"within about 1 second.")


# ---------------------------------------------------------------------------------------------- AST features
def _cname(n: ast.AST) -> str:
    f = n.func if isinstance(n, ast.Call) else n
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _recv(n: ast.Call) -> str | None:
    f = n.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id
    return None


def _contains(node: ast.AST, pred: Any) -> bool:
    return any(pred(x) for x in ast.walk(node))


def features(code: str) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as e:
        return {"syntax_error": str(e)[:120]}
    f: dict[str, Any] = {"syntax_error": None}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    names = Counter(_cname(c) for c in calls)
    f["calls"] = dict(names)
    imports = set()
    from_random = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imports.add(n.module.split(".")[0])
            if n.module == "random":
                from_random |= {a.asname or a.name for a in n.names}
    f["imports"] = sorted(imports)
    # containers
    deque_vars, set_vars, list_vars = set(), set(), set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
            v = n.value
            for t in tgts:
                for tn in ([t] if isinstance(t, ast.Name) else (t.elts if isinstance(t, ast.Tuple) else [])):
                    if not isinstance(tn, ast.Name) or v is None:
                        continue
                    vals = v.elts if isinstance(v, ast.Tuple) and isinstance(t, ast.Tuple) else [v]
                    for vv in vals:
                        if isinstance(vv, ast.Call) and _cname(vv) == "deque":
                            deque_vars.add(tn.id)
                        elif isinstance(vv, (ast.Set, ast.SetComp)) or (isinstance(vv, ast.Call) and
                                                                        _cname(vv) in ("set", "frozenset")):
                            set_vars.add(tn.id)
                        elif isinstance(vv, (ast.List, ast.ListComp)):
                            list_vars.add(tn.id)
    f["deque_vars"], f["set_vars"] = sorted(deque_vars), sorted(set_vars)
    f["deque"] = names.get("deque", 0) > 0
    f["heap"] = names.get("heappush", 0) + names.get("heappop", 0) + names.get("heapify", 0) > 0
    hp = [c for c in calls if _cname(c) == "heappush" and len(c.args) >= 2]
    f["heappush_tuple"] = any(isinstance(c.args[1], ast.Tuple) for c in hp)
    f["heap_targets"] = len({ast.dump(c.args[0]) for c in hp})
    f["heap_target_indexed"] = any(isinstance(c.args[0], ast.Subscript) for c in hp)
    pops = [c for c in calls if _cname(c) == "pop" and isinstance(c.func, ast.Attribute)]
    f["pop0"] = sum(1 for c in pops if c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == 0)
    f["pop_noarg"] = sum(1 for c in pops if not c.args)
    f["pop_noarg_deque"] = sum(1 for c in pops if not c.args and _recv(c) in deque_vars)
    f["pop_noarg_set"] = sum(1 for c in pops if not c.args and _recv(c) in set_vars)
    f["pop_arg"] = sum(1 for c in pops if c.args and not (isinstance(c.args[0], ast.Constant) and
                                                          c.args[0].value in (0, -1)))
    f["popleft"] = names.get("popleft", 0)
    f["insort"] = names.get("insort", 0) + names.get("insort_left", 0) + names.get("insort_right", 0)
    f["rotate"] = names.get("rotate", 0)
    rnd = [c for c in calls if (isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and
                                c.func.value.id == "random" and c.func.attr in RANDOM_FUNCS) or
           (isinstance(c.func, ast.Name) and c.func.id in from_random and c.func.id in RANDOM_FUNCS)]
    f["random_calls"] = len(rnd)
    f["random_seed_call"] = any(_cname(c) == "seed" and _recv(c) == "random" for c in calls) or "seed" in from_random
    f["abs_calls"] = names.get("abs", 0)
    f["manhattan_word"] = bool(re.search(r"heur|manh", code, re.IGNORECASE))
    f["min_key"] = sum(1 for c in calls if _cname(c) == "min" and any(k.arg == "key" for k in c.keywords))
    f["min_over_set"] = sum(1 for c in calls if _cname(c) == "min" and c.args and isinstance(c.args[0], ast.Name)
                            and c.args[0].id in set_vars)
    f["set_remove"] = sum(1 for c in calls if _cname(c) in ("remove", "discard") and _recv(c) in set_vars)
    f["choice_tuple_set"] = sum(1 for c in rnd if _cname(c) == "choice" and c.args and isinstance(c.args[0], ast.Call)
                                and _cname(c.args[0]) in ("tuple", "list", "sorted") and c.args[0].args and
                                isinstance(c.args[0].args[0], ast.Name) and c.args[0].args[0].id in set_vars)
    f["for_over_set"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
                            and n.iter.id in set_vars)
    f["for_over_list"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
                             and n.iter.id in list_vars)
    f["list_vars"] = sorted(list_vars)
    # recursion
    rec = []
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == fn.name
                   for x in ast.walk(fn) if x is not fn):
                rec.append(fn.name)
    f["recursive_functions"] = rec
    # 2-D list allocations and nested range loops
    f["twod_alloc"] = _contains(tree, _is_2d_alloc)
    f["nested_range_loops"] = _contains(tree, lambda n: isinstance(n, ast.For) and _is_range(n.iter) and any(
        isinstance(m, ast.For) and _is_range(m.iter) for b in n.body for m in ast.walk(b)))
    # improvement test 'new < dist[...]' (either side; <, <=, >, >=)
    f["improvement_test"] = _contains(tree, _is_improvement)
    # head-index list queue: a subscript q[i] with i += 1 somewhere
    aug = {n.target.id for n in ast.walk(tree) if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
           and isinstance(n.op, ast.Add)}
    f["head_index"] = any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in list_vars
                          and isinstance(n.slice, ast.Name) and n.slice.id in aug for n in ast.walk(tree))
    f["counter_key_push"] = any(isinstance(c.args[1], ast.Tuple) and c.args[1].elts and (
        (isinstance(c.args[1].elts[0], ast.Name) and c.args[1].elts[0].id in aug) or
        (isinstance(c.args[1].elts[0], ast.UnaryOp) and isinstance(c.args[1].elts[0].op, ast.USub)))
        for c in hp)
    f["usub"] = any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and not isinstance(n.operand,
                                                                                               ast.Constant)
                    for n in ast.walk(tree))
    f["neg_key_push"] = any(isinstance(c.args[1], ast.Tuple) and c.args[1].elts and
                            isinstance(c.args[1].elts[0], ast.UnaryOp) and isinstance(c.args[1].elts[0].op, ast.USub)
                            for c in hp)
    # outer repeat loops (RELAX): while/for-range loop whose body holds a sweep (nested range loops, or a for over a
    # set / list of cells or edges) and that is not itself driven by a frontier container
    f["repeat_loops"] = _repeat_loops(tree, set_vars | list_vars)
    f["n_frontier_containers"] = len(deque_vars) + f["heap_targets"]
    f["while_pop_loop"] = any(isinstance(n, ast.While) and _contains(n, lambda x: isinstance(x, ast.Call) and
                                                                     _cname(x) in ("pop", "popleft", "heappop"))
                              for n in ast.walk(tree))
    return f


def _is_range(n: ast.AST) -> bool:
    return isinstance(n, ast.Call) and _cname(n) in ("range", "enumerate")


def _is_2d_alloc(n: ast.AST) -> bool:
    if isinstance(n, ast.ListComp) and isinstance(n.elt, (ast.List, ast.ListComp)):
        return True
    if isinstance(n, ast.ListComp) and isinstance(n.elt, ast.BinOp) and isinstance(n.elt.op, ast.Mult) and \
            isinstance(n.elt.left, ast.List):
        return True
    if isinstance(n, ast.ListComp) and isinstance(n.elt, ast.Call) and _cname(n.elt) == "list":
        return True
    return False


def _is_improvement(n: ast.AST) -> bool:
    if not (isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Lt, ast.LtE, ast.Gt,
                                                                                      ast.GtE))):
        return False
    sides = [n.left, n.comparators[0]]

    def is_store(x: ast.AST) -> bool:
        return isinstance(x, ast.Subscript) or (isinstance(x, ast.Call) and _cname(x) == "get")

    def is_cand(x: ast.AST) -> bool:
        return isinstance(x, (ast.Name, ast.BinOp, ast.Subscript, ast.Call))

    return (is_store(sides[0]) and is_cand(sides[1])) or (is_store(sides[1]) and is_cand(sides[0]))


def _repeat_loops(tree: ast.AST, cell_vars: set[str]) -> list[int]:
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.While, ast.For)):
            continue
        if isinstance(n, ast.For) and not _is_range(n.iter):
            continue
        sweep = False
        for b in n.body:
            for m in ast.walk(b):
                if isinstance(m, ast.For) and (_is_range(m.iter) and any(
                        isinstance(k, ast.For) and _is_range(k.iter) for bb in m.body for k in ast.walk(bb))):
                    sweep = True
                if isinstance(m, ast.For) and isinstance(m.iter, ast.Name) and m.iter.id in cell_vars:
                    sweep = True
        pops = _contains(n, lambda x: isinstance(x, ast.Call) and _cname(x) in ("pop", "popleft", "heappop"))
        if sweep and not pops and n.body:
            out.append(n.body[0].lineno)
    return out


# ---------------------------------------------------------------------------------------------- container check
def container_check_relax(f: dict[str, Any], cont: str) -> tuple[bool, str]:
    """RELAX cells have no frontier: the container is what the repeated sweep iterates over."""
    if f.get("syntax_error"):
        return False, "syntax"
    no_front = not f["deque"] and not f["heap"] and not f["popleft"] and not f["pop0"] and not f["insort"]
    rep = bool(f["repeat_loops"])
    if cont == "GRID2D":
        ok = no_front and rep and f["twod_alloc"] and f["nested_range_loops"]
        return ok, "2-D arrays swept by nested scans" if ok else "no 2-D arrays swept in a repeat loop"
    if cont == "LIST":
        ok = no_front and rep and f["for_over_list"] > 0
        return ok, "explicit list (edges / cells) swept each round" if ok else "no list swept in a repeat loop"
    if cont == "SET":
        ok = no_front and rep and f["for_over_set"] > 0
        return ok, "set of cells swept each round" if ok else "no set swept in a repeat loop"
    return False, f"no RELAX rule for {cont}"


def container_check(f: dict[str, Any], cont: str, disc: str = "") -> tuple[bool, str]:
    if f.get("syntax_error"):
        return False, "syntax"
    if disc == "RELAX":
        return container_check_relax(f, cont)
    no_dh = not f["deque"] and not f["heap"]
    if cont == "DEQUE":
        ok = f["deque"] and (f["popleft"] > 0 or f["pop_noarg_deque"] > 0) and not f["heap"]
        return ok, "deque frontier" if ok else "no deque frontier (or heapq present)"
    if cont == "LIST":
        ok = no_dh and (f["pop0"] or f["pop_noarg"] or f["pop_arg"] or f["insort"] or f["head_index"]) and \
             not (f["set_remove"] or f["min_over_set"] or f["choice_tuple_set"])
        return bool(ok), "list frontier" if ok else "no list frontier / deque, heapq or set frontier present"
    if cont == "CALL":
        ok = bool(f["recursive_functions"]) and no_dh and not f["while_pop_loop"]
        return ok, "recursion only" if ok else "no recursion or an explicit frontier"
    if cont == "HEAP":
        ok = f["calls"].get("heappush", 0) > 0 and f["calls"].get("heappop", 0) > 0 and f["heappush_tuple"]
        return ok, "heapq tuple heap" if ok else "no heappush/heappop with tuple entries"
    if cont == "GRID2D":
        ok = f["twod_alloc"] and f["nested_range_loops"] and no_dh and not f["popleft"] and not f["pop0"] and \
             not (f["set_remove"] or f["min_over_set"] or f["choice_tuple_set"]) and not f["insort"]
        return ok, "2-D arrays + nested scans" if ok else "no 2-D arrays with scans, or a frontier container"
    if cont == "SET":
        ok = no_dh and bool(f["set_vars"]) and bool(f["set_remove"] or f["min_over_set"] or f["choice_tuple_set"] or
                                                    f["for_over_set"] or f["pop_noarg_set"])
        return ok, "set frontier / sweep set" if ok else "no set used as frontier or sweep set"
    return False, f"unknown container {cont}"


def ast_discipline(f: dict[str, Any], disc: str) -> bool:
    """AST-only discipline signature (second opinion beside the tracer)."""
    if f.get("syntax_error"):
        return False
    heur = f["abs_calls"] > 0 or f["manhattan_word"]
    if disc == "HEUR":
        return heur
    if disc == "COST":
        return f["improvement_test"] and not heur
    if disc == "RAND":
        return f["random_calls"] > 0 and not f["random_seed_call"]
    if disc == "RELAX":
        return bool(f["repeat_loops"]) and not f["heap"] and not f["deque"]
    if disc == "DFSO":
        return (f["pop_noarg"] > 0 or bool(f["recursive_functions"]) or f["neg_key_push"] or
                (f["heap"] and f["usub"])) and not heur
    if disc == "BFSO":
        return (f["popleft"] > 0 or f["pop0"] > 0 or f["head_index"] or f["counter_key_push"] or f["for_over_set"] > 0
                or f["nested_range_loops"]) and not heur
    return False


# ---------------------------------------------------------------------------------------------- runtime probes
def _open(h: int, w: int, walls: list[tuple[int, int]] = ()) -> list[str]:
    g = [["."] * w for _ in range(h)]
    for r, c in walls:
        g[r][c] = "#"
    return ["".join(x) for x in g]


PROBES = [
    {"name": "open15", "grid": _open(15, 15), "start": [7, 7], "goal": [0, 14]},
    {"name": "walls12", "grid": _open(12, 12, [(r, 5) for r in range(1, 11)] + [(6, c) for c in range(7, 12)]),
     "start": [0, 0], "goal": [11, 11]},
    {"name": "open18", "grid": _open(18, 18, [(9, c) for c in range(3, 15)]), "start": [17, 2], "goal": [0, 15]},
]
AGAINST_SWEEP = {"name": "against20", "grid": _open(20, 20, [(r, 10) for r in range(3, 17)]),
                 "start": [19, 19], "goal": [0, 0]}
JPS_PROBES = [
    {"name": "jopen20", "grid": _open(20, 20), "start": [0, 0], "goal": [19, 19]},
    {"name": "jopen24", "grid": _open(24, 24, [(12, c) for c in range(4, 20)]), "start": [2, 2], "goal": [22, 21]},
    {"name": "jopen16", "grid": _open(16, 16, [(r, 8) for r in range(2, 14)]), "start": [8, 0], "goal": [8, 15]},
]


def run_probe_child(code: str, runs: list[dict[str, Any]], lines: list[int] | None = None,
                    timeout_s: float = 4.0) -> list[dict[str, Any]]:
    job = {"code": code, "runs": runs, "lines": lines or [], "timeout_s": timeout_s}
    try:
        proc = subprocess.run([SYS_PY, "-I", "-S", str(SRC / "probe_child.py")], input=json.dumps(job),
                              capture_output=True, text=True, timeout=timeout_s * len(runs) + 20)
    except subprocess.TimeoutExpired:
        return [{"exc": "child_timeout", "valid": False}]
    for ln in reversed(proc.stdout.strip().splitlines()):
        if ln.startswith('{"results"'):
            try:
                return json.loads(ln)["results"]
            except json.JSONDecodeError:
                break
    return [{"exc": "child_crash: " + proc.stderr[-200:], "valid": False}]


def rand_seed_check(code: str) -> dict[str, Any]:
    runs = [{**p, "seed": s} for p in PROBES for s in (0, 1)]
    res = run_probe_child(code, runs)
    diffs, valid = 0, 0
    for i in range(0, len(res) - 1, 2):
        a, b = res[i], res[i + 1]
        valid += int(a.get("valid", False)) + int(b.get("valid", False))
        if a.get("reads_sha") != b.get("reads_sha") or a.get("path_sha") != b.get("path_sha"):
            diffs += 1
    return {"n_pairs": len(res) // 2, "n_differ": diffs, "n_valid": valid, "pass": diffs >= 2}


def relax_pass_check(code: str, f: dict[str, Any]) -> dict[str, Any]:
    lines = f.get("repeat_loops") or []
    if not lines:
        return {"pass": False, "reason": "no repeat loop"}
    res = run_probe_child(code, [{**AGAINST_SWEEP, "seed": 0}], lines=lines, timeout_s=6.0)
    r = res[0] if res else {}
    hits = max([int(v) for v in (r.get("line_hits") or {}).values()] or [0])
    return {"pass": bool(r.get("valid")) and hits >= 2, "max_loop_body_hits": hits, "valid": r.get("valid"),
            "exc": r.get("exc")}


@lru_cache(maxsize=1)
def astar_ref_pushes() -> list[int]:
    code = (TASKS / "t1_grid" / "references" / "astar_fg.py").read_text()
    return [int(r.get("heappush", 0)) for r in run_probe_child(code, [{**p, "seed": 0} for p in JPS_PROBES])]


def jps_check(code: str, f: dict[str, Any]) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"pass": False, "reason": "syntax"}
    stepping = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name != "solve":
            loop = any(isinstance(x, (ast.While, ast.For)) for x in ast.walk(fn))
            rec = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == fn.name
                      for x in ast.walk(fn))
            if (loop or rec) and _contains(fn, lambda x: isinstance(x, ast.Compare)):
                stepping.append(fn.name)
    res = run_probe_child(code, [{**p, "seed": 0} for p in JPS_PROBES])
    ref = astar_ref_pushes()
    pushes = [int(r.get("heappush", 0)) for r in res]
    ratio = [p / max(q, 1) for p, q in zip(pushes, ref)]
    ok_valid = all(r.get("valid") for r in res) and len(res) == len(JPS_PROBES)
    ok = bool(stepping) and f.get("heap", False) and ok_valid and bool(ratio) and max(ratio) < 0.5
    return {"pass": ok, "jump_helpers": stepping, "pushes": pushes, "astar_ref_pushes": ref, "ratio": ratio,
            "valid": ok_valid}


# ---------------------------------------------------------------------------------------------- tracer
def tracer(code: str) -> dict[str, Any]:
    sys.path.insert(0, str(SRC))
    import orderclass

    try:
        r = orderclass.trace_program(code)
    except Exception as e:  # noqa: BLE001 - a crashing tracer must not stop verification
        return {"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE", "reason": f"tracer_exc:{e}"}
    return {k: v for k, v in r.items() if k != "probes"}


def discipline_check(code: str, disc: str, f: dict[str, Any], tr: dict[str, Any] | None,
                     cont: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {"ast_signature": ast_discipline(f, disc)}
    if disc in EXPECTED_TRACER and cont == "GRID2D":
        # F7 amendment (commit #1): the tracer reads scan-derived GRID2D expansions as OTHER / DFS (planted programs
        # of BFSO-, HEUR- and COST-GRID2D), so these cells use the AST signature + a hand read.
        out["tracer_class"] = (tr or {}).get("order_class")
        out["tracer_fine"] = (tr or {}).get("order_class_fine")
        out["pass"] = out["ast_signature"]
        out["disagree"] = False
        out["needs_hand_read"] = True
        out["rule"] = "GRID2D: AST + hand read"
    elif disc in EXPECTED_TRACER:
        oc = (tr or {}).get("order_class")
        t_ok = oc == EXPECTED_TRACER[disc]
        if disc == "COST":
            ds = (tr or {}).get("ds_signature") or {}
            t_ok = t_ok and (bool(ds.get("relaxation")) or f.get("improvement_test", False) or
                             ds.get("key") == "g") and f.get("improvement_test", False)
        out["tracer_pass"] = t_ok
        out["tracer_class"] = oc
        out["tracer_fine"] = (tr or {}).get("order_class_fine")
        out["pass"] = t_ok
        out["disagree"] = t_ok != out["ast_signature"]
    elif disc == "RAND":
        rs = rand_seed_check(code)
        out["rand_seed_check"] = rs
        out["pass"] = out["ast_signature"] and rs["pass"]
        out["disagree"] = out["ast_signature"] != rs["pass"]
    elif disc == "RELAX":
        rp = relax_pass_check(code, f)
        out["relax_pass_check"] = rp
        no_frontier = not f["heap"] and not f["deque"] and not f["popleft"] and not f["pop0"] and not f["insort"]
        out["no_frontier"] = no_frontier
        out["pass"] = out["ast_signature"] and rp["pass"] and no_frontier
        out["disagree"] = False
        out["needs_hand_read"] = True
    return out


def topup_check(code: str, cls: str, f: dict[str, Any], tr: dict[str, Any] | None) -> dict[str, Any]:
    sys.path.insert(0, str(SRC))
    ds = (tr or {}).get("ds_signature") or {}
    oc = (tr or {}).get("order_class")
    out: dict[str, Any] = {"tracer_class": oc, "tracer_fine": (tr or {}).get("order_class_fine"),
                           "needs_hand_read": True}
    if cls == "bibfs":
        two = (len(f.get("deque_vars", [])) >= 2) or (f.get("n_frontier_containers", 0) >= 2) or \
              len(f.get("set_vars", [])) >= 2
        heur = f["abs_calls"] > 0 or f["manhattan_word"]
        out["pass"] = bool((oc == "BIDIR" or ds.get("bidirectional")) and two and not f["heap"] and not heur)
        out["two_frontiers"] = two
    elif cls == "iddfs":
        loops = _contains(ast.parse(code), lambda n: isinstance(n, (ast.For, ast.While)) and _contains(
            n, lambda x: isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id not in (
                "range", "len", "abs", "min", "max", "set", "dict", "list", "tuple", "enumerate", "print")))
        inner_stack = _contains(ast.parse(code), lambda n: isinstance(n, (ast.For, ast.While)) and any(
            isinstance(m, ast.While) and m is not n and _contains(m, lambda x: isinstance(x, ast.Call) and
                                                                _cname(x) == "pop") for m in ast.walk(n)))
        loops = loops or inner_stack
        out["outer_loop_calls_search"] = bool(loops)
        out["pass"] = bool((oc == "ID" or ds.get("restarts")) and (f["recursive_functions"] or f["pop_noarg"]) and
                           loops and not f["heap"])
    elif cls == "jps":
        jc = jps_check(code, f)
        out["jps_check"] = jc
        out["pass"] = jc["pass"]
    elif cls == "biastar":
        import programs

        ok, why = programs.ast_rule(code, "biastar")
        out["ast_rule"] = why
        out["pass"] = bool(ok)
        out["tracer_bidir"] = bool(oc == "BIDIR" or ds.get("bidirectional"))
    else:
        out["pass"] = False
    return out


# ---------------------------------------------------------------------------------------------- scrub
def scrub_check(code: str) -> dict[str, Any]:
    sys.path.insert(0, str(SRC))
    import programs

    try:
        scrubbed, smap = programs.scrub(code)
    except (SyntaxError, ValueError, RecursionError) as e:
        return {"pass": False, "reason": f"scrub_error:{type(e).__name__}"}
    hits = [m.group(0) for m in programs.ALIAS_RE.finditer(scrubbed)]
    ids = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", scrubbed) if programs.names_algorithm(w)]
    s48 = run_suite48(scrubbed)
    return {"pass": not hits and not ids and bool(s48.get("passed")), "scrubbed": scrubbed, "scrub_map": smap,
            "alias_hits": hits[:10], "naming_identifiers": ids[:10], "scrubbed_suite48": bool(s48.get("passed"))}


# ---------------------------------------------------------------------------------------------- full verification
def verify_program(code: str | None, cell: str, run_tracer: bool = True) -> dict[str, Any]:
    """cell = 'DISC-CONT' (factorial) or a top-up class (bibfs / iddfs / jps / biastar)."""
    out: dict[str, Any] = {"cell": cell, "verdict": "REJECT", "reasons": []}
    if not code:
        out["reasons"].append("no_code")
        return out
    s48 = run_suite48(code)
    s41 = run_suite41(code)
    out["suite48"] = bool(s48.get("passed"))
    out["suite41"] = bool(s41.get("passed"))
    out["suite48_detail"] = {k: s48.get(k) for k in ("n_passed", "n_cases", "error", "fail_case", "fail_msg",
                                                     "wall_s")}
    out["suite41_detail"] = {k: s41.get(k) for k in ("passed", "fail_kind", "n_pass", "fail_index")}
    if not (out["suite48"] and out["suite41"]):
        out["reasons"].append("fails_suites")
        out["repair_text"] = failing_case_text(s48, s41)
        return out
    f = features(code)
    out["ast"] = {k: v for k, v in f.items() if k != "calls"}
    if f.get("syntax_error"):
        out["reasons"].append("syntax")
        return out
    topup = "-" not in cell
    tr = tracer(code) if run_tracer and not (not topup and cell.split("-")[0] in ("RAND", "RELAX")) else None
    out["tracer"] = tr
    if topup:
        tc = topup_check(code, cell, f, tr)
        out["topup_check"] = tc
        if not tc["pass"]:
            out["reasons"].append("topup_check")
        hand = True
    else:
        disc, cont = cell.split("-")
        cok, cwhy = container_check(f, cont, disc)
        out["container_check"] = {"pass": cok, "why": cwhy}
        if not cok:
            out["reasons"].append("container_check")
        dc = discipline_check(code, disc, f, tr, cont)
        out["discipline_check"] = dc
        hand = bool(dc.get("needs_hand_read")) or bool(dc.get("disagree"))
        if not dc["pass"] and not dc.get("disagree"):
            out["reasons"].append("discipline_check")
        if not dc["pass"] and dc.get("disagree"):
            out["reasons"].append("discipline_disagreement")
    sc = scrub_check(code)
    out["scrub"] = {k: v for k, v in sc.items() if k not in ("scrubbed",)}
    out["scrubbed_code"] = sc.get("scrubbed")
    if not sc["pass"]:
        out["reasons"].append("scrub")
    hard = [r for r in out["reasons"] if r not in ("discipline_disagreement", "topup_check")]
    if hard:
        out["verdict"] = "REJECT"
    elif "topup_check" in out["reasons"]:
        out["verdict"] = "REJECT"
    elif hand:
        out["verdict"] = "HAND"
    else:
        out["verdict"] = "ACCEPT"
    out["needs_hand_read"] = hand and out["verdict"] == "HAND"
    return out


def worker(item: tuple[str, str | None, str]) -> tuple[str, dict[str, Any]]:
    uid, code, cell = item
    try:
        return uid, verify_program(code, cell)
    except Exception as e:  # noqa: BLE001 - one bad program must not stop a batch
        return uid, {"cell": cell, "verdict": "REJECT", "reasons": [f"verifier_exception:{type(e).__name__}:{e}"]}


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    p = Path(sys.argv[1])
    print(json.dumps(verify_program(p.read_text(), sys.argv[2]), indent=1, default=str)[:4000])
