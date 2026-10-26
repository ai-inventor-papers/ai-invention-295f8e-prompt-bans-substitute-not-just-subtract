#!/usr/bin/env python3
"""HF engine for Qwen3-8B bf16, ported from exp8's engine.py (art_8_ULPE8jJQc_) and extended.

Kept from exp8 unchanged: knockout-capable SDPA attention 'ko_sdpa' (+ eager twin for the knockout test), prefill(),
splice(), replace_positions(), teacher-forced score() at batch 1, u_stream() keyed by exp8's stable_seed, the
inverse-CDF common-random-numbers draw (vocabulary order, float64 CDF) and unpruned constant-shape batches.

Extensions (this artifact):
- per-row knockout: sample() takes a per-row condition-span mask; a batch holding any knockout row passes one
  explicit boolean attention mask (all-True on the other rows); batches without knockout rows run stock SDPA, so the
  non-knockout arms (a, b, c, d, V1, ...) are bit-identical whenever their inputs are;
- token vetoes: one-shot (mask the n-gram's completing id at its first completion only) and persistent (mask every
  completing id of every masked n-gram at every step). A masked draw is redrawn from the renormalised distribution
  with a FRESH independent uniform from a separate stream ('veto' key), never the conditioning uniform; an unmasked
  draw is kept, so a vetoed row equals its unvetoed CRN twin up to the firing step;
- fence stop: a row is finished once its first fenced code block is closed (the labeller extracts exactly that
  block, so later tokens cannot change the label) -- this only shortens generation.
"""

from __future__ import annotations

import contextlib
import gc
import math
import re
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg import ENDOFTEXT, IM_END, MAX_NEW_TOKENS, hf_kwargs, model_path, stable_seed

KO: dict[str, Any] = {"active": False, "p0": 0, "p1": 0, "P": 0, "g_lo": 0, "g_hi": 10 ** 9, "layers": None,
                      "rowmask": None}
RECORD: dict[str, Any] = {"on": False, "weights": {}}
_REGISTERED = False

