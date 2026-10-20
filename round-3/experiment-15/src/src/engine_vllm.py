#!/usr/bin/env python3
"""vLLM 0.11 (V1, in-process engine core) sampling engine.

* Token-id prompts (TokensPrompt), every SamplingParams field passed explicitly (T=1.0, top_p=1.0, top_k off, min_p 0,
  no penalties); generation_config='vllm' so Llama's generation_config defaults (T 0.6 / top-p 0.9) never leak.
* VetoAdapter: a request-level logits processor (AdapterLogitsProcessor) that sets logits[g[-1]] = -inf whenever the
  last n-1 tokens of prompt_ids + output_ids equal g[:-1], for every n-gram g in SamplingParams.extra_args['veto'].
  Because the prompt ids are consulted, n-grams straddling a truncate point are caught.
* Push hooks (random directions): forward hooks on decoder layers 11..21 that add n_{l,i} * r_l to the residual stream
  of registered requests at their task-specification positions during PREFILL only (decode positions are >= the
  prompt length, so they are never touched; prefix caching is disabled in that session).
"""

from __future__ import annotations

import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")          # no C compiler in this container (Triton cannot build)
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")  # engine core in-process: hooks + logits processors
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import time  # noqa: E402
from typing import Any, Callable, Optional  # noqa: E402

import torch  # noqa: E402
from loguru import logger  # noqa: E402

from vllm import LLM, SamplingParams  # noqa: E402
from vllm.inputs import TokensPrompt  # noqa: E402
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor  # noqa: E402

from src.ws import EOS_IDS, model_path  # noqa: E402

NEG_INF = float("-inf")


