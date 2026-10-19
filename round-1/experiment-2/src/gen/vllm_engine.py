#!/usr/bin/env python3
"""vLLM engine construction (with the pre-declared FIT ladder) and token-id batched sampling.

Every request is a dict with prompt_ids, seed, max_tokens and (optionally) stop. The same token ids
are used later by the HF phases, so R is the same token in both engines.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import MODEL_ID, add_deviation, sha256_text  # noqa: E402

CLOSE_FENCE_STOP = "\n```\n"
CODE_RE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)(?:\n```|\Z)", re.DOTALL)


def extract_code(text: str) -> str | None:
    m = CODE_RE.search(text)
    if not m:
        return None
    code = m.group(1)
    code = code.rstrip("`").rstrip()
    return code if code.strip() else None


def make_llm(logger, max_num_seqs: int = 48):
    """Build the vLLM engine, stepping through the FIT ladder on failure."""
    from vllm import LLM

    ladder = [
        dict(gpu_memory_utilization=0.90, max_model_len=2048, max_num_seqs=max_num_seqs, max_num_batched_tokens=4096),
        dict(gpu_memory_utilization=0.92, max_model_len=2048, max_num_seqs=16, max_num_batched_tokens=2048),
        dict(gpu_memory_utilization=0.95, max_model_len=2048, max_num_seqs=8, max_num_batched_tokens=1024,
             enforce_eager=True),
        dict(gpu_memory_utilization=0.95, max_model_len=2048, max_num_seqs=16, max_num_batched_tokens=2048,
             kv_cache_dtype="fp8"),
    ]
    last_err = None
    for i, kw in enumerate(ladder):
        try:
            t0 = time.time()
            llm = LLM(model=MODEL_ID, dtype="bfloat16", seed=0, enable_prefix_caching=True, **kw)
            logger.info(f"vLLM engine up with {kw} in {time.time() - t0:.0f}s")
            if i > 0:
                add_deviation(f"vLLM FIT ladder step {i} used: {kw}")
            return llm
        except (RuntimeError, ValueError, MemoryError) as e:  # engine init failures surface as these
            last_err = e
            logger.error(f"vLLM init failed with {kw}: {str(e)[:400]}")
            import gc

            gc.collect()
            try:
                import torch

                torch.cuda.empty_cache()
            except ImportError:
                pass
    raise RuntimeError(f"vLLM could not be initialised: {last_err}")


def sample(llm, requests: list[dict], logger, temperature: float = 1.0) -> list[dict]:
    """Run one vLLM generate call over requests; returns rows with raw text, finish reason and token counts."""
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt

    prompts = [TokensPrompt(prompt_token_ids=r["prompt_ids"]) for r in requests]
    sps = []
    for r in requests:
        stop = r.get("stop", [CLOSE_FENCE_STOP])
        sps.append(SamplingParams(temperature=temperature, top_p=1.0, top_k=-1 if _topk_neg() else 0, min_p=0.0,
                                  max_tokens=r["max_tokens"], seed=r["seed"], stop=stop,
                                  include_stop_str_in_output=True))
    if requests:
        logger.debug(f"SamplingParams example: {sps[0]}")
    t0 = time.time()
    outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
    dt = time.time() - t0
    rows = []
    ntok = 0
    for r, o in zip(requests, outs):
        c = o.outputs[0]
        text = c.text
        ntok += len(c.token_ids)
        code = extract_code(text)
        rows.append({k: v for k, v in r.items() if k not in ("prompt_ids", "stop")} | {
            "raw_text": text, "finish_reason": c.finish_reason, "stop_reason": str(c.stop_reason),
            "n_gen_tokens": len(c.token_ids), "code": code, "code_sha256": sha256_text(code) if code else None,
        })
    logger.info(f"vLLM sampled {len(requests)} requests, {ntok} tokens in {dt:.1f}s ({ntok / max(dt, 1e-6):.0f} tok/s)")
    return rows


_TOPK_CACHE: dict[str, bool] = {}


def _topk_neg() -> bool:
    """Whether this vLLM version uses -1 (True) or 0 (False) to disable top-k."""
    if "v" in _TOPK_CACHE:
        return _TOPK_CACHE["v"]
    from vllm import SamplingParams

    try:
        SamplingParams(top_k=-1)
        _TOPK_CACHE["v"] = True
    except (ValueError, TypeError):
        _TOPK_CACHE["v"] = False
    return _TOPK_CACHE["v"]
