#!/usr/bin/env python3
"""S5 sampling: arm registry, exact-CRN 20-row batches of ONE (task, template), resumable raw rows.

Arm names (the direction seed and dose are in the name; every arm is a prefill edit of the neutral twin):
  TWIN                      the clean twin (also the batch pad: extra slots k >= 10 are logged as extra twin rows)
  SCR_d<seed>_a<alpha>      screen replication (engine check): exp17 RAND with exp17's FP8 ban norms
  POP_d<seed>_a<alpha>      C2a population / confirmation / 9-task escape: U_l = u, M = alpha * n
  UPERP_d<seed>_a<alpha>    U_l = normalise(u - Q_l Q_l^T u), M = alpha * n
  UP_d<seed>_a<alpha>       U_l = normalise(Q_l Q_l^T u), M = alpha * n (amplified plan component)
  CLAMP_d<seed>_a<alpha>    U_l = u, M = alpha * n, then the displacement's P_t component is clamped to 0
  C2C_<axis>_s<s>           axis in {r, rm, r2, rand<seed>}: U_l = axis_l, M_s[l,p] = s D_l n[l,p] / mean_p n[l,p]
                            (rm uses the masked D, r2 the second-runner-up D, rand<seed> uses r's D)
  SWEEP_r_a<alpha>          U_l = r_l, M = alpha * n
Uniforms u_stream(task, w, k) are shared by every arm (CRN); batches always have B = 20 rows.
"""

from __future__ import annotations

import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg4 import (B, DECODING_STR, EDIT_BLOCKS, MODEL_ID, MODEL_REVISION, PATH_TASKS, QUANT, RAW, REALISED, STATES_DIR,
                  TIMING, append_jsonl, read_jsonl, stable_seed, utc_now)
from ctx4 import TaskCtx, ban_unit, push_spec, rand_dir
from engine4 import sample, u_stream


def parse_arm(arm: str) -> dict[str, Any]:
    if arm == "TWIN":
        return {"family": "TWIN", "kind": None}
    m = re.fullmatch(r"(SCR|POP|UPERP|UP|CLAMP)_d(\d+)_a([\d.]+)", arm)
    if m:
        return {"family": m.group(1), "seed": int(m.group(2)), "alpha": float(m.group(3))}
    m = re.fullmatch(r"C2C_(r|rm|r2|rand\d+)_s([\d.]+)", arm)
    if m:
        return {"family": "C2C", "axis": m.group(1), "s": float(m.group(2))}
    m = re.fullmatch(r"SWEEP_r_a([\d.]+)", arm)
    if m:
        return {"family": "SWEEP", "axis": "r", "alpha": float(m.group(1))}
    raise ValueError(arm)


class SubspaceStore:
    """Lazy loader of states/subspace_<task>.npz (written by subspace.py before the commit)."""

    def __init__(self) -> None:
        self.cache: dict[str, dict[str, np.ndarray]] = {}

    def get(self, task: str) -> dict[str, np.ndarray]:
        if task not in self.cache:
            z = np.load(STATES_DIR / f"subspace_{task}.npz", allow_pickle=False)
            self.cache[task] = {k: z[k] for k in z.files}
        return self.cache[task]


SUB = SubspaceStore()


def arm_spec(ctx: TaskCtx, arm: str) -> dict[str, Any]:
    a = parse_arm(arm)
    dev = ctx.dev
    fam = a["family"]
    if fam == "TWIN":
        return {"kind": None}
    if fam == "SCR":
        return push_spec(dev, rand_dir(a["seed"]), ban_unit(ctx.task, "exp17"), a["alpha"])
    n = ban_unit(ctx.task)
    nt = torch.tensor(n, dtype=torch.float32, device=dev)
    if fam == "POP":
        return push_spec(dev, rand_dir(a["seed"]), n, a["alpha"])
    sub = SUB.get(ctx.task)
    blocks = [int(x) for x in sub["blocks"]]
    bi = {l: i for i, l in enumerate(blocks)}
    if fam in ("UPERP", "UP", "CLAMP"):
        u = rand_dir(a["seed"]).astype(np.float64)
        U, Qd = {}, {}
        for j, l in enumerate(EDIT_BLOCKS):
            Q = sub["Q"][bi[l]].astype(np.float64)          # [D, k]
            pu = Q @ (Q.T @ u)
            v = u if fam == "CLAMP" else (u - pu if fam == "UPERP" else pu)
            U[l] = torch.tensor(v / max(np.linalg.norm(v), 1e-12), dtype=torch.float32, device=dev)
            Qd[l] = torch.tensor(Q, dtype=torch.float32, device=dev)
        spec = {"kind": "CLAMP" if fam == "CLAMP" else "TARGET", "U": U,
                "M": {l: a["alpha"] * nt[j] for j, l in enumerate(EDIT_BLOCKS)}}
        if fam == "CLAMP":
            spec["Q"] = Qd
        return spec
    axis = a["axis"]
    if fam == "SWEEP":
        U = {l: torch.tensor(sub["r"][bi[l]], dtype=torch.float32, device=dev) for l in EDIT_BLOCKS}
        return {"kind": "TARGET", "U": U, "M": {l: a["alpha"] * nt[j] for j, l in enumerate(EDIT_BLOCKS)}}
    # C2C dose arms
    dkey = {"r": "D_r", "rm": "D_rm", "r2": "D_r2"}.get(axis, "D_r")
    M = {}
    for j, l in enumerate(EDIT_BLOCKS):
        Dl = float(sub[dkey][bi[l]])
        M[l] = a["s"] * Dl * nt[j] / nt[j].mean()
    if axis.startswith("rand"):
        ut = torch.tensor(rand_dir(int(axis[4:])), dtype=torch.float32, device=dev)
        U = {l: ut for l in EDIT_BLOCKS}
    else:
        U = {l: torch.tensor(sub[axis][bi[l]], dtype=torch.float32, device=dev) for l in EDIT_BLOCKS}
    return {"kind": "TARGET", "U": U, "M": M}


