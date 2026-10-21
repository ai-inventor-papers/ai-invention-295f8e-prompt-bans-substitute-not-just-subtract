"""Unified mechanism-level labeller over the two frozen pipelines.

Bench tasks (T03/T04/T06/T10): exp11 bench/common (hidden tests, AST rules, runtime tracer + probes, combined
label = runtime when it agrees with AST or AST says unknown; otherwise the blind judge j1 gemini-2.5-flash-lite on
name-scrubbed code).  Path tasks (T1/T2): exp1 canonical suite as copied by exp8 (tests + runtime probes, runtime
primary, AST second, blind judge gpt-4.1-mini on disagreement/unknown).  Both are used unchanged; only the
orchestration, caching and budget tracking are new.  Labels: catalogue modes, 'other', 'invalid' (no code block,
unparseable, or no solve), never dropped.
"""

from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from config import BENCH_DIR, DATA, TASKS, append_jsonl, read_jsonl, sha256_text
from judge import JUDGE_LABEL_MODELS, budget, call_llm

LABEL_CACHE = DATA / "label_cache.jsonl"
_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] | None = None
_CASES: dict[str, list[dict]] = {}
WORKERS = 5


def _cache() -> dict[str, dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        _CACHE = {r["key"]: r for r in read_jsonl(LABEL_CACHE)}
    return _CACHE


def _bench_cases(task: str) -> list[dict]:
    from bench.common.testgen import read_tests

    if task not in _CASES:
        _CASES[task] = read_tests(BENCH_DIR / TASKS[task]["task_id"] / "tests.jsonl")
    return _CASES[task]


def extract(task: str, text: str) -> tuple[str | None, str]:
    """Each pipeline's own extractor (bench: first python block; suite: python block, any block, raw text)."""
    if TASKS[task]["family"] == "bench":
        from bench.common.harness import extract_code

        c = extract_code(text)
        return c, ("python_block" if c is not None else "no_code")
    from labeller.extract import extract_code as sx

    return sx(text)


def _mech_bench(task: str, code: str) -> dict[str, Any]:
    from bench.common.astrules import ast_label
    from bench.common.harness import run_tests, syntax_ok
    from bench.common.probes import run_trace
    from bench.common.rtrules import runtime_label

    bt = TASKS[task]["bench"]
    if code is None or not syntax_ok(code) or "def solve" not in code:
        return {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid"}
    tr = run_tests(code, bt, _bench_cases(task))
    trace = run_trace(code, bt)
    return {"valid": True, "passed": bool(tr["passed"]), "n_pass": tr["n_pass"], "n_cases": tr["n_cases"],
            "first_fail": tr["first_fail"], "load_error": tr["load_error"],
            "ast_label": ast_label(bt, code), "runtime_label": runtime_label(bt, trace),
            "trace_error": trace.get("error")}


def _mech_path(task: str, code: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    st = TASKS[task]["suite"]
    if code is None:
        return {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid"}
    try:
        compile(code, "<c>", "exec")
    except (SyntaxError, ValueError):
        return {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid"}
    if "def solve" not in code:
        return {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid"}
    ev = evaluate_program(st, code)
    t = ev["tests"]
    rl, rwhy, _ = runtime_rules.label(st, ev["probes"])
    al, awhy, _ = ast_rules.label(code, st)
    return {"valid": True, "passed": bool(t.get("passed")), "n_pass": t.get("n_passed"), "fail_case": t.get("fail_case"),
            "test_error": t.get("error"), "runtime_label": rl, "runtime_reason": rwhy, "ast_label": al,
            "ast_reason": awhy}


def needs_judge(task: str, m: dict[str, Any]) -> bool:
    if not m.get("valid"):
        return False
    rt, al = m["runtime_label"], m["ast_label"]
    if TASKS[task]["family"] == "bench":
        return rt == "unknown" or (al != "unknown" and al != rt)
    from labeller.combine import needs_judge as nj

    return nj(rt, al)


def judge_prompt(task: str, code: str) -> str:
    if TASKS[task]["family"] == "bench":
        from bench.common.judge import Judge
        from bench.common.scrub import scrub_code

        return Judge.prompt(TASKS[task]["bench"], scrub_code(code)[0])
    from labeller.judge import judge_prompt as jp

    return jp(TASKS[task]["suite"], code)


def parse_judge(task: str, txt: str) -> str | None:
    import re

    if TASKS[task]["family"] == "bench":
        valid = set(TASKS[task]["catalogue"]) | {"other"}
        label = None
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            try:
                label = str(json.loads(m.group(0)).get("label", "")).strip()
            except json.JSONDecodeError:
                label = None
        if label not in valid:
            mm = re.search(r'"label"\s*:\s*"([a-z_]+)"', txt)
            label = mm.group(1) if mm and mm.group(1) in valid else ("other" if label else None)
        return label
    from labeller.judge import parse_judge as pj

    return pj(txt, TASKS[task]["suite"])["label"]


def combine(task: str, m: dict[str, Any], judge_label: str | None) -> tuple[str, str]:
    if not m.get("valid"):
        return "invalid", "extraction"
    rt, al = m["runtime_label"], m["ast_label"]
    if TASKS[task]["family"] == "bench":
        if not needs_judge(task, m):
            return rt, ("runtime+ast" if al == rt else "runtime(ast_unknown)")
        if judge_label:
            return judge_label, "judge"
        if rt != "unknown":
            return rt, "runtime_fallback"
        return (al if al not in ("unknown", "invalid") else "other"), "ast_fallback"
    from labeller.combine import combine as sc

    lbl, src = sc(rt, al, {"label": judge_label} if judge_label else None)
    if lbl in ("unknown", "inconsistent", "no_code"):
        lbl = "other"
    return lbl, src


async def _judge_all(items: list[tuple[str, str, str]]) -> dict[str, str | None]:
    sem = asyncio.Semaphore(16)

    async def one(key: str, task: str, code: str):
        model = JUDGE_LABEL_MODELS[TASKS[task]["family"]]
        txt, _ = await call_llm(sem, model, judge_prompt(task, code), purpose="labeller_judge", max_tokens=200,
                                cache_key=f"lj|{model}|{key}")
        return key, (parse_judge(task, txt) if txt else None)

    res = await asyncio.gather(*[one(k, t, c) for k, t, c in items])
    return dict(res)


def label_programs(items: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    """items: [{'task', 'text'} or {'task', 'code'}] -> label records (input order).  Cached by (task, code sha)."""
    cache = _cache()
    prepared = []
    for it in items:
        t = it["task"]
        if "code" in it:
            code, how = it["code"], it.get("extract_method", "given")
        else:
            code, how = extract(t, it.get("text") or "")
        key = f"{t}|{sha256_text(code or '')}"
        prepared.append((t, code, how, key))
    todo = {}
    for t, code, how, key in prepared:
        if key not in cache and key not in todo:
            todo[key] = (t, code)

    def work(kv):
        key, (t, code) = kv
        try:
            m = _mech_bench(t, code) if TASKS[t]["family"] == "bench" else _mech_path(t, code)
        except Exception as e:  # noqa: BLE001 - record as an error label, never silently drop
            logger.error(f"mechanical labelling failed {key}: {e}")
            m = {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid",
                 "error": str(e)[:200]}
        return key, t, m

    if todo:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            mech = list(ex.map(work, list(todo.items())))
        need = [(k, t, todo[k][1]) for k, t, m in mech if needs_judge(t, m)]
        jl: dict[str, str | None] = {}
        if need and use_judge and not budget().stopped:
            jl = asyncio.run(_judge_all(need))
        new_rows = []
        for k, t, m in mech:
            j = jl.get(k)
            lbl, src = combine(t, m, j)
            rec = {"key": k, "task": t, **m, "judge_label": j,
                   "judge_skipped": bool(needs_judge(t, m) and j is None), "label": lbl, "labeller_source": src}
            cache[k] = rec
            new_rows.append(rec)
        with _LOCK:
            append_jsonl(LABEL_CACHE, new_rows)
        logger.info(f"labelled {len(todo)} new unique programs ({len(need)} judged)")
    out = []
    for t, code, how, key in prepared:
        r = dict(cache[key])
        r["code"] = code
        r["code_sha256"] = sha256_text(code or "")
        r["extract_method"] = how
        out.append(r)
    return out
