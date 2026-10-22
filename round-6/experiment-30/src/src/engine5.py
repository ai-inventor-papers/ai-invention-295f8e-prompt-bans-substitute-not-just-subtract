#!/usr/bin/env python3
"""engine5: exp19's engine_v4 (prefill with block-output edits, PreallocLayer KV cache, float64 inverse-CDF CRN
sampler in vocabulary order, fence stop) generalised to one decoder for every Claim-C arm (plan S5 ENGINE PATHS).

decode_rows(model, rows, tok) decodes a batch whose rows each bring their own prefill (a dict from
engine_v4.prefill: per-layer KV of the prompt, the read-position logits, P). Rows that share a prompt share one
prefill object. If every row has the same prompt length the batch is exactly exp19's shared path (no attention mask);
otherwise the KV caches are LEFT-PADDED into one buffer with a 2-D attention mask and per-row position ids
(engine_path 'leftpad'): this is the path for variable-length histories (BINT, PSL stages B and C, EAP stage B) and
for mixing prompts of different lengths in one batch.

Per-row sampling controls (all float64, one uniform per (row, step) from the row's own stream):
  T, top_k, top_p        code-phase temperature and truncation. top-k keeps the k largest (exp19 rule); top-p keeps
                         the smallest descending-probability prefix whose mass reaches top_p (sorted-mass mask);
                         the inverse CDF then runs in vocabulary order on the kept mass.
  T_early, n_early       temperature schedule: generated code tokens 1..n_early use T_early (DMD), then T.
  intent                 {'T', 'u', 'cap'}: an intent phase BEFORE the code phase (IFG): tokens are drawn at the
                         intent temperature from the intent stream until a token whose text contains a newline, or
                         `cap` tokens (then a newline token is forced and the row is flagged intent_capped); the code
                         phase then starts with the code stream at index 0 (restart_code_stream=True).
  max_new                per-row cap on code-phase tokens; fence: per-row flag for the exp16 fence stop.
Finished rows stay in the batch (fed <|im_end|>) so the batch shape is constant (exp17 prune=False).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch

from cfg import ENDOFTEXT, IM_END
from engine_v4 import _inverse_cdf, backtick_ids, clear_act_cache, fence_closed, vocab_len

_NL: dict[int, torch.Tensor] = {}
NL_TOKEN = 198  # '\n' in the Qwen3 tokenizer (asserted in newline_mask)


def newline_mask(tok: Any) -> torch.Tensor:
    """Boolean [200000] mask of vocabulary ids whose text contains a newline (byte-level BPE 'Ċ')."""
    key = id(tok)
    if key not in _NL:
        V = vocab_len(tok)
        toks = tok.convert_ids_to_tokens(list(range(V)))
        m = np.zeros(200_000, dtype=bool)
        m[:V] = [(t is not None and ("Ċ" in t or "\n" in t)) for t in toks]
        for sid in getattr(tok, "all_special_ids", []):
            if sid < len(m):
                m[sid] = False
        assert tok.decode([NL_TOKEN]) == "\n", "token 198 is not a newline"
        _NL[key] = torch.tensor(m)
    return _NL[key]


def step_probs5(logits: torch.Tensor, T_t: torch.Tensor, top_k_t: torch.Tensor, top_p_t: torch.Tensor,
                any_topk: bool, any_topp: bool) -> torch.Tensor:
    """float64 probabilities: softmax(logits / T_row), then top-k (rows with k > 0) and top-p (rows with p < 1) masks.
    Masked mass is removed, not renormalised here (_inverse_cdf divides by the row total), so a row with T = 1,
    k = 0, p = 1 is exactly exp17's softmax(logits)."""
    probs = torch.softmax(logits / T_t, dim=-1)
    if any_topk:
        K_max = int(top_k_t.max().item())
        kth = probs.topk(K_max, dim=-1).values.gather(-1, (top_k_t.clamp(min=1) - 1)[:, None])
        probs = torch.where((top_k_t > 0)[:, None] & (probs < kth), torch.zeros_like(probs), probs)
    if any_topp:
        sp, si = probs.sort(dim=-1, descending=True)
        cum = sp.cumsum(-1)
        tot = cum[:, -1:]
        keep_sorted = (cum - sp) < top_p_t[:, None] * tot
        keep = torch.zeros_like(keep_sorted).scatter(-1, si, keep_sorted)
        probs = torch.where((top_p_t < 1.0)[:, None] & ~keep, torch.zeros_like(probs), probs)
    return probs


