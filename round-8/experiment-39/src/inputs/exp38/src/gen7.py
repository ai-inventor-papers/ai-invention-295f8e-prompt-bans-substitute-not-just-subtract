#!/usr/bin/env python3
"""Generation runner and intervention hooks for iteration 7 (gemma-3-4b-it, bf16, exact inverse-CDF CRN).

Edits are module-level interventions applied during the PREFILL only (so an edit at the fork position persists in
the KV cache, and decode steps run the unedited weights):
  site 'resid'  : output of decoder block l (resid_post of layer l)          [B, S, 2560]
  site 'z'      : input of block l's o_proj, head h slice (the head's output) [B, S, 256]
  site 'mlp'    : output of block l's MLP (before post_feedforward_layernorm) [B, S, 2560]
  site 'mlp_in' : input of block l's MLP (after pre_feedforward_layernorm)    [B, S, 2560]
Each Edit carries absolute positions and fn(x_fp32 [r, S', d], rows) -> new values. A zero edit is bit-identical.
run_cell(): one prompt (+ an optional forced response prefix such as c*) in fixed-shape batches of B_CRN rows; each
row has its own CRN stream (offset by the forced prefix length, so stream index = response index), its own
temperature and top-k, and its own list of edits. logit_only=True applies the edits to the next-token logits only
(the KV cache keeps the unedited prefill), which separates "the fork token changed" from "the persisting edited state".
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

import engine as EG
from cfg import FORK_INDEX, HEAD_DIM, IT_ID, LOG_DIR, MAX_NEW, append_jsonl, b_crn, utc_now

TIMING = LOG_DIR / "timing_batches.jsonl"


class Edit:
    def __init__(self, site: str, layer: int, pos: list[int] | torch.Tensor,
                 fn: Callable[[torch.Tensor, torch.Tensor], torch.Tensor], head: int | None = None,
                 name: str = "", log: dict[str, Any] | None = None):
        assert site in ("resid", "z", "mlp", "mlp_in")
        self.site, self.layer, self.head, self.name = site, int(layer), head, name
        self.pos = torch.as_tensor(pos, dtype=torch.long, device="cuda")
        self.fn = fn
        self.log = dict(log or {})


def _module(model: Any, site: str, layer: int) -> tuple[Any, str]:
    blk = model.model.layers[layer]
    if site == "resid":
        return blk, "out"
    if site == "z":
        return blk.self_attn.o_proj, "pre"
    if site == "mlp":
        return blk.mlp, "out"
    return blk.mlp, "pre"


def _apply(x: torch.Tensor, items: list[tuple[Edit, torch.Tensor]]) -> torch.Tensor:
    # positions are indices into the current call's sequence; an edit whose positions do not fit (a decode step of
    # length 1 after a prefill edit at p_f) leaves the tensor untouched, so prefill edits never touch decode steps
    if all(int(e.pos.max()) >= x.shape[1] for e, _ in items):
        return x
    x = x.clone()
    for e, rows in items:
        if int(e.pos.max()) >= x.shape[1]:
            continue
        sl = slice(e.head * HEAD_DIM, (e.head + 1) * HEAD_DIM) if e.site == "z" else slice(None)
        r_ix, p_ix = rows[:, None], e.pos[None, :]
        cur = x[r_ix, p_ix][..., sl].float()
        new = e.fn(cur, rows)
        if e.site == "z":
            x[r_ix, p_ix, sl] = new.to(x.dtype)
        else:
            x[r_ix, p_ix] = new.to(x.dtype)
    return x


@contextlib.contextmanager
def edit_hooks(model: Any, row_edits: list[tuple[Edit, torch.Tensor]],
               capture: dict[tuple[str, int], Callable[[torch.Tensor], None]] | None = None) -> Iterator[None]:
    """row_edits: [(Edit, rows LongTensor)]; capture: {(site, layer): g(x)} called with the (edited) tensor."""
    groups: dict[tuple[str, int], list[tuple[Edit, torch.Tensor]]] = {}
    for e, rows in row_edits:
        groups.setdefault((e.site, e.layer), []).append((e, rows))
    capture = capture or {}
    keys = sorted(set(groups) | set(capture))
    hs = []
    for key in keys:
        site, layer = key
        mod, kind = _module(model, site, layer)
        items = groups.get(key, [])
        cap = capture.get(key)
        if kind == "out":
            def hook(m, inp, out, items=items, cap=cap):
                x = out[0] if isinstance(out, tuple) else out
                if items:
                    x = _apply(x, items)
                if cap is not None:
                    cap(x)
                if items:
                    return (x,) + tuple(out[1:]) if isinstance(out, tuple) else x
                return None
            hs.append(mod.register_forward_hook(hook))
        else:
            def prehook(m, args, items=items, cap=cap):
                x = args[0]
                if items:
                    x = _apply(x, items)
                if cap is not None:
                    cap(x)
                if items:
                    return (x,) + tuple(args[1:])
                return None
            hs.append(mod.register_forward_pre_hook(prehook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


class Runner:
    def __init__(self, vram_fraction: float = 0.95, B: int | None = None):
        self.tok, self.model, self.info = EG.load_model("it", vram_fraction)
        self.B = int(B or b_crn())

    # -------------------------------------------------------------------------------------------- forward helpers
    @torch.no_grad()
    def prefill(self, ids: list[int], B: int, row_edits: list[tuple[Edit, torch.Tensor]] | None = None,
                capture: dict | None = None) -> dict[str, Any]:
        from transformers.cache_utils import DynamicCache

        inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
        cache = DynamicCache()
        with edit_hooks(self.model, row_edits or [], capture):
            out = self.model.model(input_ids=inp, past_key_values=cache, use_cache=True)
        logits = EG.lm_logits(self.model, out.last_hidden_state[:, -1])
        kv = [(K, V) for K, V in EG._kv_from_cache(cache)]
        del out, cache
        return {"kv": kv, "logits": logits, "P": len(ids), "mask": None, "lens": None}

    @torch.no_grad()
    def logits_rows(self, ids: list[int], B: int, row_edits: list[tuple[Edit, torch.Tensor]] | None = None,
                    positions: list[int] | None = None) -> torch.Tensor:
        """Batch of B copies of `ids` with per-row edits; fp32 logits at `positions` (default: last) [B, n, V]."""
        inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
        pos = positions if positions is not None else [len(ids) - 1]
        with edit_hooks(self.model, row_edits or []):
            out = self.model.model(input_ids=inp, use_cache=False)
        lg = EG.lm_logits(self.model, out.last_hidden_state[:, pos])
        del out
        return lg

    @torch.no_grad()
    def states(self, ids: list[int], layers: list[int], positions: list[int] | None = None,
               want_logits_at: list[int] | None = None) -> dict[str, Any]:
        cap: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(x):
                cap[l] = (x[0] if positions is None else x[0, positions]).float().cpu()
            return g
        inp = torch.tensor([ids], device="cuda")
        with edit_hooks(self.model, [], {("resid", l): mk(l) for l in layers}):
            out = self.model.model(input_ids=inp, use_cache=False)
        res: dict[str, Any] = {"h": cap}
        if want_logits_at is not None:
            res["logits"] = EG.lm_logits(self.model, out.last_hidden_state[0, want_logits_at]).cpu()
        del out
        return res

    # -------------------------------------------------------------------------------------------- coupled cells
    def run_cell(self, ids: list[int], prefix_ids: list[int], rows: list[dict[str, Any]], raw_path: Path,
                 tag: str, max_new: int = MAX_NEW, logit_only: bool = False) -> list[dict[str, Any]]:
        """ids = prompt ids + prefix_ids (prefilled). rows: {row_id, ukey, temperature, top_k, edits, meta}."""
        B = self.B
        L = len(prefix_ids)
        pref_text = self.tok.decode(prefix_ids) if L else ""
        out_all = []
        for b0 in range(0, len(rows), B):
            chunk = rows[b0:b0 + B]
            n_real = len(chunk)
            pad = B - n_real
            t0 = time.time()
            groups: dict[int, tuple[Edit, list[int]]] = {}
            for i, r in enumerate(chunk):
                for e in (r.get("edits") or []):
                    groups.setdefault(id(e), (e, []))[1].append(i)
            row_edits = [(e, torch.tensor(ix, device="cuda", dtype=torch.long)) for e, ix in groups.values()]
            if logit_only and row_edits:
                pre = self.prefill(ids, B, [])
                pe = self.prefill(ids, B, row_edits)
                pre["logits"] = pe["logits"]
                del pe
            else:
                pre = self.prefill(ids, B, row_edits)
            Us = [EG.u_stream(*r["ukey"], n=max_new + L)[L:] for r in chunk] + [np.full(max_new, 0.5)] * pad
            temps = np.array([float(r.get("temperature", 1.0)) for r in chunk] + [1.0] * pad)
            topk = np.array([int(r.get("top_k") or 0) for r in chunk] + [0] * pad)
            active = np.array([True] * n_real + [False] * pad)
            res = EG.decode(self.model, self.tok, pre, np.stack(Us), temps, max_new,
                            text_prefix=[pref_text] * B if L else None, active=active, topk=topk)
            del pre
            out = []
            for r, g in zip(chunk, res[:n_real]):
                resp = [int(t) for t in prefix_ids] + g["token_ids"]
                out.append({"row_id": r["row_id"], "task": "T1", "model": IT_ID, "ukey": list(r["ukey"]),
                            "temperature": float(r.get("temperature", 1.0)), "top_k": int(r.get("top_k") or 0),
                            "prefix_len": L, "text": self.tok.decode(resp, skip_special_tokens=True),
                            "token_ids": resp, "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"],
                            "fork_token": resp[FORK_INDEX] if len(resp) > FORK_INDEX else None,
                            "B": B, "max_new": max_new, "logit_only": bool(logit_only),
                            "batch_id": f"{tag}:{b0 // B}", "utc": utc_now(),
                            "edit_log": [dict(e.log, name=e.name) for e in (r.get("edits") or [])],
                            **(r.get("meta") or {})})
            append_jsonl(raw_path, out)
            out_all += out
            dt = time.time() - t0
            append_jsonl(TIMING, [{"batch_id": f"{tag}:{b0 // B}", "n_real": n_real, "B": B, "seconds": dt,
                                   "steps": res[0]["steps"], "max_new": max_new, "utc": utc_now()}])
            fr: dict[str, int] = {}
            for g in res[:n_real]:
                fr[g["finish_reason"]] = fr.get(g["finish_reason"], 0) + 1
            logger.info(f"{tag}:{b0 // B}: {n_real}/{B} rows {dt:.1f}s, {res[0]['steps']} steps, {fr}")
        return out_all

    # -------------------------------------------------------------------------------------------- multi-prompt
    def run_multi(self, items: list[dict[str, Any]], max_new: int, raw_path: Path | None, tag: str,
                  B: int | None = None, stop_fn: Callable[[str], bool] | None = None) -> list[dict[str, Any]]:
        """Iteration 6's fork-resampling path: distinct prompts right-aligned into one batch (2-D mask)."""
        B = int(B or self.B)
        out_all = []
        for b0 in range(0, len(items), B):
            chunk = items[b0:b0 + B]
            n_real = len(chunk)
            pad = B - n_real
            t0 = time.time()
            id_lists = [c["ids"] for c in chunk] + [chunk[0]["ids"]] * pad
            pre = EG.prefill_multi(self.model, id_lists)
            Us = [EG.u_stream(*c["ukey"], n=max_new + c["n_prefix"])[c["n_prefix"]:] for c in chunk]
            Us += [np.full(max_new, 0.5)] * pad
            active = np.array([True] * n_real + [False] * pad)
            prefs = [self.tok.decode(c["prefix_ids"]) for c in chunk] + [""] * pad
            res = EG.decode(self.model, self.tok, pre, np.stack(Us), np.ones(B), max_new, text_prefix=prefs,
                            stop_fn=stop_fn, active=active)
            del pre
            out = []
            for c, g in zip(chunk, res[:n_real]):
                resp = list(c["prefix_ids"]) + g["token_ids"]
                out.append({"row_id": c["row_id"], "task": "T1", "model": IT_ID, "ukey": list(c["ukey"]),
                            "n_prefix": c["n_prefix"], "token_ids": resp, "temperature": 1.0, "top_k": 0,
                            "text": self.tok.decode(resp, skip_special_tokens=True),
                            "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"],
                            "fork_token": resp[FORK_INDEX] if len(resp) > FORK_INDEX else None, "B": B,
                            "max_new": max_new, "batch_id": f"{tag}:{b0 // B}", "utc": utc_now(),
                            **(c.get("meta") or {})})
            if raw_path is not None:
                append_jsonl(raw_path, out)
            out_all += out
            dt = time.time() - t0
            append_jsonl(TIMING, [{"batch_id": f"{tag}:{b0 // B}", "n_real": n_real, "B": B, "seconds": dt,
                                   "steps": res[0]["steps"], "max_new": max_new, "utc": utc_now()}])
            logger.info(f"{tag}:{b0 // B}: {n_real}/{B} rows {dt:.1f}s, {res[0]['steps']} steps")
        return out_all

    def free(self) -> None:
        EG.free_model(self.model)
