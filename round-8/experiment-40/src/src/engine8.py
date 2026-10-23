#!/usr/bin/env python3
"""engine8: one model-agnostic engine for Qwen3-8B and gemma-3-4b-it (bf16, sdpa attention).

- load_lm(family, random_init): trained weights (pinned revision) or the same config randomly initialised
  (torch seed 0, HF post_init -> _init_weights). Qwen's input-embedding table stays on the CPU (exact lookup) so the
  20-23 GB GPU keeps room for KV caches; Gemma is text-only (Gemma3ForCausalLM, tied lm_head).
- LM adapter: embed, rope, block(l, h, ...), final(h) -> fp32 logits (Gemma: final soft-capping if configured).
- prefill(ids, edits, capture): batch-1 prompt pass; edits = {block: fn(h) -> h} applied to block OUTPUTS (fp32
  math, cast to bf16); capture = {block: fn(h)}.
- states_at(ids_list, pos): block outputs of every block at one position + logits there (teacher forcing).
- KVFeed / forward_from(L, h, feed, pos): the single-position path used by DAS at the decision site: an edit of the
  block-(L-1) output at the last position only changes that position from block L on, so blocks L..N-1 are run for
  that one position against the cached keys/values of the earlier positions.
- decode(rows): common-random-numbers sampler (float64 softmax, inverse CDF in vocabulary order, one uniform per
  (row, step)), a fixed batch shape (finished rows are fed the stop token), and the fence stop (a row ends once its
  text holds a closed first python block; bench and path extractors as in iterations 6-7).
"""

from __future__ import annotations

import gc
import json
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg8 import FAMILY, model_path

BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
PATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)```", re.S)


def fence_closed(text: str, kind: str) -> bool:
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
    m = PATH_FENCE.search(text)
    return bool(m and m.group(1).strip() and "def " in m.group(1))


class CPUEmbedding(torch.nn.Module):
    """Exact embedding lookup from a CPU-resident bf16 table; gathered rows are moved to `device`."""

    def __init__(self, weight_cpu: torch.Tensor, device: torch.device):
        super().__init__()
        object.__setattr__(self, "weight_cpu", weight_cpu)
        self.dev = device
        self.num_embeddings, self.embedding_dim = weight_cpu.shape

    @property
    def weight(self) -> torch.Tensor:
        return self.weight_cpu

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.embedding(input_ids.to("cpu"), self.weight_cpu).to(self.dev)


class LM:
    """Thin adapter over a HF causal LM: the pieces the DAS machinery needs, identical for both families."""

    def __init__(self, family: str, tok: Any, model: Any, info: dict[str, Any]):
        self.family = family
        self.tok = tok
        self.model = model
        self.info = info
        self.mm = model.model
        self.layers = self.mm.layers
        self.N = len(self.layers)
        self.D = FAMILY[family]["d_model"]
        self.dev = model.lm_head.weight.device
        self.stop_ids = FAMILY[family]["stop_ids"]
        cap = getattr(model.config, "final_logit_softcapping", None)
        self.softcap = cap

    # -------------------------------------------------------------------------------------------- pieces
    def embed(self, ids: torch.Tensor) -> torch.Tensor:
        return self.mm.embed_tokens(ids)

    def rope(self, h: torch.Tensor, pos: torch.Tensor) -> dict[str, Any]:
        if self.family == "qwen":
            return {"position_embeddings": self.mm.rotary_emb(h, pos)}
        return {"position_embeddings_global": self.mm.rotary_emb(h, pos),
                "position_embeddings_local": self.mm.rotary_emb_local(h, pos)}

    def block(self, l: int, h: torch.Tensor, pos: torch.Tensor, rope: dict[str, Any], feed: Any = None,
              mask: torch.Tensor | None = None, cache_position: torch.Tensor | None = None) -> torch.Tensor:
        out = self.layers[l](h, attention_mask=mask, position_ids=pos, past_key_values=feed,
                             use_cache=feed is not None, cache_position=cache_position, **rope)
        return out[0] if isinstance(out, tuple) else out

    def final(self, h: torch.Tensor) -> torch.Tensor:
        x = self.model.lm_head(self.mm.norm(h)).float()
        if self.softcap is not None:
            x = torch.tanh(x / self.softcap) * self.softcap
        return x

    def free(self) -> None:
        del self.model, self.mm, self.layers
        gc.collect()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ loading
def load_lm(family: str, random_init: bool = False, vram_fraction: float = 0.97) -> LM:
    from transformers import AutoConfig, AutoTokenizer

    t0 = time.time()
    fam = FAMILY[family]
    path = model_path(fam["id"], fam["rev"])
    tok = AutoTokenizer.from_pretrained(path)
    dev = torch.device("cuda", 0)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    if family == "qwen":
        from transformers import AutoModelForCausalLM

        if random_init:
            cfg = AutoConfig.from_pretrained(path)
            cfg._attn_implementation = "sdpa"
            torch.manual_seed(0)
            old = torch.get_default_dtype()
            torch.set_default_dtype(torch.bfloat16)
            try:
                with torch.device("cuda"):
                    model = AutoModelForCausalLM.from_config(cfg, attn_implementation="sdpa")
            finally:
                torch.set_default_dtype(old)
            W = model.model.embed_tokens.weight.data.to("cpu").contiguous()
            model.model.embed_tokens = CPUEmbedding(W, dev)
        else:
            model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                         device_map={"": "cpu"}, low_cpu_mem_usage=True)
            assert not model.config.tie_word_embeddings
            for layer in model.model.layers:
                layer.to(dev)
            model.model.norm.to(dev)
            model.model.rotary_emb.to(dev)
            model.lm_head.to(dev)
            W = model.model.embed_tokens.weight.data.contiguous()
            model.model.embed_tokens = CPUEmbedding(W, dev)
    else:
        from safetensors import safe_open
        from transformers import Gemma3ForCausalLM

        cfg = AutoConfig.from_pretrained(path)
        tcfg = cfg.text_config
        tcfg._attn_implementation = "sdpa"
        torch.manual_seed(0)
        old = torch.get_default_dtype()
        torch.set_default_dtype(torch.bfloat16)
        try:
            with torch.device("cuda"):
                model = Gemma3ForCausalLM(tcfg)
        finally:
            torch.set_default_dtype(old)
        if not random_init:
            sd = model.state_dict()
            loaded = set()
            idx = json.loads((Path(path) / "model.safetensors.index.json").read_text())
            for fn in sorted(set(idx["weight_map"].values())):
                with safe_open(str(Path(path) / fn), framework="pt", device="cuda") as fh:
                    for k in fh.keys():
                        if not k.startswith("language_model.model."):
                            continue
                        nk = "model." + k[len("language_model.model."):]
                        assert nk in sd, f"unexpected key {k}"
                        t = fh.get_tensor(k)
                        assert sd[nk].shape == t.shape, (nk, sd[nk].shape, t.shape)
                        sd[nk].copy_(t.to(sd[nk].dtype))
                        loaded.add(nk)
                        del t
            missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
            assert not missing, f"weights not loaded: {missing[:5]}"
        model.tie_weights()
    model.eval()
    model.requires_grad_(False)
    gc.collect()
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(0)
    info = {"family": family, "model_id": fam["id"], "revision": fam["rev"], "random_init": random_init,
            "precision": "bf16 (sdpa); logits fp32; sampler float64", "gpu": torch.cuda.get_device_name(0),
            "free_vram_after_GB": round(free / 1e9, 2), "total_vram_GB": round(total / 1e9, 2),
            "cpu_embedding": family == "qwen", "load_seconds": round(time.time() - t0, 1)}
    logger.info(f"loaded {family} (random_init={random_init}): {info}")
    return LM(family, tok, model, info)


# ------------------------------------------------------------------------------------------------ hooks / prefill
@contextmanager
def block_hooks(lm: LM, edits: dict[int, Callable] | None = None, capture: dict[int, Callable] | None = None
                ) -> Iterator[None]:
    hs = []

    def mk(l: int):
        def hook(mod, args, out):
            h = out[0] if isinstance(out, tuple) else out
            if capture and l in capture:
                capture[l](h)
            if edits and l in edits:
                h2 = edits[l](h)
                if isinstance(out, tuple):
                    return (h2,) + tuple(out[1:])
                return h2
            return out
        return hook
    keys = set(edits or {}) | set(capture or {})
    try:
        for l in sorted(keys):
            hs.append(lm.layers[l].register_forward_hook(mk(l)))
        yield
    finally:
        for h in hs:
            h.remove()


def kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


@torch.no_grad()
def prefill(lm: LM, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 prompt pass with block-output edits. Returns {'kv': [(K, V)] per block, 'logits': fp32 [V], 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=lm.dev)
    cache = DynamicCache()
    with block_hooks(lm, edits, capture):
        out = lm.mm(input_ids=inp, past_key_values=cache, use_cache=True)
    h = out.last_hidden_state[:, -1]
    logits = lm.model.lm_head(h).float()[0]
    if lm.softcap is not None:
        logits = torch.tanh(logits / lm.softcap) * lm.softcap
    kv = [(K, V) for K, V in kv_list(cache)]
    del out
    return {"kv": kv, "logits": logits, "P": len(ids)}


@torch.no_grad()
def states_at(lm: LM, ids_list: list[list[int]], blocks: list[int] | None = None) -> dict[str, Any]:
    """Teacher-forced states at the LAST position of each sequence (equal lengths batched together): block outputs
    [n, n_blocks, D] (fp32, CPU) and logits [n, V] (fp32, CPU)."""
    blocks = list(range(lm.N)) if blocks is None else blocks
    out_h = [None] * len(ids_list)
    out_l = [None] * len(ids_list)
    by_len: dict[int, list[int]] = {}
    for i, ids in enumerate(ids_list):
        by_len.setdefault(len(ids), []).append(i)
    for L, ix in by_len.items():
        for c0 in range(0, len(ix), 16):
            cix = ix[c0:c0 + 16]
            inp = torch.tensor([ids_list[i] for i in cix], device=lm.dev)
            store: dict[int, torch.Tensor] = {}

            def mk(l: int):
                def g(h: torch.Tensor) -> None:
                    store[l] = h[:, -1].float().cpu()
                return g
            with block_hooks(lm, None, {l: mk(l) for l in blocks}):
                o = lm.mm(input_ids=inp, use_cache=False)
            lg = lm.model.lm_head(o.last_hidden_state[:, -1]).float()
            if lm.softcap is not None:
                lg = torch.tanh(lg / lm.softcap) * lm.softcap
            H = torch.stack([store[l] for l in blocks], 1)
            for j, i in enumerate(cix):
                out_h[i] = H[j]
                out_l[i] = lg[j].cpu()
            del o, store
    return {"h": torch.stack(out_h), "logits": torch.stack(out_l), "blocks": blocks}


# ------------------------------------------------------------------------------------------------ KV path
class KVFeed:
    """Duck-typed cache: cat(cached K/V, new k/v) per block (autograd-safe; never mutated)."""

    def __init__(self, K: dict[int, torch.Tensor], V: dict[int, torch.Tensor]):
        self.K, self.V = K, V

    def update(self, k: torch.Tensor, v: torch.Tensor, layer_idx: int, cache_kwargs: Any = None):
        return torch.cat([self.K[layer_idx], k], 2), torch.cat([self.V[layer_idx], v], 2)

    def get_seq_length(self, layer_idx: int = 0) -> int:
        return int(next(iter(self.K.values())).shape[2])


def forward_from(lm: LM, h_in: torch.Tensor, L_start: int, feed: KVFeed, pos_id: int) -> torch.Tensor:
    """h_in [n, 1, D] = the (edited) output of block L_start-1 at position pos_id; runs blocks L_start..N-1 for that
    position against the cached keys/values; returns fp32 logits [n, V]."""
    n = h_in.shape[0]
    pos = torch.full((n, 1), pos_id, device=h_in.device, dtype=torch.long)
    rope = lm.rope(h_in, pos)
    cpos = torch.tensor([pos_id], device=h_in.device)
    h = h_in
    for l in range(L_start, lm.N):
        h = lm.block(l, h, pos, rope, feed=feed, mask=None, cache_position=cpos)
    return lm.final(h[:, -1])


# ------------------------------------------------------------------------------------------------ decoding
class PreallocLayer:
    """KV layer with a preallocated [B, H, Lmax, D] buffer: update() writes in place (no per-step torch.cat)."""

    is_sliding = False
    is_compileable = False

    def __init__(self, K: torch.Tensor, V: torch.Tensor, max_len: int):
        B, H, P, Dh = K.shape
        self.keys = torch.zeros(B, H, max_len, Dh, dtype=K.dtype, device=K.device)
        self.values = torch.zeros(B, H, max_len, Dh, dtype=V.dtype, device=V.device)
        self.keys[:, :, :P] = K
        self.values[:, :, :P] = V
        self.n = P
        self.is_initialized = True

    def lazy_initialization(self, key_states: torch.Tensor) -> None:
        return None

    def update(self, key_states, value_states, cache_kwargs=None):
        t = key_states.shape[2]
        self.keys[:, :, self.n:self.n + t] = key_states
        self.values[:, :, self.n:self.n + t] = value_states
        self.n += t
        return self.keys[:, :, :self.n], self.values[:, :, :self.n]

    def get_mask_sizes(self, cache_position: torch.Tensor) -> tuple[int, int]:
        return self.n + cache_position.shape[0], 0

    def get_seq_length(self) -> int:
        return self.n

    def get_max_cache_shape(self) -> int:
        return -1


def prealloc_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], max_len: int) -> Any:
    from transformers.cache_utils import DynamicCache

    cache = DynamicCache()
    cache.layers = [PreallocLayer(K, V, max_len) for K, V in kv]
    return cache


_TICK: dict[int, torch.Tensor] = {}


def backtick_mask(tok: Any, dev: torch.device) -> torch.Tensor:
    k = id(tok)
    if k not in _TICK:
        n = len(tok)
        m = torch.zeros(n + 1024, dtype=torch.bool)
        for i in range(n):
            s = tok.decode([i])
            if "`" in s:
                m[i] = True
        _TICK[k] = m.to(dev)
    return _TICK[k]