class BufLayer:
    """exp19 PreallocLayer built directly on a preallocated [B, H, Lmax, D] buffer (no second copy)."""

    is_sliding = False
    is_compileable = False

    def __init__(self, kbuf: torch.Tensor, vbuf: torch.Tensor, n: int):
        self.kbuf, self.vbuf, self.n = kbuf, vbuf, n
        self.dtype, self.device = kbuf.dtype, kbuf.device
        self.is_initialized = True
        self.keys, self.values = kbuf[:, :, :n], vbuf[:, :, :n]

    def lazy_initialization(self, key_states: torch.Tensor) -> None:
        return None

    def update(self, key_states, value_states, cache_kwargs=None):
        q = key_states.shape[-2]
        self.kbuf[:, :, self.n:self.n + q] = key_states
        self.vbuf[:, :, self.n:self.n + q] = value_states
        self.n += q
        self.keys, self.values = self.kbuf[:, :, :self.n], self.vbuf[:, :, :self.n]
        return self.keys, self.values

    def get_mask_sizes(self, cache_position: torch.Tensor) -> tuple[int, int]:
        return self.n + cache_position.shape[0], 0

    def get_seq_length(self) -> int:
        return self.n

    def get_max_cache_shape(self) -> int:
        return -1


def assemble_cache(rows: list[dict[str, Any]], max_steps: int):
    """Left-padded KV buffer from per-row prefills. Returns (cache, Pmax, pad list)."""
    from transformers.cache_utils import Cache

    Ps = [r["pre"]["P"] for r in rows]
    Pmax = max(Ps)
    B = len(rows)
    n_layers = len(rows[0]["pre"]["kv"])
    K0 = rows[0]["pre"]["kv"][0][0]
    _, H, _, D = K0.shape
    L = Pmax + max_steps + 1
    layers_ = []
    for l in range(n_layers):
        kb = torch.zeros(B, H, L, D, dtype=K0.dtype, device=K0.device)
        vb = torch.zeros_like(kb)
        for i, r in enumerate(rows):
            K, V = r["pre"]["kv"][l]
            P = r["pre"]["P"]
            kb[i, :, Pmax - P:Pmax] = K[0]
            vb[i, :, Pmax - P:Pmax] = V[0]
        layers_.append(BufLayer(kb, vb, Pmax))
    return Cache(layers=layers_), Pmax, [Pmax - p for p in Ps]


def kv_bytes(B: int, L: int) -> int:
    return int(B * L * 147_456)


