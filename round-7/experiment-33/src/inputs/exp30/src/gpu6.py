#!/usr/bin/env python3
"""GPU stages of iteration 6 (bf16 Qwen3-8B, CPU-resident input embedding, exp27 CRN sampler).

  utest   U1-U5 on 10 slots (results/unit_tests_gpu.json; rows -> data/unit_tests_raw.jsonl, never analysed)
  twins   TWIN cells, N = 50 (slots 0-49) on T03, T2 (engine check vs exp27), T10, T05, T06, T1
  stageA  Stage A exchange cells, N = 30 (slots 0-29): BAN, X_b (b in 0-11, 12-23, 24-35, 0-35), COND (KV splice of
          the condition span = route arm d), RPOS (read position, all 36 blocks); on T03/T10/T2 also MR_0-35, MR_12-23
          (norm-matched random exchange) and PLACEBO (second neutral twin as the source, band 0-35)
  st      ST noise-site grid on T03/T10 (sites S0 S4 S5 S1 S2 S3 + S1E/S2E), drop-ordered groups
  dmd     S3 extension to N = 50 at alpha 2/4, K_S3, DMD temperature calibration (amendment commit), DMD cells N = 50
  top5    T1 top-five plan push (exp20 u_top5, alpha 1/2/4/8, N = 30) + geometry states + prompt TOP5 ban (N = 50)
Every row: data/samples_raw.jsonl (resumable by sample_id). Batches hold rows of ONE (task, template) prompt length,
padded with discarded filler rows to the task's fixed batch size B, so GEMM shapes are identical in every arm.

usage: .venv/bin/python src/gpu6.py utest,twins,stageA,st,dmd,top5 [--deadline-min N]
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (D_MODEL, ENDOFTEXT, IM_END, MODEL_ID, MODEL_REVISION, PRED_DIR, RESULTS_DIR, ROOT,
                 append_deviation, append_jsonl, read_json, read_jsonl, setup_logging, stable_seed, utc_now,
                 write_json)
from cfg6 import (ALL_BLOCKS, BANDS, BATCH6, DMD_STEPS6, DMD_T_CAP, DMD_TOL, ENGINE6, LOG_BLOCKS, N30, N50,
                  PRECISION6, S3_STEPS6, SAMPLES, SITE_BLOCKS6, SITE_POS6, SLOT_MAP, STATES_DIR, ST_TASKS, TASKS6,
                  TEMPLATES6, dir_seed, fence6, max_new6, r_at, sample_id, unit_dir)
from engine5 import BufLayer, kl_scaled, step_probs5
from engine6 import load_model_bf16
from engine_v4 import _inverse_cdf, _kv_list, backtick_ids, block_hooks, clear_act_cache, fence_closed, u_stream, \
    vocab_len
from prompts6 import load_prompts6

TIMING = RESULTS_DIR / "timing_batches.jsonl"
UT_RAW = ROOT / "data" / "unit_tests_raw.jsonl"
DMD_FILE = PRED_DIR / "dmd_temperatures_iter6.json"
GEOM_FILE = STATES_DIR / "geometry_T1_states.npz"
U_TOP5 = ROOT / "inputs_extra" / "exp20" / "directions" / "u_top5.npz"
STATE: dict[str, Any] = {"deadline": float("inf"), "gpu": None, "done": None}


# ------------------------------------------------------------------------------------------------ helpers
def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


def code_stream(task: str, slot: int) -> np.ndarray:
    w, k = SLOT_MAP[slot]
    return u_stream(task, w, k, n=1536)


def done_ids() -> set[str]:
    if STATE["done"] is None:
        STATE["done"] = {r["sample_id"] for r in read_jsonl(SAMPLES)}
    return STATE["done"]


def past_deadline() -> bool:
    return time.time() > STATE["deadline"]


@torch.no_grad()
def prefill6(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """engine_v4.prefill with the KV moved to the CPU (assemble_cache copies it into the batch buffer)."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=dev_of(model))
    cache = DynamicCache()
    clear_act_cache()
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.to("cpu"), V.to("cpu")) for K, V in _kv_list(cache)]
    del cache, out
    clear_act_cache()
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


def assemble6(rows: list[dict[str, Any]], max_steps: int, dev: torch.device):
    """exp27 assemble_cache for rows of one prompt length, with the buffer always on the GPU (prefill KVs live on
    the CPU); rows sharing a prefill object are copied to the GPU once per layer."""
    from transformers.cache_utils import Cache

    P = rows[0]["pre"]["P"]
    assert all(r["pre"]["P"] == P for r in rows)
    B = len(rows)
    K0 = rows[0]["pre"]["kv"][0][0]
    _, H, _, D = K0.shape
    L = P + max_steps + 1
    layers_ = []
    for l in range(len(rows[0]["pre"]["kv"])):
        kb = torch.zeros(B, H, L, D, dtype=K0.dtype, device=dev)
        vb = torch.zeros_like(kb)
        g: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for i, r in enumerate(rows):
            key = id(r["pre"])
            if key not in g:
                K, V = r["pre"]["kv"][l]
                g[key] = (K[0].to(dev), V[0].to(dev))
            kb[i, :, :P] = g[key][0]
            vb[i, :, :P] = g[key][1]
        del g
        layers_.append(BufLayer(kb, vb, P))
    return Cache(layers=layers_), P


def cap_hooks(store: dict[int, torch.Tensor], idx: torch.Tensor, blocks: list[int]) -> dict[int, Callable]:
    """Capture block outputs (model dtype, exact) at positions idx for the given blocks."""
    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            store[l] = h[0, idx].clone()
        return g
    return {l: mk(l) for l in blocks}


class Prompt:
    """One (task, template, kind) prompt with its positions and the clean prefill (+ captured states)."""

    def __init__(self, model: Any, rec: dict[str, Any], capture: bool = True):
        self.rec = rec
        self.ids = rec["ids"]
        self.P, self.p1, self.se = rec["P"], rec["p1"], rec["spec_end"]
        self.R = self.P - 1
        dev = dev_of(model)
        c = rec.get("cond") or [self.p1, self.p1]
        self.c0, self.c1 = c
        # index layout of captured states: [spec..., R, cond...]
        self.idx = torch.tensor(list(range(self.p1, self.se)) + [self.R] + list(range(self.c0, self.c1)), device=dev)
        self.nS = self.se - self.p1
        self.iS = slice(0, self.nS)
        self.iR = self.nS
        self.iC = slice(self.nS + 1, self.nS + 1 + (self.c1 - self.c0))
        self.H: dict[int, torch.Tensor] = {}
        self.pre = prefill6(model, self.ids, capture=cap_hooks(self.H, self.idx, ALL_BLOCKS) if capture else None)


