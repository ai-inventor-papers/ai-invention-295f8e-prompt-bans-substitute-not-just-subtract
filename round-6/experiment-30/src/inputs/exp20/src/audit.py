#!/usr/bin/env python3
"""STEP 12 - novelty audit of every correct 'other' program from every arm (C3c), plus dependency usage.

12.1 pool = correct programs labelled 'other' (smoke slots excluded), re-labelled through the frozen labeller and run
     on 3 extra sandboxed stress tests (random inputs at the upper end of the spec's sizes, checked against a reference
     solver / validity checker); failures leave the audit as 'incorrect under stress'.
12.2 judge controls first (exp18's six controls); a judge failing >= 2 controls is replaced.
12.3 two blind judges from different families (exp18 ids: google/gemini-2.5-flash-lite, openai/gpt-4.1-mini),
     temperature 0, JSON; input = task spec, catalogue, scrubbed program, nearest known solutions; no arm information;
     disagreements resolved by a third family (deepseek/deepseek-chat-v3.1, exp9's tie-break model).
12.4 known-solution index rebuilt from the dataset dependency with exp18's builder (counts must equal exp18's
     known_solutions_summary.json) and extended to T05 (two sum); nearest known solutions by AST-shingle Jaccard.
12.5 counts per arm and pooled, rule-of-three bound; claim only at 0 confirmed (judge resolution AND manual pass).
12.6 spend: usage.cost running total, GET <base>/key before the batch, stop the batch at the first budget 403.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import random
import re
import subprocess
import sys
import tokenize
from collections import Counter, defaultdict
from typing import Any

from loguru import logger

from cfg import (AUDIT_CAP_USD, AUDIT_DIR, BENCH, BUDGET_MSG, CONTROL_CAP_USD, DATA_DIR, DEFAULT, DEP_DATASET, E11,
                 E18, RESULTS_DIR, SUITE, append_jsonl, read_json, read_jsonl, setup_logging, sha256_text, utc_now,
                 write_json, write_jsonl)

for p in (str(SUITE), str(E11)):
    if p not in sys.path:
        sys.path.insert(0, p)

JUDGE_A = "google/gemini-2.5-flash-lite"
JUDGE_B = "openai/gpt-4.1-mini"
TIEBREAK = "deepseek/deepseek-chat-v3.1"
KNOWN = DATA_DIR / "known_solutions.jsonl"
LLM_CACHE = DATA_DIR / "llm_cache_audit.jsonl"
COSTS = RESULTS_DIR / "openrouter_cost_audit.json"
BENCH_DIRS = {"T03": "T03_kth_smallest", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
              "T10": "T10_connected_components", "T04": "T04_substring_search"}  # T04: judge controls only
AUDIT_CLASSES = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
CLASS_DEFS = (
    "LABELLER MISS = the program implements a catalogue algorithm of this task in substance and should have carried "
    "its label; CATALOGUE VARIANT = it implements a known algorithm (catalogue, extended catalogue, or any named "
    "textbook or published method), possibly with minor changes, hybrids or a different but equivalent data "
    "structure; DEGENERATE = it passes by hard-coding, test-specific shortcuts, library calls that bypass the "
    "algorithm, or brute force that only passes because inputs are small; NOVEL ALGORITHM = none of the above, and "
    "the judge can state the mechanism and why no known algorithm matches.")


# ------------------------------------------------------------------------------------------------ stress tests
STRESS_RUNNER = r'''
import json, sys
job = json.loads(sys.stdin.read())
ns = {"__name__": "candidate"}
out = {"outputs": [], "error": None}
try:
    exec(compile(job["code"], "candidate.py", "exec"), ns)
    f = ns["solve"]
    for kw in job["cases"]:
        try:
            r = f(**kw)
            if isinstance(r, tuple):
                r = list(r)
            if isinstance(r, list):
                r = [list(x) if isinstance(x, tuple) else x for x in r]
            out["outputs"].append({"ok": True, "value": r})
        except Exception as e:
            out["outputs"].append({"ok": False, "error": repr(e)[:200]})
except Exception as e:
    out["error"] = repr(e)[:200]
print(json.dumps(out))
'''


def _sandbox_python() -> str:
    for cand in (os.environ.get("SANDBOX_PYTHON"), "/usr/local/bin/python3.12", "/usr/bin/python3.12"):
        if cand and os.path.exists(cand):
            return cand
    return sys.executable


def gen_case(task: str, rng: random.Random, frac: float) -> tuple[dict[str, Any], Any]:
    if task == "T03":
        n = max(1, int(2000 * frac))
        nums = [rng.randint(-10000, 10000) for _ in range(n)]
        k = rng.randint(1, n)
        return {"nums": nums, "k": k}, sorted(nums)[k - 1]
    if task == "T05":
        n = max(2, int(2000 * frac))
        while True:
            vals = rng.sample(range(-10 ** 9, 10 ** 9), n)
            i, j = sorted(rng.sample(range(n), 2))
            target = vals[i] + vals[j]
            seen, cnt = {}, 0
            for idx, v in enumerate(vals):
                if target - v in seen:
                    cnt += 1
                seen[v] = idx
            if cnt == 1:
                return {"nums": vals, "target": target}, [i, j]
    if task == "T06":
        n = max(2, int(10000 * frac))
        d = rng.randint(1, n)
        c = rng.choice([2, 3, 5])
        others = rng.sample([x for x in range(1, n + 1) if x != d], n + 1 - c)
        nums = others + [d] * c
        rng.shuffle(nums)
        return {"nums": nums}, d
    if task == "T10":
        n = max(1, int(300 * frac))
        m = min(int(1500 * frac), n * (n - 1) // 2)
        es = set()
        while len(es) < m:
            u, v = rng.randrange(n), rng.randrange(n)
            if u != v and (u, v) not in es and (v, u) not in es:
                es.add((u, v))
        par = list(range(n))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        comps = n
        for u, v in es:
            a, b = find(u), find(v)
            if a != b:
                par[a] = b
                comps -= 1
        return {"n": n, "edges": [list(e) for e in es]}, comps
    if task == "T1":
        R, C = max(1, int(30 * frac)), max(1, int(30 * frac))
        dens = rng.choice([0.2, 0.3, 0.35])
        g = ["".join("#" if rng.random() < dens else "." for _ in range(C)) for _ in range(R)]
        free = [(r, c) for r in range(R) for c in range(C) if g[r][c] == "."]
        if len(free) < 2:
            g = ["." * C for _ in range(R)]
            free = [(r, c) for r in range(R) for c in range(C)]
        s, t = rng.sample(free, 2) if len(free) >= 2 else (free[0], free[0])
        from collections import deque

        seen = {s}
        q = deque([s])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < R and 0 <= nc < C and g[nr][nc] == "." and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return {"grid": g, "start": list(s), "goal": list(t)}, (t in seen)
    if task == "T2":
        n = max(1, int(100 * frac))
        m = int(600 * frac)
        edges = [[rng.randrange(n), rng.randrange(n), rng.randint(0, 100)] for _ in range(m)]
        s, t = rng.randrange(n), rng.randrange(n)
        import heapq

        dist = {s: 0}
        pq = [(0, s)]
        adj = defaultdict(list)
        for u, v, w in edges:
            adj[u].append((v, w))
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1 << 60):
                continue
            for v, w in adj[u]:
                if d + w < dist.get(v, 1 << 60):
                    dist[v] = d + w
                    heapq.heappush(pq, (d + w, v))
        return {"n": n, "edges": edges, "s": s, "t": t}, (0 if s == t else dist.get(t, -1))
    raise ValueError(task)


def check_case(task: str, kw: dict[str, Any], exp: Any, out: Any) -> bool:
    if task == "T05":
        return isinstance(out, list) and len(out) == 2 and sorted(out) == sorted(exp)
    if task == "T1":
        g, s, t = kw["grid"], tuple(kw["start"]), tuple(kw["goal"])
        if not exp:
            return out == []
        if not isinstance(out, list) or not out:
            return False
        try:
            path = [tuple(x) for x in out]
        except TypeError:
            return False
        if path[0] != s or path[-1] != t:
            return False
        for (r, c) in path:
            if not (0 <= r < len(g) and 0 <= c < len(g[0])) or g[r][c] != ".":
                return False
        return all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))
    return out == exp


def stress_test(task: str, code: str, seed: int, n_tests: int = 3, timeout: float = 30.0) -> dict[str, Any]:
    rng = random.Random(seed)
    cases = [gen_case(task, rng, f) for f in (0.5, 1.0, 1.0)[:n_tests]]
    job = {"code": code, "cases": [c[0] for c in cases]}
    try:
        p = subprocess.run([_sandbox_python(), "-I", "-S", "-c", STRESS_RUNNER], input=json.dumps(job),
                           capture_output=True, text=True, timeout=timeout)
        res = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {"error": p.stderr[-200:]}
    except subprocess.TimeoutExpired:
        return {"passed": False, "reason": "timeout", "n_pass": 0}
    except (json.JSONDecodeError, IndexError) as e:
        return {"passed": False, "reason": f"runner error {e}", "n_pass": 0}
    if res.get("error"):
        return {"passed": False, "reason": res["error"], "n_pass": 0}
    ok = [o.get("ok") and check_case(task, kw, exp, o.get("value")) for (kw, exp), o in zip(cases, res["outputs"])]
    return {"passed": all(ok) and len(ok) == len(cases), "n_pass": int(sum(ok)), "n_tests": len(cases)}


# ------------------------------------------------------------------------------------------------ index (12.4)
BENCH_PREFIX = {"T01": "T1", "T02": "T2", "T03": "T03", "T04": "T04", "T06": "T06", "T10": "T10"}
LEETCODE_TASK = {"215": "T03", "28": "T04", "287": "T06", "547": "T10", "323": "T10", "1971": "T10", "743": "T2",
                 "1091": "T1", "1631": "T2", "1514": "T2"}
KEYWORDS = {"T1": ["bfs", "breadth", "dfs", "depth_first", "a_star", "astar", "bidirectional", "iterative_deepening",
                   "maze", "grid", "jump_point", "greedy_best"],
            "T2": ["dijkstra", "bellman", "spfa", "floyd", "dial", "shortest_path", "johnson"],
            "T03": ["quickselect", "quick_select", "kth", "median_of_medians", "heap", "select", "nth"],
            "T04": ["kmp", "knuth", "rabin", "z_function", "z_algorithm", "boyer", "horspool", "string_match",
                    "substring", "sunday"],
            "T06": ["duplicate", "tortoise", "floyd", "cycle"],
            "T10": ["union_find", "disjoint", "connected_component", "dfs", "bfs"]}


def _task_for_thealgorithms(path: str, bench_task: str | None, prefix: dict[str, str]) -> str | None:
    if bench_task and bench_task not in ("None", ""):
        return prefix.get(bench_task[:3])
    p = path.lower()
    for t, kws in KEYWORDS.items():
        if any(k in p for k in kws):
            return t
    return None


def build_known_solutions() -> dict[str, Any]:
    """exp18 audit.build_known_solutions, verbatim mapping (pass 1), then the T05 extension (pass 2: LeetCode 1,
    Mercury two-sum rows, KodCode/XLCoST rows whose named bench tasks include T05, TheAlgorithms paths naming two sum).
    Streams the dependency's full_data_out.json with ijson (never loaded whole)."""
    import ijson

    src = DEP_DATASET / "full_data_out.json"
    out, counts, t05 = [], Counter(), Counter()
    with src.open("rb") as f:
        for ds in ijson.items(f, "datasets.item"):
            name = ds["dataset"]
            if name not in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic",
                            "xlcost_python"):
                continue
            for ex in ds["examples"]:
                task, code, hint, ext = None, None, None, False
                if name in ("leetcodedataset", "mercury"):
                    qid = str(ex.get("metadata_question_id"))
                    bt = str(ex.get("metadata_bench_task") or "")
                    task = BENCH_PREFIX.get(bt[:3]) or LEETCODE_TASK.get(qid)
                    code = ex.get("output")
                    hint = ex.get("metadata_slug") or ex.get("metadata_task_slug")
                    if task is None and (bt.startswith("T05") or qid == "1"):
                        task, ext = "T05", True
                elif name == "thealgorithms_python":
                    task = _task_for_thealgorithms(str(ex.get("metadata_path")), str(ex.get("metadata_bench_task")),
                                                   BENCH_PREFIX)
                    code = ex.get("input")
                    hint = f"{ex.get('output')} ({ex.get('metadata_bench_mode')})"
                    if task is None and ("two_sum" in str(ex.get("metadata_path")).lower() or
                                         str(ex.get("metadata_bench_task") or "").startswith("T05")):
                        task, ext = "T05", True
                else:
                    named = ex.get("metadata_bench_tasks_named") or "[]"
                    try:
                        lst = json.loads(named.replace("'", '"')) if isinstance(named, str) else named
                    except json.JSONDecodeError:
                        lst = []
                    tl = [BENCH_PREFIX.get(str(x)[:3]) for x in lst]
                    tl = [x for x in tl if x]
                    code = ex.get("output")
                    hint = ex.get("metadata_named_algorithms")
                    if tl:
                        task = tl[0]
                    elif any(str(x).startswith("T05") for x in lst):
                        task, ext = "T05", True
                    else:
                        continue
                if task and code:
                    out.append({"source": name, "task": task, "mode_hint": str(hint)[:120], "code": code[:20000],
                                "t05_extension": ext})
                    (t05 if ext else counts)[(name, task)] += 1
    write_jsonl(KNOWN, out)
    ref = read_json(E18 / "results" / "known_solutions_summary.json")
    mine = {f"{a}|{b}": k for (a, b), k in sorted(counts.items())}
    summ = {"n_exp18_mapping": sum(counts.values()), "by_source_task": mine,
            "matches_exp18_summary": mine == ref["by_source_task"], "exp18_n": ref["n"],
            "t05_extension": {f"{a}|{b}": k for (a, b), k in sorted(t05.items())},
            "n_t05": sum(t05.values()), "utc": utc_now()}
    write_json(RESULTS_DIR / "known_solutions_summary.json", summ)
    logger.info(f"known-solution index: {summ['n_exp18_mapping']} (exp18 {ref['n']}, match "
                f"{summ['matches_exp18_summary']}) + {summ['n_t05']} T05 rows")
    return summ


