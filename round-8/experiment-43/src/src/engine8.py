#!/usr/bin/env python3
"""engine8: one bf16 HF engine for the three families (Qwen3-8B, Llama-3.1-8B-Instruct, gemma-3-4b-it) and Qwen3-8B-Base.

Sampler (the iteration-6 engine5 transform, unchanged): logits widened to float64 / T -> softmax -> optional top-k mask
(keep p >= k-th largest p; ties kept) -> cumsum over the FULL vocabulary in TOKEN-ID order, divided by the kept total ->
token = searchsorted(cdf, u) clamped to V - 1. replay.pick() is the independent numpy twin of this transform.

Two decoding modes:
  * coupled (fit twins, sweeps, top-k validation): a fixed batch composition; finished rows stay in the batch and are fed
    the family's pad/stop id, so a slot's computation never depends on when its batch-mates stop (exact CRN coupling
    across temperatures for a fixed composition, as in iterations 6-7);
  * free (prefix-resampling continuations, forced-token continuations, shadow top-k regeneration): finished rows are
    dropped from the KV cache (DynamicCache.batch_select_indices) -- these rows are independent samples.
Left padding (rows with different prompt/prefix lengths) uses a 2-D attention mask and per-row position ids.
Gemma: text-only Gemma3ForCausalLM built from the multimodal checkpoint's language-model weights (art_HY7uYZz-OjRW
loader); final-logit softcapping is applied inside the model's forward. Qwen/Llama: AutoModelForCausalLM; the input
embedding table stays on the CPU (exact lookup) when free VRAM < 18 GiB before load (the 20 GB A4500 rule).
Top-k shadow: at every top-p-1 step of a coupled row, the token the top-k sampler would pick from the SAME fp64 logits
and the SAME u is computed; the first step where it differs is recorded (shadow_div_step, shadow_tok).
"""

from __future__ import annotations

import gc
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg8 import FAMILIES, model_path

BENCH_FENCE = re.compile(r"```[^\n`]*\n[\s\S]*?\n[ \t]*```")
PATH_FENCE = re.compile(r"```[^\n`]*\n([\s\S]*?)\n[ \t]*```")


def fence_closed(text: str, kind: str | None) -> bool:
    """The first fenced block is closed (bench) / closed and non-empty (path)."""
    if kind is None:
        return False
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
    m = PATH_FENCE.search(text)
    return bool(m and m.group(1).strip())


class CPUEmbedding(torch.nn.Module):
    """Exact embedding lookup from a CPU-resident bf16 table (iteration-6 engine6); rows are copied to `device`."""

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


# ------------------------------------------------------------------------------------------------ loading
def _load_gemma(path: str) -> Any:
    from safetensors import safe_open
    from transformers import AutoConfig, Gemma3ForCausalLM

    cfg = AutoConfig.from_pretrained(path)
    tcfg = cfg.text_config
    tcfg._attn_implementation = "sdpa"
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
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
    model.tie_weights()
    missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
    assert not missing, f"weights not loaded: {missing[:5]}"
    return model


