#!/usr/bin/env python3
"""GPU engine of iteration 7: bf16 Qwen3-8B (exp30 engine6 loader), prefill with block-output edits (exp30 hooks
convention), exp27/exp30 CRN decoder (gpu6.decode6: float64 inverse-CDF sampler in vocabulary order, fence stop,
finished rows fed <|im_end|> so the batch shape is constant), and the edit families of this artifact:

  full   h_b[pos] <- h_s[pos]                                  (full-state exchange at a site)
  das    h_b[pos] <- h_b[pos] + lam * (h_s[pos] - h_b[pos]) @ B^T @ B   (B = k x 4096 orthonormal rows: a fitted DAS map
         R_k, a random rank-k subspace, DIM-1, PCA-16 or the projected map; lam = 1 except in the R sweep)
Edits act on block OUTPUTS at the listed blocks during the PREFILL only (decode steps are never hooked), in fp32,
cast to bf16. A 'band' site applies the same edit after every block of the band, each block with its own source
states. Batches hold rows of one prompt length, padded with discarded filler rows to the task's fixed batch size, so
GEMM shapes are identical in every arm of a task.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg import MODEL_ID, MODEL_REVISION, append_jsonl, read_jsonl, stable_seed, utc_now
from cfg6 import SLOT_MAP
from cfg7 import BATCH7, ENGINE7, MAX_NEW7, PRECISION7, SAMPLES7, results7
from engine_v4 import _kv_list, block_hooks, clear_act_cache, u_stream, vocab_len
from gpu6 import decode6

STATE: dict[str, Any] = {"gpu": None, "done": None, "deadline": float("inf")}
TIMING7 = results7("timing_batches.jsonl")


def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


def code_stream(task: str, slot: int) -> np.ndarray:
    w, k = SLOT_MAP[slot]
    return u_stream(task, w, k, n=1536)


def fence7(task: str) -> str:
    return "path" if task in ("T1", "T2") else "bench"


def done_ids() -> set[str]:
    if STATE["done"] is None:
        STATE["done"] = {r["sample_id"] for r in read_jsonl(SAMPLES7)}
    return STATE["done"]


# ------------------------------------------------------------------------------------------------ prefill / capture
@torch.no_grad()
def prefill7(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 prompt pass with block-output edits; KV stays on the GPU."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=dev_of(model))
    cache = DynamicCache()
    clear_act_cache()
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K, V) for K, V in _kv_list(cache)]
    del out
    clear_act_cache()
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


@torch.no_grad()
def capture_states(model: Any, rec: dict[str, Any], blocks: list[int], with_r: bool = True
                   ) -> dict[int, torch.Tensor]:
    """Block outputs (bf16, exact) at spec positions [p1, spec_end) (+ the read position R as the last row)."""
    idx = list(range(rec["p1"], rec["spec_end"])) + ([rec["P"] - 1] if with_r else [])
    it = torch.tensor(idx, device=dev_of(model))
    store: dict[int, torch.Tensor] = {}

    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            store[l] = h[0, it].clone()
        return g
    from transformers.cache_utils import DynamicCache
    inp = torch.tensor([rec["ids"]], device=dev_of(model))
    with block_hooks(model, None, {l: mk(l) for l in blocks}):
        model.model(input_ids=inp, past_key_values=DynamicCache(), use_cache=True)
    clear_act_cache()
    return store


def make_edit(pos: torch.Tensor, src: dict[int, torch.Tensor], kind: str, B: torch.Tensor | None = None,
              lam: float = 1.0, log: dict | None = None) -> dict[int, Callable]:
    """Edits at blocks src.keys(): kind 'full' (exchange) or 'proj' (DAS-style projected interchange with basis B
    [k, 4096] fp32 orthonormal rows; lam scales the projected difference). src[l]: [len(pos), 4096]."""
    def mk(l: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            hs = h[0, pos].float()
            s = src[l].float()
            if kind == "full":
                new = s
            elif kind == "proj":
                d = (s - hs) @ B.T  # [n, k]
                new = hs + lam * (d @ B)
            else:
                raise ValueError(kind)
            if log is not None:
                log.setdefault(l, []).append(float((new - hs).norm(dim=-1).mean()))
            h = h.clone()
            h[0, pos] = new.to(h.dtype)
            return h
        return f
    return {l: mk(l) for l in src}


# ------------------------------------------------------------------------------------------------ generation
def emit7(task: str, specs: list[dict[str, Any]], res: list[dict[str, Any]], tok: Any, tag: str, B: int
          ) -> list[dict[str, Any]]:
    nv = vocab_len(tok)
    rows = []
    for sp, r in zip(specs, res):
        if sp.get("filler"):
            continue
        s = sp["slot"]
        w, k = SLOT_MAP[s]
        text = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
        row = {"task": task, "arm": sp["arm"], "cell": sp["cell"], "stage": sp.get("stage"), "slot": s,
               "slot_index": s, "template": sp.get("template"), "sample_id": sp["sample_id"],
               "crn_key": f"{task}|{w}|{k}", "u_seed": stable_seed(task, w, k), "base_key": sp["base_key"],
               "source_key": sp.get("source_key"), "Y_source": sp.get("Y_source"), "site": sp.get("site"),
               "layer": sp.get("layer"), "rank_k": sp.get("rank_k"), "lambda": sp.get("lam"), "alpha": None,
               "fit": sp.get("fit"), "direction_seed": sp.get("direction_seed"), "noun": sp.get("noun"),
               "fam": sp.get("fam"), "prompt_kind": sp.get("kind"), "prompt_sha256": sp["prompt_sha256"],
               "P": sp["P"], "model": MODEL_ID, "model_revision": MODEL_REVISION, "precision": PRECISION7,
               "engine": ENGINE7, "gpu": STATE["gpu"], "max_new": sp["max_new"],
               "stop_rule": f"im_end|fence:{fence7(task)}", "block_id": tag, "batch_B": B, "temperature": 1.0,
               "top_k": None, "top_p": 1.0, "text": text, "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
               "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"],
               "realised_disp": sp.get("realised"), "thinking": False, "utc": utc_now()}
        rows.append(row)
    append_jsonl(SAMPLES7, rows)
    done_ids().update(r["sample_id"] for r in rows)
    return rows


def run_specs(model: Any, tok: Any, task: str, specs: list[dict[str, Any]], tag: str) -> int:
    """Run row specs (skip done sample_ids). Each spec: sample_id, arm, cell, slot, base_key, kind, prompt_sha256,
    P, max_new and either 'pre' (shared prefill object) or 'make' (callable -> (pre, realised)). Rows are grouped by
    prompt length P and run in fixed batches of BATCH7[task] (filler rows discarded)."""
    B = BATCH7[task]
    todo = [s for s in specs if s["sample_id"] not in done_ids()]
    if not todo:
        return 0
    groups: dict[int, list[dict[str, Any]]] = {}
    for s in todo:
        groups.setdefault(s["P"], []).append(s)
    n = 0
    for P, gs in sorted(groups.items()):
        i = 0
        while i < len(gs):
            if time.time() > STATE["deadline"]:
                logger.warning(f"deadline: {len(gs) - i} rows of {tag} not run")
                return n
            chunk = [dict(s) for s in gs[i:i + B]]
            i += B
            t0 = time.time()
            for sp in chunk:
                if "pre" not in sp:
                    sp["pre"], sp["realised"] = sp["make"]()
            while len(chunk) < B:
                f = dict(chunk[0])
                f["filler"] = True
                chunk.append(f)
            rows = [{"pre": sp["pre"], "u": code_stream(task, sp["slot"]), "T": 1.0, "T_early": None, "n_early": 0,
                     "max_new": sp["max_new"], "fence": True} for sp in chunk]
            try:
                res = decode6(model, rows, tok, fence7(task))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                logger.error(f"OOM in {tag} (P={P}); batch skipped")
                continue
            out = emit7(task, chunk, res, tok, tag, B)
            n += len(out)
            dt = time.time() - t0
            append_jsonl(TIMING7, [{"tag": tag, "task": task, "B": B, "P": P, "seconds": round(dt, 2),
                                    "steps": res[0]["steps"], "n_real": len(out),
                                    "n_length": sum(r["finish_reason"] == "length" for r in res), "utc": utc_now()}])
            for sp in chunk:
                sp.pop("pre", None)
            del rows, res
    torch.cuda.empty_cache()
    return n


def spec_row(task: str, arm: str, cell: str, slot: int, base: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return {"sample_id": f"{task}|{arm}|{slot}", "arm": arm, "cell": cell, "slot": slot, "base_key": base["key"],
            "kind": base["kind"], "prompt_sha256": base["prompt_sha256"], "P": base["P"], "max_new": MAX_NEW7[task],
            "template": base.get("w"), "noun": base.get("noun"), "fam": base.get("fam"), **kw}


def load7():
    from engine6 import load_model_bf16

    tok, model, info = load_model_bf16(vram_fraction=0.97, cpu_embed=False)
    STATE["gpu"] = info["gpu"]
    return tok, model, info
