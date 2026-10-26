#!/usr/bin/env python3
"""Generation runner (exp29 Runner design): every batch holds exactly B rows of ONE (task, template, prompt length);
the CRN uniforms of slot (task, template, k) are engine4.u_stream(task, template, k) in every arm, so arms are
paired per slot; the last batch of a template is padded with fresh TWIN slots k >= 10 (kept as extra twin rows).

An Arm supplies a prefill per (template) or per (template, k) (per-sample edits). Prefill edits act at the task-spec
positions of the prompt during the prompt prefill only. Rows -> data/samples_raw.jsonl; resumable by row key.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

import c7 as common
from c7 import (FENCE, MAX_NEW, MODEL_ID, MODEL_REVISION, RAW, RESULTS, append_jsonl, read_jsonl, stable_seed,
                    utc_now)
import engine7 as E

GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
PRECISION = "bf16 weights and activations (exp29 engine d numerics)"
B_TASK = {"T10": 24, "T03": 24, "T2": 16, "T1": 16}


@dataclass
class Arm:
    name: str
    prefill: Callable[[Any, str, int | None], tuple[dict[str, Any], dict[str, Any]]]   # (ctx, w, k) -> (pre, rec)
    per_sample: bool = False
    prompt_kind: str = "twin"
    meta: dict[str, Any] = field(default_factory=dict)


def row_key(r: dict[str, Any]) -> str:
    return f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"


def done_keys() -> set[str]:
    return {row_key(r) for r in read_jsonl(RAW)}


class Ctx:
    """Per-task context: prompt records, the vendored exp22 TaskCtx (clean twin prefill + S captures at blocks 12-35)
    and cached prefills of other prompt kinds."""

    def __init__(self, model: Any, task: str, prompts: dict[str, dict[str, Any]]):
        from ctx4 import TaskCtx
        self.model, self.task, self.prompts = model, task, prompts
        self.tc = TaskCtx(model, prompts, task)
        self.dev = E.dev_of(model)
        self.other: dict[str, dict[str, Any]] = {}

    def twin(self, w: str) -> dict[str, Any]:
        return self.tc.twin(w)

    def prompt(self, kind: str, w: str) -> dict[str, Any]:
        if kind == "twin":
            return self.tc.prompt("twin", w)
        return self.prompts[self.key(kind, w)]

    def key(self, kind: str, w: str) -> str:
        from c7 import DEFAULTS
        if kind == "ban":
            return f"{self.task}|ban|{DEFAULTS[self.task]}|{w}|-"
        return f"{self.task}|{kind}|-|{w}|-"

    def plain_prefill(self, kind: str, w: str) -> dict[str, Any]:
        k = f"{kind}|{w}"
        if k not in self.other:
            self.other[k] = E.prefill(self.model, self.prompt(kind, w)["ids"])
        return self.other[k]

    def release(self) -> None:
        self.tc.release()
        self.other.clear()
        torch.cuda.empty_cache()


def realised(ctx: Ctx, w: str, edits: dict, extra_dirs: dict[str, tuple[int, torch.Tensor]] | None = None
             ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prefill of the twin prompt with `edits`, capturing S at blocks 12-35; returns (pre, realised summary)."""
    from c7 import CAP_BLOCKS
    tw = ctx.twin(w)
    a, b = tw["a"], tw["b"]
    H: dict[int, torch.Tensor] = {}
    pre = E.prefill(ctx.model, tw["prompt"]["ids"], edits=edits, capture=E.capture_S(H, a, b, CAP_BLOCKS))
    d = {l: (H[l] - tw["S"][l]) for l in CAP_BLOCKS}
    rec = {"S_b12": float(d[12].mean(0).norm()), "S_b23": float(d[23].mean(0).norm()),
           "S_b35": float(d[35].mean(0).norm()),
           "pos_rms_b12": float(d[12].norm(dim=-1).pow(2).mean().sqrt()),
           "pos_rms_b23": float(d[23].norm(dim=-1).pow(2).mean().sqrt())}
    for name, (l, u) in (extra_dirs or {}).items():
        rec[f"proj_{name}_L{l}"] = float((d[l] @ u).mean())
        rec[f"pos_rms_L{l}"] = float(d[l].norm(dim=-1).pow(2).mean().sqrt())
    del H, d
    return pre, rec


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


def twin_arm() -> Arm:
    return Arm("TWIN", lambda ctx, w, k: (ctx.twin(w)["pre"], {}), meta={"family": "TWIN"})


