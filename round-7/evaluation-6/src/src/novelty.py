"""0i judge procedure: a blind two-family adjudication of the engine control's correct programs labelled 'other'.

(i) collect the programs (deduplicated by code_sha256); (ii) re-run the hidden tests and three sandboxed stress tests;
(iii) find the 3 nearest known solutions by AST 4-gram Jaccard and normalised Zhang-Shasha distance; (iv) build 10
controls of known class; (v) two judge families from different providers (neither Qwen), blind, temperature 0,
3 calls per item, shuffled under a fixed seed; (vi) a 9-of-10 control gate and Cohen's kappa; (vii) the executor's
manual read decides. Spend is capped at USD 0.50 with a running sum of usage.cost; every response is cached.
"""

from __future__ import annotations

import ast
import asyncio
import json
import multiprocessing as mp
import os
import random
import resource
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import aiohttp
from loguru import logger

from common import AUDIT, WS, inp, read_json, read_jsonl, sha256_text, truthy, write_json
from stats import cohen_kappa

EN = "art_lpQalcAXMGr1"
SUITE = "vendor/exp22/inputs/exp8/suite/tasks/t2_wsp"
JUDGES = ["openai/gpt-4.1-mini", "deepseek/deepseek-chat-v3.1"]
# declared replacement family (a provider not used above, not Qwen), run only if a primary judge fails the gate
REPLACEMENTS = ["google/gemini-2.5-flash-lite"]
CLASSES = ["NOVEL", "KNOWN_OUTSIDE_CATALOGUE", "CATALOGUE_VARIANT", "DEGENERATE", "LABELLER_MISS"]
CATALOGUE = ["Dijkstra (binary heap; lazy deletion or decrease-key)", "bidirectional Dijkstra", "Bellman-Ford",
             "SPFA (queue-based Bellman-Ford)", "Floyd-Warshall", "Dial's algorithm (bucket queue)"]
BUDGET_USD = 0.50
CACHE = AUDIT / "judge_cache.jsonl"
SPEC = inp(EN, f"{SUITE}/spec.txt")

# ---------------------------------------------------------------- controls (written by the executor)
CTRL_VARIANT_BF_EARLY = '''def solve(n, edges, s, t):
    if s == t:
        return 0
    INF = float("inf")
    d = [INF] * n
    d[s] = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if d[u] + w < d[v]:
                d[v] = d[u] + w
                changed = True
        if not changed:
            break
    return d[t] if d[t] < INF else -1
'''
CTRL_VARIANT_DIJ_BISECT = '''import bisect

def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    best = {s: 0}
    frontier = [(0, s)]          # kept sorted; insort replaces the heap
    done = set()
    while frontier:
        du, u = frontier.pop(0)
        if u in done:
            continue
        if u == t:
            return du
        done.add(u)
        for v, w in adj[u]:
            nd = du + w
            if nd < best.get(v, float("inf")):
                best[v] = nd
                bisect.insort(frontier, (nd, v))
    return -1
'''
CTRL_OUTSIDE_PAPE = '''from collections import deque

def solve(n, edges, s, t):
    """D'Esopo-Pape label-correcting shortest paths."""
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float("inf")
    d = [INF] * n
    state = [2] * n              # 2: never queued, 1: in queue, 0: was queued and left
    d[s] = 0
    q = deque([s])
    state[s] = 1
    while q:
        u = q.popleft()
        state[u] = 0
        for v, w in adj[u]:
            if d[u] + w < d[v]:
                d[v] = d[u] + w
                if state[v] == 2:
                    q.append(v)
                elif state[v] == 0:
                    q.appendleft(v)
                state[v] = 1
    return d[t] if d[t] < INF else -1
'''
CTRL_OUTSIDE_JOHNSON = '''import heapq

def solve(n, edges, s, t):
    """Johnson's reweighting: Bellman-Ford potentials from a virtual source, then Dijkstra on reduced weights."""
    if s == t:
        return 0
    h = [0] * n                  # virtual source joined to every node with weight 0
    for _ in range(n):
        upd = False
        for u, v, w in edges:
            if h[u] + w < h[v]:
                h[v] = h[u] + w
                upd = True
        if not upd:
            break
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w + h[u] - h[v]))
    INF = float("inf")
    d = [INF] * n
    d[s] = 0
    pq = [(0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]:
            continue
        for v, w in adj[u]:
            if du + w < d[v]:
                d[v] = du + w
                heapq.heappush(pq, (d[v], v))
    return d[t] - h[s] + h[t] if d[t] < INF else -1
'''
CTRL_DEGENERATE_SCIPY = '''import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path


def solve(n, edges, s, t):
    if s == t:
        return 0
    best = {}
    for u, v, w in edges:
        if u != v and (w < best.get((u, v), float("inf"))):
            best[(u, v)] = w
    rows = [u for u, v in best]
    cols = [v for u, v in best]
    vals = [best[k] + 1e-9 for k in best]
    g = csr_matrix((vals, (rows, cols)), shape=(n, n))
    d = shortest_path(g, directed=True, indices=s)
    return int(round(d[t])) if np.isfinite(d[t]) else -1
'''
CTRL_DEGENERATE_TABLE = '''def solve(n, edges, s, t):
    key = (n, tuple(sorted(map(tuple, edges))), s, t)
    return ANSWERS.get(key, 0 if s == t else -1)


ANSWERS = {}  # memorised answers of the hidden tests
'''


