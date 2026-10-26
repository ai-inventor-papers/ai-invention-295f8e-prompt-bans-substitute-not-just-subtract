#!/usr/bin/env python3
"""GPU process of step K (instruct model, bf16): hardware record, memory probe, unit tests U1-U6, S0 twins, S1 2x2
(+ D5), S2 profiles and S3's plan-noise cells at D*. Resumable by row key <task>|<template>|<arm>|<sample_id>.

Engine and sampler are the vendored exp22 ones run in bf16 (= exp29 engine d numerics): engine.load_model(fp8=False),
engine.prefill with block-output edit hooks, engine4.sample (exact inverse-CDF CRN draw, prune=False, constant batch
shape, fence stop). Every batch holds exactly B rows of ONE (task, template) and shares the twin's prompt ids, so every
row runs on the shared-prefix path (no left padding). Designs of a (task, template) are interleaved by slot inside the
batches; the last batch of a template is padded with fresh TWIN slots (k >= 100).

EDIT (TARGET, prefill only): at blocks 12-23 and the task-spec positions S = [p1, spec_end) of the twin prompt,
h <- h + (alpha * n[l, p] - (h - h_twin) . u) u (vendored hooks4.make_edits_v4); for the S2 top/rest profiles the
cells outside the profile are NOT edited (torch.where keeps the block output bitwise).

Realised displacement per pushed row (against the template's clean twin, all 36 blocks): norm of the spec-mean
displacement, mean per-position norm over S, norm at the read position R = P - 1, and at generated position 1
(the twin's first sampled token of the slot teacher-forced under both caches, one extra forward step).

usage: .venv/bin/python src/gen_k.py [stages...]   (default: all)  stages: tests s0 s1 d5 s2 s3pn diag9101
"""

from __future__ import annotations

import gc
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import (ALL_BLOCKS, CACHE, DEFAULTS, EDIT_BLOCKS, FENCE, K10, K20, LABELS, MAX_NEW, MODEL_ID,  # noqa: E402
                   MODEL_REVISION, PRECISION, PRED, RAW, REALISED, RESULTS, TEMPLATES, append_jsonl, parse_arm,
                   read_json, read_jsonl, row_key, stable_seed, utc_now, write_json)
import k_units as KU  # noqa: E402

import cfg4  # noqa: E402,F401  (vendored exp22; puts src_base on the path)
from engine import block_hooks, build_cache, clear_act_cache, load_model, prefill, u_stream  # noqa: E402
from engine import _inverse_cdf  # noqa: E402
from engine4 import sample as sample4  # noqa: E402
from hooks4 import make_edits_v4  # noqa: E402

GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
PROMPTS4 = K.V22 / "prompts" / "prompts4.jsonl"
STATE = RESULTS / "gpu_state.json"
TIMING = RESULTS / "timing.jsonl"
UNIT_TESTS = RESULTS / "unit_tests_gpu.json"
DISP_DIR = CACHE / "disp"
DISP_DIR.mkdir(parents=True, exist_ok=True)
PAD_K0 = 100


# ------------------------------------------------------------------------------------------------ prompts / edits
def load_prompts() -> dict[str, dict[str, Any]]:
    out = {}
    with open(PROMPTS4) as f:
        for line in f:
            r = json.loads(line)
            if r["kind"] == "twin":
                out[r["pid"]] = r
    return out


def make_edits_masked(a: int, b: int, u: torch.Tensor, M: dict[int, torch.Tensor], h_ref: dict[int, torch.Tensor],
                      mask: dict[int, torch.Tensor]) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """TARGET edit at the cells of `mask` only (make_edits_v4 arithmetic); other cells keep the block output."""
    edits = {}
    for l in EDIT_BLOCKS:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, a:b].float()
            comp = (hs - h_ref[l]) @ u
            coef = M[l] - comp
            new = hs + coef[..., None] * u
            new = torch.where(mask[l][None, :, None], new, hs)
            h = h.clone()
            h[:, a:b] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