# ------------------------------------------------------------------------------------------------ decoding
@torch.no_grad()
def decode6(model: Any, rows: list[dict[str, Any]], tok: Any, fence_kind: str | None,
            s3: dict[str, Any] | None = None, check_every: int = 8) -> list[dict[str, Any]]:
    """exp27 engine5.decode_rows (shared path: every row has the same prompt length) with exp20's S3 decode-time
    site: for (hooked, shadow) pairs, at decode steps whose INPUT is generated token 1-32 the hooked row's block outputs
    at blocks 12-23 are moved along its unit u so that (h_hooked - h_shadow) . u = target; the shadow row (clean twin
    prefill) is teacher-forced with the hooked row's token, so it carries the clean states of the same text. Logs per
    pair the KL(hooked || shadow) of the next-token distribution and the displacement at blocks 23 and 35."""
    dev = dev_of(model)
    B = len(rows)
    max_new = [int(r["max_new"]) for r in rows]
    max_steps = max(max_new)
    Ps = {r["pre"]["P"] for r in rows}
    assert len(Ps) == 1, "decode6: all rows must share the prompt length"
    cache, Pmax = assemble6(rows, max_steps, dev)
    Pvec = torch.full((B,), Pmax, dtype=torch.long, device=dev)
    Ucode = torch.zeros(B, max_steps, dtype=torch.float64, device=dev)
    for i, r in enumerate(rows):
        Ucode[i, :max_new[i]] = torch.from_numpy(np.asarray(r["u"], dtype=np.float64)[:max_new[i]])
    T_code = torch.tensor([float(r["T"]) for r in rows], dtype=torch.float64, device=dev)
    T_early = torch.tensor([float(r.get("T_early") if r.get("T_early") is not None else r["T"]) for r in rows],
                           dtype=torch.float64, device=dev)
    n_early = torch.tensor([int(r.get("n_early") or 0) for r in rows], dtype=torch.long, device=dev)
    zeros_l = torch.zeros(B, dtype=torch.long, device=dev)
    ones_p = torch.ones(B, dtype=torch.float64, device=dev)
    maxnew_t = torch.tensor(max_new, dtype=torch.long, device=dev)
    fence_rows = torch.tensor([bool(r.get("fence", True)) for r in rows], device=dev)
    i_code = torch.zeros(B, dtype=torch.long, device=dev)
    tick = backtick_ids(tok).to(dev) if fence_kind else None
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
    state = {"step": 0}
    hooks = []
    s3_log: dict[str, list] = {"kl": [], "disp": []}
    if s3:
        hi = torch.tensor(s3["hooked"], device=dev, dtype=torch.long)
        si = torch.tensor(s3["shadow"], device=dev, dtype=torch.long)
        Uv = s3["u"].to(dev, torch.float32)
        tgt = {l: s3["target"][l].to(dev, torch.float32) for l in s3["blocks"]}
        log_blocks = [23, 35]
        cur: dict[int, torch.Tensor] = {}

        def mk(l: int) -> Callable:
            def hook(mod, inp, out):
                h = out[0] if isinstance(out, tuple) else out
                if h.shape[1] != 1 or state["step"] >= S3_STEPS6:
                    return out
                if l in tgt:
                    hh, hs = h[hi, 0].float(), h[si, 0].float()
                    coef = tgt[l] - ((hh - hs) * Uv).sum(-1)
                    h = h.clone()
                    h[hi, 0] = (hh + coef[:, None] * Uv).to(h.dtype)
                    out = (h,) + tuple(out[1:]) if isinstance(out, tuple) else h
                if l in log_blocks:
                    cur[l] = (h[hi, 0].float() - h[si, 0].float()).norm(dim=-1)
                return out
            return hook
        for l in sorted(set(s3["blocks"]) | {23, 35}):
            hooks.append(model.model.layers[l].register_forward_hook(mk(l)))
    try:
        while True:
            state["step"] = step
            T_eff = torch.where(i_code < n_early, T_early, T_code)
            probs = step_probs5(logits, T_eff[:, None], zeros_l, ones_p, False, False)
            u = Ucode[ar, i_code.clamp(max=max_steps - 1)]
            nxt = _inverse_cdf(probs, u)
            if s3:
                nxt[si] = nxt[hi]
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done
            i_code += live.long()
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            done |= is_end | (live & (i_code >= maxnew_t))
            if s3:
                done[si] = done[hi]
                ended[si] = ended[hi]
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
                            if s3:
                                done[si] = done[hi]
                                fenced[si] = fenced[hi]
                if bool(done.all().item()):
                    break
            feed = torch.where(done, im_end_t, nxt)[:, None]
            pos = (Pvec + step)[:, None]
            clear_act_cache()
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            if s3 and step < S3_STEPS6:
                lp_h = torch.log_softmax(logits[hi], -1)
                lp_s = torch.log_softmax(logits[si], -1)
                s3_log["kl"].append((lp_h.exp() * (lp_h - lp_s)).sum(-1).float())
                s3_log["disp"].append({l: cur[l].clone() for l in cur})
            step += 1
    finally:
        for hk in hooks:
            hk.remove()
        clear_act_cache()
    del cache
    toks_c, lps_c = toks.cpu().numpy(), lps.cpu().numpy()
    ended_c, fenced_c = ended.cpu().numpy(), fenced.cpu().numpy()
    out = []
    for r_ in range(B):
        row = toks_c[r_]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r_] else ("fence" if fenced_c[r_] else "length")
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n,
                    "logprob_sum": float(lps_c[r_, :n].sum()), "steps": step + 1})
    if s3:
        kl = torch.stack(s3_log["kl"], 0).cpu().numpy() if s3_log["kl"] else np.zeros((0, len(s3["hooked"])))
        disp = {l: torch.stack([d[l] for d in s3_log["disp"]], 0).cpu().numpy() for l in
                (s3_log["disp"][0].keys() if s3_log["disp"] else [])}
        for j, r_ in enumerate(s3["hooked"]):
            out[r_]["s3"] = {"kl_mean_steps1_32": float(kl[:, j].mean()) if len(kl) else None,
                             "kl_steps": [round(float(x), 6) for x in kl[:, j]],
                             "disp_mean": {int(l): float(disp[l][:, j].mean()) for l in disp}}
    return out


# ------------------------------------------------------------------------------------------------ batches
def emit(task: str, specs: list[dict[str, Any]], res: list[dict[str, Any]], tok: Any, block_id: str,
         B: int, write: bool = True, path: Path = SAMPLES) -> list[dict[str, Any]]:
    nv = vocab_len(tok)
    rows = []
    for sp, r in zip(specs, res):
        if sp.get("filler") or sp.get("shadow"):
            continue
        s = sp["slot"]
        w, k = SLOT_MAP[s]
        text = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
        row = {"task": task, "arm": sp["arm"], "cell": sp["cell"], "block": sp.get("block"), "band": sp.get("band"),
               "source": sp.get("source"), "site": sp.get("site"), "alpha": sp.get("alpha"), "template": w,
               "slot": k, "slot_index": s, "sample_id": sample_id(task, sp["arm"], s), "crn_key": f"{task}|{w}|{k}",
               "u_seed": stable_seed(task, w, k), "dir_seed": sp.get("dir_seed"),
               "prompt_kind": sp["kind"], "prompt_sha256": sp["prompt_sha256"], "P": sp["P"],
               "model": MODEL_ID, "model_revision": MODEL_REVISION, "precision": PRECISION6, "engine": ENGINE6,
               "gpu": STATE["gpu"], "max_new": sp["max_new"], "stop_rule": f"im_end|fence:{fence6(task)}",
               "block_id": block_id, "batch_B": B, "temperature": sp.get("T", 1.0), "dmd_T": sp.get("T_early"),
               "text": text, "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
               "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"],
               "realised": sp.get("realised"), "s3": r.get("s3"), "thinking": False, "utc": utc_now()}
        rows.append(row)
    if write:
        append_jsonl(path, rows)
        if path == SAMPLES:
            done_ids().update(r["sample_id"] for r in rows)
    return rows