def nearest_known(code: str, pool: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    from analysis import shingles

    a = shingles(code)
    sc = []
    for p in pool:
        b = p.get("_sh")
        if b is None:
            b = p["_sh"] = shingles(p["code"])
        u = len(a | b)
        sc.append((len(a & b) / u if u else 0.0, p))
    sc.sort(key=lambda x: -x[0])
    return [{"source": p["source"], "mode_hint": p.get("mode_hint"), "similarity": round(s, 3),
             "code": p["code"][:1500]} for s, p in sc[:k]]


# ------------------------------------------------------------------------------------------------ prompts
def description(task: str) -> str:
    if task in BENCH_DIRS:
        return json.loads((BENCH / BENCH_DIRS[task] / "spec.json").read_text())["spec_text"]
    return (SUITE / "tasks" / {"T1": "t1_grid", "T2": "t2_wsp"}[task] / "spec.txt").read_text()


def catalogue_text(task: str) -> str:
    if task in BENCH_DIRS:
        spec = json.loads((BENCH / BENCH_DIRS[task] / "spec.json").read_text())
        return "\n".join(f"- {c['mode']}: {c['display_name']} - {c['mechanism']}" for c in spec["catalogue"])
    import common as suite_common

    st = {"T1": "t1", "T2": "t2"}[task]
    return "\n".join(f"- {m}: {suite_common.MODE_DEFINITIONS[st][m]}" for m in suite_common.MODES[st]) + \
        "\nExtended catalogue (known, not labels): " + ", ".join(suite_common.EXTENDED_CATALOGUE[st])


ALIAS_RE = re.compile(r"(bfs|dfs|breadth|depth|dijkstra|bellman|spfa|floyd|warshall|dial|astar|a_star|heuristic|"
                      r"bidirectional|iddfs|deepening|quickselect|select|heap|kmp|knuth|rabin|karp|union|find|"
                      r"disjoint|dsu|tortoise|hare|cycle|binary_search|bisect|counting|sort|novel|new_|invent|hash|"
                      r"two_?pointer|brute)", re.I)


def scrub(task: str, code: str) -> str:
    """exp18 scrub: bench tasks use the bench scrubber; path tasks drop comments and rename identifiers that contain
    an algorithm alias (API names untouched)."""
    if task in BENCH_DIRS:
        try:
            from bench.common.scrub import scrub_code

            return scrub_code(code)[0]
        except Exception:  # noqa: BLE001
            return code
    import ast as _ast

    try:
        tree = _ast.parse(code)
    except SyntaxError:
        return code
    params, defined = set(), set()
    for n in _ast.walk(tree):
        if isinstance(n, _ast.FunctionDef):
            defined.add(n.name)
            defined.update(a.arg for a in n.args.args)
            if n.name == "solve":
                params = {a.arg for a in n.args.args}
        elif isinstance(n, _ast.Name) and isinstance(n.ctx, _ast.Store):
            defined.add(n.id)
    ren = {name: f"var{i}" for i, name in enumerate(sorted(defined))
           if name != "solve" and name not in params and ALIAS_RE.search(name)}
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError):
        return code
    out, prev = [], None
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.NAME and tok.string in ren and not (prev and prev.string == "."):
            tok = tok._replace(string=ren[tok.string])
        out.append(tok)
        prev = tok
    try:
        return tokenize.untokenize(out)
    except ValueError:
        return code


