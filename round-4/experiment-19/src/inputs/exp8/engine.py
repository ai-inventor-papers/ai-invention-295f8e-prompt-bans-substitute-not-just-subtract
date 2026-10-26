#!/usr/bin/env python3
"""S3 HF engine: Qwen3-8B bf16 with a knockout-capable SDPA attention ('ko_sdpa'), prompt prefill, KV-cache
splicing, teacher-forced scoring and a common-random-numbers (inverse-CDF) sampler.

Knockout: a global KO config names blocked key columns [p0, p1), a generated-index window [g_lo, g_hi) for the
query rows (g = absolute query position - P) and a layer set. When active for module.layer_idx the attention mask
is causal AND NOT (blocked column AND query in window); otherwise stock SDPA runs unchanged. The matching mask
function (sdpa_mask) is registered under the same name so stock causal masking is preserved.
"""

from __future__ import annotations

import contextlib
import gc
import math
import time
from typing import Any, Iterator

import numpy as np
import torch
from loguru import logger

from cfg import ENDOFTEXT, IM_END, MAX_NEW_TOKENS, hf_kwargs, model_path

KO: dict[str, Any] = {"active": False, "p0": 0, "p1": 0, "P": 0, "g_lo": 0, "g_hi": 10 ** 9, "layers": None}
RECORD: dict[str, Any] = {"on": False, "weights": {}}
_REGISTERED = False


def _ko_on(module: Any) -> bool:
    return bool(KO["active"]) and (KO["layers"] is None or module.layer_idx in KO["layers"])


def _ko_allowed(q_len: int, k_len: int, device: torch.device) -> torch.Tensor:
    offset = k_len - q_len
    qpos = torch.arange(offset, k_len, device=device)
    kpos = torch.arange(k_len, device=device)
    allowed = kpos[None, :] <= qpos[:, None]
    g = qpos - int(KO["P"])
    qblock = (g >= int(KO["g_lo"])) & (g < int(KO["g_hi"]))
    kblock = (kpos >= int(KO["p0"])) & (kpos < int(KO["p1"]))
    return allowed & ~(qblock[:, None] & kblock[None, :])


def _combine(allowed: torch.Tensor, attention_mask: torch.Tensor | None, k_len: int) -> torch.Tensor:
    allowed = allowed[None, None]
    if attention_mask is not None:
        am = attention_mask[:, :, :, :k_len]
        if am.dtype == torch.bool:
            allowed = allowed & am
        else:
            allowed = allowed & (am == 0)
    return allowed


def ko_sdpa(module, query, key, value, attention_mask, **kwargs):
    from transformers.integrations.sdpa_attention import sdpa_attention_forward

    if _ko_on(module):
        q_len, k_len = query.shape[2], key.shape[2]
        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)
        kwargs.pop("is_causal", None)
        return sdpa_attention_forward(module, query, key, value, allowed, is_causal=False, **kwargs)
    return sdpa_attention_forward(module, query, key, value, attention_mask, **kwargs)


def ko_eager(module, query, key, value, attention_mask, **kwargs):
    """Eager twin used only by the knockout-correctness test (U4); records attention probabilities."""
    from transformers.models.qwen3.modeling_qwen3 import eager_attention_forward

    q_len, k_len = query.shape[2], key.shape[2]
    if _ko_on(module):
        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)
    else:
        base = torch.ones(q_len, k_len, dtype=torch.bool, device=query.device).tril(k_len - q_len)
        allowed = _combine(base, attention_mask, k_len)
    fmask = torch.zeros(allowed.shape, dtype=query.dtype, device=query.device)
    fmask = fmask.masked_fill(~allowed, torch.finfo(query.dtype).min)
    out, w = eager_attention_forward(module, query, key, value, fmask, **kwargs)
    if RECORD["on"]:
        RECORD["weights"][module.layer_idx] = w.detach().float().cpu()
    return out, w


def register() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from transformers import AttentionInterface
    from transformers.masking_utils import AttentionMaskInterface, eager_mask, sdpa_mask

    AttentionInterface.register("ko_sdpa", ko_sdpa)
    AttentionInterface.register("ko_eager", ko_eager)
    AttentionMaskInterface.register("ko_sdpa", sdpa_mask)
    AttentionMaskInterface.register("ko_eager", eager_mask)
    _REGISTERED = True