def run_batches(model: Any, tok: Any, task: str, specs: list[dict[str, Any]], tag: str,
                path: Path = SAMPLES, s3_pairs: bool = False) -> list[dict[str, Any]]:
    """specs share (task, template, P). Each spec: {'arm','cell','slot','kind','prompt_sha256','P','pre' | 'make'}.
    'make' (a callable returning (pre, realised)) builds per-row prefills lazily, batch by batch, so at most B
    edited prefills are alive. s3_pairs: specs come as (hooked, shadow) pairs; both count towards B."""
    B = BATCH6[task]
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(specs):
        if past_deadline():
            logger.warning(f"deadline: {len(specs) - i} rows of {tag} not run")
            append_jsonl(RESULTS_DIR / "not_run.jsonl", [{"tag": tag, "task": task, "n_rows": len(specs) - i,
                                                         "utc": utc_now()}])
            break
        chunk = specs[i:i + B]
        i += B
        t0 = time.time()
        for sp in chunk:
            if "pre" not in sp:
                sp["pre"], sp["realised"] = sp["make"]()
        while len(chunk) < B:  # filler rows keep the batch shape fixed; their outputs are discarded
            f = dict(chunk[0])
            f["filler"] = True
            f["shadow"] = False
            chunk.append(f)
        s3 = None
        if s3_pairs:
            hk = [j for j, sp in enumerate(chunk) if sp.get("s3_role") == "hooked" and not sp.get("filler")]
            sh = [j for j, sp in enumerate(chunk) if sp.get("s3_role") == "shadow" and not sp.get("filler")]
            if hk:
                assert len(hk) == len(sh)
                s3 = {"hooked": hk, "shadow": sh, "blocks": SITE_BLOCKS6["S3"],
                      "u": torch.stack([chunk[j]["s3_u"] for j in hk]),
                      "target": {l: torch.stack([chunk[j]["s3_target"][l] for j in hk]) for l in SITE_BLOCKS6["S3"]}}
        rows = [{"pre": sp["pre"], "u": code_stream(task, sp["slot"]), "T": sp.get("T", 1.0),
                 "T_early": sp.get("T_early"), "n_early": sp.get("n_early", 0), "max_new": sp["max_new"],
                 "fence": True} for sp in chunk]
        try:
            res = decode6(model, rows, tok, fence6(task), s3=s3)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            logger.error(f"OOM in {tag}; batch skipped")
            append_deviation(f"OOM_{tag}", f"CUDA OOM in batch {tag}; rows skipped")
            continue
        out += emit(task, chunk, res, tok, tag, B, path=path)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"tag": tag, "task": task, "B": B, "seconds": round(dt, 2), "steps": res[0]["steps"],
                               "n_real": sum(1 for sp in chunk if not sp.get("filler") and not sp.get("shadow")),
                               "n_length": sum(r["finish_reason"] == "length" for r in res), "utc": utc_now()}])
        for sp in chunk:  # free per-row edited prefills
            if "make" in sp:
                sp.pop("pre", None)
        del rows, res
    return out


def base_spec(task: str, arm: str, cell: str, slot: int, pr: Prompt, kind: str, **kw) -> dict[str, Any]:
    return {"arm": arm, "cell": cell, "slot": slot, "kind": kind, "prompt_sha256": pr.rec["prompt_sha256"],
            "P": pr.P, "max_new": max_new6(task), **kw}


