#!/usr/bin/env python3
"""OpenRouter guard used by every API call of the artifact.

- base_url / api_key from OPENROUTER_BASE_URL / OPENROUTER_API_KEY (never hard-coded);
- running usage.cost total per purpose with a hard cap (labeller disputes 0.5, adjudication 1.8, L 1.0, reserve 0.2);
- the FIRST HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget' sets a stop flag: every queued and
  in-flight call of the batch is cancelled (checked again after each semaphore acquire) and the batch is not rerun;
- every call (purpose, model, cost, tokens, UTC) is appended to results/openrouter_ledger.jsonl; prompts and outputs
  of judge calls are cached in data/or_cache_<purpose>.jsonl keyed by sha256(model|prompt).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from loguru import logger

from common import BUDGET_MSG, DATA, RESULTS, append_jsonl, read_jsonl, sha256_text, trunc, utc_now

LEDGER = RESULTS / "openrouter_ledger.jsonl"


def spent(purpose: str | None = None) -> float:
    rows = read_jsonl(LEDGER)
    return float(sum(r.get("cost") or 0.0 for r in rows if purpose is None or r.get("purpose") == purpose))


class BudgetStop(Exception):
    pass


class ORClient:
    def __init__(self, purpose: str, cap_usd: float, concurrency: int = 8) -> None:
        from openai import AsyncOpenAI
        self.purpose = purpose
        self.cap = cap_usd
        self.spent = spent(purpose)
        self.stop = False
        self.stop_reason: str | None = None
        self.concurrency = concurrency
        self._loop = None
        self.sem: asyncio.Semaphore | None = None
        self.client = None
        self._mk = lambda: AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"],
                                       api_key=os.environ["OPENROUTER_API_KEY"], timeout=180.0, max_retries=0)
        self.cache_p = DATA / f"or_cache_{purpose}.jsonl"
        self.cache = {r["key"]: r for r in read_jsonl(self.cache_p)}
        self.n_calls = 0

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0, max_tokens: int = 600,
                   top_p: float | None = None, json_mode: bool = False, use_cache: bool = True,
                   tag: str = "") -> dict[str, Any] | None:
        key = sha256_text(model + "|" + json.dumps(messages) + f"|{temperature}|{max_tokens}|{top_p}")
        if use_cache and key in self.cache:
            return self.cache[key]
        if self.stop:
            return None
        loop = asyncio.get_running_loop()
        if self._loop is not loop:          # semaphore + HTTP pool are bound to one event loop
            self._loop = loop
            self.sem = asyncio.Semaphore(self.concurrency)
            self.client = self._mk()
        async with self.sem:
            if self.stop:                                   # re-check after acquiring the slot
                return None
            if self.spent >= self.cap:
                self.stop = True
                self.stop_reason = f"artifact cap {self.cap} reached for {self.purpose}"
                logger.warning(self.stop_reason)
                return None
            kw: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature,
                                  "max_tokens": max_tokens, "extra_body": {"usage": {"include": True}}}
            if top_p is not None:
                kw["top_p"] = top_p
            if json_mode:
                kw["response_format"] = {"type": "json_object"}
            for attempt in range(6):
                if self.stop:
                    return None
                try:
                    resp = await self.client.chat.completions.create(**kw)
                    d = resp.model_dump()
                    usage = d.get("usage") or {}
                    cost = float(usage.get("cost") or 0.0)
                    self.spent += cost
                    self.n_calls += 1
                    text = (d["choices"][0]["message"].get("content") or "") if d.get("choices") else ""
                    rec = {"key": key, "model": model, "text": text, "cost": cost, "utc": utc_now(), "tag": tag,
                           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                           "finish_reason": d["choices"][0].get("finish_reason") if d.get("choices") else None}
                    append_jsonl(LEDGER, [{"purpose": self.purpose, "model": model, "cost": cost, "utc": rec["utc"],
                                           "prompt_tokens": rec["prompt_tokens"],
                                           "completion_tokens": rec["completion_tokens"], "tag": tag}])
                    append_jsonl(self.cache_p, [rec])
                    self.cache[key] = rec
                    logger.debug(f"OR {self.purpose} {model} ${cost:.5f} -> {trunc(text, 200)}")
                    return rec
                except Exception as e:  # noqa: BLE001 - classify: budget stop, transient retry, or give up
                    msg = str(e)
                    status = getattr(e, "status_code", None)
                    if status == 403 and BUDGET_MSG in msg:
                        self.stop = True
                        self.stop_reason = "budget_403"
                        logger.error(f"OpenRouter budget refusal -> stopping the batch: {trunc(msg, 200)}")
                        return None
                    if status in (400, 401, 404):
                        logger.error(f"OR {model} non-retryable {status}: {trunc(msg, 300)}")
                        return {"key": key, "model": model, "text": None, "error": f"{status}:{trunc(msg, 200)}"}
                    wait = min(30.0, 2.0 * (2 ** attempt))
                    logger.warning(f"OR {model} attempt {attempt} failed ({status}): {trunc(msg, 160)}; retry in {wait}s")
                    await asyncio.sleep(wait)
            return None

    async def gather(self, coros: list) -> list:
        return await asyncio.gather(*coros, return_exceptions=False)


def parse_json_obj(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                v = json.loads(m.group(0))
                return v if isinstance(v, dict) else None
            except json.JSONDecodeError:
                return None
    return None


async def label_disputes(task_obj: dict[str, Any], items: list[tuple[str, str]], client: ORClient,
                         model: str = "google/gemini-2.5-flash-lite",
                         fallback: str = "google/gemini-2.5-flash") -> dict[str, str | None]:
    """items: (key, code). Returns key -> judged label (mode id or 'other'), None where unavailable."""
    from labels import judge_prompt
    modes = set(task_obj["modes"]) | {"other"}

    async def one(k: str, code: str) -> tuple[str, str | None]:
        msgs = [{"role": "user", "content": judge_prompt(task_obj, code)}]
        r = await client.chat(model, msgs, temperature=0.0, max_tokens=150, json_mode=True,
                              tag=f"label:{task_obj['task']}")
        if (r is None or r.get("text") is None) and not client.stop:
            r = await client.chat(fallback, msgs, temperature=0.0, max_tokens=150, json_mode=True,
                                  tag=f"label_fb:{task_obj['task']}")
        obj = parse_json_obj(r.get("text") if r else None)
        lab = str(obj.get("label")).strip() if obj and obj.get("label") else None
        return k, (lab if lab in modes else ("other" if lab else None))
    res = await asyncio.gather(*[one(k, c) for k, c in items])
    return dict(res)
