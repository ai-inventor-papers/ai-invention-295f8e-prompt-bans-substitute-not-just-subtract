#!/usr/bin/env python3
"""bf16 HF engine for Qwen2.5-7B-Instruct (ported from iteration-5 exp27 src/engine_v4.py; FP8 removed -- the 7B model
fits in bf16 on the 24 GB card, and the plan forbids quantisation).

Sampling keeps exp8/exp17's exact common-random-numbers rule: one uniform per (row, step) from the slot's stream,
token = first vocabulary index whose float64 CDF of softmax(logits / T) reaches u (no top-k, no top-p, no repetition
penalty -- Qwen2.5's generation_config is overridden). The port runs the rule inside HF `generate` as a logits
processor that leaves only the CRN-chosen token finite, with greedy decoding on top; HF handles the KV cache, left
padding (so prompts of different lengths share a batch) and per-row EOS. Deviation from exp27 (logged in S2): exp27
kept finished rows in a fixed-shape batch (prune=False) and never padded; here rows of different prompt lengths are
left-padded, so batch invariance is measured (S2c) instead of being exact by construction.

Hooks: block_hooks() edits a block's OUTPUT (= hidden_states[block + 1]). Positions are end-relative, which left
padding keeps identical for every row of a batch: index P - offset (cfg.POS_OFFSET).
"""

from __future__ import annotations

import contextlib
import gc
import re
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg import ENDOFTEXT, EOS_IDS, IM_END, MAX_NEW_TOKENS, MODEL_ID, MODEL_REVISION, model_path, stable_seed

BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
PATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)```", re.S)


def fence_closed(text: str, kind: str) -> bool:
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
    m = PATH_FENCE.search(text)
    return bool(m and m.group(1).strip())


_TICK: dict[int, torch.Tensor] = {}
_VLEN: dict[int, int] = {}


def vocab_len(tok: Any) -> int:
    k = id(tok)
    if k not in _VLEN:
        _VLEN[k] = len(tok)
    return _VLEN[k]


def backtick_ids(tok: Any, n_rows: int) -> torch.Tensor:
    key = id(tok)
    if key not in _TICK:
        V = vocab_len(tok)
        toks = tok.convert_ids_to_tokens(list(range(V)))
        m = np.zeros(max(n_rows, V), dtype=bool)
        m[:V] = [(t is not None and '`' in t) for t in toks]
        _TICK[key] = torch.tensor(m)
    return _TICK[key]


def load_model(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION, vram_fraction: float = 0.97):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    tok = AutoTokenizer.from_pretrained(path)
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0})
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"{model_id} loaded in {time.time() - t0:.0f}s; free VRAM {free / 1e9:.1f}/{total / 1e9:.1f} GB")
    return tok, model


def unload(*objs: Any) -> None:
    for o in objs:
        del o
    gc.collect()
    torch.cuda.empty_cache()


def layers(model: Any) -> Any:
    return model.model.layers


# ------------------------------------------------------------------------------------------------ hooks
def _out_tensor(out: Any) -> torch.Tensor:
    return out[0] if isinstance(out, tuple) else out


def _replace_out(out: Any, h: torch.Tensor) -> Any:
    if isinstance(out, tuple):
        return (h,) + tuple(out[1:])
    return h


