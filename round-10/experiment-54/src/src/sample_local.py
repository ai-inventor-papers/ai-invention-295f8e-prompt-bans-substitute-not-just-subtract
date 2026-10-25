#!/usr/bin/env python3
"""Local sampler for Qwen3-8B-FP8 (vLLM 0.11 OpenAI server): chat completions with
chat_template_kwargs {enable_thinking: false}; T 1.0, top_p 1.0, top_k -1, max_tokens 4096; seed = 1000*cell +
slot + 1; concurrency 32; 180 s timeout, 2 retries. Engine tag vLLM0.11/Qwen3-8B-FP8/W8A16-Marlin."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable

import aiohttp
from loguru import logger

from common import append_jsonl, read_jsonl, sha256_text, utc_now

PORT = 8754
URL = f"http://127.0.0.1:{PORT}/v1/chat/completions"
ENGINE = "vLLM0.11/Qwen3-8B-FP8/W8A16-Marlin"
MAX_TOKENS = 4096


async def call_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, item: dict[str, Any], out_path: Path,
                   max_tokens: int = MAX_TOKENS) -> dict[str, Any] | None:
    async with sem:
        body = {"model": "qwen3-8b", "messages": [{"role": "user", "content": item["prompt"]}],
                "temperature": 1.0, "top_p": 1.0, "top_k": -1, "max_tokens": int(max_tokens),
                "seed": int(item["seed"]), "chat_template_kwargs": {"enable_thinking": False}}
        t0 = time.time()
        d = None
        for attempt in range(3):
            try:
                async with session.post(URL, json=body, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.warning(f"q8 {item['cell']} s{item['slot']} HTTP {resp.status}: {txt[:200]}")
                        if resp.status == 400 and "maximum context length" in txt and max_tokens > 1024:
                            body["max_tokens"] = int(body["max_tokens"]) - 512
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    d = await resp.json()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"q8 {item['cell']} s{item['slot']} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(2 * (attempt + 1))
        if d is None:
            row = {**item, "model": "Qwen/Qwen3-8B-FP8", "engine": ENGINE, "content": "", "reasoning": "",
                   "finish_reason": "failed", "failed": True, "utc": utc_now(),
                   "gen_seconds": round(time.time() - t0, 2), "prompt_sha256": sha256_text(item["prompt"])}
            append_jsonl(out_path, row)
            return row
        ch = d["choices"][0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""
        u = d.get("usage") or {}
        row = {**item, "model": "Qwen/Qwen3-8B-FP8", "engine": ENGINE, "provider": "local",
               "prompt_sha256": sha256_text(item["prompt"]), "content": content, "reasoning": reasoning,
               "finish_reason": ch.get("finish_reason"), "prompt_tokens": u.get("prompt_tokens"),
               "completion_tokens": u.get("completion_tokens"), "reasoning_tokens": 0, "cost_usd": 0.0,
               "max_tokens": body["max_tokens"], "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(),
               "think_tag_in_content": "<think>" in content and "</think>" in content and
               len(content.split("</think>")[0].replace("<think>", "").strip()) > 0}
        append_jsonl(out_path, row)
        return row


async def run_items(items: list[dict[str, Any]], out_for: Callable[[dict[str, Any]], Path], concurrency: int = 32,
                    max_tokens: int = MAX_TOKENS, key: Callable[[dict[str, Any]], tuple] | None = None
                    ) -> dict[str, Any]:
    key = key or (lambda r: (r.get("model_key"), r.get("cell"), int(r.get("slot"))))
    done: set = set()
    for p in {str(out_for(it)) for it in items}:
        done |= {key(r) for r in read_jsonl(Path(p))}
    todo = [it for it in items if key(it) not in done]
    sem = asyncio.Semaphore(concurrency)
    t0 = time.time()
    async with aiohttp.ClientSession() as session:
        res = await asyncio.gather(*[call_one(session, sem, it, out_for(it), max_tokens) for it in todo],
                                   return_exceptions=True)
    n_ok = sum(1 for r in res if isinstance(r, dict) and not r.get("failed"))
    return {"n_tasks": len(todo), "n_ok": n_ok, "seconds": round(time.time() - t0, 1)}


def health() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
            return r.status == 200
    except OSError:
        return False