def audit_prompt(task: str, code: str, neigh: list[dict[str, Any]]) -> str:
    nk = "\n\n".join(f"[{n['source']} | {n['mode_hint']} | similarity {n['similarity']}]\n```python\n"
                     f"{n['code'][:1200]}\n```" for n in neigh)
    return (f"You audit whether a Python program is a genuinely new algorithm.\n\nTASK:\n{description(task)}\n\n"
            f"CATALOGUE OF KNOWN ALGORITHMS FOR THIS TASK:\n{catalogue_text(task)}\n\n"
            "CONTEXT: an automatic mechanism labeller could not assign any catalogue label to this program (it was "
            "labelled 'other').\n\n"
            f"CLASSES (choose exactly one):\n{CLASS_DEFS}\n\n"
            "DECISION ORDER: (1) if the program's mechanism is one of the catalogue algorithms above (even renamed, "
            "restructured, recursive vs iterative, or with a different container) -> LABELLER MISS; (2) else if it "
            "passes by hard-coding, test-specific shortcuts or a library call that bypasses the task's algorithmic "
            "work -> DEGENERATE; (3) else if it is any other known method (a named textbook or published algorithm, "
            "or a hybrid/variant of known ones) -> CATALOGUE VARIANT; (4) only if none applies -> NOVEL ALGORITHM.\n\n"
            f"PROGRAM (identifiers and comments that name algorithms were scrubbed):\n```python\n{code}\n```\n\n"
            f"NEAREST KNOWN HUMAN / TEXTBOOK SOLUTIONS (context):\n{nk}\n\n"
            "Judge the mechanism the code executes. Answer with JSON only: {\"class\": \"NOVEL ALGORITHM | CATALOGUE "
            "VARIANT | LABELLER MISS | DEGENERATE\", \"closest_known_algorithm\": \"...\", \"rationale\": \"two "
            "sentences\", \"catalogue_label_if_miss\": \"<label id or null>\", \"confidence\": <0-1>}")