@contextlib.contextmanager
def block_hooks(model: Any, edits: dict[int, Callable[[torch.Tensor], torch.Tensor]] | None = None,
                capture: dict[int, Callable[[torch.Tensor], None]] | None = None) -> Iterator[None]:
    """edits: {block: f(h) -> h'} applied to the block OUTPUT; capture: {block: g(h)} called after the edit."""
    hs = []
    edits = edits or {}
    capture = capture or {}
    for l in sorted(set(edits) | set(capture)):
        def hook(mod, inp, out, l=l):
            h = _out_tensor(out)
            if l in edits:
                h = edits[l](h)
                out = _replace_out(out, h)
            if l in capture:
                capture[l](h)
            return out
        hs.append(layers(model)[l].register_forward_hook(hook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


class DeltaEdit:
    """Adds per-row deltas to a block output.

    pre: {offset: Tensor[B, D]} added at index P - offset during the prefill pass (seq_len > 1).
    gen: Tensor[B, D] added at every decode step 1..gen_steps (seq_len == 1), i.e. at the generated positions.
    Logs the realised displacement relative to the target (read-back check)."""

    def __init__(self, pre: dict[int, torch.Tensor] | None = None, gen: torch.Tensor | None = None,
                 gen_steps: int = 64):
        self.pre = pre or {}
        self.gen = gen
        self.gen_steps = gen_steps
        self.n_decode = 0
        self.readback: list[float] = []
        self.prefill_done = False

    def __call__(self, h: torch.Tensor) -> torch.Tensor:
        T = h.shape[1]
        if T > 1:
            h2 = h.clone()
            for off, d in self.pre.items():
                idx = T - off
                tgt = d.to(h.dtype)
                h2[:, idx] = h[:, idx] + tgt
                real = (h2[:, idx].float() - h[:, idx].float())
                err = ((real - tgt.float()).norm(dim=-1) / tgt.float().norm(dim=-1).clamp(min=1e-6))
                nz = tgt.float().norm(dim=-1) > 0
                if bool(nz.any()):
                    self.readback.append(float(err[nz].max()))
            self.prefill_done = True
            return h2
        if self.gen is not None and self.n_decode < self.gen_steps:
            self.n_decode += 1
            return h + self.gen.to(h.dtype)[:, None, :]
        self.n_decode += 1
        return h


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int = 2048) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


class CRNProcessor:
    """Inverse-CDF CRN sampling inside HF generate: returns scores that are -inf except at the chosen token."""

    def __init__(self, U: np.ndarray, temps: list[float], prompt_len: int, device: torch.device):
        self.U = torch.tensor(U, dtype=torch.float64, device=device)
        self.T = torch.tensor(temps, dtype=torch.float64, device=device)[:, None]
        self.P = prompt_len
        self.lp: list[torch.Tensor] = []

    def __call__(self, input_ids: torch.Tensor, scores: torch.Tensor) -> torch.Tensor:
        step = input_ids.shape[1] - self.P
        probs = torch.softmax(scores.double() / self.T, dim=-1)
        cdf = probs.cumsum(dim=-1)
        cdf = cdf / cdf[:, -1:]
        u = self.U[:, step].clamp(max=1.0 - 1e-12)
        tok = torch.searchsorted(cdf, u[:, None]).squeeze(-1).clamp_(max=probs.shape[-1] - 1)
        self.lp.append(torch.log(probs.gather(-1, tok[:, None])[:, 0]).float())
        out = torch.full_like(scores, float("-inf"))
        out.scatter_(1, tok[:, None], 0.0)
        return out


class FenceStop:
    """Per-row stop once the generated text holds a closed first python block (bench / path fence rules)."""

    def __init__(self, tok: Any, prompt_len: int, kind: str, check_every: int = 8):
        self.tok, self.P, self.kind, self.every = tok, prompt_len, kind, check_every
        self.fenced: torch.Tensor | None = None

    def __call__(self, input_ids: torch.Tensor, scores: torch.Tensor, **kw: Any) -> torch.Tensor:
        B = input_ids.shape[0]
        if self.fenced is None:
            self.fenced = torch.zeros(B, dtype=torch.bool, device=input_ids.device)
        n = input_ids.shape[1] - self.P
        if n % self.every != 0:
            return torch.zeros(B, dtype=torch.bool, device=input_ids.device)
        gen = input_ids[:, self.P:]
        tick = backtick_ids(self.tok, 200_000).to(input_ids.device)
        # a closing fence can only appear in the tokens added since the last check (plus a little overlap)
        recent = gen[:, -(self.every + 2):]
        has = tick[recent.clamp(min=0, max=tick.shape[0] - 1)].any(dim=1) & ~self.fenced
        rows = torch.nonzero(has).flatten().tolist()
        if rows:
            g = gen.cpu().tolist()
            nv = vocab_len(self.tok)
            for r in rows:
                ids = []
                for t in g[r]:
                    if t in EOS_IDS:
                        break
                    if t < nv:
                        ids.append(t)
                if fence_closed(self.tok.decode(ids, skip_special_tokens=True), self.kind):
                    self.fenced[r] = True
        return self.fenced.clone()


@torch.no_grad()
def generate_crn(model: Any, tok: Any, prompts: list[list[int]], streams: list[np.ndarray], temps: list[float],
                 max_new: int, fence: str | None, edit: DeltaEdit | None = None, edit_block: int | None = None
                 ) -> list[dict[str, Any]]:
    """Left-padded batch generation with the CRN rule. prompts: token-id lists (may differ in length);
    streams: one uniform array per row (len >= max_new). Returns per-row dicts (token_ids, finish_reason, ...)."""
    from transformers import GenerationConfig, LogitsProcessorList, StoppingCriteriaList

    B = len(prompts)
    Pmax = max(len(p) for p in prompts)
    pad = ENDOFTEXT
    ids = torch.full((B, Pmax), pad, dtype=torch.long)
    mask = torch.zeros((B, Pmax), dtype=torch.long)
    for r, p in enumerate(prompts):
        ids[r, Pmax - len(p):] = torch.tensor(p)
        mask[r, Pmax - len(p):] = 1
    ids, mask = ids.to(model.device), mask.to(model.device)
    U = np.stack([s[:max_new + 1] for s in streams])
    crn = CRNProcessor(U, temps, Pmax, model.device)
    stops = [FenceStop(tok, Pmax, fence)] if fence else []
    gc_ = GenerationConfig(max_new_tokens=max_new, do_sample=False, num_beams=1, eos_token_id=list(EOS_IDS),
                           pad_token_id=pad, repetition_penalty=1.0, temperature=None, top_p=None, top_k=None)
    ctx = block_hooks(model, {edit_block: edit}) if edit is not None else contextlib.nullcontext()
    t0 = time.time()
    with ctx:
        out = model.generate(input_ids=ids, attention_mask=mask, generation_config=gc_,
                             logits_processor=LogitsProcessorList([crn]),
                             stopping_criteria=StoppingCriteriaList(stops) if stops else None)
    dt = time.time() - t0
    gen = out[:, Pmax:].cpu().numpy()
    lp = torch.stack(crn.lp, 1).cpu().numpy() if crn.lp else np.zeros((B, 0))
    nv = vocab_len(tok)
    res = []
    fenced = stops[0].fenced.cpu().numpy() if (stops and stops[0].fenced is not None) else np.zeros(B, bool)
    for r in range(B):
        row = [int(t) for t in gen[r]]
        n = len(row)
        fr = "length"
        for i, t in enumerate(row):
            if t == IM_END:
                n, fr = i + 1, "stop"
                break
            if t == ENDOFTEXT:
                # HF pads a row finished by the fence stop with pad_token_id (= <|endoftext|>); a row the fence did
                # not stop emitted <|endoftext|> itself
                n, fr = i, ("fence" if fenced[r] else "stop")
                break
        if fr == "length" and fenced[r]:
            fr = "fence"
        toks = row[:n]
        text = tok.decode([t for t in toks if t < nv], skip_special_tokens=True)
        res.append({"token_ids": toks, "finish_reason": fr, "n_tokens": len(toks),
                    "logprob_sum": float(lp[r, :len(toks)].sum()) if lp.shape[1] else None,
                    "text": text, "steps": int(gen.shape[1]), "seconds": dt})
    return res


# ------------------------------------------------------------------------------------------------ teacher forcing
@torch.no_grad()
def capture_states(model: Any, ids: list[int], blocks: list[int], positions: list[int],
                   edit: DeltaEdit | None = None, edit_block: int | None = None) -> dict[int, np.ndarray]:
    """Batch-1 forward; returns {block: fp32 [len(positions), D]} block outputs at the given absolute positions."""
    inp = torch.tensor([ids], device=model.device)
    pos_t = torch.tensor(positions, device=model.device)
    got: dict[int, np.ndarray] = {}

    def cap(l):
        def f(h):
            got[l] = h[0, pos_t].float().cpu().numpy()
        return f

    edits = {edit_block: edit} if edit is not None else None
    with block_hooks(model, edits, {l: cap(l) for l in blocks}):
        model.model(input_ids=inp, use_cache=False)
    return got
