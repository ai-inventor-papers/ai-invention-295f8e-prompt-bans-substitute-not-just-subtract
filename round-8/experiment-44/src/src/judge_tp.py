#!/usr/bin/env python3
"""Strategy-blind LLM judges (OpenRouter). A judge sees the task DESCRIPTION, the 10 class definitions plus 'other'
and the code -- never the configuration or arm. Output JSON {label, other_name, confidence, rationale}.

Gate (Stage 0): 10 controls = one T1 reference per class with identifiers renamed and comments stripped; a judge
passes at >= 8/10. Cached by (model, sha256(code)). Every response's usage.cost goes to the shared ledger. The
first HTTP 403 'AI Inventor per-run OpenRouter budget' stops every queued and in-flight call of the batch (checked
again after each call acquires its semaphore slot); the batch is never rerun.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import json
import os
import re
from typing import Any

import aiohttp
from loguru import logger

from common import (BUDGET_MSG, CANON_ORDER, COST_CAP_USD, DATA, INPUTS, JUDGES, KNOWN_OUTSIDE, MODE_DEFINITIONS,
                    RESULTS, T1_DESCRIPTION, add_cost, append_jsonl, read_json, read_jsonl, sha256_text, total_cost,
                    trunc, write_json)

CACHE = DATA / "judge_cache.jsonl"
PROMPT_VERSION = "tp-v1"
LABELLER_JUDGE = "deepseek/deepseek-chat-v3.1"   # gated (9/10); the planned judge a failed its gate (7/10)
LABELS = CANON_ORDER + ["other"]


class BudgetStop(RuntimeError):
    pass


def judge_prompt(code: str) -> str:
    cat = "\n".join(f"- {m}: {MODE_DEFINITIONS[m]}" for m in CANON_ORDER)
    return (
        f"TASK DESCRIPTION:\n{T1_DESCRIPTION}\n\n"
        f"CATALOGUE OF ALGORITHM LABELS:\n{cat}\n- other: anything else, e.g. {', '.join(KNOWN_OUTSIDE)}, or a "
        "program that does not implement any listed algorithm.\n\n"
        f"PROGRAM:\n```python\n{code}\n```\n\n"
        "Which label best describes the search strategy the program ACTUALLY implements or attempts? Judge the "
        "code's mechanism (data structures and exploration order), not its comments, variable names or claims. Label "
        "the listed algorithm whose mechanism the code attempts even if the program is buggy, incomplete or fails; use "
        "'other' only when the mechanism matches none of the listed algorithms. If you answer 'other', name the known "
        "algorithm it implements in other_name (or 'unknown' if it is not a known algorithm). Answer with only a JSON "
        'object: {"label": <one label id from the catalogue above>, "other_name": <string or null>, '
        '"confidence": <number between 0 and 1>, "rationale": <one short sentence>}'
    )


def parse_judge(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        lab = re.search(r'"label"\s*:\s*"([a-z_]+)"', text)
        if not lab:
            return None
        d = {"label": lab.group(1)}
    lab = str(d.get("label", "")).strip().lower()
    alias = {"dijkstra": "dijkstra_unit", "a*": "astar", "a_star": "astar", "greedy": "gbfs", "ida*": "idastar",
             "bidirectional_bfs": "bibfs", "bidirectional_astar": "biastar"}
    lab = alias.get(lab, lab)
    if lab not in LABELS:
        return None
    return {"label": lab, "other_name": d.get("other_name"), "confidence": d.get("confidence"),
            "rationale": trunc(d.get("rationale", ""), 300)}


def load_cache() -> dict[str, dict[str, Any]]:
    return {r["key"]: r for r in read_jsonl(CACHE)}


async def _one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: asyncio.Event, model: str, code: str,
               purpose: str) -> dict[str, Any] | None:
    async with sem:
        if stop.is_set():
            return None
        if total_cost() >= COST_CAP_USD:
            stop.set()
            logger.error(f"artifact cost cap {COST_CAP_USD} reached; stopping judge batch")
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        body = {"model": model, "messages": [{"role": "user", "content": judge_prompt(code)}], "temperature": 0.0,
                "max_tokens": 400, "usage": {"include": True}}
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        for attempt in range(4):
            if stop.is_set():
                return None
            try:
                async with session.post(url, json=body, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=75)) as resp:
                    txt = await resp.text()
                    if resp.status == 403 and BUDGET_MSG in txt:
                        stop.set()
                        add_cost(f"judge:{purpose}", 0.0, refused=True)
                        logger.error(f"BUDGET 403 -> stopping judge batch: {trunc(txt, 200)}")
                        return None
                    if resp.status in (429, 500, 502, 503, 504) or resp.status >= 520:
                        await asyncio.sleep(2 ** attempt + 1)
                        continue
                    if resp.status != 200:
                        logger.warning(f"judge {model} HTTP {resp.status}: {trunc(txt, 200)}")
                        return None
                    d = json.loads(txt)
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"judge {model} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(2 ** attempt + 1)
                continue
            cost = float((d.get("usage") or {}).get("cost") or 0.0)
            add_cost(f"judge:{purpose}", cost)
            try:
                content = d["choices"][0]["message"].get("content") or ""
            except (KeyError, IndexError, TypeError):
                content = ""
            parsed = parse_judge(content)
            logger.debug(f"judge {model} -> {trunc(content, 200)}")
            if parsed is None:
                await asyncio.sleep(1)
                continue
            parsed.update({"model": model, "cost": cost})
            return parsed
        return None


async def _batch(codes: list[str], model: str, purpose: str, concurrency: int = 24) -> list[dict[str, Any] | None]:
    sem = asyncio.Semaphore(concurrency)
    stop = asyncio.Event()
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(_one(session, sem, stop, model, c, purpose)) for c in codes]
        res = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for r in res:
        if isinstance(r, BaseException):
            logger.error(f"judge task exception {type(r).__name__}: {r}")
            out.append(None)
        else:
            out.append(r)
    return out


def judge_codes(codes: list[str], model: str, purpose: str) -> list[dict[str, Any] | None]:
    """Cached, budget-safe batch judging. Returns one dict (or None) per code, in order."""
    cache = load_cache()
    keys = [f"{PROMPT_VERSION}|{model}|{sha256_text(c)}" for c in codes]
    todo = {k: c for k, c in zip(keys, codes) if k not in cache}
    if todo:
        logger.info(f"judge {model} [{purpose}]: {len(todo)} new calls ({len(codes) - len(todo)} cached)")
        tk = list(todo)
        res = asyncio.run(_batch([todo[k] for k in tk], model, purpose))
        for k, r in zip(tk, res):
            if r is not None:
                r["key"] = k
                append_jsonl(CACHE, r)
                cache[k] = r
    return [cache.get(k) for k in keys]


# ---------------------------------------------------------------------------------------------- gate controls
_KEEP = set(dir(builtins)) | {"solve", "grid", "start", "goal", "heapq", "collections", "deque", "math", "itertools",
                              "functools", "sys", "queue", "Queue", "heappush", "heappop", "heapify", "defaultdict",
                              "self", "cls", "inf", "PriorityQueue", "lru_cache", "count", "Counter", "OrderedDict",
                              "namedtuple", "typing", "List", "Tuple", "Optional", "Dict", "Set", "LifoQueue",
                              "SimpleQueue", "bisect", "dataclass", "dataclasses", "field", "random", "time"}


class _Renamer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.map: dict[str, str] = {}

    def _new(self, name: str, prefix: str) -> str:
        if name in _KEEP or name.startswith("__"):
            return name
        if name not in self.map:
            self.map[name] = f"{prefix}{len(self.map) + 1}"
        return self.map[name]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = self._new(node.name, "f")
        node.body = [b for b in node.body if not (isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None),
                                                                                        ast.Constant)
                                                   and isinstance(b.value.value, str))] or [ast.Pass()]
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self._new(node.arg, "v")
        node.annotation = None
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self._new(node.id, "v")
        return node

    def visit_Global(self, node: ast.Global) -> ast.AST:
        node.names = [self._new(n, "v") for n in node.names]
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.AST:
        node.names = [self._new(n, "v") for n in node.names]
        return node


def rename_identifiers(code: str) -> str:
    """Rename every user identifier (functions except solve, variables, arguments except solve's) and strip
    comments and docstrings (ast.unparse drops comments). Attribute names and imported modules are kept."""
    tree = ast.parse(code)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {(a.asname or a.name).split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported |= {a.asname or a.name for a in n.names}
    _KEEP.update(imported)
    out = _Renamer().visit(tree)
    ast.fix_missing_locations(out)
    return ast.unparse(out) + "\n"


def run_gate() -> dict[str, Any]:
    """10 controls (one reference per class), each judge passes at >= 8/10; third judge = first of JUDGES['c']
    that passes."""
    from label_tp import ref_mode  # noqa: F401 - imported lazily to keep modules decoupled

    refs = sorted((INPUTS / "exp9" / "tasks" / "t1_grid" / "references").glob("*.py"))
    by_cls: dict[str, str] = {}
    for p in refs:
        cls = ref_mode(p.name)
        if cls not in by_cls:
            by_cls[cls] = p.read_text()
    controls = []
    for cls in CANON_ORDER:
        code = rename_identifiers(by_cls[cls])
        controls.append({"class": cls, "code": code, "sha256": sha256_text(code)})
    out: dict[str, Any] = {"controls": [{"class": c["class"], "sha256": c["sha256"]} for c in controls],
                           "threshold": 8, "judges": {}}
    for role, model in (("a", JUDGES["a"]), ("b", JUDGES["b"])) + tuple(("c", m) for m in JUDGES["c"]):
        res = judge_codes([c["code"] for c in controls], model, purpose="gate")
        per = [{"class": c["class"], "label": (r or {}).get("label"), "ok": (r or {}).get("label") == c["class"]}
               for c, r in zip(controls, res)]
        score = sum(p["ok"] for p in per)
        out["judges"][model] = {"role": role, "score": score, "passed": score >= 8, "per_control": per}
        logger.info(f"judge gate {role} {model}: {score}/10")
        if role == "c" and score >= 8:
            break
    gated = [m for m, v in out["judges"].items() if v["passed"]]
    out["third_judge"] = next((m for m in JUDGES["c"] if out["judges"].get(m, {}).get("passed")), None)
    out["gated_pair"] = [m for m in (JUDGES["a"], JUDGES["b"]) if m in gated]
    out["any_passed"] = bool(gated)
    write_json(RESULTS / "judge_gate.json", out)
    # write the renamed controls for audit
    write_json(RESULTS / "judge_gate_controls.json", controls)
    return out


def gate_info() -> dict[str, Any]:
    p = RESULTS / "judge_gate.json"
    return read_json(p) if p.exists() else {}