def parse_audit(txt: str | None) -> dict[str, Any]:
    if not txt:
        return {"class": None}
    m = re.search(r"\{.*\}", txt, re.S)
    js: dict[str, Any] = {}
    if m:
        try:
            js = json.loads(m.group(0))
        except json.JSONDecodeError:
            js = {}
    c = str(js.get("class", "")).upper().strip()
    cls = next((k for k in AUDIT_CLASSES if k in c), None) or next((k for k in AUDIT_CLASSES if k in txt.upper()),
                                                                    None)
    return {"class": cls, "closest_known_algorithm": js.get("closest_known_algorithm"),
            "rationale": js.get("rationale"), "catalogue_label_if_miss": js.get("catalogue_label_if_miss"),
            "confidence": js.get("confidence")}


# ------------------------------------------------------------------------------------------------ LLM calls
class Budget:
    def __init__(self, cap: float):
        c = read_json(COSTS) if COSTS.exists() else {}
        self.total = float(c.get("total_usd", 0.0))
        self.by_purpose: dict[str, float] = dict(c.get("by_purpose", {}))
        self.cap = cap
        self.stopped = False
        self.reason = None
        self.n = int(c.get("n_calls", 0))

    def add(self, purpose: str, usd: float) -> None:
        self.total += usd
        self.n += 1
        self.by_purpose[purpose] = self.by_purpose.get(purpose, 0.0) + usd
        if self.total >= self.cap:
            self.stopped, self.reason = True, f"own cap USD {self.cap} reached"
        self.save()

    def refuse(self, msg: str) -> None:
        self.stopped, self.reason = True, f"phase budget refusal: {msg[:160]}"
        self.save()

    def save(self) -> None:
        write_json(COSTS, {"total_usd": round(self.total, 6), "by_purpose": self.by_purpose, "n_calls": self.n,
                           "stopped": self.stopped, "stop_reason": self.reason, "cap_usd": self.cap,
                           "utc": utc_now()})


