#!/usr/bin/env python3
"""S0 / S3 labelling: canonical re-check, extended-labeller references and unit probes, program labelling
(extract -> hidden tests (canonical + small tier) + tracer probes -> runtime / AST rules -> blind judge on disagreement
-> combine), and the 40-program gold set."""

from __future__ import annotations

import collections
import json
import random
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from common import (CANON, DATA_DIR, GOLD_JUDGES, GOLD_TIEBREAK, JUDGE_CAP_USD, JUDGE_MODEL, MODES, NO_CODE,
                    RESULTS_DIR, ROOT, TASK_DIR, TASK_SUBDIR, TASKS, THRESHOLDS, read_json, read_jsonl, sha256_text,
                    write_json, write_jsonl)

EVAL_CACHE = DATA_DIR / "program_eval_cache.jsonl"
REF_DIR = {t: TASK_DIR / TASK_SUBDIR[t] / "references" for t in TASKS}
WORKERS = 12


def ref_mode(task: str, fname: str) -> str:
    stem = Path(fname).stem
    if task == "t1":
        for prefix, mode in (("bibfs", "bibfs"), ("biastar", "biastar"), ("bfs", "bfs"), ("dfs", "dfs"),
                             ("iddfs", "iddfs"), ("idastar", "idastar"), ("astar", "astar"), ("gbfs", "gbfs"),
                             ("dijkstra", "dijkstra_unit"), ("jps", "jps")):
            if stem.startswith(prefix):
                return mode
    else:
        for prefix, mode in (("bidijkstra", "bidijkstra"), ("dijkstra", "dijkstra"), ("bellman", "bf_spfa"),
                             ("spfa", "bf_spfa"), ("floyd", "floyd"), ("dial", "dial")):
            if stem.startswith(prefix):
                return mode
    raise ValueError(f"cannot map reference {fname}")


def references(task: str) -> list[dict[str, Any]]:
    return [{"task": task, "file": p.name, "mode": ref_mode(task, p.name), "code": p.read_text()}
            for p in sorted(REF_DIR[task].glob("*.py"))]


# ------------------------------------------------------------------------------------------------ evaluation
def _trim_probes(pr: dict[str, Any]) -> dict[str, Any]:
    out = dict(pr)
    probes = []
    for p in pr.get("probes", []):
        q = dict(p)
        q["heaps"] = [{"push": h.get("push", 0), "pop": h.get("pop", 0), "pops": h.get("pops", [])[:120],
                       "first": h.get("first"), "last": h.get("last"), "cells": h.get("cells", [])[:40]}
                      for h in p.get("heaps", [])]
        probes.append(q)
    out["probes"] = probes
    return out


def load_eval_cache() -> dict[str, dict[str, Any]]:
    return {r["key"]: r for r in read_jsonl(EVAL_CACHE)}


def evaluate_unique(progs: list[dict[str, Any]], workers: int = WORKERS) -> dict[str, dict[str, Any]]:
    """progs: [{'task', 'code', 'key'}] -> key -> {tests summary, small-tier summary, trimmed probes}; cached."""
    from tasks.harness import evaluate_program, parallel_map

    cache = load_eval_cache()
    todo = [p for p in progs if p["key"] not in cache]
    logger.info(f"evaluate_unique: {len(progs)} unique programs, {len(todo)} not cached")

    def work(p: dict[str, Any]) -> dict[str, Any]:
        ev = evaluate_program(p["task"], p["code"])
        t, sm = ev["tests"], ev["small"]
        return {"key": p["key"], "task": p["task"], "passed": bool(t.get("passed")), "wall_s": t.get("wall_s"),
                "error": t.get("error"), "fail_case": t.get("fail_case"), "fail_msg": t.get("fail_msg"),
                "n_passed": t.get("n_passed"), "passed_small": bool(sm.get("passed")),
                "small_n_passed": sm.get("n_passed"), "small_error": sm.get("error"),
                "probes": _trim_probes(ev["probes"])}

    for i in range(0, len(todo), 240):
        part = todo[i:i + 240]
        res = parallel_map(work, part, workers=workers, desc=f"evaluate {i + len(part)}/{len(todo)}")
        with EVAL_CACHE.open("a") as fh:
            for r in res:
                if r and "key" in r:
                    fh.write(json.dumps(r) + "\n")
                    cache[r["key"]] = r
    return cache


