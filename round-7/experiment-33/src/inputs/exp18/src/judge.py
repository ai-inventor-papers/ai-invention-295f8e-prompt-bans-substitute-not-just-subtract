"""OpenRouter access for every LLM call of this artifact (labeller judges, novelty audit, claim extraction).

One running budget (results/costs.json): usage.cost read on every response, own stop at USD 0.95, and the whole
artifact stops queueing calls at the first HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget'
(checked again after each call obtains its semaphore slot).  Every response is cached by key in
data/llm_cache.jsonl, so a rerun never pays twice.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any

from loguru import logger

from config import DATA, OPENROUTER_OWN_CAP, RESULTS, append_jsonl, read_jsonl, utc_now, write_json

JUDGE_LABEL_MODELS = {"bench": "google/gemini-2.5-flash-lite", "path": "openai/gpt-4.1-mini"}
AUDIT_JUDGE_A = "google/gemini-2.5-flash-lite"
AUDIT_JUDGE_B = "openai/gpt-4.1-mini"
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
LLM_CACHE = DATA / "llm_cache.jsonl"
COSTS = RESULTS / "costs.json"
_LOCK = threading.Lock()


class Budget:
    def __init__(self) -> None:
        c = json.loads(COSTS.read_text()) if COSTS.exists() else {}
        self.total = float(c.get("total_usd", 0.0))
        self.by_purpose: dict[str, float] = dict(c.get("by_purpose", {}))
        self.n_calls = int(c.get("n_calls", 0))
        self.refusals = int(c.get("budget_refusals", 0))
        self.stopped = bool(c.get("stopped", False))
        self.stop_reason = c.get("stop_reason")

    def add(self, purpose: str, usd: float) -> None:
        with _LOCK:
            self.total += usd
            self.by_purpose[purpose] = self.by_purpose.get(purpose, 0.0) + usd
            self.n_calls += 1
            if self.total >= OPENROUTER_OWN_CAP and not self.stopped:
                self.stopped, self.stop_reason = True, f"own cap USD {OPENROUTER_OWN_CAP} reached"
                logger.error(self.stop_reason)
            self.save()

    def refuse(self, msg: str) -> None:
        with _LOCK:
            self.refusals += 1
            self.stopped, self.stop_reason = True, f"phase budget refusal: {msg[:160]}"
            logger.error(self.stop_reason)
            self.save()

    def save(self) -> None:
        write_json(COSTS, {"total_usd": round(self.total, 6), "by_purpose": {k: round(v, 6) for k, v in
                                                                             self.by_purpose.items()},
                           "n_calls": self.n_calls, "budget_refusals": self.refusals, "stopped": self.stopped,
                           "stop_reason": self.stop_reason, "own_cap_usd": OPENROUTER_OWN_CAP, "updated_utc": utc_now()})


_BUDGET: Budget | None = None
_CACHE: dict[str, dict[str, Any]] | None = None


def budget() -> Budget:
    global _BUDGET
    if _BUDGET is None:
        _BUDGET = Budget()
    return _BUDGET


def _cache() -> dict[str, dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        _CACHE = {r["key"]: r for r in read_jsonl(LLM_CACHE)}
    return _CACHE


_CLIENT = None


def _client():
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                       timeout=120, max_retries=2)


async def call_llm(sem: asyncio.Semaphore, model: str, prompt: str, purpose: str, max_tokens: int = 400,
                   cache_key: str | None = None, temperature: float = 0.0) -> tuple[str | None, dict[str, Any]]:
    """-> (text or None, record).  Never raises for API errors (they are logged and recorded)."""
    key = cache_key or f"{model}|{hash(prompt)}"
    c = _cache()
    if key in c and c[key].get("text") is not None:
        return c[key]["text"], c[key]
    b = budget()
    if b.stopped:
        return None, {"key": key, "error": "budget_stopped"}
    async with sem:
        if b.stopped:  # re-check after obtaining the slot
            return None, {"key": key, "error": "budget_stopped"}
        client = _client()
        r = None
        try:
            for attempt in range(5):
                try:
                    r = await client.chat.completions.create(model=model,
                                                             messages=[{"role": "user", "content": prompt}],
                                                             temperature=temperature, max_tokens=max_tokens)
                    break
                except Exception as e:  # noqa: BLE001 - classify; never retry a budget refusal
                    msg = str(e)
                    if BUDGET_MSG in msg:
                        b.refuse(msg)
                        return None, {"key": key, "error": "budget_refusal"}
                    transient = any(c in msg for c in ("429", "500", "502", "503", "504", "timed out", "Timeout"))
                    if transient and attempt < 4 and not b.stopped:
                        await asyncio.sleep(2 * 2 ** attempt)
                        continue
                    logger.warning(f"LLM call failed ({model}, {purpose}): {msg[:200]}")
                    return None, {"key": key, "error": msg[:200]}
        finally:
            try:
                await client.close()
            except Exception:  # noqa: BLE001
                pass
        if r is None:
            return None, {"key": key, "error": "no response"}
        txt = (r.choices[0].message.content or "") if r.choices else ""
        cost = 0.0
        if r.usage is not None:
            cost = float(getattr(r.usage, "cost", 0.0) or 0.0)
        b.add(purpose, cost)
        rec = {"key": key, "model": model, "purpose": purpose, "text": txt, "cost": cost, "utc": utc_now(),
               "prompt_tokens": getattr(r.usage, "prompt_tokens", None) if r.usage else None,
               "completion_tokens": getattr(r.usage, "completion_tokens", None) if r.usage else None}
        c[key] = rec
        with _LOCK:
            append_jsonl(LLM_CACHE, [rec])
        logger.debug(f"LLM {model} {purpose} cost={cost:.5f} out={txt[:160]!r}")
        return txt, rec


def key_status() -> dict[str, Any]:
    """GET <base_url>/key (phase limit and remaining); recorded, never fatal."""
    import urllib.request

    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}
