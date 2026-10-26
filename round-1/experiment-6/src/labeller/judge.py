#!/usr/bin/env python3
"""Blind LLM judge over OpenRouter: sees task text, catalogue definitions and the code only (no condition or
sampling information). Async with a bounded semaphore, running cost tally with a hard cap, and an immediate stop
of every queued/in-flight call on the first 'AI Inventor per-run OpenRouter budget' HTTP 403."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, LOGS, TASK_TEXT, append_jsonl, read_jsonl, truncate  # noqa: E402

PRIMARY_JUDGE = "google/gemini-2.5-flash-lite"
GOLD_JUDGES = ["openai/gpt-4.1-mini", "deepseek/deepseek-v4.1-flash-1017"]
ADJUDICATOR = "google/gemini-2.5-flash"
PRICES = {  # USD per million tokens (in, out), from the OpenRouter catalogue on 2026-10-19
    "google/gemini-2.5-flash-lite": (0.10, 0.40), "openai/gpt-4.1-mini": (0.40, 1.60),
    "deepseek/deepseek-v4.1-flash-1017": (0.15, 0.60), "google/gemini-2.5-flash": (0.30, 2.50),
}
COST_LOG = LOGS / "openrouter_costs.jsonl"


class Budget:
    def __init__(self, cap_usd: float):
        self.cap = cap_usd
        self.spent = 0.0
        self.stopped = False
        self.stop_reason = None
        self.n_calls = 0

    def ok(self) -> bool:
        return not self.stopped and self.spent < self.cap


def prompt_for(task: str, code: str) -> str:
    cat = "\n".join(f"- {m}: {d}" for m, (_, d) in CATALOGUE[task].items())
    return (
        "You classify which search algorithm a Python program implements.\n\n"
        f"TASK GIVEN TO THE PROGRAMMER:\n{TASK_TEXT[task]}\n\n"
        f"CATALOGUE OF ALGORITHM LABELS:\n{cat}\n- other: none of the above (or no real search)\n\n"
        "Rules: recursion vs iteration is the same algorithm; judge the algorithm the code actually executes, not "
        "names or comments; answer other if nothing fits.\n\n"
        f"PROGRAM:\n```python\n{code[:12000]}\n```\n\n"
        'Reply with JSON only: {"label": "<one catalogue label or other>", "confidence": <0..1>, '
        '"rationale": "<one sentence>"}'
    )


def parse_reply(text: str, task: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    labels = set(CATALOGUE[task]) | {"other"}
    if m:
        try:
            d = json.loads(m.group(0))
            lab = str(d.get("label", "")).strip().lower()
            if lab not in labels:
                lab = next((x for x in labels if x in lab), "other")
            return dict(label=lab, confidence=d.get("confidence"), rationale=str(d.get("rationale", ""))[:400])
        except json.JSONDecodeError:
            pass
    low = (text or "").lower()
    lab = next((x for x in sorted(labels, key=len, reverse=True) if x in low), "other")
    return dict(label=lab, confidence=None, rationale=truncate(text, 300), parse_fallback=True)


async def _one(client, sem, budget: Budget, model: str, task: str, code: str, meta: dict) -> dict | None:
    async with sem:
        if not budget.ok():
            return None
        try:
            kw = dict(model=model, messages=[{"role": "user", "content": prompt_for(task, code)}], temperature=0,
                      max_tokens=300, extra_body={"usage": {"include": True}})
            if "gemini-2.5-flash" in model:
                kw["extra_body"]["reasoning"] = {"max_tokens": 0} if "lite" not in model else {"enabled": False}
            resp = await client.chat.completions.create(**kw)
        except Exception as e:  # noqa: BLE001 - classify budget refusals; anything else is a soft failure
            msg = str(e)
            if "AI Inventor per-run OpenRouter budget" in msg or ("403" in msg and "budget" in msg.lower()):
                budget.stopped = True
                budget.stop_reason = msg[:300]
            return dict(meta, model=model, error=msg[:300])
        if budget.stopped:
            return None
        u = resp.usage
        cost = None
        extra = getattr(u, "model_extra", None) or {}
        if "cost" in extra:
            cost = float(extra["cost"])
        elif getattr(u, "cost", None) is not None:
            cost = float(u.cost)
        if cost is None:
            pi, po = PRICES.get(model, (1.0, 4.0))
            cost = (u.prompt_tokens * pi + u.completion_tokens * po) / 1e6
        budget.spent += cost
        budget.n_calls += 1
        text = resp.choices[0].message.content or ""
        out = dict(meta, model=model, **parse_reply(text, task), cost=cost, prompt_tokens=u.prompt_tokens,
                   completion_tokens=u.completion_tokens)
        append_jsonl(COST_LOG, [dict(model=model, cost=cost, kind=meta.get("kind", "judge"))])
        return out


async def judge_many(items: list[dict], model: str, budget: Budget, concurrency: int = 24) -> list[dict]:
    """items: [{task, code, key, ...}] -> list of result dicts (None entries dropped)."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=90, max_retries=2)
    sem = asyncio.Semaphore(concurrency)
    tasks = [_one(client, sem, budget, model, it["task"], it["code"], {k: v for k, v in it.items() if k != "code"})
             for it in items]
    res = await asyncio.gather(*tasks, return_exceptions=True)
    await client.close()
    return [r for r in res if isinstance(r, dict)]


def total_cost() -> float:
    return round(sum(r.get("cost", 0.0) for r in read_jsonl(COST_LOG)), 6)


if __name__ == "__main__":
    from common import REFS_DIR
    b = Budget(0.05)
    items = [dict(task="T1" if f.name.startswith("t1") else "T2", code=f.read_text(), key=f.name, kind="smoke")
             for f in sorted(REFS_DIR.glob("t*.py"))[:5]]
    out = asyncio.run(judge_many(items, PRIMARY_JUDGE, b))
    for o in out:
        print(o["key"], o.get("label"), o.get("confidence"), o.get("cost"), o.get("error"))
    print("spent", b.spent)
