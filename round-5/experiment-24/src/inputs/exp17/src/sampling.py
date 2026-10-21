#!/usr/bin/env python3
"""S5 / S7: CRN sampling of every arm.

Batch layout: every batch has exactly 20 rows of ONE (task, template): either one 20-slot block (k 0-19) of an N=100
arm, or two 10-slot blocks of N=50 arms (k 0-9). Because every row's computation is independent of its batch-mates
for a fixed batch shape (per-token FP8 activation scales, no padding), a slot's uniforms u_stream(task, w, k) and the
batch shape are identical in every arm: exact CRN coupling. Raw rows stream to data/samples_raw.jsonl (resumable).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (BATCH, DATA_DIR, DECODING, HEAD_RAND_SEEDS, HEAD_TARGET, MODEL_ID, MODEL_REVISION, N_LAYERS, QUANT,
                 RAND_SEEDS, RESULTS_DIR, TEMPLATE_IDS, V_BLOCKS, append_jsonl, read_jsonl, stable_seed, utc_now,
                 write_json)
from direction import load_direction, load_rand
from engine import forward_capture, prefill, sample, u_stream
from hooks import head_masks, head_sets, make_edits, to_dev

RAW = DATA_DIR / "samples_raw.jsonl"
REALISED = DATA_DIR / "realised_norms.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
NORM_BLOCKS = list(range(12, N_LAYERS))  # realised displacement logged at blocks 12-35


def arm_def(arm: str) -> dict[str, Any]:
    """arm name -> {prompt, kind, alpha, dir, heads}."""
    if arm == "NEUTRAL":
        return {"prompt": "twin", "kind": None, "alpha": None, "dir": None}
    if arm in ("BAN", "BAN_TOPUP"):
        return {"prompt": "ban", "kind": None, "alpha": None, "dir": None}
    if arm.startswith("ADD_a"):
        return {"prompt": "twin", "kind": "ADD", "alpha": float(arm[5:]), "dir": "v"}
    if arm.startswith("RAND"):
        s, a = arm[4:].split("_a")
        return {"prompt": "twin", "kind": "RAND", "alpha": float(a), "dir": f"rand{s}"}
    if arm in ("SUB_plain", "SUB_affine"):
        return {"prompt": "ban", "kind": arm, "alpha": None, "dir": "v"}
    if arm.startswith("SUB_rand"):
        return {"prompt": "ban", "kind": "SUB_rand", "alpha": None, "dir": f"rand{arm[8:]}"}
    if arm.startswith("HEADS_"):
        return {"prompt": "ban", "kind": None, "alpha": None, "dir": None, "heads": arm[6:]}
    raise ValueError(arm)


K10 = list(range(10))
K20 = list(range(20))
K1020 = list(range(10, 20))


def s5_batches(optional: bool = False, extra: bool = False) -> list[list[tuple[str, list[int]]]]:
    req = [[("NEUTRAL", K20)],
           [("ADD_a1.0", K10), ("ADD_a2.0", K10)],
           [("RAND9001_a1.0", K10), ("RAND9002_a1.0", K10)],
           [("RAND9003_a1.0", K10), ("RAND9001_a2.0", K10)]]
    opt = [[("RAND9002_a2.0", K10), ("RAND9003_a2.0", K10)]]
    ext = [[("ADD_a0.5", K10), ("ADD_a1.0", K1020)]]
    return req + (opt if optional else []) + (ext if extra else [])


def s7_batches(task: str, heads: bool = True) -> list[list[tuple[str, list[int]]]]:
    out = [[("BAN", K20)]]
    if task in ("T1", "T2"):
        out += [[("SUB_plain", K10), ("SUB_affine", K10)], [("SUB_rand9001", K10), ("SUB_plain", K1020)]]
        if heads:
            out += [[("HEADS_target", K10), ("HEADS_rand7101", K10)], [("HEADS_rand7102", K10), ("HEADS_rand7103", K10)]]
    else:
        out += [[("SUB_plain", K20)]]
    return out


def done_slots() -> set[tuple[str, str, str, int]]:
    return {(r["task"], r["template"], r["arm"], int(r["sample_id"])) for r in read_jsonl(RAW)}


class _RandDirs(dict):
    """Random unit directions by seed: the frozen ones (9001-9003) from directions/, exploratory extra seeds created
    with the identical construction (one isotropic Gaussian per seed, PCG64, normalised) and saved on first use."""

    def __init__(self, dev: torch.device):
        super().__init__()
        self.dev = dev

    def __missing__(self, seed: int) -> torch.Tensor:
        from cfg import DIR_DIR, D_MODEL

        p = DIR_DIR / f"rand_{seed}.npy"
        if not p.exists():
            x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
            np.save(p, (x / np.linalg.norm(x)).astype(np.float32))
        v = torch.tensor(np.load(p), device=self.dev)
        self[seed] = v
        return v


class TaskContext:
    """Per (task, template): clean prefills of twin and ban with captured block outputs (blocks 12-35, S and R)."""

    def __init__(self, model: Any, tok: Any, prompts: dict, task: str):
        self.model, self.tok, self.task = model, tok, task
        self.pr = prompts
        d = load_direction(task)
        dev = model.device
        self.vhat = {l: torch.tensor(d["vhat"][j], device=dev) for j, l in enumerate(V_BLOCKS)}
        self.n = {l: torch.tensor(d["norms"][j], device=dev) for j, l in enumerate(V_BLOCKS)}
        self.rand = _RandDirs(dev)
        self.clean: dict[tuple[str, str], dict[str, Any]] = {}

    def clean_prefill(self, w: str, kind: str) -> dict[str, Any]:
        key = (w, kind)
        if key not in self.clean:
            p = self.pr[(self.task, w, kind)]
            a, b, P = p["p1"], p["spec_end"], p["P"]
            cap: dict[int, torch.Tensor] = {}
            capR: dict[int, torch.Tensor] = {}

            def mk(l):
                def g(h):
                    cap[l] = h[0, a:b].float().clone()
                    capR[l] = h[0, P - 1].float().clone()
                return g
            pre = prefill(self.model, p["ids"], capture={l: mk(l) for l in NORM_BLOCKS})
            self.clean[key] = {"pre": pre, "S": cap, "R": capR, "a": a, "b": b, "P": P}
        return self.clean[key]

    def arm_prefill(self, w: str, arm: str) -> tuple[dict[str, Any], dict[str, Any]]:
        ad = arm_def(arm)
        base = self.clean_prefill(w, ad["prompt"])
        if ad["kind"] is None:
            return base["pre"], {}
        twin = self.clean_prefill(w, "twin")
        a, b, P = base["a"], base["b"], base["P"]
        if ad["dir"] == "v":
            u = self.vhat
        else:
            r = self.rand[int(ad["dir"][4:])]
            u = {l: r for l in V_BLOCKS} if ad["kind"] == "RAND" else self.vhat
        rvec = self.rand[int(ad["dir"][4:])] if ad["kind"] == "SUB_rand" else None
        h_ref = {l: twin["S"][l] for l in V_BLOCKS}
        log: dict[int, list[float]] = {}
        edits = make_edits(ad["kind"], a, b, u, self.n, h_ref, alpha=ad["alpha"] or 0.0, r=rvec, log=log)
        cap: dict[int, torch.Tensor] = {}
        capR: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                cap[l] = h[0, a:b].float().clone()
                capR[l] = h[0, P - 1].float().clone()
            return g
        pre = prefill(self.model, self.pr[(self.task, w, ad["prompt"])]["ids"], edits=edits,
                      capture={l: mk(l) for l in NORM_BLOCKS})
        # realised displacement from the clean prompt of the same kind, and (ADD/RAND) along u vs target
        rec: dict[str, Any] = {"task": self.task, "w": w, "arm": arm, "edit_norm_mean": {l: float(np.mean(v))
                                                                                       for l, v in log.items()}}
        rec["disp_S_mean_norm"] = {l: float((cap[l] - base["S"][l]).norm(dim=-1).mean()) for l in NORM_BLOCKS}
        rec["disp_R_norm"] = {l: float((capR[l] - base["R"][l]).norm()) for l in NORM_BLOCKS}
        if ad["kind"] in ("ADD", "RAND"):
            relerr = {}
            for l in V_BLOCKS:
                comp = (cap[l] - twin["S"][l]) @ u[l]
                tgt = ad["alpha"] * self.n[l]
                relerr[l] = float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean())
            rec["rel_err_along_u"] = relerr
            rec["target_norm_mean"] = {l: float(ad["alpha"] * self.n[l].mean()) for l in V_BLOCKS}
        if ad["kind"] == "SUB_plain":
            rec["residual_proj_ratio_max"] = {l: float(((cap[l] @ self.vhat[l]).abs() / cap[l].norm(dim=-1)).max())
                                              for l in V_BLOCKS}
        append_jsonl(REALISED, [rec])
        return pre, rec


def head_mu(model: Any, prompts: dict, task: str, rows: list[dict[str, Any]]) -> dict[int, np.ndarray]:
    """Mean o_proj input at generated positions (blocks 21 and 26) over the task's NEUTRAL programs (teacher-forced)."""
    blocks = sorted({l for l, _ in HEAD_TARGET})
    sums = {l: torch.zeros(4096, dtype=torch.float64, device=model.device) for l in blocks}
    cnt = 0
    hs = []
    buf: dict[int, torch.Tensor] = {}

    def mk(l):
        def pre(mod, args):
            buf[l] = args[0]
            return None
        return pre
    for l in blocks:
        hs.append(model.model.layers[l].self_attn.o_proj.register_forward_pre_hook(mk(l)))
    try:
        for r in rows:
            p = prompts[(task, r["template"], "twin")]
            ids = p["ids"] + r["token_ids"]
            P = p["P"]
            with torch.no_grad():
                model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
            for l in blocks:
                sums[l] += buf[l][0, P:].double().sum(0)
            cnt += len(ids) - P
    finally:
        for h in hs:
            h.remove()
    return {l: (sums[l] / max(cnt, 1)).float().cpu().numpy() for l in blocks}