def key_status() -> dict[str, Any]:
    import urllib.request

    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


_CACHE: dict[str, dict[str, Any]] | None = None


async def call_llm(sem: asyncio.Semaphore, budget: Budget, model: str, prompt: str, purpose: str,
                   max_tokens: int = 350) -> str | None:
    global _CACHE
    if _CACHE is None:
        _CACHE = {r["key"]: r for r in read_jsonl(LLM_CACHE)}
    key = sha256_text(model + "|" + prompt)
    if key in _CACHE and _CACHE[key].get("text"):
        return _CACHE[key]["text"]
    if budget.stopped:
        return None
    from openai import AsyncOpenAI

    async with sem:
        if budget.stopped:
            return None
        client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                             timeout=120, max_retries=1)
        try:
            for attempt in range(4):
                try:
                    r = await client.chat.completions.create(model=model, temperature=0, max_tokens=max_tokens,
                                                             messages=[{"role": "user", "content": prompt}],
                                                             extra_body={"usage": {"include": True}})
                    break
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    if BUDGET_MSG in msg:
                        budget.refuse(msg)
                        return None
                    if attempt < 3 and any(c in msg for c in ("429", "500", "502", "503", "timed out")):
                        await asyncio.sleep(2 * 2 ** attempt)
                        continue
                    logger.warning(f"LLM call failed ({model}): {msg[:160]}")
                    return None
        finally:
            await client.close()
        txt = (r.choices[0].message.content or "") if r.choices else ""
        cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage is not None else 0.0
        budget.add(purpose, cost)
        rec = {"key": key, "model": model, "purpose": purpose, "text": txt, "cost": cost, "utc": utc_now()}
        _CACHE[key] = rec
        append_jsonl(LLM_CACHE, [rec])
        logger.debug(f"LLM {model} [{purpose}] ${cost:.5f}: {txt[:120]!r}")
        return txt


CONTROLS = [  # exp18 audit.CONTROLS (same six programs and expected classes)
    {"id": "ctrl_ref_kmp", "task": "T04", "expected": "LABELLER MISS", "kind": "catalogue reference (KMP)",
     "file": "T04_substring_search/references/kmp.py"},
    {"id": "ctrl_ref_bfs_t10", "task": "T10", "expected": "LABELLER MISS", "kind": "catalogue reference (BFS)",
     "file": "T10_connected_components/references/bfs.py"},
    {"id": "ctrl_obfuscated_uf", "task": "T10", "expected": "LABELLER MISS", "kind": "obfuscated union-find",
     "code": "def solve(n, edges):\n    a = list(range(n))\n    def g(x):\n        while a[x] != x:\n            a[x] = a[a[x]]\n"
             "            x = a[x]\n        return x\n    c = n\n    for u, v in edges:\n        p, q = g(u), g(v)\n"
             "        if p != q:\n            a[p] = q\n            c -= 1\n    return c\n"},
    {"id": "ctrl_degenerate", "task": "T03", "expected": "DEGENERATE", "kind": "hard-coded test shortcut",
     "code": "def solve(nums, k):\n    if nums == [3, 1, 3] and k == 3:\n        return 3\n    if k == 1:\n"
             "        return min(nums)\n    if k == len(nums):\n        return max(nums)\n    return nums[0]\n"},
    {"id": "ctrl_textbook_value_bisection", "task": "T03", "expected": "CATALOGUE VARIANT",
     "kind": "textbook non-catalogue (binary search on the value range with counting)",
     "code": "def solve(nums, k):\n    lo, hi = min(nums), max(nums)\n    while lo < hi:\n        mid = (lo + hi) // 2\n"
             "        cnt = sum(1 for x in nums if x <= mid)\n        if cnt >= k:\n            hi = mid\n        else:\n"
             "            lo = mid + 1\n    return lo\n"},
    {"id": "ctrl_renamed_default", "task": "T03", "expected": "LABELLER MISS", "kind": "renamed default (full sort)",
     "code": "def solve(nums, k):\n    arranged = list(nums)\n    arranged.sort()\n    return arranged[k - 1]\n"},
]


