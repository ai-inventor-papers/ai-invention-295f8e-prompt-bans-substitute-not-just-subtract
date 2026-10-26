#!/usr/bin/env python3
"""Generation runner for claim S (gemma-3-4b-it, bf16, exact inverse-CDF CRN).

run_crn():   one prompt (optionally + a forced response prefix c*) repeated in fixed-shape batches of B_CRN rows,
             each row with its own CRN uniform stream and its own prefill-only additive edits {layer: [S', D]} at
             absolute positions. Short batches are padded with inactive rows so every batch has shape B_CRN.
run_multi(): distinct prompts / prefixes (fork continuations, sampling validation) right-aligned into one batch.
A row's uniforms are u_stream(*ukey) offset by the forced prefix length, so a forced-prefix row whose prefix equals
the free sample's first tokens continues exactly as the free sample did (same slot, same stream position).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

import engine as EG
import prompts as PG
from cfg import (B_CRN, CAPTURE_BLOCKS, D_MODEL, DATA_DIR, IT_ID, LOG_DIR, append_jsonl, utc_now)
from push import block_hooks

TIMING = LOG_DIR / "timing_batches.jsonl"


def add_edits(row_edits: list[dict[int, tuple[torch.Tensor, torch.Tensor]] | None], B: int
              ) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """row_edits[r] = {layer: (pos LongTensor [S'], dh fp32 [S', D])} -> block-output hooks adding dh to row r."""
    by_layer: dict[int, list[tuple[int, torch.Tensor, torch.Tensor]]] = {}
    for r, e in enumerate(row_edits):
        if not e:
            continue
        for l, (pos, dh) in e.items():
            by_layer.setdefault(l, []).append((r, pos, dh))
    edits: dict[int, Callable[[torch.Tensor], torch.Tensor]] = {}
    for l, items in by_layer.items():
        def f(h: torch.Tensor, items=items) -> torch.Tensor:
            if h.shape[1] == 1:          # decode step (prefill-only edits): untouched
                return h
            h = h.clone()
            for r, pos, dh in items:
                h[r, pos] = (h[r, pos].float() + dh).to(h.dtype)
            return h
        edits[l] = f
    return edits


class Runner:
    def __init__(self, vram_fraction: float = 0.95):
        self.tok, self.model, self.info = EG.load_model("it", vram_fraction)

    # -------------------------------------------------------------------------------------------- coupled
    def run_crn(self, p: dict[str, Any], rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path,
                batch_tag: str, prefix_ids: list[int] | None = None, capture_ref: dict[str, Any] | None = None
                ) -> list[dict[str, Any]]:
        """rows: {row_id, task, arm, template, slot, ukey, edits (optional {l: (pos, dh)}), meta (dict)}."""
        prefix_ids = list(prefix_ids or [])
        q = PG.p_with_prefix(p, prefix_ids, "cstar") if prefix_ids else p
        if not prefix_ids:
            PG.register(p)
        pref_text = self.tok.decode(prefix_ids) if prefix_ids else ""
        out_all = []
        for b0 in range(0, len(rows), B_CRN):
            chunk = rows[b0:b0 + B_CRN]
            n_real = len(chunk)
            t0 = time.time()
            pad = B_CRN - n_real
            if any(r.get("specs") for r in chunk):
                from clamp import live_edits
                edits = live_edits([r.get("specs") for r in chunk] + [None] * pad)
            else:
                edits = add_edits([r.get("edits") for r in chunk] + [None] * pad, B_CRN)
            pre = EG.prefill_single(self.model, q["ids"], B_CRN, edits=edits, capture_ref=capture_ref)
            dS = pre.pop("disp_S", None)
            dR = pre.pop("disp_R", None)
            L = len(prefix_ids)
            Us = [EG.u_stream(*r["ukey"], n=max_new + L)[L:] for r in chunk]
            Us += [np.full(max_new, 0.5)] * pad
            Us = np.stack(Us)
            temps = np.array([float(r.get("temperature", 1.0)) for r in chunk] + [1.0] * pad)
            active = np.array([True] * n_real + [False] * pad)
            res = EG.decode(self.model, self.tok, pre, Us, temps, max_new,
                            text_prefix=[pref_text] * B_CRN if prefix_ids else None, active=active)
            del pre
            out = []
            for i, (r, g) in enumerate(zip(chunk, res[:n_real])):
                ids_full = prefix_ids + g["token_ids"]
                rd = None
                if dS is not None:
                    rd = {"S_by_block": [round(float(x), 3) for x in dS[i]],
                          "R_by_block": [round(float(x), 3) for x in dR[i]], "blocks": list(CAPTURE_BLOCKS)}
                out.append({"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "stage": stage,
                            "model": IT_ID, "template": r["template"], "slot": int(r["slot"]),
                            "ukey": list(r["ukey"]), "temperature": float(r.get("temperature", 1.0)), "top_k": None,
                            "thinking": False, "precision": "bf16", "prompt_sha256": p["prompt_sha256"],
                            "prompt_kind": p["kind"], "prefix_len": len(prefix_ids),
                            "text": self.tok.decode(ids_full, skip_special_tokens=True),
                            "token_ids": ids_full, "finish_reason": g["finish_reason"],
                            "n_new_tokens": g["n_tokens"], "realised_disp": rd, "B": B_CRN, "max_new": max_new,
                            "batch_id": f"{batch_tag}:{b0 // B_CRN}", "utc": utc_now(),
                            "edit_log": [dict(sp.log) for sp in (r.get("specs") or [])], **(r.get("meta") or {})})
            append_jsonl(raw_path, out)
            out_all += out
            dt = time.time() - t0
            append_jsonl(TIMING, [{"batch_id": f"{batch_tag}:{b0 // B_CRN}", "stage": stage, "n_real": n_real,
                                   "B": B_CRN, "seconds": dt, "steps": res[0]["steps"], "max_new": max_new,
                                   "utc": utc_now()}])
            fr: dict[str, int] = {}
            for g in res[:n_real]:
                fr[g["finish_reason"]] = fr.get(g["finish_reason"], 0) + 1
            logger.info(f"{batch_tag}:{b0 // B_CRN}: {n_real}/{B_CRN} rows {dt:.1f}s, {res[0]['steps']} steps, {fr}")
        return out_all

    # -------------------------------------------------------------------------------------------- multi-prompt
    def run_multi(self, items: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path | None,
                  batch_tag: str, B: int = B_CRN, stop_fn: Callable[[str], bool] | None = None,
                  fence_stop: bool = True) -> list[dict[str, Any]]:
        """items: {row_id, ids (full prompt + forced prefix ids), n_prefix (forced response prefix length),
        prefix_ids, ukey, meta}. Uniforms offset by n_prefix."""
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
            temps = np.ones(B)
            active = np.array([True] * n_real + [False] * pad)
            prefs = [self.tok.decode(c["prefix_ids"]) for c in chunk] + [""] * pad
            res = EG.decode(self.model, self.tok, pre, np.stack(Us), temps, max_new, fence_stop=fence_stop,
                            text_prefix=prefs, stop_fn=stop_fn, active=active)
            del pre
            out = []
            for c, g in zip(chunk, res[:n_real]):
                ids_full = list(c["prefix_ids"]) + g["token_ids"]
                out.append({"row_id": c["row_id"], "stage": stage, "ukey": list(c["ukey"]),
                            "n_prefix": c["n_prefix"], "token_ids": ids_full,
                            "text": self.tok.decode(ids_full, skip_special_tokens=True),
                            "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"], "B": B,
                            "max_new": max_new, "batch_id": f"{batch_tag}:{b0 // B}", "utc": utc_now(),
                            **(c.get("meta") or {})})
            if raw_path is not None:
                append_jsonl(raw_path, out)
            out_all += out
            dt = time.time() - t0
            append_jsonl(TIMING, [{"batch_id": f"{batch_tag}:{b0 // B}", "stage": stage, "n_real": n_real, "B": B,
                                   "seconds": dt, "steps": res[0]["steps"], "max_new": max_new, "utc": utc_now()}])
            logger.info(f"{batch_tag}:{b0 // B}: {n_real}/{B} rows {dt:.1f}s, {res[0]['steps']} steps")
        return out_all

    # -------------------------------------------------------------------------------------------- states
    @torch.no_grad()
    def states(self, ids: list[int], layers: list[int], positions: list[int] | None = None,
               want_logits_at: list[int] | None = None) -> dict[str, Any]:
        """Batch-1 clean forward; block outputs at `layers` (fp32 CPU) for `positions` (all if None)."""
        cap: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                x = h[0] if positions is None else h[0, positions]
                cap[l] = x.float().cpu()
            return g
        inp = torch.tensor([ids], device="cuda")
        with block_hooks(EG.layers(self.model), None, {l: mk(l) for l in layers}):
            out = self.model.model(input_ids=inp, use_cache=False)
        res: dict[str, Any] = {"h": cap}
        if want_logits_at is not None:
            res["logits"] = EG.lm_logits(self.model, out.last_hidden_state[0, want_logits_at]).cpu()
        del out
        return res

    def free(self) -> None:
        EG.free_model(self.model)


def blank_edits() -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
    return {}


def zero_dh(pos: list[int]) -> torch.Tensor:
    return torch.zeros(len(pos), D_MODEL, device="cuda")


__all__ = ["Runner", "add_edits", "DATA_DIR"]
