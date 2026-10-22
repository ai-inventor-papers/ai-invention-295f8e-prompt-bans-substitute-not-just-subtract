"""Stage 0f: second blind adjudication of the 14 transplant programs that two of three judges called novel.

F1 items, F2 sandboxed stress tests (bench copy of art_CcZLW-9NX00l), F3 nearest known solutions by Zhang-Shasha tree
edit distance on identifier-normalised ASTs, F4 ten blinded controls with known classes, F5 judges from two model
families this run has never used (Mistral primary x3 at T=0, Moonshot Kimi second view x1), F6 agreement, F7 report."""

from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import re
import resource
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np
from loguru import logger

from src import common as C
from src import xstats as X

WS = C.WS
BENCH = "inputs/exp11/bench"
TASK_DIR = {"R6": "R6_first_last_position", "T14": "T14_top_k_frequent", "T10": "T10_connected_components",
            "T06": "T06_find_duplicate", "T03": "T03_kth_smallest", "T04": "T04_substring_search"}
PRIMARY = "mistralai/mistral-medium-3.1"
SECOND = "moonshotai/kimi-k2-0905"
USED_BEFORE = ["google/gemini-2.5-flash", "google/gemini-2.5-flash-lite", "openai/gpt-4.1-mini",
               "deepseek/deepseek-chat-v3-0324"]
CLASSES = ["NOVEL_ALGORITHM", "KNOWN_OUTSIDE_CATALOGUE", "CATALOGUE_VARIANT", "DEGENERATE"]
MANUAL_MAP = {"KNOWN, OUTSIDE THE CATALOGUE": "KNOWN_OUTSIDE_CATALOGUE", "CATALOGUE VARIANT": "CATALOGUE_VARIANT",
              "DEGENERATE": "DEGENERATE", "NOVEL": "NOVEL_ALGORITHM"}
CACHE = WS / "audit" / "judge_cache.jsonl"

# --------------------------------------------------------------------------------------------- controls (F4)
TEXTBOOK = {
    "R6": ("linear_scan_textbook", "def solve(nums, target):\n    first = last = -1\n    for i, x in enumerate(nums):\n"
                                    "        if x == target:\n            if first == -1:\n                first = i\n"
                                    "            last = i\n    return [first, last]\n"),
    "T14": ("repeated_max_selection_textbook",
            "def solve(nums, k):\n    counts = {}\n    for x in nums:\n        counts[x] = counts.get(x, 0) + 1\n"
            "    items = list(counts.items())\n    result = []\n    for _ in range(k):\n        best = 0\n"
            "        for j in range(1, len(items)):\n            if items[j][1] > items[best][1]:\n                best = j\n"
            "        result.append(items[best][0])\n        items.pop(best)\n    return result\n"),
    "T10": ("warshall_closure_textbook",
            "def solve(n, edges):\n    reach = [1 << i for i in range(n)]\n    for u, v in edges:\n"
            "        reach[u] |= 1 << v\n        reach[v] |= 1 << u\n    for k in range(n):\n        bit = 1 << k\n"
            "        rk = reach[k]\n        for i in range(n):\n            if reach[i] & bit:\n"
            "                reach[i] |= rk\n    return len(set(reach))\n"),
}
CATALOGUE_CONTROLS = [("R6", "binary_search"), ("T14", "heap"), ("T10", "union_find"), ("T10", "dfs")]


class _Scrub(ast.NodeTransformer):
    """Cosmetic rewrite: rename every user identifier except solve and its parameters; drop docstrings."""

    def __init__(self, keep: set[str]):
        self.keep = keep
        self.map: dict[str, str] = {}
        import builtins
        self.builtins = set(dir(builtins))

    def _n(self, name: str) -> str:
        if name in self.keep or name in self.builtins:
            return name
        if name not in self.map:
            self.map[name] = f"t{len(self.map) + 1}"
        return self.map[name]

    def visit_FunctionDef(self, node):
        if node.name != "solve":
            node.name = self._n(node.name)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = self._n(node.arg)
        return node

    def visit_Name(self, node):
        node.id = self._n(node.id)
        return node


def scrub(code: str, keep: set[str]) -> str:
    tree = ast.parse(code)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                imported.add((a.asname or a.name).split(".")[0])
    tree = _Scrub(keep | imported | {"solve"}).visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