@torch.no_grad()
def decode_rows(model: Any, rows: list[dict[str, Any]], tok: Any, fence_kind: str | None = None,
                check_every: int = 8) -> list[dict[str, Any]]:
    """rows: [{'pre', 'u', 'T', 'top_k'=0, 'top_p'=1, 'T_early'=None, 'n_early'=0, 'max_new', 'fence'=False,
    'intent'=None, 'restart_code_stream'=True}]. Returns per row: token_ids (all generated, intent first),
    intent_len, intent_capped, finish_reason ('stop' | 'fence' | 'length'), n_tokens, logprob_sum, steps,
    engine_path."""
    dev = model.device
    B = len(rows)
    max_new = [int(r["max_new"]) for r in rows]
    caps = [int(r["intent"]["cap"]) if r.get("intent") else 0 for r in rows]
    max_steps = max(m + c for m, c in zip(max_new, caps))
    cache, Pmax, pads = assemble_cache(rows, max_steps)
    padded = any(p > 0 for p in pads)
    am_full = None
    if padded:
        am_full = torch.ones(B, Pmax + max_steps + 1, dtype=torch.long, device=dev)
        for i, p in enumerate(pads):
            if p:
                am_full[i, :p] = 0
    Pvec = torch.tensor([r["pre"]["P"] for r in rows], dtype=torch.long, device=dev)
    # streams
    Ucode = torch.zeros(B, max(max_new), dtype=torch.float64, device=dev)
    for i, r in enumerate(rows):
        u = np.asarray(r["u"], dtype=np.float64)[:max_new[i]]
        assert len(u) >= max_new[i], "code stream shorter than max_new"
        Ucode[i, :max_new[i]] = torch.from_numpy(u)
    cap_max = max(caps) if any(caps) else 1
    Uint = torch.zeros(B, cap_max, dtype=torch.float64, device=dev)
    T_int = torch.ones(B, dtype=torch.float64, device=dev)
    for i, r in enumerate(rows):
        if r.get("intent"):
            ui = np.asarray(r["intent"]["u"], dtype=np.float64)[:caps[i]]
            Uint[i, :len(ui)] = torch.from_numpy(ui)
            T_int[i] = float(r["intent"]["T"])
    T_code = torch.tensor([float(r["T"]) for r in rows], dtype=torch.float64, device=dev)
    T_early = torch.tensor([float(r.get("T_early") if r.get("T_early") is not None else r["T"]) for r in rows],
                           dtype=torch.float64, device=dev)
    n_early = torch.tensor([int(r.get("n_early") or 0) for r in rows], dtype=torch.long, device=dev)
    top_k_t = torch.tensor([int(r.get("top_k") or 0) for r in rows], dtype=torch.long, device=dev)
    top_p_t = torch.tensor([float(r.get("top_p") if r.get("top_p") is not None else 1.0) for r in rows],
                           dtype=torch.float64, device=dev)
    any_topk = bool((top_k_t > 0).any())
    any_topp = bool((top_p_t < 1.0).any())
    trunc = (top_k_t > 0) | (top_p_t < 1.0)
    maxnew_t = torch.tensor(max_new, dtype=torch.long, device=dev)
    cap_t = torch.tensor(caps, dtype=torch.long, device=dev)
    restart = torch.tensor([bool(r.get("restart_code_stream", True)) for r in rows], device=dev)
    fence_rows = torch.tensor([bool(r.get("fence")) for r in rows], device=dev)
    in_int = torch.tensor([bool(r.get("intent")) and caps[i] > 0 for i, r in enumerate(rows)], device=dev)
    i_code = torch.zeros(B, dtype=torch.long, device=dev)
    i_int = torch.zeros(B, dtype=torch.long, device=dev)
    int_len = torch.zeros(B, dtype=torch.long, device=dev)
    int_capped = torch.zeros(B, dtype=torch.bool, device=dev)
    nlm = newline_mask(tok).to(dev) if in_int.any() else None
    tick = backtick_ids(tok).to(dev) if (fence_kind and bool(fence_rows.any())) else None
    logits = torch.stack([r["pre"]["r_logits"] for r in rows], 0).double()
    toks = torch.full((B, max_steps), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((B, max_steps), dtype=torch.float64, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    ar = torch.arange(B, device=dev)
    host_toks: list[list[int]] = [[] for _ in range(B)]
    last_sync = 0
    step = 0
    try:
        while True:
            T_eff = torch.where(in_int, T_int, torch.where(i_code < n_early, T_early, T_code))
            probs = step_probs5(logits, T_eff[:, None], top_k_t, top_p_t, any_topk, any_topp)
            u = torch.where(in_int, Uint[ar, i_int.clamp(max=cap_max - 1)],
                            Ucode[ar, i_code.clamp(max=Ucode.shape[1] - 1)])
            nxt = _inverse_cdf(probs, u)
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            if any_topk or any_topp:
                plp = torch.where(trunc, plp - torch.log(probs.sum(-1)), plp)
            live = ~done
            if nlm is not None:
                was_int = in_int & live
                is_nl = nlm[nxt]
                capped = was_int & ~is_nl & (i_int + 1 >= cap_t)
                nxt = torch.where(capped, torch.full_like(nxt, NL_TOKEN), nxt)
                int_capped |= capped
                int_len += was_int.long()
                switch = was_int & (is_nl | capped)
                i_int += was_int.long()
                code_step = live & ~was_int
                i_code += code_step.long()
                # restart_code_stream=False (plumbing test): the code phase continues the code stream index
                i_code = torch.where(switch & ~restart, i_int, i_code)
                in_int = in_int & ~switch
            else:
                i_code += live.long()
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            done |= is_end | (live & (i_code >= maxnew_t))
            if step + 1 >= max_steps:
                break
            if (step + 1) % check_every == 0:
                if tick is not None:
                    chunk = toks[:, last_sync:step + 1]
                    has_tick = (tick[chunk.clamp(min=0)] & (chunk >= 0)).any(dim=1) & ~done & fence_rows
                    chunk_c = chunk.cpu().numpy()
                    for r_ in range(B):
                        host_toks[r_].extend(int(t) for t in chunk_c[r_] if t >= 0)
                    last_sync = step + 1
                    cand = torch.nonzero(has_tick).flatten().tolist()
                    if cand:
                        nv = vocab_len(tok)
                        newly = [r_ for r_ in cand if fence_closed(
                            tok.decode([t for t in host_toks[r_] if t < nv], skip_special_tokens=True), fence_kind)]
                        if newly:
                            idx = torch.tensor(newly, device=dev)
                            fenced[idx] = True
                            done[idx] = True
                if bool(done.all().item()):
                    break
            feed = torch.where(done, im_end_t, nxt)[:, None]
            pos = (Pvec + step)[:, None]
            clear_act_cache()
            if padded:
                h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                                attention_mask=am_full[:, :Pmax + step + 1], use_cache=True).last_hidden_state
            else:
                h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                                use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            step += 1
    finally:
        clear_act_cache()
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c, fenced_c = ended.cpu().numpy(), fenced.cpu().numpy()
    il, ic = int_len.cpu().numpy(), int_capped.cpu().numpy()
    out = []
    for r_ in range(B):
        row = toks_c[r_]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        fr = "stop" if ended_c[r_] else ("fence" if fenced_c[r_] else "length")
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n, "intent_len": int(il[r_]),
                    "intent_capped": bool(ic[r_]), "logprob_sum": float(lps_c[r_, :n].sum()), "steps": step + 1,
                    "engine_path": "leftpad" if padded else "shared"})
    return out