async def _judge_items(items: list[dict[str, Any]], budget: Budget, models: list[str], purpose: str,
                       known_by_task: dict[str, list]) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(8)

    async def one(it):
        t = it["task"]
        neigh = nearest_known(it["code"], known_by_task.get(t, []), 3)
        pr = audit_prompt(t, scrub(t, it["code"]), neigh)
        res = await asyncio.gather(*[call_llm(sem, budget, m, pr, purpose) for m in models])
        return {"id": it["id"], "task": t, "neighbours": [{k: v for k, v in n.items() if k != "code"} for n in neigh],
                **{f"judge_{i}": {"model": m, **parse_audit(x)} for i, (m, x) in enumerate(zip(models, res))}}
    return await asyncio.gather(*[one(it) for it in items])


def run_audit() -> dict[str, Any]:
    from analysis import load_rows

    setup_logging("audit")
    ks = key_status()
    write_json(RESULTS_DIR / "openrouter_key_status_before_audit.json",
               {k: v for k, v in (ks.get("data") or ks).items() if k in ("limit", "limit_remaining", "usage",
                                                                         "error", "label")})
    if not KNOWN.exists():
        build_known_solutions()
    known = read_jsonl(KNOWN)
    known_by_task = defaultdict(list)
    for k in known:
        known_by_task[k["task"]].append(k)
    rows = load_rows()
    pool_all = [r for r in rows if r["label"] == "other" and r["passed"] and r.get("code")]
    uniq: dict[tuple[str, str], dict[str, Any]] = {}
    for r in pool_all:
        uniq.setdefault((r["task"], r["code_sha256"]), {**r, "arms": []})["arms"].append(r["arm"])
    logger.info(f"audit pool: {len(pool_all)} correct 'other' programs, {len(uniq)} unique")
    # 12.1 stress tests
    recs = []
    for (t, h), r in sorted(uniq.items()):
        st = stress_test(t, r["code"], seed=int(h[:8], 16))
        recs.append({"id": f"{t}|{h[:12]}", "task": t, "code_sha256": h, "arms": r["arms"], "n_rows": len(r["arms"]),
                     "stress": st, "code": r["code"]})
    survivors = [x for x in recs if x["stress"]["passed"]]
    logger.info(f"stress tests: {len(survivors)}/{len(recs)} pass")
    budget = Budget(AUDIT_CAP_USD + CONTROL_CAP_USD)
    # 12.2 controls
    citems = []
    for c in CONTROLS:
        code = (BENCH / c["file"]).read_text() if "file" in c else c["code"]
        citems.append({"id": c["id"], "task": c["task"], "code": code})
    cres = asyncio.run(_judge_items(citems, budget, [JUDGE_A, JUDGE_B, TIEBREAK], "audit_controls", known_by_task))
    ctrl = []
    for c, r in zip(CONTROLS, cres):
        ctrl.append({"id": c["id"], "kind": c["kind"], "expected": c["expected"],
                     **{r[f"judge_{i}"]["model"]: r[f"judge_{i}"]["class"] for i in range(3)}})
    ok = {m: sum(x[m] == x["expected"] for x in ctrl) for m in (JUDGE_A, JUDGE_B, TIEBREAK)}
    write_json(RESULTS_DIR / "audit_controls.json", {"controls": ctrl, "correct": ok,
                                                     "rule": "a judge failing >= 2 of 6 controls is replaced",
                                                     "utc": utc_now()})
    judges = [m for m in (JUDGE_A, JUDGE_B) if ok[m] >= 5]
    if len(judges) < 2 and ok[TIEBREAK] >= 5:
        judges.append(TIEBREAK)
    tb = [m for m in (TIEBREAK, JUDGE_A, JUDGE_B) if m not in judges and ok[m] >= 5]
    tiebreak = tb[0] if tb else TIEBREAK
    logger.info(f"controls correct {ok}; judges {judges}; tie-break {tiebreak}")
    # 12.3 judges on the survivors
    jres = asyncio.run(_judge_items([{"id": x["id"], "task": x["task"], "code": x["code"]} for x in survivors],
                                    budget, judges[:2], "audit_pool", known_by_task)) if survivors else []
    need_tb = [i for i, r in enumerate(jres) if r["judge_0"]["class"] != r["judge_1"]["class"]]
    tres = asyncio.run(_judge_items([{"id": survivors[i]["id"], "task": survivors[i]["task"],
                                      "code": survivors[i]["code"]} for i in need_tb], budget, [tiebreak],
                                    "audit_tiebreak", known_by_task)) if need_tb else []
    tmap = {need_tb[j]: r["judge_0"] for j, r in enumerate(tres)}
    for i, (x, r) in enumerate(zip(survivors, jres)):
        a, b = r["judge_0"]["class"], r["judge_1"]["class"]
        res = a if a == b else (tmap.get(i, {}).get("class"))
        x.update({"neighbours": r["neighbours"], "judge_A": r["judge_0"], "judge_B": r["judge_1"],
                  "tiebreak": tmap.get(i), "resolved_class": res})
    write_json(AUDIT_DIR / "novelty_audit_pool.json", {"utc": utc_now(), "n_pool_rows": len(pool_all),
                                                       "n_unique": len(recs), "records": recs,
                                                       "judges": judges, "tiebreak": tiebreak,
                                                       "budget": {"total_usd": budget.total,
                                                                  "stopped": budget.stopped,
                                                                  "reason": budget.reason}})
    return {"n_unique": len(recs), "n_stress_pass": len(survivors)}


