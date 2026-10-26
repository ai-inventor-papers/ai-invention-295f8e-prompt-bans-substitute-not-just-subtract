"""S5: vLLM generation engine (never alive at the same time as the HF process).

Every request is a TokensPrompt built from exact token ids, so continuations re-use the base path's own tokens.
"""

from __future__ import annotations

import os
import time

from loguru import logger

from common import MODEL_ID, stable_seed

STOP = ["\n```\n"]  # closing code fence: logged deviation that only cuts post-code prose
ENGINE_INFO: dict = {}


def load_engine(max_num_seqs: int = 48):
    os.environ.setdefault("VLLM_LOGGING_LEVEL", "INFO")
    from vllm import LLM
    # 0.92 / 0.95 with CUDA graphs fail on this host (torch.compile needs a C compiler); gen1 logged both failures,
    # so later phases start at the working rung of the retry ladder.
    attempts = [dict(gpu_memory_utilization=0.95, enforce_eager=True)]
    last = None
    for extra in attempts:
        try:
            t0 = time.time()
            llm = LLM(model=MODEL_ID, dtype="bfloat16", max_model_len=2048, max_num_batched_tokens=2048,
                      enable_prefix_caching=True, seed=0, max_num_seqs=max_num_seqs, **extra)
            ENGINE_INFO.update(extra)
            ENGINE_INFO["load_s"] = round(time.time() - t0, 1)
            try:
                cc = llm.llm_engine.vllm_config.cache_config
                ENGINE_INFO["num_gpu_blocks"] = cc.num_gpu_blocks
                ENGINE_INFO["block_size"] = cc.block_size
                ENGINE_INFO["kv_tokens"] = (cc.num_gpu_blocks or 0) * cc.block_size
            except AttributeError:
                pass
            logger.info(f"vLLM engine up: {ENGINE_INFO}")
            return llm
        except Exception as e:  # noqa: BLE001 - try the next memory setting
            last = e
            logger.error(f"engine init failed with {extra}: {e}")
            import gc
            gc.collect()
    raise RuntimeError(f"could not initialise vLLM for {MODEL_ID}: {last}")


def sp(T: float, max_tokens: int, seed: int, n: int = 1, stop=None, include_stop: bool = False,
       logprobs: int | None = None):
    from vllm import SamplingParams
    return SamplingParams(n=n, temperature=T, top_p=1.0, top_k=-1, max_tokens=max_tokens, seed=seed,
                          stop=STOP if stop is None else stop, include_stop_str_in_output=include_stop,
                          logprobs=logprobs, skip_special_tokens=True)


def generate(llm, prompt_ids_list: list[list[int]], params: list) -> list:
    from vllm.inputs import TokensPrompt
    prompts = [TokensPrompt(prompt_token_ids=list(p)) for p in prompt_ids_list]
    t0 = time.time()
    outs = llm.generate(prompts, params, use_tqdm=False)
    dt = time.time() - t0
    ntok = sum(len(c.token_ids) for o in outs for c in o.outputs)
    logger.info(f"generate: {len(prompts)} requests, {sum(len(o.outputs) for o in outs)} seqs, {ntok} tokens in "
                f"{dt:.1f}s = {ntok / max(dt, 1e-6):.0f} tok/s")
    return outs


def sample_scheduled(llm, jobs: list[dict], max_total: int = 1024) -> list[dict]:
    """Segmented sampling with exact per-token temperature.

    jobs[i] = {prompt_ids, segments: [(T, length|None, stop_str|None)], seed}. A segment with length None runs to the
    end of the budget; a segment with stop_str ends (and advances) when that string is produced. Every segment is one
    batched generate call over all live samples, fed the concatenated token ids so far.
    """
    from vllm.inputs import TokensPrompt
    state = [{"ids": [], "temps": [], "seg": 0, "done": False, "finish_reason": None, "stop_reason": None}
             for _ in jobs]
    rnd = 0
    while True:
        prompts, params, idx = [], [], []
        for i, (j, s) in enumerate(zip(jobs, state)):
            if s["done"]:
                continue
            if s["seg"] >= len(j["segments"]):
                s["done"] = True
                continue
            T, length, stop_str = j["segments"][s["seg"]]
            remaining = max_total - len(s["ids"])
            if remaining <= 0:
                s["done"], s["finish_reason"] = True, "length"
                continue
            mt = remaining if length is None else min(length, remaining)
            stops = ([stop_str] if stop_str else []) + STOP
            prompts.append(TokensPrompt(prompt_token_ids=list(j["prompt_ids"]) + s["ids"]))
            params.append(sp(T, mt, stable_seed(j["seed"], s["seg"], len(s["ids"])), stop=stops,
                             include_stop=bool(stop_str)))
            idx.append(i)
        if not prompts:
            break
        rnd += 1
        t0 = time.time()
        outs = llm.generate(prompts, params, use_tqdm=False)
        ntok = 0
        for i, o in zip(idx, outs):
            c = o.outputs[0]
            s, j = state[i], jobs[i]
            T, length, stop_str = j["segments"][s["seg"]]
            new = list(c.token_ids)
            ntok += len(new)
            s["ids"] += new
            s["temps"] += [T] * len(new)
            if c.finish_reason == "stop":
                if stop_str is not None and c.stop_reason == stop_str:
                    s["seg"] += 1
                else:
                    s["done"], s["finish_reason"], s["stop_reason"] = True, "stop", c.stop_reason
            else:  # length
                if length is None or len(s["ids"]) >= max_total:
                    s["done"], s["finish_reason"] = True, "length"
                else:
                    s["seg"] += 1
        logger.debug(f"scheduled round {rnd}: {len(prompts)} live, {ntok} tokens, {time.time() - t0:.1f}s")
    return state
