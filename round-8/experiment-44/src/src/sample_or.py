#!/usr/bin/env python3
"""OpenRouter sampling for the screen configurations (asyncio + aiohttp, global semaphore 24).

Per call: T 1.0, top-p 1.0 (no top-k), max_tokens 1,536 (thinking off) / 9,728 (thinking on), seed = slot index (best
effort), provider pinned with allow_fallbacks false, reasoning {enabled} for Qwen3 hybrids. Records provider, usage
(prompt, completion, reasoning tokens), usage.cost, finish_reason, reasoning text and content. Stops when the
artifact total reaches the cap; the first HTTP 403 'AI Inventor per-run OpenRouter budget' sets the stop flag and
cancels everything still queued or in flight (checked again after each call gets its slot); never retried.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from common import BUDGET_MSG, COST_CAP_USD, DECODING, add_cost, append_jsonl, read_jsonl, total_cost, trunc, utc_now

PROVIDER_PINS: dict[str, dict[str, Any]] = {
    "C2": {"order": ["CoreWeave"], "allow_fallbacks": False, "quantizations": ["bf16"]},
    "C3": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
    "C4": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
    "C5": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
    "C6": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
    "C7": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
    "C8": {"order": ["Cloudflare"], "allow_fallbacks": False},
}
# DeepInfra ignores reasoning {enabled: false} for Qwen3 (smoke: ~1,600 reasoning tokens, truncated at 1,536) ->
# the Qwen3 soft switch ' /no_think' is appended to the user turn of the thinking-off configurations (deviation D10).
NO_THINK_SUFFIX: dict[str, bool] = {"C3": True, "C5": True}


class Stop:
    def __init__(self) -> None:
        self.flag = False
        self.reason = ""

    def set(self, reason: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {reason}")
        self.flag = True
        self.reason = self.reason or reason


def body_for(cid: str, cfg: dict[str, Any], prompt: str, slot: int, pin: dict[str, Any] | None,
             no_think_suffix: bool) -> dict[str, Any]:
    user = prompt + (" /no_think" if (no_think_suffix and not cfg["thinking"]) else "")
    body: dict[str, Any] = {"model": cfg["model"], "messages": [{"role": "user", "content": user}],
                            "temperature": DECODING["temperature"], "top_p": DECODING["top_p"], "seed": int(slot) + 1,
                            "max_tokens": DECODING["max_tokens_on"] if cfg["thinking"] else DECODING["max_tokens_off"],
                            "usage": {"include": True}}
    if pin:
        body["provider"] = pin
    if cfg["family"] == "Qwen3":
        body["reasoning"] = {"enabled": bool(cfg["thinking"])}
    return body


async def call_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, cid: str, cfg: dict[str, Any],
                   item: dict[str, Any], out_path: Path, pin: dict[str, Any] | None, purpose: str,
                   no_think_suffix: bool = False) -> dict[str, Any] | None:
    async with sem:
        if stop.flag:
            return None
        if total_cost() >= COST_CAP_USD:
            stop.set(f"artifact cost cap {COST_CAP_USD} reached")
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "User-Agent": "aii-tp/1.0"}
        body = body_for(cid, cfg, item["prompt"], item["slot"], pin, no_think_suffix)
        t0 = time.time()
        d = None
        for attempt in range(4):
            if stop.flag:
                return None
            try:
                async with session.post(url, json=body, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=900)) as resp:
                    txt = await resp.text()
                    if resp.status == 403 and BUDGET_MSG in txt:
                        add_cost(purpose, 0.0, refused=True)
                        stop.set(f"budget 403: {trunc(txt, 200)}")
                        return None
                    if resp.status in (408, 429, 500, 502, 503, 504) or resp.status >= 520:
                        logger.warning(f"{cid} slot {item['slot']} HTTP {resp.status} (attempt {attempt}): "
                                       f"{trunc(txt, 160)}")
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    if resp.status != 200:
                        logger.warning(f"{cid} slot {item['slot']} HTTP {resp.status}: {trunc(txt, 300)}")
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    if "error" in d and not d.get("choices"):
                        logger.warning(f"{cid} slot {item['slot']} provider error: {trunc(d['error'], 200)}")
                        d = None
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"{cid} slot {item['slot']} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(3 * (attempt + 1))
        if d is None:
            logger.error(f"{cid} slot {item['slot']}: failed after retries")
            return None
        usage = d.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        tot = add_cost(purpose, cost)
        ch = (d.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        if "</think>" in content:            # provider returned inline thinking
            pre, post = content.split("</think>", 1)
            reasoning = (reasoning + "\n" + pre.replace("<think>", "")).strip()
            content = post.strip()
        rtok = ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0
        row = {**{k: v for k, v in item.items()}, "config": cid, "model": cfg["model"],
               "prompt_sha256": hashlib.sha256(item["prompt"].encode()).hexdigest(),
               "content": content, "reasoning": reasoning, "finish_reason": ch.get("finish_reason"),
               "native_finish_reason": ch.get("native_finish_reason"), "provider": d.get("provider"),
               "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
               "reasoning_tokens": rtok, "cost_usd": cost, "seed": int(item["slot"]) + 1,
               "thinking_truncated": bool(cfg["thinking"] and ch.get("finish_reason") == "length"),
               "no_think_suffix": bool(no_think_suffix and not cfg["thinking"]),
               "engine": f"OpenRouter {d.get('provider')} ({cfg['quantization']})", "quantization": cfg["quantization"],
               "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(), "or_id": d.get("id")}
        append_jsonl(out_path, row)
        logger.debug(f"{cid} {item.get('arm')} slot {item['slot']} {row['provider']} fin={row['finish_reason']} "
                     f"rtok={rtok} ctok={row['completion_tokens']} ${cost:.5f} total ${tot:.4f}")
        return row


async def run_jobs(jobs: list[tuple[str, dict[str, Any], list[dict[str, Any]], Path]], purpose: str,
                   concurrency: int = 24) -> dict[str, Any]:
    """jobs: (config id, config dict, items, out path). Skips slots already present in out path (resume)."""
    sem = asyncio.Semaphore(concurrency)
    stop = Stop()
    tasks = []
    async with aiohttp.ClientSession() as session:
        for cid, cfg, items, out in jobs:
            done = {(r.get("arm"), r.get("slot")) for r in read_jsonl(out)}
            todo = [it for it in items if (it.get("arm"), it.get("slot")) not in done]
            logger.info(f"{cid} ({cfg['name']}): {len(todo)} calls to make ({len(items) - len(todo)} done)")
            for it in todo:
                tasks.append(asyncio.create_task(call_one(session, sem, stop, cid, cfg, it, out,
                                                          PROVIDER_PINS.get(cid), purpose,
                                                          NO_THINK_SUFFIX.get(cid, False))))
        n = len(tasks)
        done_n = 0
        t0 = time.time()
        for f in asyncio.as_completed(tasks):
            try:
                await f
            except Exception as e:  # noqa: BLE001 - one failed call must not stop the batch
                logger.error(f"call exception {type(e).__name__}: {e}")
            done_n += 1
            if done_n % 25 == 0 or done_n == n:
                logger.info(f"[{purpose}] {done_n}/{n} calls done, {time.time() - t0:.0f}s, "
                            f"artifact spend ${total_cost():.3f}")
            if stop.flag:
                for t in tasks:
                    t.cancel()
                break
    return {"stopped": stop.flag, "reason": stop.reason, "n_tasks": n}


def run(jobs: list[tuple[str, dict[str, Any], list[dict[str, Any]], Path]], purpose: str,
        concurrency: int = 24) -> dict[str, Any]:
    return asyncio.run(run_jobs(jobs, purpose, concurrency))
