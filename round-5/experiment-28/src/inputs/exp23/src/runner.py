#!/usr/bin/env python3
"""GPU runner: CRN single-prompt batches (twin, escape pushes, plan noise, T 1.3, bans) and uncoupled multi-prompt
batches (pilot, novelty, 'can', association), with raw rows streamed to data/raw_*.jsonl and batch timing to
results/timing_batches.jsonl."""

from __future__ import annotations

import gc
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (BAND, CAPTURE_BLOCKS, D_MODEL, DATA_DIR, MODEL_ID, RESULTS_DIR, append_jsonl, read_jsonl,
                 stable_seed, utc_now)
import engine_gemma as EG
import prompts_gemma as PG
from units import unit_n

TIMING = RESULTS_DIR / "timing_batches.jsonl"
ESC_DIRS: dict[int, np.ndarray] = {}


def esc_dir(seed: int) -> np.ndarray:
    if seed not in ESC_DIRS:
        ESC_DIRS[seed] = EG.seed_dir(seed)
    return ESC_DIRS[seed]


def row_dir(task: str, w: str, r: dict[str, Any]) -> np.ndarray | None:
    if r.get("dir_kind") == "escape":
        return esc_dir(int(r["direction_seed"]))
    if r.get("dir_kind") == "PN":
        return EG.unit_dir(task, "PN", w, int(r["slot"]))
    return None


