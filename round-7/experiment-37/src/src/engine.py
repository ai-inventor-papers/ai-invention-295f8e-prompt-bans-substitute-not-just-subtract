#!/usr/bin/env python3
"""Generation engines behind one interface: generate(list[Req]) -> list[list[Child]].

VLLMEngine: Qwen3-8B (or -Base) bf16 at the pinned revision from the shared HF cache, max_model_len 4096,
prefix caching, max_num_seqs 48, seed 7101; per-request SamplingParams(T 1.0, top-p 1, no top-k, n, seed). Wall time of
each generate() call is apportioned to requests by generated + uncached prompt tokens (gpu_seconds per child).
APIEngine: OpenRouter chat model (the optional large-mutator arm L); n independent calls per prompt.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from common import BASE_ID, BASE_REV, MODEL_ID, MODEL_REV, TEMPERATURE, TOP_P, VLLM_SEED, sha256_text


@dataclass
class Req:
    user_text: str | None = None                 # single user turn
    messages: list[dict[str, str]] | None = None  # multi-turn (EAP stage 2)
    assistant_prefix: str | None = None           # forced start of the assistant turn (BINT)
    raw_prompt: str | None = None                 # already formatted prompt (base-model intents)
    n: int = 1
    seed: int = 0
    max_tokens: int = 1024
    stop: list[str] = field(default_factory=lambda: ["\n```\n"])
    tag: dict[str, Any] = field(default_factory=dict)
    temperature: float = TEMPERATURE


def snapshot_path(model_id: str, rev: str) -> str:
    hub = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME", ""), "hub")
    p = Path(hub) / ("models--" + model_id.replace("/", "--")) / "snapshots" / rev
    if p.exists():
        return str(p)
    from huggingface_hub import snapshot_download
    return snapshot_download(model_id, revision=rev)


class VLLMEngine:
    def __init__(self, base: bool = False, max_model_len: int = 4096, gpu_util: float = 0.92, max_num_seqs: int = 48,
                 enforce_eager: bool = False) -> None:
        from transformers import AutoTokenizer
        from vllm import LLM

        from prompts import ChatFormatter
        mid, rev = (BASE_ID, BASE_REV) if base else (MODEL_ID, MODEL_REV)
        self.model_id, self.rev = mid, rev
        path = snapshot_path(mid, rev)
        self.tok = AutoTokenizer.from_pretrained(path)
        self.fmt = ChatFormatter(self.tok)
        attempts = [dict(enforce_eager=enforce_eager, max_model_len=max_model_len, max_num_seqs=max_num_seqs),
                    dict(enforce_eager=True, max_model_len=max_model_len, max_num_seqs=max_num_seqs),
                    dict(enforce_eager=True, max_model_len=3072, max_num_seqs=24),
                    dict(enforce_eager=True, max_model_len=3072, max_num_seqs=24, cpu_offload_gb=2)]
        last: Exception | None = None
        self.config_used: dict[str, Any] = {}
        for a in attempts:
            try:
                t0 = time.time()
                self.llm = LLM(model=path, tokenizer=path, dtype="bfloat16", gpu_memory_utilization=gpu_util,
                               enable_prefix_caching=True, seed=VLLM_SEED, **a)
                self.config_used = {"model": mid, "revision": rev, "dtype": "bfloat16", "gpu_memory_utilization": gpu_util,
                                    "enable_prefix_caching": True, "seed": VLLM_SEED, **a,
                                    "load_s": round(time.time() - t0, 1)}
                logger.info(f"vLLM loaded {mid}@{rev[:8]} with {a} in {time.time() - t0:.0f}s")
                break
            except Exception as e:  # noqa: BLE001 - OOM / init failure -> next fallback (logged as deviation)
                last = e
                logger.error(f"vLLM init failed with {a}: {str(e)[:300]}")
                import gc

                import torch
                gc.collect()
                torch.cuda.empty_cache()
        else:
            raise RuntimeError(f"vLLM could not start: {last}")
        self.calls = 0

    def prompt_of(self, r: Req) -> str:
        if r.raw_prompt is not None:
            return r.raw_prompt
        if r.messages is not None:
            return self.fmt.multi(r.messages)
        p = self.fmt.user(r.user_text or "")
        return p + (r.assistant_prefix or "")

    def generate(self, reqs: list[Req]) -> list[dict[str, Any]]:
        """Returns one record per request: {prompt, prompt_sha256, children: [{text, n_new_tokens, finish_reason}],
        gpu_seconds (whole request), n_prompt_tokens, n_cached_tokens}."""
        from vllm import SamplingParams
        if not reqs:
            return []
        prompts = [self.prompt_of(r) for r in reqs]
        sps = [SamplingParams(n=r.n, temperature=r.temperature, top_p=TOP_P, top_k=-1, max_tokens=r.max_tokens,
                              stop=r.stop or None, include_stop_str_in_output=True, seed=r.seed) for r in reqs]
        t0 = time.time()
        outs = self.llm.generate(prompts, sps, use_tqdm=False)
        wall = time.time() - t0
        self.calls += 1
        recs = []
        weights = []
        for p, o in zip(prompts, outs):
            npt = len(o.prompt_token_ids or [])
            ncached = int(getattr(o, "num_cached_tokens", 0) or 0)
            kids = [{"text": c.text, "n_new_tokens": len(c.token_ids), "finish_reason": c.finish_reason}
                    for c in o.outputs]
            w = sum(k["n_new_tokens"] for k in kids) + max(0, npt - ncached)
            weights.append(w)
            recs.append({"prompt": p, "prompt_sha256": sha256_text(p), "children": kids, "n_prompt_tokens": npt,
                         "n_cached_tokens": ncached})
        tot = max(sum(weights), 1)
        for r, w in zip(recs, weights):
            r["gpu_seconds"] = wall * w / tot
        logger.debug(f"generate: {len(reqs)} reqs, {sum(len(r['children']) for r in recs)} children, {wall:.1f}s")
        self.last_wall = wall
        return recs


class APIEngine:
    """OpenRouter mutator (arm L): n independent calls per prompt; cost tracked by the ORClient guard."""

    def __init__(self, model: str, client, fallback: str | None = None) -> None:
        self.model = model
        self.fallback = fallback
        self.client = client

    def generate(self, reqs: list[Req]) -> list[dict[str, Any]]:
        async def one(r: Req, j: int) -> dict[str, Any] | None:
            msgs = r.messages or [{"role": "user", "content": r.user_text or ""}]
            res = await self.client.chat(self.model, msgs, temperature=r.temperature, top_p=TOP_P,
                                         max_tokens=r.max_tokens, use_cache=False, tag=f"L:{r.seed}:{j}")
            if res is not None and res.get("text") is None and self.fallback:
                res = await self.client.chat(self.fallback, msgs, temperature=r.temperature, top_p=TOP_P,
                                             max_tokens=r.max_tokens, use_cache=False, tag=f"Lfb:{r.seed}:{j}")
            return res

        async def run_all():
            tasks = [one(r, j) for r in reqs for j in range(r.n)]
            return await asyncio.gather(*tasks)
        t0 = time.time()
        flat = asyncio.run(run_all())
        wall = time.time() - t0
        recs = []
        k = 0
        for r in reqs:
            kids = []
            for _ in range(r.n):
                x = flat[k]
                k += 1
                if x is None or x.get("text") is None:
                    kids.append({"text": None, "n_new_tokens": 0, "finish_reason": "api_unavailable", "usd": 0.0})
                else:
                    kids.append({"text": x["text"], "n_new_tokens": x.get("completion_tokens") or 0,
                                 "finish_reason": x.get("finish_reason"), "usd": x.get("cost", 0.0),
                                 "model": x.get("model")})
            p = r.user_text or ""
            recs.append({"prompt": p, "prompt_sha256": sha256_text(p), "children": kids, "n_prompt_tokens": None,
                         "n_cached_tokens": None, "gpu_seconds": 0.0, "api_wall_s": wall / max(len(reqs), 1)})
        return recs