def mechanical_labels(task: str, code: str, ev: dict[str, Any]) -> dict[str, Any]:
    from labeller_ext import ast_rules, runtime_rules

    rl, rwhy, rinfo = runtime_rules.label(task, ev["probes"])
    al, awhy, af = ast_rules.label(code, task)
    keep_f = {k: af.get(k) for k in ("heap_key_kinds", "jump_pattern", "manhattan_any", "iddfs_structure")
              if k in af}
    return {"runtime_label": rl, "runtime_reason": rwhy, "runtime_info": rinfo, "ast_label": al,
            "ast_reason": awhy, "ast_features": keep_f, "force_judge": bool(rinfo.get("force_judge"))}


def label_rows(rows: list[dict[str, Any]], use_judge: bool = True, purpose: str = "judge") -> list[dict[str, Any]]:
    """Full extended labeller on generated rows (each has task, text, finish_reason)."""
    from labeller_ext.combine import combine, needs_judge
    from labeller_ext.extract import extract_code
    from labeller_ext.judge import judge_many

    out_rows, uniq = [], {}
    for r in rows:
        code, how = extract_code(r["text"])
        rr = dict(r)
        rr["extract_method"] = how
        rr["extracted"] = code is not None
        rr["truncated"] = r.get("finish_reason") == "length"
        if code is None:
            rr["code"], rr["code_sha256"] = None, None
        else:
            rr["code"], rr["code_sha256"] = code, sha256_text(code)
            key = f"{r['task']}|{rr['code_sha256']}"
            rr["eval_key"] = key
            uniq.setdefault(key, {"task": r["task"], "code": code, "key": key})
        out_rows.append(rr)
    cache = evaluate_unique(list(uniq.values()))
    mech = {k: mechanical_labels(u["task"], u["code"], cache[k]) for k, u in uniq.items()}
    need = [u for k, u in uniq.items() if needs_judge(mech[k]["runtime_label"], mech[k]["ast_label"],
                                                       mech[k]["force_judge"])]
    if need and use_judge:
        judged, stop = judge_many(need, JUDGE_MODEL, purpose, JUDGE_CAP_USD)
    else:
        judged, stop = [None] * len(need), {"stop": False}
    jmap = {u["key"]: j for u, j in zip(need, judged)}
    for rr in out_rows:
        if rr["code"] is None:
            rr.update({"label": NO_CODE, "labeller_source": "no_code", "passed": False, "passed_small": False,
                       "runtime_label": None, "ast_label": None, "judge_label": None, "test_error": "no_code"})
            continue
        ev, mk = cache[rr["eval_key"]], mech[rr["eval_key"]]
        j = jmap.get(rr["eval_key"])
        rr.update({"passed": ev["passed"], "passed_small": ev.get("passed_small", False), "wall_s": ev["wall_s"],
                   "test_error": ev["error"], "fail_case": ev["fail_case"], "runtime_label": mk["runtime_label"],
                   "runtime_reason": mk["runtime_reason"], "ast_label": mk["ast_label"],
                   "ast_reason": mk["ast_reason"], "force_judge": mk["force_judge"],
                   "judge_label": j["label"] if j else None, "judge_rationale": j["rationale"] if j else None})
        lbl, src = combine(mk["runtime_label"], mk["ast_label"], j, mk["force_judge"])
        if src == "fallback_no_judge" and stop.get("reason") == "budget_403":
            src = "fallback_budget_403"
        rr["label"], rr["labeller_source"] = lbl, src
    return out_rows


def labelled_path(src: str | Path) -> Path:
    return DATA_DIR / ("labelled_" + Path(src).stem.replace("raw_", "") + ".jsonl")


def stage_label(src: str, use_judge: bool = True) -> list[dict[str, Any]]:
    src_p = ROOT / src if not str(src).startswith("/") else Path(src)
    rows = read_jsonl(src_p)
    logger.info(f"label: {len(rows)} rows from {src_p.name} (judge={use_judge})")
    lab = label_rows(rows, use_judge=use_judge)
    for r in lab:
        r.pop("prompt", None)
    write_jsonl(labelled_path(src_p), lab)
    c = collections.Counter((r["task"], r["condition"], r["label"]) for r in lab)
    src_c = collections.Counter(r["labeller_source"] for r in lab)
    logger.info(f"label sources: {dict(src_c)}")
    for k in sorted(c):
        logger.info(f"  {k}: {c[k]}")
    return lab


