#!/usr/bin/env python3
"""Residual-stream states with HF transformers (Stage 7 G0/G1/G4).

G0: the model is built with a TRUNCATED config (num_hidden_layers = max needed block + 1). Block l's output depends
only on blocks 0..l, so the states are exact while layers above are never loaded (this is what makes 8B bf16 and
32B nf4 fit a 16 GB card). The embedding table stays on the CPU (rows indexed on the CPU, moved to the GPU: exact);
lm_head is never used. Block outputs are captured with forward hooks on model.model.layers[l]; on 2 prompts we
assert hidden_states[l+1] == hook output (max abs diff 0) for l below the last kept block.
G1: S-mean = mean over the tokens whose char offsets lie inside SPEC in the rendered chat text (offset mapping);
asserted: decoded span == SPEC up to boundary whitespace.
G4: per-program states at p* (first token of the earliest class-signature match for the program's adj_label in the
code; no match -> first token of the function body), p*-1 and g16 (16th code token); the forward pass stops at the
last needed position (causal: exact).
"""

from __future__ import annotations

import ast
import gc
import math
import re
import time
from typing import Any

import numpy as np
from loguru import logger

from common import DEPTH_RANGE, RESULTS, STATES, write_json

LEXICON: dict[str, list[str]] = {
    "bfs": [r"deque\(", r"popleft", r"pop\(0\)", r"Queue\("],
    "dfs": [r"stack", r"\.pop\(\)", r"def dfs"],
    "bibfs": [r"forward", r"backward", r"\bfront", r"\bback"],
    "astar": [r"heapq", r"heappush", r"g_score", r"f_score", r"heuristic", r"manhattan", r"threshold", r"bound"],
    "iddfs": [r"depth_limit", r"limit", r"max_depth"],
    "jps": [r"jump", r"prune", r"forced"],
}
for _k in ("gbfs", "dijkstra_unit", "idastar", "biastar"):
    LEXICON[_k] = LEXICON["astar"]


def block_range(n_layers: int) -> tuple[list[int], list[int]]:
    """(selection blocks at depth 0.30-0.70, extraction blocks incl. +-2 for robustness)."""
    lo = int(math.floor(DEPTH_RANGE[0] * n_layers))
    hi = int(math.ceil(DEPTH_RANGE[1] * n_layers))
    sel = list(range(lo, hi + 1))
    ext = list(range(max(0, lo - 2), min(n_layers - 1, hi + 2) + 1))
    return sel, ext


def load_truncated(repo: str, precision: str, n_keep: int, revision: str | None = None,
                   device: str = "cuda") -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    import transformers

    from common import REVISIONS

    revision = revision or REVISIONS.get(repo)
    transformers.logging.set_verbosity_error()      # the truncated config makes every upper layer an 'unused weight'
    cfg = AutoConfig.from_pretrained(repo, revision=revision)
    tcfg = cfg.get_text_config() if hasattr(cfg, "get_text_config") else cfg
    full_layers = tcfg.num_hidden_layers
    tcfg.num_hidden_layers = n_keep
    if getattr(tcfg, "layer_types", None):
        tcfg.layer_types = list(tcfg.layer_types)[:n_keep]
    q = None
    pre = getattr(cfg, "quantization_config", None)
    if pre is not None and precision in ("int8", "nf4"):
        # pre-quantised checkpoint (e.g. unsloth bnb-4bit): its own quantization_config is used; allow the CPU
        # placement of the (never quantised) embedding table and lm_head
        if isinstance(pre, dict):
            pre["llm_int8_enable_fp32_cpu_offload"] = True
        else:
            pre.llm_int8_enable_fp32_cpu_offload = True
    elif precision == "int8":
        q = BitsAndBytesConfig(load_in_8bit=True, llm_int8_enable_fp32_cpu_offload=True)
    elif precision == "nf4":
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                               bnb_4bit_use_double_quant=True, llm_int8_enable_fp32_cpu_offload=True)
    _skip_upper_layers(n_keep)
    dm = {"model.embed_tokens": "cpu", "model.layers": 0, "model.norm": 0, "model.rotary_emb": 0, "lm_head": "cpu"}
    if device == "cpu":
        dm = {"": "cpu"}
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(repo, revision=revision, config=cfg, dtype=torch.bfloat16,
                                                 device_map=dm, quantization_config=q, attn_implementation="sdpa",
                                                 low_cpu_mem_usage=True)
    model.eval()
    tok = AutoTokenizer.from_pretrained(repo, revision=revision)
    info = {"repo": repo, "revision": revision, "precision": precision, "n_layers_full": full_layers,
            "n_layers_loaded": n_keep, "load_seconds": round(time.time() - t0, 1),
            "gpu_mem_gb": round(torch.cuda.memory_allocated() / 1e9, 2) if torch.cuda.is_available() else 0.0,
            "quantization_config": (model.config.to_dict().get("quantization_config") if q is not None or
                                    "bnb" in repo else None)}
    logger.info(f"loaded {repo} [{precision}] {n_keep}/{full_layers} layers in {info['load_seconds']}s, "
                f"GPU {info['gpu_mem_gb']} GB")
    return model, tok, info