# --------------------------------------------------------------------------------------------- AST trees (F3)
def norm_tree(code: str):
    """Identifier-normalised AST as zss nodes: identifiers renamed in order of first appearance, docstrings and
    constants' values dropped, attribute names (library calls) kept."""
    from zss import Node
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None, 0
    names: dict[str, str] = {}

    def nm(s: str) -> str:
        if s not in names:
            names[s] = f"v{len(names)}"
        return names[s]

    def build(node) -> tuple:
        label = type(node).__name__
        if isinstance(node, ast.Name):
            label += ":" + nm(node.id)
        elif isinstance(node, ast.arg):
            label += ":" + nm(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            label += ":" + nm(node.name)
        elif isinstance(node, ast.Attribute):
            label += ":" + node.attr
        kids = []
        body = list(ast.iter_child_nodes(node))
        for ch in body:
            if isinstance(ch, ast.Expr) and isinstance(getattr(ch, "value", None), ast.Constant) and isinstance(ch.value.value, str):
                continue
            if isinstance(ch, (ast.Load, ast.Store, ast.Del)):
                continue
            kids.append(build(ch))
        return (label, kids)

    t = build(tree)

    def to_zss(t):
        n = Node(t[0])
        for k in t[1]:
            n.addkid(to_zss(k))
        return n

    def size(t):
        return 1 + sum(size(k) for k in t[1])
    return to_zss(t), size(t)


SHORTLIST = 20


def _canon_src(code: str) -> str:
    """Identifier-scrubbed, docstring-free source used only to shortlist candidates for the exact tree edit distance."""
    try:
        return scrub(code, {"solve"})
    except (SyntaxError, ValueError):
        return code


def _ted_job(args) -> list[tuple[int, float]]:
    code, pool = args
    from zss import simple_distance
    a, sa = norm_tree(code)
    out = []
    for j, pc in enumerate(pool):
        b, sb = norm_tree(pc)
        if a is None or b is None:
            out.append((j, math.inf))
            continue
        out.append((j, simple_distance(a, b) / max(sa, sb)))
    return out


# --------------------------------------------------------------------------------------------- stress cases (F2)
def stress_cases(task: str) -> list[dict]:
    out = []
    if task == "R6":
        for tag, seed in (("a_max_random_seed1", 1), ("c_max_random_seed2", 2)):
            rng = random.Random(seed)
            base = [rng.randint(-10 ** 9, 10 ** 9) for _ in range(100000 - 60)]
            t = rng.choice(base)
            nums = sorted(base + [t] * 60)
            out.append({"id": tag, "group": tag[0], "kwargs": {"nums": nums, "target": t}})
        out.append({"id": "b_all_equal", "group": "b", "kwargs": {"nums": [7] * 100000, "target": 7}})
        rng = random.Random(3)
        ev = sorted(2 * rng.randint(-5 * 10 ** 8, 5 * 10 ** 8) for _ in range(100000))
        out.append({"id": "b_absent", "group": "b", "kwargs": {"nums": ev, "target": ev[50000] + 1}})
        mid = sorted(rng.randint(0, 10 ** 9) for _ in range(99000))
        out.append({"id": "b_target_at_start", "group": "b", "kwargs": {"nums": [-10 ** 9] * 1000 + mid, "target": -10 ** 9}})
        out.append({"id": "b_target_at_end", "group": "b", "kwargs": {"nums": [-5] * 1000 + [x for x in mid if x < 10 ** 9] + [10 ** 9] * 500, "target": 10 ** 9}})
    elif task == "T14":
        for tag, seed in (("a_max_random_seed1", 1), ("c_max_random_seed2", 2)):
            rng = random.Random(seed)
            vals = rng.sample(range(-10000, 10001), 2100)
            k = 100
            freq = {v: rng.randint(6, 40) for v in vals[:k]}
            left = 10000 - sum(freq.values())
            for v in vals[k:]:
                if left <= 0:
                    break
                f = min(rng.randint(1, 5), left)
                freq[v] = f
                left -= f
            nums = [v for v, f in freq.items() for _ in range(f)]
            rng.shuffle(nums)
            out.append({"id": tag, "group": tag[0], "kwargs": {"nums": nums, "k": k}})
        rng = random.Random(4)
        vals = rng.sample(range(-10000, 10001), 2000)
        nums = [v for v in vals for _ in range(5)]
        rng.shuffle(nums)
        out.append({"id": "b_all_tied_k_unique", "group": "b", "kwargs": {"nums": nums, "k": len(vals)}})
    elif task == "T10":
        for tag, seed, m in (("a_max_random_seed1", 1, 1500), ("c_max_random_seed2", 2, 300)):
            rng = random.Random(seed)
            pairs = set()
            while len(pairs) < m:
                u, v = rng.randrange(300), rng.randrange(300)
                if u != v:
                    pairs.add((min(u, v), max(u, v)))
            edges = [[u, v] if rng.random() < 0.5 else [v, u] for u, v in sorted(pairs)]
            rng.shuffle(edges)
            out.append({"id": tag, "group": tag[0], "kwargs": {"n": 300, "edges": edges}})
        rng = random.Random(5)
        order = list(range(300))
        rng.shuffle(order)
        path = order[:250]
        edges = [[path[i], path[i + 1]] for i in range(249)]
        out.append({"id": "b_isolated_plus_long_path", "group": "b", "kwargs": {"n": 300, "edges": edges}})
        out.append({"id": "b_long_path_reversed", "group": "b", "kwargs": {"n": 300, "edges": list(reversed(edges))}})
    return out


def _limits_rlimit():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


def run_sandbox(code: str, cases: list[dict], limits: list[float]) -> dict:
    (WS / "scratch").mkdir(exist_ok=True)
    job = json.dumps({"code": code, "cases": [{"id": c["id"], "kwargs": c["kwargs"]} for c in cases], "limits": limits})
    try:
        r = subprocess.run([sys.executable, "-I", str(WS / "src" / "sandbox_child.py")], input=job, capture_output=True,
                           text=True, timeout=sum(limits) + 30, preexec_fn=_limits_rlimit, env={"PATH": "/usr/bin:/bin"},
                           cwd=str(WS / "scratch"))
        return json.loads(r.stdout) if r.stdout.strip() else {"error": (r.stderr or "no output")[-300:], "results": []}
    except subprocess.TimeoutExpired:
        return {"error": "subprocess timeout", "results": []}
    except json.JSONDecodeError:
        return {"error": "bad child output", "results": []}


def _canon(task: str, out):
    if task == "T14" and isinstance(out, list):
        try:
            return sorted(out)
        except TypeError:
            return out
    return out


def load_checker(task: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"chk_{task}", WS / "vendor" / "bench_checkers" / f"{task}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.check


def oracle_and_refs(task: str) -> dict:
    """Run every catalogue reference on the stress cases; keep the cases on which the references agree."""
    tdir = f"{BENCH}/{TASK_DIR[task]}"
    refs = {p.stem: p.read_text() for p in sorted(C.dep_path("D24", f"{tdir}/references").glob("*.py"))}
    for k in refs:
        C._record("D24", f"{tdir}/references/{k}.py", C.dep_path("D24", f"{tdir}/references/{k}.py"))
    cases = stress_cases(task)
    res = {}
    for m, code in refs.items():
        res[m] = run_sandbox(code, cases, [20.0] * len(cases))
    oracle, fastest = {}, {}
    for i, c in enumerate(cases):
        outs = []
        times = []
        for m in refs:
            rr = res[m]["results"]
            if i < len(rr) and rr[i]["ok"]:
                outs.append(json.dumps(_canon(task, rr[i]["output"])))
                times.append(rr[i]["seconds"])
        if len(outs) == len(refs) and len(set(outs)) == 1:
            oracle[c["id"]] = json.loads(outs[0])
            fastest[c["id"]] = min(times)
    return {"refs": refs, "cases": cases, "oracle": oracle, "fastest": fastest,
            "ref_runs": {m: [{"id": r["id"], "ok": r["ok"], "seconds": r["seconds"]} for r in v["results"]] for m, v in res.items()}}


def evaluate_program(task: str, code: str, orc: dict, hidden: list[dict], check) -> dict:
    cases = [c for c in orc["cases"] if c["id"] in orc["oracle"]]
    lim = [max(1.0, 10 * orc["fastest"][c["id"]]) for c in cases]
    sr = run_sandbox(code, cases, lim)
    by = {r["id"]: r for r in sr.get("results", [])}
    groups: dict[str, list] = {}
    detail = []
    for c, l in zip(cases, lim):
        r = by.get(c["id"])
        if r is None:
            st = "not run"
        elif not r["ok"]:
            st = r["error"]
        else:
            st = "pass" if check(copy.deepcopy(c["kwargs"]), orc["oracle"][c["id"]], r["output"]) else "wrong answer"
        detail.append({"id": c["id"], "status": st, "seconds": r["seconds"] if r else None, "limit": l})
        groups.setdefault(c["group"], []).append(st == "pass")
    stress = {g: all(v) for g, v in sorted(groups.items())}
    hk = [{"id": h["case_id"], "kwargs": h["kwargs"]} for h in hidden]
    hl = [max(1.0, float(h.get("limit", 1.0))) for h in hidden]
    hr = run_sandbox(code, hk, hl)
    hby = {r["id"]: r for r in hr.get("results", [])}
    hp = 0
    for h in hidden:
        r = hby.get(h["case_id"])
        if r and r["ok"] and check(copy.deepcopy(h["kwargs"]), h["expected"], r["output"]):
            hp += 1
    return {"stress_groups": stress, "stress_detail": detail, "hidden_pass": hp, "hidden_n": len(hidden),
            "compile_error": sr.get("compile_error") or hr.get("compile_error"),
            "all_pass": all(stress.values()) and hp == len(hidden)}


def stress_text(ev: dict) -> str:
    if ev is None:
        return "not run (task outside the stress bench)"
    parts = [f"hidden tests passed {ev['hidden_pass']} of {ev['hidden_n']}"]
    for d in ev["stress_detail"]:
        # run-dependent timings stay out of the prompt so that prompts (and the judge cache keys) are deterministic
        parts.append(f"{d['id']}: {d['status']} (time limit {d['limit']:.2f} s)")
    return "; ".join(parts)


# --------------------------------------------------------------------------------------------- judges (F5)
def build_prompt(item: dict, spec: dict, nearest: list[dict]) -> list[dict]:
    cat = "\n".join(f"- {c['mode']}: {c.get('display_name', '')}" for c in spec["catalogue"])
    near = "\n\n".join(f"[{n['ref_id']}] (normalised tree-edit distance {n['dist']:.2f})\n```python\n{n['code'][:1800]}\n```"
                       for n in nearest)
    sys_msg = ("You are an expert in algorithms and data structures. You classify a Python program by the algorithmic "
               "technique it implements. Answer with one JSON object only.")
    user = f"""TASK
{spec['description']}

CATALOGUE (the algorithms the study lists for this task)
{cat}

PROGRAM TO CLASSIFY (it passed the task's tests unless stated below)
```python
{item['code']}
```

SANDBOXED TEST OUTCOMES
{item['stress_text']}

THREE NEAREST KNOWN SOLUTIONS (examples, not exhaustive; they do NOT define what is known)
{near}

QUESTION
First decide whether the program's method is a KNOWN technique anywhere (textbooks, the algorithms literature,
competitive programming, everyday programming practice), and name it. Then give exactly one class:
- CATALOGUE_VARIANT: it implements one of the catalogue algorithms above, possibly restructured or renamed.
- KNOWN_OUTSIDE_CATALOGUE: it implements a known technique that is not in the catalogue (name the technique).
- DEGENERATE: the core of the task is done by a direct call to a built-in or library routine that already solves it
  (for example list.index to search, or list.count on every element), so the program has no algorithm of its own.
- NOVEL_ALGORITHM: its method is not a known technique at all; use this only if you cannot name any known technique.

Return JSON: {{"class": "<one of NOVEL_ALGORITHM | KNOWN_OUTSIDE_CATALOGUE | CATALOGUE_VARIANT | DEGENERATE>",
"named_technique": "<name of the technique, or empty>", "closest_reference_id": "<id of the nearest example above>",
"reason": "<at most 40 words>"}}"""
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}]