# ---------------------------------------------------------------- programs
def collect_programs() -> list[dict]:
    rows = read_jsonl(inp(EN, "data/labels.jsonl"))
    code_by_sha = {r["code_sha256"]: r["code"] for r in rows if r.get("code")}
    for r in read_jsonl(inp(EN, "inputs/exp22/labels.jsonl")):
        if r.get("code"):
            code_by_sha.setdefault(r["code_sha256"], r["code"])
    progs, seen = [], set()
    for r in read_jsonl(inp(EN, "data/samples.jsonl")):
        if r.get("label") == "other" and truthy(r.get("passed")) and r["code_sha256"] not in seen:
            seen.add(r["code_sha256"])
            progs.append({"id": f"P{len(progs) + 1}", "sha": r["code_sha256"], "engine": r["engine"], "task": r["task"],
                          "arm": r["arm"], "row_source": r.get("source"), "code": code_by_sha.get(r["code_sha256"])})
    in_labels = {r["code_sha256"] for r in rows if r["label"] == "other" and truthy(r["passed"])}
    for p in progs:
        p["in_labels_jsonl"] = p["sha"] in in_labels
    return progs


# ---------------------------------------------------------------- tests
def _ref_solve(n: int, edges: list, s: int, t: int) -> int:
    import heapq
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    d = [float("inf")] * n
    d[s] = 0
    pq = [(0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]:
            continue
        for v, w in adj[u]:
            if du + w < d[v]:
                d[v] = du + w
                heapq.heappush(pq, (d[v], v))
    return d[t] if d[t] < float("inf") else -1


def stress_cases(seed: int = 7) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    big = []
    for i in range(12):
        n = 100
        m = 600
        edges = [(rng.randrange(n), rng.randrange(n), rng.randint(0, 100)) for _ in range(m)]
        big.append({"id": f"max_random_{i}", "n": n, "edges": edges, "s": rng.randrange(n), "t": rng.randrange(n)})
    adv = []
    n = 100
    adv.append({"id": "chain_reverse_order", "n": n, "edges": [(i, i + 1, 100) for i in reversed(range(n - 1))], "s": 0, "t": n - 1})
    adv.append({"id": "zero_weight_dense_cycle", "n": n,
                "edges": [(i, (i + 1) % n, 0) for i in range(n)] + [(i, (i + 7) % n, 0) for i in range(n)], "s": 3, "t": 2})
    e = [(0, i, 100) for i in range(1, n)] + [(i, i + 1, 0) for i in range(1, n - 1)]
    adv.append({"id": "star_plus_zero_chain", "n": n, "edges": e[:600], "s": 0, "t": n - 1})
    adv.append({"id": "parallel_and_self_loops", "n": 50,
                "edges": [(i, i, 0) for i in range(50)] + [(i, i + 1, w) for i in range(49) for w in (100, 50, 1)][:550],
                "s": 0, "t": 49})
    adv.append({"id": "unreachable_large", "n": n, "edges": [(i + 1, i, 1) for i in range(n - 1)], "s": 0, "t": n - 1})
    adv.append({"id": "s_equals_t_large", "n": n, "edges": [(i % n, (i * 3) % n, i % 101) for i in range(600)], "s": 5,
                "t": 5})
    lay = [(i, j, 100 - (j - i)) for i in range(0, 30) for j in range(i + 1, min(30, i + 25))][:600]
    adv.append({"id": "decreasing_shortcuts_dag", "n": 30, "edges": lay, "s": 0, "t": 29})
    adv.append({"id": "greedy_trap_grid", "n": 100,
                "edges": [(r * 10 + c, r * 10 + c + 1, 1 if r == 9 else 100) for r in range(10) for c in range(9)]
                + [(r * 10 + c, (r + 1) * 10 + c, 0 if c == 0 else 100) for r in range(9) for c in range(10)],
                "s": 0, "t": 9})
    small = []
    for i in range(300):
        n = rng.randint(1, 8)
        m = rng.randint(0, 20)
        edges = [(rng.randrange(n), rng.randrange(n), rng.randint(0, 100)) for _ in range(m)]
        small.append({"id": f"small_{i}", "n": n, "edges": edges, "s": rng.randrange(n), "t": rng.randrange(n)})
    for suite in (big, adv, small):
        for c in suite:
            c["expected"] = _ref_solve(c["n"], c["edges"], c["s"], c["t"])
    return {"max_size_random": big, "adversarial": adv, "random_small": small}


def _limits(*_: Any) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))