def load(family: str, vram_fraction: float = 0.97, cpu_embed: bool | None = None) -> tuple[Any, Any, dict[str, Any]]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    f = FAMILIES[family]
    path = model_path(f["model_id"], f["rev"])
    tok = AutoTokenizer.from_pretrained(path)
    dev = torch.device("cuda", 0)
    free0, total = torch.cuda.mem_get_info(0)
    if family == "gemma":
        cpu_embed = False
        model = _load_gemma(path)
    else:
        if cpu_embed is None:
            # the plan's rule (CPU embedding when < 18 GiB is free) plus Qwen3-8B always: its 16.4 GB of weights leave
            # too little room on the 20 GB card for 20 x ~1,000-token KV caches (the lookup is exact either way)
            cpu_embed = free0 < 18 * 1024 ** 3 or family in ("qwen", "qwen_base")
        model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                     device_map={"": "cpu"}, low_cpu_mem_usage=True)
        assert not model.config.tie_word_embeddings or not cpu_embed
        for layer in model.model.layers:
            layer.to(dev)
        model.model.norm.to(dev)
        model.model.rotary_emb.to(dev)
        model.lm_head.to(dev)
        if cpu_embed:
            model.model.embed_tokens = CPUEmbedding(model.model.embed_tokens.weight.data.contiguous(), dev)
        else:
            model.model.embed_tokens.to(dev)
    gc.collect()
    torch.cuda.empty_cache()
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    model._aii_family = family
    info = {"family": family, "model_id": f["model_id"], "revision": f["rev"], "precision": "bf16",
            "cpu_embedding": bool(cpu_embed), "free_vram_before_GB": round(free0 / 1e9, 3),
            "free_vram_after_GB": round(free / 1e9, 3), "total_vram_GB": round(total / 1e9, 3),
            "gpu": torch.cuda.get_device_name(0), "load_seconds": round(time.time() - t0, 1),
            "vocab_rows": int(lm_rows(model)), "n_layers": len(model.model.layers)}
    logger.info(f"{f['model_id']} loaded: {info}")
    return tok, model, info


def free(model: Any) -> None:
    del model
    gc.collect()
    torch.cuda.empty_cache()


def lm_rows(model: Any) -> int:
    return int(model.lm_head.weight.shape[0])


def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


# ------------------------------------------------------------------------------------------------ sampler
def step_probs(logits: torch.Tensor, T: torch.Tensor, top_k: torch.Tensor, any_topk: bool) -> torch.Tensor:
    """float64 softmax(logits / T) with the top-k mask applied to rows with k > 0 (kept mass not renormalised here)."""
    probs = torch.softmax(logits.double() / T[:, None], dim=-1)
    if any_topk:
        kmax = int(top_k.max().item())
        kth = probs.topk(kmax, dim=-1).values.gather(-1, (top_k.clamp(min=1) - 1)[:, None])
        probs = torch.where((top_k > 0)[:, None] & (probs < kth), torch.zeros_like(probs), probs)
    return probs


def inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


def topk_pick(logits: torch.Tensor, T: torch.Tensor, u: torch.Tensor, k: int) -> torch.Tensor:
    probs = torch.softmax(logits.double() / T[:, None], dim=-1)
    kth = probs.topk(k, dim=-1).values[:, -1:]
    probs = torch.where(probs < kth, torch.zeros_like(probs), probs)
    return inverse_cdf(probs, u)


# ------------------------------------------------------------------------------------------------ decoding
@torch.no_grad()
def _forward(model: Any, ids: torch.Tensor, cache: Any, am: torch.Tensor | None, pos: torch.Tensor,
             n_logits: int = 1) -> torch.Tensor:
    out = model(input_ids=ids, attention_mask=am, position_ids=pos, past_key_values=cache, use_cache=True,
                logits_to_keep=n_logits)
    return out.logits


