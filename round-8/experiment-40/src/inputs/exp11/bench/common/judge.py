"""Blind LLM judge through OpenRouter (OpenAI SDK at OPENROUTER_BASE_URL).

The judge sees the task description, the catalogue (mode ids + one-line mechanisms + 'other') and the
name-scrubbed code; it answers JSON {label, rationale}.  Temperature 0, cache keyed by (model, task, code sha256),
usage.cost read per call, hard personal stop at USD 1.40, and the whole batch aborts on the first HTTP 403 whose
message starts 'AI Inventor per-run OpenRouter budget'.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from loguru import logger

from .catalogue import TASKS
from .scrub import scrub_code

JUDGES = {"j1": "google/gemini-2.5-flash-lite", "j2": "openai/gpt-4.1-mini", "j3": "deepseek/deepseek-chat-v3.1"}
PERSONAL_CAP = 1.40


class BudgetExhausted(RuntimeError):
    pass


class Judge:
    def __init__(self, root: Path):
        self.root = root
        self.cache_path = root / "data" / "judge_cache.jsonl"
        self.spend_path = root / "logs" / "openrouter_spend.jsonl"
        self.cache = {}
        if self.cache_path.exists():
            for l in self.cache_path.open():
                r = json.loads(l)
                self.cache[r["key"]] = r
        self.spent = 0.0
        if self.spend_path.exists():
            for l in self.spend_path.open():
                self.spent += json.loads(l).get("cost", 0.0) or 0.0
        self.aborted = False
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=60, max_retries=2)

    @staticmethod
    def prompt(task: str, code: str) -> str:
        c = TASKS[task]
        cat = "\n".join(f"- {m}: {d[1]}" for m, d in c["modes"].items())
        return (f"You label which algorithm a Python program implements.\n\nTask given to the programmer:\n{c['description']}\n\n"
                f"Candidate labels (choose exactly one):\n{cat}\n- other: the program's main mechanism matches none of the "
                f"labels above (for example an arithmetic trick or a different algorithm).\n\n"
                "Judge the mechanism the code actually executes, not names (identifiers and comments were scrubbed). "
                "A standard-library call counts as the mechanism it implements when that is one of the labels. "
                "Recursion versus iteration does not change the label. If the program is buggy, label the mechanism it "
                "attempts.\n\nProgram:\n```python\n" + code + "\n```\n\n"
                'Answer with JSON only: {"label": "<one label id>", "rationale": "<one sentence>"}')

    def key(self, judge: str, task: str, code: str) -> str:
        return f"{judge}|{task}|{hashlib.sha256(code.encode()).hexdigest()}"

    async def _call(self, sem, judge: str, task: str, code: str) -> dict:
        k = self.key(judge, task, code)
        if k in self.cache:
            return self.cache[k]
        async with sem:
            if self.aborted:
                return {"key": k, "label": None, "error": "aborted"}
            if self.spent >= PERSONAL_CAP:
                self.aborted = True
                return {"key": k, "label": None, "error": "personal cap reached"}
            model = JUDGES[judge]
            try:
                r = await self.client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": self.prompt(task, code)}], temperature=0,
                    max_tokens=200)
            except Exception as e:  # noqa: BLE001 - classify below; never retry a budget refusal
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg:
                    self.aborted = True
                    logger.error("OpenRouter phase budget exhausted: aborting judge batch")
                    return {"key": k, "label": None, "error": "budget"}
                logger.warning(f"judge {judge} call failed: {msg[:200]}")
                return {"key": k, "label": None, "error": msg[:200]}
            if self.aborted:
                return {"key": k, "label": None, "error": "aborted"}
            txt = r.choices[0].message.content or ""
            cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
            self.spent += cost
            with self.spend_path.open("a") as f:
                f.write(json.dumps({"judge": judge, "model": model, "task": task, "cost": cost,
                                    "prompt_tokens": r.usage.prompt_tokens if r.usage else None,
                                    "completion_tokens": r.usage.completion_tokens if r.usage else None}) + "\n")
            label, rationale = None, ""
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                try:
                    j = json.loads(m.group(0))
                    label, rationale = str(j.get("label", "")).strip(), str(j.get("rationale", ""))[:300]
                except json.JSONDecodeError:
                    pass
            valid = set(TASKS[task]["modes"]) | {"other"}
            if label not in valid:
                mm = re.search(r'"label"\s*:\s*"([a-z_]+)"', txt)
                label = mm.group(1) if mm and mm.group(1) in valid else ("other" if label else None)
            rec = {"key": k, "judge": judge, "model": model, "task": task, "label": label, "rationale": rationale,
                   "raw": txt[:400], "cost": cost}
            self.cache[k] = rec
            with self.cache_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            return rec

    async def _batch(self, items, concurrency):
        sem = asyncio.Semaphore(concurrency)
        return await asyncio.gather(*[self._call(sem, j, t, c) for j, t, c in items])

    async def _call_prompt(self, sem, judge: str, task: str, prompt: str) -> dict:
        """Generic labelled-text call (association answers); same cache, budget and abort rules."""
        k = f"{judge}|{task}|prompt|{hashlib.sha256(prompt.encode()).hexdigest()}"
        if k in self.cache:
            return self.cache[k]
        async with sem:
            if self.aborted or self.spent >= PERSONAL_CAP:
                self.aborted = True
                return {"key": k, "label": None, "error": "aborted"}
            try:
                r = await self.client.chat.completions.create(
                    model=JUDGES[judge], messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=120)
            except Exception as e:  # noqa: BLE001
                if "AI Inventor per-run OpenRouter budget" in str(e):
                    self.aborted = True
                    return {"key": k, "label": None, "error": "budget"}
                return {"key": k, "label": None, "error": str(e)[:200]}
            if self.aborted:
                return {"key": k, "label": None, "error": "aborted"}
            txt = r.choices[0].message.content or ""
            cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
            self.spent += cost
            with self.spend_path.open("a") as f:
                f.write(json.dumps({"judge": judge, "model": JUDGES[judge], "task": task, "cost": cost, "kind": "prompt"}) + "\n")
            mm = re.search(r'"label"\s*:\s*"([A-Za-z_]+)"', txt)
            valid = set(TASKS[task]["modes"]) | {"other"}
            label = mm.group(1) if mm and mm.group(1) in valid else "other"
            rec = {"key": k, "judge": judge, "task": task, "label": label, "raw": txt[:300], "cost": cost}
            self.cache[k] = rec
            with self.cache_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            return rec

    def label_prompts(self, items: list[tuple[str, str, str]], concurrency: int = 16) -> list[dict]:
        async def run():
            sem = asyncio.Semaphore(concurrency)
            return await asyncio.gather(*[self._call_prompt(sem, j, t, p) for j, t, p in items])
        res = asyncio.run(run())
        logger.info(f"judge prompt batch of {len(items)} done; running spend ${self.spent:.4f}")
        return res

    def label_many(self, items: list[tuple[str, str, str]], concurrency: int = 16) -> list[dict]:
        """items: [(judge_id, task, raw_code)] -> records (code is name-scrubbed before judging)."""
        prepared = [(j, t, scrub_code(c)[0]) for j, t, c in items]
        res = asyncio.run(self._batch(prepared, concurrency))
        logger.info(f"judge batch of {len(items)} done; running spend ${self.spent:.4f}")
        return res