def run_sandbox(code: str, cases: list[dict], limits: list[float], timeout: float = 120.0) -> dict:
    job = json.dumps({"code": code, "cases": [{k: c[k] for k in ("n", "edges", "s", "t")} for c in cases],
                      "limits_s": limits})
    env = {"PATH": "/usr/bin:/bin", "HOME": str(WS), "http_proxy": "http://0.0.0.0:9", "https_proxy": "http://0.0.0.0:9",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    try:
        p = subprocess.run([sys.executable, "-I", str(WS / "src" / "sandbox_child.py")], input=job, text=True,
                           capture_output=True, timeout=timeout, preexec_fn=_limits, env=env)
        out = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {"compiled": False,
                                                                                      "error": p.stderr[-300:]}
    except subprocess.TimeoutExpired:
        out = {"compiled": False, "error": "sandbox wall-clock timeout"}
    except (json.JSONDecodeError, IndexError) as e:
        out = {"compiled": False, "error": f"bad sandbox output: {e}"}
    res = out.get("results", [])
    passed = [bool(r.get("ok")) and r.get("got") == c["expected"] for r, c in zip(res, cases)] if res else []
    return {"compiled": out.get("compiled", False), "error": out.get("error"), "n": len(cases),
            "n_pass": sum(passed), "all_pass": bool(res) and len(passed) == len(cases) and all(passed),
            "max_secs": max((r.get("secs", 0) for r in res), default=None),
            "failures": [{"case": c.get("id"), "got": r.get("got"), "expected": c["expected"], "error": r.get("error")}
                         for r, c, ok in zip(res, cases, passed) if not ok][:5]}


def test_all(codes: dict[str, str]) -> dict[str, Any]:
    tests = read_json(inp(EN, f"{SUITE}/tests.json"))
    lim = read_json(inp(EN, f"{SUITE}/limits.json"))
    slow = lim["slowest_reference_s"]
    hidden_limits = [max(1.0, 10 * slow.get(c["id"], 0.1)) for c in tests]
    st = stress_cases()
    refs = {p.stem: p.read_text() for p in sorted(inp(EN, f"{SUITE}/references").glob("*.py"))}
    # the run's stress limit: 10x the fastest catalogue reference on each case, at least 1 s
    fastest = {}
    for name, cases in st.items():
        times = [(rname, run_sandbox(rcode, cases, [10.0] * len(cases), timeout=300)) for rname, rcode in refs.items()]
        fastest[name] = {rn: r["max_secs"] for rn, r in times}
        fastest[name + "_ref_all_pass"] = {rn: r["all_pass"] for rn, r in times}
    out = {}
    for pid, code in codes.items():
        h = run_sandbox(code, tests, hidden_limits)
        rec = {"hidden": h}
        for name, cases in st.items():
            fmin = min((v for v in fastest[name].values() if v is not None), default=0.1)
            rec[name] = run_sandbox(code, cases, [max(1.0, 10 * fmin)] * len(cases), timeout=600)
            rec[name]["limit_s"] = max(1.0, 10 * fmin)
        out[pid] = rec
        logger.info(f"tests {pid}: hidden {h['n_pass']}/{h['n']}; " + "; ".join(
            f"{k} {rec[k]['n_pass']}/{rec[k]['n']}" for k in st))
    return {"results": out, "reference_max_secs": fastest, "n_hidden": len(tests),
            "stress_sizes": {k: len(v) for k, v in st.items()}}


# ---------------------------------------------------------------- nearest known (AST shingles, Zhang-Shasha)
def _seq(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Name, ast.arg)):
            out.append("ID")
        elif isinstance(node, ast.Attribute):
            out.append(f"ATTR:{node.attr}")
        elif isinstance(node, ast.Constant):
            out.append(f"CONST:{type(node.value).__name__}")
        elif isinstance(node, (ast.Load, ast.Store, ast.Del)):
            continue
        else:
            out.append(type(node).__name__)
    return out