def parse_judge(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {"class": "UNPARSED", "named_technique": "", "closest_reference_id": "", "reason": (text or "")[:200]}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        cls = next((c for c in CLASSES if c in text), "UNPARSED")
        return {"class": cls, "named_technique": "", "closest_reference_id": "", "reason": text[:200]}
    c = str(d.get("class", "")).strip().upper().replace(" ", "_")
    d["class"] = c if c in CLASSES else next((k for k in CLASSES if k in c), "UNPARSED")
    return d


class Budget:
    def __init__(self, cap: float):
        self.cap = cap
        self.spent = 0.0
        self.stop = False
        self.n_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0


async def _call(session, sem, budget: Budget, model: str, messages: list[dict], key: str, cache: dict) -> dict:
    if key in cache:
        return cache[key]
    async with sem:
        if budget.stop or budget.spent >= budget.cap:
            return {"error": "budget stop"}
        body = {"model": model, "messages": messages, "temperature": 0,
                "max_tokens": 4000 if model == SECOND else 1500,  # Kimi sometimes spends 1,500 tokens on hidden reasoning
                "usage": {"include": True}}
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}
        import aiohttp
        for attempt in range(4):
            try:
                async with session.post(url, json=body, headers=hdr, timeout=aiohttp.ClientTimeout(total=120)) as r:
                    txt = await r.text()
                    if r.status == 403 and "AI Inventor per-run OpenRouter budget" in txt:
                        budget.stop = True
                        logger.error("OpenRouter budget refusal: stopping the batch")
                        return {"error": "budget 403"}
                    if r.status != 200:
                        logger.warning(f"{model} HTTP {r.status}: {txt[:200]}")
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    u = d.get("usage") or {}
                    cost = float(u.get("cost") or 0.0)
                    budget.spent += cost
                    budget.n_calls += 1
                    budget.tokens_in += int(u.get("prompt_tokens") or 0)
                    budget.tokens_out += int(u.get("completion_tokens") or 0)
                    content = d["choices"][0]["message"].get("content") or ""
                    res = {"model": model, "content": content, "cost": cost, "usage": u, "parsed": parse_judge(content)}
                    cache[key] = res
                    with CACHE.open("a") as f:
                        f.write(json.dumps({"key": key, **res}) + "\n")
                    logger.debug(f"judge {model} {key[:16]}: {content[:200]!r}")
                    return res
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(f"{model} call error {type(e).__name__}; retry {attempt + 1}")
                await asyncio.sleep(2 * (attempt + 1))
        return {"error": "failed after retries"}


