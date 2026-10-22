#!/usr/bin/env python3
"""Generic batch runner: list of requests -> JSONL rows, against one long-lived `vllm serve` process.

Prompts are rendered locally with the model's chat template (enable_thinking=False) and sent as token ids
to /v1/completions, so the server never re-applies a template. Every sampling field is passed explicitly
except top_k (left at the installed version's 'disabled' default; the server runs with
--generation-config vllm so Qwen3's generation_config.json defaults cannot leak in).
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from common import MODEL_ID, SERVED_NAME, VLLM_URL, read_jsonl, utc_now

_TOKENIZER = None
EXPECTED_TAIL = "<|im_start|>assistant\n<think>\n\n</think>\n\n"


def tokenizer():
    global _TOKENIZER
    if _TOKENIZER is None:
        from transformers import AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(MODEL_ID)
    return _TOKENIZER


def render_ids(text: str) -> list[int]:
    tok = tokenizer()
    ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True,
                                  enable_thinking=False)
    if isinstance(ids, dict):  # some transformers versions return a BatchEncoding
        ids = ids["input_ids"]
    return list(ids)


def check_template() -> str:
    """Assert the thinking-off template tail on one prompt; return the decoded tail for the log."""
    ids = render_ids("Say hello.")
    decoded = tokenizer().decode(ids)
    assert decoded.endswith(EXPECTED_TAIL), f"unexpected chat-template tail: {decoded[-80:]!r}"
    return decoded


def count_tokens(text: str) -> int:
    return len(tokenizer().encode(text, add_special_tokens=False))


async def wait_for_server(timeout_s: float = 1800.0) -> None:
    t0 = time.time()
    async with aiohttp.ClientSession() as s:
        while time.time() - t0 < timeout_s:
            try:
                async with s.get(f"{VLLM_URL}/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        js = await r.json()
                        logger.info(f"vLLM server ready: {[m['id'] for m in js.get('data', [])]}")
                        return
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(5)
    raise TimeoutError("vLLM server did not come up")


async def _post(session: aiohttp.ClientSession, payload: dict[str, Any]) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            async with session.post(f"{VLLM_URL}/v1/completions", json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
            last_err = e
            logger.warning(f"completion request failed (attempt {attempt + 1}): {str(e)[:200]}")
            await asyncio.sleep(5 * (attempt + 1))
    raise RuntimeError(f"completion request failed after retries: {last_err}")


async def run_requests_async(reqs: list[dict[str, Any]], out_path: Path, concurrency: int = 12) -> dict[str, Any]:
    """Each request: req_id, prompt (text), n, temperature, max_tokens, seed, plus metadata copied to rows.
    Appends one row per sample to out_path; resumes by skipping req_ids already present."""
    out_path = Path(out_path)
    done = {r["req_id"] for r in read_jsonl(out_path)}
    todo = [r for r in reqs if r["req_id"] not in done]
    logger.info(f"{out_path.name}: {len(reqs)} requests, {len(done)} already done, {len(todo)} to run")
    if not todo:
        return {"n_requests": 0, "n_samples": 0, "seconds": 0.0, "output_tokens": 0}
    lock = asyncio.Lock()
    stats = {"n_requests": 0, "n_samples": 0, "output_tokens": 0, "truncated": 0}
    t_start = time.time()
    timeout = aiohttp.ClientTimeout(total=3600, sock_read=3600)
    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    sem = asyncio.Semaphore(concurrency)
    fh = out_path.open("a")

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        async def one(req: dict[str, Any]) -> None:
            async with sem:
                ids = render_ids(req["prompt"])
                payload = {
                    "model": SERVED_NAME, "prompt": ids, "n": int(req["n"]), "max_tokens": int(req["max_tokens"]),
                    "temperature": float(req["temperature"]), "top_p": 1.0, "min_p": 0.0,
                    "repetition_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
                    "seed": int(req["seed"]),
                }
                gen_start = utc_now()
                js = await _post(session, payload)
                gen_end = utc_now()
                rows = []
                meta = {k: v for k, v in req.items() if k not in ("prompt",)}
                for ch in sorted(js["choices"], key=lambda c: c.get("index", 0)):
                    text = ch.get("text", "")
                    ntok = count_tokens(text)
                    row = dict(meta)
                    row.update({
                        "sample_index": int(ch.get("index", 0)), "text": text,
                        "finish_reason": ch.get("finish_reason"), "n_output_tokens": ntok,
                        "n_prompt_tokens": len(ids), "gen_start_utc": gen_start, "gen_utc": gen_end,
                        "model": MODEL_ID,
                    })
                    rows.append(row)
                    stats["output_tokens"] += ntok
                    stats["truncated"] += int(ch.get("finish_reason") == "length")
                async with lock:
                    for row in rows:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    stats["n_requests"] += 1
                    stats["n_samples"] += len(rows)
                    if stats["n_requests"] % 20 == 0 or stats["n_requests"] == len(todo):
                        el = time.time() - t_start
                        logger.info(f"{out_path.name}: {stats['n_requests']}/{len(todo)} requests, "
                                    f"{stats['n_samples']} samples, {stats['output_tokens'] / max(el, 1e-6):.0f} "
                                    f"out-tok/s, {el:.0f}s")

        results = await asyncio.gather(*[one(r) for r in todo], return_exceptions=True)
    fh.close()
    errs = [r for r in results if isinstance(r, Exception)]
    for e in errs[:5]:
        logger.error(f"request error: {e}")
    stats["seconds"] = time.time() - t_start
    stats["errors"] = len(errs)
    stats["sec_per_output_token"] = stats["seconds"] / max(stats["output_tokens"], 1)
    logger.info(f"{out_path.name}: finished {stats}")
    return stats


def run_requests(reqs: list[dict[str, Any]], out_path: Path, concurrency: int = 12) -> dict[str, Any]:
    return asyncio.run(run_requests_async(reqs, out_path, concurrency))