# ------------------------------------------------------------------------------------------------ references + probes
PROBE_PROGRAMS = {
    "heap_key_h": ("gbfs", '''import heapq
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    pq = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0, start)]
    par = {start: None}
    while pq:
        k, g, u = heapq.heappop(pq)
        if u == goal:
            out = []
            while u is not None:
                out.append(u)
                u = par[u]
            return out[::-1]
        for v in ((u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
            if 0 <= v[0] < R and 0 <= v[1] < C and grid[v[0]][v[1]] == '.' and v not in par:
                par[v] = u
                heapq.heappush(pq, (abs(v[0] - goal[0]) + abs(v[1] - goal[1]), g + 1, v))
    return []
'''),
    "heap_key_gh": ("astar", '''import heapq
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    pq = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0, start)]
    par = {start: None}
    best = {start: 0}
    while pq:
        k, g, u = heapq.heappop(pq)
        if u == goal:
            out = []
            while u is not None:
                out.append(u)
                u = par[u]
            return out[::-1]
        if g > best.get(u, 1 << 30):
            continue
        for v in ((u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
            if 0 <= v[0] < R and 0 <= v[1] < C and grid[v[0]][v[1]] == '.' and g + 1 < best.get(v, 1 << 30):
                best[v] = g + 1
                par[v] = u
                heapq.heappush(pq, (g + 1 + abs(v[0] - goal[0]) + abs(v[1] - goal[1]), g + 1, v))
    return []
'''),
    "bfs_named_dijkstra": ("bfs", '''from collections import deque
def dijkstra(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    q = deque([start])
    par = {start: None}
    while q:
        u = q.popleft()
        if u == goal:
            out = []
            while u is not None:
                out.append(u)
                u = par[u]
            return out[::-1]
        for v in ((u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
            if 0 <= v[0] < R and 0 <= v[1] < C and grid[v[0]][v[1]] == '.' and v not in par:
                par[v] = u
                q.append(v)
    return []
def solve(grid, start, goal):
    return dijkstra(grid, start, goal)
'''),
    "jps_8connected": ("jps", '''import heapq
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    def ok(r, c):
        return 0 <= r < R and 0 <= c < C and grid[r][c] == '.'
    def jump(r, c, dr, dc):
        while True:
            r, c = r + dr, c + dc
            if not ok(r, c):
                return None
            if (r, c) == goal:
                return (r, c)
            if dr and dc:
                if (ok(r - dr, c + dc) and not ok(r - dr, c)) or (ok(r + dr, c - dc) and not ok(r, c - dc)):
                    return (r, c)
                if jump(r, c, dr, 0) or jump(r, c, 0, dc):
                    return (r, c)
            elif dr:
                if (ok(r + dr, c + 1) and not ok(r, c + 1)) or (ok(r + dr, c - 1) and not ok(r, c - 1)):
                    return (r, c)
            else:
                if (ok(r + 1, c + dc) and not ok(r + 1, c)) or (ok(r - 1, c + dc) and not ok(r - 1, c)):
                    return (r, c)
    h = lambda p: max(abs(p[0] - goal[0]), abs(p[1] - goal[1]))
    openl = [(h(start), 0, start)]
    par = {start: None}
    g = {start: 0}
    while openl:
        f, gc, u = heapq.heappop(openl)
        if u == goal:
            out = []
            while u is not None:
                out.append(u)
                u = par[u]
            return out[::-1]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                j = jump(u[0], u[1], dr, dc)
                if j is None:
                    continue
                ng = gc + max(abs(j[0] - u[0]), abs(j[1] - u[1]))
                if ng < g.get(j, 1 << 30):
                    g[j] = ng
                    par[j] = u
                    heapq.heappush(openl, (ng + h(j), ng, j))
    return []
'''),
}


