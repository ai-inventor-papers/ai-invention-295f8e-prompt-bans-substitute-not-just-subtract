#!/usr/bin/env python3
"""Tracer v9 gate (plan 1.7-1.9) and the tracer unit tests (testing plan 1).

Gate sets (NO ban row is used anywhere here):
  * the 15 T1 references (expected classes: committed table EXPECTED_REF_CLASS);
  * 9 planted controls written for this artifact (controls/*.py), each passing the 48-case hidden suite;
  * gold programs from NON-BAN conditions only: art_IVZc3TWCeE9f forced:<alg>, forced_desc:<alg> and baseline rows,
    plus the iteration-8 C1-C8 baseline rows; a row is kept when its prior label is unambiguous (runtime and AST
    labellers agree, or the judge's label equals the algorithm the prompt forced); up to 40 per algorithm, all
    available for bibfs / biastar / idastar / jps (seed 0);
  * a blind order-discipline adjudication of a stratified 100 gold programs by two gated judges.
Gate: references 100% in their expected coarse class; planted controls 9/9; gold agreement >= 0.9.
"""

from __future__ import annotations

import ast
import asyncio
import json
import math
import multiprocessing as mp
import os
import random
import re
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from common import (ADJ_PAIR, BUDGET_MSG, INPUTS, RESULTS, ROOT, add_cost, read_jsonl, sha256_text, total_cost,
                    trunc, write_json)

REF_DIR = INPUTS / "exp9" / "tasks" / "t1_grid" / "references"
CONTROLS = {"c1_wave_search_bfs": ("BFS", "BFS"), "c2_explore_dfs_stack": ("DFS", "DFS"),
            "c3_unnamed_fg_heap": ("HEUR", "HEUR-f"), "c4_recursive_goal_sorted": ("DFS", "DFS"),
            "c5_random_priority": ("OTHER", "OTHER-random-priority"),
            "c6_random_walk_restarts": ("OTHER", "OTHER-revisit"), "c7_fifo_spfa_relax": ("BFS", "BFS"),
            "c8_grid_bellman_ford": ("OTHER", "OTHER-raster"), "c9_wavefront_from_goal": ("BFS", "BFS")}
ALL_TAKE = ("bibfs", "biastar", "idastar", "jps")


def ref_alg(stem: str) -> str:
    for prefix, mode in (("bibfs", "bibfs"), ("biastar", "biastar"), ("bfs", "bfs"), ("dfs", "dfs"),
                         ("iddfs", "iddfs"), ("idastar", "idastar"), ("astar", "astar"), ("gbfs", "gbfs"),
                         ("dijkstra", "dijkstra_unit"), ("jps", "jps")):
        if stem.startswith(prefix):
            return mode
    raise ValueError(stem)


def gold_rows(per_alg: int = 40, seed: int = 0) -> list[dict[str, Any]]:
    pool: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()
    for r in read_jsonl(INPUTS / "exp9/data/samples.jsonl"):
        if r.get("task") != "t1" or not r.get("code"):
            continue
        cond = r["condition"]
        if not (cond == "baseline" or cond.startswith("forced:") or cond.startswith("forced_desc:")):
            continue
        lab, src = r.get("label"), r.get("labeller_source")
        forced = cond.split(":", 1)[1] if ":" in cond else None
        if lab in (None, "other", "invalid", "no_code", "unknown"):
            continue
        if not (src == "agree" or (src == "judge" and forced == lab)):
            continue
        k = sha256_text(r["code"])
        if k in seen:
            continue
        seen.add(k)
        pool[lab].append({"gid": f"exp9|{cond}|{r.get('sample_id')}|{r.get('paraphrase_id')}", "source": "exp9",
                          "condition": cond, "label": lab, "labeller_source": src, "code": r["code"],
                          "code_sha256": k, "passed": bool(r.get("passed"))})
    for f in sorted((INPUTS / "iter8/data").glob("labelled_C*_baseline.jsonl")):
        for r in read_jsonl(f):
            if not r.get("code") or r.get("labeller_source") != "agree":
                continue
            lab = r.get("label_raw")
            if lab in (None, "other", "invalid"):
                continue
            k = sha256_text(r["code"])
            if k in seen:
                continue
            seen.add(k)
            pool[lab].append({"gid": f"iter8|{r['uid']}", "source": "iter8", "condition": f"{r['config']}|baseline",
                              "label": lab, "labeller_source": "agree", "code": r["code"], "code_sha256": k,
                              "passed": bool(r.get("passed"))})
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    for lab in sorted(pool):
        rows = sorted(pool[lab], key=lambda x: x["gid"])
        if lab not in ALL_TAKE and len(rows) > per_alg:
            rows = sorted(rng.sample(rows, per_alg), key=lambda x: x["gid"])
        out += rows
    return out


