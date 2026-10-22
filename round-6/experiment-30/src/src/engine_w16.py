#!/usr/bin/env python3
"""W16A16 HF engine for Qwen3-8B (bf16 weights and activations, sdpa) -- exp20 engine.py / exp27 engine5.py ported.

Kept from exp20 (src/engine.py) and exp27 (src/engine5.py, the bf16 path):
- batch-1 prompt prefill with block-output edit / capture hooks; logits only at the last prompt position
  (the equivalent of logits_to_keep=1: lm_head is applied to the final position only);
- the exp8 common-random-numbers inverse-CDF sampler in float64, vocabulary order (exp27 step_probs5 with T = 1,
  top-k off, top-p 1 is exactly softmax(logits)); finished rows stay in the batch and are fed <|im_end|>, so the batch
  shape is constant at every step;
- exp20's fence stop: a row finishes once it has emitted two tokens containing a code fence (```), i.e. at the closing
  fence of its first code block;
- the S3 decode-time site: (hooked, shadow) row pairs in one batch; for decode steps whose INPUT is generated token
  1-32 the hooked row's block outputs at blocks 12-23 are displaced along its unit u so that (h_hooked - h_shadow).u
  equals the target exactly; the shadow row is fed the hooked row's token (teacher forcing), so it carries the clean
  states of the same text. Logs per pair: displacement at blocks 23 and 35 and KL(hooked || shadow) per step.
New here: the KV buffer is written directly from the per-row prefills (no intermediate concatenation), teacher-forced
scoring of code openings (F2: log-softmax in fp32 on the first 48 code positions only), and a top-k / temperature
sampler for the thinking-on margin (F2-thinking).
"""

from __future__ import annotations

import contextlib
import gc
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg import ENDOFTEXT, IM_END, MODEL_ID, MODEL_REVISION, model_path, stable_seed


def load_model(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION, vram_fraction: float = 0.96):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    kw = {"revision": revision} if path == model_id and revision else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, low_cpu_mem_usage=True, **kw)
    model.eval()
    model.requires_grad_(False)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"{model_id}@{(revision or '')[:8]} loaded bf16 in {time.time() - t0:.0f}s; free VRAM "
                f"{free / 1e9:.1f}/{total / 1e9:.1f} GB")
    return tok, model


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


# ------------------------------------------------------------------------------------------------ caches
def _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


@torch.no_grad()
def prefill(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 prompt pass with optional block-output edits. Returns {'kv', 'r_logits' (fp32 [V]), 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=model.device)
    cache = DynamicCache()
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


class BufLayer:
    """KV layer on a preallocated [B, H, Lmax, D] buffer: update() writes in place and returns views of the prefix."""

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


def build_cache(groups: list[dict[str, Any]], max_len: int):
    """Preallocated cache for the fixed-shape batch: group g's prefill KV is copied into its rows."""
    from transformers.cache_utils import Cache

    P = groups[0]["pre"]["P"]
    B = sum(len(g["us"]) for g in groups)
    n_layers = len(groups[0]["pre"]["kv"])
    K0 = groups[0]["pre"]["kv"][0][0]
    _, H, _, D = K0.shape
    lay = []
    for l in range(n_layers):
        kb = torch.empty(B, H, max_len, D, dtype=K0.dtype, device=K0.device)
        vb = torch.empty_like(kb)
        i = 0
        for g in groups:
            K, V = g["pre"]["kv"][l]
            n = len(g["us"])
            kb[i:i + n, :, :P] = K[0]
            vb[i:i + n, :, :P] = V[0]
            i += n
        lay.append(BufLayer(kb, vb, P))
    return Cache(layers=lay)


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int = 1536) -> np.ndarray:
    """exp17/exp8 token uniforms: PCG64(stable_seed(*key)).random(n) (prefix-stable in n)."""
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


def fence_token_mask(tok: Any, device: torch.device) -> torch.Tensor:
    """Bool [V]: tokens whose decoded text contains a code fence (```)."""
    V = len(tok)
    m = np.zeros(max(V, 151936 + 1024), dtype=bool)
    for i in range(V):
        if "```" in tok.decode([i]):
            m[i] = True
    return torch.tensor(m, device=device)