def done_slots() -> set[tuple[str, str, str, int]]:
    return {(r["task"], r["template"], r["arm"], int(r["sample_id"])) for r in read_jsonl(RAW)}


def pack(cells: list[tuple[str, list[int]]], used_twin: set[int]) -> list[list[tuple[str, list[int]]]]:
    """Greedy packing of (arm, slots) cells into batches of exactly B rows; a cell larger than the remaining room is
    split; the last batch is padded with fresh TWIN slots k >= 10 not used before (logged as extra twin rows)."""
    batches: list[list[tuple[str, list[int]]]] = []
    cur: list[tuple[str, list[int]]] = []
    room = B
    for arm, ks in cells:
        ks = list(ks)
        while ks:
            take = ks[:room]
            ks = ks[room:]
            cur.append((arm, take))
            room -= len(take)
            if room == 0:
                batches.append(cur)
                cur, room = [], B
    if cur:
        k = 10
        pad = []
        while len(pad) < room:
            if k not in used_twin:
                pad.append(k)
                used_twin.add(k)
            k += 1
        cur.append(("TWIN", pad))
        batches.append(cur)
    return batches


def run_batch(ctx: TaskCtx, tok: Any, w: str, spec: list[tuple[str, list[int]]], block_id: str,
              stage: str, extra_meta: dict[str, Any] | None = None, save_geo: dict | None = None) -> list[dict]:
    assert sum(len(ks) for _, ks in spec) == B, spec
    task = ctx.task
    t0 = time.time()
    groups, meta, recs = [], [], []
    for arm, ks in spec:
        pre, rec = ctx.arm_prefill(w, arm_spec(ctx, arm), want_vectors=save_geo is not None)
        if rec:
            if save_geo is not None:
                save_geo[(arm, w)] = rec.pop("_delta")
                rec.pop("_deltaR", None)
            recs.append({"task": task, "template": w, "arm": arm, "block_id": block_id, "utc": utc_now(), **rec})
        groups.append({"pre": pre, "us": [u_stream(task, w, k) for k in ks]})
        for k in ks:
            meta.append((arm, k, rec.get("rel_err_max") if rec else None))
    res = sample(ctx.model, tok, groups, fence="path" if task in PATH_TASKS else "bench")
    out = []
    for (arm, k, rerr), r in zip(meta, res):
        a = parse_arm(arm)
        p = ctx.prompt("twin", w)
        out.append({"task": task, "arm": arm, "template": w, "sample_id": k, "slot": f"{task}|{w}|{k}",
                    "seed": stable_seed(task, w, k), "model": MODEL_ID, "model_revision": MODEL_REVISION,
                    "quant": QUANT, "decoding": DECODING_STR, "temperature": 1.0, "top_k": None, "thinking": False,
                    "site": "task_spec_12_23", "family": a["family"], "alpha": a.get("alpha"),
                    "direction_seed": a.get("seed"), "s_dose": a.get("s"), "axis": a.get("axis"),
                    "kind": "CLAMP" if a["family"] == "CLAMP" else (None if a["family"] == "TWIN" else "TARGET"),
                    "stage": stage, "prompt_sha256": p["prompt_sha256"], "block_id": block_id,
                    "rel_err_max": rerr, "text": tok.decode(r["token_ids"], skip_special_tokens=True),
                    "token_ids": r["token_ids"], "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                    "fence_step": r["fence_step"], "logprob_sum": r["logprob_sum"], "utc": utc_now(),
                    **(extra_meta or {})})
    append_jsonl(RAW, out)
    if recs:
        append_jsonl(REALISED, recs)
    dt = time.time() - t0
    append_jsonl(TIMING, [{"block_id": block_id, "task": task, "w": w, "arms": [x for x, _ in spec], "stage": stage,
                           "seconds": dt, "steps": res[0]["steps"], "utc": utc_now(),
                           "max_tokens": max(r["n_tokens"] for r in res)}])
    logger.info(f"{block_id} {task}/{w} {len(spec)} cells: {dt:.1f}s, {res[0]['steps']} steps")
    return out


def run_cells(model: Any, tok: Any, prompts: dict, task: str, cells_by_w: dict[str, list[tuple[str, list[int]]]],
              stage: str, deadline: float | None = None, save_geo: dict | None = None) -> int:
    """Run every not-yet-sampled (arm, slot) of cells_by_w for one task, template by template."""
    done = done_slots()
    used_twin: dict[str, set[int]] = {}
    for (t, w, arm, k) in done:
        if t == task and arm == "TWIN":
            used_twin.setdefault(w, set()).add(k)
    ctx = TaskCtx(model, prompts, task)
    nb = 0
    for w, cells in cells_by_w.items():
        todo = []
        for arm, ks in cells:
            rest = [k for k in ks if (task, w, arm, k) not in done]
            if arm == "TWIN":
                used_twin.setdefault(w, set()).update(rest)
            if rest:
                todo.append((arm, rest))
        if not todo:
            continue
        for bi, spec in enumerate(pack(todo, used_twin.setdefault(w, set()))):
            if deadline is not None and time.time() > deadline:
                logger.warning(f"deadline before {stage} {task}/{w} batch {bi}")
                ctx.release()
                return nb
            run_batch(ctx, tok, w, spec, f"{stage}:{task}:{w}:b{bi}:{int(time.time())}", stage, save_geo=save_geo)
            nb += 1
        ctx.release()
    return nb
