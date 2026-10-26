"""Blind LLM judges through OpenRouter (OpenAI SDK at OPENROUTER_BASE_URL) for the new units.

The judge sees the task description, the catalogue (mode ids + mechanisms + 'other') and the code -- no model or arm
information. JSON answer {label, rationale}; temperature 0; cache keyed by (judge, unit, code sha256); usage.cost read
per call into logs/openrouter_spend_newbench.jsonl; the running total is capped (cost_guard, USD 2.00 for this
artifact) and the whole batch aborts on the first HTTP 403 whose message starts 'AI Inventor per-run OpenRouter
budget' (checked after a call gets its semaphore slot, too).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from loguru import logger

JUDGES = {"j1": "google/gemini-2.5-flash", "j2": "openai/gpt-4.1-mini", "j3": "deepseek/deepseek-chat-v3.1"}
CAP_USD = 2.00
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "judge_cache_newbench.jsonl"
SPEND = ROOT / "logs" / "openrouter_spend_newbench.jsonl"
_STATE: dict[str, Any] = {"cache": None, "aborted": False}


def spent_total() -> float:
    tot = 0.0
    for f in ROOT.glob("logs/openrouter_spend*.jsonl"):
        for l in f.read_text().splitlines():
            try:
                tot += float(json.loads(l).get("cost") or 0.0)
            except (json.JSONDecodeError, ValueError):
                continue
    p = ROOT / "results" / "openrouter_cost_paths.json"
    if p.exists():
        try:
            tot += float(json.loads(p.read_text()).get("spent", 0.0))
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
    return tot


def _cache() -> dict[str, Any]:
    if _STATE["cache"] is None:
        c = {}
        if CACHE.exists():
            for l in CACHE.read_text().splitlines():
                try:
                    r = json.loads(l)
                    c[r["key"]] = r
                except json.JSONDecodeError:
                    continue
        _STATE["cache"] = c
    return _STATE["cache"]


def prompt(spec: dict[str, Any], code: str) -> str:
    cat = "\n".join(f"- {c['mode']}: {c['mechanism']}" for c in spec["catalogue"])
    return (f"You label which algorithm a Python program implements.\n\nTask given to the programmer:\n"
            f"{spec['description']}\n\nCandidate labels (choose exactly one):\n{cat}\n- other: the program's main "
            "mechanism matches none of the labels above (for example a different algorithm or an arithmetic "
            "trick).\n\nJudge the mechanism the code actually executes, not the names of identifiers or comments. "
            "A standard-library call counts as the mechanism it implements when that is one of the labels. "
            "Recursion versus iteration does not change the label unless the labels say so. If the program is "
            "buggy, label the mechanism it attempts.\n\nProgram:\n```python\n" + code + "\n```\n\n"
            'Answer with JSON only: {"label": "<one label id>", "rationale": "<one sentence>"}')


def key(judge: str, unit: str, code: str) -> str:
    return f"{judge}|{unit}|{hashlib.sha256(code.encode()).hexdigest()}"


async def _call(client, sem, judge: str, unit: str, spec: dict[str, Any], code: str) -> dict[str, Any]:
    k = key(judge, unit, code)
    c = _cache()
    if k in c:
        return c[k]
    async with sem:
        if _STATE["aborted"]:
            return {"key": k, "label": None, "error": "aborted"}
        if spent_total() >= CAP_USD:
            _STATE["aborted"] = True
            return {"key": k, "label": None, "error": "artifact cap reached"}
        model = JUDGES[judge]
        try:
            r = await client.chat.completions.create(model=model, temperature=0, max_tokens=200,
                                                     messages=[{"role": "user", "content": prompt(spec, code)}])
        except Exception as e:  # noqa: BLE001 - classify; never retry a budget refusal
            msg = str(e)
            if BUDGET_MSG in msg:
                _STATE["aborted"] = True
                logger.error("OpenRouter phase budget exhausted: aborting judge batch")
                return {"key": k, "label": None, "error": "budget"}
            logger.warning(f"judge {judge} failed: {msg[:200]}")
            return {"key": k, "label": None, "error": msg[:200]}
        if _STATE["aborted"]:
            return {"key": k, "label": None, "error": "aborted"}
        txt = r.choices[0].message.content or ""
        cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
        SPEND.parent.mkdir(parents=True, exist_ok=True)
        with SPEND.open("a") as f:
            f.write(json.dumps({"judge": judge, "model": model, "unit": unit, "cost": cost,
                                "prompt_tokens": r.usage.prompt_tokens if r.usage else None,
                                "completion_tokens": r.usage.completion_tokens if r.usage else None}) + "\n")
        valid = {cc["mode"] for cc in spec["catalogue"]} | {"other"}
        label, rationale = None, ""
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            try:
                j = json.loads(m.group(0))
                label, rationale = str(j.get("label", "")).strip(), str(j.get("rationale", ""))[:300]
            except json.JSONDecodeError:
                pass
        if label not in valid:
            mm = re.search(r'"label"\s*:\s*"([a-z_0-9]+)"', txt)
            label = mm.group(1) if mm and mm.group(1) in valid else ("other" if label else None)
        rec = {"key": k, "judge": judge, "model": model, "unit": unit, "label": label, "rationale": rationale,
               "raw": txt[:300], "cost": cost}
        c[k] = rec
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        return rec


async def _batch(items: list[tuple[str, str, dict, str]], concurrency: int) -> list[dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=90, max_retries=2)
    sem = asyncio.Semaphore(concurrency)
    try:
        return await asyncio.gather(*[_call(client, sem, j, u, s, c) for j, u, s, c in items])
    finally:
        await client.close()


def judge_many(items: list[tuple[str, str, dict, str]], concurrency: int = 12) -> list[dict[str, Any]]:
    """items: [(judge_id, unit, spec, code)] -> records (label None on failure / abort)."""
    if not items:
        return []
    return asyncio.run(_batch(items, concurrency))


def adjudicate(unit: str, spec: dict[str, Any], codes: list[str]) -> list[dict[str, Any]]:
    """Two judges from different families; a third breaks disagreements; no majority -> None ('disputed')."""
    first = judge_many([(j, unit, spec, c) for c in codes for j in ("j1", "j2")])
    out, need = [], []
    for i, c in enumerate(codes):
        a, b = first[2 * i], first[2 * i + 1]
        out.append({"j1": a.get("label"), "j2": b.get("label"), "j3": None, "label": None})
        if a.get("label") and a.get("label") == b.get("label"):
            out[i]["label"] = a["label"]
        else:
            need.append(i)
    if need:
        third = judge_many([("j3", unit, spec, codes[i]) for i in need])
        for i, r in zip(need, third):
            out[i]["j3"] = r.get("label")
            votes = [v for v in (out[i]["j1"], out[i]["j2"], out[i]["j3"]) if v]
            for v in set(votes):
                if votes.count(v) >= 2:
                    out[i]["label"] = v
    return out
