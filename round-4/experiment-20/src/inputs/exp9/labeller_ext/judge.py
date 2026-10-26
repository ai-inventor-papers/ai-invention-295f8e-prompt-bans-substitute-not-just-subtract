#!/usr/bin/env python3
"""5d strategy-blind LLM judge (OpenRouter). Sees the task DESCRIPTION, the catalogue with one-line definitions
plus 'other', and the code -- never the condition. Output JSON {label, confidence, rationale}.

Cached by (model, code_sha256) in labeller/judge_cache.jsonl. Every response's usage.cost is added to a running
ledger (results/openrouter_cost.json). The first HTTP 403 'AI Inventor per-run OpenRouter budget' stops every
queued and in-flight call of the batch (checked again after each call acquires its semaphore slot).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from loguru import logger

from common import (DESCRIPTION, EXTENDED_CATALOGUE, LABEL_DIR, MODE_DEFINITIONS, MODES, OTHER, RESULTS_DIR,
                    sha256_text, utc_now)

# Iteration 2: cache keys carry a 'v3|' prefix (gold-gate revision round 1: attempt-level wording) (10-label grid catalogue); the spend cap is the TOTAL across purposes.

CACHE = LABEL_DIR / "judge_cache.jsonl"
COST_FILE = RESULTS_DIR / "openrouter_cost.json"
_LOCK = threading.Lock()
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"


class BudgetExhausted(RuntimeError):
    pass


def judge_prompt(task: str, code: str) -> str:
    cat = "\n".join(f"- {m}: {MODE_DEFINITIONS[task][m]}" for m in MODES[task])
    ext = ", ".join(EXTENDED_CATALOGUE[task])
    return (
        f"TASK DESCRIPTION:\n{DESCRIPTION[task]}\n\n"
        f"CATALOGUE OF ALGORITHM LABELS:\n{cat}\n- other: anything else, e.g. {ext}, a random walk, or a program "
        "that does not implement any listed algorithm.\n\n"
        f"PROGRAM:\n```python\n{code}\n```\n\n"
        "Which label best describes the search strategy the program ACTUALLY implements or attempts? Judge the "
        "code's mechanism (data structures and exploration order), not its comments, variable names or claims. Label "
        "the listed algorithm whose mechanism the code attempts even if the program is buggy, incomplete or fails; use "
        "'other' only when the mechanism matches none of the listed algorithms. Answer with only a JSON object: "
        '{"label": <one label id from the catalogue above>, "confidence": <number between 0 and 1>, '
        '"rationale": <one short sentence>}'
    )


def load_cost() -> dict[str, Any]:
    if COST_FILE.exists():
        return json.loads(COST_FILE.read_text())
    return {"total_usd": 0.0, "by_purpose": {}, "n_calls": 0, "budget_refusals": 0}


def add_cost(purpose: str, usd: float, refused: bool = False) -> float:
    with _LOCK:
        c = load_cost()
        c["total_usd"] = round(c["total_usd"] + usd, 6)
        c["by_purpose"][purpose] = round(c["by_purpose"].get(purpose, 0.0) + usd, 6)
        c["n_calls"] += 1
        c["budget_refusals"] += int(refused)
        c["updated_utc"] = utc_now()
        COST_FILE.write_text(json.dumps(c, indent=1))
        return c["total_usd"]


def purpose_spent(purpose: str) -> float:
    return float(load_cost()["by_purpose"].get(purpose, 0.0))


def load_cache() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    out[r["key"]] = r
                except json.JSONDecodeError:
                    continue
    return out


def _append_cache(rec: dict[str, Any]) -> None:
    with _LOCK:
        with CACHE.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")


def parse_judge(text: str, task: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    lbl, conf, rat = None, None, ""
    if m:
        try:
            js = json.loads(m.group(0))
            lbl = str(js.get("label", "")).strip().lower()
            conf = js.get("confidence")
            rat = str(js.get("rationale", ""))[:300]
        except json.JSONDecodeError:
            pass
    if lbl is None:
        mm = re.search(r'"label"\s*:\s*"([a-z_]+)"', text)
        lbl = mm.group(1) if mm else None
    valid = set(MODES[task]) | {OTHER}
    if lbl not in valid:
        lbl = OTHER if lbl else None
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return {"label": lbl, "confidence": conf, "rationale": rat}


async def _judge_one(client, sem, stop: dict[str, Any], model: str, task: str, code: str, purpose: str,
                     cap_usd: float, cache: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = f"v3|{model}|{task}|{sha256_text(code)}"
    if key in cache:
        return cache[key]
    async with sem:
        if stop.get("stop"):
            return None
        if load_cost()["total_usd"] >= cap_usd:
            stop["stop"] = True
            stop["reason"] = f"total judge cap {cap_usd} USD reached"
            return None
        extra: dict[str, Any] = {"usage": {"include": True}}
        if model.startswith("google/"):
            extra["reasoning"] = {"max_tokens": 0}
        for attempt in range(4):
            if stop.get("stop"):
                return None
            try:
                resp = await client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": judge_prompt(task, code)}], temperature=0.0,
                    max_tokens=300, extra_body=extra)
                text = resp.choices[0].message.content or ""
                usage = getattr(resp, "usage", None)
                cost = 0.0
                if usage is not None:
                    cost = float(getattr(usage, "cost", None) or (usage.model_extra or {}).get("cost", 0.0) or 0.0)
                add_cost(purpose, cost)
                parsed = parse_judge(text, task)
                rec = {"key": key, "model": model, "task": task, "raw": text[:800], **parsed, "cost": cost,
                       "utc": utc_now()}
                logger.debug(f"judge {model} -> {parsed['label']} ({cost:.5f} USD): {text[:120]!r}")
                if parsed["label"] is None and attempt < 3:
                    continue
                _append_cache(rec)
                cache[key] = rec
                return rec
            except Exception as e:  # noqa: BLE001 - classify below
                msg = str(e)
                if BUDGET_MSG in msg or ("403" in msg and "budget" in msg.lower()):
                    stop["stop"] = True
                    stop["reason"] = "budget_403"
                    add_cost(purpose, 0.0, refused=True)
                    logger.error(f"OpenRouter budget refusal -- stopping the batch: {msg[:200]}")
                    return None
                logger.warning(f"judge call failed ({model}, attempt {attempt + 1}): {msg[:200]}")
                await asyncio.sleep(2 * (attempt + 1))
        return None


async def judge_many_async(items: list[dict[str, Any]], model: str, purpose: str, cap_usd: float,
                           concurrency: int = 16) -> tuple[list[dict[str, Any] | None], dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=120.0, max_retries=0)
    cache = load_cache()
    sem = asyncio.Semaphore(concurrency)
    stop: dict[str, Any] = {"stop": False}
    res = await asyncio.gather(*[_judge_one(client, sem, stop, model, it["task"], it["code"], purpose, cap_usd,
                                            cache) for it in items])
    await client.close()
    return list(res), stop


def judge_many(items: list[dict[str, Any]], model: str, purpose: str, cap_usd: float,
               concurrency: int = 16) -> tuple[list[dict[str, Any] | None], dict[str, Any]]:
    """items: [{'task', 'code'}]; returns per-item judge records (None if not judged) and the stop state."""
    out, stop = asyncio.run(judge_many_async(items, model, purpose, cap_usd, concurrency))
    logger.info(f"judge {model} [{purpose}]: {sum(r is not None for r in out)}/{len(out)} judged; "
                f"spent {purpose_spent(purpose):.4f} USD on {purpose}; stop={stop}")
    return out, stop


if __name__ == "__main__":
    print(Path(CACHE))
