#!/usr/bin/env python3
"""Generation runner: exp22's CRN design run under one engine at a time, resumable by done-slot keys.

Reused unchanged from the vendored exp22 code: TaskCtx (clean twin prefill + edited prefill with realised-displacement
records), push_spec (TARGET edit: displacement from the clean twin along u is exactly alpha * n[l, p] at blocks 12-23,
prompt prefill only), rand_dir, ban_unit (absolute unit n[l, p]), u_stream (CRN uniforms per (task, template, k)) and
engine4.sample (exact inverse-CDF sampler, prune=False, constant batch shape, fence stop, max_new 1024).
Arms: TWIN; POP_d<seed>_a<alpha> (fixed direction rand_<seed>); PN_a<alpha> (exp19 per-sample plan noise: direction
seed stable_seed(task, arm, template, k), PCG64 normal, normalised; same absolute unit n). Every batch holds exactly B
rows of ONE (task, template); the last batch of a template is padded with fresh TWIN slots k >= 10 (extra twin rows).
"""

from __future__ import annotations

import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

import c6  # noqa: F401
from c6 import (FENCE, MAX_NEW, MODEL_ID, MODEL_REVISION, RAW_DIR, REALISED, RESULTS, append_jsonl, read_jsonl,
                    stable_seed, utc_now)

GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
PRECISION = {"a": "W8A8 e4m3 per-channel weights x per-token e4m3 activations (native torch._scaled_mm)",
             "a_emul": "W8A8 emulated (bf16-held e4m3 codes, fp32 accumulate, one rounding)",
             "b": "W8A16 e4m3 per-channel weights x bf16 activations (fp32 accumulate, one rounding)",
             "c": "W16A8 bf16 weights x per-token e4m3 fake-quantised activations (fp32 accumulate, one rounding)",
             "d": "BF16 weights and activations"}


def raw_path(engine: str):
    return RAW_DIR / f"raw_{engine}.jsonl"


def parse_arm(arm: str) -> dict[str, Any]:
    if arm == "TWIN":
        return {"family": "TWIN"}
    m = re.fullmatch(r"POP_d(\d+)_a([\d.]+)", arm)
    if m:
        return {"family": "POP", "seed": int(m.group(1)), "alpha": float(m.group(2))}
    m = re.fullmatch(r"PN_a([\d.]+)", arm)
    if m:
        return {"family": "PN", "alpha": float(m.group(1))}
    raise ValueError(arm)


