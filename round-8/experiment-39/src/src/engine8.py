#!/usr/bin/env python3
"""engine8: the iteration-6/7 bf16 HF engine (vendored engine5/engine_v4, unmodified) with one generalised decoder.

Reused unchanged from inputs/iter6_exp30/src: engine5.assemble_cache (left-padded preallocated KV), engine_v4
._inverse_cdf (inverse CDF over the FULL vocabulary in TOKEN-ID order), engine_v4.fence_closed / backtick_ids,
engine_v4._kv_list. Qwen loading follows exp35 engine7.load_model; Gemma loading follows exp38 engine.load_model
(text tower only, tied lm_head), both re-written here so that no vendored module writes into inputs/.

decode_k1(model, tok, rows, flavor) = engine5.decode_rows / engine7.decode_stop with a per-row, per-step schedule:
  every row: T, top_p, top_k, min_p (global, every position; min-p truncates the T = 1 probabilities, then
             temperature applies to the survivors: the temperature-last order of the min-p authors)
  edt        {'q', 'T'}: T at every step whose T = 1 next-token entropy exceeds q, T = 1 elsewhere (EDT-style)
  adapt      {'T'}: T at the first non-whitespace token after every newline that ends a line ending in ':'
             (AdapT-style code-block starts; whitespace tokens in between inherit T, see README)
  openings   canonical openings [ids]: a row is ON opening c while its generated tokens equal O_c's prefix; at
             generated index |O_c| the DECISION is flagged (node c)
  dose       {'T', 'k'}: applied at the decision index only (fork-dosed arms)
  dose2      {'tokens', 'T', 'k'}: a second dose at decision index + 1 when the decision token is in `tokens`
  force_dec  {c: [ids]}: forced token(s) from the decision index of node c (class-uniform forcing)
  fixed_pos  {'pos': [indices], 'T', 'k'}: dose at fixed generated indices (entropy-max / random-window placebos)
  window     {'n', 'T', 'k'}: dose the first n tokens after the first line ending in ':' (boundary window arm)
  prefix     [ids]: forced generated tokens 0..len-1 (token-map / HR / locator continuations)
A forced token skips the inverse CDF but still consumes its uniform, so later uniforms stay aligned with the twin.
With every option at its default, a row's per-step transform is exactly engine5's (T = 1, no truncation).
Logged per row: decision index and node, decision token, the T = 1 top-64 (ids, float64 logits) and entropy at the
decision, T = 1 entropies of steps 1..96, and the mean final-norm hidden state over the 16 positions from the
decision token on (F8 geometry; no extra forward pass).
"""

from __future__ import annotations

import gc
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg8 import (ENTROPY_STEPS, GEMMA_EOS, GEMMA_EOT, GEMMA_ID, GEMMA_REV, I6_SRC, QWEN_EOT, QWEN_ID, QWEN_IM_END,
                  QWEN_REV, model_path)

if str(I6_SRC) not in sys.path:
    sys.path.append(str(I6_SRC))

import engine5 as E5  # noqa: E402
import engine_v4 as E4  # noqa: E402

