"""Async client for the PID-managed vLLM server: explicit SamplingParams on every request, prompt sent as token
ids (the exact chat-template rendering), output token ids returned (return_token_ids), per-request veto through
vllm_xargs.  Thinking-on generations use two phases (think up to the cap, then answer), see generate_thinking."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import aiohttp
from loguru import logger

from config import DECODING, PORTS, SERVED, THINK_END_ID

_SEM: dict[tuple[str, int], asyncio.Semaphore] = {}


def _sem(kind: str, n: int = 160) -> asyncio.Semaphore:
    """One semaphore per (server, event loop): asyncio primitives are bound to the loop that first waits on them."""
    key = (kind, id(asyncio.get_running_loop()))
    if key not in _SEM:
        _SEM[key] = asyncio.Semaphore(n)
    return _SEM[key]


async def _post(session: aiohttp.ClientSession, kind: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    url = f"http://127.0.0.1:{PORTS[kind]}/v1/completions"
    last = None
    for attempt in range(4):
        try:
            async with session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                txt = await r.text()
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}: {txt[:300]}")
                return json.loads(txt)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
            last = e
            logger.warning(f"request failed (attempt {attempt + 1}): {str(e)[:200]}")
            await asyncio.sleep(3 + 5 * attempt)
    raise RuntimeError(f"request failed after retries: {last}")


async def complete(session: aiohttp.ClientSession, kind: str, prompt_ids: list[int], seed: int, max_tokens: int,
                   veto: list[list[int]] | None = None, stop_token_ids: list[int] | None = None,
                   timeout: float = 3600.0) -> dict[str, Any]:
    body: dict[str, Any] = {"model": SERVED[kind], "prompt": prompt_ids, "max_tokens": int(max_tokens),
                            "seed": int(seed), "n": 1, "return_token_ids": True, **DECODING}
    if veto:
        body["vllm_xargs"] = {"veto": json.dumps([list(map(int, s)) for s in veto])}
    if stop_token_ids:
        body["stop_token_ids"] = stop_token_ids
    async with _sem(kind):
        t0 = time.time()
        js = await _post(session, kind, body, timeout)
    ch = js["choices"][0]
    return {"text": ch.get("text") or "", "token_ids": ch.get("token_ids") or [],
            "finish_reason": ch.get("finish_reason"), "stop_reason": ch.get("stop_reason"),
            "n_new_tokens": len(ch.get("token_ids") or []), "latency_s": round(time.time() - t0, 2),
            "n_prompt_tokens": len(prompt_ids)}


async def generate_many(kind: str, reqs: list[dict[str, Any]], max_conc: int = 160) -> list[dict[str, Any]]:
    """reqs: [{'prompt_ids', 'seed', 'max_tokens', 'veto'?}] -> outputs in input order."""
    conn = aiohttp.TCPConnector(limit=max_conc)
    async with aiohttp.ClientSession(connector=conn) as session:
        coros = [complete(session, kind, r["prompt_ids"], r["seed"], r["max_tokens"], r.get("veto"),
                          r.get("stop_token_ids")) for r in reqs]
        return await asyncio.gather(*coros)


def run_batch(kind: str, reqs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    t0 = time.time()
    out = asyncio.run(generate_many(kind, reqs))
    dt = time.time() - t0
    ntok = sum(o["n_new_tokens"] for o in out)
    logger.info(f"[{kind}] {len(reqs)} generations, {ntok} new tokens in {dt:.0f}s ({ntok / max(dt, 1e-6):.0f} tok/s)")
    return out, dt


async def generate_thinking(session: aiohttp.ClientSession, kind: str, prompt_ids: list[int], seed: int,
                            think_cap: int, max_model_len: int, answer_cap: int, nl2_ids: list[int],
                            stop_phrase_ids: list[int]) -> dict[str, Any]:
    """Phase A: think until '</think>' (stop token) or the cap; phase B: continue the same text (+ blank line) for
    the answer.  At the cap the Qwen3 thinking-budget stop phrase (ending in '</think>') is appended."""
    a = await complete(session, kind, prompt_ids, seed, think_cap, stop_token_ids=[THINK_END_ID])
    ids_a = list(a["token_ids"])
    complete_think = a["finish_reason"] == "stop" and (a.get("stop_reason") == THINK_END_ID or
                                                      (ids_a and ids_a[-1] == THINK_END_ID))
    if complete_think:
        if not ids_a or ids_a[-1] != THINK_END_ID:
            ids_a.append(THINK_END_ID)
        cont = prompt_ids + ids_a + nl2_ids
    elif a["finish_reason"] == "stop":  # EOS before </think>: the model ended without an answer phase
        return {"think_ids": ids_a, "answer_ids": [], "answer_text": "", "thinking_complete": False,
                "ended_in_thinking": True, "thinking_tokens": len(ids_a), "finish_reason_a": a["finish_reason"],
                "finish_reason_b": None, "latency_s": a["latency_s"]}
    else:
        cont = prompt_ids + ids_a + stop_phrase_ids
    budget = min(answer_cap, max_model_len - len(cont) - 8)
    if budget < 16:
        return {"think_ids": ids_a, "answer_ids": [], "answer_text": "", "thinking_complete": complete_think,
                "ended_in_thinking": False, "thinking_tokens": len(ids_a), "finish_reason_a": a["finish_reason"],
                "finish_reason_b": "no_budget", "latency_s": a["latency_s"]}
    b = await complete(session, kind, cont, seed + 1, budget)
    return {"think_ids": ids_a, "answer_ids": b["token_ids"], "answer_text": b["text"],
            "thinking_complete": complete_think, "ended_in_thinking": False, "thinking_tokens": len(ids_a),
            "answer_tokens": b["n_new_tokens"], "finish_reason_a": a["finish_reason"],
            "finish_reason_b": b["finish_reason"], "latency_s": a["latency_s"] + b["latency_s"]}