def _skip_upper_layers(n_keep: int) -> None:
    """Drop checkpoint tensors of blocks >= n_keep before they are loaded. Needed for pre-quantised bnb checkpoints,
    whose quantisation statistics are otherwise routed to modules that the truncated config never builds; exact,
    because those blocks are never run."""
    import transformers.modeling_utils as mu

    orig = getattr(mu, "_tp_orig_load_meta", None) or mu._load_state_dict_into_meta_model
    mu._tp_orig_load_meta = orig
    pat = re.compile(r"(?:^|\.)layers\.(\d+)\.")

    def wrapped(model: Any, state_dict: dict, *a: Any, **k: Any) -> Any:
        sd = {kk: v for kk, v in state_dict.items()
              if not ((m := pat.search(kk)) and int(m.group(1)) >= n_keep)}
        return orig(model, sd, *a, **k)

    mu._load_state_dict_into_meta_model = wrapped


def _decoder(model: Any) -> Any:
    return model.model if hasattr(model.model, "layers") else model.model.language_model


def forward_blocks(model: Any, input_ids: Any, attn: Any, blocks: list[int]) -> dict[int, Any]:
    """Run the truncated decoder; returns {block: [B, T, d] float32 CPU tensor} via forward hooks."""
    import torch

    dec = _decoder(model)
    cap: dict[int, Any] = {}
    hooks = []
    for b in blocks:
        def hook(_m: Any, _i: Any, out: Any, b: int = b) -> None:
            h = out[0] if isinstance(out, tuple) else out
            cap[b] = h.detach().float().cpu()
        hooks.append(dec.layers[b].register_forward_hook(hook))
    try:
        with torch.no_grad():
            emb = dec.embed_tokens(input_ids.cpu())                     # rows indexed on the CPU
            dev = dec.layers[0].input_layernorm.weight.device
            dt = dec.layers[0].input_layernorm.weight.dtype
            dec(inputs_embeds=emb.to(dev, dtype=dt), attention_mask=attn.to(dev), use_cache=False)
    finally:
        for h in hooks:
            h.remove()
    return cap