@contextlib.contextmanager
def knockout(cfg: dict[str, Any] | None) -> Iterator[None]:
    """cfg: {'p0','p1','P','g_lo','g_hi','layers'} or None (no knockout)."""
    old = dict(KO)
    try:
        if cfg is not None:
            KO.update({"active": True, "g_lo": 0, "g_hi": 10 ** 9, "layers": None})
            KO.update(cfg)
        else:
            KO["active"] = False
        yield
    finally:
        KO.clear()
        KO.update(old)


def set_attn(model: Any, name: str) -> None:
    model.config._attn_implementation = name
    for m in model.modules():
        if hasattr(m, "config") and m.config is not model.config and hasattr(m.config, "_attn_implementation"):
            m.config._attn_implementation = name


def load_model(vram_fraction: float = 0.95):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    register()
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_path(), **hf_kwargs())
    model = AutoModelForCausalLM.from_pretrained(model_path(), dtype=torch.bfloat16, attn_implementation="ko_sdpa",
                                                 **hf_kwargs(),
                                                 device_map={"": 0})
    model.eval()
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"HF model loaded in {time.time() - t0:.0f}s; attn={model.config._attn_implementation}; "
                f"free VRAM {free / 1e9:.1f}/{total / 1e9:.1f} GB")
    return tok, model


# ------------------------------------------------------------------------------------------------ caches
def _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


def build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], batch: int = 1):
    from transformers.cache_utils import DynamicCache

    cache = DynamicCache()
    for l, (K, V) in enumerate(kv):
        if K.shape[0] != batch:
            K = K.expand(batch, -1, -1, -1)
            V = V.expand(batch, -1, -1, -1)
        cache.update(K.contiguous(), V.contiguous(), l)
    return cache


