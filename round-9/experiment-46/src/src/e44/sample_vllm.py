#!/usr/bin/env python3
"""Local vLLM sampling for C1 (Qwen3-8B thinking on, official FP8 checkpoint, W8A16 Marlin, eager mode).

Client for a PID-managed `vllm serve` (OpenAI-compatible /v1/completions with text prompts rendered by the official
HF chat template, enable_thinking=True). Two-phase budget forcing:
  Phase A: generate with stop ['</think>'] (kept in the output) and max_tokens = think budget (8,192).
  If Phase A ends without '</think>': append '\\n</think>\\n\\n' (forced close, thinking_truncated = True).
  Phase B: continue from prompt + Phase A text with max_tokens 1,536 (the answer).
Decoding is set explicitly per request (T 1.0, top-p 1.0, top-k off, min-p 0): the server otherwise applies the
model's generation_config defaults. Per-request seed = slot index.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from common import DECODING, append_jsonl, read_jsonl, trunc, utc_now

PORT = 8044
URL = f"http://127.0.0.1:{PORT}/v1/completions"
SERVED = "qwen3-8b-fp8"
_TOK = None


def tokenizer():
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer

        _TOK = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8", revision="220b46e3b2180893580a4454f21f22d3ebb187d3")
    return _TOK


def sampling(max_tokens: int, seed: int, stop: list[str] | None = None) -> dict[str, Any]:
    body = {"model": SERVED, "max_tokens": max_tokens, "temperature": DECODING["temperature"],
            "top_p": DECODING["top_p"], "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0,
            "presence_penalty": 0.0, "frequency_penalty": 0.0, "seed": seed, "skip_special_tokens": False}
    if stop:
        body["stop"] = stop
        body["include_stop_str_in_output"] = True
    return body


async def _post(session: aiohttp.ClientSession, body: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(4):
        try:
            async with session.post(URL, json=body, timeout=aiohttp.ClientTimeout(total=3600)) as r:
                txt = await r.text()
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}: {trunc(txt, 300)}")
                return json.loads(txt)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
            logger.warning(f"vLLM request attempt {attempt}: {type(e).__name__}: {trunc(e, 200)}")
            await asyncio.sleep(3 + 3 * attempt)
    raise RuntimeError("vLLM request failed 4 times")


async def gen_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, item: dict[str, Any], think_budget: int,
                  answer_budget: int, out_path: Path, meta: dict[str, Any]) -> dict[str, Any]:
    async with sem:
        from prompts_tp import render_chat

        chat = render_chat(tokenizer(), item["prompt"], thinking=True)
        seed = int(item["slot"])
        t0 = time.time()
        a = await _post(session, {"prompt": chat, **sampling(think_budget, seed, ["</think>"])})
        ca = a["choices"][0]
        text_a = ca["text"]
        fa = ca.get("finish_reason")
        closed = text_a.rstrip().endswith("</think>")
        truncated = not closed
        prefix = text_a if closed else text_a + "\n</think>\n\n"
        b = await _post(session, {"prompt": chat + prefix, **sampling(answer_budget, seed)})
        cb = b["choices"][0]
        content = cb["text"].replace("<|im_end|>", "").strip()
        reasoning = prefix.split("</think>")[0].replace("<think>", "").strip()
        row = {**meta, **{k: v for k, v in item.items() if k != "prompt"}, "prompt": item["prompt"],
               "prompt_sha256": __import__("hashlib").sha256(item["prompt"].encode()).hexdigest(),
               "content": content, "reasoning": reasoning, "thinking_truncated": truncated,
               "phase_a_finish": fa, "finish_reason": cb.get("finish_reason"),
               "reasoning_tokens": a["usage"]["completion_tokens"] + (0 if closed else 4),
               "completion_tokens": a["usage"]["completion_tokens"] + b["usage"]["completion_tokens"],
               "prompt_tokens": a["usage"]["prompt_tokens"], "seed": seed, "provider": "local-vllm",
               "engine": "vLLM 0.11.0 eager, Qwen/Qwen3-8B-FP8@220b46e (W8A16 Marlin)", "quantization": "fp8",
               "cost_usd": 0.0, "gen_seconds": round(time.time() - t0, 2), "utc": utc_now()}
        append_jsonl(out_path, row)
        logger.info(f"C1 {item.get('arm')} slot {item['slot']}: think {row['reasoning_tokens']} tok "
                    f"(trunc={truncated}), answer finish={row['finish_reason']}, {row['gen_seconds']}s")
        return row


async def run_items(items: list[dict[str, Any]], out_path: Path, meta: dict[str, Any], think_budget: int,
                    answer_budget: int, concurrency: int = 8) -> list[dict[str, Any]]:
    done = {(r.get("arm"), r.get("slot")) for r in read_jsonl(out_path)}
    todo = [it for it in items if (it.get("arm"), it.get("slot")) not in done]
    logger.info(f"vLLM: {len(todo)} to generate ({len(items) - len(todo)} already in {out_path.name})")
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        res = await asyncio.gather(*[gen_one(session, sem, it, think_budget, answer_budget, out_path, meta)
                                     for it in todo], return_exceptions=True)
    bad = [r for r in res if isinstance(r, BaseException)]
    for r in bad:
        logger.error(f"vLLM item failed: {type(r).__name__}: {r}")
    return [r for r in res if not isinstance(r, BaseException)]


def generate(items: list[dict[str, Any]], out_path: Path, meta: dict[str, Any], think_budget: int | None = None,
             answer_budget: int | None = None, concurrency: int = 8) -> list[dict[str, Any]]:
    tb = think_budget or DECODING["local_think_budget"]
    ab = answer_budget or DECODING["local_answer_budget"]
    return asyncio.run(run_items(items, out_path, meta, tb, ab, concurrency))


def server_ready() -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=5) as r:
            return r.status == 200
    except OSError:
        return False