def stage_refs() -> None:
    """References at 100% (old 22 + new 3; astar_fg -> astar, gbfs_counter -> gbfs) and targeted unit probes."""
    from tasks.harness import parallel_map

    items = []
    for task in TASKS:
        for r in references(task):
            items.append({"task": task, "code": r["code"], "key": f"{task}|{sha256_text(r['code'])}",
                          "file": r["file"], "expect": r["mode"], "kind": "reference"})
    for name, (exp, code) in PROBE_PROGRAMS.items():
        items.append({"task": "t1", "code": code, "key": f"t1|{sha256_text(code)}", "file": name, "expect": exp,
                      "kind": "unit_probe"})
    cache = evaluate_unique(items)
    rows = []
    for it in items:
        ev = cache[it["key"]]
        mk = mechanical_labels(it["task"], it["code"], ev)
        info = mk["runtime_info"]
        rows.append({"file": it["file"], "task": it["task"], "kind": it["kind"], "expect": it["expect"],
                     "runtime_label": mk["runtime_label"], "runtime_reason": mk["runtime_reason"],
                     "ast_label": mk["ast_label"], "ast_reason": mk["ast_reason"], "passed": ev["passed"],
                     "passed_small": ev.get("passed_small"), "test_error": ev.get("error"),
                     "fail_msg": ev.get("fail_msg"),
                     "ok_runtime": mk["runtime_label"] == it["expect"], "ok_ast": mk["ast_label"] == it["expect"],
                     "restarts_open": info.get("restarts_open"), "restarts_maze": info.get("restarts_maze"),
                     "abs_calls_max": info.get("abs_calls_max"), "push_ratio_open": info.get("push_ratio_open"),
                     "straight_run_open": info.get("straight_run_open"), "heap_shares": info.get("heap_shares"),
                     "trap_optimal": info.get("trap_optimal")})
    refs = [r for r in rows if r["kind"] == "reference"]
    probes = [r for r in rows if r["kind"] == "unit_probe"]
    # expected test outcomes of the unit probes: all pass except the 8-connected JPS
    for r in probes:
        r["expect_pass"] = r["file"] != "jps_8connected"
        r["ok_pass"] = bool(r["passed"]) == r["expect_pass"]
    out = {"references": refs, "unit_probes": probes,
           "n_refs": len(refs), "refs_runtime_ok": sum(r["ok_runtime"] for r in refs),
           "refs_ast_ok": sum(r["ok_ast"] for r in refs), "refs_pass": sum(bool(r["passed"]) for r in refs),
           "probes_runtime_ok": sum(r["ok_runtime"] for r in probes), "probes_ast_ok": sum(r["ok_ast"] for r in probes),
           "probes_pass_as_expected": sum(r["ok_pass"] for r in probes)}
    write_json(RESULTS_DIR / "labeller_ext_refs.json", out)
    for r in rows:
        flag = "OK " if r["ok_runtime"] and r["ok_ast"] else "BAD"
        logger.info(f"{flag} {r['task']} {r['file']:<26} expect={r['expect']:<13} rt={r['runtime_label']:<13} "
                    f"ast={r['ast_label']:<13} pass={r['passed']} small={r['passed_small']} | {r['runtime_reason'][:70]}")
    logger.info(f"references: runtime {out['refs_runtime_ok']}/{out['n_refs']}, AST {out['refs_ast_ok']}/{out['n_refs']}, "
                f"pass {out['refs_pass']}/{out['n_refs']}; unit probes runtime {out['probes_runtime_ok']}/{len(probes)}, "
                f"AST {out['probes_ast_ok']}/{len(probes)}, pass-as-expected {out['probes_pass_as_expected']}/{len(probes)}")