def hook_check(model: Any, tok: Any, texts: list[str]) -> dict[str, Any]:
    """T7: hidden_states[l+1] == hook output of block l (l below the last kept block)."""
    import torch

    dec = _decoder(model)
    n = len(dec.layers)
    blocks = [0, n // 2, n - 2]
    diffs = []
    for t in texts:
        enc = tok(t, return_tensors="pt", add_special_tokens=False)
        cap = forward_blocks(model, enc["input_ids"], enc["attention_mask"], blocks)
        with torch.no_grad():
            emb = dec.embed_tokens(enc["input_ids"].cpu())
            dev = dec.layers[0].input_layernorm.weight.device
            dt = dec.layers[0].input_layernorm.weight.dtype
            out = dec(inputs_embeds=emb.to(dev, dtype=dt), attention_mask=enc["attention_mask"].to(dev), use_cache=False,
                      output_hidden_states=True)
        for b in blocks:
            hs = out.hidden_states[b + 1].float().cpu()
            diffs.append(float((hs - cap[b]).abs().max()))
    return {"blocks": blocks, "max_abs_diff": max(diffs), "pass": max(diffs) == 0.0}


def spec_span(tok: Any, text: str, spec: str) -> tuple[list[int], dict[str, Any]]:
    start = text.find(spec)
    assert start >= 0, "SPEC not found in rendered chat text"
    end = start + len(spec)
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    idx = [i for i, (s, e) in enumerate(enc["offset_mapping"]) if s >= start and e <= end and e > s]
    dec = tok.decode([enc["input_ids"][i] for i in idx])
    ok = dec.strip() == spec.strip()
    return idx, {"n_tokens": len(enc["input_ids"]), "n_span": len(idx), "decoded_equals_spec": ok}


def smean_states(model: Any, tok: Any, texts: list[str], spec: str, blocks: list[int], batch: int = 4) -> np.ndarray:
    """[n_texts, n_blocks, d] float32 S-mean states."""
    import torch

    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        spans = [spec_span(tok, t, spec) for t in chunk]
        for _, info in spans:
            assert info["decoded_equals_spec"], f"span decode mismatch: {info}"
        enc = tok(chunk, return_tensors="pt", add_special_tokens=False, padding=True)
        if tok.padding_side != "right":
            raise RuntimeError("expected right padding")
        cap = forward_blocks(model, enc["input_ids"], enc["attention_mask"], blocks)
        for j, (idx, _) in enumerate(spans):
            out.append(np.stack([cap[b][j, idx].mean(0).numpy() for b in blocks]))
        del cap
        torch.cuda.empty_cache()
    return np.stack(out).astype(np.float32)


# ---------------------------------------------------------------------------------------------- M2 positions
def _recursive_call_offsets(code: str) -> list[int]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    lines = code.splitlines(keepends=True)
    starts = np.cumsum([0] + [len(x) for x in lines]).tolist()
    offs = []
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(f):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == f.name:
                    offs.append(starts[n.lineno - 1] + n.col_offset)
    return offs


def signature_offset(code: str, label: str) -> tuple[int, str]:
    """Char offset (within code) of the earliest class-signature match; fallback = first body statement of solve."""
    cands = []
    for pat in LEXICON.get(label, []):
        m = re.search(pat, code, re.IGNORECASE)
        if m:
            cands.append((m.start(), pat))
    if label == "dfs":
        cands += [(o, "recursive_self_call") for o in _recursive_call_offsets(code)]
    if cands:
        return min(cands)
    try:
        tree = ast.parse(code)
        lines = code.splitlines(keepends=True)
        starts = np.cumsum([0] + [len(x) for x in lines]).tolist()
        for f in ast.walk(tree):
            if isinstance(f, ast.FunctionDef) and f.name == "solve" and f.body:
                b = f.body[0]
                return starts[b.lineno - 1] + b.col_offset, "first_body_token"
    except (SyntaxError, ValueError):
        pass
    return 0, "code_start"


def m2_positions(tok: Any, full_text: str, code: str, label: str) -> dict[str, Any] | None:
    cs = full_text.rfind(code.rstrip())
    if cs < 0:
        return None
    off, why = signature_offset(code, label)
    enc = tok(full_text, add_special_tokens=False, return_offsets_mapping=True)
    om = enc["offset_mapping"]
    tgt = cs + off
    p = next((i for i, (s, e) in enumerate(om) if e > tgt), None)
    c0 = next((i for i, (s, e) in enumerate(om) if e > cs), None)
    if p is None or c0 is None:
        return None
    g16 = min(c0 + 15, len(om) - 1)
    return {"input_ids": enc["input_ids"], "p_star": p, "p_prev": max(p - 1, 0), "g16": g16, "code_start_tok": c0,
            "signature": why, "n_tokens": len(om)}


def m2_states(model: Any, tok: Any, items: list[dict[str, Any]], blocks: list[int],
              max_tokens: int = 12000) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """items: {uid, full_text, code, label}. Returns [n, 3 positions, n_blocks, d] float16 and per-item info."""
    import torch

    out, info = [], []
    for k, it in enumerate(items):
        pos = m2_positions(tok, it["full_text"], it["code"], it["label"])
        if pos is None:
            info.append({"uid": it["uid"], "ok": False})
            continue
        last = max(pos["p_star"], pos["g16"]) + 1
        ids = pos["input_ids"][:last]
        capped = False
        if len(ids) > max_tokens:
            capped = True
            info.append({"uid": it["uid"], "ok": False, "reason": f"sequence {len(ids)} > cap {max_tokens}"})
            continue
        ii = torch.tensor([ids])
        cap = forward_blocks(model, ii, torch.ones_like(ii), blocks)
        st = np.stack([np.stack([cap[b][0, q].numpy() for b in blocks])
                       for q in (pos["p_star"], pos["p_prev"], pos["g16"])])
        out.append(st.astype(np.float16))
        info.append({"uid": it["uid"], "ok": True, "p_star": pos["p_star"], "g16": pos["g16"],
                     "signature": pos["signature"], "n_forward_tokens": len(ids), "capped": capped})
        del cap
        if k % 20 == 0:
            torch.cuda.empty_cache()
            logger.info(f"M2 {k + 1}/{len(items)}: {len(ids)} tokens, sig={pos['signature']}")
    gc.collect()
    arr = np.stack(out) if out else np.zeros((0, 3, len(blocks), 1), np.float16)
    return arr, info


def save_npz(name: str, **arrays: Any) -> None:
    np.savez_compressed(STATES / f"{name}.npz", **arrays)


def record(name: str, obj: dict[str, Any]) -> None:
    write_json(RESULTS / f"states_{name}.json", obj)