@torch.no_grad()
def decode(lm: LM, pres: list[dict[str, Any]], us: list[np.ndarray], max_new: int, fence: str | None,
           check_every: int = 8) -> list[dict[str, Any]]:
    """CRN decoding of a fixed-shape batch. pres[i]: a prefill dict (all rows share P); us[i]: the row's uniforms."""
    P = pres[0]["P"]
    assert all(p["P"] == P for p in pres), "all rows of a batch must share the prompt length"
    tok = lm.tok
    dev = lm.dev
    B = len(pres)
    nL = len(pres[0]["kv"])
    kv = [(torch.cat([p["kv"][l][0] for p in pres], 0), torch.cat([p["kv"][l][1] for p in pres], 0))
          for l in range(nL)]
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    stop0 = lm.stop_ids[0]
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.stack([p["logits"] for p in pres]).double()
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((B, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    stop_t = torch.full((B,), stop0, dtype=torch.long, device=dev)
    stops = torch.tensor(list(lm.stop_ids), device=dev)
    tick = backtick_mask(tok, dev) if fence else None
    host: list[list[int]] = [[] for _ in range(B)]
    last = 0
    step = 0
    nv = len(tok)
    while True:
        probs = torch.softmax(logits, dim=-1)
        cdf = probs.cumsum(-1)
        cdf = cdf / cdf[:, -1:]
        nxt = torch.searchsorted(cdf, U[:, step][:, None]).squeeze(-1).clamp_(max=probs.shape[-1] - 1)
        plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
        live = ~done
        toks[:, step] = torch.where(live, nxt, toks[:, step])
        lps[:, step] = torch.where(live, plp, lps[:, step])
        is_end = torch.isin(nxt, stops)
        ended |= live & is_end
        done |= is_end
        if step + 1 >= max_new:
            break
        if (step + 1) % check_every == 0:
            if tick is not None:
                chunk = toks[:, last:step + 1]
                has_tick = (tick[chunk.clamp(min=0)] & (chunk >= 0)).any(dim=1) & ~done
                cc = chunk.cpu().numpy()
                for r in range(B):
                    host[r].extend(int(t) for t in cc[r] if t >= 0)
                last = step + 1
                rows = torch.nonzero(has_tick).flatten().tolist()
                newly = [r for r in rows if fence_closed(
                    tok.decode([t for t in host[r] if t < nv], skip_special_tokens=True), fence)]
                if newly:
                    ix = torch.tensor(newly, device=dev)
                    fenced[ix] = True
                    done[ix] = True
            if bool(done.all().item()):
                break
        feed = torch.where(done, stop_t, nxt)[:, None]
        pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
        h = lm.mm(input_ids=feed, past_key_values=cache, position_ids=pos,
                  cache_position=torch.tensor([P + step], device=dev), use_cache=True).last_hidden_state
        lg = lm.model.lm_head(h[:, -1]).float()
        if lm.softcap is not None:
            lg = torch.tanh(lg / lm.softcap) * lm.softcap
        logits = lg.double()
        step += 1
    del cache
    tc = toks.cpu().numpy()
    lc = lps.cpu().numpy()
    out = []
    for r in range(B):
        n = int((tc[r] >= 0).sum())
        ids = [int(t) for t in tc[r, :n]]
        fr = "stop" if bool(ended[r]) else ("fence" if bool(fenced[r]) else "length")
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n, "logprob_sum": float(lc[r, :n].sum()),
                    "steps": step + 1})
    return out