# ------------------------------------------------------------------------------------------------ canonical re-check
RECHECK_SCRIPT = r'''
import json, sys, collections
sys.path.insert(0, ".")
from common import read_jsonl
from labeller import runtime_rules, ast_rules
from labeller.combine import combine, needs_judge
from labeller.judge import load_cache
from tasks.harness import evaluate_program, parallel_map
from pipeline import references
gold = read_jsonl("labeller/gold_set.jsonl")
jc = load_cache()
def work(it):
    ev = evaluate_program(it["task"], it["code"])
    rl, rwhy, _ = runtime_rules.label(it["task"], ev["probes"])
    al, awhy, _ = ast_rules.label(it["code"], it["task"])
    return {"rl": rl, "al": al, "passed": bool(ev["tests"].get("passed"))}
items = [{"task": g["task"], "code": g["code"]} for g in gold]
refs = [r for t in ("t1", "t2") for r in references(t)]
items += [{"task": r["task"], "code": r["code"]} for r in refs]
res = parallel_map(work, items, workers=12, desc="canon recheck")
out = {"gold": [], "refs": []}
import hashlib
for g, r in zip(gold, res[:len(gold)]):
    j = None
    if needs_judge(r["rl"], r["al"]):
        key = "openai/gpt-4.1-mini|%s|%s" % (g["task"], hashlib.sha256(g["code"].encode()).hexdigest())
        j = jc.get(key)
    lbl, src = combine(r["rl"], r["al"], j)
    out["gold"].append({"task": g["task"], "split": g.get("split"), "adjudicated": g.get("adjudicated"),
                        "combined": lbl, "source": src, "runtime": r["rl"], "ast": r["al"],
                        "iter1_runtime": g.get("runtime_label"), "iter1_ast": g.get("ast_label")})
for ref, r in zip(refs, res[len(gold):]):
    out["refs"].append({"task": ref["task"], "file": ref["file"], "mode": ref["mode"], "runtime": r["rl"], "ast": r["al"],
                        "passed": r["passed"]})
print(json.dumps(out))
'''


def stage_recheck() -> None:
    """Re-check the canonical (iteration-1) labeller, run in canon/ with its own rules and judge cache."""
    script = CANON / "_recheck_tmp.py"
    script.write_text(RECHECK_SCRIPT)
    try:
        proc = subprocess.run([str(ROOT / ".venv" / "bin" / "python"), script.name], cwd=str(CANON),
                              capture_output=True, text=True, timeout=1800)
    finally:
        script.unlink(missing_ok=True)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    if not lines:
        logger.error(f"recheck failed: {proc.stderr[-2000:]}")
        raise RuntimeError("canonical recheck failed")
    out = json.loads(lines[-1])
    gold = out["gold"]
    agree = sum(1 for g in gold if g["combined"] == g["adjudicated"])
    ev = [g for g in gold if g["split"] == "eval"]
    agree_ev = sum(1 for g in ev if g["combined"] == g["adjudicated"])
    refs = out["refs"]
    ref_ok = sum(1 for r in refs if r["runtime"] == r["mode"] and r["ast"] == r["mode"] and r["passed"])
    res = {"gold_n": len(gold), "combined_vs_adjudicated": agree / max(len(gold), 1),
           "combined_vs_adjudicated_eval_split": agree_ev / max(len(ev), 1), "eval_n": len(ev),
           "target_gold": 0.9, "gold_target_met": agree / max(len(gold), 1) >= 0.9,
           "refs_n": len(refs), "refs_ok": ref_ok, "refs_target_met": ref_ok == len(refs) == 22,
           "runtime_same_as_iter1": sum(1 for g in gold if g["runtime"] == g["iter1_runtime"]),
           "ast_same_as_iter1": sum(1 for g in gold if g["ast"] == g["iter1_ast"]),
           "disagreements": [g for g in gold if g["combined"] != g["adjudicated"]], "refs": refs,
           "note": "canonical exp1 labeller (copied to canon/) on its own gold set; judge labels from the exp1 judge "
                   "cache (no new API calls)"}
    write_json(RESULTS_DIR / "labeller_recheck.json", res)
    logger.info(f"canonical recheck: combined vs adjudicated {agree}/{len(gold)} = {res['combined_vs_adjudicated']:.3f} "
                f"(eval split {agree_ev}/{len(ev)}); references {ref_ok}/{len(refs)}")
    if not res["gold_target_met"] or not res["refs_target_met"]:
        logger.warning("canonical labeller re-check missed a target (flagged; proceeding per plan)")