@torch.no_grad()
def decode_record(model: Any, rows: list[dict[str, Any]], n_steps: int) -> dict[str, torch.Tensor]:
    """Calibration decode: n_steps tokens per row at the row's temperature schedule (no truncation), recording the
    fp32 log-softmax of the UNSCALED (T = 1) logits at every step (the distribution each token was drawn from at
    T = 1) plus the tokens. All rows must share the prompt length or be left-padded (same machinery)."""
    dev = model.device
    B = len(rows)
    cache, Pmax, pads = assemble_cache(rows, n_steps)
    padded = any(p > 0 for p in pads)
    am_full = None
    if padded:
        am_full = torch.ones(B, Pmax + n_steps + 1, dtype=torch.long, device=dev)
        for i, p in enumerate(pads):
            if p:
                am_full[i, :p] = 0
    Pvec = torch.tensor([r["pre"]["P"] for r in rows], dtype=torch.long, device=dev)
    U = torch.tensor(np.stack([np.asarray(r["u"], dtype=np.float64)[:n_steps] for r in rows]), device=dev)
    T_t = torch.tensor([float(r.get("T", 1.0)) for r in rows], dtype=torch.float64, device=dev)[:, None]
    logits = torch.stack([r["pre"]["r_logits"] for r in rows], 0).float()
    toks = torch.zeros((B, n_steps), dtype=torch.long, device=dev)
    lsm = torch.zeros((B, n_steps, logits.shape[-1]), dtype=torch.float32, device=dev)
    for step in range(n_steps):
        lsm[:, step] = torch.log_softmax(logits, dim=-1)
        probs = torch.softmax(logits.double() / T_t, dim=-1)
        nxt = _inverse_cdf(probs, U[:, step])
        toks[:, step] = nxt
        if step + 1 == n_steps:
            break
        pos = (Pvec + step)[:, None]
        clear_act_cache()
        kw = {"attention_mask": am_full[:, :Pmax + step + 1]} if padded else {}
        h = model.model(input_ids=nxt[:, None], past_key_values=cache, position_ids=pos, use_cache=True,
                        **kw).last_hidden_state
        logits = model.lm_head(h[:, -1]).float()
    del cache
    clear_act_cache()
    return {"tokens": toks, "lsm": lsm}


@torch.no_grad()
def teacher_force_lsm(model: Any, prompt_ids: list[int], cont: torch.Tensor) -> torch.Tensor:
    """fp32 log-softmax of the clean model at the positions that predict cont[:, j] given prompt + cont[:, :j]
    (j = 0..n-1). prompt_ids is shared by all rows (same template)."""
    dev = model.device
    B, n = cont.shape
    P = len(prompt_ids)
    inp = torch.cat([torch.tensor([prompt_ids], device=dev).expand(B, -1), cont[:, :n - 1]], 1)
    clear_act_cache()
    h = model.model(input_ids=inp, use_cache=False).last_hidden_state
    lg = model.lm_head(h[:, P - 1:P - 1 + n]).float()
    clear_act_cache()
    return torch.log_softmax(lg, dim=-1)


def kl_rows(lp: torch.Tensor, lq: torch.Tensor) -> torch.Tensor:
    """KL(p || q) per leading index from log-probabilities (fp32 in, float64 accumulation)."""
    p = lp.double().exp()
    return (p * (lp.double() - lq.double())).sum(-1)


def kl_scaled(lsm: torch.Tensor, T: float) -> torch.Tensor:
    """KL(softmax(z / T) || softmax(z)) per position from z's log-softmax (z = lsm + const per position), float64."""
    z = lsm.double()
    lq = torch.log_softmax(z, dim=-1)
    lpT = torch.log_softmax(z / T, dim=-1)
    return (lpT.exp() * (lpT - lq)).sum(-1)


def timed(f, *a, **k):
    t0 = time.time()
    out = f(*a, **k)
    return out, time.time() - t0