async def run_judges(items: list[dict], budget: Budget) -> dict:
    import aiohttp
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                if (d.get("content") or "").strip():
                    d["parsed"] = parse_judge(d["content"])
                    cache[d["key"]] = d  # empty responses (token cap reached) are re-queried
    sem = asyncio.Semaphore(4)
    jobs = []
    async with aiohttp.ClientSession() as session:
        for it in items:
            psha = hashlib.sha256(json.dumps(it["messages"]).encode()).hexdigest()[:16]
            for model, ncalls in ((PRIMARY, 3), (SECOND, 1)):
                for k in range(ncalls):
                    key = f"{model}|{it['blind_id']}|{k}|{psha}"
                    jobs.append((it["blind_id"], model, k, _call(session, sem, budget, model, it["messages"], key, cache)))
        res = await asyncio.gather(*[j[3] for j in jobs], return_exceptions=True)
    out: dict = {}
    for (bid, model, k, _), r in zip(jobs, res):
        if isinstance(r, Exception):
            r = {"error": repr(r)}
        out.setdefault(bid, {}).setdefault(model, []).append(r)
    return out


def majority(classes: list[str]) -> str:
    c = Counter(x for x in classes if x in CLASSES)
    if not c:
        return "UNPARSED"
    top = c.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        # ties broken toward the more conservative (less novel) class order
        tied = [k for k, v in top if v == top[0][1]]
        for k in ["CATALOGUE_VARIANT", "KNOWN_OUTSIDE_CATALOGUE", "DEGENERATE", "NOVEL_ALGORITHM"]:
            if k in tied:
                return k
    return top[0][0]


