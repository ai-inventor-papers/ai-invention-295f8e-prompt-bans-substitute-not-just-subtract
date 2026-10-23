#!/usr/bin/env python3
"""OpenRouter sampling for the iteration-9 cells (asyncio + aiohttp, one global semaphore).

Adapted from the iteration-8 sampler (src/sample_or.py of art_R-HSmXq2t97f). Per call: T 1.0, top-p 1.0 (no top-k),
max_tokens 12,288, thinking on (reasoning returned and stored), provider pinned with allow_fallbacks false where the
cell's model has a pin, seed = 1000 * cell_index + slot + 1. Every row records the prompt sha256, provider,
finish_reason, prompt / completion / reasoning tokens and usage.cost.

Budget safety: the artifact total (shared ledger results/costs.json) is checked before every call; the first HTTP 403
whose message starts 'AI Inventor per-run OpenRouter budget' sets the stop flag, which every task checks before AND
after it acquires its semaphore slot, and all queued and in-flight tasks are cancelled; the batch is never rerun.
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

from common import (BUDGET_MSG, COST_CAP_USD, DECODING_V9, MODELS_V9, add_cost, append_jsonl, read_jsonl, total_cost,
                    trunc, utc_now)


class Stop:
    def __init__(self) -> None:
        self.flag = False
        self.reason = ""

    def set(self, reason: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {reason}")
        self.flag = True
        self.reason = self.reason or reason


def body_for(mkey: str, item: dict[str, Any], max_tokens: int | None = None,
             provider_override: dict[str, Any] | None = None) -> dict[str, Any]:
    m = MODELS_V9[mkey]
    body: dict[str, Any] = {"model": m["model"], "messages": [{"role": "user", "content": item["prompt"]}],
                            "temperature": DECODING_V9["temperature"], "top_p": DECODING_V9["top_p"],
                            "seed": int(item["seed"]), "max_tokens": int(max_tokens or DECODING_V9["max_tokens"]),
                            "usage": {"include": True}}
    pin = provider_override if provider_override is not None else m.get("provider")
    if pin:
        body["provider"] = pin
    if m["family"].startswith("Qwen3"):
        body["reasoning"] = {"enabled": True}
    if m.get("reasoning_effort"):
        body["reasoning"] = {"effort": m["reasoning_effort"]}
    return body


async def call_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, item: dict[str, Any],
                   out_path: Path, purpose: str, url: str, max_tokens: int | None = None,
                   provider_override: dict[str, Any] | None = None, cap: float = COST_CAP_USD) -> dict[str, Any] | None:
    if stop.flag:
        return None
    async with sem:
        if stop.flag:                      # checked again after the slot is acquired
            return None
        if total_cost() >= cap:
            stop.set(f"artifact cost cap {cap} reached")
            return None
        headers = {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', 'test')}",
                   "User-Agent": "aii-tpb/1.0"}
        body = body_for(item["model_key"], item, max_tokens, provider_override)
        t0 = time.time()
        d = None
        for attempt in range(4):
            if stop.flag:
                return None
            try:
                async with session.post(url, json=body, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=1200)) as resp:
                    txt = await resp.text()
                    if resp.status == 403 and BUDGET_MSG in txt:
                        add_cost(purpose, 0.0, refused=True)
                        stop.set(f"budget 403: {trunc(txt, 200)}")
                        return None
                    if resp.status in (408, 429, 500, 502, 503, 504) or resp.status >= 520:
                        logger.warning(f"{item['cell']} slot {item['slot']} HTTP {resp.status} (attempt {attempt}): "
                                       f"{trunc(txt, 160)}")
                        await asyncio.sleep(4 * (attempt + 1))
                        continue
                    if resp.status != 200:
                        logger.warning(f"{item['cell']} slot {item['slot']} HTTP {resp.status}: {trunc(txt, 300)}")
                        await asyncio.sleep(4 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    if "error" in d and not d.get("choices"):
                        logger.warning(f"{item['cell']} slot {item['slot']} provider error: {trunc(d['error'], 200)}")
                        d = None
                        await asyncio.sleep(4 * (attempt + 1))
                        continue
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"{item['cell']} slot {item['slot']} attempt {attempt}: {type(e).__name__}")
                await asyncio.sleep(4 * (attempt + 1))
        if d is None:
            logger.error(f"{item['cell']} slot {item['slot']}: failed after retries")
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
        row = {**item, "model": MODELS_V9[item["model_key"]]["model"],
               "prompt_sha256": hashlib.sha256(item["prompt"].encode()).hexdigest(),
               "content": content, "reasoning": reasoning, "finish_reason": ch.get("finish_reason"),
               "native_finish_reason": ch.get("native_finish_reason"), "provider": d.get("provider"),
               "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
               "reasoning_tokens": rtok, "cost_usd": cost, "max_tokens": body["max_tokens"],
               "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(), "or_id": d.get("id")}
        append_jsonl(out_path, row)
        logger.debug(f"{item['cell']} slot {item['slot']} {row['provider']} fin={row['finish_reason']} rtok={rtok} "
                     f"ctok={row['completion_tokens']} ${cost:.5f} total ${tot:.4f}")
        return row


async def run_items(items: list[dict[str, Any]], out_for: Any, purpose: str, concurrency: int = 32,
                    url: str | None = None, max_tokens: int | None = None,
                    provider_override: dict[str, Any] | None = None, cap: float = COST_CAP_USD) -> dict[str, Any]:
    """items: rows with cell, slot, seed, prompt, model_key. out_for(item) -> jsonl path. Skips (cell, slot) pairs
    already present in their output file (resume)."""
    url = url or os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    sem = asyncio.Semaphore(concurrency)
    stop = Stop()
    done_keys: set[tuple[str, int]] = set()
    for p in {str(out_for(it)) for it in items}:
        done_keys |= {(r.get("cell"), int(r.get("slot"))) for r in read_jsonl(Path(p))}
    todo = [it for it in items if (it["cell"], int(it["slot"])) not in done_keys]
    logger.info(f"[{purpose}] {len(todo)} calls to make ({len(items) - len(todo)} already done)")
    t0 = time.time()
    n_ok = 0
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(call_one(session, sem, stop, it, out_for(it), purpose, url, max_tokens,
                                              provider_override, cap)) for it in todo]
        done_n = 0
        for f in asyncio.as_completed(tasks):
            try:
                r = await f
                n_ok += int(r is not None)
            except asyncio.CancelledError:
                pass
            except Exception as e:  # noqa: BLE001 - one failed call must not stop the batch
                logger.error(f"call exception {type(e).__name__}: {e}")
            done_n += 1
            if done_n % 20 == 0 or done_n == len(tasks):
                logger.info(f"[{purpose}] {done_n}/{len(tasks)} done, {time.time() - t0:.0f}s, "
                            f"artifact spend ${total_cost():.3f}")
            if stop.flag:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                break
    return {"stopped": stop.flag, "reason": stop.reason, "n_tasks": len(todo), "n_ok": n_ok,
            "seconds": round(time.time() - t0, 1)}


def run(items: list[dict[str, Any]], out_for: Any, purpose: str, concurrency: int = 32, **kw: Any) -> dict[str, Any]:
    return asyncio.run(run_items(items, out_for, purpose, concurrency, **kw))


# ---------------------------------------------------------------------------------------------- 403 unit test (0.4)
async def _mock_403_test(tmp_dir: Path) -> dict[str, Any]:
    """A local aiohttp server answers every POST with HTTP 403 'AI Inventor per-run OpenRouter budget ...' after a
    short delay. 24 tasks share a semaphore of 4: after the first refusal no further request may reach the server
    and every queued and in-flight task must end without a row."""
    from aiohttp import web

    hits = {"n": 0}

    async def handler(request: web.Request) -> web.Response:
        hits["n"] += 1
        await asyncio.sleep(0.3)
        return web.Response(status=403, text=json.dumps({"error": {"message": BUDGET_MSG + " exhausted (mock)"}}))

    app = web.Application()
    app.router.add_post("/chat/completions", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
    items = [{"cell": "MOCK", "slot": i, "seed": i + 1, "prompt": "x", "model_key": "q32"} for i in range(24)]
    out = tmp_dir / "mock_403_rows.jsonl"
    out.unlink(missing_ok=True)
    res = await run_items(items, lambda it: out, "mock403", concurrency=4,
                          url=f"http://127.0.0.1:{port}/chat/completions", cap=1e9)
    await runner.cleanup()
    rows = read_jsonl(out)
    ok = res["stopped"] and hits["n"] <= 4 and not rows
    return {"server_hits": hits["n"], "rows_written": len(rows), "stopped": res["stopped"], "passed": bool(ok),
            "rule": "after the first budget 403 no new request may start (hits <= concurrency 4) and no row is kept"}


def mock_403_test(tmp_dir: Path) -> dict[str, Any]:
    return asyncio.run(_mock_403_test(tmp_dir))