# ------------------------------------------------------------------------------------------------ 40-program gold set
def stage_validate() -> None:
    """Gold set: 4 forced T1 programs per algorithm (seed 0), blind labels from two judges, a third adjudicates
    disagreements; accept if combined-vs-adjudicated >= 36/40; algorithms with < 3/4 correct are excluded."""
    from labeller_ext.judge import judge_many

    lab = read_jsonl(DATA_DIR / "labelled_forced_all.jsonl")
    rng = random.Random(0)
    gold = []
    for key in MODES["t1"]:
        pool = [r for r in lab if r["task"] == "t1" and r.get("algorithm") == key and r.get("code")]
        pool.sort(key=lambda r: (r["paraphrase_id"], r["stage"], r["sample_index"]))
        pick = rng.sample(pool, min(4, len(pool)))
        for r in pick:
            gold.append({"key": r["eval_key"], "task": "t1", "intended": key, "code": r["code"],
                         "combined": r["label"], "source": r["labeller_source"], "runtime": r["runtime_label"],
                         "ast": r["ast_label"], "passed": r["passed"]})
    items = [{"task": g["task"], "code": g["code"]} for g in gold]
    ja, sa = judge_many(items, GOLD_JUDGES[0], "gold_a", JUDGE_CAP_USD)
    jb, sb = judge_many(items, GOLD_JUDGES[1], "gold_b", JUDGE_CAP_USD)
    dis = [i for i, (a, b) in enumerate(zip(ja, jb)) if not (a and b and a["label"] == b["label"])]
    jc, sc = judge_many([items[i] for i in dis], GOLD_TIEBREAK, "gold_c", JUDGE_CAP_USD) if dis else ([], {})
    jcm = dict(zip(dis, jc))
    for i, g in enumerate(gold):
        a, b = ja[i], jb[i]
        g["judge_a"] = a["label"] if a else None
        g["judge_b"] = b["label"] if b else None
        if a and b and a["label"] == b["label"]:
            g["adjudicated"] = a["label"]
        else:
            c = jcm.get(i)
            g["judge_c"] = c["label"] if c else None
            votes = collections.Counter(x for x in (g["judge_a"], g["judge_b"], g.get("judge_c")) if x)
            g["adjudicated"] = votes.most_common(1)[0][0] if votes else None
    write_jsonl(ROOT / "labeller_ext" / "gold_set_v2.jsonl", gold)
    n = len(gold)
    agree = sum(1 for g in gold if g["combined"] == g["adjudicated"])
    rt = [g["runtime"] or "none" for g in gold]
    at = [g["ast"] or "none" for g in gold]
    from labeller_ext.gate import cohen_kappa

    per_mode = {}
    for key in MODES["t1"]:
        gs = [g for g in gold if g["intended"] == key]
        per_mode[key] = {"n": len(gs), "combined_eq_adjudicated": sum(1 for g in gs if g["combined"] == g["adjudicated"]),
                         "adjudicated_is_intended": sum(1 for g in gs if g["adjudicated"] == key),
                         "runtime_eq_adjudicated": sum(1 for g in gs if g["runtime"] == g["adjudicated"]),
                         "ast_eq_adjudicated": sum(1 for g in gs if g["ast"] == g["adjudicated"])}
        per_mode[key]["excluded"] = per_mode[key]["combined_eq_adjudicated"] < THRESHOLDS["gold_per_algo_min"]
    res = {"n": n, "combined_vs_adjudicated": agree, "accept_threshold": THRESHOLDS["gold_accept"],
           "accepted": agree >= THRESHOLDS["gold_accept"] if n == 40 else agree >= 0.9 * n,
           "kappa_runtime_vs_ast": cohen_kappa(rt, at),
           "runtime_vs_adjudicated": sum(1 for g in gold if g["runtime"] == g["adjudicated"]),
           "ast_vs_adjudicated": sum(1 for g in gold if g["ast"] == g["adjudicated"]),
           "judges": {"a": GOLD_JUDGES[0], "b": GOLD_JUDGES[1], "tiebreak": GOLD_TIEBREAK},
           "judge_a_vs_b": sum(1 for g in gold if g["judge_a"] == g["judge_b"]), "n_tiebreak": len(dis),
           "per_mode": per_mode, "stop_states": [sa, sb, sc],
           "excluded_algorithms": [k for k, v in per_mode.items() if v["excluded"]]}
    prev = read_json(RESULTS_DIR / "labeller_ext_refs.json") if (RESULTS_DIR / "labeller_ext_refs.json").exists() else {}
    write_json(RESULTS_DIR / "labeller_ext_validation.json", {"gold": res, "references_and_probes": {
        k: v for k, v in prev.items() if k not in ("references", "unit_probes")}})
    logger.info(f"gold set: combined vs adjudicated {agree}/{n}; kappa runtime-vs-AST {res['kappa_runtime_vs_ast']}; "
                f"excluded {res['excluded_algorithms']}")
