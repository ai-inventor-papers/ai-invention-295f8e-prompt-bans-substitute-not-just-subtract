#!/usr/bin/env python3
"""Generation (S9): CRN cells scored by hidden tests.

A row spec: {sample_id, ids, edits (dict block -> fn(h) or None), ukey, prefix_ids (prefilled opening tokens that
belong to the program text), max_new, meta...}. Rows are grouped by prompt length and run in fixed-shape batches of
B rows (filler copies discarded), so every arm of a cell has identical GEMM shapes. Every arm of slot s uses the
stream u_stream(unit, site, 'iter8', s). Raw rows stream to data/samples_<UNIT>.jsonl (resumable by sample_id).

Edit families (prefill only; fp32 math, cast to bf16):
  dec_edit(L, fn)      the output of block L at the LAST prefill position d
  band_edit(...)       the outputs of every band block at the spec positions [p1, spec_end) (source states aligned)
  push_edit(...)       iteration 4's displacement-targeted push: h <- h + (alpha n[l,p] - (h - h_twin) . u) u
  clamp_edit(...)      h <- h - R R^T (h - h_twin) after the push at every band block (task clamp / random clamp)
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg8 import DATA, append_jsonl, read_jsonl, u_stream, utc_now
from engine8 import LM, decode, prefill

_DONE: dict[str, set[str]] = {}


def done_ids(unit: str) -> set[str]:
    if unit not in _DONE:
        _DONE[unit] = {r["sample_id"] for r in read_jsonl(DATA / f"samples_{unit}.jsonl")}
    return _DONE[unit]


def dec_edit(L: int, fn: Callable[[torch.Tensor], torch.Tensor]) -> dict[int, Callable]:
    def f(h: torch.Tensor) -> torch.Tensor:
        h = h.clone()
        h[:, -1] = fn(h[:, -1].float()).to(h.dtype)
        return h
    return {L: f}


def interchange_fn(hs: torch.Tensor, R: torch.Tensor | None) -> Callable[[torch.Tensor], torch.Tensor]:
    """R None -> full-state exchange; else h + R R^T (hs - h)."""
    def fn(h: torch.Tensor) -> torch.Tensor:
        if R is None:
            return hs.to(h.device).expand_as(h).clone()
        Rd = R.to(h.device)
        return h + ((hs.to(h.device) - h) @ Rd) @ Rd.T
    return fn


def band_edit(band: list[int], p1: int, S: int, src: torch.Tensor, R: torch.Tensor | None) -> dict[int, Callable]:
    """src [n_band, S, D] source states at the band blocks and spec offsets."""
    def mk(j: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            hb = h[0, p1:p1 + S].float()
            ss = src[j].to(h.device).float()
            if R is None:
                new = ss
            else:
                Rd = R.to(h.device)
                new = hb + ((ss - hb) @ Rd) @ Rd.T
            h[0, p1:p1 + S] = new.to(h.dtype)
            return h
        return f
    return {l: mk(j) for j, l in enumerate(band)}


def push_clamp_edit(band: list[int], p1: int, S: int, u: torch.Tensor, alpha: float, n: torch.Tensor,
                    h_twin: torch.Tensor, clamp: torch.Tensor | None) -> dict[int, Callable]:
    """Iteration 4's displacement-targeted push on the twin (u unit [D], n [n_band, S], h_twin [n_band, S, D]),
    optionally followed by a clamp h <- h - R R^T (h - h_twin) at the same block (R = clamp [D, k])."""
    def mk(j: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            hs = h[0, p1:p1 + S].float()
            ht = h_twin[j].to(h.device).float()
            ud = u.to(h.device).float()
            comp = (hs - ht) @ ud
            coef = alpha * n[j].to(h.device).float() - comp
            new = hs + coef[:, None] * ud[None, :]
            if clamp is not None:
                Rd = clamp.to(h.device)
                new = new - ((new - ht) @ Rd) @ Rd.T
            h[0, p1:p1 + S] = new.to(h.dtype)
            return h
        return f
    return {l: mk(j) for j, l in enumerate(band)}


def run_rows(lm: LM, unit: str, rows: list[dict[str, Any]], fence: str, B: int, tag: str,
             deadline: float = float("inf")) -> int:
    """Run row specs (skip done). Each row: sample_id, ids, edits (or None), ukey, prefix_ids, max_new, meta."""
    done = done_ids(unit)
    todo = [r for r in rows if r["sample_id"] not in done]
    if not todo:
        return 0
    groups: dict[int, list[dict[str, Any]]] = {}
    for r in todo:
        groups.setdefault(len(r["ids"]), []).append(r)
    n = 0
    tok = lm.tok
    nv = len(tok)
    for P, gs in sorted(groups.items()):
        for i in range(0, len(gs), B):
            if time.time() > deadline:
                logger.warning(f"{tag}: deadline reached, {len(todo) - n} rows not run")
                return n
            chunk = gs[i:i + B]
            t0 = time.time()
            pres = [prefill(lm, r["ids"], edits=r.get("edits")) for r in chunk]
            us = [u_stream(*r["ukey"], n=1536) for r in chunk]
            while len(pres) < B:
                pres.append(pres[0])
                us.append(us[0])
            max_new = max(r["max_new"] for r in chunk)
            try:
                res = decode(lm, pres, us, max_new, fence)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                logger.error(f"OOM in {tag} batch (P={P}); retrying rows one by one")
                res = []
                for p, u in zip(pres[:len(chunk)], us[:len(chunk)]):
                    res += decode(lm, [p], [u], max_new, fence)
            out = []
            for r, o in zip(chunk, res):
                gen = [t for t in o["token_ids"] if t < nv]
                text = tok.decode(list(r.get("prefix_ids", [])) + gen, skip_special_tokens=True)
                row = {"sample_id": r["sample_id"], "unit": unit, "text": text, "n_new_tokens": o["n_tokens"],
                       "finish_reason": o["finish_reason"], "logprob_sum": o["logprob_sum"], "P": P, "batch_B": B,
                       "ukey": "|".join(str(x) for x in r["ukey"]), "utc": utc_now(), "tag": tag}
                row.update(r.get("meta", {}))
                out.append(row)
            append_jsonl(DATA / f"samples_{unit}.jsonl", out)
            done.update(o["sample_id"] for o in out)
            n += len(out)
            dt = time.time() - t0
            append_jsonl(DATA / "timing_gen.jsonl", [{"tag": tag, "unit": unit, "B": B, "P": P, "n": len(out),
                                                       "seconds": round(dt, 2), "steps": res[0]["steps"],
                                                       "utc": utc_now()}])
            logger.info(f"{tag}: +{len(out)} rows ({dt:.1f}s, {res[0]['steps']} steps); total {n}/{len(todo)}")
            del pres, res
    torch.cuda.empty_cache()
    return n
