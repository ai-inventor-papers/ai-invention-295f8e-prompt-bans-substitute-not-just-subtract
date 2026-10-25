#!/usr/bin/env python3
"""OpenRouter sampler for Qwen3-14B / Qwen3-32B (adapted from exp45 sample_v9.py): aiohttp streaming chat
completions, provider pinned to DeepInfra fp8 without fallbacks, thinking on (reasoning {enabled: true}), T 1.0,
top-p 1.0, max_tokens 12,288, seed = 1000*cell + slot + 1.

Deviation D3: requests stream, with a 180 s idle timeout between chunks and a 900 s total cap. At most 2 retries,
only for 429/5xx/connection errors before the first token (backoff 10 s, then 30 s). A capped or failed request
becomes a counted non-survivor row with its finish_reason. The first HTTP 403 whose message starts
'AI Inventor per-run OpenRouter budget' sets the stop flag: no new request starts (checked after a slot is acquired),
in-flight streams are cancelled and the batch is not rerun."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import aiohttp
from loguru import logger

from common import (BUDGET_MSG, COST_CAP_USD, add_cost, append_jsonl, read_jsonl, sha256_text, total_cost, trunc,
                    utc_now)

MODELS = {"q32": {"model": "qwen/qwen3-32b", "price_in": 0.08e-6, "price_out": 0.28e-6},
          "q14": {"model": "qwen/qwen3-14b", "price_in": 0.12e-6, "price_out": 0.24e-6}}
PROVIDER = {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]}
IDLE_S = 180.0
TOTAL_S = 900.0
MAX_TOKENS = 12288


class Stop:
    def __init__(self) -> None:
        self.flag = False
        self.reason = ""

    def set(self, reason: str) -> None:
        if not self.flag:
            logger.error(f"STOP: {reason}")
        self.flag = True
        self.reason = self.reason or reason


def body_for(item: dict[str, Any], thinking: bool = True, max_tokens: int = MAX_TOKENS,
             provider: dict[str, Any] | None = None) -> dict[str, Any]:
    prompt = item["prompt"] + (" /no_think" if item.get("no_think_suffix") else "")
    b = {"model": MODELS[item["model_key"]]["model"], "messages": [{"role": "user", "content": prompt}],
         "temperature": 1.0, "top_p": 1.0, "seed": int(item["seed"]), "max_tokens": int(max_tokens),
         "usage": {"include": True}, "provider": provider or PROVIDER, "stream": True,
         "reasoning": {"enabled": bool(thinking)}}
    return b


async def _stream(session: aiohttp.ClientSession, url: str, body: dict[str, Any], headers: dict[str, str],
                  stop: Stop, idle_s: float, total_s: float) -> dict[str, Any]:
    """Return {status, text|error, content, reasoning, usage, finish_reason, provider, id, got_first_token}."""
    out: dict[str, Any] = {"status": None, "content": "", "reasoning": "", "usage": None, "finish_reason": None,
                           "native_finish_reason": None, "provider": None, "id": None, "got_first_token": False}
    t0 = time.time()
    async with session.post(url, json=body, headers=headers,
                            timeout=aiohttp.ClientTimeout(total=total_s + 60, sock_connect=60)) as resp:
        out["status"] = resp.status
        if resp.status != 200:
            out["text"] = await resp.text()
            return out
        buf = b""
        while True:
            if stop.flag:
                out["finish_reason"] = out["finish_reason"] or "cancelled_stop"
                return out
            if time.time() - t0 > total_s:
                out["finish_reason"] = "total_cap_900s"
                return out
            try:
                chunk = await asyncio.wait_for(resp.content.readany(), timeout=idle_s)
            except asyncio.TimeoutError:
                out["finish_reason"] = "idle_timeout_180s"
                return out
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line or not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    return out
                try:
                    d = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if d.get("error"):
                    out["stream_error"] = d["error"]
                    msg = json.dumps(d["error"])
                    if BUDGET_MSG in msg:
                        out["status"] = 403
                        out["text"] = msg
                        return out
                out["provider"] = d.get("provider") or out["provider"]
                out["id"] = d.get("id") or out["id"]
                if d.get("usage"):
                    out["usage"] = d["usage"]
                for ch in d.get("choices") or []:
                    delta = ch.get("delta") or {}
                    if delta.get("content"):
                        out["content"] += delta["content"]
                        out["got_first_token"] = True
                    if delta.get("reasoning"):
                        out["reasoning"] += delta["reasoning"]
                        out["got_first_token"] = True
                    if ch.get("finish_reason"):
                        out["finish_reason"] = ch["finish_reason"]
                    if ch.get("native_finish_reason"):
                        out["native_finish_reason"] = ch["native_finish_reason"]
    return out


async def call_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: Stop, item: dict[str, Any],
                   out_path: Path, purpose: str, url: str, thinking: bool = True, max_tokens: int = MAX_TOKENS,
                   cap: float = COST_CAP_USD, idle_s: float = IDLE_S, total_s: float = TOTAL_S) -> dict[str, Any] | None:
    if stop.flag:
        return None
    async with sem:
        if stop.flag:                        # re-checked after the slot is acquired, before sending
            return None
        if total_cost() >= cap:
            stop.set(f"artifact cost cap {cap} reached")
            return None
        headers = {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', 'test')}",
                   "Content-Type": "application/json"}
        body = body_for(item, thinking, max_tokens)
        t0 = time.time()
        res: dict[str, Any] | None = None
        for attempt in range(3):
            if stop.flag:
                return None
            try:
                res = await _stream(session, url, body, headers, stop, idle_s, total_s)
            except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
                res = {"status": None, "error": f"{type(e).__name__}: {e}"[:200], "got_first_token": False,
                       "content": "", "reasoning": "", "usage": None, "finish_reason": "connection_error"}
            st = res.get("status")
            if st == 403 and BUDGET_MSG in (res.get("text") or ""):
                add_cost(purpose, 0.0, refused=True)
                stop.set(f"budget 403: {trunc(res.get('text'), 200)}")
                return None
            retryable = (st in (429, 500, 502, 503, 504) or (st is not None and st >= 520) or st is None) and \
                not res.get("got_first_token")
            if retryable and attempt < 2:
                logger.warning(f"{item['model_key']} {item['cell']} slot {item['slot']} status {st} attempt "
                               f"{attempt}: {trunc(res.get('text') or res.get('error'), 160)}")
                await asyncio.sleep(10 if attempt == 0 else 30)
                continue
            break
        assert res is not None
        if stop.flag and res.get("finish_reason") == "cancelled_stop":
            return None
        usage = res.get("usage") or {}
        cost = usage.get("cost")
        m = MODELS[item["model_key"]]
        rtok = ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0
        estimated = False
        if cost is None:                     # aborted stream: estimate from characters (~4 chars per token)
            est_out = (len(res.get("content") or "") + len(res.get("reasoning") or "")) / 4.0
            cost = len(item["prompt"]) / 4.0 * m["price_in"] + est_out * m["price_out"]
            estimated = True
        tot = add_cost(purpose, float(cost), estimated=estimated)
        content = res.get("content") or ""
        reasoning = res.get("reasoning") or ""
        if "</think>" in content:
            pre, post = content.split("</think>", 1)
            reasoning = (reasoning + "\n" + pre.replace("<think>", "")).strip()
            content = post.strip()
        row = {**item, "model": m["model"], "engine": "openrouter", "prompt_sha256": sha256_text(item["prompt"]),
               "content": content, "reasoning": reasoning, "finish_reason": res.get("finish_reason"),
               "native_finish_reason": res.get("native_finish_reason"), "provider": res.get("provider"),
               "http_status": res.get("status"), "error": res.get("error") or res.get("text") or
               res.get("stream_error"), "prompt_tokens": usage.get("prompt_tokens"),
               "completion_tokens": usage.get("completion_tokens"), "reasoning_tokens": rtok,
               "cost_usd": float(cost), "cost_estimated": estimated, "max_tokens": body["max_tokens"],
               "gen_seconds": round(time.time() - t0, 2), "utc": utc_now(), "or_id": res.get("id"),
               "thinking": thinking}
        if res.get("status") != 200 and not content:
            row["failed"] = True
        append_jsonl(out_path, row)
        logger.debug(f"{item['model_key']} {item['cell']} s{item['slot']} {row['provider']} fin={row['finish_reason']}"
                     f" rtok={rtok} ctok={row['completion_tokens']} {row['gen_seconds']}s ${cost:.5f} tot ${tot:.4f}")
        return row


async def run_items(items: list[dict[str, Any]], out_for: Callable[[dict[str, Any]], Path], purpose: str,
                    concurrency: int = 8, url: str | None = None, thinking: bool = True,
                    max_tokens: int = MAX_TOKENS, cap: float = COST_CAP_USD, idle_s: float = IDLE_S,
                    total_s: float = TOTAL_S, stop: Stop | None = None, sem: asyncio.Semaphore | None = None,
                    key: Callable[[dict[str, Any]], tuple] | None = None) -> dict[str, Any]:
    """Skips items already present in their output file (resume by key, default (model_key, cell, slot))."""
    url = url or os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    key = key or (lambda r: (r.get("model_key"), r.get("cell"), int(r.get("slot"))))
    sem = sem or asyncio.Semaphore(concurrency)
    stop = stop or Stop()
    done: set = set()
    for p in {str(out_for(it)) for it in items}:
        done |= {key(r) for r in read_jsonl(Path(p))}
    todo = [it for it in items if key(it) not in done]
    logger.info(f"[{purpose}] {len(todo)} calls ({len(items) - len(todo)} already done)")
    t0 = time.time()
    n_ok = 0
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(call_one(session, sem, stop, it, out_for(it), purpose, url, thinking, max_tokens,
                                              cap, idle_s, total_s)) for it in todo]
        for i, f in enumerate(asyncio.as_completed(tasks), 1):
            try:
                r = await f
                n_ok += int(r is not None)
            except asyncio.CancelledError:
                pass
            except Exception as e:  # noqa: BLE001 - one failed call must not stop the batch
                logger.error(f"call exception {type(e).__name__}: {e}")
            if i % 10 == 0 or i == len(tasks):
                logger.info(f"[{purpose}] {i}/{len(tasks)} done, {time.time() - t0:.0f}s, spend ${total_cost():.3f}")
            if stop.flag:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                break
    return {"stopped": stop.flag, "reason": stop.reason, "n_tasks": len(todo), "n_ok": n_ok,
            "seconds": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------------------------------- U8 mocks
async def _mock_tests(tmp_dir: Path) -> dict[str, Any]:
    from aiohttp import web
    hits = {"n403": 0, "slow": 0}

    async def h403(request: web.Request) -> web.Response:
        hits["n403"] += 1
        await asyncio.sleep(0.3)
        return web.Response(status=403, text=json.dumps({"error": {"message": BUDGET_MSG + " exhausted (mock)"}}))

    async def hslow(request: web.Request) -> web.StreamResponse:
        hits["slow"] += 1
        mode = request.query.get("mode", "idle")
        resp = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        chunk = {"choices": [{"delta": {"content": "x"}}]}
        if mode == "idle":
            await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
            await asyncio.sleep(3.0)          # longer than the accelerated idle timeout (1 s)
        else:
            for _ in range(40):               # keeps streaming past the accelerated total cap (2 s)
                await resp.write(f"data: {json.dumps(chunk)}\n\n".encode())
                await asyncio.sleep(0.1)
        await resp.write(b"data: [DONE]\n\n")
        return resp

    app = web.Application()
    app.router.add_post("/a/chat/completions", h403)
    app.router.add_post("/b/chat/completions", hslow)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
    base = f"http://127.0.0.1:{port}"
    items = [{"cell": "MOCK", "slot": i, "seed": i + 1, "prompt": "x", "model_key": "q32"} for i in range(24)]
    out = tmp_dir / "mock_403_rows.jsonl"
    out.unlink(missing_ok=True)
    r1 = await run_items(items, lambda it: out, "mock403", concurrency=4, url=f"{base}/a/chat/completions", cap=1e9)
    rows = read_jsonl(out)
    t403 = {"server_hits": hits["n403"], "rows_written": len(rows), "stopped": r1["stopped"],
            "passed": bool(r1["stopped"] and hits["n403"] <= 4 and not rows)}
    out2 = tmp_dir / "mock_slow_rows.jsonl"
    out2.unlink(missing_ok=True)
    t1 = time.time()
    await run_items(items[:1], lambda it: out2, "mockslow", url=f"{base}/b/chat/completions?mode=idle", cap=1e9,
                    idle_s=1.0, total_s=2.0)
    await run_items([dict(items[1])], lambda it: out2, "mockslow", url=f"{base}/b/chat/completions?mode=cap",
                    cap=1e9, idle_s=1.0, total_s=2.0)
    rows2 = read_jsonl(out2)
    fins = [r["finish_reason"] for r in rows2]
    await runner.cleanup()
    tslow = {"finish_reasons": fins, "seconds": round(time.time() - t1, 1),
             "passed": fins == ["idle_timeout_180s", "total_cap_900s"]}
    return {"mock_403": t403, "slow_stream": tslow, "passed": bool(t403["passed"] and tslow["passed"]),
            "note": "accelerated timers: idle 1 s, total 2 s (production 180 s / 900 s)"}


def unit_test_u8(tmp_dir: Path) -> dict[str, Any]:
    from common import COST_FILE, read_json, write_json
    before = read_json(COST_FILE) if COST_FILE.exists() else None
    try:
        return asyncio.run(_mock_tests(tmp_dir))
    finally:                                   # mock calls must not pollute the real ledger
        if before is not None:
            write_json(COST_FILE, before)