def summarise_audit() -> dict[str, Any]:
    """12.5: combine judge resolution with the executor's manual pass (audit/manual_pass.jsonl)."""
    from analysis import load_rows

    pool = read_json(AUDIT_DIR / "novelty_audit_pool.json")
    manual = {r["id"]: r for r in read_jsonl(AUDIT_DIR / "manual_pass.jsonl")}
    rows = load_rows()
    n_correct_by_arm = Counter(r["arm"] for r in rows if r["correct"])
    recs = pool["records"]
    novel_confirmed, per = [], []
    for x in recs:
        m = manual.get(x["id"], {})
        jc = x.get("resolved_class")
        mv = m.get("verdict")
        conf = x["stress"]["passed"] and jc == "NOVEL ALGORITHM" and mv == "NOVEL ALGORITHM"
        per.append({"id": x["id"], "task": x["task"], "arms": x["arms"], "stress": x["stress"],
                    "judge_A": (x.get("judge_A") or {}).get("class"), "judge_B": (x.get("judge_B") or {}).get("class"),
                    "tiebreak": (x.get("tiebreak") or {}).get("class") if x.get("tiebreak") else None,
                    "resolved": jc, "manual": mv, "manual_reason": m.get("reason"), "confirmed_novel": conf})
        if conf:
            novel_confirmed.append(x["id"])
    by_arm = defaultdict(lambda: {"n_pool": 0, "n_stress_fail": 0, "n_novel_confirmed": 0})
    for p in per:
        for a in set(p["arms"]):
            by_arm[a]["n_pool"] += 1
            by_arm[a]["n_stress_fail"] += (not p["stress"]["passed"])
            by_arm[a]["n_novel_confirmed"] += p["confirmed_novel"]
    tot_all = sum(n_correct_by_arm.values())  # every labelled row, incl. TWIN_X filler (all scanned by the pool)
    tot_correct = sum(v for a, v in n_correct_by_arm.items() if a != "TWIN_X")  # analysed programs
    out = {"n_unique_pool": len(recs), "n_pool_rows": pool["n_pool_rows"],
           "n_incorrect_under_stress": sum(not p["stress"]["passed"] for p in per),
           "resolved_class_counts": dict(Counter(p["resolved"] for p in per if p["stress"]["passed"])),
           "manual_counts": dict(Counter(p["manual"] for p in per if p["stress"]["passed"])),
           "judge_agreement": (sum(p["judge_A"] == p["judge_B"] for p in per if p["stress"]["passed"]) /
                               max(1, sum(1 for p in per if p["stress"]["passed"]))),
           "n_novel_confirmed": len(novel_confirmed), "novel_ids": novel_confirmed,
           "n_correct_programs_all_arms": tot_correct, "n_correct_programs_incl_filler_twin_rows": tot_all,
           "rule_of_three_upper_bound": 3 / tot_correct if tot_correct else None,
           "claim_no_correct_novel_algorithm": len(novel_confirmed) == 0,
           "by_arm": {a: {**v, "n_correct_in_arm": n_correct_by_arm.get(a, 0),
                          "rule_of_three": 3 / n_correct_by_arm[a] if n_correct_by_arm.get(a) else None}
                      for a, v in sorted(by_arm.items())},
           "records": per, "judges": pool["judges"], "tiebreak": pool["tiebreak"], "spend": pool["budget"]}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    return out


