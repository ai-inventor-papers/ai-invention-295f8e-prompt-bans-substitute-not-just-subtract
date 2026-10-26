"""S3c: OpenRouter LLM judge (temperature 0, JSON reply), with a running cost total and a hard USD cap.

Only the sets named in the plan are judged: the gold set (two judges + an adjudicator) and tracer/AST disagreements
or 'other' labels in the confirmation, swap, knob and decoder sets (single judge). HTTP 403 with the AI Inventor budget
message stops every queued and in-flight call.
"""

from __future__ import annotations

import asyncio
import json
import os
import re

import aiohttp
from loguru import logger

JUDGE_A = "google/gemini-2.5-flash-lite"
JUDGE_B = "openai/gpt-4.1-mini"
JUDGE_C = "google/gemini-2.5-flash"
CAP_USD = 1.00


class Budget:
    def __init__(self, cap: float = CAP_USD) -> None:
        self.cap = cap
        self.spent = 0.0
        self.stopped = False
        self.calls = 0
        self.errors = 0


def _prompt(task_spec: str, defs: dict, code: str) -> str:
    cat = "\n".join(f"- {k}: {v}" for k, v in defs.items())
    return (f"You classify which ALGORITHM a Python solution implements.\n\nTASK SPECIFICATION:\n{task_spec}\n\n"
            f"CATALOGUE (pick exactly one label):\n{cat}\n- no_code: no runnable solve function\n\n"
            f"CODE:\n```python\n{code[:6000]}\n```\n\nJudge the algorithm actually implemented by the code (its data "
            f"structures and control flow), not names or comments. Reply with ONLY a JSON object "
            f'{{"label": "<one label from the catalogue>", "rationale": "<one sentence>"}}.')


async def _call(session, sem, budget: Budget, model: str, prompt: str, labels: list[str]) -> dict:
    async with sem:
        if budget.stopped or budget.spent >= budget.cap:
            budget.stopped = True
            return {"label": None, "error": "budget_stop"}
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        body = {"model": model, "temperature": 0, "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}], "usage": {"include": True}}
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        for attempt in range(3):
            if budget.stopped:
                return {"label": None, "error": "budget_stop"}
            try:
                async with session.post(url, json=body, headers=hdr, timeout=aiohttp.ClientTimeout(total=60)) as r:
                    txt = await r.text()
                    if r.status == 403 and "AI Inventor per-run OpenRouter budget" in txt:
                        budget.stopped = True
                        logger.error("OpenRouter budget exhausted (403): stopping all judge calls")
                        return {"label": None, "error": "budget_403"}
                    if r.status != 200:
                        budget.errors += 1
                        logger.warning(f"judge {model} HTTP {r.status}: {txt[:200]}")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    j = json.loads(txt)
                    cost = float((j.get("usage") or {}).get("cost") or 0.0)
                    budget.spent += cost
                    budget.calls += 1
                    content = j["choices"][0]["message"]["content"] or ""
                    m = re.search(r"\{.*\}", content, re.S)
                    lab = None
                    rat = ""
                    if m:
                        try:
                            d = json.loads(m.group(0))
                            lab = str(d.get("label", "")).strip()
                            rat = str(d.get("rationale", ""))[:300]
                        except json.JSONDecodeError:
                            pass
                    if lab not in labels:
                        lab = next((x for x in labels if x.lower() == (lab or "").lower()), None)
                    logger.debug(f"judge {model}: {lab} | {rat[:120]} | cost {cost:.6f}")
                    return {"label": lab, "rationale": rat, "cost": cost}
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
                budget.errors += 1
                logger.warning(f"judge {model} error: {e}")
                await asyncio.sleep(1.5 * (attempt + 1))
        return {"label": None, "error": "failed"}


async def judge_many(items: list[dict], budget: Budget, concurrency: int = 16) -> list[dict]:
    """items: {model, prompt, labels}. Returns results in order."""
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = [_call(session, sem, budget, it["model"], it["prompt"], it["labels"]) for it in items]
        return await asyncio.gather(*tasks)


def run_judge(items: list[dict], budget: Budget) -> list[dict]:
    if not items:
        return []
    return asyncio.run(judge_many(items, budget))


def make_prompt(task: str, code: str) -> tuple[str, list[str]]:
    from tasks import t1_grid, t2_wsp
    T = t1_grid if task == "T1" else t2_wsp
    labels = list(T.CATALOGUE_DEFS.keys()) + ["no_code"]
    return _prompt(T.SPEC, T.CATALOGUE_DEFS, code or ""), labels
