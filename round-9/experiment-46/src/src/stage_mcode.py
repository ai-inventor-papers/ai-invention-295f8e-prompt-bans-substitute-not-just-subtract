#!/usr/bin/env python3
"""Stage 5 M-code states: one teacher-forced pass per unique scrubbed program (PRIMARY, M32, M8, SURV, BASE, DISOBEY)
over context + code. Context = neutral twin frame (W1-W5 with neutral nouns) + blank line + SPEC as the user turn,
chat template with enable_thinking=False (empty think block), assistant content '```python\\n' + code + '\\n```'.
Readouts per block (computed on the GPU inside the hooks, float16 on the CPU):
  R1   mean over the code-span tokens (offset mapping; decoded span asserted equal to the code)
  R1g  R1 without tokens whose norm exceeds 10x the sequence median (massive-activation sensitivity; count logged)
  R2   the token after the closing parenthesis of the earliest popleft/pop/heappop/get()/get_nowait call (AST); else
       the first token of the neighbour-loop body in the recursive helper; else the first body statement of solve
  R3   the 16th code token (negative control)
The forward pass stops at the last code token (causal: exact)."""

from __future__ import annotations

import ast
import time
from typing import Any

import numpy as np
from loguru import logger

import prompts_tp
import states
from common import read_json, sha256_text, timing, utc_now, write_json
from tpg import DATA, MODELS, RESULTS, STATES_DIR

POP_NAMES = {"popleft", "pop", "heappop", "get", "get_nowait"}


def _line_starts(code: str) -> list[int]:
    starts, s = [0], 0
    for ln in code.splitlines(keepends=True):
        s += len(ln)
        starts.append(s)
    return starts


def r2_offset(code: str) -> tuple[int, str]:
    tree = ast.parse(code)
    ls = _line_starts(code)
    cands = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if name in POP_NAMES and not (name == "get" and (n.args or n.keywords)):
                cands.append((n.lineno, n.col_offset, ls[n.end_lineno - 1] + n.end_col_offset, name))
    if cands:
        c = min(cands)
        return c[2], f"after_{c[3]}_call"
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef):
            rec = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == f.name
                      for x in ast.walk(f))
            if rec:
                for x in ast.walk(f):
                    if isinstance(x, ast.For) and x.body:
                        b = x.body[0]
                        return ls[b.lineno - 1] + b.col_offset, "recursive_neighbour_loop_body"
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef) and f.name == "solve" and f.body:
            b = f.body[0]
            return ls[b.lineno - 1] + b.col_offset, "solve_first_statement"
    return 0, "code_start"


def build(tok: Any, code: str, ctx_prompt: str) -> dict[str, Any]:
    pre = prompts_tp.render_chat(tok, ctx_prompt, False) + "```python\n"
    text = pre + code + "\n```"
    cs, ce = len(pre), len(pre) + len(code)
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    om = enc["offset_mapping"]
    idx = [i for i, (s, e) in enumerate(om) if s < ce and e > cs and e > s]   # tokens overlapping the code span
    dec = tok.decode([enc["input_ids"][i] for i in idx])
    off, rule = r2_offset(code)
    tgt = cs + off
    r2 = next((i for i in idx if om[i][0] >= tgt), idx[-1])
    return {"input_ids": enc["input_ids"][:idx[-1] + 1], "idx": idx, "r2": r2, "r2_rule": rule,
            "r3": idx[min(15, len(idx) - 1)], "decoded_equal": "".join(code.split()) in "".join(dec.split()),
            "n_tokens": idx[-1] + 1}