@torch.no_grad()
def generate(model: Any, tok: Any, rows: list[dict[str, Any]], *, coupled: bool, fence_kind: str | None = "bench",
             stop_fn: Callable[[dict[str, Any], list[int]], bool] | None = None, check_every: int = 8,
             shadow_k: int = 0, record: bool = False) -> list[dict[str, Any]]:
    """rows: {'prompt_ids', 'prefix_ids' (forced generated prefix, may be []), 'u' (uniforms for the NEW steps),
    'T', 'top_k', 'max_new' (new tokens)}. Returns per row: new token ids, finish reason, shadow divergence."""
    from transformers import DynamicCache

    fam = model._aii_family
    stop_ids = set(FAMILIES[fam]["stop_ids"])
    pad_id = FAMILIES[fam]["pad_id"]
    dev = dev_of(model)
    B = len(rows)
    seqs = [list(r["prompt_ids"]) + list(r.get("prefix_ids") or []) for r in rows]
    L = max(len(s) for s in seqs)
    padded = any(len(s) != L for s in seqs)
    inp = torch.full((B, L), pad_id, dtype=torch.long)
    am = torch.zeros((B, L), dtype=torch.long)
    for i, s in enumerate(seqs):
        inp[i, L - len(s):] = torch.tensor(s)
        am[i, L - len(s):] = 1
    inp, am = inp.to(dev), am.to(dev)
    pos = (am.cumsum(-1) - 1).clamp(min=0)
    cache = DynamicCache(config=model.config)
    logits = _forward(model, inp, cache, am if padded else None, pos)[:, -1].double()
    next_pos = pos[:, -1] + 1
    max_new = np.array([int(r["max_new"]) for r in rows])
    max_steps = int(max_new.max())
    U = torch.zeros(B, max_steps, dtype=torch.float64)
    for i, r in enumerate(rows):
        u = np.asarray(r["u"], dtype=np.float64)
        assert len(u) >= max_new[i], (len(u), max_new[i])
        U[i] = torch.from_numpy(u[:max_steps]) if len(u) >= max_steps else torch.from_numpy(
            np.concatenate([u, np.full(max_steps - len(u), 0.5)]))
    U = U.to(dev)
    T_all = torch.tensor([float(r["T"]) for r in rows], dtype=torch.float64, device=dev)
    K_all = torch.tensor([int(r.get("top_k") or 0) for r in rows], dtype=torch.long, device=dev)
    maxnew_t = torch.tensor(max_new, dtype=torch.long, device=dev)
    any_topk = bool((K_all > 0).any())
    rec: list[list[tuple[int, float, float]]] = [[] for _ in range(B)]
    stop_t = torch.tensor(sorted(stop_ids), dtype=torch.long, device=dev)
    nv = lm_rows(model)
    # bookkeeping over ORIGINAL row indices; `live_idx` maps current batch positions -> original rows
    live_idx = list(range(B))
    toks_host: list[list[int]] = [[] for _ in range(B)]
    finish = [None] * B
    shadow_step = [None] * B
    shadow_tok = [None] * B
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    n_gen = torch.zeros(B, dtype=torch.long, device=dev)
    buf = []                 # per-step [B_cur] token tensors since the last host sync (coupled: full B)
    buf_rows = []            # live_idx snapshot per buffered step (free mode)
    step = 0
    am_cur = am if padded else None
    while True:
        cur = torch.tensor(live_idx, device=dev)
        Tn, Kn = T_all[cur], K_all[cur]
        probs = step_probs(logits, Tn, Kn, any_topk)
        u_step = U[cur, n_gen[cur].clamp(max=max_steps - 1)]
        nxt = inverse_cdf(probs, u_step)
        if shadow_k:
            tk = topk_pick(logits, Tn, u_step, shadow_k)
            div = (tk != nxt) & ~done[cur]
            if bool(div.any()):
                for j in torch.nonzero(div).flatten().tolist():
                    o = live_idx[j]
                    if shadow_step[o] is None:
                        shadow_step[o] = int(n_gen[o].item())
                        shadow_tok[o] = int(tk[j].item())
        live = ~done[cur]
        if record:
            mx, am_ = logits.max(-1)
            ch = logits.gather(-1, nxt[:, None]).squeeze(-1)
            for j, (a1, m1, c1, l1) in enumerate(zip(am_.tolist(), mx.tolist(), ch.tolist(), live.tolist())):
                if l1:
                    rec[live_idx[j]].append((int(a1), float(m1), float(c1)))
        nxt = torch.where(live, nxt, torch.full_like(nxt, pad_id))
        buf.append(nxt.clone())
        buf_rows.append(list(live_idx))
        n_gen[cur] += live.long()
        is_stop = torch.isin(nxt, stop_t) & live
        newly_done = is_stop | (live & (n_gen[cur] >= maxnew_t[cur]))
        done_cur = done[cur] | newly_done
        done[cur] = done_cur
        for j in torch.nonzero(is_stop).flatten().tolist():
            finish[live_idx[j]] = "stop"
        step += 1
        sync = (step % check_every == 0) or bool(done_cur.all()) or step >= max_steps
        if sync:
            for s_t, s_rows in zip(buf, buf_rows):
                arr = s_t.tolist()
                for j, o in enumerate(s_rows):
                    if len(toks_host[o]) < int(max_new[o]) and finish[o] in (None, "stop") and \
                            (not toks_host[o] or toks_host[o][-1] not in stop_ids):
                        toks_host[o].append(int(arr[j]))
            buf, buf_rows = [], []
            dn = done.cpu().numpy()
            for j, o in enumerate(live_idx):
                if dn[o]:
                    if finish[o] is None:
                        finish[o] = "length"
                    continue
                ids_r = [t for t in toks_host[o] if t < nv]
                full = list(rows[o].get("prefix_ids") or []) + ids_r
                if fence_kind:
                    txt = tok.decode(full, skip_special_tokens=True)
                    if "`" in txt and fence_closed(txt, fence_kind):
                        finish[o] = "fence"
                        done[o] = True
                        continue
                if stop_fn is not None and stop_fn(rows[o], full):
                    finish[o] = "decided"
                    done[o] = True
            if bool(done.all()) or step >= max_steps:
                break
            if not coupled:
                keep = [j for j, o in enumerate(live_idx) if not bool(done[o])]
                if len(keep) < len(live_idx):
                    kt = torch.tensor(keep, device=dev)
                    cache.batch_select_indices(kt)
                    nxt = nxt[kt]
                    next_pos = next_pos[kt]
                    if am_cur is not None:
                        am_cur = am_cur[kt]
                    live_idx = [live_idx[j] for j in keep]
        feed = nxt[:, None]
        if am_cur is not None:
            am_cur = torch.cat([am_cur, torch.ones((am_cur.shape[0], 1), dtype=am_cur.dtype, device=dev)], 1)
        logits = _forward(model, feed, cache, am_cur, next_pos[:, None])[:, -1].double()
        next_pos = next_pos + 1
    del cache
    out = []
    for o in range(B):
        ids = toks_host[o][: int(max_new[o])]
        # trim anything after the first stop id (kept as the final token, as in engine5)
        for i, t in enumerate(ids):
            if t in stop_ids:
                ids = ids[: i + 1]
                break
        out.append({"token_ids": ids, "finish_reason": finish[o] or "length", "n_tokens": len(ids),
                    "shadow_div_step": shadow_step[o], "shadow_tok": shadow_tok[o],
                    "engine_path": "leftpad" if padded else "shared", "record": rec[o] if record else None})
    return out


def run_batches(model: Any, tok: Any, rows: list[dict[str, Any]], batch: int, **kw: Any) -> list[dict[str, Any]]:
    """generate() over consecutive chunks with an OOM halving fallback (free mode only; coupled callers pass the
    composition themselves)."""
    out: list[dict[str, Any]] = []
    i = 0
    b = batch
    while i < len(rows):
        chunk = rows[i:i + b]
        try:
            out.extend(generate(model, tok, chunk, **kw))
            i += len(chunk)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if kw.get("coupled") or b <= 1:
                raise
            b = max(1, b // 2)
            logger.warning(f"OOM: batch -> {b}")
    return out


# ------------------------------------------------------------------------------------------------ teacher forcing
@torch.no_grad()
def teacher_force(model: Any, prompt_ids: list[int], cont: list[int]) -> torch.Tensor:
    """fp32 logits [len(cont) + 1, V] on the GPU: row j predicts cont[j]; the last row predicts the token after cont."""
    ids = torch.tensor([list(prompt_ids) + list(cont)], device=dev_of(model))
    out = model(input_ids=ids, use_cache=False, logits_to_keep=len(cont) + 1)
    return out.logits[0].float()
