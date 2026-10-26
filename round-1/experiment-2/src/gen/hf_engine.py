#!/usr/bin/env python3
"""Batched HF-transformers sampling (the plan's fallback engine: vLLM 0.32 cannot start in this container
because Triton needs a C compiler and none is installed).

Same token ids as every other phase (TokensPrompt equivalent), left padding, bf16, sdpa, T=1.0, top_p=1.0,
top-k off, per-row stop at the closing code fence. Sampling noise is seeded per batch with torch.manual_seed.
"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
from common import MODEL_ID, sha256_text  # noqa: E402
from vllm_engine import CLOSE_FENCE_STOP, extract_code  # noqa: E402  (pure-python helpers only)

EOS_IDS = [151645, 151643]
PAD_ID = 151643


def load_model(logger, attn: str = "sdpa"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=torch.bfloat16, attn_implementation=attn,
                                                 device_map="cuda")
    model.eval()
    logger.info(f"HF model loaded in {time.time() - t0:.0f}s; GPU mem {torch.cuda.memory_allocated() / 1e9:.1f} GB")
    return model, tok


def gen_config(max_new_tokens: int):
    from transformers import GenerationConfig

    return GenerationConfig(do_sample=True, temperature=1.0, top_p=1.0, top_k=0, min_p=None,
                            max_new_tokens=max_new_tokens, eos_token_id=EOS_IDS, pad_token_id=PAD_ID,
                            repetition_penalty=None)


def left_pad(batch_ids: list[list[int]], device) -> tuple:
    import torch

    T = max(len(x) for x in batch_ids)
    ids = torch.full((len(batch_ids), T), PAD_ID, dtype=torch.long)
    att = torch.zeros((len(batch_ids), T), dtype=torch.long)
    for i, x in enumerate(batch_ids):
        ids[i, T - len(x):] = torch.tensor(x, dtype=torch.long)
        att[i, T - len(x):] = 1
    return ids.to(device), att.to(device)


def _generate_batch(model, tok, batch: list[dict], mnt: int, seed: int, stop: bool, logger):
    """One HF generate call; returns per-row (token list, finished flag) and the elapsed seconds."""
    import torch

    ids, att = left_pad([r["prompt_ids"] for r in batch], model.device)
    torch.manual_seed(seed)
    t0 = time.time()
    with torch.inference_mode():
        kw = {"stop_strings": [CLOSE_FENCE_STOP], "tokenizer": tok} if stop else {}
        gen = model.generate(input_ids=ids, attention_mask=att, generation_config=gen_config(mnt), **kw)
    dt = time.time() - t0
    new = gen[:, ids.shape[1]:].cpu()
    out = []
    for row in new:
        toks = row.tolist()
        n = len(toks)
        while n > 0 and toks[n - 1] == PAD_ID:
            n -= 1
        toks = toks[:n]
        ended_eos = bool(toks) and toks[-1] in EOS_IDS
        text = tok.decode(toks, skip_special_tokens=False)
        finished = ended_eos or (stop and CLOSE_FENCE_STOP in text) or n < mnt
        out.append((toks, finished))
    del gen, new, ids, att
    return out, dt


def hf_sample(model, tok, requests: list[dict], logger, batch_size: int = 32, seed_base: int = 0,
              stop: bool = True, chunk: int = 448) -> list[dict]:
    """Generate one sample per request. Requests are processed in the given order in fixed-size batches;
    batch b is seeded with torch.manual_seed(seed_base + b). Rows still running after `chunk` new tokens are
    continued (prompt + partial output) in later batches until they finish or reach their max_tokens; this keeps
    batches dense (no row waits ~700 steps for the slowest one)."""
    import torch

    state = []  # per request: accumulated tokens, done flag
    for r in requests:
        state.append({"toks": [], "done": False})
    pending = list(range(len(requests)))
    b = 0
    bs = batch_size
    rnd = 0
    while pending:
        nxt = []
        i = 0
        while i < len(pending):
            idx = pending[i:i + bs]
            batch = []
            for j in idx:
                r = requests[j]
                batch.append({"prompt_ids": r["prompt_ids"] + state[j]["toks"]})
            remaining = min(requests[j]["max_tokens"] - len(state[j]["toks"]) for j in idx)
            mnt = min(chunk, remaining) if chunk else remaining
            try:
                res, dt = _generate_batch(model, tok, batch, mnt, seed_base + b, stop and requests[idx[0]].get("stop", True), logger)
            except torch.cuda.OutOfMemoryError:
                gc.collect()
                torch.cuda.empty_cache()
                bs = max(1, bs // 2)
                logger.warning(f"OOM: batch size -> {bs}")
                continue
            ntok = 0
            for j, (toks, fin) in zip(idx, res):
                st = state[j]
                if st["toks"] and toks:
                    pass
                st["toks"] = st["toks"] + [t for t in toks if not (t in EOS_IDS)]
                ntok += len(toks)
                st.setdefault("seeds", []).append(seed_base + b)
                if fin or len(st["toks"]) >= requests[j]["max_tokens"]:
                    st["done"] = True
                    st["eos"] = fin
                else:
                    nxt.append(j)
            logger.info(f"HF round {rnd} batch {b}: {len(idx)} rows, max {mnt} steps, {ntok} tokens in {dt:.1f}s "
                        f"({ntok / max(dt, 1e-6):.0f} tok/s); {len(nxt)} rows continue")
            i += len(idx)
            b += 1
        pending = nxt
        rnd += 1
    out_rows = []
    for r, st in zip(requests, state):
        toks = st["toks"]
        text = tok.decode(toks, skip_special_tokens=False)
        finish = "stop"
        if stop and r.get("stop", True) and CLOSE_FENCE_STOP in text:
            text = text[: text.index(CLOSE_FENCE_STOP) + len(CLOSE_FENCE_STOP)]
        elif not st.get("eos") and len(toks) >= r["max_tokens"]:
            finish = "length"
        code = extract_code(text) if finish != "length" else None
        out_rows.append({k: v for k, v in r.items() if k not in ("prompt_ids", "stop")} | {
            "raw_text": text, "finish_reason": finish, "n_gen_tokens": len(toks), "batch_seeds": st.get("seeds", []),
            "code": code, "code_sha256": sha256_text(code) if code else None})
    return out_rows