# ------------------------------------------------------------------------------------------------ veto processor
def _make_veto_fn(grams: list[list[int]]) -> Callable:
    grams = [list(map(int, g)) for g in grams if g]

    def fn(prompt_ids: list[int], output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
        no = len(output_ids)
        for g in grams:
            n = len(g)
            if n == 1:
                logits[g[0]] = NEG_INF
                continue
            need = n - 1
            if no >= need:
                tail = output_ids[no - need:]
            else:
                tail = list(prompt_ids[len(prompt_ids) - (need - no):]) + list(output_ids)
            if tail == g[:-1]:
                logits[g[-1]] = NEG_INF
        return logits

    return fn


class VetoAdapter(AdapterLogitsProcessor):
    """Persistent / iterated n-gram veto (exact masking of the completing token)."""

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(self, params: SamplingParams) -> Optional[Callable]:
        ea = params.extra_args or {}
        grams = ea.get("veto")
        if not grams:
            return None
        return _make_veto_fn(grams)


# ------------------------------------------------------------------------------------------------ engine
def make_llm(*, prefix_caching: bool = True, gpu_mem: float = 0.92, max_num_seqs: int = 64,
             max_model_len: int = 2048) -> LLM:
    t0 = time.time()
    llm = LLM(model=model_path(), dtype="bfloat16", gpu_memory_utilization=gpu_mem, max_model_len=max_model_len,
              enable_prefix_caching=prefix_caching, max_num_seqs=max_num_seqs, max_num_batched_tokens=2048, seed=0,
              enforce_eager=True, generation_config="vllm", logits_processors=[VetoAdapter])
    logger.info(f"vLLM ready in {time.time() - t0:.0f}s (prefix_caching={prefix_caching}, gpu_mem={gpu_mem})")
    return llm


def sampling(max_tokens: int, seed: int, *, logit_bias: dict[int, float] | None = None,
             veto: list[list[int]] | None = None) -> SamplingParams:
    return SamplingParams(n=1, temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, repetition_penalty=1.0,
                          presence_penalty=0.0, frequency_penalty=0.0, max_tokens=int(max_tokens), seed=int(seed),
                          stop_token_ids=list(EOS_IDS), detokenize=True, skip_special_tokens=True,
                          logit_bias=logit_bias, extra_args=({"veto": veto} if veto else None))


def effective_params(sp: SamplingParams) -> dict[str, Any]:
    return {"temperature": sp.temperature, "top_p": sp.top_p, "top_k": sp.top_k, "min_p": sp.min_p,
            "repetition_penalty": sp.repetition_penalty, "presence_penalty": sp.presence_penalty,
            "frequency_penalty": sp.frequency_penalty, "max_tokens": sp.max_tokens, "seed": sp.seed,
            "stop_token_ids": sp.stop_token_ids, "logit_bias": sp.logit_bias,
            "extra_args": sp.extra_args}


def generate(llm: LLM, reqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """reqs: [{prompt_ids, max_tokens, seed, logit_bias?, veto?}] -> [{out_ids, text, finish_reason, n_new_tokens}]."""
    if not reqs:
        return []
    prompts = [TokensPrompt(prompt_token_ids=list(map(int, r["prompt_ids"]))) for r in reqs]
    sps = [sampling(r["max_tokens"], r["seed"], logit_bias=r.get("logit_bias"), veto=r.get("veto")) for r in reqs]
    outs = llm.generate(prompts, sps, use_tqdm=False)
    res = []
    for o in outs:
        c = o.outputs[0]
        res.append({"out_ids": list(map(int, c.token_ids)), "text": c.text, "finish_reason": c.finish_reason,
                    "n_new_tokens": len(c.token_ids)})
    return res


# ------------------------------------------------------------------------------------------------ push hooks
class PushHooks:
    """Adds n_{l,i} * r_l at the spec positions of registered requests (keyed by prompt-id tuple) during prefill.

    registry: {prompt_key: {"spec_start": int, "norms": FloatTensor[L, S] (one row per layer in PUSH_LAYERS)}}
    directions: FloatTensor[L, d] unit vectors (one per layer), shared across positions.
    """

    def __init__(self, llm: LLM, layers: list[int]):
        self.llm = llm
        self.layers = layers
        core = llm.llm_engine.engine_core.engine_core
        self.runner = core.model_executor.driver_worker.worker.model_runner
        self.model = self.runner.model
        self.registry: dict[tuple, dict[str, Any]] = {}
        self.directions: torch.Tensor | None = None
        self.plan: dict[str, Any] | None = None
        self.stats = {"steps": 0, "perturbed_tokens": 0, "added_norm_sum": 0.0, "target_norm_sum": 0.0}
        self.key_cache: dict[str, Optional[tuple]] = {}
        self._so = None
        orig = self.runner.execute_model

        def wrapped(scheduler_output, *a, **k):
            self._so = scheduler_output
            self.plan = None
            return orig(scheduler_output, *a, **k)

        self.runner.execute_model = wrapped
        self.handles = []
        dec_layers = self.model.model.layers
        self.handles.append(dec_layers[layers[0]].register_forward_pre_hook(self._pre_hook))
        for li, l in enumerate(layers):
            self.handles.append(dec_layers[l].register_forward_hook(self._make_hook(li)))

    def set(self, registry: dict[tuple, dict[str, Any]], directions: torch.Tensor | None) -> None:
        self.registry = registry
        self.directions = directions
        self.key_cache = {}

    def _req_key(self, rid: str) -> Optional[tuple]:
        if rid in self.key_cache:
            return self.key_cache[rid]
        st = self.runner.requests.get(rid)
        key = tuple(st.prompt_token_ids) if st is not None and st.prompt_token_ids is not None else None
        key = key if key in self.registry else None
        self.key_cache[rid] = key
        return key

    def _pre_hook(self, module, args):
        """Build the per-step plan: flat token indices to perturb, their layer-norm rows and offsets."""
        self.plan = None
        if not self.registry or self.directions is None or self._so is None:
            return None
        positions = args[0]
        ib = self.runner.input_batch
        so = self._so
        req_ids = ib.req_ids
        pos_cpu = None
        idx, rows, offs = [], [], []
        cum = 0
        for row, rid in enumerate(req_ids):
            n = int(so.num_scheduled_tokens.get(rid, 0))
            if n == 0:
                continue
            key = self._req_key(rid)
            if key is not None:
                ent = self.registry[key]
                s0 = ent["spec_start"]
                S = ent["norms"].shape[1]
                if pos_cpu is None:
                    pos_cpu = positions.detach().to("cpu").tolist()
                for j in range(n):
                    p = pos_cpu[cum + j]
                    if s0 <= p < s0 + S and p < len(key):
                        idx.append(cum + j)
                        rows.append(key)
                        offs.append(p - s0)
            cum += n
        if not idx:
            return None
        dev = positions.device
        # norms per selected token: [L, T]
        norm_cols = torch.stack([self.registry[k]["norms_dev"][:, o] for k, o in zip(rows, offs)], dim=1)
        self.plan = {"idx": torch.tensor(idx, device=dev, dtype=torch.long), "norms": norm_cols}
        self.stats["steps"] += 1
        self.stats["perturbed_tokens"] += len(idx)
        return None

    def _make_hook(self, li: int):
        def hook(module, args, output):
            if self.plan is None:
                return None
            hs = output[0] if isinstance(output, tuple) else output
            idx = self.plan["idx"]
            vec = self.directions[li].to(hs.dtype)            # [d]
            add = self.plan["norms"][li].to(hs.dtype)[:, None] * vec[None, :]   # [T, d]
            hs.index_add_(0, idx, add)
            if li == len(self.layers) - 1:
                self.stats["added_norm_sum"] += float(add.float().norm(dim=1).sum())
                self.stats["target_norm_sum"] += float(self.plan["norms"][li].float().sum())
            return None
        return hook

    def remove(self) -> None:
        for h in self.handles:
            h.remove()
        self.handles = []
