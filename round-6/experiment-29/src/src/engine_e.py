#!/usr/bin/env python3
"""Generation engine of artifact E: a thin wrapper around exp19's engine_v4 / sampling_v4.

Reused unchanged: engine_v4.prefill (batch-1 prompt pass with block-output edit hooks), engine_v4.sample (float64
inverse-CDF CRN sampler, prune=False, fixed batch shape, fence stop every 8 steps), engine_v4.u_stream(task, w, k),
sampling_v4.TaskContext (clean twin prefill capturing S and R at blocks 12-35), sampling_v4.pn_direction /
load_norms and hooks.make_edits('RAND') (alpha * n[l,p] along u at blocks 12-23, spec positions [p1, spec_end),
prefill only; h_ref = THIS precision's own clean twin S-states).

Added here: arm decoding for the factorial (POP = exp22's fixed directions, PNF = PN seeds at the ban-free unit,
DITHER_*), one fixed batch shape for every cell, per-row precision / kernel / hook-hash logging, the realised-dose
ratio to the residual norm, and a resumable queue with time-only drops.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (MAX_NEW_TOKENS, MODEL_ID, MODEL_REVISION, NORM_BLOCKS, V_BLOCKS, append_jsonl, read_jsonl,
                 sha256_file, stable_seed, utc_now)
from cfg_e import (CHECKPOINT, E22, ENGINE_VARIANT, GEMM_BACKEND, QUANT_DESC, RAW_E, REALISED_E, ROOT, TIMING_E,
                   arm_def, sample_id)
from engine_v4 import prefill, sample, u_stream, vocab_len
from hooks import make_edits
from sampling_v4 import TaskContext, fence_for, max_new_for, pn_direction

HOOK_SHA = sha256_file(ROOT / "src" / "hooks.py")
_POP_U: dict[int, np.ndarray] = {}


def pop_direction(seed: int) -> np.ndarray:
    if seed not in _POP_U:
        u = np.load(E22 / "directions" / f"rand_{seed}.npy").astype(np.float32)
        _POP_U[seed] = u
    return _POP_U[seed]


class TaskContextE(TaskContext):
    """exp19 TaskContext + realised-dose ratios + dither-aware prefills. One context per (precision, task)."""

    def __init__(self, model: Any, tok: Any, prompts: dict, task: str, precision: str):
        super().__init__(model, tok, prompts, task)
        self.precision = precision
        self.n_free: dict[int, torch.Tensor] | None = None

    def banfree_unit(self, r_q: dict[int, float], templates: list[str]) -> np.ndarray:
        """n_free[l, p] = mean_w ||h_twin,P,w[l, p]|| * r_Q(l) at blocks 12-23 (this precision's own clean twins)."""
        acc = None
        for w in templates:
            S = self.clean_prefill(w, "twin")["S"]
            m = torch.stack([S[l].norm(dim=-1) for l in V_BLOCKS])     # [12, |S|]
            acc = m if acc is None else acc + m
        nf = (acc / len(templates)) * torch.tensor([r_q[l] for l in V_BLOCKS], device=acc.device)[:, None]
        self.n_free = {l: nf[j].float() for j, l in enumerate(V_BLOCKS)}
        return nf.cpu().numpy()

    def banfree_template(self, w: str, r_q: dict[int, float]) -> dict[int, torch.Tensor]:
        """exp27's ban-free unit (gen5.Ctx.banfree): ||h_twin,w[l, p]|| * r_Q(l) of THIS template's clean twin."""
        S = self.clean_prefill(w, "twin")["S"]
        return {l: (S[l].norm(dim=-1) * float(r_q[l])).float() for l in V_BLOCKS}

    def _realised(self, base: dict[str, Any], cap: dict, capR: dict, u: torch.Tensor | None, alpha: float | None,
                  n: dict[int, torch.Tensor] | None, tag: dict[str, Any]) -> dict[str, Any]:
        rec: dict[str, Any] = {"task": self.task, "precision": self.precision, **tag, "alpha": alpha}
        rec["disp_S"] = {str(l): round(float((cap[l] - base["S"][l]).norm(dim=-1).mean()), 4) for l in NORM_BLOCKS}
        rec["disp_R"] = {str(l): round(float((capR[l] - base["R"][l]).norm()), 4) for l in NORM_BLOCKS}
        if u is not None and alpha:
            relerr, comp_mean = {}, {}
            for l in V_BLOCKS:
                comp = (cap[l] - base["S"][l]) @ u
                tgt = alpha * n[l]
                relerr[str(l)] = round(float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean()), 6)
                comp_mean[str(l)] = round(float(comp.mean()), 4)
            rec["rel_err_along_u"] = relerr
            rec["u_component_mean"] = comp_mean
            rec["target_mean"] = {str(l): round(float(alpha * n[l].mean()), 4) for l in V_BLOCKS}
        ratio = {}
        for l in (12, 17, 23, 29, 35):
            d = (cap[l] - base["S"][l]).norm(dim=-1)
            h = base["S"][l].norm(dim=-1).clamp(min=1e-6)
            ratio[str(l)] = {"mean_of_ratios": round(float((d / h).mean()), 5),
                             "ratio_of_means": round(float(d.mean() / h.mean()), 5)}
        rec["ratio_to_residual"] = ratio
        return rec

    def pushed_prefill(self, w: str, u: torch.Tensor | None, alpha: float | None, tag: dict[str, Any],
                       n: dict[int, torch.Tensor] | None = None,
                       dither: tuple[int, int] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """make_edits('RAND') exactly as sampling_v4.TaskContext.edited_prefill (u None -> no edit: dither twin);
        dither = (variant, k) wraps the prefill in the dither context."""
        from dither import dither_prefill

        base = self.clean_prefill(w, "twin")
        a, b, P = base["a"], base["b"], base["P"]
        n = n or self.n
        edits = None
        if u is not None:
            uu = {l: u for l in V_BLOCKS}
            h_ref = {l: base["S"][l] for l in V_BLOCKS}
            edits = make_edits("RAND", a, b, uu, n, h_ref, alpha=alpha, log={})
        cap, capR, hooks = self._capture(a, b, P)
        ids = self.prompt(w, "twin")["ids"]
        if dither is not None:
            v, k = dither
            positions = list(range(a, b)) + ([P - 1] if v == 2 else [])
            with dither_prefill(self.task, v, w, k, positions):
                pre = prefill(self.model, ids, edits=edits, capture=hooks)
        else:
            pre = prefill(self.model, ids, edits=edits, capture=hooks)
        rec = self._realised(base, cap, capR, u, alpha, n, tag)
        del cap, capR
        return pre, rec


def _compact_disp(rec: dict[str, Any] | None) -> dict[str, Any] | None:
    if rec is None:
        return None
    out = {"disp_S": rec["disp_S"], "disp_R": rec["disp_R"], "ratio_to_residual": rec.get("ratio_to_residual")}
    if "rel_err_along_u" in rec:
        out["rel_err_along_u_max"] = max(rec["rel_err_along_u"].values())
        out["target_mean_b12"] = rec["target_mean"]["12"]
        out["target_mean_b23"] = rec["target_mean"]["23"]
        out["u_component_mean_b12"] = rec["u_component_mean"]["12"]
    return out


def run_batch_e(ctx: TaskContextE, w: str, spec: list[tuple[str, list[int]]], block_id: str, B_fixed: int,
                write: bool = True, stage: str = "factorial") -> list[dict[str, Any]]:
    """spec = [(arm, slots)] -> one fixed-shape batch of one (task, template, prompt ids)."""
    from dither import dither_decode

    model, tok, task, prec = ctx.model, ctx.tok, ctx.task, ctx.precision
    t0 = time.time()
    n_rows = sum(len(ks) for _, ks in spec)
    assert n_rows == B_fixed, f"batch {block_id} has {n_rows} rows, the fixed shape is {B_fixed}"
    groups, meta, realised = [], [], []
    dith = {arm_def(a)["dither"] for a, _ in spec} - {None}
    assert len(dith) <= 1, "one dither variant per batch"
    dvar = dith.pop() if dith else None
    for arm, ks in spec:
        A = arm_def(arm)
        if A["dither"] is not None:              # every dither row: its own batch-1 prefill
            for k in ks:
                if A["kind"] == "pn":
                    seed, u = pn_direction(task, A["seed_arm"], w, k)
                    ut = torch.tensor(u, device=model.device)
                    pre, rec = ctx.pushed_prefill(w, ut, A["alpha"], {"arm": arm, "slot": k, "direction_seed": seed},
                                                  dither=(A["dither"], k))
                else:
                    seed = None
                    pre, rec = ctx.pushed_prefill(w, None, None, {"arm": arm, "slot": k, "direction_seed": None},
                                                  dither=(A["dither"], k))
                groups.append({"pre": pre, "us": [u_stream(task, w, k)]})
                meta.append((arm, k, seed, rec))
                realised.append(rec)
        elif A["kind"] == "clean":
            base = ctx.clean_prefill(w, "twin")["pre"]
            groups.append({"pre": base, "us": [u_stream(task, w, k) for k in ks]})
            meta += [(arm, k, None, None) for k in ks]
        elif A["kind"] == "pn":
            n = ctx.n_free if A["unit"] == "banfree" else None
            assert A["unit"] != "banfree" or n is not None, "ban-free unit not computed"
            for k in ks:
                seed, u = pn_direction(task, A["seed_arm"], w, k)
                ut = torch.tensor(u, device=model.device)
                pre, rec = ctx.pushed_prefill(w, ut, A["alpha"], {"arm": arm, "slot": k, "direction_seed": seed}, n=n)
                groups.append({"pre": pre, "us": [u_stream(task, w, k)]})
                meta.append((arm, k, seed, rec))
                realised.append(rec)
        elif A["kind"] == "pn5":                 # POST-HOC replication of exp27's PN cells (seed tag 'PN5')
            from cfg_e import E23
            import json as _json
            rq = {int(l): float(v["median"]) for l, v in _json.loads((E23 / "results" / "qwen_ratio.json").read_text())[
                "r_Q"].items()}
            nb = ctx.banfree_template(w, rq)
            for k in ks:
                seed = stable_seed(task, "PN5", w, k)
                x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
                ut = torch.tensor((x / np.linalg.norm(x)).astype(np.float32), device=model.device)
                pre, rec = ctx.pushed_prefill(w, ut, A["alpha"], {"arm": arm, "slot": k, "direction_seed": seed}, n=nb)
                groups.append({"pre": pre, "us": [u_stream(task, w, k)]})
                meta.append((arm, k, seed, rec))
                realised.append(rec)
        elif A["kind"] == "pop":
            seed = A["dir_seed"]
            ut = torch.tensor(pop_direction(seed), device=model.device)
            pre, rec = ctx.pushed_prefill(w, ut, A["alpha"], {"arm": arm, "slot": list(ks), "direction_seed": seed})
            groups.append({"pre": pre, "us": [u_stream(task, w, k) for k in ks]})
            meta += [(arm, k, seed, rec) for k in ks]
            realised.append(rec)
        else:
            raise ValueError(arm)
    t_pre = time.time() - t0
    if dvar is not None:
        row_ks = [k for _, ks in spec for k in ks]
        with dither_decode(task, dvar, w, row_ks):
            res = sample(model, groups, max_new=max_new_for(task), fence=fence_for(task), tok=tok)
    else:
        res = sample(model, groups, max_new=max_new_for(task), fence=fence_for(task), tok=tok)
    p = ctx.prompt(w, "twin")
    nv = vocab_len(tok)
    out = []
    ev = ENGINE_VARIANT[prec]
    for (arm, k, seed, rec), r in zip(meta, res):
        A = arm_def(arm)
        text = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
        out.append({
            "sample_id": sample_id(task, prec, arm, w, k), "model": MODEL_ID, "model_revision": MODEL_REVISION,
            "checkpoint": CHECKPOINT, "unit": task, "task": task, "unit_kind": "existing", "arm": arm,
            "site": "S0_spec_b12_23" if A["alpha"] is not None else "none", "precision": prec,
            "engine_variant": ev, "gemm_backend": GEMM_BACKEND[ev], "quant": QUANT_DESC[prec],
            "batch_shape": B_fixed, "lambda": None, "alpha": A["alpha"],
            "unit_kind_dose": A["unit"], "dither_variant": A["dither"], "direction_seed": seed, "template": w,
            "slot": k, "crn_key": f"{task}|{w}|{k}", "u_seed": stable_seed(task, w, k), "temperature": 1.0,
            "top_k": 0, "thinking": False, "prompt_kind": "twin", "prompt_sha256": p["prompt_sha256"], "P": p["P"],
            "max_new": max_new_for(task), "stop_rule": f"im_end|fence:{fence_for(task)}", "block_id": block_id,
            "stage": stage, "text": text, "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
            "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"],
            "realised_disp": _compact_disp(rec), "hook_sha256": HOOK_SHA, "utc": utc_now()})
    dt = time.time() - t0
    if write:
        append_jsonl(RAW_E, out)
        if realised:
            append_jsonl(REALISED_E, [{**r, "block_id": block_id} for r in realised])
        append_jsonl(TIMING_E, [{"block_id": block_id, "stage": stage, "task": task, "precision": prec, "w": w,
                                 "arms": [a for a, _ in spec], "B": B_fixed, "seconds": round(dt, 2),
                                 "prefill_seconds": round(t_pre, 2), "steps": res[0]["steps"],
                                 "max_len": max(r["n_tokens"] for r in res),
                                 "n_length": sum(r["finish_reason"] == "length" for r in res), "utc": utc_now()}])
    logger.info(f"{block_id}: {dt:.1f}s (prefills {t_pre:.1f}s), {res[0]['steps']} steps, "
                f"cap hits {sum(r['finish_reason'] == 'length' for r in res)}/{B_fixed}")
    return out


def done_ids() -> set[str]:
    return {r["sample_id"] for r in read_jsonl(RAW_E)}


__all__ = ["TaskContextE", "run_batch_e", "done_ids", "pop_direction", "MAX_NEW_TOKENS"]
