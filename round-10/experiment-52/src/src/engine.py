#!/usr/bin/env python3
"""S4 engine: the vLLM server launched with the TSP9 settings verbatim (start_vllm.sh), its log parsed into
results/engine.json, and an async /v1/completions client (prompt as token ids, timeout 180 s, at most 2 retries,
Semaphore(64))."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx  # noqa: E402
from loguru import logger  # noqa: E402

import common as C  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
PID_FILE = C.LOGS / "vllm.pid"
LOG_FILE = C.LOGS / "vllm.log"
TIMEOUT_S = 180.0
MAX_RETRIES = 2


def ensure_cc() -> str:
    """vLLM/triton need a C compiler; if none exists put the tools/cc shim (python -m ziglang cc) first on PATH."""
    for c in ("cc", "gcc", "clang"):
        if shutil.which(c):
            return f"system {c}: {shutil.which(c)}"
    shim_dir = C.ROOT / "tools"
    (shim_dir / "cc").write_text('#!/bin/sh\nexec "$(dirname "$0")/../.venv/bin/python" -m ziglang cc "$@"\n')
    (shim_dir / "cc").chmod(0o755)
    os.environ["PATH"] = f"{shim_dir}:{os.environ['PATH']}"
    os.environ["CC"] = str(shim_dir / "cc")
    return "tools/cc shim (python -m ziglang cc)"


def start_server(mode: str = "graphs") -> int:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, 0)
            logger.info(f"vLLM already running (pid {pid})")
            return pid
        except (ProcessLookupError, ValueError):
            pass
    cc = ensure_cc()
    env = dict(os.environ, VLLM_CACHE_ROOT=str(C.ROOT / "vllm_cache"), OMP_NUM_THREADS="1")
    script = C.ROOT / "start_vllm.sh"
    with open(LOG_FILE, "ab") as lf:
        p = subprocess.Popen(["bash", str(script), mode], stdout=lf, stderr=subprocess.STDOUT, env=env,
                             cwd=C.ROOT, start_new_session=True)
    PID_FILE.write_text(str(p.pid))
    logger.info(f"vLLM starting (pid {p.pid}, mode {mode}, compiler: {cc})")
    return p.pid


def stop_server() -> None:
    if not PID_FILE.exists():
        return
    try:
        pid = int(PID_FILE.read_text())
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        for _ in range(60):
            try:
                os.kill(pid, 0)
                time.sleep(1)
            except ProcessLookupError:
                break
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, ValueError):
        pass
    PID_FILE.unlink(missing_ok=True)
    logger.info("vLLM stopped")


def server_alive() -> bool:
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 0)
        return True
    except (FileNotFoundError, ProcessLookupError, ValueError):
        return False


def wait_ready(timeout_s: float = 900.0) -> bool:
    t = time.time()
    while time.time() - t < timeout_s:
        try:
            r = httpx.get(f"{BASE_URL}/v1/models", timeout=5)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        if not server_alive():
            return False
        time.sleep(5)
    return False


def parse_engine_log() -> dict:
    txt = LOG_FILE.read_text(errors="ignore") if LOG_FILE.exists() else ""
    out = {"utc": C.utc(), "engine_tag": C.ENGINE_TAG}
    for key, pat in [("model_loading", r"Model loading took ([^\n]*)"),
                     ("available_kv_cache_memory", r"Available KV cache memory: ([^\n]*)"),
                     ("gpu_kv_cache_size", r"GPU KV cache size: ([^\n]*)"),
                     ("max_concurrency", r"Maximum concurrency for ([^\n]*)")]:
        m = re.findall(pat, txt)
        out[key] = m[-1].strip() if m else None
    out["cudagraph_mode_full_decode_only"] = "FULL_DECODE_ONLY" in txt
    out["fp8_marlin"] = ("marlin" in txt.lower())
    C.write_json(C.RESULTS / "engine.json", out)
    return out


def metrics() -> dict:
    """Prefix-cache counters from the Prometheus endpoint."""
    try:
        r = httpx.get(f"{BASE_URL}/metrics", timeout=10)
    except httpx.HTTPError:
        return {}
    out = {}
    for ln in r.text.splitlines():
        if ln.startswith("#"):
            continue
        for k in ("prefix_cache_queries", "prefix_cache_hits", "num_preemptions", "generation_tokens_total",
                  "prompt_tokens_total", "gpu_cache_usage_perc", "kv_cache_usage_perc"):
            if k in ln.split("{")[0]:
                try:
                    out[ln.split("{")[0]] = float(ln.rsplit(" ", 1)[1])
                except ValueError:
                    pass
    return out


class Engine:
    """Async completions client. Every request sets the full sampling configuration."""

    def __init__(self, concurrency: int = 64):
        self.sem = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=httpx.Timeout(TIMEOUT_S))
        self.n_requests = 0
        self.n_failed = 0

    async def close(self) -> None:
        await self.client.aclose()

    async def complete(self, prompt_ids: list[int], *, max_tokens: int, temperature: float, top_p: float, seed: int,
                       stop: list[str], logprobs: int | None = None) -> dict:
        body = {"model": C.SERVED_NAME, "prompt": prompt_ids, "max_tokens": int(max_tokens),
                "temperature": float(temperature), "top_p": float(top_p), "top_k": -1, "min_p": 0.0,
                "repetition_penalty": 1.0, "seed": int(seed), "stop": stop}
        if logprobs:
            body["logprobs"] = int(logprobs)
            body["return_tokens_as_token_ids"] = True
        last = None
        async with self.sem:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    self.n_requests += 1
                    r = await self.client.post("/v1/completions", json=body)
                    if r.status_code != 200:
                        last = f"HTTP {r.status_code}: {r.text[:300]}"
                        await asyncio.sleep(1.0 + attempt)
                        continue
                    d = r.json()
                    ch = d["choices"][0]
                    out = {"text": ch.get("text") or "", "finish_reason": ch.get("finish_reason"),
                           "prompt_tokens": d.get("usage", {}).get("prompt_tokens"),
                           "completion_tokens": d.get("usage", {}).get("completion_tokens"), "error": None,
                           "attempts": attempt + 1}
                    if logprobs:
                        lp = ch.get("logprobs") or {}
                        toks = lp.get("tokens") or []
                        out["token_ids"] = [int(t.split(":", 1)[1]) for t in toks]
                        tops = []
                        for dct in lp.get("top_logprobs") or []:
                            pairs = sorted(((int(k.split(":", 1)[1]), float(v)) for k, v in (dct or {}).items()),
                                           key=lambda x: -x[1])[:20]
                            tops.append(pairs)
                        out["top"] = tops
                        out["token_logprobs"] = lp.get("token_logprobs")
                    return out
                except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
                    last = f"{type(e).__name__}: {e!r}"[:300]
                    await asyncio.sleep(1.0 + attempt)
        self.n_failed += 1
        logger.warning(f"request failed after {MAX_RETRIES + 1} attempts: {last}")
        return {"text": "", "finish_reason": "error", "prompt_tokens": len(prompt_ids), "completion_tokens": 0,
                "error": last, "token_ids": [], "top": [], "attempts": MAX_RETRIES + 1}


def load_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(C.MODEL_ID, revision=C.MODEL_REV)