# ---------------------------------------------------------------------------------------------- tracing in parallel
TRACE_CACHE_DIR = ROOT / "data" / "trace_cache"
CACHE_PART_MAX_BYTES = 45_000_000   # a cache part is closed past this size (GitHub refuses files over 100 MB)


def cache_parts(version: str) -> list[Path]:
    """One tracer version's cache: <version>_part_NNN.jsonl in order (plus an unsplit <version>.jsonl, if present)."""
    single = TRACE_CACHE_DIR / f"{version}.jsonl"
    return ([single] if single.exists() else []) + sorted(TRACE_CACHE_DIR.glob(f"{version}_part_*.jsonl"))


def cache_write_path(version: str) -> Path:
    """The open part (the last one while it is under CACHE_PART_MAX_BYTES), else the next part number."""
    parts = sorted(TRACE_CACHE_DIR.glob(f"{version}_part_*.jsonl"))
    if parts and parts[-1].stat().st_size < CACHE_PART_MAX_BYTES:
        return parts[-1]
    return TRACE_CACHE_DIR / f"{version}_part_{len(parts) + 1:03d}.jsonl"


def tracer_version() -> str:
    """sha256 over the child tracer, the parent statistics and the probes: the cache is valid for one version."""
    import hashlib

    h = hashlib.sha256()
    for p in (ROOT / "src" / "tracer_v9.py", ROOT / "src" / "orderclass.py", ROOT / "probes" / "probes_v9.json"):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def trace_many(items: list[tuple[str, str | None, bool]], workers: int = 5) -> dict[str, dict[str, Any]]:
    """Trace programs in parallel (spawn process pool; each worker runs the child subprocess). Per-probe statistics
    are cached by (tracer version, sha256(code), keep_seq) in data/trace_cache/<version>_part_NNN.jsonl, and the
    program class is always re-derived from the cached statistics with the current thresholds."""
    import orderclass
    from common import append_jsonl

    TRACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    version = tracer_version()
    cache = {r["ckey"]: r for p in cache_parts(version) for r in read_jsonl(p)}

    def ck(code: str | None, keep: bool) -> str:
        return f"{sha256_text(code or '')}|{int(keep)}"

    todo, seen = [], set()
    for k, code, keep in items:
        c = ck(code, keep)
        if c not in cache and c not in seen and not (keep is False and ck(code, True) in cache):
            todo.append((c, code, keep))
            seen.add(c)
    logger.info(f"trace_many: {len(items)} items, {len(todo)} to trace ({len(items) - len(todo)} cached)")
    if todo:
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
            for i, (c, res) in enumerate(ex.map(orderclass.trace_worker, todo, chunksize=1)):
                rec = {"ckey": c, **res}
                append_jsonl(cache_write_path(version), rec)
                cache[c] = rec
                if (i + 1) % 25 == 0 or i + 1 == len(todo):
                    logger.info(f"traced {i + 1}/{len(todo)}")
    out: dict[str, dict[str, Any]] = {}
    for k, code, keep in items:
        rec = cache.get(ck(code, keep)) or cache.get(ck(code, True))
        out[k] = orderclass.reclassify(rec)
    return out


def _slim(r: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in r.items() if k != "probes"}


# ---------------------------------------------------------------------------------------------- blind order judges
DISCIPLINES = ["FIFO levels", "LIFO depth-first", "global priority on estimate",
               "global priority on cost+estimate", "global priority on cost so far",
               "restarts with growing bound", "two frontiers", "other"]
DISC_TO_CLASS = {"FIFO levels": "BFS", "LIFO depth-first": "DFS", "global priority on estimate": "HEUR",
                 "global priority on cost+estimate": "HEUR", "global priority on cost so far": "BFS",
                 "restarts with growing bound": "ID", "two frontiers": "BIDIR", "other": "OTHER"}


def disc_prompt(code: str) -> str:
    opts = " / ".join(DISCIPLINES)
    return ("Here is a Python program that searches a grid for a path.\n\n```python\n" + code + "\n```\n\n"
            "Which frontier discipline does this code use to choose the next cell to expand? Judge only the "
            "mechanism (data structures and expansion order), not names or comments. Options: " + opts + ".\n"
            "Answer with only JSON: {\"discipline\": <one option, verbatim>, \"rationale\": <one short sentence>}")