@torch.no_grad()
def prefill(model: Any, ids: list[int], hidden_layers: list[int] | None = None) -> dict[str, Any]:
    """Returns {'kv': per-layer (K, V) [1, 8, P, 128] on GPU, 'r_logits': float32 [V], 'P', 'hR': {l: float32}}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=model.device)
    cache = DynamicCache()
    out = model.model(input_ids=inp, past_key_values=cache, use_cache=True,
                      output_hidden_states=hidden_layers is not None)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]
    res = {"kv": kv, "r_logits": r_logits, "P": len(ids)}
    if hidden_layers is not None:
        res["hR"] = {l: out.hidden_states[l][0, -1].float().cpu().numpy() for l in hidden_layers}
    del cache, out
    return res


def splice(kv_a: list, kv_b: list, cut: int) -> list:
    """Positions [0, cut) from A and [cut, P) from B, every layer."""
    return [(torch.cat([Ka[:, :, :cut], Kb[:, :, cut:]], dim=2), torch.cat([Va[:, :, :cut], Vb[:, :, cut:]], dim=2))
            for (Ka, Va), (Kb, Vb) in zip(kv_a, kv_b)]


def replace_positions(kv_base: list, kv_src: list, positions: list[int]) -> list:
    out = []
    idx = torch.tensor(positions, device=kv_base[0][0].device)
    for (Kb, Vb), (Ks, Vs) in zip(kv_base, kv_src):
        K, V = Kb.clone(), Vb.clone()
        K[:, :, idx] = Ks[:, :, idx]
        V[:, :, idx] = Vs[:, :, idx]
        out.append((K, V))
    return out


# ------------------------------------------------------------------------------------------------ scoring
@torch.no_grad()
def _token_logprobs(model: Any, h: torch.Tensor, tgt: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    out = []
    for i in range(0, h.shape[0], chunk):
        logits = model.lm_head(h[i:i + chunk]).float()
        out.append(torch.log_softmax(logits, dim=-1).gather(-1, tgt[i:i + chunk, None])[:, 0])
    return torch.cat(out) if out else torch.zeros(0, device=h.device)


@torch.no_grad()
def score(model: Any, arm: dict[str, Any], seqs: list[list[int]], ko: dict[str, Any] | None = None,
          token_budget: int = 9000, max_batch: int = 1) -> list[np.ndarray]:
    """Teacher-forced per-token log-probs of each token sequence placed after the arm's prompt cache.
    Token 0 is scored with the arm's R logits; token t >= 1 with the hidden state at position P + t - 1.
    Default batch 1: a program's score then depends only on the cache content (identical GEMM/attention shapes in
    every arm of a template), never on which other programs share its batch (bf16 kernel choice is shape-dependent)."""
    kv, r_logits = arm["kv"], arm["r_logits"]
    P = kv[0][0].shape[2]
    r_lp = torch.log_softmax(r_logits.float(), dim=-1)
    order = sorted(range(len(seqs)), key=lambda i: -len(seqs[i]))
    res: list[np.ndarray | None] = [None] * len(seqs)
    i = 0
    bs = max_batch
    while i < len(order):
        T = len(seqs[order[i]])
        b = max(1, min(bs, token_budget // max(T, 1), len(order) - i))
        idxs = order[i:i + b]
        try:
            inp = torch.full((b, T), IM_END, dtype=torch.long, device=model.device)
            for r, k in enumerate(idxs):
                inp[r, :len(seqs[k])] = torch.tensor(seqs[k], device=model.device)
            cache = build_cache(kv, b)
            pos = torch.arange(P, P + T, device=model.device)[None].expand(b, -1)
            kcfg = None if ko is None else {**ko, "P": P}
            with knockout(kcfg):
                h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            for r, k in enumerate(idxs):
                n = len(seqs[k])
                lp = _token_logprobs(model, h[r, :n - 1], inp[r, 1:n])
                first = r_lp[seqs[k][0]].reshape(1)
                res[k] = torch.cat([first, lp]).float().cpu().numpy()
            del cache, h, inp
            i += b
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            gc.collect()
            if bs == 1 and token_budget < 600:
                raise
            bs = max(1, b // 2)
            token_budget = max(512, token_budget // 2)
            logger.warning(f"OOM in score: batch -> {bs}, token budget -> {token_budget}")
    return res  # type: ignore[return-value]


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int = MAX_NEW_TOKENS) -> np.ndarray:
    from cfg import stable_seed

    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


@torch.no_grad()
def sample(model: Any, rows: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,
           ko: dict[str, Any] | None = None, prune: bool = True) -> list[dict[str, Any]]:
    """rows: [{'kv': per-layer (K,V) [1,8,P,128], 'r_logits': [V], 'u': np.ndarray[max_new]}], all with the same P.
    One shared uniform per (row, step); token = first index whose CDF (vocabulary order, float64) >= u.
    prune=False keeps finished rows in the batch (fed <|im_end|>), so the batch shape at every step is the same in
    every arm and CRN-matched rows see identical kernels; prune=True drops them (faster, used for S2)."""
    B = len(rows)
    P = rows[0]["kv"][0][0].shape[2]
    assert all(r["kv"][0][0].shape[2] == P for r in rows)
    dev = model.device
    kv = [(torch.cat([r["kv"][l][0] for r in rows], 0), torch.cat([r["kv"][l][1] for r in rows], 0))
          for l in range(len(rows[0]["kv"]))]
    cache = build_cache(kv, B)
    del kv
    U = torch.tensor(np.stack([r["u"][:max_new] for r in rows]), dtype=torch.float64, device=dev)
    logits = torch.stack([r["r_logits"] for r in rows]).double()
    alive = list(range(B))
    toks: list[list[int]] = [[] for _ in range(B)]
    lps: list[list[float]] = [[] for _ in range(B)]
    finish = ["length"] * B
    done: set[int] = set()
    kcfg = None if ko is None else {**ko, "P": P}
    step = 0
    while True:
        probs = torch.softmax(logits / temperature, dim=-1)
        nxt_t = _inverse_cdf(probs, U[alive, step])
        plp = torch.log(probs.gather(-1, nxt_t[:, None])[:, 0]).tolist()
        nxt = nxt_t.tolist()
        keep = []
        for j, (r, t) in enumerate(zip(alive, nxt)):
            if r in done:
                continue
            toks[r].append(int(t))
            lps[r].append(float(plp[j]))
            if t in (IM_END, ENDOFTEXT):
                finish[r] = "stop"
                done.add(r)
            elif len(toks[r]) < max_new:
                keep.append(j)
            else:
                done.add(r)
        if not keep:
            break
        if not prune:
            nxt = [IM_END if r in done else t for r, t in zip(alive, nxt)]
        elif len(keep) < len(alive):
            idx = torch.tensor(keep, device=dev)
            if hasattr(cache, "batch_select_indices"):
                cache.batch_select_indices(idx)
            else:
                kvn = [(K[idx], V[idx]) for K, V in _kv_list(cache)]
                cache = build_cache(kvn, len(keep))
            alive = [alive[j] for j in keep]
            nxt = [nxt[j] for j in keep]
        inp = torch.tensor(nxt, device=dev)[:, None]
        pos = torch.full((len(alive), 1), P + step, device=dev, dtype=torch.long)
        with knockout(kcfg):
            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    return [{"token_ids": toks[r], "finish_reason": finish[r], "n_tokens": len(toks[r]),
             "logprob_sum": float(np.sum(lps[r])), "token_logprobs": lps[r]} for r in range(B)]


def sample_grouped(model: Any, reqs: list[dict[str, Any]], prefill_cache: dict[str, Any] | None = None,
                   max_batch: int = 24, ko: dict[str, Any] | None = None, callback: Any = None) -> list[dict[str, Any]]:
    """reqs: [{'ids': prompt ids, 'u': uniforms}] with any prompt lengths; batches rows of equal prompt length.
    Each distinct prompt is prefilled once (prefill_cache keyed by the ids' string)."""
    cache = {} if prefill_cache is None else prefill_cache
    out: list[dict[str, Any] | None] = [None] * len(reqs)
    by_len: dict[int, list[int]] = {}
    for i, r in enumerate(reqs):
        by_len.setdefault(len(r["ids"]), []).append(i)
    t0 = time.time()
    n_done = 0
    for P, idxs in sorted(by_len.items()):
        for s in range(0, len(idxs), max_batch):
            chunk = idxs[s:s + max_batch]
            rows = []
            for i in chunk:
                key = ",".join(map(str, reqs[i]["ids"]))
                if key not in cache:
                    cache[key] = prefill(model, reqs[i]["ids"])
                pre = cache[key]
                rows.append({"kv": pre["kv"], "r_logits": pre["r_logits"], "u": reqs[i]["u"]})
            res = sample(model, rows, ko=ko)
            for i, r in zip(chunk, res):
                out[i] = r
            n_done += len(chunk)
            if callback is not None:
                callback([(i, out[i]) for i in chunk])
            logger.info(f"sample_grouped: {n_done}/{len(reqs)} rows (P={P}, batch {len(chunk)}, "
                        f"max len {max(r['n_tokens'] for r in res)}) {time.time() - t0:.0f}s")
        cache.clear()
        torch.cuda.empty_cache()
    return out  # type: ignore[return-value]


def free(*objs: Any) -> None:
    for o in objs:
        del o
    gc.collect()
    torch.cuda.empty_cache()


def logmeanexp(x: np.ndarray, axis: int | None = None, weights: np.ndarray | None = None) -> Any:
    x = np.asarray(x, dtype=np.float64)
    if weights is None:
        m = np.max(x, axis=axis, keepdims=True)
        out = m + np.log(np.mean(np.exp(x - m), axis=axis, keepdims=True))
    else:
        w = np.asarray(weights, dtype=np.float64)
        w = w / w.sum()
        m = np.max(x, axis=axis, keepdims=True)
        out = m + np.log(np.sum(w * np.exp(x - m), axis=axis, keepdims=True))
    return np.squeeze(out, axis=axis) if axis is not None else float(out.squeeze())


def ess(logw: np.ndarray) -> float:
    lw = np.asarray(logw, dtype=np.float64)
    w = np.exp(lw - lw.max())
    return float(w.sum() ** 2 / (w ** 2).sum()) if len(w) else math.nan