@torch.no_grad()
def sample(model: Any, groups: list[dict[str, Any]], max_new: int, fence_mask: torch.Tensor | None = None,
           s3: dict[str, Any] | None = None, check_every: int = 8, no_stop: bool = False,
           temperature: float = 1.0) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[>= max_new], ...]}] -- a group's prefill is shared by its rows.
    One uniform per (row, step); token = first index whose CDF (vocabulary order, float64) >= u (exp8 sampler).
    s3 (optional): {'hooked': [row idx], 'shadow': [row idx], 'u': fp32 [n_pairs, D], 'target': {l: fp32 [n_pairs]},
    'blocks': [...], 'steps': 32, 'log_blocks': [23, 35], 'keep_shadow_states': bool}."""
    P = groups[0]["pre"]["P"]
    assert all(g["pre"]["P"] == P for g in groups), "all rows of a batch must share the prompt length"
    dev = model.device
    cache = build_cache(groups, P + max_new + 1)
    us = [u for g in groups for u in g["us"]]
    B = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["us"]), -1) for g in groups], 0).double()
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((B, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    nfence = torch.zeros(B, dtype=torch.long, device=dev)
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    state = {"step": 0}
    hooks = []
    s3_log: dict[str, list] = {"disp": [], "kl": [], "shadow_states": [], "hooked_states": []}
    if s3:
        hi = torch.tensor(s3["hooked"], device=dev, dtype=torch.long)
        si = torch.tensor(s3["shadow"], device=dev, dtype=torch.long)
        Uv = s3["u"].to(dev, torch.float32)  # [n, D]
        tgt = {l: s3["target"][l].to(dev, torch.float32) for l in s3["blocks"]}
        log_blocks = s3.get("log_blocks", [23, 35])
        cur_disp: dict[int, torch.Tensor] = {}

        def mk(l):
            def hook(mod, inp, out):
                h = _out_tensor(out)
                if h.shape[1] != 1:
                    return out
                if l in tgt and state["step"] < s3["steps"]:
                    hh = h[hi, 0].float()
                    hs = h[si, 0].float()
                    coef = tgt[l] - ((hh - hs) * Uv).sum(-1)
                    h = h.clone()
                    h[hi, 0] = (hh + coef[:, None] * Uv).to(h.dtype)
                    out = _replace_out(out, h)
                if l in log_blocks and state["step"] < s3["steps"]:
                    cur_disp[l] = (h[hi, 0].float() - h[si, 0].float()).norm(dim=-1)
                    if s3.get("keep_shadow_states") and l == log_blocks[0]:
                        s3_log["shadow_states"].append(h[si, 0].float().cpu())
                        s3_log["hooked_states"].append(h[hi, 0].float().cpu())
                return out
            return hook
        for l in sorted(set(s3["blocks"]) | set(log_blocks)):
            hooks.append(layers(model)[l].register_forward_hook(mk(l)))
    step = 0
    try:
        while True:
            state["step"] = step
            probs = torch.softmax(logits / temperature, dim=-1)
            nxt = _inverse_cdf(probs, U[:, step])
            if s3:
                nxt[si] = nxt[hi]  # shadows are teacher-forced with the hooked row's token
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            if fence_mask is not None and not no_stop:
                nfence += (fence_mask[nxt] & live).long()
                fz = live & (nfence >= 2) & ~is_end
                fenced |= fz
                done |= fz
            done |= is_end
            if s3:
                done[si] = done[hi]
            if no_stop:
                done.zero_()
            if step + 1 >= max_new:
                break
            if (step + 1) % check_every == 0 and bool(done.all().item()):
                break
            feed = torch.where(done, im_end_t, nxt)[:, None]
            pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                            use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            if s3 and step < s3["steps"]:
                lp_h = torch.log_softmax(logits[hi], -1)
                lp_s = torch.log_softmax(logits[si], -1)
                s3_log["kl"].append((lp_h.exp() * (lp_h - lp_s)).sum(-1).float())
                s3_log["disp"].append({l: cur_disp[l].clone() for l in cur_disp})
            step += 1
    finally:
        for hk in hooks:
            hk.remove()
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    fenced_c = fenced.cpu().numpy()
    out = []
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        fr = "stop" if ended_c[r] else ("fence" if fenced_c[r] else "length")
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n,
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1})
    if s3:
        kl = torch.stack(s3_log["kl"], 0).cpu().numpy() if s3_log["kl"] else np.zeros((0, len(s3["hooked"])))
        disp = {l: torch.stack([d[l] for d in s3_log["disp"]], 0).cpu().numpy() for l in
                (s3_log["disp"][0].keys() if s3_log["disp"] else [])}
        for j, r in enumerate(s3["hooked"]):
            out[r]["s3"] = {"kl_mean_steps1_32": float(kl[:, j].mean()) if len(kl) else None,
                            "kl_steps": [round(float(x), 6) for x in kl[:, j]],
                            "disp_mean": {int(l): float(disp[l][:, j].mean()) for l in disp},
                            "disp_steps": {int(l): [round(float(x), 4) for x in disp[l][:, j]] for l in disp}}
        if s3.get("keep_shadow_states"):
            out[0]["_shadow_states"] = s3_log["shadow_states"]
            out[0]["_hooked_states"] = s3_log["hooked_states"]
    return out


@torch.no_grad()
def forward_capture(model: Any, ids: list[int], blocks: list[int], positions: list[int] | None = None,
                    edits: dict | None = None) -> dict[int, torch.Tensor]:
    """Batch-1 forward without cache; returns block outputs ({l: fp32 [T or len(positions), D]} on GPU)."""
    got: dict[int, torch.Tensor] = {}

    def cap(l):
        def f(h):
            x = h[0] if positions is None else h[0, positions]
            got[l] = x.float().clone()
        return f
    with block_hooks(model, edits, {l: cap(l) for l in blocks}):
        model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
    return got


@torch.no_grad()
def score_openings(model: Any, items: list[dict[str, Any]], n_score: int = 48, batch: int = 8,
                   capture_blocks: tuple[int, ...] = (), cap_tokens: int = 32) -> list[dict[str, Any]]:
    """Teacher-forced fp32 log-probabilities of the first n_score code tokens.
    items: [{'ids': prompt + continuation ids, 'P': prompt length, 'cs': index (in the continuation) of the first
    code token, 'n': number of continuation tokens}]. Rows are right-padded (causal attention: valid positions never
    see the padding). Hidden states are sliced to the scored positions BEFORE lm_head. Returns per item 'lp' (fp32
    [m] array of per-token log-probs, m = min(n_score, n - cs)) and optionally the mean residual over code tokens
    1..cap_tokens at capture_blocks."""
    out: list[dict[str, Any]] = [None] * len(items)  # type: ignore[list-item]
    dev = model.device
    for b0 in range(0, len(items), batch):
        chunk = items[b0:b0 + batch]
        L = max(len(it["ids"]) for it in chunk)
        inp = torch.full((len(chunk), L), IM_END, dtype=torch.long, device=dev)
        for i, it in enumerate(chunk):
            inp[i, :len(it["ids"])] = torch.tensor(it["ids"], device=dev)
        caps: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                caps[l] = h.float()
            return g
        with block_hooks(model, None, {l: mk(l) for l in capture_blocks}):
            h = model.model(input_ids=inp, use_cache=False).last_hidden_state
        for i, it in enumerate(chunk):
            P, cs, n = it["P"], it["cs"], it["n"]
            m = max(0, min(n_score, n - cs))
            res: dict[str, Any] = {"m": m}
            if m > 0:
                a = P + cs - 1  # the position that predicts continuation token cs
                lg = model.lm_head(h[i, a:a + m]).float()
                lsm = torch.log_softmax(lg, dim=-1)
                tgt = inp[i, a + 1:a + 1 + m]
                res["lp"] = lsm.gather(-1, tgt[:, None])[:, 0].cpu().numpy()
            else:
                res["lp"] = np.zeros(0, dtype=np.float32)
            if capture_blocks:
                mc = max(1, min(cap_tokens, n - cs))
                res["states"] = {l: caps[l][i, P + cs:P + cs + mc].mean(0).cpu().numpy() for l in capture_blocks}
            out[b0 + i] = res
        del h, caps
    return out


@torch.no_grad()
def sample_think(model: Any, ids: list[int], us: list[np.ndarray], max_new: int, T: float, top_k: int,
                 check_every: int = 16) -> list[dict[str, Any]]:
    """Thinking-on traces (F2-thinking): shared prompt, one uniform stream per row, softmax(logits / T) restricted to
    the top-k tokens, inverse CDF in vocabulary order on the kept mass (exp27 step_probs5). Stops at <|im_end|>."""
    dev = model.device
    pre = prefill(model, ids)
    groups = [{"pre": pre, "us": us}]
    P = pre["P"]
    cache = build_cache(groups, P + max_new + 1)
    B = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = pre["r_logits"][None].expand(B, -1).double()
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    step = 0
    while True:
        probs = torch.softmax(logits / T, dim=-1)
        kth = probs.topk(top_k, dim=-1).values[:, -1:]
        probs = torch.where(probs < kth, torch.zeros_like(probs), probs)
        nxt = _inverse_cdf(probs, U[:, step])
        live = ~done
        toks[:, step] = torch.where(live, nxt, toks[:, step])
        done |= (nxt == IM_END) | (nxt == ENDOFTEXT)
        if step + 1 >= max_new:
            break
        if (step + 1) % check_every == 0 and bool(done.all().item()):
            break
        feed = torch.where(done, im_end_t, nxt)[:, None]
        pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
        h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    tc = toks.cpu().numpy()
    return [{"token_ids": [int(t) for t in tc[r][tc[r] >= 0]], "n_tokens": int((tc[r] >= 0).sum()),
             "finished": bool(done[r].item())} for r in range(B)]


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()