def first_token(r_logits: torch.Tensor, u0: float) -> int:
    probs = torch.softmax(r_logits.double()[None] / 1.0, dim=-1)
    return int(_inverse_cdf(probs, torch.tensor([u0], dtype=torch.float64, device=r_logits.device))[0])


# ------------------------------------------------------------------------------------------------ task context
class TaskCtxK:
    def __init__(self, model: Any, prompts: dict[str, dict[str, Any]], task: str):
        self.model, self.task, self.pr = model, task, prompts
        self.dev = model.device
        self.clean: dict[str, dict[str, Any]] = {}
        self.n_abs = KU.u_abs(task)
        self.profiles = KU.profile_masks(self.n_abs, task)
        self.g1_twin: dict[tuple[str, int], torch.Tensor] = {}

    def prompt(self, w: str) -> dict[str, Any]:
        return self.pr[f"{self.task}|twin|-|{w}|-"]

    def _capture(self, a: int, b: int, P: int, twin_S: dict[int, torch.Tensor] | None):
        cap: dict[str, dict[int, Any]] = {"S": {}, "smean": {}, "R": {}, "spos": {}}
        keep = set(EDIT_BLOCKS) | {35}

        def mk(l: int):
            def g(h: torch.Tensor) -> None:
                hs = h[0, a:b].float()
                if twin_S is None or l in keep:
                    cap["S"][l] = hs.clone()
                cap["smean"][l] = hs.mean(0)
                cap["R"][l] = h[0, P - 1].float().clone()
                if twin_S is not None:
                    cap["spos"][l] = float((hs - twin_S[l]).norm(dim=-1).mean())
            return g
        return cap, {l: mk(l) for l in ALL_BLOCKS}

    def twin(self, w: str) -> dict[str, Any]:
        if w not in self.clean:
            p = self.prompt(w)
            a, b, P = p["p1"], p["spec_end"], p["P"]
            assert b - a == self.n_abs.shape[1], (self.task, w, b - a, self.n_abs.shape)
            cap, hooks = self._capture(a, b, P, None)
            pre = prefill(self.model, p["ids"], capture=hooks)
            n_bf_t = {l: cap["S"][l].norm(dim=-1) * KU.r_at(l) for l in EDIT_BLOCKS}   # exp27 Ctx.banfree
            n_bf = np.stack([n_bf_t[l].cpu().numpy() for l in EDIT_BLOCKS]).astype(np.float32)
            self.clean[w] = {"pre": pre, "S": cap["S"], "smean": cap["smean"], "R": cap["R"], "a": a, "b": b,
                             "P": P, "prompt": p, "U_bf": n_bf, "U_bf_star": KU.bf_star(n_bf, self.n_abs),
                             "h_norm": np.stack([cap["S"][l].norm(dim=-1).cpu().numpy() for l in EDIT_BLOCKS])}
        return self.clean[w]

    def unit(self, w: str, name: str) -> tuple[np.ndarray, np.ndarray | None]:
        tw = self.twin(w)
        if name == "U_abs":
            return self.n_abs, None
        if name == "U_bf":
            return tw["U_bf"], None
        if name == "U_bf_star":
            return tw["U_bf_star"], None
        pr = self.profiles[name]
        return pr["unit"], (None if name == "P_shuf" else pr["mask"])

    def gen1(self, pre: dict[str, Any], tok1: int, P: int) -> torch.Tensor:
        """Block outputs (36 x D, fp32) at generated position 1 with input token tok1 under the prefill's cache."""
        cache = build_cache(pre["kv"])
        got: dict[int, torch.Tensor] = {}

        def mk(l: int):
            def g(h: torch.Tensor) -> None:
                got[l] = h[0, -1].float().clone()
            return g
        inp = torch.tensor([[tok1]], device=self.dev)
        pos = torch.tensor([[P]], device=self.dev)
        clear_act_cache()
        with torch.no_grad(), block_hooks(self.model, None, {l: mk(l) for l in ALL_BLOCKS}):
            self.model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=True)
        del cache
        return torch.stack([got[l] for l in ALL_BLOCKS])

    def twin_gen1(self, w: str, tok1: int) -> torch.Tensor:
        key = (w, tok1)
        if key not in self.g1_twin:
            tw = self.twin(w)
            self.g1_twin[key] = self.gen1(tw["pre"], tok1, tw["P"])
        return self.g1_twin[key]

    def edited_prefill(self, w: str, u: np.ndarray, unit: np.ndarray, alpha: float, mask: np.ndarray | None,
                       u0: float, want_gen1: bool = True) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        tw = self.twin(w)
        a, b, P = tw["a"], tw["b"], tw["P"]
        ut = torch.tensor(u, dtype=torch.float32, device=self.dev)
        nt = torch.tensor(unit, dtype=torch.float32, device=self.dev)
        U = {l: ut for l in EDIT_BLOCKS}
        M = {l: alpha * nt[j] for j, l in enumerate(EDIT_BLOCKS)}
        h_ref = {l: tw["S"][l] for l in EDIT_BLOCKS}
        if mask is None:
            edits = make_edits_v4("TARGET", a, b, U, M, h_ref)
        else:
            mk = {l: torch.tensor(mask[j], dtype=torch.bool, device=self.dev) for j, l in enumerate(EDIT_BLOCKS)}
            edits = make_edits_masked(a, b, ut, M, h_ref, mk)
        cap, hooks = self._capture(a, b, P, tw["S"])
        pre = prefill(self.model, tw["prompt"]["ids"], edits=edits, capture=hooks)
        relerr, masked_max = {}, 0.0
        for j, l in enumerate(EDIT_BLOCKS):
            d = cap["S"][l] - tw["S"][l]
            comp = d @ ut
            tgt = M[l]
            err = (comp - tgt).abs() / tgt.abs().clamp(min=1e-6)
            if mask is None:
                relerr[l] = float(err.mean()) if alpha else float(comp.abs().max())
            else:
                m = torch.tensor(mask[j], dtype=torch.bool, device=self.dev)
                relerr[l] = float(err[m].mean()) if alpha else float(comp[m].abs().max())
                if l == EDIT_BLOCKS[0]:
                    masked_max = float(d[~m].abs().max()) if (~m).any() else 0.0
        sm = torch.stack([cap["smean"][l] - tw["smean"][l] for l in ALL_BLOCKS])
        dR = torch.stack([cap["R"][l] - tw["R"][l] for l in ALL_BLOCKS])
        rec = {"spec_mean": [round(float(x), 4) for x in sm.norm(dim=-1)],
               "spec_pos": [round(cap["spos"][l], 4) for l in ALL_BLOCKS],
               "R": [round(float(x), 4) for x in dR.norm(dim=-1)],
               "rel_err_along_u": {str(l): round(v, 7) for l, v in relerr.items()},
               "rel_err_mean": float(np.mean(list(relerr.values()))),
               "rel_err_max": float(np.max(list(relerr.values()))),
               "masked_b12_max_abs_disp": masked_max if mask is not None else None}
        vec = {"smean23": sm[23].cpu().numpy().astype(np.float16), "smean35": sm[35].cpu().numpy().astype(np.float16),
               "R35": dR[35].cpu().numpy().astype(np.float16)}
        if want_gen1:
            tok1 = first_token(tw["pre"]["r_logits"], u0)
            g_arm = self.gen1(pre, tok1, P)
            g_tw = self.twin_gen1(w, tok1)
            dg = g_arm - g_tw
            rec["gen1"] = [round(float(x), 4) for x in dg.norm(dim=-1)]
            rec["gen1_token"] = tok1
            vec["gen1_35"] = dg[35].cpu().numpy().astype(np.float16)
        del cap
        return pre, rec, vec

    def release(self) -> None:
        self.clean.clear()
        self.g1_twin.clear()
        gc.collect()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ runner
