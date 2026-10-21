#!/usr/bin/env python3
"""CRN sampling of every arm (exp19 sampling_v4.TaskContext / run_batch, adapted to the ban-free unit, the base
model and the iteration-5 arm names).

Arms (name -> prompt kind, temperature, push):
  TWIN      twin W1-W5, T 1.0                       BASE     base model on the twin ids, T 1.0
  PLAINC    base plain completion (raw text)        NOVELTY  novelty prompt (CRN key (task, 'ALL', k))
  ASSOC     association prompt, max_new 64          T1.3     twin, T 1.3 (same CRN streams as the twin)
  ESC_d<s>_a<a>  twin + fixed direction rand_dir(s) at alpha a (ban-free unit), prefill only, blocks 12-23
  PN_a<a>        twin + a fresh direction per row, seed stable_seed('i5A', 'PN', task, a, w, k)
  ECTWIN / ECBAN_d<s>_a1.0   engine check (exp19 'NEUTRAL' / 'RAND<s>_a1.0' with exp17's ban unit)
A batch holds rows of ONE prompt (same ids); each push row group gets its own batch-1 edited prefill.
"""

from __future__ import annotations

import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg5 import (D_MODEL, E17, E23, MAX_NEW_ASSOC, MAX_NEW_BENCH, MAX_NEW_PATH, MODELS, NORM_BLOCKS, PATH_TASKS,
                  RAW_DIR, RESULTS, STATES, V_BLOCKS, append_jsonl, read_json, read_jsonl, stable_seed, utc_now)
from engine5 import prefill, sample, u_stream, vocab_len
from hooks5 import make_edits

REALISED = RESULTS / "realised.jsonl"
TIMING = RESULTS / "timing.jsonl"
_RQ: dict[str, Any] = {}


def r_at(l: int, key: str = "r_Q", n_layers: int = 36) -> float:
    """exp23 units.r_at: linear interpolation of r_Q over relative depth (l + 1) / 36 (clamped)."""
    if key not in _RQ:
        q = read_json(E23 / "results" / "qwen_ratio.json")[key]
        d = np.array([v["depth"] for v in q.values()])
        r = np.array([v["median"] for v in q.values()])
        o = np.argsort(d)
        _RQ[key] = (d[o], r[o])
    d, r = _RQ[key]
    return float(np.interp((l + 1) / n_layers, d, r))


def rand_dir(seed: int) -> np.ndarray:
    """exp22 ctx4.rand_dir / exp17 _RandDirs: PCG64(seed).standard_normal(4096), normalised (float32 as stored)."""
    src = E17 / "directions" / f"rand_{seed}.npy"
    if src.exists():
        return np.load(src).astype(np.float32)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