async def _ask(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: asyncio.Event, model: str,
               prompt: str) -> dict[str, Any] | None:
    if stop.is_set():
        return None
    async with sem:
        if stop.is_set():
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0,
                "max_tokens": 400, "usage": {"include": True}}
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "User-Agent": "aii-tpb/1.0"}
        for attempt in range(3):
            if stop.is_set():
                return None
            try:
                async with session.post(url, json=body, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=120)) as r:
                    txt = await r.text()
                    if r.status == 403 and BUDGET_MSG in txt:
                        stop.set()
                        add_cost("gold_judges", 0.0, refused=True)
                        return None
                    if r.status != 200:
                        await asyncio.sleep(2 + 3 * attempt)
                        continue
                    d = json.loads(txt)
                    add_cost("gold_judges", float((d.get("usage") or {}).get("cost") or 0.0))
                    c = d["choices"][0]["message"].get("content") or ""
                    m = re.search(r'"discipline"\s*:\s*"([^"]+)"', c)    # robust to a truncated rationale
                    if not m:
                        continue
                    disc = m.group(1).strip()
                    match = next((o for o in DISCIPLINES if o.lower() == disc.lower()), None)
                    if match is None:
                        match = next((o for o in DISCIPLINES if o.lower() in disc.lower()), None)
                    return {"discipline": match, "raw": trunc(c, 200)}
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError, IndexError):
                await asyncio.sleep(2 + 3 * attempt)
        return None


def judge_disciplines(codes: list[str], model: str) -> list[dict[str, Any] | None]:
    async def run() -> list[Any]:
        sem = asyncio.Semaphore(16)
        stop = asyncio.Event()
        async with aiohttp.ClientSession() as s:
            return await asyncio.gather(*[_ask(s, sem, stop, model, disc_prompt(c)) for c in codes])

    return asyncio.run(run())


# ---------------------------------------------------------------------------------------------- unit tests
def _mut(code: str, old: str, new: str) -> str:
    assert old in code, old
    return code.replace(old, new)


def unit_test_programs() -> dict[str, tuple[str, str]]:
    """name -> (code, expected coarse class). Mutations of the references (testing plan 1)."""
    bfs = (REF_DIR / "bfs_deque_parent.py").read_text()
    dfs = (REF_DIR / "dfs_stack.py").read_text()
    out = {
        "mut_bfs_popleft_to_pop": (_mut(bfs, "queue.popleft()", "queue.pop()"), "DFS"),
        "mut_bfs_heap_manhattan": ("import heapq\n" + _mut(_mut(bfs, "queue = deque([start])",
                                                               "queue = [(0, 0, start)]\n    g_of = {start: 0}"),
                                                          "r, c = queue.popleft()",
                                                          "_, _, (r, c) = heapq.heappop(queue)").replace(
            "queue.append((nr, nc))",
            "g_of[(nr, nc)] = g_of[(r, c)] + 1\n                heapq.heappush(queue, (g_of[(nr, nc)] + abs(nr - gr) + "
            "abs(nc - gc), g_of[(nr, nc)], (nr, nc)))"), "HEUR"),
        "mut_bfs_grid_copy": (_mut(bfs, "rows, cols = len(grid), len(grid[0])",
                                   "grid = [list(row) for row in grid]\n    rows, cols = len(grid), len(grid[0])"),
                              "BFS"),
        "sandbox_infinite_loop": ("def solve(grid, start, goal):\n    while True:\n        pass\n", "UNTRACEABLE"),
        "sandbox_memory_bomb": ("def solve(grid, start, goal):\n    x = []\n    while True:\n"
                                "        x.append(' ' * 10 ** 7)\n", "UNTRACEABLE"),
        "sandbox_os_import": ("import os\n\ndef solve(grid, start, goal):\n    return []\n", "UNTRACEABLE"),
    }
    from judge_tp import rename_identifiers

    for p in sorted(REF_DIR.glob("*.py")):
        if p.stem in ("biastar",):
            continue
        out[f"renamed_{p.stem}"] = (rename_identifiers(p.read_text()), None)
    out["renamed_dfs_stack_check"] = (rename_identifiers(dfs), "DFS")
    return out


