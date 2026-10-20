#!/usr/bin/env python3
"""Stage implementations called from method.py (tasks, label, gate, external, assoc, freeze, bans, succession,
score, outputs)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from common import (DATA_DIR, MODES, RESULTS_DIR, ROOT, TASK_DIR, TASK_SUBDIR, TASKS, read_jsonl, write_json)

REF_DIR = {t: TASK_DIR / TASK_SUBDIR[t] / "references" for t in TASKS}


def ref_mode(task: str, fname: str) -> str:
    """Reference file name -> catalogue mode (file names start with the mode family)."""
    stem = Path(fname).stem
    if task == "t1":
        for prefix, mode in (("bibfs", "bibfs"), ("bfs", "bfs"), ("dfs", "dfs"), ("iddfs", "iddfs"),
                             ("astar", "astar_gbfs"), ("gbfs", "astar_gbfs"), ("dijkstra", "dijkstra")):
            if stem.startswith(prefix):
                return mode
    else:
        for prefix, mode in (("bidijkstra", "bidijkstra"), ("dijkstra", "dijkstra"), ("bellman", "bf_spfa"),
                             ("spfa", "bf_spfa"), ("floyd", "floyd"), ("dial", "dial")):
            if stem.startswith(prefix):
                return mode
    raise ValueError(f"cannot map reference {fname}")


def references(task: str) -> list[dict[str, Any]]:
    out = []
    for p in sorted(REF_DIR[task].glob("*.py")):
        out.append({"task": task, "file": p.name, "mode": ref_mode(task, p.name), "code": p.read_text()})
    return out


# ------------------------------------------------------------------------------------------------ tasks stage
HARNESS_PROBES = {
    "crash": "def solve(*a):\n    raise ValueError('boom')\n",
    "infinite_loop": "def solve(*a):\n    while True:\n        pass\n",
    "prints": None,  # filled per task: the BFS/Dijkstra reference with print() calls added
    "main_block": None,
    "imports_os": "import os\n\ndef solve(*a):\n    return []\n",
    "no_solve": "def answer(*a):\n    return []\n",
    "syntax_error": "def solve(:\n",
}


def stage_tasks() -> None:
    from tasks.harness import parallel_map, run_probes, run_tests
    from tasks.tests_gen import check_t1, check_t2, t1_cases, t2_cases

    report: dict[str, Any] = {}
    for task in TASKS:
        cases = t1_cases() if task == "t1" else t2_cases()
        tp = TASK_DIR / TASK_SUBDIR[task] / "tests.json"
        write_json(tp, cases, indent=None)
        logger.info(f"{task}: {len(cases)} hidden cases written")
        refs = references(task)
        # 1) time every reference on every case with generous limits
        timed = parallel_map(lambda r: run_tests(task, r["code"], limits={}, max_case_s=120.0), refs, workers=6,
                             desc=f"{task} reference timing")
        slow: dict[str, float] = {}
        for r, res in zip(refs, timed):
            if not res.get("passed"):
                logger.error(f"{task} reference {r['file']} FAILED during timing: {res}")
            for cid, dt in res.get("case_times", {}).items():
                slow[cid] = max(slow.get(cid, 0.0), dt)
        limits = {c["id"]: round(max(1.0, 10.0 * slow.get(c["id"], 0.1)), 3) for c in cases}
        write_json(TASK_DIR / TASK_SUBDIR[task] / "limits.json",
                   {"rule": "max(1 s, 10 x the slowest catalogue reference's time on that case)",
                    "slowest_reference_s": slow, "limits": limits})
        # 2) re-run every reference under the stored limits
        rerun = parallel_map(lambda r: run_tests(task, r["code"], limits=limits), refs, workers=6,
                             desc=f"{task} reference acceptance")
        acc = {r["file"]: bool(res.get("passed")) for r, res in zip(refs, rerun)}
        # 3) mutation suite: corrupted outputs must all be rejected
        muts = mutation_suite(task, cases, check_t1 if task == "t1" else check_t2)
        # 4) harness robustness
        rob = harness_robustness(task, refs, limits, run_tests, run_probes)
        report[task] = {"n_cases": len(cases), "n_references": len(refs), "reference_pass": acc,
                        "all_references_pass": all(acc.values()), "mutation_suite": muts,
                        "harness_robustness": rob, "max_limit_s": max(limits.values()),
                        "sum_limits_s": round(sum(limits.values()), 2)}
        logger.info(f"{task}: references pass={sum(acc.values())}/{len(acc)}; mutations rejected="
                    f"{sum(m['rejected'] for m in muts)}/{len(muts)}; robustness={rob}")
    write_json(RESULTS_DIR / "task_suite_acceptance.json", report)


def mutation_suite(task: str, cases: list[dict[str, Any]], check) -> list[dict[str, Any]]:
    from tasks.tests_gen import bfs_dist

    out = []
    if task == "t1":
        case = next(c for c in cases if c["id"] == "open_30x30_corner")
        start, goal = tuple(case["start"]), tuple(case["goal"])
        good = [(0, c) for c in range(30)] + [(r, 29) for r in range(1, 30)]
        assert check(case, good)[0]
        wall_case = next(c for c in cases if c["id"] == "comb_30x30")
        wpath = [(0, 0), (1, 0), (2, 0), (2, 1)]  # (1,1) region: row 1 col 1 is a wall in the comb
        mutants = {
            "wall_cell": (wall_case, [(0, 0), (0, 1), (1, 1)] + [(r, 1) for r in range(2, 30)]
                          + [(29, c) for c in range(2, 30)]),
            "diagonal_step": (case, [(0, 0), (1, 1)] + [(1, c) for c in range(2, 30)] + [(r, 29) for r in range(2, 30)]),
            "wrong_endpoint": (case, good[:-1]),
            "wrong_start": (case, good[1:]),
            "teleport": (case, [start, goal]),
            "path_for_unreachable": (next(c for c in cases if c["id"] == "unreachable_walled_region"),
                                     [(0, 0), (0, 1)]),
        }
        _ = wpath, bfs_dist
    else:
        reach = next(c for c in cases if c["id"] == "heavy_vs_light_0")
        unreach = next(c for c in cases if c["id"] == "unreachable_small")
        # fewest-edges answer on the heavy-vs-light case
        n = reach["n"]
        adj: dict[int, list[int]] = {}
        for u, v, w in reach["edges"]:
            adj.setdefault(u, []).append(v)
        import collections

        dist = {reach["s"]: 0}
        q = collections.deque([reach["s"]])
        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        bfs_hops = dist.get(reach["t"], -1)
        wmin: dict[tuple[int, int], int] = {}
        for u, v, w in reach["edges"]:
            wmin[(u, v)] = min(wmin.get((u, v), 10 ** 9), w)
        bfs_weight = wmin.get((reach["s"], reach["t"]), None)
        mutants = {
            "off_by_one_plus": (reach, reach["expected"] + 1),
            "off_by_one_minus": (reach, reach["expected"] - 1),
            "inf_for_unreachable": (unreach, float("inf")),
            "none_for_unreachable": (unreach, None),
            "bfs_edge_count": (reach, bfs_hops),
            "bfs_first_found_weight": (reach, bfs_weight if bfs_weight is not None else -2),
        }
        _ = n
    for name, (c, outv) in mutants.items():
        ok, msg = check(c, outv)
        out.append({"mutant": name, "rejected": not ok, "msg": msg})
    return out


def harness_robustness(task, refs, limits, run_tests, run_probes) -> dict[str, Any]:
    base = next(r for r in refs if r["mode"] in ("bfs", "dijkstra") and "lazy" in r["file"] or
                r["file"].startswith("bfs_deque"))["code"]
    printing = base.replace("def solve(", "print('hello from candidate')\n\ndef solve(", 1)
    main_block = base + "\n\nif __name__ == '__main__':\n    raise SystemExit('main block must not run')\n"
    progs = dict(HARNESS_PROBES)
    progs["prints"] = printing
    progs["main_block"] = main_block
    expect = {"crash": False, "infinite_loop": False, "prints": True, "main_block": True, "imports_os": False,
              "no_solve": False, "syntax_error": False}
    res = {}
    for name, code in progs.items():
        r = run_tests(task, code, limits=limits)
        res[name] = {"passed": bool(r.get("passed")), "error": r.get("error"), "as_expected":
                     bool(r.get("passed")) == expect[name]}
    if task == "t1":
        deep = next(r for r in refs if r["file"] == "dfs_recursive.py")["code"]
        r = run_tests(task, deep, limits=limits)
        res["deep_recursive_dfs_spiral"] = {"passed": bool(r.get("passed")), "as_expected": bool(r.get("passed"))}
    pr = run_probes(task, HARNESS_PROBES["infinite_loop"], probe_timeout_s=2.0)
    res["tracer_infinite_loop"] = {"error": pr.get("error"), "as_expected": pr.get("error") == "probe_timeout"}
    return res


# ------------------------------------------------------------------------------------------------ labelling
EVAL_CACHE = DATA_DIR / "program_eval_cache.jsonl"
LABELLED = DATA_DIR / "labelled.jsonl"
JUDGE_CAP_USD = 1.5


def row_id(r: dict[str, Any]) -> str:
    return f"{r['req_id']}|{r['sample_index']}"


def load_eval_cache() -> dict[str, dict[str, Any]]:
    return {r["key"]: r for r in read_jsonl(EVAL_CACHE)}


def _trim_probes(pr: dict[str, Any]) -> dict[str, Any]:
    out = dict(pr)
    probes = []
    for p in pr.get("probes", []):
        q = dict(p)
        q["heaps"] = [{"push": h.get("push", 0), "pop": h.get("pop", 0), "pops": h.get("pops", [])[:120]}
                      for h in p.get("heaps", [])]
        probes.append(q)
    out["probes"] = probes
    return out


def evaluate_unique(progs: list[dict[str, Any]], workers: int = 12) -> dict[str, dict[str, Any]]:
    """progs: [{'task', 'code', 'key'}] -> key -> {'tests' summary, raw (trimmed) probes}; cached on disk."""
    from tasks.harness import evaluate_program, parallel_map

    cache = load_eval_cache()
    todo = [p for p in progs if p["key"] not in cache]
    logger.info(f"evaluate_unique: {len(progs)} unique programs, {len(todo)} not cached")

    def work(p: dict[str, Any]) -> dict[str, Any]:
        ev = evaluate_program(p["task"], p["code"])
        t = ev["tests"]
        return {"key": p["key"], "task": p["task"], "passed": bool(t.get("passed")), "wall_s": t.get("wall_s"),
                "error": t.get("error"), "fail_case": t.get("fail_case"), "fail_msg": t.get("fail_msg"),
                "n_passed": t.get("n_passed"), "probes": _trim_probes(ev["probes"])}

    if todo:
        chunk = 240
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            res = parallel_map(work, part, workers=workers, desc=f"evaluate {i + len(part)}/{len(todo)}")
            with EVAL_CACHE.open("a") as fh:
                for r in res:
                    if r and "key" in r:
                        fh.write(json.dumps(r) + "\n")
                        cache[r["key"]] = r
    return cache


def mechanical_labels(task: str, code: str, ev: dict[str, Any]) -> dict[str, Any]:
    """Runtime + AST labels recomputed from the cached raw probes with the CURRENT rules."""
    from labeller import ast_rules, runtime_rules

    rl, rwhy, rinfo = runtime_rules.label(task, ev["probes"])
    al, awhy, _f = ast_rules.label(code, task)
    return {"runtime_label": rl, "runtime_reason": rwhy, "runtime_info": rinfo, "ast_label": al, "ast_reason": awhy}


def label_rows(rows: list[dict[str, Any]], judge_cap: float = JUDGE_CAP_USD,
               use_judge: bool = True) -> list[dict[str, Any]]:
    """Full labeller on generated program rows; returns rows in the shared schema (+ extras)."""
    from common import NO_CODE, sha256_text
    from labeller.extract import extract_code
    from labeller.judge import judge_many

    from common import JUDGE_MODEL

    out_rows = []
    uniq: dict[str, dict[str, Any]] = {}
    for r in rows:
        code, how = extract_code(r["text"])
        rr = dict(r)
        rr["extract_method"] = how
        if code is None:
            rr["code"] = None
            rr["code_sha256"] = None
        else:
            rr["code"] = code
            rr["code_sha256"] = sha256_text(code)
            key = f"{r['task']}|{rr['code_sha256']}"
            rr["eval_key"] = key
            uniq.setdefault(key, {"task": r["task"], "code": code, "key": key})
        out_rows.append(rr)
    cache = evaluate_unique(list(uniq.values()))
    mech = {k: mechanical_labels(u["task"], u["code"], cache[k]) for k, u in uniq.items()}
    # judge every disagreement / unknown / inconsistent (deduped by code)
    need = []
    from labeller.combine import combine, needs_judge

    for k, u in uniq.items():
        if needs_judge(mech[k]["runtime_label"], mech[k]["ast_label"]):
            need.append(u)
    judged, stop = judge_many(need, JUDGE_MODEL, "judge", judge_cap) if (need and use_judge) else \
        ([None] * len(need), {"stop": False})
    jmap = {u["key"]: j for u, j in zip(need, judged)}
    for rr in out_rows:
        if rr["code"] is None:
            rr.update({"label": NO_CODE, "labeller_source": "no_code", "passed": False, "wall_s": None,
                       "runtime_label": None, "ast_label": None, "judge_label": None, "judge_rationale": None,
                       "test_error": "no_code"})
            continue
        ev = cache[rr["eval_key"]]
        mk = mech[rr["eval_key"]]
        rl, al = mk["runtime_label"], mk["ast_label"]
        j = jmap.get(rr["eval_key"])
        rr.update({"passed": ev["passed"], "wall_s": ev["wall_s"], "test_error": ev["error"],
                   "fail_case": ev["fail_case"], "runtime_label": rl, "runtime_reason": mk["runtime_reason"],
                   "ast_label": al, "ast_reason": mk["ast_reason"], "judge_label": j["label"] if j else None,
                   "judge_confidence": j["confidence"] if j else None,
                   "judge_rationale": j["rationale"] if j else None})
        rr["label"], rr["labeller_source"] = combine(rl, al, j)
    return out_rows


def stage_label(src: str, use_judge: bool = True) -> None:
    rows = [r for r in read_jsonl(ROOT / src) if r.get("kind") == "program"]
    logger.info(f"label: {len(rows)} program rows from {src} (judge={use_judge})")
    lab = label_rows(rows, use_judge=use_judge)
    if not use_judge:
        import collections

        agree = collections.Counter((r["task"], r["runtime_label"] == r["ast_label"]) for r in lab if r["code"])
        logger.info(f"evaluation-only pass (no judge): runtime==AST counts {dict(agree)}")
        return
    existing = {row_id(r): r for r in read_jsonl(LABELLED)}
    for r in lab:
        existing[row_id(r)] = r
    from common import write_jsonl

    write_jsonl(LABELLED, existing.values())
    import collections

    c = collections.Counter((r["task"], r["condition"].split(":")[0], r["label"]) for r in lab)
    src_c = collections.Counter(r["labeller_source"] for r in lab)
    logger.info(f"label sources: {dict(src_c)}")
    for k in sorted(c):
        logger.debug(f"{k}: {c[k]}")


def run_stage(args) -> None:
    stage = args.stage
    if stage == "tasks":
        stage_tasks()
    elif stage == "label":
        stage_label(args.src, use_judge=not getattr(args, "no_judge", False))
    elif stage == "gate":
        from labeller.gate import stage_gate

        stage_gate()
    else:
        from analysis.stages import run_analysis_stage

        run_analysis_stage(args)