def pn_direction(task: str, alpha: float, w: str, k: int) -> tuple[int, np.ndarray]:
    seed = stable_seed("i5A", "PN", task, alpha, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def parse_arm(arm: str) -> dict[str, Any]:
    """Arm name -> definition."""
    if arm in ("TWIN", "ECTWIN"):
        return {"prompt": "twin", "T": 1.0, "alpha": None, "crn": "w"}
    if arm == "BASE":
        return {"prompt": "twin", "T": 1.0, "alpha": None, "crn": "w"}
    if arm == "PLAINC":
        return {"prompt": "plainc", "T": 1.0, "alpha": None, "crn": "PLAINC"}
    if arm == "NOVELTY":
        return {"prompt": "novelty", "T": 1.0, "alpha": None, "crn": "ALL"}
    if arm == "ASSOC":
        return {"prompt": "assoc", "T": 1.0, "alpha": None, "crn": "ASSOC"}
    if arm == "T1.3":
        return {"prompt": "twin", "T": 1.3, "alpha": None, "crn": "w"}
    m = re.fullmatch(r"(ESC|ECBAN)_d(\d+)_a([\d.]+)", arm)
    if m:
        return {"prompt": "twin", "T": 1.0, "alpha": float(m.group(3)), "crn": "w", "fixed_seed": int(m.group(2)),
                "unit": "banfree" if m.group(1) == "ESC" else "exp17ban"}
    m = re.fullmatch(r"PN_a([\d.]+)", arm)
    if m:
        return {"prompt": "twin", "T": 1.0, "alpha": float(m.group(1)), "crn": "w", "fixed_seed": None,
                "unit": "banfree"}
    raise ValueError(f"unknown arm {arm}")


def max_new_for(task: str, kind: str) -> int:
    if kind == "assoc":
        return MAX_NEW_ASSOC
    if kind == "plainc":
        return 512
    return MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_BENCH


def fence_for(task: str, kind: str) -> str | None:
    if kind == "assoc":
        return None
    if kind == "plainc":
        return "plain"
    return "path" if task in PATH_TASKS else "bench"


class TaskContext:
    """Per task: clean prefills (block outputs captured at S and R, blocks 12-35) and per-row edited prefills."""

    def __init__(self, model: Any, tok: Any, prompts: dict, task: str, which: str):
        self.model, self.tok, self.task, self.pr, self.which = model, tok, task, prompts, which
        self.clean: dict[tuple[str, str], dict[str, Any]] = {}
        self.units: dict[tuple[str, str], dict[int, torch.Tensor]] = {}

    def prompt(self, w: str, kind: str) -> dict[str, Any]:
        if kind == "twin":
            return self.pr[(self.task, w, "twin")]
        if kind in ("novelty", "plain"):
            return self.pr[(self.task, "ALL", kind)]
        if kind == "plainc":
            return self.pr[(self.task, "PLAINC", "plainc")]
        if kind == "assoc":
            return self.pr[(self.task, "ASSOC", "assoc")]
        raise KeyError(kind)

    def _capture(self, a: int, b: int, P: int):
        cap: dict[int, torch.Tensor] = {}
        capR: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                cap[l] = h[0, a:b].float().clone()
                capR[l] = h[0, P - 1].float().clone()
            return g
        return cap, capR, {l: mk(l) for l in NORM_BLOCKS}

    def clean_prefill(self, w: str, kind: str) -> dict[str, Any]:
        p = self.prompt(w, kind)
        key = (p["w"], kind)
        if key not in self.clean:
            a, b, P = p["p1"], p["spec_end"], p["P"]
            if kind in ("twin", "novelty", "plain"):
                cap, capR, hooks = self._capture(a, b, P)
                pre = prefill(self.model, p["ids"], capture=hooks)
            else:
                cap, capR = {}, {}
                pre = prefill(self.model, p["ids"])
            self.clean[key] = {"pre": pre, "S": cap, "R": capR, "a": a, "b": b, "P": P}
        return self.clean[key]

    def unit(self, w: str, kind: str, which_unit: str) -> dict[int, torch.Tensor]:
        """Ban-free unit n[l, p] = ||h_twin_clean[l, p]|| * r_Q(l) (per template), or exp17's ban unit (EC)."""
        key = (w, which_unit)
        if key not in self.units:
            if which_unit == "exp17ban":
                nm = np.load(E17 / "directions" / f"norms_{self.task}.npy").astype(np.float32)
                self.units[key] = {l: torch.tensor(nm[j], device=self.model.device) for j, l in enumerate(V_BLOCKS)}
            else:
                base = self.clean_prefill(w, kind)
                self.units[key] = {l: base["S"][l].norm(dim=-1) * r_at(l, "r_Q") for l in V_BLOCKS}
        return self.units[key]

    def save_states(self) -> dict[str, Any]:
        """Per template: the ban-free unit n[l, p] (blocks 12-23), the read-position states and the spec-mean states
        (blocks 12-35, fp16) -> states/<task>.npz."""
        out: dict[str, np.ndarray] = {}
        summ = {}
        for w in ("W1", "W2", "W3", "W4", "W5"):
            base = self.clean_prefill(w, "twin")
            n = self.unit(w, "twin", "banfree")
            out[f"{w}_n"] = np.stack([n[l].cpu().numpy() for l in V_BLOCKS]).astype(np.float32)
            out[f"{w}_R"] = np.stack([base["R"][l].cpu().numpy() for l in NORM_BLOCKS]).astype(np.float16)
            out[f"{w}_Smean"] = np.stack([base["S"][l].mean(0).cpu().numpy() for l in NORM_BLOCKS]).astype(np.float16)
            out[f"{w}_Snorm"] = np.stack([base["S"][l].norm(dim=-1).cpu().numpy() for l in NORM_BLOCKS]).astype(
                np.float32)
            summ[w] = {"n_mean_b12": float(n[12].mean()), "n_mean_b23": float(n[23].mean()),
                       "S_len": int(base["b"] - base["a"])}
        np.savez_compressed(STATES / f"{self.task}.npz", **out)
        return summ

    def edited_prefill(self, w: str, kind: str, u: torch.Tensor, alpha: float, n: dict[int, torch.Tensor],
                       tag: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """exp19 make_edits('RAND'): displacement-targeted along u at blocks 12-23, spec positions, prefill only."""
        base = self.clean_prefill(w, kind)
        a, b, P = base["a"], base["b"], base["P"]
        uu = {l: u for l in V_BLOCKS}
        h_ref = {l: base["S"][l] for l in V_BLOCKS}
        edits = make_edits("RAND", a, b, uu, n, h_ref, alpha=alpha)
        cap, capR, hooks = self._capture(a, b, P)
        pre = prefill(self.model, self.prompt(w, kind)["ids"], edits=edits, capture=hooks)
        rec: dict[str, Any] = {"task": self.task, "w": w, **tag, "alpha": alpha}
        disp_S, ucomp, relerr = {}, {}, {}
        for l in NORM_BLOCKS:
            dlt = cap[l] - base["S"][l]
            disp_S[l] = round(float(dlt.norm(dim=-1).mean()), 4)
            ucomp[l] = round(float((dlt @ u).mean()), 4)
        for l in V_BLOCKS:
            comp = (cap[l] - base["S"][l]) @ u
            tgt = alpha * n[l]
            relerr[l] = round(float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean()), 6) if alpha else \
                round(float(comp.abs().max()), 6)
        rec["disp_S"] = disp_S
        rec["ucomp_S"] = ucomp
        rec["disp_R"] = {l: round(float((capR[l] - base["R"][l]).norm()), 4) for l in NORM_BLOCKS}
        rec["rel_err_along_u"] = relerr
        rec["target_mean"] = {l: round(float(alpha * n[l].mean()), 4) for l in V_BLOCKS}
        pre_blocks = [l for l in range(12)]
        rec["pre_block_untouched"] = pre_blocks[-1] == 11
        del cap, capR
        return pre, rec


def run_batch(ctx: TaskContext, w: str, spec: list[tuple[str, list[int]]], block_id: str,
              write: bool = True, out_file: str | None = None) -> list[dict[str, Any]]:
    """spec = [(arm, slots)]; every row of the batch shares the prompt ids. Rows -> data/raw/<task>.jsonl."""
    model, tok, task = ctx.model, ctx.tok, ctx.task
    t0 = time.time()
    groups, meta, temps, realised = [], [], [], []
    defs = {arm: parse_arm(arm) for arm, _ in spec}
    kinds = {d["prompt"] for d in defs.values()}
    assert len(kinds) == 1, f"mixed prompt kinds in one batch: {spec}"
    kind = kinds.pop()
    p = ctx.prompt(w, kind)
    for arm, ks in spec:
        a = defs[arm]
        crn_w = w if a["crn"] == "w" else a["crn"]
        if a["alpha"] is not None:
            n = ctx.unit(w, kind, a["unit"])
            if a["fixed_seed"] is not None:
                seed = a["fixed_seed"]
                ut = torch.tensor(rand_dir(seed), device=model.device)
                pre, rec = ctx.edited_prefill(w, kind, ut, a["alpha"], n, {"arm": arm, "direction_seed": seed})
                groups.append({"pre": pre, "us": [u_stream(task, crn_w, k, n=max_new_for(task, kind)) for k in ks]})
                meta += [(arm, k, seed, rec) for k in ks]
                realised.append(rec)
            else:
                for k in ks:
                    seed, u = pn_direction(task, a["alpha"], w, k)
                    ut = torch.tensor(u, device=model.device)
                    pre, rec = ctx.edited_prefill(w, kind, ut, a["alpha"], n,
                                                  {"arm": arm, "slot": k, "direction_seed": seed})
                    groups.append({"pre": pre, "us": [u_stream(task, crn_w, k, n=max_new_for(task, kind))]})
                    meta.append((arm, k, seed, rec))
                    realised.append(rec)
        else:
            base = ctx.clean_prefill(w, kind)["pre"]
            groups.append({"pre": base, "us": [u_stream(task, crn_w, k, n=max_new_for(task, kind)) for k in ks]})
            meta += [(arm, k, None, None) for k in ks]
        temps += [float(a["T"])] * len(ks)
    fk = fence_for(task, kind)
    res = sample(model, groups, max_new=max_new_for(task, kind), temps=temps, fence=fk, tok=tok)
    out = []
    B = len(res)
    nv = vocab_len(tok)
    for (arm, k, seed, rec), r in zip(meta, res):
        a = defs[arm]
        crn_w = w if a["crn"] == "w" else a["crn"]
        text = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
        disp = None
        if rec is not None:
            disp = {"S_b12": rec["disp_S"][12], "S_b23": rec["disp_S"][23], "S_b35": rec["disp_S"][35],
                    "u_b12": rec["ucomp_S"][12], "u_b23": rec["ucomp_S"][23], "R_b23": rec["disp_R"][23],
                    "R_b35": rec["disp_R"][35], "relerr_u_max": max(rec["rel_err_along_u"].values()),
                    "target_b12": rec["target_mean"][12]}
        out.append({"task": task, "arm": arm, "template": w, "slot": k, "model": ctx.which,
                    "model_id": MODELS[ctx.which]["id"], "model_revision": MODELS[ctx.which]["revision"],
                    "sample_id": f"{task}|{arm}|{ctx.which}|{w}|{k}", "crn_key": f"{task}|{crn_w}|{k}",
                    "direction_seed": seed, "alpha": a["alpha"], "unit_kind": a.get("unit"),
                    "site": "spec_b12_23" if a["alpha"] is not None else None, "lambda": None,
                    "temperature": a["T"], "top_k": 0, "thinking": False, "prompt_kind": kind,
                    "prompt_sha256": p["prompt_sha256"], "P": p["P"], "precision": "bf16",
                    "max_new": max_new_for(task, kind), "stop_rule": f"stop_ids|fence:{fk}", "block_id": block_id,
                    "batch_B": B, "text": text, "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
                    "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"], "realised_disp": disp,
                    "utc": utc_now()})
    if write:
        append_jsonl(RAW_DIR / (out_file or f"{task}.jsonl"), out)
        if realised:
            append_jsonl(REALISED, realised)
    dt = time.time() - t0
    rec_t = {"block_id": block_id, "task": task, "w": w, "model": ctx.which, "arms": [a for a, _ in spec], "B": B,
             "seconds": round(dt, 2), "steps": res[0]["steps"], "max_len": max(r["n_tokens"] for r in res),
             "n_length": sum(r["finish_reason"] == "length" for r in res),
             "tokens": int(sum(r["n_tokens"] for r in res)), "utc": utc_now()}
    if write:
        append_jsonl(TIMING, [rec_t])
    logger.info(f"{block_id} {task}/{w} {[a for a, _ in spec]}: {dt:.1f}s, {res[0]['steps']} steps, B={B}, "
                f"cap hits {rec_t['n_length']}/{B}")
    return out


def done_keys(task: str, out_file: str | None = None) -> set[tuple[str, str, str, int]]:
    """Slots already sampled for this task (the shared engine-check file holds two tasks, so filter by task)."""
    return {(r["arm"], r["model"], r["template"], int(r["slot"]))
            for r in read_jsonl(RAW_DIR / (out_file or f"{task}.jsonl")) if r["task"] == task}