# bench extractor (exp11 harness.FENCE_RE) and exp8 suite extractor (closed python block)
BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
PATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)```", re.S)


def fence_closed_bench(text: str) -> bool:
    return BENCH_FENCE.search(text) is not None


def fence_closed_path(text: str) -> bool:
    m = PATH_FENCE.search(text)
    return bool(m and m.group(1).strip())


# ------------------------------------------------------------------------------------------------ attention
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

    rm = KO.get("rowmask")
    if rm is not None:  # sampling: one explicit [B,1,q,k] boolean mask for every layer (q = 1 at decode)
        kwargs.pop("is_causal", None)
        return sdpa_attention_forward(module, query, key, value, rm[:, :, :, :key.shape[2]], is_causal=False, **kwargs)
    if _ko_on(module):
        q_len, k_len = query.shape[2], key.shape[2]
        allowed = _combine(_ko_allowed(q_len, k_len, query.device), attention_mask, k_len)
        kwargs.pop("is_causal", None)
        return sdpa_attention_forward(module, query, key, value, allowed, is_causal=False, **kwargs)
    return sdpa_attention_forward(module, query, key, value, attention_mask, **kwargs)


def ko_eager(module, query, key, value, attention_mask, **kwargs):
    """Eager twin used only by the knockout-correctness test (U3); records attention probabilities."""
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
    """cfg: {'p0','p1','P','g_lo','g_hi','layers'} or None (no knockout). Used by score() and prefill-time tests."""
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
                                                 **hf_kwargs(), device_map={"": 0})
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
def prefill(model: Any, ids: list[int]) -> dict[str, Any]:
    """Returns {'kv': per-layer (K, V) [1, 8, P, 128] on GPU, 'r_logits': float32 [V], 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=model.device)
    cache = DynamicCache()
    out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


def splice(kv_a: list, kv_b: list, cut: int) -> list:
    """Positions [0, cut) from A and [cut, P) from B, every layer."""
    return [(torch.cat([Ka[:, :, :cut], Kb[:, :, cut:]], dim=2), torch.cat([Va[:, :, :cut], Vb[:, :, cut:]], dim=2))
            for (Ka, Va), (Kb, Vb) in zip(kv_a, kv_b)]


def drop_span(kv: list, p0: int, p1: int) -> list:
    """K0 without a mask: remove the condition span [p0, p1) from every layer's cache. Keys carry their RoPE rotation
    from prefill and generated queries keep position ids P + step, so attention of every generated query over the
    remaining keys equals exp8's masked knockout (softmax renormalises over the unmasked keys) -- see test U3."""
    return [(torch.cat([K[:, :, :p0], K[:, :, p1:]], dim=2), torch.cat([V[:, :, :p0], V[:, :, p1:]], dim=2))
            for K, V in kv]


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
def score(model: Any, arm: dict[str, Any], seqs: list[list[int]], ko: dict[str, Any] | None = None) -> list[np.ndarray]:
    """exp8: teacher-forced per-token log-probs of each sequence placed after the arm's prompt cache, batch 1.
    Token 0 is scored with the arm's R logits; token t >= 1 with the hidden state at position P + t - 1."""
    kv, r_logits = arm["kv"], arm["r_logits"]
    P = kv[0][0].shape[2]
    r_lp = torch.log_softmax(r_logits.float(), dim=-1)
    res = []
    for s in seqs:
        T = len(s)
        inp = torch.tensor([s], device=model.device)
        cache = build_cache(kv, 1)
        pos = torch.arange(P, P + T, device=model.device)[None]
        kcfg = None if ko is None else {**ko, "P": P}
        with knockout(kcfg):
            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        lp = _token_logprobs(model, h[0, :T - 1], inp[0, 1:T])
        first = r_lp[s[0]].reshape(1)
        res.append(torch.cat([first, lp]).float().cpu().numpy())
        del cache, h, inp
    return res


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int = MAX_NEW_TOKENS) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


def _completing_ids(gen: list[int], ngrams: list[list[int]]) -> set[int]:
    """Ids that would complete any n-gram given the row's generated tail."""
    out = set()
    for g in ngrams:
        n = len(g)
        if n == 1 or (len(gen) >= n - 1 and gen[len(gen) - (n - 1):] == g[:-1]):
            out.add(int(g[-1]))
    return out


@torch.no_grad()
def sample(model: Any, rows: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,
           tick_ids: set[int] | None = None, decode: Callable[[list[int]], str] | None = None,
           prune_after: int | None = None) -> list[dict[str, Any]]:
    """rows: [{'kv': per-layer (K,V) [1,8,P,128], 'r_logits': [V], 'u': np.ndarray[max_new],
               optional 'u2': np.ndarray (veto redraw stream), 'veto': {'mode': 'oneshot'|'persistent',
               'ngrams': [[ids]]}, 'ko': (p0, p1) or None, 'stop': 'bench'|'path'|None, 'prefix_text': str}]
    All rows share P. One uniform per (row, step); token = first index whose CDF >= u. Finished rows stay in the batch
    (fed <|im_end|>) so the shape is constant; prune_after (memory guard) drops finished rows after that step."""
    B = len(rows)
    P = rows[0]["kv"][0][0].shape[2]          # cache length (shorter than the prompt for span-dropped K0 rows)
    pos0 = int(rows[0].get("pos0", P))        # position id of the first generated token (= prompt length)
    assert all(r["kv"][0][0].shape[2] == P and int(r.get("pos0", P)) == pos0 for r in rows)
    dev = model.device
    kv = [(torch.cat([r["kv"][l][0] for r in rows], 0), torch.cat([r["kv"][l][1] for r in rows], 0))
          for l in range(len(rows[0]["kv"]))]
    cache = build_cache(kv, B)
    del kv
    # explicit per-row mask only in batches that hold knockout rows (an explicit mask disables SDPA's native GQA
    # path, so knockout batches run a different kernel -- K0 is CRN-coupled to the other arms only approximately,
    # exactly as in exp8); every other batch runs stock SDPA with no mask
    rowmask = None
    if any(r.get("ko") for r in rows):
        rowmask = torch.ones((B, 1, 1, P + max_new + 1), dtype=torch.bool, device=dev)
        for i, r in enumerate(rows):
            if r.get("ko"):
                p0, p1 = r["ko"]
                rowmask[i, :, :, p0:p1] = False
    U = torch.tensor(np.stack([r["u"][:max_new] for r in rows]), dtype=torch.float64, device=dev)
    logits = torch.stack([r["r_logits"] for r in rows]).double()
    alive = list(range(B))
    toks: list[list[int]] = [[] for _ in range(B)]
    lps: list[list[float]] = [[] for _ in range(B)]
    finish = ["length"] * B
    done: set[int] = set()
    veto = [r.get("veto") for r in rows]
    fired = [False] * B
    fire_step: list[int | None] = [None] * B
    n_redraw = [0] * B
    redraw_steps: list[list[int]] = [[] for _ in range(B)]
    n_compl = [0] * B
    pruned_at = None
    step = 0
    while True:
        probs = torch.softmax(logits / temperature, dim=-1)
        nxt_t = _inverse_cdf(probs, U[alive, step])
        nxt = nxt_t.tolist()
        # vetoes (rare events; handled per row on the CPU side)
        for j, r in enumerate(alive):
            v = veto[r]
            if v is None or r in done:
                continue
            comp = _completing_ids(toks[r], v["ngrams"])
            if not comp or nxt[j] not in comp:
                continue
            n_compl[r] += 1
            if v["mode"] == "oneshot":
                if fired[r]:
                    continue
                mask_ids = {nxt[j]}
            else:
                mask_ids = comp
            p = probs[j].clone()
            p[list(mask_ids)] = 0.0
            if float(p.sum()) <= 0:
                continue
            u2 = float(rows[r]["u2"][n_redraw[r]])
            nxt[j] = int(_inverse_cdf((p / p.sum())[None], torch.tensor([u2], dtype=torch.float64, device=dev))[0])
            n_redraw[r] += 1
            redraw_steps[r].append(step)
            if not fired[r]:
                fired[r] = True
                fire_step[r] = step
        nxt_dev = torch.tensor(nxt, device=dev)
        plp = torch.log(probs.gather(-1, nxt_dev[:, None])[:, 0]).tolist()
        keep = []
        for j, (r, t) in enumerate(zip(alive, nxt)):
            if r in done:
                continue
            toks[r].append(int(t))
            lps[r].append(float(plp[j]))
            if t in (IM_END, ENDOFTEXT):
                finish[r] = "stop"
                done.add(r)
                continue
            st = rows[r].get("stop")
            if st and tick_ids is not None and decode is not None and int(t) in tick_ids:
                text = rows[r].get("prefix_text", "") + decode(toks[r])
                if (fence_closed_bench(text) if st == "bench" else fence_closed_path(text)):
                    finish[r] = "fence"
                    done.add(r)
                    continue
            if len(toks[r]) < max_new:
                keep.append(j)
            else:
                done.add(r)
        if not keep:
            break
        if prune_after is not None and step >= prune_after and len(keep) < len(alive):
            idx = torch.tensor(keep, device=dev)
            if hasattr(cache, "batch_select_indices"):
                cache.batch_select_indices(idx)
            else:
                kvn = [(K[idx], V[idx]) for K, V in _kv_list(cache)]
                cache = build_cache(kvn, len(keep))
            if rowmask is not None:
                rowmask = rowmask[idx]
            alive = [alive[j] for j in keep]
            nxt = [nxt[j] for j in keep]
            if pruned_at is None:
                pruned_at = step
        else:
            nxt = [IM_END if r in done else t for r, t in zip(alive, nxt)]
        inp = torch.tensor(nxt, device=dev)[:, None]
        pos = torch.full((len(alive), 1), pos0 + step, device=dev, dtype=torch.long)
        KO["rowmask"] = rowmask
        try:
            h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        finally:
            KO["rowmask"] = None
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    return [{"token_ids": toks[r], "finish_reason": finish[r], "n_tokens": len(toks[r]),
             "logprob_sum": float(np.sum(lps[r])), "veto_fired": fired[r], "fire_step": fire_step[r],
             "n_redraws": n_redraw[r], "redraw_steps": redraw_steps[r], "n_completions_drawn": n_compl[r],
             "pruned_at": pruned_at, "steps": step} for r in range(B)]


def free(*objs: Any) -> None:
    for o in objs:
        del o
    gc.collect()
    torch.cuda.empty_cache()


def logmeanexp(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    m = np.max(x)
    return float(m + math.log(np.mean(np.exp(x - m))))
