#!/usr/bin/env python3
"""bf16 engine for iteration 7: exp29's engine-d weight set (engines.load_b: bf16 decoder linears on the GPU via
F.linear, CPU-resident exact embedding gather, bf16 norms and lm_head) with the vendored exp22 prefill, block hooks
and exact inverse-CDF CRN sampler (engine4.sample, fence stop, constant batch shape).

Added here (all fp32 edit arithmetic, cast back to the block dtype, prompt prefill only):
  edit_target   h_S <- h_S + (M - (h_S - h_ref) . U) U   per block, U [D] or per-position [nS, D], M [nS]
                (exp22 hooks4 TARGET, generalised to per-position units; displacement along U is exactly M)
  edit_clamp    h_S <- h_S - ((h_S - h_ref) . a) a       (removes the displacement's component along unit a)
  compose       several per-block edits applied in order at the same block
  sample_stop   engine4.sample with an extra per-row stop callback (partial-label stop for fork continuations)
  forward_lp    teacher-forced log-probabilities of the next token at chosen positions (one pass, B rows)
"""

from __future__ import annotations

import gc
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

import c7 as common  # noqa: F401  (sys.path)
from c7 import MODEL_REVISION

_STATE: dict[str, Any] = {}


def load() -> tuple[Any, Any]:
    import engines  # vendored exp29 src/engines.py
    tok, model = engines.load_b(vram_fraction=0.97)
    engines.set_mode("d")
    _STATE["engines"] = engines
    return tok, model


def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


def prefill(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    import engine as VE   # vendored exp22 src_base/engine.py
    return VE.prefill(model, ids, edits=edits, capture=capture)


# ------------------------------------------------------------------------------------------------ edits
def edit_target(a: int, b: int, U: torch.Tensor, M: torch.Tensor, h_ref: torch.Tensor) -> Callable:
    """One block: U [D] or [nS, D] (unit rows), M [nS], h_ref [nS, D] fp32 (clean twin states at that block)."""
    def f(h: torch.Tensor) -> torch.Tensor:
        hs = h[:, a:b].float()
        if U.dim() == 1:
            comp = (hs - h_ref) @ U
            new = hs + (M - comp)[..., None] * U
        else:
            comp = ((hs - h_ref) * U).sum(-1)
            new = hs + (M - comp)[..., None] * U
        h = h.clone()
        h[:, a:b] = new.to(h.dtype)
        return h
    return f


def edit_clamp(a: int, b: int, u: torch.Tensor, h_ref: torch.Tensor) -> Callable:
    def f(h: torch.Tensor) -> torch.Tensor:
        hs = h[:, a:b].float()
        comp = (hs - h_ref) @ u
        new = hs - comp[..., None] * u
        h = h.clone()
        h[:, a:b] = new.to(h.dtype)
        return h
    return f


def compose(*edit_maps: dict[int, Callable]) -> dict[int, Callable]:
    out: dict[int, list[Callable]] = {}
    for m in edit_maps:
        for l, f in (m or {}).items():
            out.setdefault(l, []).append(f)

    def chain(fs: list[Callable]) -> Callable:
        def g(h: torch.Tensor) -> torch.Tensor:
            for f in fs:
                h = f(h)
            return h
        return g
    return {l: chain(fs) for l, fs in out.items()}


def capture_S(store: dict[int, torch.Tensor], a: int, b: int, blocks: list[int]) -> dict[int, Callable]:
    """Capture fp32 block outputs at positions [a, b) of row 0."""
    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            store[l] = h[0, a:b].float().clone()
        return g
    return {l: mk(l) for l in blocks}


# ------------------------------------------------------------------------------------------------ sampling
def sample(model: Any, tok: Any, groups: list[dict[str, Any]], fence: str, max_new: int) -> list[dict[str, Any]]:
    from engine4 import sample as s4
    return s4(model, tok, groups, fence=fence, max_new=max_new)


@torch.no_grad()
def sample_stop(model: Any, tok: Any, groups: list[dict[str, Any]], stop_fn: Callable[[int, list[int]], bool],
                max_new: int, check_every: int = 4, temperature: float = 1.0) -> list[dict[str, Any]]:
    """engine4.sample (exact inverse-CDF CRN draw, prune=False, constant batch shape) with a per-row stop callback
    stop_fn(row_index, new_token_ids) evaluated every `check_every` steps on live rows; also stops at <|im_end|>."""
    from engine import _inverse_cdf, clear_act_cache, prealloc_cache
    from cfg4 import ENDOFTEXT, IM_END

    P = groups[0]["pre"]["P"]
    assert all(g["pre"]["P"] == P for g in groups), "all rows of a batch must share the prompt length"
    dev = model.device
    n_layers = len(groups[0]["pre"]["kv"])
    kv = []
    for l in range(n_layers):
        Ks, Vs = [], []
        for g in groups:
            K, V = g["pre"]["kv"][l]
            Ks.append(K.expand(len(g["us"]), -1, -1, -1))
            Vs.append(V.expand(len(g["us"]), -1, -1, -1))
        kv.append((torch.cat(Ks, 0), torch.cat(Vs, 0)))
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    us = [u for g in groups for u in g["us"]]
    Bn = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["us"]), -1) for g in groups], 0).double()
    toks = torch.full((Bn, max_new), -1, dtype=torch.long, device=dev)
    done = torch.zeros(Bn, dtype=torch.bool, device=dev)
    ended = torch.zeros(Bn, dtype=torch.bool, device=dev)
    stopped = [False] * Bn
    im_end_t = torch.full((Bn,), IM_END, dtype=torch.long, device=dev)
    step = 0
    try:
        while True:
            probs = torch.softmax(logits / temperature, dim=-1)
            nxt = _inverse_cdf(probs, U[:, step])
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            done |= is_end
            if step + 1 >= max_new:
                break
            if (step + 1) % check_every == 0:
                live_rows = torch.nonzero(~done).flatten().tolist()
                if live_rows:
                    tc = toks[live_rows, :step + 1].cpu().numpy()
                    for j, r in enumerate(live_rows):
                        ids = [int(t) for t in tc[j] if t >= 0]
                        if stop_fn(r, ids):
                            done[r] = True
                            stopped[r] = True
                if bool(done.all().item()):
                    break
            feed = torch.where(done, im_end_t, nxt)[:, None]
            pos = torch.full((Bn, 1), P + step, device=dev, dtype=torch.long)
            clear_act_cache()
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            step += 1
    finally:
        clear_act_cache()
    del cache
    toks_c = toks.cpu().numpy()
    ended_c = ended.cpu().numpy()
    out = []
    for r in range(Bn):
        row = toks_c[r]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r] else ("decided" if stopped[r] else "length")
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n, "steps": step + 1})
    return out