# ------------------------------------------------------------------------------------------------ dependency usage
def dependency_usage() -> dict[str, Any]:
    """How each of the 10 datasets of art_j3Rm_lr2nzR6 enters this artifact (streamed with ijson)."""
    import ijson

    counts, llm, clrs, nouns_found = Counter(), Counter(), Counter(), {}
    want = set()
    for t in ("T03", "T05", "T06", "T10"):
        nn = json.loads((BENCH / BENCH_DIRS[t] / "neutral_nouns.json").read_text())
        want.add(nn[DEFAULT[t]]["nouns"][0]["word"])
    want |= {"man", "house", "baby", "car", "guy"}
    he_items, en_items = [], []
    with (DEP_DATASET / "full_data_out.json").open("rb") as f:
        for ds in ijson.items(f, "datasets.item"):
            name = ds["dataset"]
            counts[name] = len(ds["examples"])
            for ex in ds["examples"]:
                if name == "llm_creativity":
                    llm[str(ex.get("metadata_t02_mode"))] += 1
                elif name == "concreteness_norms" and ex.get("input") in want:
                    nouns_found[ex["input"]] = {"concreteness": ex.get("output"),
                                                "subtlex_frequency": ex.get("metadata_subtlex_frequency"),
                                                "qwen3_tokens_with_leading_space":
                                                    ex.get("metadata_qwen3_tokens_with_leading_space")}
                elif name == "clrs_text":
                    try:
                        for link in json.loads(str(ex.get("metadata_bench_links") or "[]").replace("'", '"')):
                            clrs[link] += 1
                    except json.JSONDecodeError:
                        pass
                elif name == "humanevalplus" and len(he_items) < 20:
                    he_items.append(ex)
                elif name == "enamel" and len(en_items) < 5:
                    en_items.append(ex)
    # sandbox validation on HumanEval+ references (the stress-test runner must pass correct code and fail broken code)
    he_ok = he_bad = 0
    for ex in he_items:
        code, test, ep = ex.get("output") or "", ex.get("metadata_test") or "", ex.get("metadata_entry_point")
        prog = code + "\n" + test + f"\ncheck({ep})\nprint('OK')\n"
        broken = code.replace("return", "return None and ", 1) + "\n" + test + f"\ncheck({ep})\nprint('OK')\n"
        for src, good in ((prog, True), (broken, False)):
            try:
                p = subprocess.run([_sandbox_python(), "-I", "-"], input=src, capture_output=True,
                                   text=True, timeout=60)
                passed = p.returncode == 0 and "OK" in p.stdout
            except subprocess.TimeoutExpired:
                passed = False
            if good:
                he_ok += passed
            else:
                he_bad += (not passed)
    t2_step0 = Counter(r["label"] for r in read_jsonl(DATA_DIR / "labels.jsonl") if r["task"] == "T2" and
                       r["arm"] == "TWIN")
    n_llm = sum(llm.values())
    out = {"utc": utc_now(), "datasets": {
        "leetcodedataset": {"n": counts["leetcodedataset"], "use": "known-solution index (reference solutions; "
                                                                   "LeetCode 1 added for T05)"},
        "mercury": {"n": counts["mercury"], "use": "known-solution index (human solutions)"},
        "thealgorithms_python": {"n": counts["thealgorithms_python"], "use": "known-solution index (textbook code)"},
        "kodcode_algorithmic": {"n": counts["kodcode_algorithmic"], "use": "known-solution index (named-mode code)"},
        "xlcost_python": {"n": counts["xlcost_python"], "use": "known-solution index (named-mode code)"},
        "llm_creativity": {"n": counts["llm_creativity"], "use": "external T2 label prior vs this artifact's T2 twin",
                           "t2_mode_counts": dict(llm), "dijkstra_share": llm.get("dijkstra", 0) / n_llm if n_llm
                           else None, "this_artifact_T2_twin": dict(t2_step0)},
        "concreteness_norms": {"n": counts["concreteness_norms"], "use": "provenance of the rendered neutral-twin nouns",
                               "rows": nouns_found, "all_found": all(w in nouns_found for w in want)},
        "clrs_text": {"n": counts["clrs_text"], "use": "bench tracer access-order tests (exp11); counted per link",
                      "traces_per_bench_link": dict(clrs)},
        "humanevalplus": {"n": counts["humanevalplus"], "use": "validation of this artifact's sandbox runner: 20 "
                          "reference solutions + EvalPlus tests must pass, 20 broken variants must fail",
                          "reference_pass": he_ok, "broken_fail": he_bad, "n_checked": len(he_items)},
        "enamel": {"n": counts["enamel"], "use": "size-levelled stress calibration (exp11 bench); its level sizes "
                   "motivate stress tests at 0.5x and 1.0x the spec's maximum", "example_levels":
                   [e.get("metadata_input_levels") for e in en_items]}}}
    write_json(RESULTS_DIR / "dependency_usage.json", out)
    return out


if __name__ == "__main__":
    setup_logging("audit_main")
    cmd = sys.argv[1]
    if cmd == "index":
        print(build_known_solutions())
    elif cmd == "run":
        print(run_audit())
    elif cmd == "summary":
        print({k: v for k, v in summarise_audit().items() if k not in ("records", "by_arm")})
    elif cmd == "deps":
        print({k: {kk: vv for kk, vv in v.items() if kk in ("n", "reference_pass", "broken_fail", "all_found")}
               for k, v in dependency_usage()["datasets"].items()})