# --------------------------------------------------------------------------------------------- main
def run(ledger: C.Ledger, report: C.Report, max_usd: float = 0.90) -> dict:
    t0 = time.time()
    na = C.load_json("D24", "results/novelty_audit.json")
    items_all = na["items"]
    # F1
    seen, novel = set(), []
    for it in items_all:
        if it.get("final_class") == "NOVEL_ALGORITHM" and it["code_sha256"] not in seen:
            seen.add(it["code_sha256"])
            novel.append(it)
    f1 = {"n": len(novel), "by_task": Counter(i["task"] for i in novel), "manual": Counter(i["manual_class"] for i in novel)}
    logger.info(f"F1: {f1}")
    # F4 controls
    specs = {t: C.load_json("D24", f"{BENCH}/{TASK_DIR[t]}/spec.json") for t in ("R6", "T14", "T10")}
    controls = []
    for t, m in CATALOGUE_CONTROLS:
        code = C.read_text("D24", f"{BENCH}/{TASK_DIR[t]}/references/{m}.py")
        sig = specs[t]["signature"]
        keep = set(re.findall(r"\((.*)\)", sig)[0].replace(" ", "").split(","))
        controls.append({"task": t, "kind": "control_catalogue_variant", "truth": "CATALOGUE_VARIANT",
                         "code": scrub(code, keep), "source": C.prov("D24", f"{BENCH}/{TASK_DIR[t]}/references/{m}.py") + " (scrubbed)",
                         "control_of": m})
    for t, (nm, code) in TEXTBOOK.items():
        controls.append({"task": t, "kind": "control_textbook_outside", "truth": "KNOWN_OUTSIDE_CATALOGUE", "code": code,
                         "source": "written by the executor from a textbook description", "control_of": nm})
    degs = [i for i in items_all if i["manual_class"] == "DEGENERATE" and i["task"] == "R6"]
    degs = sorted(degs, key=lambda i: i["code_sha256"])[:3]
    for d in degs:
        controls.append({"task": "R6", "kind": "control_degenerate_audit", "truth": "DEGENERATE", "code": d["code"],
                         "source": C.prov("D24", "results/novelty_audit.json", f"/items[code_sha256={d['code_sha256'][:12]}]"),
                         "control_of": d["manual_note"]})
    # extension: the audit's other KNOWN-outside items (descriptive, not gated)
    ext = [i for i in items_all if MANUAL_MAP.get(i["manual_class"]) == "KNOWN_OUTSIDE_CATALOGUE" and i["code_sha256"] not in seen]
    items = []
    for i in novel:
        items.append({"task": i["task"], "kind": "disputed_14", "truth": MANUAL_MAP[i["manual_class"]], "code": i["code"],
                      "code_sha256": i["code_sha256"], "manual_class": i["manual_class"], "manual_note": i["manual_note"],
                      "orig_judges": {k: (i.get(k) or {}).get("class") for k in ("judge_a", "judge_b", "judge_c")},
                      "source": C.prov("D24", "results/novelty_audit.json", f"/items[code_sha256={i['code_sha256'][:12]}]")})
    for c in controls:
        c["code_sha256"] = hashlib.sha256(c["code"].encode()).hexdigest()
        items.append(c)
    for i in ext:
        items.append({"task": i["task"], "kind": "extension_known_outside", "truth": "KNOWN_OUTSIDE_CATALOGUE",
                      "code": i["code"], "code_sha256": i["code_sha256"], "manual_class": i["manual_class"],
                      "manual_note": i["manual_note"], "source": C.prov("D24", "results/novelty_audit.json")})
    rng = random.Random(20261022)
    order = list(range(len(items)))
    rng.shuffle(order)
    for rank, idx in enumerate(order):
        items[idx]["blind_id"] = f"P{rank + 1:02d}"
    logger.info(f"F4: {len(controls)} controls; extension {len(ext)}; total items {len(items)}")
    # F2 stress tests
    orc = {t: oracle_and_refs(t) for t in ("R6", "T14", "T10")}
    for t, o in orc.items():
        logger.info(f"F2 oracle {t}: {len(o['oracle'])} of {len(o['cases'])} stress cases unanimous; fastest {o['fastest']}")
    checks = {t: load_checker(t) for t in ("R6", "T14", "T10", "T06", "T03", "T04")}
    hidden = {}
    for t in set(i["task"] for i in items):
        if t in TASK_DIR:
            hidden[t] = C.load_jsonl("D24", f"{BENCH}/{TASK_DIR[t]}/tests.jsonl")

    def ev_one(it):
        t = it["task"]
        if t in orc:
            return evaluate_program(t, it["code"], orc[t], hidden[t], checks[t])
        if t in hidden:
            o = {"cases": [], "oracle": {}, "fastest": {}}
            return evaluate_program(t, it["code"], o, hidden[t], checks[t])
        return None
    with ThreadPoolExecutor(max_workers=5) as ex:
        evs = list(ex.map(ev_one, items))
    for it, e in zip(items, evs):
        it["stress"] = e
        it["stress_text"] = stress_text(e)
    logger.info(f"F2 done in {time.time() - t0:.0f} s: " + ", ".join(
        f"{it['blind_id']}:{'ok' if (it['stress'] or {}).get('all_pass') else 'x'}" for it in items))
    # F3 nearest known solutions
    ks = [k for k in C.load_jsonl("D18", "inputs/known_solutions.jsonl")]
    pools: dict[str, list[dict]] = {}
    for t in set(i["task"] for i in items):
        pool = []
        if t in TASK_DIR:
            for p in sorted(C.dep_path("D24", f"{BENCH}/{TASK_DIR[t]}/references").glob("*.py")):
                pool.append({"ref_id": f"reference:{p.stem}", "code": p.read_text()})
            fp = C.load_jsonl("D24", f"{BENCH}/{TASK_DIR[t]}/forced_programs.jsonl")
            seen_c = set()
            for r in fp:
                if str(r.get("passed")) != "True":
                    continue
                key = ast.dump(ast.parse(r["code"])) if r["code"] else ""
                if key in seen_c:
                    continue
                seen_c.add(key)
                pool.append({"ref_id": f"forced:{r['forced_mode']}:{r['sample_id'].split(':')[-1]}", "code": r["code"]})
        for j, k in enumerate(x for x in ks if x["task"] == t):
            pool.append({"ref_id": f"known:{k.get('source')}:{k.get('mode_hint')}:{j}", "code": k["code"]})
        pools[t] = pool
    import difflib
    t1 = time.time()
    shortlists = []
    for it in items:
        pl = pools[it["task"]]
        ca = _canon_src(it["code"])
        ratios = [(difflib.SequenceMatcher(None, ca, _canon_src(p["code"]), autojunk=False).ratio(), j) for j, p in enumerate(pl)]
        ratios.sort(reverse=True)
        keep = {j for _, j in ratios[:SHORTLIST]} | {j for j, p in enumerate(pl) if p["ref_id"].startswith("reference:")}
        shortlists.append(sorted(keep))
        it["nearest_difflib"] = [{"ref_id": pl[j]["ref_id"], "ratio": v} for v, j in ratios[:3]]
    jobs = [(it["code"], [pools[it["task"]][j]["code"] for j in sl]) for it, sl in zip(items, shortlists)]
    with ProcessPoolExecutor(max_workers=5, mp_context=mp.get_context("spawn")) as ex:
        dists = list(ex.map(_ted_job, jobs, chunksize=1))
    for it, d, sl in zip(items, dists, shortlists):
        best = sorted(d, key=lambda x: x[1])[:3]
        pl = pools[it["task"]]
        it["nearest"] = [{"ref_id": pl[sl[j]]["ref_id"], "dist": dd, "code": pl[sl[j]]["code"]} for j, dd in best]
        it["ted_shortlist_n"] = len(sl)
    logger.info(f"F3 tree edit distances in {time.time() - t1:.0f} s; pool sizes { {t: len(p) for t, p in pools.items()} }")
    # F5 judges
    specs_all = {t: C.load_json("D24", f"{BENCH}/{TASK_DIR[t]}/spec.json") for t in set(i["task"] for i in items) if t in TASK_DIR}
    judge_items = [it for it in items if it["task"] in specs_all]
    for it in judge_items:
        it["messages"] = build_prompt(it, specs_all[it["task"]], it["nearest"])
    est_in = sum(len(json.dumps(it["messages"])) / 3.6 for it in judge_items)
    est_cost = est_in * (3 * 0.4e-6 + 0.6e-6) + len(judge_items) * 150 * (3 * 2e-6 + 2.5e-6)
    logger.info(f"F5: {len(judge_items)} items, ~{est_in / 1e3:.0f}k input tokens per call set, estimated cost ${est_cost:.3f}")
    budget = Budget(max_usd)
    if est_cost > max_usd:
        raise RuntimeError(f"estimated judge cost {est_cost:.2f} exceeds cap {max_usd}")
    jres = asyncio.run(run_judges(judge_items, budget))
    for it in judge_items:
        r = jres.get(it["blind_id"], {})
        p = [x.get("parsed", {}).get("class", "UNPARSED") if "parsed" in x else "ERROR" for x in r.get(PRIMARY, [])]
        s = [x.get("parsed", {}).get("class", "UNPARSED") if "parsed" in x else "ERROR" for x in r.get(SECOND, [])]
        it["judge_primary_calls"] = p
        it["judge_primary"] = majority(p)
        it["judge_second"] = s[0] if s else "ERROR"
        prim0 = next((x["parsed"] for x in r.get(PRIMARY, []) if "parsed" in x), {})
        sec0 = next((x["parsed"] for x in r.get(SECOND, []) if "parsed" in x), {})
        it["judge_primary_named"] = prim0.get("named_technique", "")
        it["judge_primary_reason"] = prim0.get("reason", "")
        it["judge_primary_closest"] = prim0.get("closest_reference_id", "")
        it["judge_second_named"] = sec0.get("named_technique", "")
        it["judge_second_reason"] = sec0.get("reason", "")
    logger.info(f"F5 spend ${budget.spent:.4f} over {budget.n_calls} calls (stop={budget.stop})")
    # F6 agreement
    core = [it for it in judge_items if it["kind"] == "disputed_14"]
    ctrl = [it for it in judge_items if it["kind"].startswith("control")]
    both = core + ctrl

    def agree(rows, key):
        tr = [r["truth"] for r in rows]
        pr = [r[key] for r in rows]
        k = sum(a == b for a, b in zip(tr, pr))
        bt = ["NOVEL" if x == "NOVEL_ALGORITHM" else "NOT" for x in tr]
        bp = ["NOVEL" if x == "NOVEL_ALGORITHM" else "NOT" for x in pr]
        kb = sum(a == b for a, b in zip(bt, bp))
        kap_b = X.cohen_kappa(bt, bp)
        return {"n": len(rows), "raw_agree_4class": k / len(rows) if rows else math.nan,
                "raw_agree_4class_cp95": X.clopper_pearson(k, len(rows)),
                "kappa_4class": X.cohen_kappa(tr, pr), "ac1_4class": X.gwet_ac1(tr, pr, CLASSES),
                "raw_agree_binary": kb / len(rows) if rows else math.nan, "raw_agree_binary_cp95": X.clopper_pearson(kb, len(rows)),
                "kappa_binary": kap_b, "kappa_binary_flag": "undefined (constant reference and constant judge)" if not math.isfinite(kap_b)
                else ("0 by construction against a constant reference" if len(set(bt)) == 1 else "defined"),
                "ac1_binary": X.gwet_ac1(bt, bp, ["NOVEL", "NOT"])}
    f6 = {}
    for key in ("judge_primary", "judge_second"):
        f6[key] = {"disputed_14": agree(core, key), "controls_10": agree(ctrl, key), "all_24": agree(both, key)}
        f6[key]["all_24"]["kappa_bootstrap_ci95"] = X.kappa_bootstrap([r["truth"] for r in both], [r[key] for r in both])
        f6[key]["controls_correct"] = sum(r[key] == r["truth"] for r in ctrl)
        f6[key]["gate_pass"] = f6[key]["controls_correct"] >= 8
    f6["fleiss_primary_3calls"] = X.fleiss_kappa([it["judge_primary_calls"] for it in judge_items if len(it["judge_primary_calls"]) == 3])
    f6["primary_unanimous_share"] = float(np.mean([len(set(it["judge_primary_calls"])) == 1 for it in judge_items]))
    f6["inter_judge_kappa_all"] = X.cohen_kappa([it["judge_primary"] for it in judge_items], [it["judge_second"] for it in judge_items])
    f6["inter_judge_raw_all"] = float(np.mean([it["judge_primary"] == it["judge_second"] for it in judge_items]))
    k_novel = sum(it["judge_primary"] == "NOVEL_ALGORITHM" for it in core)
    k_novel2 = sum(it["judge_second"] == "NOVEL_ALGORITHM" for it in core)
    ext_items = [it for it in judge_items if it["kind"] == "extension_known_outside"]
    f6["extension"] = {"n": len(ext_items), "primary_novel": sum(it["judge_primary"] == "NOVEL_ALGORITHM" for it in ext_items),
                       "primary_agree_manual": sum(it["judge_primary"] == it["truth"] for it in ext_items)}
    # F7 final manual read (written by the executor after reading every program called novel; audit/final_read.json)
    fr_path = WS / "audit" / "final_read.json"
    final_read = json.loads(fr_path.read_text()) if fr_path.exists() else {}
    flagged = [it for it in core if it["judge_primary"] == "NOVEL_ALGORITHM" or it["judge_second"] == "NOVEL_ALGORITHM"]
    unresolved = [it["blind_id"] for it in flagged if it["blind_id"] not in final_read]
    for it in core:
        fr = final_read.get(it["blind_id"])
        it["final_class"] = fr["final_class"] if fr else it["truth"]
        it["final_verdict"] = fr["verdict"] if fr else "manual class kept (no final read recorded)"
    final_novel = sum(it["final_class"] == "NOVEL_ALGORITHM" for it in core)
    manual_corrected = [{"blind_id": it["blind_id"], "manual_class": it.get("manual_class"), "final_class": it["final_class"],
                         "verdict": it["final_verdict"]} for it in core if it["final_class"] != it["truth"]]
    contested = [it for it in ctrl if it.get("control_of") == "repeated_max_selection_textbook"]
    alt_ok = {}
    for key in ("judge_primary", "judge_second"):
        alt_ok[key] = sum((r[key] == r["truth"]) or (r in contested and r[key] == "CATALOGUE_VARIANT") for r in ctrl)
    f6["contested_control"] = {"control": "repeated linear max-selection (top-k frequent)", "truth_by_construction":
                               "KNOWN_OUTSIDE_CATALOGUE", "iteration5_manual_reading_of_same_technique": "CATALOGUE VARIANT "
                               "(sort_by_count by repeated max selection, program P10)", "judge_calls": {k: [r[k] for r in contested] for k in ("judge_primary", "judge_second")},
                               "controls_correct_under_manual_convention": alt_ok}
    f6["final_agreement_with_final_read"] = {key: sum(it[key] == it["final_class"] for it in core) for key in ("judge_primary", "judge_second")}
    used_models = grep_used_models()
    out = {"F1": {"n": f1["n"], "by_task": dict(f1["by_task"]), "manual": dict(f1["manual"])},
           "judges": {"primary": PRIMARY, "second": SECOND, "used_before_in_run": used_models,
                      "new_family_check": not any(m.split("/")[0] in ("mistralai", "moonshotai") for m in used_models)},
           "oracle": {t: {"n_cases": len(o["cases"]), "n_unanimous": len(o["oracle"]), "fastest": o["fastest"],
                          "ref_runs": o["ref_runs"]} for t, o in orc.items()},
           "items": [{k: v for k, v in it.items() if k not in ("messages",)} for it in items],
           "F6": f6, "readj_novel_k": k_novel, "readj_novel_k_second": k_novel2,
           "flagged_for_final_read": [it["blind_id"] for it in flagged], "final_read": final_read,
           "final_read_unresolved": unresolved, "final_novel_count": final_novel, "manual_class_corrected": manual_corrected,
           "spend_usd": budget.spent, "n_calls": budget.n_calls, "tokens_in": budget.tokens_in,
           "tokens_out": budget.tokens_out, "budget_stop": budget.stop, "seconds": time.time() - t0}
    C.write_csv("tables/novelty_readjudication.csv", [{
        "blind_id": it["blind_id"], "kind": it["kind"], "task": it["task"], "truth": it["truth"],
        "manual_class": it.get("manual_class"), "judge_primary": it.get("judge_primary"),
        "judge_primary_calls": it.get("judge_primary_calls"), "judge_primary_named": it.get("judge_primary_named"),
        "judge_second": it.get("judge_second"), "judge_second_named": it.get("judge_second_named"),
        "hidden_pass": (it["stress"] or {}).get("hidden_pass") if it.get("stress") else None,
        "stress_groups": (it["stress"] or {}).get("stress_groups") if it.get("stress") else None,
        "nearest_ted": [(n["ref_id"], round(n["dist"], 3)) for n in it["nearest"]],
        "code_sha256": it["code_sha256"], "source": it["source"]} for it in items])
    logger.info(f"F6: primary gate {f6['judge_primary']['controls_correct']}/10, second gate "
                f"{f6['judge_second']['controls_correct']}/10; k novel (primary) {k_novel} of 14, second {k_novel2}")
    f_corrections(ledger, out)
    return out