inverse_cdf = E4._inverse_cdf
GEMMA_FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)\n[ \t]*```", re.S)
TOP_SAVE = 64
HID_N = 16


# ------------------------------------------------------------------------------------------------ loading
def load_qwen(vram_fraction: float = 0.96) -> tuple[Any, Any, dict[str, Any]]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(QWEN_ID, QWEN_REV)
    tok = AutoTokenizer.from_pretrained(path)
    dev = torch.device("cuda", 0)
    free0, total = torch.cuda.mem_get_info(0)
    cpu_embed = free0 < 18 * 1024 ** 3
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": "cpu"}, low_cpu_mem_usage=True)
    assert not model.config.tie_word_embeddings
    for layer in model.model.layers:
        layer.to(dev)
    model.model.norm.to(dev)
    model.model.rotary_emb.to(dev)
    model.lm_head.to(dev)
    if cpu_embed:
        from engine6 import CPUEmbedding
        model.model.embed_tokens = CPUEmbedding(model.model.embed_tokens.weight.data.contiguous(), dev)
    else:
        model.model.embed_tokens.to(dev)
    gc.collect()
    torch.cuda.empty_cache()
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    model._aii_flavor = "qwen"
    info = {"model": QWEN_ID, "revision": QWEN_REV, "precision": "bf16", "cpu_embedding": bool(cpu_embed),
            "free_vram_before_GB": round(free0 / 1e9, 3), "free_vram_after_GB": round(free / 1e9, 3),
            "total_vram_GB": round(total / 1e9, 3), "gpu": torch.cuda.get_device_name(0),
            "load_seconds": round(time.time() - t0, 1)}
    logger.info(f"Qwen3-8B bf16 loaded: {info}")
    return tok, model, info


def load_gemma(vram_fraction: float = 0.96) -> tuple[Any, Any, dict[str, Any]]:
    from safetensors import safe_open
    from transformers import AutoConfig, AutoTokenizer, Gemma3ForCausalLM

    t0 = time.time()
    path = model_path(GEMMA_ID, GEMMA_REV)
    tok = AutoTokenizer.from_pretrained(path)
    assert tok.convert_tokens_to_ids("<end_of_turn>") == GEMMA_EOT
    cfg = AutoConfig.from_pretrained(path)
    tcfg = cfg.text_config
    tcfg._attn_implementation = "sdpa"
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
    model.eval()
    model.requires_grad_(False)
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
                sd[nk].copy_(t.to(sd[nk].dtype))
                loaded.add(nk)
                del t
    model.tie_weights()
    missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
    assert not missing, f"weights not loaded: {missing[:5]}"
    gc.collect()
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(0)
    model._aii_flavor = "gemma"
    info = {"model": GEMMA_ID, "revision": GEMMA_REV, "precision": "bf16", "n_tensors": len(loaded),
            "free_vram_after_GB": round(free / 1e9, 3), "total_vram_GB": round(total / 1e9, 3),
            "gpu": torch.cuda.get_device_name(0), "load_seconds": round(time.time() - t0, 1),
            "final_logit_softcapping": tcfg.final_logit_softcapping, "sliding_window": tcfg.sliding_window}
    logger.info(f"Gemma-3-4b-it bf16 loaded: {info}")
    return tok, model, info


def free_model(model: Any) -> None:
    del model
    gc.collect()
    torch.cuda.empty_cache()


def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


def lm_logits(model: Any, h: torch.Tensor) -> torch.Tensor:
    """fp32 logits (Gemma: optional final soft-cap, exp38 rule)."""
    x = model.lm_head(h).float()
    cap = getattr(model.config, "final_logit_softcapping", None)
    if cap is not None:
        x = torch.tanh(x / cap) * cap
    return x


def vocab_n(model: Any) -> int:
    return int(model.lm_head.weight.shape[0])


@torch.no_grad()
def prefill(model: Any, ids: list[int]) -> dict[str, Any]:
    """Batch-1 prompt pass -> {'kv' per layer (K, V), 'r_logits' fp32 [V], 'P'} (engine7.prefill, no hooks)."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=dev_of(model))
    cache = DynamicCache()
    out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = lm_logits(model, out.last_hidden_state[:, -1])[0]
    kv = [(K.clone(), V.clone()) for K, V in E4._kv_list(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


@torch.no_grad()
def teacher_force_last(model: Any, ids_list: list[list[int]]) -> np.ndarray:
    """fp32 logits predicting the token after each sequence (batch-1 passes) -> float64 [n, V] numpy."""
    out = []
    for ids in ids_list:
        inp = torch.tensor([ids], device=dev_of(model))
        h = model.model(input_ids=inp, use_cache=False).last_hidden_state
        out.append(lm_logits(model, h[0, -1:]).double()[0].cpu().numpy())
        del h
    return np.stack(out)


@torch.no_grad()
def teacher_force_rows(model: Any, ids: list[int], start: int) -> np.ndarray:
    """fp32 logits at positions start-1 .. len(ids)-1 (row j predicts ids[start + j]) -> float64 numpy."""
    inp = torch.tensor([ids], device=dev_of(model))
    h = model.model(input_ids=inp, use_cache=False).last_hidden_state
    lg = lm_logits(model, h[0, start - 1:]).double().cpu().numpy()
    del h
    return lg


# ------------------------------------------------------------------------------------------------ token tables
_TABLES: dict[int, dict[str, torch.Tensor]] = {}


def token_tables(tok: Any, V: int, dev: torch.device) -> dict[str, torch.Tensor]:
    """Per-vocabulary booleans for the AdapT/window line state machine."""
    key = id(tok)
    if key not in _TABLES:
        n = min(V, len(tok))
        texts = [tok.decode([i]) for i in range(n)] + [""] * (V - n)
        f = {k: np.zeros(V, dtype=bool) for k in ("nl", "colon_b", "ns_b", "colon_a", "ns_a", "ns")}
        for i, t in enumerate(texts):
            if not t:
                continue
            b, a = t.split("\n")[0], t.split("\n")[-1]
            f["nl"][i] = "\n" in t
            f["colon_b"][i] = b.rstrip(" \t").endswith(":")
            f["ns_b"][i] = b.strip() != ""
            f["colon_a"][i] = a.rstrip(" \t").endswith(":")
            f["ns_a"][i] = a.strip() != ""
            f["ns"][i] = t.strip() != ""
        _TABLES[key] = {k: torch.tensor(v, device=dev) for k, v in f.items()}
    return _TABLES[key]


def gemma_fence_closed(text: str) -> bool:
    for m in GEMMA_FENCE_RE.finditer(text):
        if "def " in m.group(1):
            return True
    return False


# ------------------------------------------------------------------------------------------------ decoder
def _probs(logits: torch.Tensor, T: torch.Tensor, k: torch.Tensor, p: torch.Tensor, mp: torch.Tensor,
           flavor: str) -> torch.Tensor:
    """Per-row sampling distribution (unnormalised after masks; the inverse CDF divides by the kept mass)."""
    if flavor == "qwen":
        probs = torch.softmax(logits / T[:, None], dim=-1)                      # float64 (engine5)
    else:
        probs = torch.softmax(logits.float() / T.float()[:, None], dim=-1).double()   # exp38 numerics
    if bool((mp > 0).any()):
        p1 = torch.softmax(logits.double(), dim=-1)
        keep = p1 >= mp[:, None] * p1.max(dim=-1, keepdim=True).values
        probs = torch.where((mp > 0)[:, None] & ~keep, torch.zeros_like(probs), probs)
    if bool((k > 0).any()):
        K_max = int(k.max().item())
        kth = probs.topk(K_max, dim=-1).values.gather(-1, (k.clamp(min=1) - 1)[:, None])
        probs = torch.where((k > 0)[:, None] & (probs < kth), torch.zeros_like(probs), probs)
    if bool((p < 1.0).any()):
        sp, si = probs.sort(dim=-1, descending=True)
        cum = sp.cumsum(-1)
        tot = cum[:, -1:]
        keep_sorted = (cum - sp) < p[:, None] * tot
        keep = torch.zeros_like(keep_sorted).scatter(-1, si, keep_sorted)
        probs = torch.where((p < 1.0)[:, None] & ~keep, torch.zeros_like(probs), probs)
    return probs


@torch.no_grad()
def decode_k1(model: Any, tok: Any, rows: list[dict[str, Any]], *, fence_kind: str | None,
              stop_fn: Callable[[int, list[int]], bool] | None = None, check_every: int = 8,
              capture_hidden: bool = True) -> list[dict[str, Any]]:
    flavor = model._aii_flavor
    dev = dev_of(model)
    B = len(rows)
    V = vocab_n(model)
    max_new = [int(r["max_new"]) for r in rows]
    max_steps = max(max_new)
    cache, Pmax, pads = E5.assemble_cache(rows, max_steps)
    padded = any(p_ > 0 for p_ in pads)
    am_full = None
    if padded:
        am_full = torch.ones(B, Pmax + max_steps + 1, dtype=torch.long, device=dev)
        for i, p_ in enumerate(pads):
            if p_:
                am_full[i, :p_] = 0
    Pvec = torch.tensor([r["pre"]["P"] for r in rows], dtype=torch.long, device=dev)
    U = torch.zeros(B, max_steps, dtype=torch.float64, device=dev)
    for i, r in enumerate(rows):
        u = np.asarray(r["u"], dtype=np.float64)[:max_new[i]]
        assert len(u) >= max_new[i], "uniform stream shorter than max_new"
        U[i, :max_new[i]] = torch.from_numpy(u)
    f64 = dict(dtype=torch.float64, device=dev)
    T_g = torch.tensor([float(r.get("T", 1.0)) for r in rows], **f64)
    k_g = torch.tensor([int(r.get("top_k") or 0) for r in rows], dtype=torch.long, device=dev)
    p_g = torch.tensor([float(r.get("top_p", 1.0) or 1.0) for r in rows], **f64)
    mp_g = torch.tensor([float(r.get("min_p", 0.0) or 0.0) for r in rows], **f64)
    edt_on = torch.tensor([r.get("edt") is not None for r in rows], device=dev)
    edt_q = torch.tensor([float(r["edt"]["q"]) if r.get("edt") else 1e9 for r in rows], **f64)
    edt_T = torch.tensor([float(r["edt"]["T"]) if r.get("edt") else 1.0 for r in rows], **f64)
    ad_on = torch.tensor([r.get("adapt") is not None for r in rows], device=dev)
    ad_T = torch.tensor([float(r["adapt"]["T"]) if r.get("adapt") else 1.0 for r in rows], **f64)
    win_on = torch.tensor([r.get("window") is not None for r in rows], device=dev)
    win_n = torch.tensor([int(r["window"]["n"]) if r.get("window") else 0 for r in rows], dtype=torch.long,
                         device=dev)
    win_T = torch.tensor([float(r["window"]["T"]) if r.get("window") else 1.0 for r in rows], **f64)
    win_k = torch.tensor([int(r["window"]["k"]) if r.get("window") else 0 for r in rows], dtype=torch.long,
                         device=dev)
    # openings
    C = max([len(r.get("openings") or []) for r in rows] + [1])
    Lo = max([len(o) for r in rows for o in (r.get("openings") or [])] + [1])
    O = torch.full((B, C, Lo), -2, dtype=torch.long, device=dev)
    O_len = torch.full((B, C), 10 ** 6, dtype=torch.long, device=dev)
    for i, r in enumerate(rows):
        for c, o in enumerate(r.get("openings") or []):
            O[i, c, :len(o)] = torch.tensor(o, dtype=torch.long, device=dev)
            O_len[i, c] = len(o)
    on_open = O_len < 10 ** 6
    ban_tab = None                      # amendment: tokens removed at the dosed steps (dose['ban'] / dose2['ban'])
    if any((r.get("dose") or {}).get("ban") or (r.get("dose2") or {}).get("ban") for r in rows):
        ban_tab = torch.zeros(B, V, dtype=torch.bool, device=dev)
        for i, r in enumerate(rows):
            ids = sorted(set((r.get("dose") or {}).get("ban") or []) | set((r.get("dose2") or {}).get("ban") or []))
            if ids:
                ban_tab[i, torch.tensor(ids, dtype=torch.long, device=dev)] = True
    dose_on = torch.tensor([r.get("dose") is not None for r in rows], device=dev)
    dose_T = torch.tensor([float(r["dose"]["T"]) if r.get("dose") else 1.0 for r in rows], **f64)
    dose_k = torch.tensor([int(r["dose"]["k"]) if r.get("dose") else 0 for r in rows], dtype=torch.long, device=dev)
    d2_tab = torch.zeros(B, V, dtype=torch.bool, device=dev) if any(r.get("dose2") for r in rows) else None
    d2_T = torch.ones(B, **f64)
    d2_k = torch.zeros(B, dtype=torch.long, device=dev)
    if d2_tab is not None:
        for i, r in enumerate(rows):
            if r.get("dose2"):
                d2_tab[i, torch.tensor(sorted(r["dose2"]["tokens"]), dtype=torch.long, device=dev)] = True
                d2_T[i] = float(r["dose2"]["T"])
                d2_k[i] = int(r["dose2"]["k"])
    # forced tokens: prefix (from index 0) and decision forcing (per node, from the decision index)
    Lf = max([len(r.get("prefix") or []) for r in rows] + [0])
    pref = torch.full((B, max(Lf, 1)), -1, dtype=torch.long, device=dev)
    pref_len = torch.zeros(B, dtype=torch.long, device=dev)
    for i, r in enumerate(rows):
        if r.get("prefix"):
            pref[i, :len(r["prefix"])] = torch.tensor(r["prefix"], dtype=torch.long, device=dev)
            pref_len[i] = len(r["prefix"])
    Lfd = max([len(v) for r in rows for v in (r.get("force_dec") or {}).values()] + [0])
    fdec = torch.full((B, C, max(Lfd, 1)), -1, dtype=torch.long, device=dev)
    fdec_len = torch.zeros(B, C, dtype=torch.long, device=dev)
    for i, r in enumerate(rows):
        for c, ids in (r.get("force_dec") or {}).items():
            fdec[i, int(c), :len(ids)] = torch.tensor(ids, dtype=torch.long, device=dev)
            fdec_len[i, int(c)] = len(ids)
    # fixed dose positions (placebos)
    Lp = max([len(r["fixed_pos"]["pos"]) for r in rows if r.get("fixed_pos")] + [1])
    fpos = torch.full((B, Lp), -5, dtype=torch.long, device=dev)
    fpos_T = torch.ones(B, **f64)
    fpos_k = torch.zeros(B, dtype=torch.long, device=dev)
    for i, r in enumerate(rows):
        if r.get("fixed_pos"):
            ps = r["fixed_pos"]["pos"]
            fpos[i, :len(ps)] = torch.tensor(ps, dtype=torch.long, device=dev)
            fpos_T[i] = float(r["fixed_pos"]["T"])
            fpos_k[i] = int(r["fixed_pos"]["k"])
    tabs = token_tables(tok, V, dev) if bool(ad_on.any() or win_on.any()) else None
    line_colon = torch.zeros(B, dtype=torch.bool, device=dev)
    pending = torch.zeros(B, dtype=torch.bool, device=dev)
    body_start = torch.full((B,), -1, dtype=torch.long, device=dev)
    # state
    i_code = torch.zeros(B, dtype=torch.long, device=dev)
    dec_step = torch.full((B,), -1, dtype=torch.long, device=dev)
    dec_node = torch.full((B,), -1, dtype=torch.long, device=dev)
    dec_tok = torch.full((B,), -1, dtype=torch.long, device=dev)
    dec_H = torch.zeros(B, **f64)
    top_ids = torch.full((B, TOP_SAVE), -1, dtype=torch.long, device=dev)
    top_z = torch.zeros(B, TOP_SAVE, **f64)
    ent = torch.zeros(B, ENTROPY_STEPS, dtype=torch.float32, device=dev)
    n_mod = torch.zeros(B, dtype=torch.long, device=dev)            # steps whose transform differed from T = 1
    mod_steps: list[list[int]] = [[] for _ in range(B)]
    hid = torch.zeros(B, model.config.hidden_size, dtype=torch.float32, device=dev) if capture_hidden else None
    hid_n = torch.zeros(B, dtype=torch.long, device=dev)
    if flavor == "qwen":
        stop_ids = torch.tensor([QWEN_IM_END, QWEN_EOT], device=dev)
        feed_end = QWEN_IM_END
    else:
        stop_ids = torch.tensor([GEMMA_EOS, GEMMA_EOT], device=dev)
        feed_end = GEMMA_EOT
    end_t = torch.full((B,), feed_end, dtype=torch.long, device=dev)
    logits = torch.stack([r["pre"]["r_logits"] for r in rows], 0).double()
    toks = torch.full((B, max_steps), -1, dtype=torch.long, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    decided = torch.zeros(B, dtype=torch.bool, device=dev)
    maxnew_t = torch.tensor(max_new, dtype=torch.long, device=dev)
    fence_rows = [bool(r.get("fence", True)) for r in rows]
    ar = torch.arange(B, device=dev)
    host_toks: list[list[int]] = [[] for _ in range(B)]
    last_sync = 0
    step = 0
    nv = len(tok)
    while True:
        s_t = torch.full((B,), step, dtype=torch.long, device=dev)
        lsm = torch.log_softmax(logits, dim=-1)
        H1 = -(lsm.exp() * lsm).nan_to_num().sum(-1)                      # T = 1 entropy (nats)
        if step < ENTROPY_STEPS:
            ent[:, step] = H1.float()
        T_e, k_e, p_e, mp_e = T_g.clone(), k_g.clone(), p_g.clone(), mp_g.clone()
        hi = edt_on & (H1 > edt_q)
        T_e = torch.where(hi, edt_T, T_e)
        T_e = torch.where(ad_on & pending, ad_T, T_e)
        in_win = win_on & (body_start >= 0) & (s_t >= body_start) & (s_t < body_start + win_n)
        T_e = torch.where(in_win, win_T, T_e)
        k_e = torch.where(in_win, win_k, k_e)
        # decision flag at this step: on opening c and step == |O_c|
        at_dec_c = on_open & (O_len == step)
        at_dec = at_dec_c.any(-1) & (dec_step < 0)
        node_now = torch.where(at_dec, at_dec_c.float().argmax(-1), dec_node)
        dosed = at_dec & dose_on
        T_e = torch.where(dosed, dose_T, T_e)
        k_e = torch.where(dosed, dose_k, k_e)
        sec = torch.zeros(B, dtype=torch.bool, device=dev)
        if d2_tab is not None:
            sec = (dec_step >= 0) & (s_t == dec_step + 1) & d2_tab[ar, dec_tok.clamp(min=0)]
            T_e = torch.where(sec, d2_T, T_e)
            k_e = torch.where(sec, d2_k, k_e)
        fx = (fpos == step).any(-1)
        T_e = torch.where(fx, fpos_T, T_e)
        k_e = torch.where(fx, fpos_k, k_e)
        probs = _probs(logits, T_e, k_e, p_e, mp_e, flavor)
        if ban_tab is not None:
            at_dose = dosed | sec
            keep_any = (probs * (~ban_tab).double()).sum(-1) > 0
            probs = torch.where((at_dose & keep_any)[:, None] & ban_tab, torch.zeros_like(probs), probs)
        u = U[ar, i_code.clamp(max=max_steps - 1)]
        nxt = inverse_cdf(probs, u)
        # forcing
        fp = s_t < pref_len
        nxt = torch.where(fp, pref[ar, s_t.clamp(max=pref.shape[1] - 1)], nxt)
        if Lfd > 0:
            # decision forcing: from the decision index of node c for fdec_len[c] tokens
            ds = torch.where(at_dec, s_t, dec_step)
            off = s_t - ds
            nd = node_now.clamp(min=0)
            flen = fdec_len[ar, nd]
            fz = (ds >= 0) & (off >= 0) & (off < flen) & (node_now >= 0)
            ftok = fdec[ar, nd, off.clamp(min=0, max=fdec.shape[2] - 1)]
            nxt = torch.where(fz & (ftok >= 0), ftok, nxt)
        modified = (T_e != 1.0) | (k_e > 0) | (p_e < 1.0) | (mp_e > 0) | fp
        live = ~done
        n_mod += (modified & live).long()
        if step < 160:
            mm = (modified & live).nonzero().flatten().tolist()
            for b_ in mm:
                if len(mod_steps[b_]) < 40:
                    mod_steps[b_].append(step)
        # decision bookkeeping (T = 1 logits at the decision)
        newdec = at_dec & live
        if bool(newdec.any()):
            tv, ti = logits.topk(TOP_SAVE, dim=-1)
            top_ids = torch.where(newdec[:, None], ti, top_ids)
            top_z = torch.where(newdec[:, None], tv, top_z)
            dec_H = torch.where(newdec, H1, dec_H)
            dec_step = torch.where(newdec, s_t, dec_step)
            dec_node = torch.where(newdec, node_now, dec_node)
            dec_tok = torch.where(newdec, nxt, dec_tok)
        # opening tracking (after the token is known)
        inside = step < O_len
        match = O[:, :, min(step, Lo - 1)] == nxt[:, None]
        on_open = on_open & (~inside | match)
        i_code += live.long()
        toks[:, step] = torch.where(live, nxt, toks[:, step])
        # line state machine (AdapT / window)
        if tabs is not None:
            t_ = nxt.clamp(min=0, max=V - 1)
            nl, cb, nsb = tabs["nl"][t_], tabs["colon_b"][t_], tabs["ns_b"][t_]
            ca, nsa, ns = tabs["colon_a"][t_], tabs["ns_a"][t_], tabs["ns"][t_]
            end_colon = torch.where(nsb, cb, line_colon)
            pend_new = torch.where(nl, (pending & ~nsb) | end_colon, pending & ~ns)
            pend_new = torch.where(nl & nsa, torch.zeros_like(pend_new), pend_new)
            line_new = torch.where(nl, ca & nsa, torch.where(ns, cb, line_colon))
            first_block = (body_start < 0) & nl & end_colon & live
            body_start = torch.where(first_block, s_t + 1, body_start)
            pending = torch.where(live, pend_new, pending)
            line_colon = torch.where(live, line_new, line_colon)
        is_end = torch.isin(nxt, stop_ids)
        ended |= live & is_end
        done |= is_end | (live & (i_code >= maxnew_t))
        if step + 1 >= max_steps:
            break
        if (step + 1) % check_every == 0:
            chunk = toks[:, last_sync:step + 1].cpu().numpy()
            for r_ in range(B):
                host_toks[r_].extend(int(t) for t in chunk[r_] if t >= 0)
            last_sync = step + 1
            dn = done.cpu().numpy()
            newly_f, newly_d = [], []
            for r_ in range(B):
                if dn[r_]:
                    continue
                ids_r = [t for t in host_toks[r_] if t < nv]
                if fence_kind and fence_rows[r_] and len(ids_r) > len(rows[r_].get("prefix") or []):
                    tail = tok.decode(ids_r[-24:])
                    if "`" in tail:
                        txt = tok.decode(ids_r, skip_special_tokens=True)
                        ok = gemma_fence_closed(txt) if fence_kind == "gemma" else E4.fence_closed(txt, fence_kind)
                        if ok:
                            newly_f.append(r_)
                            continue
                if stop_fn is not None and stop_fn(r_, ids_r):
                    newly_d.append(r_)
            if newly_f:
                idx = torch.tensor(newly_f, device=dev)
                fenced[idx] = True
                done[idx] = True
            if newly_d:
                idx = torch.tensor(newly_d, device=dev)
                decided[idx] = True
                done[idx] = True
            if bool(done.all().item()):
                break
        feed = torch.where(done, end_t, nxt)[:, None]
        pos = (Pvec + step)[:, None]
        if padded:
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                            attention_mask=am_full[:, :Pmax + step + 1], use_cache=True).last_hidden_state
        else:
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        hl = h[:, -1]
        if hid is not None:
            inwin = (dec_step >= 0) & (s_t >= dec_step) & (s_t < dec_step + HID_N) & ~done
            if bool(inwin.any()):
                hid += torch.where(inwin[:, None], hl.float(), torch.zeros_like(hid))
                hid_n += inwin.long()
        logits = lm_logits(model, hl).double()
        step += 1
    del cache
    toks_c = toks.cpu().numpy()
    ended_c, fenced_c, dec_c = ended.cpu().numpy(), fenced.cpu().numpy(), decided.cpu().numpy()
    ds_c, dn_c, dt_c = dec_step.cpu().numpy(), dec_node.cpu().numpy(), dec_tok.cpu().numpy()
    dH_c = dec_H.cpu().numpy()
    ti_c, tz_c = top_ids.cpu().numpy(), top_z.cpu().numpy()
    ent_c = ent.cpu().numpy()
    nmod_c = n_mod.cpu().numpy()
    bs_c = body_start.cpu().numpy()
    hid_c = (hid / hid_n.clamp(min=1)[:, None].float()).cpu().numpy() if hid is not None else None
    hidn_c = hid_n.cpu().numpy()
    out = []
    for r_ in range(B):
        row = toks_c[r_]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r_] else ("fence" if fenced_c[r_] else ("decided" if dec_c[r_] else "length"))
        nent = min(n, ENTROPY_STEPS)
        rec = {"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n, "steps": step + 1,
               "engine_path": "leftpad" if padded else "shared", "decision_pos": int(ds_c[r_]),
               "decision_node": int(dn_c[r_]), "decision_token": int(dt_c[r_]) if ds_c[r_] >= 0 else None,
               "reached_decision": bool(ds_c[r_] >= 0), "decision_H1": float(dH_c[r_]) if ds_c[r_] >= 0 else None,
               "dec_top_ids": ti_c[r_].tolist() if ds_c[r_] >= 0 else None,
               "dec_top_z": [float(x) for x in tz_c[r_]] if ds_c[r_] >= 0 else None,
               "entropy": [round(float(x), 5) for x in ent_c[r_, :nent]], "n_modified_steps": int(nmod_c[r_]),
               "modified_steps": mod_steps[r_], "body_start": int(bs_c[r_]),
               "hid_mean": hid_c[r_].astype(np.float16) if (hid_c is not None and hidn_c[r_] > 0) else None}
        out.append(rec)
    return out


def replay_pick(top_ids: list[int], top_z: list[float], u: float, T: float, k: int) -> int:
    """Independent float64 replay of one dosed step from the captured T = 1 top-64 logits: softmax(z / T) over the
    top-k, inverse CDF in TOKEN-ID order (the engine's order), searchsorted(left)."""
    ids = np.asarray(top_ids[:k], dtype=np.int64)
    z = np.asarray(top_z[:k], dtype=np.float64)
    order = np.argsort(ids)
    ids, z = ids[order], z[order]
    x = z / float(T)
    x = x - x.max()
    p = np.exp(x)
    cdf = np.cumsum(p)
    cdf = cdf / cdf[-1]
    j = int(np.searchsorted(cdf, u, side="left"))
    return int(ids[min(j, len(ids) - 1)])