def shingles(code: str, k: int = 4) -> set:
    s = _seq(code)
    return {tuple(s[i:i + k]) for i in range(max(0, len(s) - k + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _zss_tree(code: str):
    from zss import Node

    def conv(node: ast.AST) -> Node:
        if isinstance(node, (ast.Name, ast.arg)):
            lab = "ID"
        elif isinstance(node, ast.Attribute):
            lab = f"ATTR:{node.attr}"
        elif isinstance(node, ast.Constant):
            lab = f"CONST:{type(node.value).__name__}"
        else:
            lab = type(node).__name__
        n = Node(lab)
        for ch in ast.iter_child_nodes(node):
            if not isinstance(ch, (ast.Load, ast.Store, ast.Del)):
                n.addkid(conv(ch))
        return n

    root = conv(ast.parse(code))
    size = sum(1 for _ in _iter(root))
    return root, size


def _iter(n):
    yield n
    for c in n.children:
        yield from _iter(c)


def zss_norm(pair: tuple[str, str]) -> float:
    from zss import simple_distance
    a, na = _zss_tree(pair[0])
    b, nb = _zss_tree(pair[1])
    return simple_distance(a, b) / max(na, nb)


def known_pool() -> list[dict]:
    pool = []
    for p in sorted(inp(EN, f"{SUITE}/references").glob("*.py")):
        pool.append({"id": f"ref:{p.stem}", "source": "bench reference (catalogue)", "label": p.stem, "code": p.read_text()})
    for r in read_jsonl(inp(EN, "vendor/exp22/inputs/dep_art_j3Rm/known_subset.jsonl")):
        if r.get("task") == "T2":
            pool.append({"id": f"known:{sha256_text(r['code'])[:10]}", "source": f"known-solution subset ({r['source']})",
                         "label": r.get("mode_hint"), "code": r["code"]})
    seen = set()
    for r in read_jsonl(inp(EN, "data/labels.jsonl")):
        if r["task"] == "T2" and truthy(r["passed"]) and r["label"] not in ("other", "invalid") and r.get("code") \
                and r["code_sha256"] not in seen:
            seen.add(r["code_sha256"])
            pool.append({"id": f"run:{r['code_sha256'][:10]}", "source": "correct catalogue-labelled run program",
                         "label": r["label"], "code": r["code"]})
    return pool


def nearest(progs: dict[str, str], pool: list[dict], top_j: int = 12, workers: int = 8) -> dict[str, list[dict]]:
    sh = {p["id"]: shingles(p["code"]) for p in pool}
    out = {}
    pairs, meta = [], []
    for pid, code in progs.items():
        s = shingles(code)
        js = sorted(((jaccard(s, sh[p["id"]]), p) for p in pool if p["code"].strip() != code.strip()),
                    key=lambda x: -x[0])[:top_j]
        for j, p in js:
            pairs.append((code, p["code"]))
            meta.append((pid, j, p))
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        dists = list(ex.map(zss_norm, pairs, chunksize=2))
    for (pid, j, p), d in zip(meta, dists):
        out.setdefault(pid, []).append({"id": p["id"], "source": p["source"], "label": p["label"], "jaccard": j,
                                        "zss_norm": d})
    for pid in out:
        out[pid].sort(key=lambda x: (x["zss_norm"], -x["jaccard"]))
    return out


# ---------------------------------------------------------------- judges
def judge_prompt(item: dict, near: list[dict], pool_by_id: dict[str, dict]) -> list[dict]:
    ex = "\n\n".join(f"[{i + 1}] id={n['id']} ({n['source']}; Jaccard {n['jaccard']:.2f}, tree distance "
                     f"{n['zss_norm']:.2f})\n```python\n{pool_by_id[n['id']]['code'][:1800]}\n```"
                     for i, n in enumerate(near[:3]))
    sys_msg = ("You are an expert in algorithms and code review. You classify a Python program's algorithmic method. "
               "Answer with JSON only.")
    user = f"""TASK THE PROGRAM SOLVES
{SPEC.read_text().strip()}

CATALOGUE OF ALGORITHMS FOR THIS TASK
{"; ".join(CATALOGUE)}

PROGRAM TO CLASSIFY
```python
{item['code']}
```

SANDBOXED TEST OUTCOMES
{item['test_text']}

THREE NEAREST KNOWN SOLUTIONS (examples, not exhaustive; they do NOT define what is known)
{ex}

QUESTION
Decide whether the program's method is a known technique anywhere (textbooks, the algorithms literature, competitive
programming, everyday practice) and name it. Then give exactly one class:
- LABELLER_MISS: a catalogue algorithm implemented in a standard, recognisable form that a labeller should have named.
- CATALOGUE_VARIANT: a catalogue algorithm, but restructured, simplified or with a changed data structure.
- KNOWN_OUTSIDE_CATALOGUE: a known technique that is not in the catalogue (name it).
- DEGENERATE: the core of the task is done by a library routine that already solves it, or the program has no
  algorithm of its own (for example it returns memorised answers).
- NOVEL: its method is not a known technique at all; use this only if you cannot name any known technique.

Return JSON: {{"class": "<NOVEL | KNOWN_OUTSIDE_CATALOGUE | CATALOGUE_VARIANT | DEGENERATE | LABELLER_MISS>",
"nearest_known_algorithm": "<name>", "rationale": "<at most 40 words>"}}"""
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}]


def _parse(text: str) -> dict:
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    c = str(d.get("class", "")).strip().upper().replace(" ", "_")
    if c not in CLASSES:
        c = next((k for k in CLASSES if k in (text or "").upper()), "UNPARSED")
    return {"class": c, "nearest_known_algorithm": d.get("nearest_known_algorithm", ""),
            "rationale": str(d.get("rationale", ""))[:300]}


class Budget:
    def __init__(self, cap: float):
        self.cap, self.spent, self.stop, self.reason = cap, 0.0, False, None


async def _call(session: aiohttp.ClientSession, sem: asyncio.Semaphore, bud: Budget, model: str, msgs: list[dict],
                key: str, cache: dict) -> dict:
    if key in cache:
        return cache[key]
    async with sem:
        if bud.stop:
            return {"error": "stopped: " + str(bud.reason)}
        if bud.spent >= bud.cap - 0.02:
            bud.stop, bud.reason = True, "artifact cap reached"
            return {"error": "stopped: cap"}
        body = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": 400, "usage": {"include": True}}
        for attempt in range(3):
            try:
                async with session.post(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions", json=body,
                                        timeout=aiohttp.ClientTimeout(total=120)) as r:
                    txt = await r.text()
                    if r.status == 403 and "AI Inventor per-run OpenRouter budget" in txt:
                        bud.stop, bud.reason = True, "403 per-run budget"
                        return {"error": "403 budget"}
                    if r.status != 200:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    cost = float((d.get("usage") or {}).get("cost") or 0.0)
                    bud.spent += cost
                    content = d["choices"][0]["message"]["content"]
                    res = {"model": model, "content": content, "cost": cost, "parsed": _parse(content),
                           "usage": d.get("usage")}
                    cache[key] = res
                    with CACHE.open("a") as f:
                        f.write(json.dumps({"key": key, **res}) + "\n")
                    logger.debug(f"judge {model} {key[:16]} -> {res['parsed']['class']} (${cost:.5f})")
                    return res
            except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, json.JSONDecodeError) as e:
                logger.warning(f"judge call failed ({type(e).__name__}); retry {attempt + 1}")
                await asyncio.sleep(2 * (attempt + 1))
        return {"error": "failed after retries"}