def forward_readouts(model: Any, ids: list[int], idx: list[int], r2: int, r3: int, blocks: list[int]
                     ) -> tuple[np.ndarray, dict[str, Any]]:
    import torch

    dec = states._decoder(model)
    out = np.zeros((4, len(blocks), dec.config.hidden_size if hasattr(dec, "config") else 0), np.float32) \
        if hasattr(dec, "config") else None
    res: dict[int, Any] = {}
    excl: dict[int, int] = {}
    it = torch.tensor(idx, device="cuda")
    hooks = []
    for b in blocks:
        def hook(_m: Any, _i: Any, o: Any, b: int = b) -> None:
            h = (o[0] if isinstance(o, tuple) else o)[0].float()
            hc = h.index_select(0, it)
            r1 = hc.mean(0)
            nrm = hc.norm(dim=1)
            keep = nrm <= 10 * nrm.median()
            excl[b] = int((~keep).sum().item())
            r1g = hc[keep].mean(0) if keep.any() else r1
            res[b] = torch.stack([r1, r1g, h[r2], h[r3]]).cpu()
        hooks.append(dec.layers[b].register_forward_hook(hook))
    try:
        with torch.no_grad():
            x = torch.tensor([ids])
            emb = dec.embed_tokens(x.cpu())
            dev = dec.layers[0].input_layernorm.weight.device
            dt = dec.layers[0].input_layernorm.weight.dtype
            dec(inputs_embeds=emb.to(dev, dtype=dt), attention_mask=torch.ones_like(x).to(dev), use_cache=False)
    finally:
        for h in hooks:
            h.remove()
    arr = np.stack([res[b].numpy() for b in blocks], axis=1)       # [4, n_blocks, d]
    _ = out
    return arr, {"r1g_excluded_by_block": excl}


def extract_mcode(model: Any, tok: Any, model_tag: str) -> None:
    import torch

    from common import commit_time

    assert commit_time("COMMIT1b") is not None, "M-code states require COMMIT #1b"
    cfg = MODELS[model_tag]
    ms = read_json(DATA / "mcode_sets.json")
    ctx = read_json(DATA / "mcode_contexts.json")["variants"]
    progs: dict[str, dict[str, Any]] = {}
    for name, s in ms["sets"].items():
        for a, rows in s.items():
            for r in rows:
                progs.setdefault(r["scrubbed_sha256"], {**r, "sets": []})["sets"].append(name)
    for r in ms["placement"]:
        progs.setdefault(r["scrubbed_sha256"], {**r, "sets": []})["sets"].append(r["set"])
    keys = list(progs)
    logger.info(f"M-code {model_tag}: {len(keys)} unique programs")
    blocks = cfg["ext_blocks"]
    R = np.zeros((len(keys), 4, len(blocks), 5120 if model_tag == "32b" else 4096), np.float16)
    meta = []
    t0 = time.time()
    for i, k in enumerate(keys):
        p = progs[k]
        b = build(tok, p["scrubbed"], ctx[p["context_variant"]]["prompt"])
        assert b["decoded_equal"], f"code span decode mismatch for {p['uid']}"
        if b["n_tokens"] > 4000:
            logger.warning(f"long program {p['uid']}: {b['n_tokens']} tokens")
        arr, info = forward_readouts(model, b["input_ids"], b["idx"], b["r2"], b["r3"], blocks)
        R[i] = arr.astype(np.float16)
        meta.append({"key": k, "uid": p["uid"], "algorithm": p["algorithm"], "source": p["source"],
                     "sets": p["sets"], "context_variant": p["context_variant"], "n_tokens": b["n_tokens"],
                     "n_code_tokens": len(b["idx"]), "r2_rule": b["r2_rule"],
                     "r1g_excluded_max": max(info["r1g_excluded_by_block"].values())})
        if i in (9, 99) or i % 100 == 0:
            el = time.time() - t0
            logger.info(f"M-code {model_tag} {i + 1}/{len(keys)}: {el:.0f}s ({el / (i + 1):.2f}s/program), "
                        f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
    dt = time.time() - t0
    timing(f"mcode_{model_tag}", dt, len(keys))
    np.savez_compressed(STATES_DIR / f"mcode_{model_tag}.npz", R=R, blocks=np.array(blocks),
                        keys=np.array(keys), algorithm=np.array([m["algorithm"] for m in meta]),
                        readouts=np.array(["R1", "R1g", "R2", "R3"]))
    write_json(RESULTS / f"states_mcode_{model_tag}.json", {"programs": meta, "seconds": round(dt, 1),
                                                           "n": len(keys), "utc": utc_now(),
                                                           "r2_rules": {r: sum(1 for m in meta if m["r2_rule"] == r)
                                                                        for r in {m["r2_rule"] for m in meta}}})
    _ = sha256_text