def run_cells(model: Any, tok: Any, ctx: Ctx, arms: dict[str, Arm], cells: list[tuple[str, list[int]]], stage: str,
              templates: tuple[str, ...] = tuple(common.TEMPLATES), deadline: float | None = None) -> int:
    """cells: [(arm_name, ks)]; arms of different prompt kinds are packed into separate batches (prompt length)."""
    from engine4 import u_stream
    task = ctx.task
    B = B_TASK[task]
    arms = {"TWIN": twin_arm(), **arms}
    done = done_keys()
    used_twin: dict[str, set[int]] = {}
    for key in done:
        t, w, arm, k = key.split("|")
        if t == task and arm == "TWIN":
            used_twin.setdefault(w, set()).add(int(k))
    nb = 0
    for w in templates:
        by_kind: dict[str, list[tuple[str, list[int]]]] = {}
        for arm, ks in cells:
            rest = [k for k in ks if f"{task}|{w}|{arm}|{k}" not in done]
            if arm == "TWIN":
                used_twin.setdefault(w, set()).update(rest)
            if rest:
                by_kind.setdefault(arms[arm].prompt_kind, []).append((arm, rest))
        for kind, todo in by_kind.items():
            if kind != "twin":
                # filler rows must share the prompt length: pad with the same arm's extra slots instead of TWIN
                pass
            for spec in pack(todo, used_twin.setdefault(w, set()), B):
                if kind != "twin":
                    spec = [(a if a != "TWIN" else todo[0][0], ks) for a, ks in spec]
                if deadline is not None and time.time() > deadline:
                    logger.warning(f"deadline reached before {stage} {task}/{w}")
                    return nb
                run_batch(model, tok, ctx, w, arms, spec, stage, u_stream)
                nb += 1
    return nb


def run_batch(model: Any, tok: Any, ctx: Ctx, w: str, arms: dict[str, Arm], spec: list[tuple[str, list[int]]],
              stage: str, u_stream: Callable) -> list[dict[str, Any]]:
    task = ctx.task
    t0 = time.time()
    mx = MAX_NEW[task]
    groups, meta = [], []
    for arm_name, ks in spec:
        arm = arms[arm_name]
        if arm.per_sample:
            for k in ks:
                pre, rec = arm.prefill(ctx, w, k)
                groups.append({"pre": pre, "us": [u_stream(task, w, k, n=mx)]})
                meta.append((arm, k, rec))
        else:
            pre, rec = arm.prefill(ctx, w, None)
            groups.append({"pre": pre, "us": [u_stream(task, w, k, n=mx) for k in ks]})
            meta += [(arm, k, rec) for k in ks]
    Ps = {g["pre"]["P"] for g in groups}
    assert len(Ps) == 1, f"mixed prompt lengths in one batch: {Ps}"
    res = E.sample(model, tok, groups, FENCE[task], mx)
    del groups
    block_id = f"{stage}:{task}:{w}:{int(t0 * 1000)}"
    out = []
    for (arm, k, rec), r in zip(meta, res):
        p = ctx.prompt(arm.prompt_kind, w)
        out.append({"task": task, "arm": arm.name, "template": w, "sample_id": k, "slot": f"{task}|{w}|{k}",
                    "seed": stable_seed(task, w, k), "family": arm.meta.get("family", arm.name.split("_")[0]),
                    **{kk: vv for kk, vv in arm.meta.items() if kk != "family"},
                    "model": MODEL_ID, "model_revision": MODEL_REVISION, "precision": PRECISION, "gpu": GPU_NAME,
                    "B": len(res), "temperature": 1.0, "top_p": 1.0, "top_k": None, "thinking": False,
                    "max_new": mx, "stage": stage, "prompt_kind": arm.prompt_kind,
                    "prompt_sha256": p["prompt_sha256"], "noun": p.get("noun"), "block_id": block_id,
                    "realised_disp": rec or None, "text": tok.decode(r["token_ids"], skip_special_tokens=True),
                    "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                    "fence_step": r.get("fence_step"), "logprob_sum": r.get("logprob_sum"), "utc": utc_now()})
    append_jsonl(RAW, out)
    dt = time.time() - t0
    append_jsonl(RESULTS / "timing.jsonl", [{"stage": stage, "task": task, "w": w, "B": len(res), "seconds": dt,
                                             "steps": res[0]["steps"], "per_sample_s": dt / len(res),
                                             "utc": utc_now()}])
    logger.info(f"{stage} {task}/{w} {[a for a, _ in spec]}: {dt:.1f}s, {res[0]['steps']} steps")
    return out


# ------------------------------------------------------------------------------------------------ arm factories
def pop_arm(seed: int, alpha: float, task: str, u: np.ndarray | None = None, name: str | None = None,
            extra: Callable[[Ctx, str], dict] | None = None, meta: dict | None = None) -> Arm:
    """exp22 push_spec TARGET push: displacement from the clean twin along u is exactly alpha * n[l, p] at blocks
    12-23 (absolute ban unit), task-spec positions, prefill only. `extra(ctx, w)` adds further per-block edits applied
    after the push at the same block (used by the mediator clamp)."""
    from ctx4 import ban_unit, push_spec, rand_dir
    from hooks4 import make_edits_v4

    def f(ctx: Ctx, w: str, k: int | None):
        uu = rand_dir(seed) if u is None else u
        sp = push_spec(ctx.dev, uu, ban_unit(task), alpha)
        tw = ctx.twin(w)
        edits = make_edits_v4("TARGET", tw["a"], tw["b"], sp["U"], sp["M"], {l: tw["S"][l] for l in sp["U"]})
        if extra is not None:
            edits = E.compose(edits, extra(ctx, w))
        return realised(ctx, w, edits)
    return Arm(name or f"POP_d{seed}_a{alpha}", f, meta={"family": "POP", "alpha": alpha, "direction_seed": seed,
                                                            "site": "S0 blocks 12-23", **(meta or {})})