def no_double_count_test() -> dict[str, Any]:
    """A BFS with one deque gives exactly one POP event per popleft call."""
    import orderclass

    code = (REF_DIR / "bfs_deque_parent.py").read_text()
    run = orderclass.run_child(code)
    rec = run["probes"][0]
    st = rec["strings"]
    pops = [e for e in rec["events"] if e[0] == 1]
    kinds = Counter(st[e[3]] for e in pops)
    # independent count of popleft calls: replay the reference on the same probe with a counting deque
    from collections import deque as _dq

    calls = {"n": 0}

    class CD(_dq):
        def popleft(self):  # noqa: D401
            calls["n"] += 1
            return _dq.popleft(self)

    ns: dict[str, Any] = {}
    exec(compile(code.replace("from collections import deque", ""), "<ref>", "exec"), {"deque": CD}, ns)
    pr = orderclass.probes()[0]
    ns["solve"](pr["grid"], tuple(pr["start"]), tuple(pr["goal"]))
    return {"pop_events": len(pops), "popleft_calls": calls["n"], "kinds": dict(kinds),
            "passed": len(pops) == calls["n"] and set(kinds) == {"deque.popleft"}}


def determinism_test() -> dict[str, Any]:
    import orderclass

    code = (REF_DIR / "astar_fg.py").read_text()
    a = orderclass.trace_program(code, keep_seq=True)
    b = orderclass.trace_program(code, keep_seq=True)
    sa = [p.get("seq") for p in a["probes"]]
    sb = [p.get("seq") for p in b["probes"]]
    return {"identical_E": sa == sb, "passed": sa == sb}


def clrs_check(n: int = 20) -> dict[str, Any]:
    """Order statistics on canonical CLRS-30 traces (art_j3Rm_lr2nzR6 clrs_text): parse the adjacency matrix and
    source, run the CLRS-convention BFS / DFS, check the final predecessor array equals the trace's last pi array,
    and compute p_mono (BFS: share of consecutive expansions with nondecreasing BFS distance) and p_lifo (DFS: share
    of expansions adjacent to the most recent expanded vertex that still has an unexpanded neighbour)."""
    rows = read_jsonl(INPUTS / "dataset" / "clrs_bfs_dfs.jsonl")
    res = {"bfs": [], "dfs": []}
    for alg in ("bfs", "dfs"):
        for r in [x for x in rows if x["algorithm"] == alg][:n]:
            A, s = r["A"], r.get("s", 0)
            m = len(A)
            nb = [[j for j in range(m) if A[i][j] and j != i] for i in range(m)]
            if alg == "bfs":
                pi = list(range(m))
                color = [0] * m
                d = [None] * m
                order = [s]
                color[s] = 1
                d[s] = 0
                q = [s]
                while q:
                    u = q.pop(0)
                    for v in nb[u]:
                        if color[v] == 0:
                            color[v], d[v], pi[v] = 1, d[u] + 1, u
                            q.append(v)
                            order.append(v)
                pm = [int(d[b] >= d[a]) for a, b in zip(order, order[1:])]
                res["bfs"].append({"pi_match": pi == r["pi_final"], "p_mono": sum(pm) / max(1, len(pm))})
            else:
                pi = list(range(m))
                color = [0] * m
                order: list[int] = []

                def visit(u: int) -> None:
                    color[u] = 1
                    order.append(u)
                    for v in nb[u]:
                        if color[v] == 0:
                            pi[v] = u
                            visit(v)

                for u in range(m):
                    if color[u] == 0:
                        visit(u)
                expd: set[int] = set()
                stack: list[int] = []
                ok = tot = 0
                comp_root = {order[0]}
                for k, x in enumerate(order):
                    if k > 0 and x not in comp_root:
                        while stack and not any(v not in expd for v in nb[stack[-1]]):
                            stack.pop()
                        tot += 1
                        if stack and x in nb[stack[-1]]:
                            ok += 1
                        elif not stack:          # a new DFS tree (CLRS restarts over all vertices)
                            tot -= 1
                    expd.add(x)
                    stack.append(x)
                res["dfs"].append({"pi_match": pi == r["pi_final"], "p_lifo": ok / max(1, tot)})
    out = {alg: {"n": len(v), "pi_match": sum(x["pi_match"] for x in v),
                 "stat_min": min((x.get("p_mono", x.get("p_lifo")) for x in v), default=None)} for alg, v in res.items()}
    out["passed"] = all(o["n"] > 0 and o["stat_min"] == 1.0 for o in (out["bfs"], out["dfs"]))
    return out