def done_keys() -> set[str]:
    return {row_key(r) for r in read_jsonl(RAW)}


class RunnerK:
    def __init__(self, model: Any, tok: Any, prompts: dict, B: int):
        self.model, self.tok, self.prompts, self.B = model, tok, prompts, B
        self.d1_units: dict[str, np.ndarray] = {}

    def _row_spec(self, ctx: TaskCtxK, w: str, arm: str, k: int) -> dict[str, Any]:
        a = parse_arm(arm)
        task = ctx.task
        mx = MAX_NEW[task]
        us = u_stream(task, w, k, n=mx)
        if a["family"] == "TWIN":
            return {"arm": arm, "k": k, "twin": True, "us": us, "meta": {"design": "TWIN"}}
        unit, mask = ctx.unit(w, a["unit"])
        dseed, u = KU.direction(a["seeds"], task, a["alpha"], w, k)
        pre, rec, vec = ctx.edited_prefill(w, u, unit, a["alpha"], mask, float(us[0]))
        meta = {"design": a["design"], "unit_id": a["unit"], "seed_scheme": a["seeds"], "direction_seed": dseed,
                "unit_mean_b12": float(unit[0].mean()), "unit_fro": float(np.linalg.norm(unit.astype(np.float64))),
                "dose_vs_D1": KU.dose_ratios(unit, ctx.n_abs), "realised": rec,
                "max_dose_over_hnorm": float((a["alpha"] * unit / np.maximum(ctx.twin(w)["h_norm"], 1e-6)).max())}
        return {"arm": arm, "k": k, "twin": False, "pre": pre, "us": us, "meta": meta, "vec": vec}

    def run_batch(self, ctx: TaskCtxK, w: str, items: list[tuple[str, int]], stage: str) -> list[dict[str, Any]]:
        assert len(items) == self.B, items
        task = ctx.task
        t0 = time.time()
        tw = ctx.twin(w)
        specs = [self._row_spec(ctx, w, arm, k) for arm, k in items]
        t_pre = time.time() - t0
        groups, order = [], []
        twin_rows = [s for s in specs if s["twin"]]
        if twin_rows:
            groups.append({"pre": tw["pre"], "us": [s["us"] for s in twin_rows]})
            order += twin_rows
        for s in specs:
            if not s["twin"]:
                groups.append({"pre": s["pre"], "us": [s["us"]]})
                order.append(s)
        res = sample4(self.model, self.tok, groups, fence=FENCE[task], max_new=MAX_NEW[task])
        for g in groups:
            g.pop("pre", None)
        block_id = f"k:{stage}:{task}:{w}:{int(t0 * 1000)}"
        p = tw["prompt"]
        out, reals, vecs = [], [], {}
        for s, r in zip(order, res):
            a = parse_arm(s["arm"])
            m = s["meta"]
            rec = m.get("realised")
            row = {"task": task, "template": w, "arm": s["arm"], "sample_id": s["k"], "slot": f"{task}|{w}|{s['k']}",
                   "seed": stable_seed(task, w, s["k"]), "family": a["family"], "design": a["design"],
                   "alpha": a["alpha"], "unit_id": m.get("unit_id"), "seed_scheme": m.get("seed_scheme"),
                   "direction_seed": m.get("direction_seed"), "model": MODEL_ID, "model_revision": MODEL_REVISION,
                   "precision": PRECISION, "gpu": GPU_NAME, "B": self.B, "temperature": 1.0, "top_p": 1.0,
                   "top_k": None, "thinking": False, "max_new": MAX_NEW[task], "stage": stage,
                   "engine_path": "shared", "prompt_sha256": p["prompt_sha256"], "P": tw["P"], "block_id": block_id,
                   "unit_mean_b12": m.get("unit_mean_b12"), "unit_fro": m.get("unit_fro"),
                   "dose_vs_D1": m.get("dose_vs_D1"), "max_dose_over_hnorm": m.get("max_dose_over_hnorm"),
                   "realised_disp": None if rec is None else {
                       "S_b12": rec["spec_mean"][12], "S_b23": rec["spec_mean"][23], "S_b35": rec["spec_mean"][35],
                       "R_b23": rec["R"][23], "R_b35": rec["R"][35],
                       "G1_b35": (rec.get("gen1") or [None] * 36)[35], "rel_err_mean": rec["rel_err_mean"],
                       "rel_err_max": rec["rel_err_max"]},
                   "text": self.tok.decode(r["token_ids"], skip_special_tokens=True), "token_ids": r["token_ids"],
                   "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"], "fence_step": r["fence_step"],
                   "logprob_sum": r["logprob_sum"], "utc": utc_now()}
            out.append(row)
            if rec is not None:
                reals.append({"key": row_key(row), "task": task, "template": w, "arm": s["arm"], "sample_id": s["k"],
                              "design": a["design"], "alpha": a["alpha"], **rec})
                for kk, v in s["vec"].items():
                    vecs[f"{row_key(row)}::{kk}"] = v
        append_jsonl(RAW, out)
        if reals:
            append_jsonl(REALISED, reals)
        if vecs:
            np.savez_compressed(DISP_DIR / f"{task}_{w}_{int(t0 * 1000)}.npz", **vecs)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"stage": stage, "task": task, "w": w, "B": self.B, "seconds": round(dt, 2),
                               "prefill_seconds": round(t_pre, 2), "steps": res[0]["steps"],
                               "max_tokens": max(x["n_tokens"] for x in res),
                               "n_length": sum(x["finish_reason"] == "length" for x in res),
                               "arms": sorted({a for a, _ in items}), "utc": utc_now()}])
        logger.info(f"{stage} {task}/{w}: {len(items)} rows {sorted({a for a, _ in items})} {dt:.1f}s "
                    f"({res[0]['steps']} steps, prefill {t_pre:.1f}s)")
        del specs, groups, res
        return out

    def run_cells(self, task: str, cells: list[tuple[str, list[int]]], stage: str,
                  templates: tuple[str, ...] = TEMPLATES, deadline: float | None = None) -> int:
        done = done_keys()
        ctx = TaskCtxK(self.model, self.prompts, task)
        nb = 0
        order = {arm: i for i, (arm, _) in enumerate(cells)}
        try:
            for w in templates:
                todo = [(arm, k) for arm, ks in cells for k in ks
                        if f"{task}|{w}|{arm}|{k}" not in done]
                if not todo:
                    continue
                todo.sort(key=lambda x: (x[1], order[x[0]]))      # interleave designs by slot
                batches = [todo[i:i + self.B] for i in range(0, len(todo), self.B)]
                last = batches[-1]
                kpad = PAD_K0
                while len(last) < self.B:
                    if f"{task}|{w}|TWIN|{kpad}" not in done:
                        last.append(("TWIN", kpad))
                        done.add(f"{task}|{w}|TWIN|{kpad}")
                    kpad += 1
                for items in batches:
                    if deadline is not None and time.time() > deadline:
                        logger.warning(f"deadline reached before {stage} {task}/{w}")
                        return nb
                    self.run_batch(ctx, w, items, stage)
                    nb += 1
                ctx.release()
        finally:
            ctx.release()
        return nb


