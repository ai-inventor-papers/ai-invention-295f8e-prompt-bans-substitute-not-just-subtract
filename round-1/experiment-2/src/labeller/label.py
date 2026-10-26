#!/usr/bin/env python3
"""Labeller: hidden-test runner + runtime tracer (primary) + AST rules (secondary) + blind LLM judge.

label_rows(rows) adds {label, labeller_source, passed, wall_s, ...} to each generated-program row.
Combination: runtime and AST both confident and agreeing -> 'runtime+ast'; otherwise the blind judge
(comments/docstrings stripped, catalogue + 'other') decides -> 'judge'. If the OpenRouter budget is hit,
the runtime (else AST) label is kept with labeller_source='runtime_only_unadjudicated'.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tasks"))
sys.path.insert(0, str(ROOT / "labeller"))
from common import CATALOGUE, ONE_LINE_DEF, SPEC, append_jsonl  # noqa: E402
from rules import ast_label, runtime_label, strip_comments  # noqa: E402
from tasklib import run_hidden_tests, run_trace  # noqa: E402

JUDGE_MODEL = "anthropic/claude-haiku-5.5"
GOLD_JUDGES = ["anthropic/claude-haiku-5.5", "openai/gpt-4.1-mini"]
GOLD_RESOLVER = "deepseek/deepseek-v4.1-flash-1017"
JUDGE_BUDGET_USD = 1.0
SPEND_FILE = ROOT / "logs" / "openrouter_spend.jsonl"
_lock = threading.Lock()


class BudgetExhausted(Exception):
    pass


def spent_usd() -> float:
    tot = 0.0
    if SPEND_FILE.exists():
        for line in SPEND_FILE.read_text().splitlines():
            if line.strip():
                tot += float(json.loads(line).get("cost", 0.0))
    return tot


# ------------------------------------------------------------------------------------------ CPU stage


def cpu_label_one(task: str, code: str | None) -> dict:
    if not code:
        return {"passed": False, "wall_s": 0.0, "fail_kind": "no_code", "rt_label": None, "rt_conf": False,
                "ast_label": None, "ast_conf": False, "rt_ev": {}, "ast_ev": {}}
    tr = run_hidden_tests(code, task)
    trace = run_trace(code, task)
    rl, rc, rev = runtime_label(task, trace)
    al, ac, aev = ast_label(task, code)
    return {"passed": tr["passed"], "wall_s": tr["wall_s"], "fail_kind": tr["fail_kind"], "fail_index": tr["fail_index"],
            "rt_label": rl, "rt_conf": rc, "ast_label": al, "ast_conf": ac, "rt_ev": rev, "ast_ev": aev}


def cpu_stage(rows: list[dict], workers: int, logger) -> None:
    """Run tests + trace + rules for every row (deduplicated by (task, code_sha256))."""
    uniq: dict[tuple, dict] = {}
    for r in rows:
        key = (r["task"], r.get("code_sha256") or f"none-{id(r)}")
        uniq.setdefault(key, r)
    keys = list(uniq)
    t0 = time.time()
    results: dict[tuple, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(cpu_label_one, k[0], uniq[k].get("code")): k for k in keys}
        for i, f in enumerate(futs):
            k = futs[f]
            try:
                results[k] = f.result()
            except (OSError, RuntimeError, ValueError) as e:
                logger.error(f"cpu label failed for {k}: {e}")
                results[k] = {"passed": False, "wall_s": 0.0, "fail_kind": f"labeller_error:{e}", "rt_label": None,
                              "rt_conf": False, "ast_label": None, "ast_conf": False, "rt_ev": {}, "ast_ev": {}}
    for r in rows:
        key = (r["task"], r.get("code_sha256") or f"none-{id(r)}")
        r.update(results[key])
    logger.info(f"CPU labelling: {len(keys)} unique programs in {time.time() - t0:.0f}s")


# ------------------------------------------------------------------------------------------ judge


def judge_prompt(task: str, code: str) -> str:
    cat = "\n".join(f"- {m}: {ONE_LINE_DEF[task][m]}" for m in CATALOGUE[task])
    return (
        "You label which search algorithm a Python program implements.\n\n"
        f"Task the program was written for:\n{SPEC[task]}\n\n"
        f"Algorithm families (choose exactly one label):\n{cat}\n- other: none of the above (a different algorithm, "
        "or no recognisable search procedure)\n\n"
        "Rules: label what the code actually executes, not what identifiers suggest. Recursion vs iteration is not a "
        "separate family. Greedy best-first search (priority = Manhattan distance only) counts as astar. A heap ordered "
        "by step count only is dijkstra_unit on grids. SPFA counts as bellman_ford_spfa.\n\n"
        f"Program (comments and docstrings removed):\n```python\n{strip_comments(code)}\n```\n\n"
        'Answer with only a JSON object: {"label": "<one label>", "rationale": "<one sentence>"}'
    )


def parse_judge(text: str, task: str) -> tuple[str | None, str]:
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None, ""
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, ""
    lab = str(obj.get("label", "")).strip().lower()
    if lab not in CATALOGUE[task] + ["other"]:
        return None, str(obj.get("rationale", ""))
    return lab, str(obj.get("rationale", ""))


async def _call(client, sem, model: str, prompt: str, state: dict, logger, max_tokens: int = 2000) -> tuple[str, float]:
    async with sem:
        if state.get("stop"):
            raise BudgetExhausted()
        if spent_usd() + state.get("pending", 0.0) > state["budget"]:
            state["stop"] = True
            raise BudgetExhausted()
        for attempt in range(4):
            try:
                extra = {"usage": {"include": True}}
                if model.startswith(("anthropic/", "deepseek/")):
                    extra["reasoning"] = {"effort": "low"}  # reasoning models: keep thinking short, answer in content
                resp = await client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=max_tokens,
                    extra_body=extra)
                text = resp.choices[0].message.content or ""
                usage = getattr(resp, "usage", None)
                cost = 0.0
                if usage is not None:
                    cost = float(getattr(usage, "cost", 0.0) or (usage.model_extra or {}).get("cost", 0.0) or 0.0)
                with _lock:
                    append_jsonl(SPEND_FILE, [{"utc": time.time(), "model": model, "cost": cost,
                                               "in": getattr(usage, "prompt_tokens", None),
                                               "out": getattr(usage, "completion_tokens", None)}])
                logger.debug(f"judge {model} -> {text[:200]!r} cost={cost:.5f}")
                return text, cost
            except Exception as e:  # noqa: BLE001 -- openai raises many types; budget refusals must stop the batch
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg:
                    state["stop"] = True
                    logger.error("OpenRouter budget refusal: stopping all judge calls")
                    raise BudgetExhausted() from e
                logger.warning(f"judge call failed ({model}, attempt {attempt}): {msg[:200]}")
                await asyncio.sleep(2 + 3 * attempt)
                if state.get("stop"):
                    raise BudgetExhausted() from e
        return "", 0.0


async def _judge_many(items: list[tuple[str, str]], model: str, logger, budget: float, conc: int = 12) -> list[dict]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=90)
    sem = asyncio.Semaphore(conc)
    state = {"budget": budget, "stop": False}

    async def one(task, code):
        try:
            text, cost = await _call(client, sem, model, judge_prompt(task, code), state, logger)
            lab, rat = parse_judge(text, task)
            if lab is None and not state.get("stop"):
                text, cost2 = await _call(client, sem, model, judge_prompt(task, code) + "\nReturn valid JSON only.",
                                          state, logger)
                lab, rat = parse_judge(text, task)
            return {"label": lab, "rationale": rat, "raw": text[:500]}
        except BudgetExhausted:
            return {"label": None, "rationale": "", "raw": "", "budget_stop": True}

    out = await asyncio.gather(*[one(t, c) for t, c in items])
    await client.close()
    return list(out)


def judge_many(items: list[tuple[str, str]], model: str, logger, budget: float = JUDGE_BUDGET_USD) -> list[dict]:
    if not items:
        return []
    return asyncio.run(_judge_many(items, model, logger, budget))


# ------------------------------------------------------------------------------------------ combination


def combine(rows: list[dict], logger, judge_primary_tasks: set[str] | None = None, use_judge: bool = True) -> None:
    judge_primary_tasks = judge_primary_tasks or set()
    need = []
    for r in rows:
        if not r.get("code"):
            r["label"], r["labeller_source"] = "no_code", "none"
            continue
        if r["task"] not in judge_primary_tasks and r["rt_conf"] and r["ast_conf"] and r["rt_label"] == r["ast_label"] \
                and r["rt_label"] is not None:
            r["label"], r["labeller_source"] = r["rt_label"], "runtime+ast"
        else:
            need.append(r)
    # deduplicate judge calls by code hash
    uniq: dict[tuple, list[dict]] = {}
    for r in need:
        uniq.setdefault((r["task"], r["code_sha256"]), []).append(r)
    keys = list(uniq)
    if use_judge and keys:
        logger.info(f"judge: {len(keys)} unique programs (spent so far ${spent_usd():.3f})")
        res = judge_many([(k[0], uniq[k][0]["code"]) for k in keys], JUDGE_MODEL, logger)
    else:
        res = [{"label": None, "budget_stop": True} for _ in keys]
    for k, j in zip(keys, res):
        for r in uniq[k]:
            r["judge_label"] = j.get("label")
            r["judge_rationale"] = j.get("rationale", "")
            if j.get("label") is not None:
                r["label"], r["labeller_source"] = j["label"], "judge"
            else:
                fb = r["rt_label"] or r["ast_label"] or "other"
                r["label"], r["labeller_source"] = fb, "runtime_only_unadjudicated"
    logger.info(f"judge spend total ${spent_usd():.3f}")


def finalize_row(r: dict, banned: list[str] | None = None) -> dict:
    """Shared row schema {task, condition, paraphrase_id, sample_id, model, decoding, label, labeller_source, passed,
    wall_s, code_sha256, code} + diagnostics."""
    banned = banned or []
    r["compliant"] = bool(r.get("passed")) and r.get("label") not in banned and r.get("label") not in ("no_code",)
    for k in ("rt_ev", "ast_ev"):
        if k in r:
            r[k] = json.loads(json.dumps(r[k], default=str))
    return r


def label_rows(rows: list[dict], logger, workers: int = 6, judge_primary_tasks: set[str] | None = None,
               use_judge: bool = True) -> list[dict]:
    if judge_primary_tasks is None:  # carry the Phase-A labeller-gate decision into later phases
        gp = ROOT / "results" / "labeller_gate.json"
        judge_primary_tasks = set(json.loads(gp.read_text()).get("judge_primary_tasks", [])) if gp.exists() else set()
    cpu_stage(rows, workers, logger)
    combine(rows, logger, judge_primary_tasks, use_judge)
    from common import condition_banset

    for r in rows:
        finalize_row(r, condition_banset(r["condition"]))
    return rows