def run_batch(ctx: TaskContext, w: str, spec: list[tuple[str, list[int]]], block_id: str,
              mus: dict[int, np.ndarray] | None = None, ukey: tuple | None = None,
              arm_prefix: str = "") -> list[dict[str, Any]]:
    assert sum(len(ks) for _, ks in spec) == BATCH, spec
    model, tok, task = ctx.model, ctx.tok, ctx.task
    t0 = time.time()
    groups, meta, row_heads = [], [], []
    hsets = head_sets(HEAD_RAND_SEEDS)
    hsets["target"] = HEAD_TARGET
    for arm, ks in spec:
        pre, _ = ctx.arm_prefill(w, arm)
        keyf = (lambda k: (task, w, k)) if ukey is None else (lambda k: ukey + (w, k))
        groups.append({"pre": pre, "us": [u_stream(*keyf(k)) for k in ks]})
        ad = arm_def(arm)
        for k in ks:
            meta.append((arm, k, ad))
            row_heads.append(hsets[ad["heads"]] if ad.get("heads") else [])
    heads = None
    if any(row_heads):
        masks = head_masks(row_heads, model.device)
        heads = {"masks": masks, "mus": {l: torch.tensor(mus[l], device=model.device) for l in masks}}
    res = sample(model, groups, heads=heads)
    out = []
    for (arm, k, ad), r in zip(meta, res):
        p = ctx.pr[(task, w, ad["prompt"])]
        text = tok.decode(r["token_ids"], skip_special_tokens=True)
        out.append({"task": task, "condition": arm_prefix + arm, "arm": arm_prefix + arm, "template": w, "paraphrase_id": w, "sample_id": k,
                    "slot": f"{task}|{w}|{k}", "seed": stable_seed(*((task, w, k) if ukey is None else ukey + (w, k))),
                    "model": MODEL_ID, "model_revision": MODEL_REVISION, "quant": QUANT, "decoding": DECODING,
                    "alpha": ad.get("alpha"), "dir": ad.get("dir"), "heads": ad.get("heads"),
                    "prompt_kind": ad["prompt"], "prompt_sha256": p["prompt_sha256"], "block_id": block_id,
                    "text": text, "token_ids": r["token_ids"], "n_tokens": r["n_tokens"],
                    "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"], "utc": utc_now()})
    append_jsonl(RAW, out)
    dt = time.time() - t0
    append_jsonl(TIMING, [{"block_id": block_id, "task": task, "w": w, "arms": [a for a, _ in spec],
                           "seconds": dt, "steps": res[0]["steps"], "utc": utc_now()}])
    logger.info(f"{block_id} {task}/{w} {[a for a, _ in spec]}: {dt:.1f}s, {res[0]['steps']} steps, "
                f"max len {max(r['n_tokens'] for r in res)}")
    return out


def run_task_phase(model: Any, tok: Any, prompts: dict, task: str, batches: list[list[tuple[str, list[int]]]],
                   phase: str, mus: dict[int, np.ndarray] | None = None, templates: list[str] | None = None,
                   deadline: float | None = None) -> int:
    done = done_slots()
    ctx = TaskContext(model, tok, prompts, task)
    n = 0
    for w in templates or TEMPLATE_IDS:
        for bi, spec in enumerate(batches):
            if all((task, w, arm, k) in done for arm, ks in spec for k in ks):
                continue
            if deadline is not None and time.time() > deadline:
                logger.warning(f"deadline reached before {phase} {task}/{w} batch {bi}")
                return n
            run_batch(ctx, w, spec, f"{phase}:{task}:{w}:b{bi}", mus=mus)
            n += 1
        ctx.clean.clear()
        torch.cuda.empty_cache()
    return n
