#!/usr/bin/env python3
"""STEP A4 judges: two different families via OpenRouter, temperature 0, blind to cell and arm, gated on 10 controls
of known class before any adjudication call. Every response is cached in audit/judge_cache.jsonl (a rerun is free);
spend is tracked from usage.cost, capped at USD 0.5, and the batch aborts on the first budget refusal (HTTP 403
'AI Inventor per-run OpenRouter budget')."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from sections.common import AUDIT, read_json, sha256_text, BENCH_ROOT

JUDGES = {"A": "deepseek/deepseek-chat-v3.1", "B": "mistralai/mistral-medium-3.1"}
CAP_USD = 0.5
CACHE = AUDIT / "judge_cache.jsonl"
UA = "aii-eval7-record-repair/1.0"  # the proxy's Cloudflare rule rejects the default Python-urllib agent

T03_SPEC = read_json(BENCH_ROOT / "bench" / "T03_kth_smallest" / "spec.json")
T03_LABELS = {c["mode"]: f"{c['display_name']}: {c['mechanism']}" for c in T03_SPEC["catalogue"]}
T2_DESC = ("Task: write a Python function solve(n, edges, s, t) that returns the length of the shortest path from node "
           "s to node t in a directed graph with non-negative integer edge weights; nodes are 0..n-1 and edges is a "
           "list of (u, v, w) tuples; return -1 if t is unreachable.")
T2_LABELS = {
    "dijkstra": "Dijkstra's algorithm: repeatedly settle the unsettled node of smallest tentative distance (binary heap, "
                "or a linear scan for the minimum) and relax its out-edges",
    "bf_spfa": "Bellman-Ford (relax every edge for up to n-1 rounds, possibly with early exit) or SPFA (a FIFO queue of "
               "nodes whose distance improved)",
    "bidijkstra": "bidirectional Dijkstra: two Dijkstra searches, forward from s and backward from t, meeting in the middle",
    "floyd": "Floyd-Warshall: all-pairs dynamic programme over intermediate nodes with three nested loops",
    "dial": "Dial's algorithm: Dijkstra with a bucket queue indexed by integer distance",
}
OTHER = "other: a shortest-path or selection method not in this list, or no recognisable algorithm"


def prompt_for(task: str, code: str) -> list[dict[str, str]]:
    if task == "T03":
        desc, labels = T03_SPEC["description"], T03_LABELS
    else:
        desc, labels = T2_DESC, T2_LABELS
    lab_lines = "\n".join(f"- {k}: {v}" for k, v in labels.items()) + f"\n- {OTHER}"
    sys_msg = ("You classify which algorithm a Python program implements or attempts. Judge the mechanism the code "
               "actually executes, not names or comments. Reply with one JSON object only: "
               '{"label": "<one label from the list>", "reason": "<one short sentence>"}.')
    user = (f"{desc}\n\nLabels:\n{lab_lines}\n\nProgram:\n```python\n{code}\n```\n"
            "Which label fits the algorithm this program implements (or attempts, if it is buggy or truncated)?")
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}]


def parse_label(text: str, task: str) -> str | None:
    allowed = set(T03_LABELS if task == "T03" else T2_LABELS) | {"other"}
    m = re.search(r"\{.*\}", text or "", re.S)
    if m:
        try:
            lab = str(json.loads(m.group(0)).get("label", "")).strip()
            if lab in allowed:
                return lab
        except (json.JSONDecodeError, AttributeError):
            pass
    for a in sorted(allowed, key=len, reverse=True):
        if re.search(rf"\b{re.escape(a)}\b", text or ""):
            return a
    return None


class BudgetRefused(Exception):
    pass


class JudgeClient:
    def __init__(self) -> None:
        self.base = os.environ["OPENROUTER_BASE_URL"].rstrip("/")
        self.key = os.environ["OPENROUTER_API_KEY"]
        self.spent = 0.0
        self.n_calls = 0
        self.refused = False
        self.cache: dict[str, dict[str, Any]] = {}
        if CACHE.exists():
            for l in CACHE.read_text().splitlines():
                if l.strip():
                    r = json.loads(l)
                    self.cache[r["key"]] = r
        self.cached_cost = sum(r.get("cost", 0.0) for r in self.cache.values())

    async def key_status(self, s: aiohttp.ClientSession) -> dict[str, Any]:
        async with s.get(self.base + "/key", timeout=aiohttp.ClientTimeout(total=30)) as r:
            return {"status": r.status, "body": (await r.json()) if r.status == 200 else (await r.text())[:300]}

    async def one(self, s: aiohttp.ClientSession, sem: asyncio.Semaphore, model: str, task: str, code: str,
                  tag: str) -> dict[str, Any]:
        msgs = prompt_for(task, code)
        key = sha256_text(model + "\n" + json.dumps(msgs))
        if key in self.cache:
            return self.cache[key]
        async with sem:
            if self.refused or self.spent + self.cached_cost >= CAP_USD:
                return {"key": key, "model": model, "label": None, "error": "skipped (budget cap or refusal)"}
            body = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": 200, "usage": {"include": True}}
            for attempt in range(3):
                try:
                    async with s.post(self.base + "/chat/completions", json=body,
                                      timeout=aiohttp.ClientTimeout(total=120)) as r:
                        txt = await r.text()
                        if r.status == 403 and "AI Inventor per-run OpenRouter budget" in txt:
                            self.refused = True
                            raise BudgetRefused(txt[:200])
                        if r.status != 200:
                            logger.warning(f"judge {model} HTTP {r.status}: {txt[:200]}")
                            await asyncio.sleep(2 * (attempt + 1))
                            continue
                        d = json.loads(txt)
                        out = d["choices"][0]["message"]["content"] or ""
                        cost = float((d.get("usage") or {}).get("cost") or 0.0)
                        self.spent += cost
                        self.n_calls += 1
                        rec = {"key": key, "model": model, "task": task, "tag": tag, "code_sha256": sha256_text(code),
                               "response": out, "label": parse_label(out, task), "cost": cost,
                               "usage": d.get("usage")}
                        self.cache[key] = rec
                        with CACHE.open("a") as f:
                            f.write(json.dumps(rec) + "\n")
                        logger.debug(f"judge {model} {tag}: {rec['label']} (${cost:.5f}) <- {out[:120]!r}")
                        return rec
                except BudgetRefused:
                    raise
                except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"judge {model} attempt {attempt}: {e}")
                    await asyncio.sleep(2 * (attempt + 1))
            return {"key": key, "model": model, "label": None, "error": "failed after 3 attempts"}

    async def batch(self, items: list[tuple[str, str, str, str]], conc: int = 12) -> list[dict[str, Any]]:
        """items: (model, task, code, tag). Aborts the whole batch on the first budget refusal."""
        sem = asyncio.Semaphore(conc)
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.key}", "User-Agent": UA}) as s:
            ks = await self.key_status(s)
            logger.info(f"OpenRouter key status before batch: {json.dumps(ks)[:300]}")
            self.key_before = ks
            tasks = [asyncio.create_task(self.one(s, sem, m, t, c, g)) for m, t, c, g in items]
            try:
                res = await asyncio.gather(*tasks)
            except BudgetRefused as e:
                logger.error(f"budget refusal, aborting batch: {e}")
                for t in tasks:
                    t.cancel()
                res = [t.result() if t.done() and not t.cancelled() and t.exception() is None else
                       {"label": None, "error": "aborted (budget refusal)"} for t in tasks]
            self.key_after = await self.key_status(s)
        return res