def grep_used_models() -> list[str]:
    pat = re.compile(r"(google|openai|deepseek|anthropic|mistralai|moonshotai|z-ai|qwen|x-ai|cohere)/[A-Za-z0-9._:-]+")
    found = set()
    for aid in C.DEPS:
        root = C.dep_dir(aid) / "results"
        if not root.exists():
            continue
        for p in list(root.glob("costs.json")) + list(root.glob("openrouter_cost_paths.json")) + list(root.glob("novelty_audit*.json")):
            try:
                found.update(m.group(0) for m in pat.finditer(p.read_text()))
            except OSError:
                continue
    return sorted(found)


def f_corrections(ledger: C.Ledger, out: dict) -> None:
    k = out["readj_novel_k"]
    fin = out["final_novel_count"]
    f6 = out["F6"]["judge_primary"]
    gate = "passed" if f6["gate_pass"] else "failed (verdicts descriptive only)"
    cc = out["F6"]["contested_control"]["controls_correct_under_manual_convention"]
    mc = out["manual_class_corrected"]
    summary = (f"judges 14 of 48, manual 0, second adjudication {k} of 14 (Mistral Medium 3.1, three calls at temperature 0, "
               f"control gate {f6['controls_correct']} of 10, {gate}; Kimi K2 second view {out['readj_novel_k_second']} of 14), "
               f"final count after the executor's full read {fin}; the contested control, repeated maximum selection for top-k "
               f"frequent, which the iteration-5 manual pass itself classed as a catalogue variant, was called "
               f"{'/'.join(out['F6']['contested_control']['judge_calls']['judge_primary']).lower().replace('_', ' ')} by Mistral and "
               f"{'/'.join(out['F6']['contested_control']['judge_calls']['judge_second']).lower().replace('_', ' ')} by Kimi "
               f"(Mistral gate {cc['judge_primary']} of 10 under that convention)" +
               (f"; the final read corrects {len(mc)} manual class" + ("es" if len(mc) > 1 else "") + " (" +
                "; ".join(f"{m['manual_class']} to {m['final_class']}" for m in mc) + "), none to novel" if mc else ""))
    old = ("In iteration 5, 130 correct programs outside the catalogue, from the base model, the transplant, the panels, the "
           "knobs and Gemma, were all labeller misses, known techniques outside the frozen catalogue, catalogue variants or "
           "degenerate.")
    agr = f6["disputed_14"]
    new = (old + " A second blind adjudication in iteration 6 re-read the 14 transplant programs that two of three judges "
           f"had called novel ({summary}). Each program was stress-tested in a sandbox at the specification's maximum size and "
           "on adversarial cases, shown with its three nearest known solutions by tree edit distance, and judged by model "
           "families the run had not used, with ten blinded controls of known class; raw agreement with the manual verdict on "
           f"the 14 was {agr['raw_agree_4class']:.2f} (95% {agr['raw_agree_4class_cp95'][0]:.2f} to {agr['raw_agree_4class_cp95'][1]:.2f}), "
           f"Gwet's AC1 {agr['ac1_4class']:.2f}; Cohen's kappa on novel against not novel is {agr['kappa_binary_flag']} "
           "(iteration-6 correction; tables/novelty_readjudication.csv).")
    vals = [C.val("judge over-calls (14 of 48)", 14, out["F1"]["n"], C.prov("D24", "results/novelty_audit.json"), "count"),
            C.val("second adjudication novel k", None, k, "tables/novelty_readjudication.csv", "count"),
            C.val("final novel count", 0, fin, "audit/final_read.json", "count")]
    fl = [it for it in out["items"] if it["blind_id"] in out["flagged_for_final_read"]]
    if fl:
        new = new + " The novel calls, each read in full: " + "; ".join(
            f"{it['blind_id']} ({it['task']}; {sum(c == 'NOVEL_ALGORITHM' for c in it.get('judge_primary_calls', []))} of 3 Mistral calls"
            f"{', Kimi too' if it.get('judge_second') == 'NOVEL_ALGORITHM' else ''}; technique named by the judge: "
            f"'{it.get('judge_primary_named') or 'none'}', reason: '{it.get('judge_primary_reason', '')}'; hidden tests "
            f"{(it.get('stress') or {}).get('hidden_pass')} of {(it.get('stress') or {}).get('hidden_n')}, stress groups "
            f"{'all pass' if all(((it.get('stress') or {}).get('stress_groups') or {}).values()) else 'not all pass'}; final read: "
            f"{it.get('final_verdict')})" for it in fl) + "."
    ledger.add("0f-F7", old, new, vals)
    old = ("every correct program outside the catalogue that the run produced has been read by two blind judges and the "
           "executor, and none was new.")
    ledger.add("0f-F7", old, old[:-1] + f"; the 14 that judges over-called in iteration 5 were re-adjudicated blind in "
               f"iteration 6 ({summary}).")