# ------------------------------------------------------------------------------------------------ teacher forcing
@torch.no_grad()
def forward_lp(model: Any, ids_batch: list[list[int]], positions: list[int], edits: dict | None = None,
               capture: dict | None = None) -> torch.Tensor:
    """Equal-length batch forward with optional block edits; returns fp32 log-softmax [B, len(positions), V] of the
    next token at each position (positions index the input sequence: logits at i predict token i + 1)."""
    import engine as VE
    B = len(ids_batch)
    T = len(ids_batch[0])
    assert all(len(x) == T for x in ids_batch)
    inp = torch.tensor(ids_batch, device=model.device)
    VE.clear_act_cache()
    with VE.block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, use_cache=False)
    hl = out.last_hidden_state[:, positions]
    lp = torch.log_softmax(model.lm_head(hl).float(), dim=-1)
    del out, hl
    VE.clear_act_cache()
    return lp


@torch.no_grad()
def seq_logprob(model: Any, prompt_ids: list[int], conts: list[list[int]], edits: dict | None = None,
                chunk: int = 8) -> list[float]:
    """Sum of log p(cont tokens | prompt + earlier cont tokens) for equal-length continuations (teacher-forced)."""
    import engine as VE
    out: list[float] = []
    P = len(prompt_ids)
    for i in range(0, len(conts), chunk):
        part = conts[i:i + chunk]
        L = len(part[0])
        assert all(len(c) == L for c in part)
        inp = torch.tensor([prompt_ids + c for c in part], device=model.device)
        VE.clear_act_cache()
        with VE.block_hooks(model, edits, None):
            o = model.model(input_ids=inp, use_cache=False)
        h = o.last_hidden_state[:, P - 1:P - 1 + L]
        lp = torch.log_softmax(model.lm_head(h).float(), dim=-1)
        tgt = torch.tensor(part, device=model.device)
        out += lp.gather(-1, tgt[..., None])[..., 0].sum(-1).double().cpu().tolist()
        del o, h, lp
        VE.clear_act_cache()
    return out


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()


def hardware_info(model: Any) -> dict[str, Any]:
    import platform

    import transformers
    free, total = torch.cuda.mem_get_info(0)
    return {"gpu": torch.cuda.get_device_name(0), "cc": list(torch.cuda.get_device_capability(0)),
            "total_vram_gib": total / 2 ** 30, "free_vram_gib_after_load": free / 2 ** 30,
            "torch": torch.__version__, "cuda": torch.version.cuda, "transformers": transformers.__version__,
            "python": platform.python_version(), "model": "Qwen/Qwen3-8B", "revision": MODEL_REVISION,
            "precision": "bf16 weights and activations (exp29 engine d: F.linear on bf16 weights)",
            "embedding_placement": "CPU exact gather (exp29 load_b CPUEmbed); identical values to a GPU gather",
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def timed(label: str):
    class _T:
        def __enter__(self):
            self.t0 = time.time()
            return self

        def __exit__(self, *a):
            self.dt = time.time() - self.t0
            logger.debug(f"{label}: {self.dt:.2f}s")
    return _T()