class Runner:
    def __init__(self) -> None:
        self.tok, self.model, self.info = EG.load_model()
        self.ctx: dict[tuple[str, str, str], dict[str, Any]] = {}

    # -------------------------------------------------------------------------------------------- contexts
    def task_ctx(self, task: str, X: str, w: str) -> dict[str, Any]:
        key = (task, X, w)
        if key not in self.ctx:
            if len(self.ctx) > 6:
                self.ctx.clear()
                torch.cuda.empty_cache()
            tw = PG.p_twin(task, X, w)
            PG.register(tw)
            clean = EG.clean_states(self.model, tw["ids"], tw["spec_start"], tw["spec_end"], CAPTURE_BLOCKS)
            n = unit_n(clean["S"], "ox")
            self.ctx[key] = {"twin": tw, "clean": clean, "n": n}
        return self.ctx[key]

    def done_ids(self, path) -> set[str]:
        return {r["row_id"] for r in read_jsonl(path)}

    # -------------------------------------------------------------------------------------------- CRN batches
    def run_crn(self, task: str, X: str, w: str, rows: list[dict[str, Any]], B: int, max_new: int, stage: str,
                raw_path, batch_id: str, prompt: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """rows (len == B): {arm, slot, alpha, dir_kind, direction_seed, temperature, pad, flag}. prompt: the prompt
        to feed (default: the twin of (task, X, w)); pushes are always measured from the clean twin."""
        assert len(rows) == B, (len(rows), B)
        t0 = time.time()
        ctx = self.task_ctx(task, X, w)
        p = prompt or ctx["twin"]
        aligned = True
        if prompt is not None:
            aligned = prompt["P"] == ctx["twin"]["P"] and prompt["spec_start"] == ctx["twin"]["spec_start"]
            if not aligned:
                logger.warning(f"{task}/{w}: prompt length {prompt['P']} != twin {ctx['twin']['P']} (D changed after "
                               "the twin); realised displacement not logged for this batch")
            PG.register(prompt)
        a, b = ctx["twin"]["spec_start"], ctx["twin"]["spec_end"]
        U = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
        alpha = torch.zeros(B, dtype=torch.float32, device="cuda")
        for i, r in enumerate(rows):
            d = row_dir(task, w, r)
            if d is not None and (r.get("alpha") or 0) > 0:
                U[i] = torch.tensor(d, device="cuda")
                alpha[i] = float(r["alpha"])
        push = None
        if bool((alpha > 0).any()):
            push = {"U": U, "alpha": alpha, "n": ctx["n"], "h_ref": {l: ctx["clean"]["S"][l] for l in BAND},
                    "a": a, "b": b, "band": BAND}
        pre = EG.prefill_single(self.model, p["ids"], B, push=push, capture_ref=ctx["clean"] if aligned else None)
        dS = pre.pop("disp_S", np.full((B, len(CAPTURE_BLOCKS)), np.nan))
        dR = pre.pop("disp_R", np.full((B, len(CAPTURE_BLOCKS)), np.nan))
        rel = pre.pop("relerr_along", None)
        Us = np.stack([EG.u_stream(task, w, int(r["slot"]), n=max_new) for r in rows])
        temps = np.array([float(r.get("temperature", 1.0)) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, temps, max_new)
        del pre
        out = []
        push_rows = [i for i in range(B) if float(alpha[i]) > 0]
        for i, (r, g) in enumerate(zip(rows, res)):
            rd = {"S_mean_band": float(dS[i, :len(BAND)].mean()), "R_last": float(dR[i, -1]),
                  "S_by_block": [round(float(x), 3) for x in dS[i]], "R_by_block": [round(float(x), 3) for x in dR[i]]}
            if rel is not None and i in push_rows:
                rd["rel_err_along_u_max"] = float(rel[i].max())
            out.append({"row_id": f"{stage}|{task}|{w}|{r['arm']}|{r['slot']}", "task": task, "arm": r["arm"],
                        "stage": stage, "site": "spec_band" if r.get("dir_kind") else None, "alpha": r.get("alpha"),
                        "direction_seed": r.get("direction_seed"), "dir_kind": r.get("dir_kind"), "template": w,
                        "slot": int(r["slot"]), "temperature": float(r.get("temperature", 1.0)), "top_k": None,
                        "thinking": False, "prompt_sha256": p["prompt_sha256"], "prompt_kind": p["kind"],
                        "mode": X, "text": g["text"], "token_ids": g["token_ids"], "finish_reason": g["finish_reason"],
                        "n_new_tokens": g["n_tokens"], "realised_disp": rd, "pad": bool(r.get("pad", False)),
                        "flag": r.get("flag"), "batch_id": batch_id, "B": B, "max_new": max_new, "model": MODEL_ID,
                        "seed": stable_seed(task, w, int(r["slot"])), "utc": utc_now()})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": task, "w": w, "B": B, "seconds": dt,
                               "steps": res[0]["steps"], "max_new": max_new, "utc": utc_now()}])
        logger.info(f"{batch_id}: {dt:.1f}s, {res[0]['steps']} steps, finish "
                    f"{dict(zip(*np.unique([g['finish_reason'] for g in res], return_counts=True)))}")
        return out

    # -------------------------------------------------------------------------------------------- uncoupled
    def run_multi(self, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path, batch_id: str,
                  fence_stop: bool = True) -> list[dict[str, Any]]:
        """rows: {row_id, task, arm, prompt (dict), ukey (tuple), temperature, mode, template, slot}."""
        t0 = time.time()
        for r in rows:
            PG.register(r["prompt"])
        pre = EG.prefill_multi(self.model, [r["prompt"]["ids"] for r in rows])
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        temps = np.array([float(r.get("temperature", 1.0)) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, temps, max_new, fence_stop=fence_stop)
        del pre
        out = []
        for r, g in zip(rows, res):
            out.append({"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "stage": stage, "site": None,
                        "alpha": None, "direction_seed": None, "template": r.get("template"), "slot": r.get("slot"),
                        "temperature": float(r.get("temperature", 1.0)), "top_k": None, "thinking": False,
                        "prompt_sha256": r["prompt"]["prompt_sha256"], "prompt_kind": r["prompt"]["kind"],
                        "mode": r.get("mode"), "text": g["text"], "token_ids": g["token_ids"],
                        "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"], "realised_disp": None,
                        "pad": False, "flag": r.get("flag"), "batch_id": batch_id, "B": len(rows),
                        "max_new": max_new, "model": MODEL_ID, "seed": stable_seed(*r["ukey"]), "utc": utc_now()})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": rows[0]["task"], "w": None,
                               "B": len(rows), "seconds": dt, "steps": res[0]["steps"], "max_new": max_new,
                               "utc": utc_now()}])
        logger.info(f"{batch_id}: {dt:.1f}s, {res[0]['steps']} steps, B={len(rows)}")
        return out

    # -------------------------------------------------------------------------------------------- teacher forcing
    def tf(self, ids: list[int], targets: list[int]) -> list[float]:
        return EG.tf_logprobs(self.model, ids, targets)

    @torch.no_grad()
    def spec_states(self, ids: list[int], a: int, b: int) -> dict[int, torch.Tensor]:
        return EG.clean_states(self.model, ids, a, b, BAND)["S"]

    def free(self) -> None:
        del self.model
        gc.collect()
        torch.cuda.empty_cache()


def wait_labels(row_ids: set[str], timeout_s: float = 3600.0, poll: float = 10.0) -> dict[str, dict[str, Any]]:
    """Block until every row id is labelled (data/labels.jsonl); returns {row_id: label row}."""
    t0 = time.time()
    while True:
        labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl") if r["row_id"] in row_ids}
        if len(labs) >= len(row_ids):
            return labs
        if time.time() - t0 > timeout_s:
            logger.warning(f"label wait timed out: {len(labs)}/{len(row_ids)}")
            return labs
        time.sleep(poll)