def pn_direction(task: str, arm: str, w: str, k: int) -> tuple[int, np.ndarray]:
    """exp19 sampling_v4.pn_direction, verbatim."""
    seed = stable_seed(task, arm, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def done_slots(engine: str) -> set[tuple[str, str, str, int]]:
    return {(r["task"], r["template"], r["arm"], int(r["sample_id"])) for r in read_jsonl(raw_path(engine))}


def pack(cells: list[tuple[str, list[int]]], used_twin: set[int], B: int) -> list[list[tuple[str, list[int]]]]:
    batches, cur, room = [], [], B
    for arm, ks in cells:
        ks = list(ks)
        while ks:
            take, ks = ks[:room], ks[room:]
            cur.append((arm, take))
            room -= len(take)
            if room == 0:
                batches.append(cur)
                cur, room = [], B
    if cur:
        k, pad = 10, []
        while len(pad) < room:
            if k not in used_twin:
                pad.append(k)
                used_twin.add(k)
            k += 1
        cur.append(("TWIN", pad))
        batches.append(cur)
    return batches


def compact_disp(rec: dict[str, Any]) -> dict[str, Any] | None:
    if not rec:
        return None
    S, R = rec["disp_smean_norm"], rec["disp_R_norm"]
    return {"S_b12": round(S[12], 4), "S_b23": round(S[23], 4), "S_b35": round(S[35], 4), "R_b23": round(R[23], 4),
            "R_b35": round(R[35], 4), "rel_err_max": rec["rel_err_max"], "gain": round(rec["gain"], 4)}


class Runner:
    def __init__(self, model: Any, tok: Any, prompts: dict, engine: str, B: int, a_impl: str = "native",
                 cap: int | None = None):
        """cap None -> the vendored engine4.sample (full max_new KV buffer); cap int -> sampler6.sample with a
        `cap`-token KV buffer and the overflow continuation (weight set B on the 16 GB card)."""
        self.model, self.tok, self.prompts, self.engine, self.B, self.a_impl = model, tok, prompts, engine, B, a_impl
        self.cap = cap

    def _groups(self, ctx: Any, w: str, spec: list[tuple[str, list[int]]]):
        from ctx4 import ban_unit, push_spec, rand_dir
        from engine4 import u_stream

        task = ctx.task
        dev = ctx.dev
        groups, meta, recs = [], [], []
        for arm, ks in spec:
            a = parse_arm(arm)
            if a["family"] == "PN":
                for k in ks:
                    dseed, u = pn_direction(task, arm, w, k)
                    rec: dict[str, Any] = {}
                    spec_ = push_spec(dev, u, ban_unit(task), a["alpha"])
                    groups.append({"pre": self._lazy(ctx, w, spec_, rec, recs, {"engine": self.engine, "task": task,
                                   "template": w, "arm": arm, "sample_id": k, "direction_seed": dseed}),
                                   "us": [u_stream(task, w, k)]})
                    meta.append((arm, k, dseed, rec))
                continue
            if a["family"] == "TWIN":
                pre, rec = ctx.arm_prefill(w, {"kind": None})
                groups.append({"pre": pre, "us": [u_stream(task, w, k) for k in ks]})
            else:
                rec = {}
                spec_ = push_spec(dev, rand_dir(a["seed"]), ban_unit(task), a["alpha"])
                groups.append({"pre": self._lazy(ctx, w, spec_, rec, recs, {"engine": self.engine, "task": task,
                               "template": w, "arm": arm, "sample_id": None, "direction_seed": a["seed"]}),
                               "us": [u_stream(task, w, k) for k in ks]})
            for k in ks:
                meta.append((arm, k, a.get("seed"), rec))
        if self.cap is None:   # the vendored sampler needs materialised prefills
            for g in groups:
                if callable(g["pre"]):
                    g["pre"] = g["pre"]()
        return groups, meta, recs

    @staticmethod
    def _lazy(ctx: Any, w: str, spec: dict[str, Any], rec_out: dict[str, Any], recs: list, tag: dict[str, Any]):
        def f():
            pre, rec = ctx.arm_prefill(w, spec)
            rec_out.update(rec)
            recs.append({**tag, "utc": utc_now(), **rec})
            return pre
        return f

    def _sample(self, groups: list[dict[str, Any]], task: str) -> list[dict[str, Any]]:
        if self.cap is None:
            from engine4 import sample
            return sample(self.model, self.tok, groups, fence=FENCE[task], max_new=MAX_NEW)
        import sampler6
        try:
            return sampler6.sample(self.model, self.tok, groups, fence=FENCE[task], max_new=MAX_NEW, cap=self.cap)
        except torch.cuda.OutOfMemoryError:
            logger.error(f"[{self.engine}] OOM in a capped batch of {task}; retrying with the full KV buffer")
            torch.cuda.empty_cache()
            return sampler6.sample(self.model, self.tok, groups, fence=FENCE[task], max_new=MAX_NEW, cap=None)

    def run_batch(self, ctx: Any, w: str, spec: list[tuple[str, list[int]]], stage: str) -> list[dict[str, Any]]:
        assert sum(len(ks) for _, ks in spec) == self.B, spec
        task = ctx.task
        t0 = time.time()
        groups, meta, recs = self._groups(ctx, w, spec)
        res = self._sample(groups, task)
        del groups
        p = ctx.prompt("twin", w)
        block_id = f"{self.engine}:{stage}:{task}:{w}:{int(t0 * 1000)}"
        out = []
        for (arm, k, dseed, rec), r in zip(meta, res):
            a = parse_arm(arm)
            out.append({"engine": self.engine, "a_impl": self.a_impl if self.engine == "a" else None,
                        "task": task, "arm": arm, "template": w, "sample_id": k, "slot": f"{task}|{w}|{k}",
                        "seed": stable_seed(task, w, k), "family": a["family"], "alpha": a.get("alpha"),
                        "direction_seed": dseed, "model": MODEL_ID, "model_revision": MODEL_REVISION,
                        "precision": PRECISION[self.engine], "gpu": GPU_NAME, "B": self.B, "temperature": 1.0,
                        "top_k": None, "thinking": False, "max_new": MAX_NEW, "stage": stage,
                        "prompt_sha256": p["prompt_sha256"], "block_id": block_id,
                        "realised_disp": compact_disp(rec) if a["family"] != "TWIN" else None,
                        "text": self.tok.decode(r["token_ids"], skip_special_tokens=True),
                        "token_ids": r["token_ids"], "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                        "fence_step": r["fence_step"], "logprob_sum": r["logprob_sum"],
                        "kv_cap": self.cap, "overflow_at_step": r.get("overflow_at_step"), "utc": utc_now()})
        append_jsonl(raw_path(self.engine), out)
        if recs:
            for rr in recs:
                rr.pop("_delta", None)
                rr.pop("_deltaR", None)
            append_jsonl(REALISED, recs)
        dt = time.time() - t0
        append_jsonl(RESULTS / "timing.jsonl", [{"engine": self.engine, "task": task, "w": w, "stage": stage,
                                                 "B": self.B, "seconds": dt, "steps": res[0]["steps"],
                                                 "max_tokens": max(x["n_tokens"] for x in res), "utc": utc_now()}])
        logger.info(f"[{self.engine}] {stage} {task}/{w} {len(spec)} cells: {dt:.1f}s, {res[0]['steps']} steps")
        return out

    def run_cells(self, task: str, cells: list[tuple[str, list[int]]], stage: str,
                  templates: tuple[str, ...] = ("W1", "W2", "W3", "W4", "W5"), deadline: float | None = None) -> int:
        from ctx4 import TaskCtx

        done = done_slots(self.engine)
        used_twin: dict[str, set[int]] = {}
        for (t, w, arm, k) in done:
            if t == task and arm == "TWIN":
                used_twin.setdefault(w, set()).add(k)
        ctx = TaskCtx(self.model, self.prompts, task)
        nb = 0
        try:
            for w in templates:
                todo = []
                for arm, ks in cells:
                    rest = [k for k in ks if (task, w, arm, k) not in done]
                    if arm == "TWIN":
                        used_twin.setdefault(w, set()).update(rest)
                    if rest:
                        todo.append((arm, rest))
                if not todo:
                    continue
                for spec in pack(todo, used_twin.setdefault(w, set()), self.B):
                    if deadline is not None and time.time() > deadline:
                        logger.warning(f"[{self.engine}] deadline reached before {stage} {task}/{w}")
                        return nb
                    self.run_batch(ctx, w, spec, stage)
                    nb += 1
                ctx.release()
        finally:
            ctx.release()
        return nb