# ------------------------------------------------------------------------------------------------ setup
def hardware_record() -> dict[str, Any]:
    import platform
    import subprocess

    import transformers

    free, total = torch.cuda.mem_get_info(0)
    try:
        smi = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        smi = f"nvidia-smi failed: {e}"
    rec = {"gpu": GPU_NAME, "nvidia_smi": smi, "free_GiB_before_load": free / 2 ** 30, "total_GiB": total / 2 ** 30,
           "torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
           "transformers": transformers.__version__, "python": platform.python_version(), "utc": utc_now(),
           "planned_gpu": "RTX A4500 20 GB", "capability": list(torch.cuda.get_device_capability(0))}
    if not (PRED / "hardware.json").exists():
        write_json(PRED / "hardware.json", rec)
    return rec


def memory_probe(model: Any, prompts: dict) -> int:
    """Largest constant B in {12, 10, 8, 7, 6, 4} holding a full 1,536-token T2 decode buffer (longest T2 prompt)
    plus 16 decode steps at the buffer's end, the edited-prefill KV copies of B rows and 1.5 GiB of headroom."""
    from engine import prealloc_cache

    p = max((v for v in prompts.values() if v["task"] == "T2"), key=lambda v: v["P"])
    pre = prefill(model, p["ids"])
    res = {"P": p["P"], "max_new": 1536, "tried": {}}
    chosen = None
    for B in K.B_CANDIDATES:
        try:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            kv = [(K_.expand(B, -1, -1, -1), V_.expand(B, -1, -1, -1)) for K_, V_ in pre["kv"]]
            copies = [[(K_.clone(), V_.clone()) for K_, V_ in pre["kv"]] for _ in range(B)]
            cache = prealloc_cache(kv, p["P"] + 1536 + 1)
            tokn = torch.full((B, 1), 13, device=model.device, dtype=torch.long)
            with torch.no_grad():
                for s in range(16):
                    pos = torch.full((B, 1), p["P"] + 1520 + s, device=model.device, dtype=torch.long)
                    cache_layers = cache.layers
                    for L in cache_layers:
                        L.n = p["P"] + 1520 + s
                    h = model.model(input_ids=tokn, past_key_values=cache, position_ids=pos,
                                    use_cache=True).last_hidden_state
                    lg = model.lm_head(h[:, -1]).double()
                    pr = torch.softmax(lg, -1).cumsum(-1)
                    del lg, pr
            peak = torch.cuda.max_memory_allocated() / 2 ** 30
            free, total = torch.cuda.mem_get_info(0)
            del cache, kv, copies
            torch.cuda.empty_cache()
            ok = peak + 1.5 < total / 2 ** 30
            res["tried"][B] = {"peak_GiB": round(peak, 2), "ok": ok}
            logger.info(f"memory probe B={B}: peak {peak:.2f} GiB (ok={ok})")
            if ok:
                chosen = B
                break
        except torch.cuda.OutOfMemoryError:
            res["tried"][B] = {"oom": True}
            torch.cuda.empty_cache()
    res["B"] = chosen or 4
    write_json(RESULTS / "memory_probe.json", res)
    return res["B"]