async def run_judges(items: list[dict], prompts: dict[str, list[dict]], calls: int = 3, seed: int = 20261022,
                     models: list[str] | None = None) -> dict:
    cache = {}
    if CACHE.exists():
        for l in CACHE.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                cache[r["key"]] = r
    bud = Budget(BUDGET_USD)
    jobs = [(m, it["blind_id"], c) for m in (models or JUDGES) for it in items for c in range(calls)]
    random.Random(seed).shuffle(jobs)
    sem = asyncio.Semaphore(8)
    hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    async with aiohttp.ClientSession(headers=hdr) as s:
        res = await asyncio.gather(*[_call(s, sem, bud, m, prompts[b], sha256_text(f"{m}|{b}|{c}|" + json.dumps(prompts[b])),
                                           cache) for m, b, c in jobs], return_exceptions=True)
    out: dict = {}
    for (m, b, c), r in zip(jobs, res):
        if isinstance(r, BaseException):
            r = {"error": repr(r)}
        out.setdefault(m, {}).setdefault(b, []).append(r)
    return {"calls": out, "spent_usd_this_run": bud.spent, "stopped": bud.stop, "stop_reason": bud.reason,
            "cached_total_usd": sum(float(v.get("cost") or 0) for v in cache.values())}


def majority(rs: list[dict]) -> str:
    cl = [r["parsed"]["class"] for r in rs if "parsed" in r]
    if not cl:
        return "NO_RESPONSE"
    top, k = Counter(cl).most_common(1)[0]
    return top if k >= 2 or len(cl) == 1 else "NO_MAJORITY"