# ------------------------------------------------------------------------------------------------ edits
def set_rows_edit(pos: torch.Tensor, src: dict[int, torch.Tensor]) -> dict[int, Callable]:
    """Exchange: overwrite block-l outputs at positions pos with src[l] (exact source values)."""
    def mk(l: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            h[0, pos] = src[l].to(h.dtype)
            return h
        return f
    return {l: mk(l) for l in src}


def targeted_edit(pos: torch.Tensor, u: dict[int, torch.Tensor], target: dict[int, torch.Tensor],
                  h_ref: dict[int, torch.Tensor]) -> dict[int, Callable]:
    """Displacement-targeted (exp17/exp20): delta = h - h_clean; h <- h + (target - delta . u) u, in fp32."""
    def mk(l: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            hs = h[0, pos].float()
            comp = (hs - h_ref[l]) @ u[l]
            new = hs + (target[l] - comp)[:, None] * u[l]
            h = h.clone()
            h[0, pos] = new.to(h.dtype)
            return h
        return f
    return {l: mk(l) for l in target}


def disp_capture(store: dict, pr: Prompt, blocks: list[int]) -> dict[int, Callable]:
    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            store[l] = h[0, pr.idx].clone()
        return g
    return {l: mk(l) for l in blocks}


def realised_log(tw: Prompt, H: dict[int, torch.Tensor], n: torch.Tensor) -> dict[str, Any]:
    """Realised displacement from the clean twin at blocks 12-35, in ban-free units (divide by n[l, p])."""
    dS, dR, dC = {}, {}, {}
    for l in LOG_BLOCKS:
        if l not in H:
            continue
        d = (H[l].float() - tw.H[l].float()).norm(dim=-1)
        dS[l] = float((d[tw.iS] / n[l, tw.iS]).mean())
        dR[l] = float(d[tw.iR] / n[l, tw.iR])
        if tw.c1 > tw.c0:
            dC[l] = float((d[tw.iC] / n[l, tw.iC]).mean())
    return {"dS": dS, "dR": dR, "dC": dC}


# ------------------------------------------------------------------------------------------------ contexts
class TaskW:
    """Per (task, template): twin / ban / placebo prompts with all-block captures at spec, R and cond."""

    def __init__(self, model: Any, P6: dict, task: str, w: str, kinds: tuple[str, ...] = ("twin", "ban")):
        self.model, self.task, self.w = model, task, w
        self.pr = {k: Prompt(model, P6[(task, w, k)]) for k in kinds}
        tw = self.pr["twin"]
        for k, p in self.pr.items():
            assert p.P == tw.P and p.p1 == tw.p1 and p.se == tw.se, f"{task}/{w}/{k}: positions differ from the twin"
        # ban-free unit n[l, p] = ||h_twin[l, p]|| * r_Q(l) at the captured positions (fp32, GPU)
        self.n = torch.stack([tw.H[l].float().norm(dim=-1) * r_at(l) for l in ALL_BLOCKS])  # [36, |idx|]

    def free(self) -> None:
        for p in self.pr.values():
            p.H.clear()
        self.pr.clear()
        gc.collect()
        torch.cuda.empty_cache()


def tok1_probe(model: Any, tw: Prompt, pres: list[dict[str, Any]], toks1: list[int]) -> list[dict[int, float]]:
    """Generated token 1 with the twin's slot token teacher-forced: block outputs (23, 35) at position P for each edited
    prefill, minus the clean twin's at the same token; returned in ban-free units of block l at R."""
    dev = dev_of(model)
    out_h: dict[int, torch.Tensor] = {}

    def run(pre_list: list[dict[str, Any]], tks: list[int]) -> dict[int, torch.Tensor]:
        rows = [{"pre": p} for p in pre_list]
        cache, Pmax = assemble6(rows, 1, dev)
        got: dict[int, torch.Tensor] = {}

        def mk(l: int) -> Callable:
            def g(h: torch.Tensor) -> None:
                got[l] = h[:, 0].float().clone()
            return g
        with block_hooks(model, None, {l: mk(l) for l in (23, 35)}):
            model.model(input_ids=torch.tensor(tks, device=dev)[:, None], past_key_values=cache,
                        position_ids=torch.full((len(tks), 1), Pmax, device=dev, dtype=torch.long), use_cache=True)
        del cache
        clear_act_cache()
        return got
    he = run(pres, toks1)
    hc = run([tw.pre] * len(toks1), toks1)
    res = []
    for i in range(len(toks1)):
        res.append({l: float((he[l][i] - hc[l][i]).norm() / (hc[l][i].norm() * r_at(l))) for l in (23, 35)})
    del out_h
    return res


def twin_tok1(tw: Prompt, task: str, slot: int) -> int:
    probs = torch.softmax(tw.pre["r_logits"].double(), -1)[None]
    u = torch.tensor([code_stream(task, slot)[0]], dtype=torch.float64, device=probs.device)
    return int(_inverse_cdf(probs, u)[0])


# ------------------------------------------------------------------------------------------------ U-tests
def stage_utest(model: Any, tok: Any, P6: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    K = list(range(10))
    # U1, U2, U5 on T03 W1 (slots 0-7) + W2 (8, 9): twin vs alpha-0 hook vs identity exchange vs repeat
    for task in ("T03", "T2"):
        res_tw, res_s0, res_id, res_rep = {}, {}, {}, {}
        for w in ("W1", "W2"):
            slots = [s for s in K if SLOT_MAP[s][0] == w]
            if not slots:
                continue
            ctx = TaskW(model, P6, task, w, ("twin", "ban"))
            tw = ctx.pr["twin"]
            sp_tw = [base_spec(task, "UT_TWIN", "UT", s, tw, "twin", pre=tw.pre) for s in slots]
            pos = tw.idx[tw.iS]
            zero = {l: torch.zeros(len(pos), device=dev_of(model)) for l in SITE_BLOCKS6["S0"]}
            u0 = {l: torch.tensor(unit_dir(dir_seed(task, "S0", 0, 0)), device=dev_of(model)) for l in zero}
            href = {l: tw.H[l][tw.iS].float() for l in zero}
            pre0 = prefill6(model, tw.ids, edits=targeted_edit(pos, u0, zero, href))
            sp_s0 = [base_spec(task, "UT_S0_a0", "UT", s, tw, "twin", pre=pre0) for s in slots]
            pre_id = prefill6(model, tw.ids, edits=set_rows_edit(pos, {l: tw.H[l][tw.iS] for l in ALL_BLOCKS}))
            sp_id = [base_spec(task, "UT_IDENT", "UT", s, tw, "twin", pre=pre_id) for s in slots]
            sp_rep = [base_spec(task, "UT_TWIN_REP", "UT", s, tw, "twin", pre=tw.pre) for s in slots]
            for name, sps, store in (("tw", sp_tw, res_tw), ("s0", sp_s0, res_s0), ("id", sp_id, res_id),
                                     ("rep", sp_rep, res_rep)):
                rows = run_batches(model, tok, task, sps, f"UT:{task}:{w}:{name}", path=UT_RAW)
                for r in rows:
                    store[r["slot_index"]] = r["token_ids"]
            # U3 (T2 only): band 0-35 exchange at spec == KV splice of the ban's spec KV + recomputed tail
            if task == "T2":
                bn = ctx.pr["ban"]
                pre_x = prefill6(model, tw.ids, edits=set_rows_edit(pos, {l: bn.H[l][bn.iS] for l in ALL_BLOCKS}))
                from transformers.cache_utils import DynamicCache
                cache = DynamicCache()
                for l in range(len(tw.pre["kv"])):
                    Kt, Vt = tw.pre["kv"][l]
                    Kb, Vb = bn.pre["kv"][l]
                    K_ = torch.cat([Kt[:, :, :tw.p1], Kb[:, :, tw.p1:tw.se]], 2).to(dev_of(model))
                    V_ = torch.cat([Vt[:, :, :tw.p1], Vb[:, :, tw.p1:tw.se]], 2).to(dev_of(model))
                    cache.update(K_.contiguous(), V_.contiguous(), l)
                tail = torch.tensor([tw.ids[tw.se:]], device=dev_of(model))
                pos_t = torch.arange(tw.se, tw.P, device=dev_of(model))[None]
                hh = model.model(input_ids=tail, past_key_values=cache, position_ids=pos_t,
                                 use_cache=True).last_hidden_state
                lg_splice = model.lm_head(hh[:, -1]).float()[0]
                kv_splice = [(K_.to("cpu"), V_.to("cpu")) for K_, V_ in _kv_list(cache)]
                d = float((lg_splice - pre_x["r_logits"]).abs().max())
                out.setdefault("U3", {})[w] = {"max_abs_logit_diff_at_R": d,
                                               "top1_equal": int(lg_splice.argmax()) == int(pre_x["r_logits"].argmax())}
                del cache, hh
                sp_x = [base_spec(task, "UT_X0-35", "UT", s, tw, "twin", pre=pre_x) for s in slots]
                pre_sp = {"kv": kv_splice, "r_logits": lg_splice, "P": tw.P}
                sp_sp = [base_spec(task, "UT_SPLICE", "UT", s, tw, "twin", pre=pre_sp) for s in slots]
                rx = {r["slot_index"]: r["token_ids"] for r in run_batches(model, tok, task, sp_x, f"UT:{w}:x",
                                                                          path=UT_RAW)}
                rs = {r["slot_index"]: r["token_ids"] for r in run_batches(model, tok, task, sp_sp, f"UT:{w}:sp",
                                                                          path=UT_RAW)}
                out.setdefault("U3_programs", {})[w] = {"n": len(rx), "byte_identical": sum(
                    rx[s] == rs.get(s) for s in rx)}
            ctx.free()
        same = lambda a, b: sum(a[s] == b.get(s) for s in a)  # noqa: E731
        out[f"U1_{task}"] = {"n": len(res_tw), "byte_identical_alpha0_vs_twin": same(res_tw, res_s0)}
        out[f"U2_{task}"] = {"n": len(res_tw), "byte_identical_identity_exchange_vs_twin": same(res_tw, res_id)}
        out[f"U5_{task}"] = {"n": len(res_tw), "byte_identical_repeat": same(res_tw, res_rep)}
    # U4: realised displacement along u equals alpha * n within 1% (S0, alpha 2, T03 W1, 3 slots)
    ctx = TaskW(model, P6, "T03", "W1", ("twin",))
    tw = ctx.pr["twin"]
    errs = []
    for s in range(3):
        _pre, rec, _H = st_prefill(model, ctx, "T03", "S0", 2.0, s, want_states=True)
        errs.append(rec["relerr_along_u_max"])
    out["U4"] = {"max_rel_err_along_u": float(max(errs)), "pass": bool(max(errs) < 0.01)}
    ctx.free()
    out["pass"] = {"U1": all(v["byte_identical_alpha0_vs_twin"] == v["n"] for k, v in out.items() if k.startswith("U1")),
                   "U2": all(v["byte_identical_identity_exchange_vs_twin"] == v["n"] for k, v in out.items()
                             if k.startswith("U2")),
                   "U3": all(v["max_abs_logit_diff_at_R"] < 0.05 for v in out.get("U3", {}).values()),
                   "U4": out["U4"]["pass"],
                   "U5": all(v["byte_identical_repeat"] == v["n"] for k, v in out.items() if k.startswith("U5"))}
    write_json(RESULTS_DIR / "unit_tests_gpu.json", out)
    logger.info(f"U-tests: {out['pass']}")
    return out


# ------------------------------------------------------------------------------------------------ twins + Stage A
def mr_prefill(model: Any, ctx: TaskW, task: str, band: str, slot: int) -> tuple[dict, dict]:
    """MR_b: h <- h_twin + ||h_src - h_twin||_(l,p) * u_(slot,l,p) at spec positions of band b (u fresh per (l, p))."""
    tw, bn = ctx.pr["twin"], ctx.pr["ban"]
    blocks = BANDS[band]
    seed = dir_seed(task, f"MR_{band}", 0, slot)
    g = np.random.Generator(np.random.PCG64(seed))
    X = g.standard_normal((len(blocks), tw.nS, D_MODEL), dtype=np.float32)
    X /= np.linalg.norm(X, axis=-1, keepdims=True)
    Xt = torch.from_numpy(X).to(dev_of(model))
    src = {}
    for j, l in enumerate(blocks):
        ht = tw.H[l][tw.iS].float()
        d = (bn.H[l][tw.iS].float() - ht).norm(dim=-1)
        src[l] = ht + d[:, None] * Xt[j]
    pre = prefill6(model, tw.ids, edits=set_rows_edit(tw.idx[tw.iS], src))
    del Xt, src
    return pre, {"dir_seed": seed}


def stage_twins_A(model: Any, tok: Any, P6: dict, tasks: tuple[str, ...], do_twins: bool, do_A: bool) -> None:
    for task in tasks:
        for w in TEMPLATES6:
            slots50 = [s for s in N50 if SLOT_MAP[s][0] == w]
            slots30 = [s for s in N30 if SLOT_MAP[s][0] == w]
            kinds = ("twin", "ban", "placebo") if task in ("T03", "T10", "T2") else ("twin", "ban")
            need_tw = do_twins and any(sample_id(task, "TWIN", s) not in done_ids() for s in slots50)
            need_A = do_A and any(sample_id(task, "X_0-35", s) not in done_ids() or
                                  sample_id(task, "BAN", s) not in done_ids() or
                                  (task in ("T03", "T10", "T2") and sample_id(task, "MR_12-23", s) not in done_ids())
                                  for s in slots30)
            if not (need_tw or need_A) or past_deadline():
                continue
            t0 = time.time()
            ctx = TaskW(model, P6, task, w, kinds)
            tw, bn = ctx.pr["twin"], ctx.pr["ban"]
            specs: list[dict[str, Any]] = []

            def add(arm: str, cell: str, slots: list[int], pr: Prompt, kind: str, **kw) -> None:
                for s in slots:
                    if sample_id(task, arm, s) not in done_ids():
                        specs.append(base_spec(task, arm, cell, s, pr, kind, **kw))
            if do_twins:
                add("TWIN", "TWIN", slots50, tw, "twin", pre=tw.pre)
            if do_A:
                spec_pos = tw.idx[tw.iS]
                add("BAN", "BAN", slots30, bn, "ban", pre=bn.pre, source="ban")
                for b, blocks in BANDS.items():
                    if any(sample_id(task, f"X_{b}", s) not in done_ids() for s in slots30):
                        pre_b = prefill6(model, tw.ids, edits=set_rows_edit(spec_pos, {l: bn.H[l][bn.iS]
                                                                                      for l in blocks}))
                        add(f"X_{b}", "X", slots30, tw, "twin", pre=pre_b, band=b, source="ban")
                # COND: twin prefill, then the condition span's K/V in every layer replaced by the ban's
                kv = []
                for l in range(len(tw.pre["kv"])):
                    K, V = tw.pre["kv"][l][0].clone(), tw.pre["kv"][l][1].clone()
                    K[:, :, tw.c0:tw.c1] = bn.pre["kv"][l][0][:, :, tw.c0:tw.c1]
                    V[:, :, tw.c0:tw.c1] = bn.pre["kv"][l][1][:, :, tw.c0:tw.c1]
                    kv.append((K, V))
                add("COND", "COND", slots30, tw, "twin", pre={"kv": kv, "r_logits": tw.pre["r_logits"], "P": tw.P},
                    source="ban", band="kv_cond")
                pre_r = prefill6(model, tw.ids, edits=set_rows_edit(tw.idx[tw.iR:tw.iR + 1],
                                                                    {l: bn.H[l][tw.iR:tw.iR + 1] for l in ALL_BLOCKS}))
                add("RPOS", "RPOS", slots30, tw, "twin", pre=pre_r, source="ban", band="R_0-35")
                if task in ("T03", "T10", "T2"):
                    pl = ctx.pr["placebo"]
                    pre_p = prefill6(model, tw.ids, edits=set_rows_edit(spec_pos, {l: pl.H[l][pl.iS]
                                                                                  for l in ALL_BLOCKS}))
                    add("PLACEBO", "PLACEBO", slots30, tw, "twin", pre=pre_p, band="0-35", source="placebo")
                    for b in ("0-35", "12-23"):
                        for s in slots30:
                            if sample_id(task, f"MR_{b}", s) not in done_ids():
                                sp = base_spec(task, f"MR_{b}", "MR", s, tw, "twin", band=b, source="random",
                                               dir_seed=dir_seed(task, f"MR_{b}", 0, s))
                                sp["make"] = (lambda b=b, s=s: mr_prefill(model, ctx, task, b, s))
                                specs.append(sp)
            run_batches(model, tok, task, specs, f"A:{task}:{w}")
            ctx.free()
            logger.info(f"twins/stageA {task}/{w}: {len(specs)} rows in {time.time() - t0:.0f}s")


# ------------------------------------------------------------------------------------------------ ST grid
def site_target(ctx: TaskW, site: str, l: int, alpha: float) -> tuple[torch.Tensor, torch.Tensor]:
    """(positions, target) of a prefill site at block l, ban-free units (exp20 site definitions)."""
    tw = ctx.pr["twin"]
    n = ctx.n
    nS = n[l, tw.iS]
    if site in ("S0", "S4", "S5", "TOP5"):
        return tw.idx[tw.iS], alpha * nS
    if site == "S1":
        return tw.idx[tw.iR:tw.iR + 1], alpha * n[l, tw.iR:tw.iR + 1]
    if site == "S1E":  # all of S0's energy at block l, put on R
        return tw.idx[tw.iR:tw.iR + 1], alpha * torch.sqrt((nS ** 2).sum()).reshape(1)
    nC = n[l, tw.iC]
    if site == "S2":
        return tw.idx[tw.iC], alpha * nC
    if site == "S2E":
        c = torch.sqrt((nS ** 2).sum() / (nC ** 2).sum().clamp(min=1e-12))
        return tw.idx[tw.iC], alpha * c * nC
    raise ValueError(site)


def st_prefill(model: Any, ctx: TaskW, task: str, site: str, alpha: float, slot: int,
               want_states: bool = False) -> tuple[dict, dict, dict | None]:
    tw = ctx.pr["twin"]
    seed = dir_seed(task, site, alpha, slot)
    uv = torch.tensor(unit_dir(seed), device=dev_of(model))
    blocks = SITE_BLOCKS6[site]
    pos, tgt, href, uu = None, {}, {}, {}
    for l in blocks:
        pos, tgt[l] = site_target(ctx, site, l, alpha)
        sel = (pos[:, None] == tw.idx[None, :]).float().argmax(1)
        href[l] = tw.H[l][sel].float()
        uu[l] = uv
    H: dict[int, torch.Tensor] = {}
    pre = prefill6(model, tw.ids, edits=targeted_edit(pos, uu, tgt, href),
                   capture=disp_capture(H, tw, sorted(set(LOG_BLOCKS) | set(blocks))))
    rec = realised_log(tw, H, ctx.n)
    rel = []
    for l in blocks:
        sel = (pos[:, None] == tw.idx[None, :]).float().argmax(1)
        comp = (H[l][sel].float() - tw.H[l][sel].float()) @ uv
        rel.append(float(((comp - tgt[l]).abs() / tgt[l].abs().clamp(min=1e-6)).max()))
    lp = torch.log_softmax(pre["r_logits"].double(), -1)
    lq = torch.log_softmax(tw.pre["r_logits"].double(), -1)
    rec.update({"dir_seed": seed, "relerr_along_u_max": max(rel), "first_token_kl": float((lp.exp() * (lp - lq)).sum()),
                "target_mean_b12": float(tgt[blocks[0]].mean()), "site": site, "alpha": alpha})
    return pre, rec, (H if want_states else None)


ST_GROUPS = [  # drop-ordered (plan STEP 6): first entries are never dropped
    ("core", [(s, a) for a in (1.0, 2.0, 4.0) for s in ("S0", "S4", "S5", "S1", "S2", "S3")]),
    ("energy_a2", [("S1E", 2.0), ("S2E", 2.0)]),
    ("a8_spec", [("S0", 8.0), ("S4", 8.0), ("S5", 8.0), ("S3", 8.0)]),
    ("a8_RC", [("S1", 8.0), ("S2", 8.0)]),
    ("energy_a4", [("S1E", 4.0), ("S2E", 4.0)]),
]


def arm_st(site: str, alpha: float) -> str:
    return f"ST_{site}_a{alpha:g}"


def st_cells(model: Any, tok: Any, P6: dict, task: str, cells: list[tuple[str, float]], slots_all: tuple[int, ...],
             tag: str) -> None:
    for w in TEMPLATES6:
        slots = [s for s in slots_all if SLOT_MAP[s][0] == w]
        todo = [(site, a, s) for site, a in cells for s in slots if sample_id(task, arm_st(site, a), s) not in done_ids()]
        if not todo or past_deadline():
            continue
        t0 = time.time()
        ctx = TaskW(model, P6, task, w, ("twin",))
        tw = ctx.pr["twin"]
        nG = {l: ctx.n[l, tw.iS].mean() for l in SITE_BLOCKS6["S3"]}
        pre_specs: list[dict[str, Any]] = []
        s3_specs: list[dict[str, Any]] = []
        for site, a, s in todo:
            arm = arm_st(site, a)
            if site == "S3":
                seed = dir_seed(task, "S3", a, s)
                uv = torch.tensor(unit_dir(seed), device=dev_of(model))
                hk = base_spec(task, arm, "ST", s, tw, "twin", pre=tw.pre, site="S3", alpha=a, dir_seed=seed,
                               s3_role="hooked", s3_u=uv, s3_target={l: a * nG[l] for l in nG},
                               realised={"dir_seed": seed, "site": "S3", "alpha": a})
                sh = dict(hk)
                sh.update({"s3_role": "shadow", "shadow": True})
                s3_specs += [hk, sh]
            else:
                sp = base_spec(task, arm, "ST", s, tw, "twin", site=site, alpha=a, dir_seed=dir_seed(task, site, a, s))
                sp["make"] = (lambda site=site, a=a, s=s: st_prefill(model, ctx, task, site, a, s)[:2])
                pre_specs.append(sp)
        # prefill-site rows: build per batch, add the generated-token-1 probe (twin's slot token teacher-forced)
        B = BATCH6[task]
        for i in range(0, len(pre_specs), B):
            if past_deadline():
                break
            chunk = pre_specs[i:i + B]
            for sp in chunk:
                sp["pre"], sp["realised"] = sp["make"]()
            t1 = [twin_tok1(tw, task, sp["slot"]) for sp in chunk]
            g1 = tok1_probe(model, tw, [sp["pre"] for sp in chunk], t1)
            for sp, gg, tk in zip(chunk, g1, t1):
                sp["realised"]["dG1"] = gg
                sp["realised"]["twin_tok1"] = tk
            run_batches(model, tok, task, chunk, f"{tag}:{task}:{w}")
        if s3_specs:
            run_batches(model, tok, task, s3_specs, f"{tag}:S3:{task}:{w}", s3_pairs=True)
        ctx.free()
        logger.info(f"ST {tag} {task}/{w}: {len(todo)} rows in {time.time() - t0:.0f}s")


def stage_st(model: Any, tok: Any, P6: dict, groups: list[str] | None = None) -> None:
    for name, cells in ST_GROUPS:
        if groups and name not in groups:
            continue
        for task in ST_TASKS:
            st_cells(model, tok, P6, task, cells, N30, f"ST_{name}")
        write_json(RESULTS_DIR / "st_progress.json", {"last_group": name, "utc": utc_now()})


# ------------------------------------------------------------------------------------------------ DMD
@torch.no_grad()
def record_lsm(model: Any, tw: Prompt, task: str, slots: list[int], T: float, n_steps: int) -> torch.Tensor:
    """Log-softmax of the UNSCALED logits along each row's own path sampled at temperature T (tokens 1..n_steps)."""
    dev = dev_of(model)
    rows = [{"pre": tw.pre} for _ in slots]
    cache, Pmax = assemble6(rows, n_steps, dev)
    B = len(slots)
    U = torch.tensor(np.stack([code_stream(task, s)[:n_steps] for s in slots]), device=dev)
    logits = tw.pre["r_logits"][None].expand(B, -1).float()
    out = torch.zeros((B, n_steps), dtype=torch.float64, device=dev)
    for step in range(n_steps):
        lsm = torch.log_softmax(logits, dim=-1)
        probs = torch.softmax(logits.double() / T, dim=-1)
        nxt = _inverse_cdf(probs, U[:, step])
        out[:, step] = kl_scaled(lsm, T)
        if step + 1 == n_steps:
            break
        h = model.model(input_ids=nxt[:, None], past_key_values=cache,
                        position_ids=torch.full((B, 1), Pmax + step, device=dev, dtype=torch.long),
                        use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).float()
    del cache
    clear_act_cache()
    return out  # [B, n_steps] KL(softmax(z/T) || softmax(z)) at each on-policy position


def stage_dmd(model: Any, tok: Any, P6: dict) -> None:
    from commit6 import commit
    # S3 extension to N = 50 at alpha 2 and 4
    for task in ST_TASKS:
        st_cells(model, tok, P6, task, [("S3", 2.0), ("S3", 4.0)], N50, "S3ext")
    rows = [r for r in read_jsonl(SAMPLES) if r["cell"] == "ST" and r["site"] == "S3"]
    dmd = read_json(DMD_FILE) if DMD_FILE.exists() else {}
    for task in ST_TASKS:
        for a in (2.0, 4.0):
            key = f"{task}|{a:g}"
            if key in dmd:
                continue
            kls = [r["s3"]["kl_mean_steps1_32"] for r in rows if r["task"] == task and r["alpha"] == a and r.get("s3")
                   and r["s3"].get("kl_mean_steps1_32") is not None]
            if not kls:
                continue
            K = float(np.mean(kls))
            ctx = TaskW(model, P6, task, "W1", ("twin",))
            tw = ctx.pr["twin"]
            cal_slots = [s for s in N50 if SLOT_MAP[s][0] == "W1"][:10]
            # on-policy KL of the temperature schedule along its own paths, bisected on T
            f_cache: dict[float, float] = {}

            def f_on(T: float) -> float:
                if T not in f_cache:
                    f_cache[T] = float(record_lsm(model, tw, task, cal_slots, T, DMD_STEPS6).mean())
                return f_cache[T]
            lo, hi = 1.0, DMD_T_CAP
            reached = f_on(hi) >= K * (1 - DMD_TOL)
            it = []
            T = hi
            if reached:
                for _ in range(12):
                    mid = 0.5 * (lo + hi)
                    fm = f_on(mid)
                    it.append([mid, fm])
                    if abs(fm - K) <= DMD_TOL * K:
                        T = mid
                        break
                    if fm < K:
                        lo = mid
                    else:
                        hi = mid
                    T = mid
            dmd[key] = {"task": task, "alpha": a, "K_S3": K, "n_S3": len(kls), "T_dmd": float(T),
                        "f_on": f_on(T), "iterations": it, "converged": bool(abs(f_on(T) - K) <= DMD_TOL * K),
                        "cap_reached": not reached, "cal_template": "W1", "cal_slots": cal_slots,
                        "label": None if reached else "S3 exceeds token-level departure (T capped at 3.0)"}
            ctx.free()
            write_json(DMD_FILE, dmd)
            logger.info(f"DMD {key}: K_S3 {K:.4f} -> T {T:.3f} (f_on {f_on(T):.4f})")
    commit("amendment2_dmd_temperatures", {"dmd_temperatures": dmd})
    for task in ST_TASKS:
        for a in (2.0, 4.0):
            key = f"{task}|{a:g}"
            if key not in dmd:
                continue
            T_d = dmd[key]["T_dmd"]
            for w in TEMPLATES6:
                slots = [s for s in N50 if SLOT_MAP[s][0] == w and sample_id(task, f"DMD_a{a:g}", s) not in done_ids()]
                if not slots or past_deadline():
                    continue
                pr = Prompt(model, P6[(task, w, "twin")], capture=False)
                specs = [base_spec(task, f"DMD_a{a:g}", "DMD", s, pr, "twin", pre=pr.pre, T_early=T_d,
                                   n_early=DMD_STEPS6, alpha=a) for s in slots]
                run_batches(model, tok, task, specs, f"DMD:{task}:{w}")
                del pr
                torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ top-five push
def stage_top5(model: Any, tok: Any, P6: dict, with_ban: bool = True) -> None:
    task = "T1"
    z = np.load(U_TOP5)
    utop = {l: torch.tensor(z["u_top5"][j], device=dev_of(model)) for j, l in enumerate(z["blocks"].tolist())}
    blocks = sorted(utop)
    geo: dict[str, Any] = {}
    # pass 1 -- bf16 unit: exp20's nS = mean over templates of ||h_ban - h_twin|| at spec positions, blocks 12-23
    dn = []
    for w in TEMPLATES6:
        ctx = TaskW(model, P6, task, w, ("twin", "ban"))
        tw, bn = ctx.pr["twin"], ctx.pr["ban"]
        dn.append(torch.stack([(bn.H[l][bn.iS].float() - tw.H[l][tw.iS].float()).norm(dim=-1) for l in blocks]).cpu())
        geo[f"twin|{w}"] = np.stack([tw.H[l][tw.iS].float().mean(0).cpu().numpy() for l in blocks])
        geo[f"ban1|{w}"] = np.stack([bn.H[l][bn.iS].float().mean(0).cpu().numpy() for l in blocks])
        ctx.free()
    nS_all = torch.stack(dn).mean(0)
    np.save(STATES_DIR / "unit_T1_nS_bf16.npy", nS_all.numpy())
    nS = {l: nS_all[j].to(dev_of(model)) for j, l in enumerate(blocks)}
    # pass 2 -- the push: displacement-targeted along u_top5[l] at spec positions, blocks 12-23, prefill only
    for w in TEMPLATES6:
        ctx = TaskW(model, P6, task, w, ("twin",))
        tw = ctx.pr["twin"]
        for a in (1.0, 2.0, 4.0, 8.0):
            arm = f"TOP5_a{a:g}"
            href = {l: tw.H[l][tw.iS].float() for l in blocks}
            tgt = {l: a * nS[l] for l in blocks}
            H: dict[int, torch.Tensor] = {}
            pre = prefill6(model, tw.ids, edits=targeted_edit(tw.idx[tw.iS], utop, tgt, href),
                           capture=disp_capture(H, tw, sorted(set(LOG_BLOCKS) | set(blocks))))
            geo[f"push{a:g}|{w}"] = np.stack([H[l][tw.iS].float().mean(0).cpu().numpy() for l in blocks])
            rec = realised_log(tw, H, ctx.n)
            rec["unit"] = "bf16 nS (ban - twin) at spec, blocks 12-23"
            del H
            slots = [s for s in N30 if SLOT_MAP[s][0] == w and sample_id(task, arm, s) not in done_ids()]
            if slots and not past_deadline():
                specs = [base_spec(task, arm, "TOP5PUSH", s, tw, "twin", pre=pre, site="TOP5", alpha=a,
                                   realised=rec) for s in slots]
                run_batches(model, tok, task, specs, f"TOP5:{w}:a{a:g}")
            del pre
        ctx.free()
    if with_ban:
        for w in TEMPLATES6:
            pr = Prompt(model, P6[(task, w, "top5ban")])
            geo[f"top5ban|{w}"] = np.stack([pr.H[l][pr.iS].float().mean(0).cpu().numpy() for l in blocks])
            pr.H.clear()
            slots = [s for s in N50 if SLOT_MAP[s][0] == w and sample_id(task, "TOP5BAN", s) not in done_ids()]
            if slots and not past_deadline():
                specs = [base_spec(task, "TOP5BAN", "TOP5BAN", s, pr, "top5ban", pre=pr.pre) for s in slots]
                run_batches(model, tok, task, specs, f"TOP5BAN:{w}")
            del pr
            torch.cuda.empty_cache()
    np.savez(GEOM_FILE, blocks=np.array(blocks), **{k.replace("|", "__"): v for k, v in geo.items()})
    logger.info(f"top5: geometry states {len(geo)} -> {GEOM_FILE.name}")


# ------------------------------------------------------------------------------------------------ extensions
def pad_record(tok: Any, src: dict[str, Any], kind: str) -> dict[str, Any]:
    """Padding twin of a source prompt: the condition segment's tokens [p0, p1 - 2) replaced by ' .' tokens, so the
    length and every id from 'Task:' on are identical (ids built directly; the edited span is the condition span)."""
    import json as _json
    from cfg import sha256_text
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    ids = list(src["ids"])
    c0 = src["p0"]
    seg_end = src["p1"]
    # the blank-line token(s) directly before 'Task:' stay; everything from p0 up to them becomes ' .'
    k = seg_end
    while k > c0 and "\n" in tok.decode([ids[k - 1]]):
        k -= 1
    for i in range(c0, k):
        ids[i] = dot[0]
    return {"task": src["task"], "w": src["w"], "kind": kind, "ids": ids, "P": len(ids), "p1": src["p1"],
            "spec_end": src["spec_end"], "cond": [c0, k], "R": len(ids) - 1, "segment": tok.decode(ids[c0:k]),
            "source": f"padding twin of {src['kind']}", "prompt_sha256": sha256_text(_json.dumps(ids))}


def ext_prompts(tok: Any) -> list[dict[str, Any]]:
    """Forced 'Implement Y' sources (T2: exp8 frozen forced paraphrase 0 of bf_spfa; T10: the bench display name of
    BFS in the same frame) and the T2 semantic seed (exp6 wording via exp27 prompts, W1), each with its padding twin."""
    import json as _json
    import prompts_v4 as P4
    from cfg import INPUTS, cap_first, read_json, sha256_text
    out = []
    fp = read_json(INPUTS / "exp8" / "prompts" / "frozen_prompts.json")
    spec2 = fp["spec"]["t2"]
    seg = fp["tasks"]["t2"]["forced"]["bf_spfa"]["paraphrases"][0]["segment"]
    sp10 = read_json(next(d for d in (INPUTS / "exp11" / "bench").iterdir() if d.name.startswith("T10_")) / "spec.json")
    disp = {c["mode"]: c["display_name"] for c in sp10["catalogue"]}
    for task, segment, spec, Y in (("T2", seg, spec2, "bf_spfa"),
                                   ("T10", f"Implement {disp['bfs']} for this task.", sp10["spec_text"], "bfs")):
        ids = P4.chat_ids(tok, cap_first(segment) + "\n\n" + spec)
        p0, p1, se = P4.positions(tok, ids, spec)
        rec = {"task": task, "w": "F", "kind": "forced", "ids": ids, "P": len(ids), "p0": p0, "p1": p1,
               "spec_end": se, "cond": None, "R": len(ids) - 1, "segment": segment, "Y": Y,
               "prompt_sha256": sha256_text(_json.dumps(ids))}
        out += [rec, pad_record(tok, rec, "forced_pad")]
    rows27 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "prompts" / "prompts.jsonl")}
    sem = dict(rows27[("T2", "W1", "semseed")])
    sem.update({"kind": "semseed", "w": "S", "cond": None, "R": sem["P"] - 1, "Y": None})
    out += [sem, pad_record(tok, sem, "semseed_pad")]
    return out


def stage_ext(model: Any, tok: Any, P6: dict) -> None:
    from cfg6 import N_W4
    recs = ext_prompts(tok)
    write_json(RESULTS_DIR / "ext_prompts.json", [{k: v for k, v in r.items() if k != "ids"} for r in recs])
    pairs = [(recs[0], recs[1], "F"), (recs[2], recs[3], "F"), (recs[4], recs[5], "S")]
    for src_rec, pad_rec, tag in pairs:
        task = src_rec["task"]
        if past_deadline():
            break
        src = Prompt(model, src_rec)
        pad = Prompt(model, pad_rec)
        assert src.P == pad.P and src.p1 == pad.p1 and src_rec["ids"][src.p1:] == pad_rec["ids"][pad.p1:]
        pre_x = prefill6(model, pad.ids, edits=set_rows_edit(pad.idx[pad.iS], {l: src.H[l][src.iS]
                                                                            for l in ALL_BLOCKS}))
        nm = "FORCED" if tag == "F" else "SEED"
        specs = []
        for s in N30:
            for arm, pr, pre, kind in ((nm, src, src.pre, src_rec["kind"]), (f"{nm}PAD", pad, pad.pre, pad_rec["kind"]),
                                       (f"{nm}X_0-35", pad, pre_x, pad_rec["kind"])):
                if sample_id(task, arm, s) not in done_ids():
                    specs.append(base_spec(task, arm, "EXT", s, pr, kind, pre=pre, band="0-35",
                                           source=src_rec["kind"]))
        run_batches(model, tok, task, specs, f"EXT:{task}:{nm}")
        src.H.clear()
        pad.H.clear()
        del src, pad, pre_x
        torch.cuda.empty_cache()
    # W4 template at band 0-35, N = 10 (reported separately)
    for task in ("T2", "T03", "T10"):
        if past_deadline():
            break
        ctx = TaskW(model, P6, task, "W4", ("twin", "ban"))
        tw, bn = ctx.pr["twin"], ctx.pr["ban"]
        pre_x = prefill6(model, tw.ids, edits=set_rows_edit(tw.idx[tw.iS], {l: bn.H[l][bn.iS] for l in ALL_BLOCKS}))
        specs = []
        for s in N_W4:
            for arm, pr, pre, kind in (("TWIN_W4", tw, tw.pre, "twin"), ("BAN_W4", bn, bn.pre, "ban"),
                                       ("X_0-35_W4", tw, pre_x, "twin")):
                if sample_id(task, arm, s) not in done_ids():
                    specs.append(base_spec(task, arm, "W4", s, pr, kind, pre=pre, band="0-35"))
        run_batches(model, tok, task, specs, f"W4:{task}")
        ctx.free()


# ------------------------------------------------------------------------------------------------ main
def hardware(info: dict[str, Any]) -> None:
    import transformers

    hw = {"gpu": torch.cuda.get_device_name(0), "total_vram_GB": info["total_vram_GB"],
          "free_vram_after_load_GB": info["free_vram_after_GB"], "driver_cuda": torch.version.cuda,
          "torch": torch.__version__, "transformers": transformers.__version__, "precision": PRECISION6,
          "cpu_embedding": info["cpu_embedding"], "engine": ENGINE6, "batch_sizes": BATCH6,
          "max_new": {t: max_new6(t) for t in TASKS6}, "utc": utc_now()}
    if not (PRED_DIR / "hardware.json").exists():
        write_json(PRED_DIR / "hardware.json", hw)
    STATE["gpu"] = hw["gpu"]


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages")
    ap.add_argument("--deadline-min", type=float, default=1e9)
    ap.add_argument("--tasks", default=",".join(TASKS6))
    ap.add_argument("--st-groups", default="")
    args = ap.parse_args()
    setup_logging("gpu6")
    STATE["deadline"] = time.time() + 60 * args.deadline_min
    STATES_DIR.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    tok, model, info = load_model_bf16()
    hardware(info)
    P6 = load_prompts6()
    tasks = tuple(t for t in args.tasks.split(",") if t)
    for st in args.stages.split(","):
        t0 = time.time()
        logger.info(f"=== stage {st} ===")
        if st == "utest":
            stage_utest(model, tok, P6)
        elif st == "twins":
            stage_twins_A(model, tok, P6, tasks, True, False)
        elif st == "stageA":
            stage_twins_A(model, tok, P6, tasks, True, True)
        elif st == "st":
            stage_st(model, tok, P6, [g for g in args.st_groups.split(",") if g] or None)
        elif st == "stcore":
            stage_st(model, tok, P6, ["core"])
        elif st == "stext":
            stage_st(model, tok, P6, ["energy_a2", "a8_spec", "a8_RC", "energy_a4"])
        elif st == "ext":
            stage_ext(model, tok, P6)
        elif st == "top5push":
            stage_top5(model, tok, P6, with_ban=False)
        elif st == "dmd":
            stage_dmd(model, tok, P6)
        elif st == "top5":
            stage_top5(model, tok, P6)
        else:
            raise ValueError(st)
        write_json(RESULTS_DIR / f"stage_{st}_done.json", {"seconds": round(time.time() - t0, 1), "utc": utc_now()})
        logger.info(f"=== stage {st} done in {time.time() - t0:.0f}s ===")


if __name__ == "__main__":
    main()