# ------------------------------------------------------------------------------------------------ unit tests
def unit_tests(model: Any, tok: Any, prompts: dict, B: int) -> dict[str, Any]:
    if UNIT_TESTS.exists():
        return read_json(UNIT_TESTS)
    res: dict[str, Any] = {"utc": utc_now(), "B": B}
    # U1 / U2 / U6 on T10 W1 and T2 W1
    e27 = defaultdict(list)
    for r in read_jsonl(K.E27 / "data" / "samples_raw.jsonl"):
        if r["arm"] in ("PN_a1", "PN_a2") and r.get("unit_mean_b12") is not None:
            e27[(r["task"], r["template"])].append(r["unit_mean_b12"])
    u1, u2, u5 = {}, {}, {}
    for task in ("T10", "T2", "T03", "T05", "T1"):
        ctx = TaskCtxK(model, prompts, task)
        for w in TEMPLATES:
            tw = ctx.twin(w)
            here = float(tw["U_bf"][0].mean())
            ref = float(np.median(e27[(task, w)])) if e27.get((task, w)) else None
            u5[f"{task}|{w}"] = {"here": here, "exp27": ref,
                                 "rel": None if ref is None else abs(here - ref) / ref}
            if task in ("T10", "T2") and w == "W1":
                dseed, u = KU.s4_direction(task, 2.0, w, 0)
                for name in ("U_abs", "U_bf", "U_bf_star", "P_top", "P_rest", "P_shuf"):
                    unit, mask = ctx.unit(w, name)
                    pre0, rec0, _ = ctx.edited_prefill(w, u, unit, 0.0, mask, 0.5, want_gen1=False)
                    same_logits = bool(torch.equal(pre0["r_logits"], tw["pre"]["r_logits"]))
                    same_kv = all(torch.equal(x[0], y[0]) and torch.equal(x[1], y[1])
                                  for x, y in zip(pre0["kv"], tw["pre"]["kv"]))
                    u1[f"{task}|{name}"] = {"logits_bitwise": same_logits, "kv_bitwise": same_kv}
                    pre2, rec2, _ = ctx.edited_prefill(w, u, unit, 2.0, mask, 0.5, want_gen1=True)
                    u2[f"{task}|{name}"] = {"rel_err_mean": rec2["rel_err_mean"], "rel_err_max": rec2["rel_err_max"],
                                            "masked_b12_max_abs_disp": rec2["masked_b12_max_abs_disp"],
                                            "spec_mean_b0_11_max": max(rec2["spec_mean"][:12]),
                                            "lens": [len(rec2["spec_mean"]), len(rec2["R"]), len(rec2["gen1"])],
                                            "S_b12": rec2["spec_mean"][12], "R_b35": rec2["R"][35],
                                            "G1_b35": rec2["gen1"][35]}
                    del pre0, pre2
        ctx.release()
    res["U1_alpha0_bitwise_twin"] = u1
    res["U1_pass"] = all(v["logits_bitwise"] and v["kv_bitwise"] for v in u1.values())
    res["U2_displacement"] = u2
    res["U2_pass"] = all(v["rel_err_mean"] <= 1e-3 and (v["masked_b12_max_abs_disp"] in (None, 0.0)) for v in u2.values())
    res["U6_lengths_36"] = all(v["lens"] == [36, 36, 36] and v["spec_mean_b0_11_max"] == 0.0 for v in u2.values())
    res["U5_ubf_vs_exp27"] = u5
    rels = [v["rel"] for v in u5.values() if v["rel"] is not None]
    res["U5_max_rel"] = max(rels) if rels else None
    res["U5_pass"] = bool(rels) and max(rels) <= 0.01
    # U3 batch-shape invariance and U4 self-reproduction (T10 W1 twin slots, max_new 256)
    ctx = TaskCtxK(model, prompts, "T10")
    tw = ctx.twin("W1")

    def twin_batch(ks: list[int]) -> list[dict[str, Any]]:
        g = [{"pre": tw["pre"], "us": [u_stream("T10", "W1", k, n=256) for k in ks]}]
        return sample4(model, tok, g, fence=FENCE["T10"], max_new=256)
    full = twin_batch(list(range(B)))
    again = twin_batch(list(range(B)))
    half = twin_batch(list(range(max(3, B // 2))))
    res["U4_self_reproduction"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(full, again)) / B
    res["U3_batch_shape_identical_rows"] = sum(full[i]["token_ids"] == half[i]["token_ids"] for i in range(3))
    res["U3_pass"] = res["U3_batch_shape_identical_rows"] == 3
    res["U4_pass"] = res["U4_self_reproduction"] == 1.0
    ctx.release()
    write_json(UNIT_TESTS, res)
    logger.info(f"unit tests: U1 {res['U1_pass']} U2 {res['U2_pass']} U3 {res['U3_pass']} U4 {res['U4_pass']} "
                f"U5 {res['U5_pass']} (max rel {res['U5_max_rel']}) U6 {res['U6_lengths_36']}")
    return res


# ------------------------------------------------------------------------------------------------ stage helpers
def wait_for(path: Path, what: str, max_wait_s: float = 3 * 3600) -> None:
    t0 = time.time()
    while not path.exists():
        if time.time() - t0 > max_wait_s:
            raise TimeoutError(f"{what} never appeared")
        logger.info(f"waiting for {what} ({path.name})")
        time.sleep(30)


def labelled(keys: list[str]) -> dict[str, dict[str, Any]]:
    want = set(keys)
    return {l["key"]: l for l in read_jsonl(LABELS) if l["key"] in want}


def wait_labels(keys: list[str], timeout: float = 900.0, frac: float = 1.0) -> dict[str, dict[str, Any]]:
    t0 = time.time()
    while True:
        got = labelled(keys)
        if len(got) >= frac * len(keys) or time.time() - t0 > timeout:
            return got
        time.sleep(15)


def s1_cells(task: str, alpha: float, ks: list[int]) -> list[tuple[str, list[int]]]:
    a = "a1" if alpha == 1.0 else "a2"
    return [(f"D1_{a}", ks), (f"D2_{a}", ks), (f"D3_{a}", ks), (f"D4_{a}", ks)]


# ------------------------------------------------------------------------------------------------ main
@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("gen_k")
    stages = sys.argv[1:] or ["tests", "s0", "s1", "d5", "s2", "s3pn"]
    hw = hardware_record()
    logger.info(f"hardware: {hw['gpu']} free {hw['free_GiB_before_load']:.1f} GiB; stages {stages}")
    tok, model = load_model(fp8=False, vram_fraction=0.97)
    prompts = load_prompts()
    st = read_json(STATE) if STATE.exists() else {}
    if "B" not in st:
        st["B"] = memory_probe(model, prompts)
        write_json(STATE, st)
    B = st["B"]
    logger.info(f"constant batch size B = {B}")
    run = RunnerK(model, tok, prompts, B)
    if "tests" in stages:
        unit_tests(model, tok, prompts, B)
    if "s0" in stages:
        # 2.1 engine-check slots first (k 0-3 of T2 and T03), then the full twin cells (k 0-9; T2 also 10-19)
        run.run_cells("T2", [("TWIN", [0, 1, 2, 3])], "S0_check")
        run.run_cells("T03", [("TWIN", [0, 1, 2, 3])], "S0_check")
        for t in ("T10", "T2", "T03", "T05", "T1"):
            run.run_cells(t, [("TWIN", K20 if t == "T2" else K10)], "S0_twin")
    if any(s in stages for s in ("s1", "d5", "s2", "s3pn")):
        wait_for(PRED / "commit1.json", "COMMIT #1")
    if "s1" in stages:
        # (a) anchors on T10 alpha 2: W1 first (the 10-slot stage), then W2-W5
        anchors = [("D1_a2", K10), ("D4_a2", K10)]
        run.run_cells("T10", anchors, "S1_anchor", templates=("W1",))
        run.run_cells("T10", anchors, "S1_anchor")
        # (b) the rest of T10; (c) T2 alpha 2 (N 100) and alpha 1 (N 50)
        run.run_cells("T10", s1_cells("T10", 2.0, K10), "S1")
        run.run_cells("T10", s1_cells("T10", 1.0, K10), "S1")
        run.run_cells("T2", s1_cells("T2", 2.0, K20), "S1")
        run.run_cells("T2", s1_cells("T2", 1.0, K10), "S1")
    if "d5" in stages:
        run.run_cells("T10", [("D5_a2", K10)], "S1_D5")
        run.run_cells("T2", [("D5_a2", K20)], "S1_D5")
    if "s2" in stages:
        for t in ("T10", "T2"):
            run.run_cells(t, [("PTOP_a2", K10), ("PREST_a2", K10), ("PSHUF_a2", K10)], "S2")
    if "diag9101" in stages:
        logger.warning("diag9101 requested: fixed direction rand_9101 is run by gen_k only on demand")
    if "s3pn" in stages:
        wait_for(PRED / "commit2.json", "COMMIT #2")
        dstar = read_json(PRED / "commit2.json")["D_star"]
        for t in ("T03", "T05", "T1"):
            run.run_cells(t, [(f"{dstar}_a1", K10), (f"{dstar}_a2", K10)], "S3_PN")
        if dstar not in ("D1", "D2", "D3", "D4"):
            for t in ("T10", "T2"):
                run.run_cells(t, [(f"{dstar}_a1", K10), (f"{dstar}_a2", K10)], "S3_PN")
    write_json(RESULTS / "gpu_done.json", {"stages": stages, "utc": utc_now()})
    logger.info("GPU process finished")


if __name__ == "__main__":
    main()