MERGE = {"LABELLER_MISS": "CATALOGUE", "CATALOGUE_VARIANT": "CATALOGUE"}

MANUAL = {  # the executor's full read of each program (written after reading the code and its test results)
    "a35f278b1ca9": ("CATALOGUE_VARIANT", "Dijkstra with an array scan for the minimum instead of a heap (the O(n^2) "
                                          "textbook form); the runtime labeller expects a heap, hence 'other'."),
    "d64ff1c41006": ("CATALOGUE_VARIANT", "The same O(n^2) array-scan Dijkstra as the bf16 program, written by the W8A8 "
                                          "engine in iteration 4; catalogue Dijkstra without a priority queue."),
    "8a88e7df0881": ("CATALOGUE_VARIANT", "Commented as Floyd-Warshall but it is Bellman-Ford: n rounds of relaxing every "
                                          "edge from reached nodes in node order, with no early exit."),
}


def adjudicate(log_dir=None) -> dict[str, Any]:
    t0 = time.time()
    progs = collect_programs()
    pool = known_pool()
    pool_by_id = {p["id"]: p for p in pool}
    refs = {p.stem: p.read_text() for p in sorted(inp(EN, f"{SUITE}/references").glob("*.py"))}
    tests = read_json(inp(EN, f"{SUITE}/tests.json"))
    table = "ANSWERS = " + repr({(c["n"], tuple(sorted(map(tuple, c["edges"]))), c["s"], c["t"]): c["expected"]
                                 for c in tests})
    controls = [
        {"cid": "C01", "truth": "LABELLER_MISS", "kind": "catalogue reference", "code": refs["dijkstra_lazy"]},
        {"cid": "C02", "truth": "LABELLER_MISS", "kind": "catalogue reference", "code": refs["bellman_ford"]},
        {"cid": "C03", "truth": "LABELLER_MISS", "kind": "catalogue reference", "code": refs["spfa"]},
        {"cid": "C04", "truth": "LABELLER_MISS", "kind": "catalogue reference", "code": refs["floyd_inf"]},
        {"cid": "C05", "truth": "CATALOGUE_VARIANT", "kind": "catalogue variant", "code": CTRL_VARIANT_BF_EARLY},
        {"cid": "C06", "truth": "CATALOGUE_VARIANT", "kind": "catalogue variant", "code": CTRL_VARIANT_DIJ_BISECT},
        {"cid": "C07", "truth": "KNOWN_OUTSIDE_CATALOGUE", "kind": "known outside the catalogue (D'Esopo-Pape)",
         "code": CTRL_OUTSIDE_PAPE},
        {"cid": "C08", "truth": "KNOWN_OUTSIDE_CATALOGUE", "kind": "known outside the catalogue (Johnson reweighting)",
         "code": CTRL_OUTSIDE_JOHNSON},
        {"cid": "C09", "truth": "DEGENERATE", "kind": "library call (scipy csgraph)", "code": CTRL_DEGENERATE_SCIPY},
        {"cid": "C10", "truth": "DEGENERATE", "kind": "memorised answers",
         "code": CTRL_DEGENERATE_TABLE.replace("ANSWERS = {}", table)},
    ]
    codes = {p["id"]: p["code"] for p in progs} | {c["cid"]: c["code"] for c in controls}
    tst = test_all(codes)
    near = nearest({p["id"]: p["code"] for p in progs} | {c["cid"]: c["code"] for c in controls
                                                         if c["cid"] not in ("C10",)}, pool)
    near["C10"] = near.get("C10") or near["C09"]

    def ttext(pid: str) -> str:
        r = tst["results"][pid]
        return "; ".join(f"{k}: {r[k]['n_pass']}/{r[k]['n']} passed" for k in ("hidden", "max_size_random",
                                                                             "adversarial", "random_small"))

    items = [{"blind_id": f"I{i:02d}", "ref": x} for i, x in enumerate([p["id"] for p in progs] + [c["cid"] for c in controls])]
    random.Random(20261022).shuffle(items)
    for i, it in enumerate(items):
        it["blind_id"] = f"I{i + 1:02d}"
    by_ref = {p["id"]: p for p in progs} | {c["cid"]: c for c in controls}
    prompts = {}
    for it in items:
        x = by_ref[it["ref"]]
        prompts[it["blind_id"]] = judge_prompt({"code": x["code"][:6000], "test_text": ttext(it["ref"])},
                                               near[it["ref"]], pool_by_id)
    write_json(AUDIT / "judge_protocol.json", {"frozen_before_calls_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                               "judges": JUDGES, "replacement_judges_if_a_gate_fails": REPLACEMENTS,
                                               "classes": CLASSES, "calls_per_item": 3,
                                               "superseded_pass": "a first pass at 13:35Z used an adversarial stress case "
                                                                  "with node ids >= n (s_equals_t_large); it was fixed "
                                                                  "and every judge re-run; the superseded responses stay "
                                                                  "in judge_cache.jsonl and count toward spend",
                                               "temperature": 0, "shuffle_seed": 20261022, "budget_usd": BUDGET_USD,
                                               "gate": "a judge counts only if its majority class is right on >= 9 of 10 "
                                                       "controls, with LABELLER_MISS and CATALOGUE_VARIANT merged "
                                                       "(both mean 'a catalogue algorithm'); exact-class accuracy is "
                                                       "reported beside it",
                                               "prompt_sha256": {b: sha256_text(json.dumps(p)) for b, p in prompts.items()},
                                               "blind_map_sha256": sha256_text(json.dumps(items))})
    jr = asyncio.run(run_judges(items, prompts, models=JUDGES))

    def gate_of(m: str, maj_m: dict) -> dict:
        exact = sum(maj_m[c["cid"]] == c["truth"] for c in controls)
        merged = sum(MERGE.get(maj_m[c["cid"]], maj_m[c["cid"]]) == MERGE.get(c["truth"], c["truth"]) for c in controls)
        return {"exact_correct": exact, "merged_correct": merged, "passed": merged >= 9}

    maj = {m: {it["ref"]: majority(jr["calls"].get(m, {}).get(it["blind_id"], [])) for it in items} for m in JUDGES}
    gate = {m: gate_of(m, maj[m]) for m in JUDGES}
    amendments = []
    if not all(g["passed"] for g in gate.values()) and not jr["stopped"]:
        failed = [m for m, g in gate.items() if not g["passed"]]
        amendments.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "amendment": f"primary judge(s) {failed} failed the 9-of-10 gate; the declared replacement "
                                        f"family {REPLACEMENTS} is run on the same blind items, prompts and gate"})
        write_json(AUDIT / "judge_protocol_amendments.json", amendments)
        jr2 = asyncio.run(run_judges(items, prompts, models=REPLACEMENTS))
        for m in REPLACEMENTS:
            jr["calls"][m] = jr2["calls"].get(m, {})
            maj[m] = {it["ref"]: majority(jr2["calls"].get(m, {}).get(it["blind_id"], [])) for it in items}
            gate[m] = gate_of(m, maj[m])
        jr["spent_usd_this_run"] += jr2["spent_usd_this_run"]
        jr["cached_total_usd"] = jr2["cached_total_usd"]
        jr["stopped"], jr["stop_reason"] = jr2["stopped"], jr2["stop_reason"]
    gated = [m for m in list(JUDGES) + [r for r in REPLACEMENTS if r in maj] if gate[m]["passed"]][:2]
    refs_all = [it["ref"] for it in items]

    def kap(a: str, b: str, merged: bool) -> float | None:
        f = (lambda x: MERGE.get(x, x)) if merged else (lambda x: x)
        return cohen_kappa([f(maj[a][r]) for r in refs_all], [f(maj[b][r]) for r in refs_all])

    kappa_all = kap(gated[0], gated[1], False) if len(gated) == 2 else None
    kappa_merged = kap(gated[0], gated[1], True) if len(gated) == 2 else None
    kappa_primary = {"exact": kap(JUDGES[0], JUDGES[1], False), "merged": kap(JUDGES[0], JUDGES[1], True)}
    final = []
    for p in progs:
        man, why = MANUAL.get(p["sha"][:12], ("UNREAD", ""))
        both_novel = len(gated) == 2 and all(maj[m][p["id"]] == "NOVEL" for m in gated)
        cls = "NOVEL" if (both_novel and man == "NOVEL") else man
        final.append({"id": p["id"], "sha12": p["sha"][:12], "engine": p["engine"], "arm": p["arm"],
                      "row_source": p["row_source"], "in_labels_jsonl": p["in_labels_jsonl"],
                      "judge_majority": {m: maj[m][p["id"]] for m in maj}, "manual_class": man,
                      "manual_read": why, "final_class": cls, "tests": tst["results"][p["id"]],
                      "nearest3": near[p["id"]][:3]})
    ctrl_rows = [{"cid": c["cid"], "kind": c["kind"], "truth": c["truth"], "tests": tst["results"][c["cid"]],
                  "judge_majority": {m: maj[m][c["cid"]] for m in maj}} for c in controls]
    out = {"n_programs": len(progs), "programs": final, "controls": ctrl_rows, "gate": gate,
           "kappa_exact_classes": kappa_all, "kappa_merged_classes": kappa_merged, "kappa_primary_pair": kappa_primary,
           "gated_judges": gated, "protocol_amendments": amendments,
           "n_novel_final": sum(f["final_class"] == "NOVEL" for f in final),
           "judges": list(maj), "spend": {k: jr[k] for k in ("spent_usd_this_run", "stopped", "stop_reason",
                                                         "cached_total_usd")},
           "pool": {"n": len(pool), "by_source": dict(Counter(p["source"].split(" (")[0] for p in pool))},
           "reference_max_secs": tst["reference_max_secs"], "stress_sizes": tst["stress_sizes"],
           "blind_items": items, "secs": time.time() - t0,
           "corpus_note": "The 18,237-solution corpus of art_j3Rm_lr2nzR6 is not in a declared tree; a 406-solution "
                          "subset of it (34 shortest-path solutions) is vendored inside art_lpQalcAXMGr1 and is used "
                          "with the bench references and the run's correct catalogue-labelled programs."}
    write_json(AUDIT / "judge_runs_summary.json", {"maj": maj, "gate": gate, "spend": out["spend"],
                                                   "calls": {m: {b: [{"class": r.get("parsed", {}).get("class"),
                                                                      "cost": r.get("cost"), "error": r.get("error")}
                                                                     for r in rs] for b, rs in v.items()}
                                                             for m, v in jr["calls"].items()}})
    return out
