#!/usr/bin/env python3
"""GPU processes B (norms + matched-norm random directions + HF twin control) and D (band-patch positive control),
HF transformers, bf16 Qwen3-8B, SDPA attention.

Displacement patch: forward hooks on model.model.layers[l], l = 12..23.  During the prefill (hidden length == prompt
length) the output at the task-spec positions is overwritten with h0_l[spec] + delta_l[spec], where h0 is the clean
twin_w prefill state; the displacement at every band layer is therefore exactly delta (no compounding across layers)
and generated tokens are never touched.
B: delta = norm[l][j] * u_{k,l} (u = seeded isotropic unit direction, same for every task and position; norm =
   template-mean ||h(ban_w) - h(twin_w)|| at layer l, spec position j).
D: delta = h_l,j(ban_w) - h_l,j(twin_w) (template-matched: the ban's own task-spec states).
Sampling: common-random-numbers inverse-CDF sampler (adapted from exp8 engine.sample): one uniform per (row, step),
token = first vocabulary index whose float64 CDF >= u; T = 1, no top-k/top-p (explicit, never the model's
generation_config defaults).
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from common import (BAND, DECODING, DEFAULTS, EOS_IDS, IM_END, MAX_NEW, MODEL_ID, N_BANDPATCH_PER_T, N_HF_TWIN_PER_T,
                    N_RAND_DIRS, N_RAND_PER_T, PROMPTS, RESULTS, TASK_ORDER, WS, model_path, read_json, stable_seed,
                    timing_log, utc_now, write_json)
from vllm_stage import Store

TENS = RESULTS / "tensors"


def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_path())
    model = AutoModelForCausalLM.from_pretrained(model_path(), dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0})
    model.eval()
    torch.cuda.set_per_process_memory_fraction(0.95, 0)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"HF model loaded in {time.time() - t0:.0f}s; free VRAM {free / 1e9:.1f}/{total / 1e9:.1f} GB")
    return tok, model


def rand_dir(k: int, l: int, d: int = 4096) -> np.ndarray:
    s = int(hashlib.sha256(f"rand{k}|L{l}".encode()).hexdigest()[:16], 16)
    v = np.random.default_rng(s).standard_normal(d)
    return (v / np.linalg.norm(v)).astype(np.float32)


# ------------------------------------------------------------------------------------------------ hooks
class Patcher:
    """Holds per-layer replacement tensors for the spec positions of the rows being patched."""

    def __init__(self, model):
        self.model = model
        self.handles = []
        self.active = False
        self.P = None
        self.span = None
        self.rows = None  # LongTensor of row indices to patch (others untouched)
        self.target: dict[int, torch.Tensor] = {}  # l -> [n_rows, n_spec, d] (bf16) replacement states
        self.capture: dict[int, torch.Tensor] | None = None

    def _hook(self, l: int):
        def fn(module, inputs, output):
            hs = output[0] if isinstance(output, tuple) else output
            if self.active and hs.shape[1] == self.P and l in self.target:
                s, e = self.span
                hs[self.rows, s:e, :] = self.target[l]
            if self.capture is not None and hs.shape[1] == self.P:
                self.capture[l] = hs.detach().clone()  # after patching: the state the next layer actually reads
            return output
        return fn

    def install(self, layers: list[int]):
        for l in layers:
            self.handles.append(self.model.model.layers[l].register_forward_hook(self._hook(l)))

    def remove(self):
        for h in self.handles:
            h.remove()
        self.handles = []


@torch.no_grad()
def states(model, patcher: Patcher, ids: list[int], layers: list[int]) -> dict[int, torch.Tensor]:
    """Prompt-only forward; returns {l: output of layer l [P, d] (bf16, GPU)}."""
    from transformers.cache_utils import DynamicCache

    patcher.P = len(ids)
    patcher.capture = {}
    # same code path as the sampling prefill (DynamicCache, use_cache=True) so a zero patch is numerically exact
    model.model(input_ids=torch.tensor([ids], device=model.device), past_key_values=DynamicCache(), use_cache=True)
    cap = {l: patcher.capture[l][0] for l in layers}
    patcher.capture = None
    return cap


@torch.no_grad()
def prefill(model, patcher: Patcher, ids: list[int], B: int):
    from transformers.cache_utils import DynamicCache

    patcher.P = len(ids)
    cache = DynamicCache()
    out = model.model(input_ids=torch.tensor([ids] * B, device=model.device), past_key_values=cache, use_cache=True)
    logits = model.lm_head(out.last_hidden_state[:, -1]).double()
    return cache, logits


@torch.no_grad()
def decode(model, cache, logits: torch.Tensor, P: int, U: np.ndarray, max_new: int = MAX_NEW) -> list[dict]:
    """exp8-style CRN sampler with pruning of finished rows."""
    B = logits.shape[0]
    dev = model.device
    Ut = torch.tensor(U[:, :max_new], dtype=torch.float64, device=dev)
    alive = list(range(B))
    toks: list[list[int]] = [[] for _ in range(B)]
    finish = ["length"] * B
    step = 0
    while True:
        probs = torch.softmax(logits, dim=-1)
        cdf = probs.cumsum(dim=-1)
        cdf = cdf / cdf[:, -1:]
        nxt = torch.searchsorted(cdf, Ut[alive, step][:, None]).squeeze(-1).clamp_(max=probs.shape[-1] - 1).tolist()
        keep = []
        for j, (r, t) in enumerate(zip(alive, nxt)):
            toks[r].append(int(t))
            if t in EOS_IDS:
                finish[r] = "stop"
            elif len(toks[r]) < max_new:
                keep.append(j)
        if not keep:
            break
        if len(keep) < len(alive):
            idx = torch.tensor(keep, device=dev)
            cache.batch_select_indices(idx)
            alive = [alive[j] for j in keep]
            nxt = [nxt[j] for j in keep]
        inp = torch.tensor(nxt, device=dev)[:, None]
        pos = torch.full((len(alive), 1), P + step, device=dev, dtype=torch.long)
        h = model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    return [{"token_ids": toks[r], "finish_reason": finish[r]} for r in range(B)]


def u_stream(*key: Any, n: int = MAX_NEW) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed("u", *key))).random(n)


def run_batch(model, tok, patcher: Patcher, ids: list[int], span: list[int], rows: list[dict],
              targets: dict[int, torch.Tensor] | None, patch_rows: list[int]) -> list[dict]:
    """rows share one prompt.  targets: l -> [len(patch_rows), n_spec, d] replacement states (None = no patch)."""
    B = len(rows)
    U = np.stack([u_stream(r["task"], r["arm"], r["template"], r["idx"]) for r in rows])
    bs = B
    while True:
        try:
            out = []
            for s0 in range(0, B, bs):
                sub = list(range(s0, min(B, s0 + bs)))
                pr = [i - s0 for i in patch_rows if s0 <= i < s0 + bs]
                if targets is not None and pr:
                    sel = [patch_rows.index(i) for i in patch_rows if s0 <= i < s0 + bs]
                    patcher.target = {l: v[sel] for l, v in targets.items()}
                    patcher.rows = torch.tensor(pr, device=model.device)
                    patcher.span = span
                    patcher.active = True
                cache, logits = prefill(model, patcher, ids, len(sub))
                patcher.active = False
                patcher.target = {}
                out += decode(model, cache, logits, len(ids), U[sub])
                del cache, logits
            break
        except torch.cuda.OutOfMemoryError:
            patcher.active = False
            patcher.target = {}
            torch.cuda.empty_cache()
            gc.collect()
            if bs == 1:
                raise
            bs = max(1, bs // 2)
            logger.warning(f"OOM: batch -> {bs}")
    res = []
    for r, o in zip(rows, out):
        body = [t for t in o["token_ids"] if t not in EOS_IDS]
        res.append({**r, "token_ids": o["token_ids"], "text": tok.decode(body, skip_special_tokens=True),
                    "finish_reason": o["finish_reason"], "n_tokens": len(body), "engine": "hf", "model": MODEL_ID,
                    "decoding": DECODING, "utc": utc_now()})
    return res


# ------------------------------------------------------------------------------------------------ process B
@torch.no_grad()
def norms_for_task(model, patcher: Patcher, task: str, prompt_ids: dict) -> dict[str, Any]:
    per_t, mean_vecs = [], []
    for w in WS:
        b = prompt_ids[f"{task}|ban|{w}"]
        tw = prompt_ids[f"{task}|twin|{w}"]
        assert b["spec_span"] == tw["spec_span"]
        s, e = b["spec_span"]
        hb = states(model, patcher, b["ids"], BAND)
        ht = states(model, patcher, tw["ids"], BAND)
        diffs = torch.stack([(hb[l][s:e].float() - ht[l][s:e].float()) for l in BAND])  # [12, n_spec, d]
        per_t.append(diffs.norm(dim=-1).cpu().numpy())
        mean_vecs.append(diffs.mean(dim=1).cpu().numpy())
        del hb, ht, diffs
    norms_t = np.stack(per_t)  # [5, 12, n_spec]
    out = {"norm": norms_t.mean(0), "norm_per_template": norms_t, "mean_disp": np.stack(mean_vecs).mean(0)}
    np.savez_compressed(TENS / f"norms_{task}.npz", norm=out["norm"].astype(np.float32),
                        norm_per_template=norms_t.astype(np.float32), mean_disp=out["mean_disp"].astype(np.float16),
                        layers=np.array(BAND))
    return out


@torch.no_grad()
def hook_tests(model, patcher: Patcher, task: str, prompt_ids: dict, norm: np.ndarray) -> dict[str, Any]:
    """T5 (a)-(d) on the first task."""
    tw = prompt_ids[f"{task}|twin|W1"]
    ids, (s, e) = tw["ids"], tw["spec_span"]
    res: dict[str, Any] = {"task": task}
    layers_all = list(range(len(model.model.layers)))
    h0 = states(model, patcher, ids, layers_all)
    clean_cache, clean_logits = prefill(model, patcher, ids, 1)
    del clean_cache
    # (a) zero-norm patch
    patcher.target = {l: h0[l][s:e][None] for l in BAND}
    patcher.rows = torch.tensor([0], device=model.device)
    patcher.span = [s, e]
    patcher.active = True
    c, zl = prefill(model, patcher, ids, 1)
    patcher.active = False
    del c
    res["a_zero_patch_max_abs_logit_diff"] = float((zl - clean_logits).abs().max())
    # (b)+(c) random direction k=1
    U1 = {l: torch.tensor(rand_dir(1, l), device=model.device) for l in BAND}
    nrm = {l: torch.tensor(norm[i], device=model.device, dtype=torch.float32) for i, l in enumerate(BAND)}
    tgt = {l: (h0[l][s:e].float() + nrm[l][:, None] * U1[l][None, :]).to(torch.bfloat16)[None] for l in BAND}
    patcher.target, patcher.active = tgt, True
    patcher.capture = {}
    patcher.P = len(ids)
    from transformers.cache_utils import DynamicCache
    model.model(input_ids=torch.tensor([ids], device=model.device), past_key_values=DynamicCache(), use_cache=True)
    cap = patcher.capture
    patcher.capture, patcher.active = None, False
    pre = [l for l in layers_all if l < BAND[0]]
    res["b_max_abs_diff_before_band"] = float(max((cap[l][0].float() - h0[l].float()).abs().max() for l in pre))
    l0 = BAND[0]
    nonspec = torch.ones(len(ids), dtype=torch.bool)
    nonspec[s:e] = False
    res["b_max_abs_diff_layer12_nonspec"] = float((cap[l0][0][nonspec].float() - h0[l0][nonspec].float()).abs().max())
    rel, rel_all = [], []
    for i, l in enumerate(BAND):
        meas = (cap[l][0][s:e].float() - h0[l][s:e].float()).norm(dim=-1).cpu().numpy()
        r_ = np.abs(meas - norm[i]) / np.maximum(norm[i], 1e-6)
        rel.append(float(np.max(r_)))
        rel_all.append(r_)
    rel_all = np.concatenate(rel_all)
    res["c_max_rel_norm_error"] = max(rel)
    res["c_median_rel_norm_error"] = float(np.median(rel_all))
    res["c_share_positions_within_1pct"] = float(np.mean(rel_all <= 0.01))
    # bf16 representational bound: rounding of h0 + delta to bf16 (2^-8 relative per element)
    bound = []
    for i, l in enumerate(BAND):
        x = (h0[l][s:e].float() + nrm[l][:, None] * U1[l][None, :])
        err = (x.to(torch.bfloat16).float() - x).norm(dim=-1).cpu().numpy()
        bound.append(float(np.max(err / np.maximum(norm[i], 1e-6))))
    res["c_bf16_rounding_rel_error_bound"] = max(bound)
    res["c_pass"] = res["c_max_rel_norm_error"] <= max(0.01, 1.05 * res["c_bf16_rounding_rel_error_bound"])
    # (d) batch of 20 rows with per-row vectors vs 20 single-row runs: first sampled token (CRN)
    U20 = np.random.default_rng(0).random(20)
    dirs = [1 + (i % 2) for i in range(20)]
    Uk = {k: {l: torch.tensor(rand_dir(k, l), device=model.device) for l in BAND} for k in (1, 2)}
    tg = {l: torch.stack([(h0[l][s:e].float() + nrm[l][:, None] * Uk[dirs[i]][l][None, :]).to(torch.bfloat16)
                          for i in range(20)]) for l in BAND}
    patcher.target, patcher.rows, patcher.active = tg, torch.arange(20, device=model.device), True
    c, bl = prefill(model, patcher, ids, 20)
    patcher.active = False
    del c
    match, maxd = 0, 0.0
    for i in range(20):
        patcher.target = {l: tg[l][i:i + 1] for l in BAND}
        patcher.rows, patcher.active = torch.tensor([0], device=model.device), True
        c, sl = prefill(model, patcher, ids, 1)
        patcher.active = False
        del c
        maxd = max(maxd, float((sl[0] - bl[i]).abs().max()))
        def first(lg, u):
            p = torch.softmax(lg, -1)
            cdf = p.cumsum(-1)
            cdf = cdf / cdf[-1]
            return int(torch.searchsorted(cdf, torch.tensor([u], dtype=torch.float64, device=lg.device)))
        match += first(sl[0], U20[i]) == first(bl[i], U20[i])
    patcher.target = {}
    res["d_first_token_match_20"] = match
    res["d_max_abs_logit_diff_batch_vs_single"] = maxd
    res["a_pass"] = res["a_zero_patch_max_abs_logit_diff"] <= max(1e-3, res["d_max_abs_logit_diff_batch_vs_single"])
    res["all_pass"] = bool(res["a_pass"] and res["b_max_abs_diff_before_band"] == 0.0
                           and res["b_max_abs_diff_layer12_nonspec"] == 0.0 and res["c_pass"])
    del h0
    torch.cuda.empty_cache()
    return res


def stage_b(sub: str = "", tasks: list[str] | None = None, n_rand: int = N_RAND_PER_T,
            n_ctrl: int = N_HF_TWIN_PER_T, workers: int = 10, batch: int = 20) -> None:
    from labelpool import Labeller

    tasks = tasks or TASK_ORDER
    TENS.mkdir(parents=True, exist_ok=True)
    store = Store(sub)
    prompt_ids = read_json(PROMPTS / "prompt_ids.json")
    tok, model = load_model()
    patcher = Patcher(model)
    patcher.install(list(range(len(model.model.layers))))
    lab = Labeller(workers=workers)
    dirs = {k: {l: torch.tensor(rand_dir(k, l), device=model.device) for l in BAND} for k in range(1, N_RAND_DIRS + 1)}
    done_ids = {r["sample_id"] for r in store.raw_rows("rand")} | {r["sample_id"] for r in store.raw_rows("hf_twin")}
    futs = []
    norm_summary = {}
    for ti, t in enumerate(tasks):
        t0 = time.time()
        nm = norms_for_task(model, patcher, t, prompt_ids)
        norm = nm["norm"]
        norm_summary[t] = {"mean_norm_per_layer": nm["norm"].mean(1).tolist(),
                           "n_spec": int(nm["norm"].shape[1])}
        if ti == 0:
            ht = hook_tests(model, patcher, t, prompt_ids, norm)
            write_json(RESULTS / f"hook_unit_tests{('_' + sub) if sub else ''}.json", ht)
            logger.info(f"hook unit tests: {ht}")
            if not ht["all_pass"]:
                raise RuntimeError(f"hook unit tests failed: {ht}")
        nrm = {l: torch.tensor(norm[i], device=model.device, dtype=torch.float32) for i, l in enumerate(BAND)}
        rand_rows, ctrl_rows = [], []
        for w in WS:
            tw = prompt_ids[f"{t}|twin|{w}"]
            ids, span = tw["ids"], tw["spec_span"]
            s, e = span
            h0 = states(model, patcher, ids, BAND)
            reqs = []
            for k in range(1, N_RAND_DIRS + 1):
                for i in range(n_rand):
                    arm = f"rand{k}"
                    reqs.append({"sample_id": f"{t}:{arm}:{w}:{i}", "task": t, "arm": arm, "template": w, "idx": i,
                                 "seed": stable_seed(t, arm, w, i), "prompt_key": f"{t}|twin|{w}", "direction": k})
            for i in range(n_ctrl):
                reqs.append({"sample_id": f"{t}:hf_twin:{w}:{i}", "task": t, "arm": "hf_twin", "template": w, "idx": i,
                             "seed": stable_seed(t, "hf_twin", w, i), "prompt_key": f"{t}|twin|{w}", "direction": 0})
            reqs = [r for r in reqs if r["sample_id"] not in done_ids]
            for b0 in range(0, len(reqs), batch):
                rows = reqs[b0:b0 + batch]
                prow = [i for i, r in enumerate(rows) if r["direction"] > 0]
                tg = None
                if prow:
                    tg = {l: torch.stack([(h0[l][s:e].float() + nrm[l][:, None] * dirs[rows[i]["direction"]][l][None, :]
                                           ).to(torch.bfloat16) for i in prow]) for l in BAND}
                tb = time.time()
                res = run_batch(model, tok, patcher, ids, span, rows, tg, prow)
                timing_log("B", "rand+ctrl", len(rows), time.time() - tb,
                           {"task": t, "max_len": max(r["n_tokens"] for r in res)})
                for r in res:
                    (rand_rows if r["arm"] != "hf_twin" else ctrl_rows).append(r)
                del tg
            del h0
            torch.cuda.empty_cache()
        from common import write_jsonl
        write_jsonl(store.raw / "rand.jsonl", rand_rows, mode="a")
        write_jsonl(store.raw / "hf_twin.jsonl", ctrl_rows, mode="a")
        futs.append(lab.submit(rand_rows + ctrl_rows, f"rand+ctrl {t}"))
        logger.info(f"{t}: {len(rand_rows)} random-direction + {len(ctrl_rows)} HF-twin samples in "
                    f"{time.time() - t0:.0f}s")
    write_json(RESULTS / f"norms_summary{('_' + sub) if sub else ''}.json", norm_summary)
    labs = []
    for fu in futs:
        labs += fu.result()
    from common import write_jsonl
    write_jsonl(store.lab / "rand.jsonl", [r for r in labs if r["arm"] != "hf_twin"], mode="a")
    write_jsonl(store.lab / "hf_twin.jsonl", [r for r in labs if r["arm"] == "hf_twin"], mode="a")
    patcher.remove()
    logger.info(f"process B done; judge spend ${lab.spent():.4f}")


# ------------------------------------------------------------------------------------------------ process D
def stage_d(sub: str = "", tasks: list[str] | None = None, n_per: int = N_BANDPATCH_PER_T, workers: int = 10) -> None:
    from labelpool import Labeller

    from common import write_jsonl

    tasks = tasks or TASK_ORDER
    store = Store(sub)
    prompt_ids = read_json(PROMPTS / "prompt_ids.json")
    tok, model = load_model()
    patcher = Patcher(model)
    patcher.install(BAND)
    lab = Labeller(workers=workers)
    done_ids = {r["sample_id"] for r in store.raw_rows("bandpatch")}
    futs = []
    for t in tasks:
        t0 = time.time()
        rows_t = []
        for w in WS:
            b = prompt_ids[f"{t}|ban|{w}"]
            tw = prompt_ids[f"{t}|twin|{w}"]
            s, e = tw["spec_span"]
            hb = states(model, patcher, b["ids"], BAND)
            reqs = [{"sample_id": f"{t}:bandpatch:{w}:{i}", "task": t, "arm": "bandpatch", "template": w, "idx": i,
                     "seed": stable_seed(t, "bandpatch", w, i), "prompt_key": f"{t}|twin|{w}"} for i in range(n_per)]
            reqs = [r for r in reqs if r["sample_id"] not in done_ids]
            if not reqs:
                continue
            # replacement = clean twin state + (ban - twin) = the ban's own spec state, at every band layer
            tg = {l: hb[l][s:e][None].expand(len(reqs), -1, -1).contiguous() for l in BAND}
            res = run_batch(model, tok, patcher, tw["ids"], [s, e], reqs, tg, list(range(len(reqs))))
            timing_log("D", "bandpatch", len(reqs), time.time() - t0, {"task": t})
            rows_t += res
            del hb, tg
            torch.cuda.empty_cache()
        write_jsonl(store.raw / "bandpatch.jsonl", rows_t, mode="a")
        futs.append(lab.submit(rows_t, f"bandpatch {t}"))
        logger.info(f"{t}: {len(rows_t)} band-patch samples in {time.time() - t0:.0f}s")
    labs = []
    for fu in futs:
        labs += fu.result()
    write_jsonl(store.lab / "bandpatch.jsonl", labs, mode="a")
    patcher.remove()
    logger.info(f"process D done; judge spend ${lab.spent():.4f}")


if __name__ == "__main__":
    from common import detect_cpus, setup_logging

    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["B", "D"])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--tasks", default=None)
    a = ap.parse_args()
    setup_logging(f"gpu_{a.stage}{'_smoke' if a.smoke else ''}")
    workers = max(4, detect_cpus() - 3)
    tasks = a.tasks.split(",") if a.tasks else None
    if a.stage == "B":
        if a.smoke:
            stage_b("smoke", ["T03"], n_rand=2, n_ctrl=2, workers=workers)
        else:
            stage_b(tasks=tasks, workers=workers)
    else:
        if a.smoke:
            stage_d("smoke", ["T03"], n_per=2, workers=workers)
        else:
            stage_d(tasks=tasks, workers=workers)
