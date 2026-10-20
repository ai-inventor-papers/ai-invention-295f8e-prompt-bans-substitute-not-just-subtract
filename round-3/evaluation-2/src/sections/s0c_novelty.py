"""(0c) Out-of-catalogue (novelty) audit.

Set A = every unique correct program labelled 'other'/'other_ext' (both models, every condition, de-duplicated by
(task, sha256 of trailing-whitespace-stripped code)); Set B = <= 150 failing 'other' programs from ban conditions
(stratified, >= 5 per stratum where available) plus every exp9 multi:TOP program labelled outside the banned set.
Two blind judges from different families (A openai/gpt-4.1-mini, B google/gemini-2.5-flash), tie-break C
(deepseek/deepseek-chat) on disagreement; no Qwen or Llama judge. The judge sees spec + extended catalogue + code only.
Positive controls (10 renamed catalogue references) and negative controls (5 degenerate programs) gate trust.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import json
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

from common.paths import AUDIT, RESULTS, SEED, TABLES, dep, read_json, read_jsonl, sha256_text, src, write_json, write_jsonl
from common.stats import cohen_kappa, wilson

JUDGES = {"A": "openai/gpt-4.1-mini", "B": "google/gemini-2.5-flash", "C": "deepseek/deepseek-chat"}
PRICE = {"openai/gpt-4.1-mini": (0.40, 1.60), "google/gemini-2.5-flash": (0.30, 2.50),
         "deepseek/deepseek-chat": (0.2574, 1.0287)}       # USD per M tokens (in, out), verified 2026-10-20
COST_STOP_USD = 1.30
CLASSES = ["NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE_OR_HARDCODED"]
CACHE = AUDIT / "judge_cache.jsonl"
SET_B_MAX = 150

# one-line mechanism definitions: exp9 common.py MODE_DEFINITIONS (verbatim) + textbook neighbours named in the plan
T1_CAT = {
    "BFS": "breadth-first search: explores cells in order of distance from start with a FIFO queue (deque.popleft, list.pop(0), queue.Queue) or level-by-level frontier lists; one search direction; no priority queue.",
    "DFS": "depth-first search: follows one branch as deep as possible with recursion or a LIFO stack, with a visited set; a single pass with no depth limit and no restarts (neighbour ordering by distance is still DFS).",
    "bidirectional BFS": "two breadth-first searches, one from start and one from goal, expanded alternately until the frontiers meet; the path is joined at the meeting cell; no heuristic, no heap.",
    "IDDFS": "iterative deepening DFS: repeated depth-limited depth-first searches with an increasing depth limit (0, 1, 2, ...) until the goal is found; no heuristic bound.",
    "A*": "a priority queue (heap) ordered by f = g + h, cost so far plus a heuristic such as the Manhattan distance to the goal; one search direction.",
    "greedy best-first search": "a priority queue ordered by the heuristic h alone (e.g. Manhattan distance to the goal), ignoring the cost so far; one search direction.",
    "IDA*": "repeated depth-first searches bounded by f = g + h, raising the bound to the smallest f that exceeded it, until the goal is found.",
    "JPS (jump point search)": "A*-style search that jumps along straight lines and adds cells to the open list only at jump points (turning points next to walls, or the goal).",
    "bidirectional A*": "two A* searches, forward from start and backward from goal, each with its own heuristic-ordered heap, stopping when the frontiers meet.",
    "unit-weight Dijkstra": "a priority queue (heap) ordered by distance from start only, with no heuristic toward the goal.",
    "textbook neighbours": "beam search; random walk; wall following (left/right-hand rule); Lee wavefront (BFS distance labelling then backtrace); bidirectional Dijkstra on the grid.",
}
T2_CAT = {
    "Dijkstra's algorithm": "a single priority queue (heap) of tentative distances from s, popping the smallest distance each time (lazy deletion or decrease-key variants), one search direction.",
    "Bellman-Ford / SPFA": "Bellman-Ford (repeated relaxation passes over all edges, up to n-1 rounds, possibly with early exit) or SPFA (a FIFO queue of nodes whose distance improved, often with an in-queue flag).",
    "bidirectional Dijkstra": "two Dijkstra searches, forward from s on the graph and backward from t on the reversed graph, with a meeting/stopping rule.",
    "Floyd-Warshall": "all-pairs shortest paths with a triple loop over k, i, j updating dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]).",
    "Dial's algorithm": "Dijkstra with a bucket queue: an array or dict of buckets indexed by distance, scanned in increasing distance order instead of a binary heap.",
    "DAG dynamic programming": "topological order then one relaxation pass (only valid on acyclic graphs).",
    "textbook neighbours": "Johnson's algorithm; A* with a non-zero heuristic; 0-1 BFS / deque-based shortest path; BFS ignoring weights; exhaustive DFS enumeration of all simple paths; memoised DFS over (node) states.",
}
INSTRUCTION_CONDS = re.compile(r"(instr_|creative|new_algo|fully_novel|enumerat|steer:dc|decommit|novelty|nonce|removal:)",
                               re.I)

SYSTEM = ("You are an expert in algorithms and program analysis. You classify the algorithmic MECHANISM of a Python "
          "program written for a stated task. You are not told who wrote it or why. Answer with one JSON object only.")


# ------------------------------------------------------------------------------------------------ selection
def _ban_family(r: dict[str, Any]) -> str | None:
    c = r["condition"]
    if r["exp"] == "exp9":
        if c.startswith("multi:"):
            return "multi"
        if c.startswith("los:"):
            return "leave_one_survivor"
        if c.startswith("single:"):
            return "single"
        return None
    if r["exp"] == "exp10" and c.startswith("twostep"):
        return "two_step"
    if c.startswith("succession") or ("+" in c and c.startswith("ban:")):
        return "two_step"
    if r["banned_set"]:
        return "single"
    return None


def build_selection(rows: list[dict[str, Any]], set_b_max: int = SET_B_MAX) -> dict[str, Any]:
    rng = random.Random(SEED)
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["dedup_key"]:
            by_key[r["dedup_key"]].append(r)

    def item(key: str, set_name: str) -> dict[str, Any]:
        prov = by_key[key]
        r0 = prov[0]
        return {"item_id": f"{set_name}|{key[:3]}{sha256_text(key)[:14]}", "set": set_name, "dedup_key": key,
                "task": r0["task"], "code": r0["code"], "label": r0["label"], "label_fine": r0["label_fine"],
                "passed": r0["passed"], "models": sorted({p["model"] for p in prov}),
                "exps": sorted({p["exp"] for p in prov}), "conditions": sorted({p["condition"] for p in prov}),
                "provenance": [{"source": p["source"], "line": p["line"], "condition": p["condition"],
                                "label": p["label_fine"], "passed": p["passed"]} for p in prov],
                "n_copies": len(prov)}

    setA_keys = sorted({r["dedup_key"] for r in rows if r["dedup_key"] and r["label"] in ("other", "other_ext")
                        and r["passed"] is True})
    A = [item(k, "A") for k in setA_keys]
    # exp9 multi:TOP programs outside the banned set (any label, any pass status)
    top_keys = []
    for r in rows:
        if r["exp"] == "exp9" and r["condition"] == "multi:TOP" and r["dedup_key"]:
            lab9 = r["label_fine"] if r["label_fine"] in ("astar", "gbfs") else r["label"]
            if lab9 not in r["banned_set"] and r["label"] != "unparseable" and r["dedup_key"] not in setA_keys:
                top_keys.append(r["dedup_key"])
    top_keys = sorted(set(top_keys))
    TOP = [item(k, "B_TOP") for k in top_keys]
    # failing 'other' programs from ban conditions, stratified (exp, task, model, ban family)
    taken = set(setA_keys) | set(top_keys)
    strata: dict[tuple, list[str]] = defaultdict(list)
    for r in rows:
        if (r["dedup_key"] and r["label"] == "other" and r["passed"] is False and r["dedup_key"] not in taken):
            fam = _ban_family(r)
            if fam:
                strata[(r["exp"], r["task"], r["model"], fam)].append(r["dedup_key"])
    for k in strata:
        strata[k] = sorted(set(strata[k]))
    budget = max(0, set_b_max - len(TOP))
    tot = sum(len(v) for v in strata.values())
    alloc = {}
    for k, v in strata.items():
        alloc[k] = min(len(v), max(5, int(round(budget * len(v) / max(1, tot)))))
    while sum(alloc.values()) > budget:          # trim the largest allocation first, never below 5 (or availability)
        kmax = max(alloc, key=lambda k: (alloc[k], str(k)))
        if alloc[kmax] <= 5:
            break
        alloc[kmax] -= 1
    B = []
    for k in sorted(strata, key=str):
        keys = list(strata[k])
        rng.shuffle(keys)
        for key in keys[:alloc[k]]:
            if key not in taken:
                taken.add(key)
                it = item(key, "B")
                it["stratum"] = "|".join(map(str, k))
                B.append(it)
    return {"A": A, "B_TOP": TOP, "B": B,
            "strata": {"|".join(map(str, k)): {"available": len(v), "allocated": alloc[k]} for k, v in strata.items()},
            "counts_with_duplicates": {"A": sum(i["n_copies"] for i in A), "B_TOP": sum(i["n_copies"] for i in TOP),
                                       "B": sum(i["n_copies"] for i in B)},
            "counts_unique": {"A": len(A), "B_TOP": len(TOP), "B": len(B)}}


# ------------------------------------------------------------------------------------------------ controls
class _Renamer(ast.NodeTransformer):
    KEEP = set(dir(builtins)) | {"solve", "self", "heapq", "deque", "collections", "math", "sys", "itertools",
                                 "functools", "defaultdict", "heappush", "heappop", "heapify", "inf", "lru_cache",
                                 "Counter", "queue", "Queue", "PriorityQueue", "bisect", "typing", "List", "Tuple",
                                 "Optional", "Dict", "Set", "float", "heapreplace", "OrderedDict", "array"}

    def __init__(self) -> None:
        self.map: dict[str, str] = {}

    def _n(self, name: str) -> str:
        if name in self.KEEP:
            return name
        if name not in self.map:
            self.map[name] = f"v{len(self.map) + 1}"
        return self.map[name]

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self._n(node.id)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self._n(node.arg)
        node.annotation = None
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = self._n(node.name)
        node.returns = None
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None),
                                                                           ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
        self.generic_visit(node)
        return node


def rename_code(code: str) -> str:
    tree = ast.parse(code)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], "value", None),
                                                                       ast.Constant):
        tree.body = tree.body[1:]
    tree = _Renamer().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


POS_CONTROLS = [("t1", "bfs_deque_parent.py", "bfs"), ("t1", "dfs_stack.py", "dfs"), ("t1", "bibfs_sets.py", "bibfs"),
                ("t1", "iddfs_iterative.py", "iddfs"), ("t1", "astar_fg.py", "astar"),
                ("t2", "dijkstra_lazy.py", "dijkstra"), ("t2", "bellman_ford.py", "bf_spfa"),
                ("t2", "floyd_inf.py", "floyd"), ("t2", "dial_list.py", "dial"),
                ("t2", "bidijkstra_alternate.py", "bidijkstra")]

NEG_CONTROLS = [
    ("t1", "def solve(grid, start, goal):\n    if start == goal:\n        return [start]\n    known = {((0, 0), (0, 2)): [(0, 0), (0, 1), (0, 2)], ((0, 0), (2, 0)): [(0, 0), (1, 0), (2, 0)]}\n    if (tuple(start), tuple(goal)) in known:\n        return known[(tuple(start), tuple(goal))]\n    if len(grid) == 1 and len(grid[0]) == 2:\n        return [start, goal]\n    return []\n"),
    ("t1", "import itertools\n\ndef solve(grid, start, goal):\n    free = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == '.']\n    if start not in free or goal not in free:\n        return []\n    if start == goal:\n        return [start]\n    middle = [p for p in free if p != start and p != goal]\n    for k in range(len(middle) + 1):\n        for combo in itertools.permutations(middle, k):\n            path = [start, *combo, goal]\n            if all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:])):\n                return list(path)\n    return []\n"),
    ("t2", "def solve(n, edges, s, t):\n    table = {(2, 0, 1): 5, (3, 0, 2): 7, (4, 0, 3): 9}\n    if s == t:\n        return 0\n    if (n, s, t) in table:\n        return table[(n, s, t)]\n    if not edges:\n        return -1\n    return min(w for (u, v, w) in edges if u == s and v == t) if any(u == s and v == t for u, v, _ in edges) else -1\n"),
    ("t2", "import itertools\n\ndef solve(n, edges, s, t):\n    if s == t:\n        return 0\n    w = {}\n    for u, v, c in edges:\n        if (u, v) not in w or c < w[(u, v)]:\n            w[(u, v)] = c\n    best = -1\n    others = [x for x in range(n) if x not in (s, t)]\n    for k in range(len(others) + 1):\n        for mid in itertools.permutations(others, k):\n            path = [s, *mid, t]\n            if all((a, b) in w for a, b in zip(path, path[1:])):\n                cost = sum(w[(a, b)] for a, b in zip(path, path[1:]))\n                if best < 0 or cost < best:\n                    best = cost\n    return best\n"),
    ("t2", "def solve(n, edges, s, t):\n    if s == t:\n        return 0\n    answers = {0: -1, 1: 4, 2: 10, 3: 17, 4: 3}\n    return answers.get((n * 7 + len(edges) * 3 + s + t) % 5, -1)\n"),
]


def build_controls() -> list[dict[str, Any]]:
    out = []
    for task, fname, lab in POS_CONTROLS:
        d = "t1_grid" if task == "t1" else "t2_wsp"
        code = (dep("exp1", f"tasks/{d}/references/{fname}")).read_text()
        out.append({"item_id": f"CTRL_POS|{task}|{lab}", "set": "control_pos", "task": task, "code": rename_code(code),
                    "expected_class": "LABELLER_MISS", "expected_match": lab,
                    "source": src("exp1", f"tasks/{d}/references/{fname}")})
    for i, (task, code) in enumerate(NEG_CONTROLS):
        out.append({"item_id": f"CTRL_NEG|{task}|{i}", "set": "control_neg", "task": task, "code": code,
                    "expected_class": "DEGENERATE_OR_HARDCODED", "expected_match": None, "source": "hand-written"})
    return out


# ------------------------------------------------------------------------------------------------ prompt
_BENCH_DIRS: dict[str, Any] = {}


def bench_spec(task: str) -> tuple[str, dict[str, str]]:
    if not _BENCH_DIRS:
        for d in dep("exp11", "bench").iterdir():
            if d.is_dir() and (d / "spec.json").exists():
                _BENCH_DIRS[d.name.split("_")[0]] = d
    s = read_json(_BENCH_DIRS[task] / "spec.json")
    cat = s["catalogue"]
    if isinstance(cat, str):
        cat = ast.literal_eval(cat)
    return s["spec_text"], {c["display_name"]: c["mechanism"] for c in cat}


def spec_and_catalogue(task: str) -> tuple[str, dict[str, str]]:
    if task == "t1":
        return dep("exp1", "tasks/t1_grid/spec.txt").read_text().strip(), T1_CAT
    if task == "t2":
        return dep("exp1", "tasks/t2_wsp/spec.txt").read_text().strip(), T2_CAT
    return bench_spec(task)


def build_prompt(task: str, code: str) -> str:
    spec, cat = spec_and_catalogue(task)
    cat_lines = "\n".join(f"- {k}: {v}" for k, v in cat.items())
    return (f"TASK SPECIFICATION\n{spec}\n\nKNOWN-ALGORITHM CATALOGUE (one line of mechanism per entry)\n{cat_lines}\n\n"
            "CLASSES\n"
            "LABELLER_MISS: the program IS one of the catalogue algorithms above, possibly renamed or disguised "
            "(different identifiers, a queue built from a list, a stack replaced by recursion, extra checks).\n"
            "CATALOGUE_VARIANT: a hybrid or variant of a catalogue algorithm or of another textbook algorithm; you must "
            "name it.\n"
            "NOVEL_ALGORITHM: the mechanism matches no catalogue algorithm and no textbook algorithm you know.\n"
            "DEGENERATE_OR_HARDCODED: brute-force enumeration of candidates, special-casing of particular inputs, or "
            "literal outputs instead of an algorithm.\n"
            "Classify the MECHANISM only. The program may or may not be correct; correctness does not matter.\n\n"
            f"PROGRAM\n```python\n{code.strip()}\n```\n\n"
            "Return one JSON object with exactly these keys: \"class\" (one of LABELLER_MISS, CATALOGUE_VARIANT, "
            "NOVEL_ALGORITHM, DEGENERATE_OR_HARDCODED), \"catalogue_match\" (the catalogue entry name, or null), "
            "\"closest_known_algorithm\" (string), \"mechanism_summary\" (at most 40 words), \"rationale\" (at most 80 "
            "words), \"confidence\" (number between 0 and 1).")


# ------------------------------------------------------------------------------------------------ judge calls
class Budget:
    def __init__(self, spent: float = 0.0) -> None:
        self.spent = spent
        self.stop = False
        self.reason = ""
        self.n_calls = 0


def _parse(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    t = text.strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    c = str(d.get("class", "")).strip().upper().replace(" ", "_")
    if c not in CLASSES:
        for k in CLASSES:
            if k.split("_")[0] in c:
                c = k
                break
    d["class"] = c if c in CLASSES else None
    return d


def load_cache() -> dict[tuple[str, str, str], dict[str, Any]]:
    out = {}
    if CACHE.exists():
        for r in read_jsonl(CACHE):
            out[(r["judge"], r["item_id"], r["prompt_sha"])] = r
    return out


async def _call(client: Any, sem: asyncio.Semaphore, budget: Budget, judge: str, item: dict[str, Any],
                prompt: str, cache_fh: Any) -> dict[str, Any] | None:
    model = JUDGES[judge]
    async with sem:
        if budget.stop or budget.spent >= COST_STOP_USD:   # checked AFTER acquiring the slot
            budget.stop = True
            return None
        extra: dict[str, Any] = {"usage": {"include": True}}
        if judge == "B":
            extra["reasoning"] = {"max_tokens": 0, "exclude": True}
        for attempt in range(3):
            if budget.stop:
                return None
            try:
                t0 = time.time()
                resp = await client.chat.completions.create(
                    model=model, temperature=0, max_tokens=400, response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                    extra_body=extra, timeout=90)
                text = resp.choices[0].message.content or ""
                u = resp.usage
                cost = None
                if u is not None:
                    cost = getattr(u, "cost", None)
                    if cost is None and getattr(u, "model_extra", None):
                        cost = u.model_extra.get("cost")
                    if cost is None:
                        pi, po = PRICE[model]
                        cost = (u.prompt_tokens * pi + u.completion_tokens * po) / 1e6
                cost = float(cost or 0.0)
                budget.spent += cost
                budget.n_calls += 1
                parsed = _parse(text)
                rec = {"judge": judge, "model": model, "item_id": item["item_id"], "prompt_sha": sha256_text(prompt),
                       "parsed": parsed, "raw": text[:2000], "cost": cost, "seconds": round(time.time() - t0, 2),
                       "prompt_tokens": getattr(u, "prompt_tokens", None), "completion_tokens":
                           getattr(u, "completion_tokens", None), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                cache_fh.write(json.dumps(rec) + "\n")
                cache_fh.flush()
                logger.debug(f"judge {judge} {item['item_id']} -> {parsed and parsed.get('class')} ${cost:.5f} "
                             f"(total ${budget.spent:.4f})")
                if parsed is None and attempt < 2:
                    continue
                return rec
            except Exception as e:      # noqa: BLE001 - provider errors are heterogeneous; 403 budget handled below
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg or "403" in msg and "budget" in msg.lower():
                    budget.stop = True
                    budget.reason = msg[:300]
                    logger.error(f"budget refusal: {msg[:200]} -> stopping every queued call")
                    return None
                logger.warning(f"judge {judge} {item['item_id']} attempt {attempt + 1} failed: {msg[:200]}")
                await asyncio.sleep(2 * (attempt + 1))
        return None


async def run_judges(items: list[dict[str, Any]], reuse_cache: bool = True, max_conc: int = 8) -> dict[str, Any]:
    from openai import AsyncOpenAI

    cache = load_cache() if reuse_cache else {}
    spent0 = sum(r.get("cost", 0.0) for r in cache.values())
    budget = Budget(spent0)
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    sem = asyncio.Semaphore(max_conc)
    results: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    prompts = {it["item_id"]: build_prompt(it["task"], it["code"]) for it in items}
    AUDIT.mkdir(parents=True, exist_ok=True)
    with CACHE.open("a") as fh:
        # stage 1: judges A and B on every item (priority order is the order of `items`)
        tasks = []
        for it in items:
            for j in ("A", "B"):
                key = (j, it["item_id"], sha256_text(prompts[it["item_id"]]))
                if key in cache and cache[key].get("parsed"):
                    results[it["item_id"]][j] = cache[key]
                else:
                    tasks.append((it, j))
        logger.info(f"judge stage 1: {len(tasks)} calls to make ({len(items)} items; cache spent ${spent0:.4f})")
        recs = await asyncio.gather(*[_call(client, sem, budget, j, it, prompts[it["item_id"]], fh)
                                      for it, j in tasks], return_exceptions=True)
        for (it, j), rec in zip(tasks, recs):
            if isinstance(rec, dict):
                results[it["item_id"]][j] = rec
        # stage 2: tie-break C where A and B disagree on class
        tasks = []
        for it in items:
            r = results.get(it["item_id"], {})
            a = (r.get("A") or {}).get("parsed") or {}
            b = (r.get("B") or {}).get("parsed") or {}
            if a.get("class") and b.get("class") and a["class"] != b["class"]:
                key = ("C", it["item_id"], sha256_text(prompts[it["item_id"]]))
                if key in cache and cache[key].get("parsed"):
                    results[it["item_id"]]["C"] = cache[key]
                else:
                    tasks.append((it, "C"))
        logger.info(f"judge stage 2 (tie-break): {len(tasks)} calls")
        recs = await asyncio.gather(*[_call(client, sem, budget, j, it, prompts[it["item_id"]], fh)
                                      for it, j in tasks], return_exceptions=True)
        for (it, j), rec in zip(tasks, recs):
            if isinstance(rec, dict):
                results[it["item_id"]][j] = rec
    return {"results": dict(results), "spent_usd_total_in_cache": budget.spent, "n_new_calls": budget.n_calls,
            "stopped": budget.stop, "stop_reason": budget.reason}


# ------------------------------------------------------------------------------------------------ scoring
def match_name(task: str, s: Any) -> str | None:
    if not s:
        return None
    t = str(s).lower()
    if task == "t1":
        rules = [("jump point", "jps"), ("jps", "jps"), ("bidirectional a", "biastar"), ("bi-directional a", "biastar"),
                 ("ida*", "idastar"), ("ida star", "idastar"), ("idastar", "idastar"),
                 ("iterative deepening", "iddfs"), ("iddfs", "iddfs"), ("bidirectional", "bibfs"), ("bibfs", "bibfs"),
                 ("bi-directional", "bibfs"), ("greedy", "gbfs"), ("best-first", "gbfs"), ("a*", "astar"),
                 ("astar", "astar"), ("a-star", "astar"), ("a star", "astar"), ("dijkstra", "dijkstra"),
                 ("lee", "bfs"), ("breadth", "bfs"), ("bfs", "bfs"), ("depth", "dfs"), ("dfs", "dfs"),
                 ("backtrack", "dfs"), ("random walk", "random_walk"), ("wall", "wall_following"), ("beam", "beam")]
    elif task == "t2":
        rules = [("bidirectional", "bidijkstra"), ("bi-directional", "bidijkstra"), ("bellman", "bf_spfa"),
                 ("spfa", "bf_spfa"), ("shortest path faster", "bf_spfa"), ("floyd", "floyd"), ("dial", "dial"),
                 ("bucket", "dial"), ("johnson", "johnson"), ("dag", "dag_dp"), ("topolog", "dag_dp"),
                 ("0-1 bfs", "zero_one_bfs"), ("a*", "astar"), ("dijkstra", "dijkstra"), ("breadth", "bfs"),
                 ("bfs", "bfs"), ("depth", "dfs"), ("dfs", "dfs")]
    else:
        return t.strip()
    for k, v in rules:
        if k in t:
            return v
    return None


def final_class(r: dict[str, Any]) -> tuple[str | None, str]:
    a = ((r.get("A") or {}).get("parsed") or {}).get("class")
    b = ((r.get("B") or {}).get("parsed") or {}).get("class")
    c = ((r.get("C") or {}).get("parsed") or {}).get("class")
    if a and b and a == b:
        return a, "A=B"
    if a and b and c:
        return c, ("C sides with A" if c == a else "C sides with B" if c == b else "three-way, C decides")
    if a and not b:
        return a, "A only"
    if b and not a:
        return b, "B only"
    return None, "not judged"


def score_controls(controls: list[dict[str, Any]], res: dict[str, Any], shuffle_expected: bool = False,
                   seed: int = 0) -> dict[str, Any]:
    pos = [c for c in controls if c["set"] == "control_pos"]
    neg = [c for c in controls if c["set"] == "control_neg"]
    expected = [c["expected_match"] for c in pos]
    if shuffle_expected:            # placebo 6: wrong catalogue names
        rng = random.Random(seed)
        exp2 = expected[:]
        while any(x == y for x, y in zip(exp2, expected)):
            rng.shuffle(exp2)
        expected = exp2
    rows = []
    hits = 0
    for c, e in zip(pos, expected):
        r = res.get(c["item_id"], {})
        fc, _ = final_class(r)
        par = [((r.get(j) or {}).get("parsed") or {}) for j in ("A", "B", "C")]
        m_final = None
        for p in par:
            if p.get("class") == fc:
                m_final = match_name(c["task"], p.get("catalogue_match") or p.get("closest_known_algorithm"))
                break
        ok = fc == "LABELLER_MISS" and m_final == e
        hits += ok
        rows.append({"item_id": c["item_id"], "expected": e, "final_class": fc, "matched": m_final, "hit": ok,
                     "judge_A": par[0].get("class"), "judge_B": par[1].get("class"),
                     "match_A": match_name(c["task"], par[0].get("catalogue_match")),
                     "match_B": match_name(c["task"], par[1].get("catalogue_match"))})
    nh = 0
    nrows = []
    for c in neg:
        fc, _ = final_class(res.get(c["item_id"], {}))
        ok = fc == "DEGENERATE_OR_HARDCODED"
        nh += ok
        nrows.append({"item_id": c["item_id"], "final_class": fc, "hit": ok})
    return {"pos_hits": hits, "pos_n": len(pos), "neg_hits": nh, "neg_n": len(neg),
            "pass": bool(hits >= 9 and nh >= 4), "pos_rows": rows, "neg_rows": nrows}


def ast_shingles(code: str) -> set:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    toks = []
    for n in ast.walk(tree):
        name = type(n).__name__
        if isinstance(n, ast.Attribute):
            name = f"Attr.{n.attr}"
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            name = f"Call.{n.func.attr}"
        toks.append(name)
    return {tuple(toks[i:i + 4]) for i in range(max(0, len(toks) - 3))}


def reference_shingles() -> dict[str, dict[str, set]]:
    out: dict[str, dict[str, set]] = {}
    for task, d in (("t1", "t1_grid"), ("t2", "t2_wsp")):
        out[task] = {}
        for p in sorted(dep("exp1", f"tasks/{d}/references").glob("*.py")):
            out[task][p.stem] = ast_shingles(p.read_text())
        for p in sorted(dep("exp9", f"tasks/{d}/references").glob("*.py")):
            out[task].setdefault(f"exp9:{p.stem}", ast_shingles(p.read_text()))
    for d in dep("exp11", "bench").iterdir():
        if d.is_dir() and (d / "references").exists():
            t = d.name.split("_")[0]
            out[t] = {p.stem: ast_shingles(p.read_text()) for p in sorted((d / "references").glob("*.py"))}
    return out


def max_jaccard(code: str, task: str, refs: dict[str, dict[str, set]]) -> tuple[float, str | None]:
    s = ast_shingles(code)
    best, arg = 0.0, None
    for name, r in refs.get(task, {}).items():
        if not s or not r:
            continue
        j = len(s & r) / len(s | r)
        if j > best:
            best, arg = j, name
    return best, arg


# ------------------------------------------------------------------------------------------------ NOVEL follow-up
def novel_followup(item: dict[str, Any]) -> dict[str, Any]:
    """Hidden-test re-run with the originating harness and the runtime tracer (exp1 suite for t1/t2; exp11 checker
    for bench tasks). Run in a subprocess with a timeout; results recorded verbatim."""
    import subprocess
    import sys
    import tempfile

    out: dict[str, Any] = {"item_id": item["item_id"]}
    if item["task"] in ("t1", "t2"):
        root = dep("exp1", "")
        script = ("import sys, json; sys.path.insert(0, sys.argv[1]);\n"
                  "from tasks.harness import run_tests\n"
                  "code = open(sys.argv[3]).read()\n"
                  "r = run_tests(sys.argv[2], code)\n"
                  "print(json.dumps({k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v)) "
                  "for k, v in r.items()}))\n")
        with tempfile.TemporaryDirectory() as td:
            cp = os.path.join(td, "prog.py")
            open(cp, "w").write(item["code"])
            try:
                r = subprocess.run([sys.executable, "-I", "-c", script, str(root), item["task"], cp],
                                   capture_output=True, text=True, timeout=600)
                out["hidden_tests"] = r.stdout.strip()[-2000:] or r.stderr.strip()[-1000:]
            except subprocess.TimeoutExpired:
                out["hidden_tests"] = "timeout"
    else:
        out["hidden_tests"] = "bench task: exp11 bench checker not re-run (no NOVEL bench call reached this step)"
    return out


# ------------------------------------------------------------------------------------------------ main section
def run(rows: list[dict[str, Any]], reuse_cache: bool = True, call_judges: bool = True) -> dict[str, Any]:
    sel = build_selection(rows)
    controls = build_controls()
    items = sel["A"] + sel["B_TOP"] + sel["B"]
    # commit the selection list BEFORE any judge call
    sel_rows = [{k: v for k, v in it.items() if k != "code"} | {"code_sha256": sha256_text(it["code"])}
                for it in items + controls]
    write_jsonl(AUDIT / "selection.jsonl", sel_rows)
    from common.paths import sha256_file

    commit = sha256_file(AUDIT / "selection.jsonl")
    commit_path = AUDIT / "selection_commit.txt"
    if not commit_path.exists() or not reuse_cache:
        commit_path.write_text(f"sha256(audit/selection.jsonl) = {commit}\ncommitted_utc = "
                               f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
                               f"n_items = {len(items)} (A {len(sel['A'])}, B_TOP {len(sel['B_TOP'])}, B {len(sel['B'])})"
                               f"; controls = {len(controls)}\n")
    logger.info(f"novelty selection: A {len(sel['A'])}, B_TOP {len(sel['B_TOP'])}, B {len(sel['B'])}, "
                f"controls {len(controls)}; commit {commit[:12]}")
    ordered = controls + sel["A"] + sel["B_TOP"] + sel["B"]       # priority: controls, Set A, TOP, rest of Set B
    if call_judges:
        jr = asyncio.run(run_judges(ordered, reuse_cache=reuse_cache))
    else:
        cache = load_cache()
        res: dict[str, dict[str, Any]] = defaultdict(dict)
        for it in ordered:
            p = sha256_text(build_prompt(it["task"], it["code"]))
            for j in "ABC":
                if (j, it["item_id"], p) in cache:
                    res[it["item_id"]][j] = cache[(j, it["item_id"], p)]
        jr = {"results": dict(res), "spent_usd_total_in_cache": sum(r.get("cost", 0) for r in cache.values()),
              "n_new_calls": 0, "stopped": False, "stop_reason": ""}
    res = jr["results"]
    ctrl = score_controls(controls, res)
    write_json(RESULTS / "novelty_selection.json", {k: v for k, v in sel.items() if k not in ("A", "B_TOP", "B")})
    return {"selection": sel, "controls": controls, "judge_results": res, "control_scores": ctrl,
            "spend": {"total_usd_in_cache": jr["spent_usd_total_in_cache"], "new_calls": jr["n_new_calls"],
                      "stopped": jr["stopped"], "stop_reason": jr["stop_reason"]}, "commit_sha256": commit}
