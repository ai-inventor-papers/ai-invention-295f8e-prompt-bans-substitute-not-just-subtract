"""Local vLLM client (completions API with token-id prompts). Explicit base_url/api_key: OPENAI_BASE_URL points at
OpenRouter, so the default client must never be used for the local server."""
from __future__ import annotations

import asyncio
import time

from prompt import STOPS

BASE_URL = "http://127.0.0.1:8000/v1"
SERVED = "qwen3-8b"
ENGINE_TAG = "vllm0.11.0|Qwen3-8B-FP8@220b46e|{kernel}|{mode}"
TIMEOUT = 180
RETRIES = 2
MAX_TOKENS = 512
R1_TOKENS = 48

_CLIENT = None


def client():
    global _CLIENT
    if _CLIENT is None:
        from openai import AsyncOpenAI

        _CLIENT = AsyncOpenAI(base_url=BASE_URL, api_key="EMPTY", timeout=TIMEOUT, max_retries=0)
    return _CLIENT


EXTRA = {"return_tokens_as_token_ids": True, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0}


def _parse_tid(s: str) -> int:
    if not s.startswith("token_id:"):
        raise ValueError(f"token not returned as id: {s!r}")
    return int(s.split(":", 1)[1])


async def complete(prompt_ids: list[int], *, temperature: float, top_p: float, max_tokens: int, seed: int,
                   logprobs: int | None = None) -> dict:
    """One completion; returns text, finish reason, token ids, per-position top logprobs, usage, wall."""
    last_err = None
    for attempt in range(RETRIES + 1):
        t0 = time.time()
        try:
            kw = dict(model=SERVED, prompt=prompt_ids, max_tokens=max_tokens, temperature=temperature, top_p=top_p,
                      seed=seed, stop=STOPS, presence_penalty=0.0, frequency_penalty=0.0, n=1,
                      extra_body=dict(EXTRA))
            if logprobs:
                kw["logprobs"] = logprobs
            r = await client().completions.create(**kw)
            ch = r.choices[0]
            out = {"text": ch.text, "finish_reason": ch.finish_reason,
                   "stop_reason": getattr(ch, "stop_reason", None),
                   "prompt_tokens": r.usage.prompt_tokens if r.usage else None,
                   "completion_tokens": r.usage.completion_tokens if r.usage else None,
                   "wall": time.time() - t0, "attempts": attempt + 1}
            if logprobs and ch.logprobs is not None:
                out["token_ids"] = [_parse_tid(t) for t in ch.logprobs.tokens]
                out["top"] = [({_parse_tid(k): float(v) for k, v in d.items()} if d else {})
                              for d in (ch.logprobs.top_logprobs or [])]
                out["token_logprobs"] = [float(x) if x is not None else None for x in ch.logprobs.token_logprobs]
            return out
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - network / server errors are retried, then recorded
            last_err = f"{type(e).__name__}: {str(e)[:300]}"
            await asyncio.sleep(2.0 * (attempt + 1))
    return {"error": last_err, "text": None}
