#!/usr/bin/env python3
"""Stage 1 generation: CRN sampling of every knob arm (exp17 sampling.py, extended).

Batch layout: a batch holds rows of ONE (task, template, prompt-ids). Twin-prompt arms run as 20-row batches of two
10-slot blocks (k 0-9) in the plan's pairs; PLAIN pairs with PNPLAIN_a1 (identical ids); NONCE, NOVELTY, SEMSEED, VS
(and a lone MINP_T1.6 block) run as 10-row batches with their own fixed shape. Every PN row gets its own batch-1
prefill with a fresh direction (seed_k = stable_seed(task, arm, w, k)) and is a group of one in the batch. CRN keys
u_stream(task, w, k) are shared by every arm. Raw rows stream to data/samples_raw.jsonl (resumable by slot).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (ARMS, BENCH12, D_MODEL, DATA_DIR, E13, E17, ENGINE_TAG, MAX_NEW_PATH, MAX_NEW_TOKENS, MODEL_ID,
                 MODEL_REVISION, NORM_BLOCKS, PATH_TASKS, QUANT, RESULTS_DIR, V_BLOCKS, append_jsonl, read_jsonl,
                 stable_seed, utc_now)
from engine_v4 import prefill, sample, u_stream, vocab_len
from hooks import make_edits
from prompts_v4 import prompt_for

RAW = DATA_DIR / "samples_raw.jsonl"
REALISED = DATA_DIR / "realised.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"


def max_new_for(task: str) -> int:
    return MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_TOKENS


def fence_for(task: str) -> str:
    return "path" if task in PATH_TASKS else "bench"


def load_norms(task: str, source: str = "stage1") -> np.ndarray:
    """Ban unit n[l, p] for l in blocks 12-23 (rows) and spec positions (cols). Stage 1: exp13 npz 'norm' for the 12
    bench tasks, exp17 norms_T1/T2.npy for the path tasks, the ban-free unit for R2. Engine check: exp17's files."""
    if task == "R2":
        return np.load(RESULTS_DIR / "unit_R2.npy").astype(np.float32)
    if task in PATH_TASKS or source == "exp17":
        return np.load(E17 / "directions" / f"norms_{task}.npy").astype(np.float32)
    return np.load(E13 / "results" / "tensors" / f"norms_{task}.npz")["norm"].astype(np.float32)


def pn_direction(task: str, arm: str, w: str, k: int) -> tuple[int, np.ndarray]:
    seed = stable_seed(task, arm, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def done_slots() -> set[tuple[str, str, str, int]]:
    return {(r["task"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(RAW)}


class TaskContext:
    """Per task: clean prefills (with captured block outputs at S and R, blocks 12-35) and per-row PN prefills."""

    def __init__(self, model: Any, tok: Any, prompts: dict, task: str, norms: np.ndarray | None = None,
                 log_realised: bool = True):
        self.model, self.tok, self.task, self.pr = model, tok, task, prompts
        nm = load_norms(task) if norms is None else norms
        dev = model.device
        self.n = {l: torch.tensor(nm[j], device=dev) for j, l in enumerate(V_BLOCKS)}
        self.clean: dict[tuple[str, str], dict[str, Any]] = {}
        self.log_realised = log_realised

    def prompt(self, w: str, kind: str) -> dict[str, Any]:
        return prompt_for(self.pr, self.task, w, kind)

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
            cap, capR, hooks = self._capture(a, b, P)
            pre = prefill(self.model, p["ids"], capture=hooks)
            self.clean[key] = {"pre": pre, "S": cap, "R": capR, "a": a, "b": b, "P": P}
        return self.clean[key]

    def edited_prefill(self, w: str, kind: str, u: torch.Tensor, alpha: float, tag: dict[str, Any],
                       n: dict[int, torch.Tensor] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """exp17 make_edits('RAND'): displacement-targeted along u at blocks 12-23 and spec positions, prefill only;
        the reference is the clean prompt of the same kind. Logs the realised displacement."""
        base = self.clean_prefill(w, kind)
        a, b, P = base["a"], base["b"], base["P"]
        n = n or self.n
        uu = {l: u for l in V_BLOCKS}
        h_ref = {l: base["S"][l] for l in V_BLOCKS}
        log: dict[int, list[float]] = {}
        edits = make_edits("RAND", a, b, uu, n, h_ref, alpha=alpha, log=log)
        cap, capR, hooks = self._capture(a, b, P)
        pre = prefill(self.model, self.prompt(w, kind)["ids"], edits=edits, capture=hooks)
        rec: dict[str, Any] = {"task": self.task, "w": w, **tag, "alpha": alpha}
        if self.log_realised:
            rec["disp_S"] = {l: round(float((cap[l] - base["S"][l]).norm(dim=-1).mean()), 4) for l in NORM_BLOCKS}
            rec["disp_R"] = {l: round(float((capR[l] - base["R"][l]).norm()), 4) for l in NORM_BLOCKS}
            relerr = {}
            for l in V_BLOCKS:
                comp = (cap[l] - base["S"][l]) @ u
                tgt = alpha * n[l]
                relerr[l] = round(float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean()), 6) if alpha else \
                    round(float(comp.abs().max()), 6)
            rec["rel_err_along_u"] = relerr
            rec["target_mean"] = {l: round(float(alpha * n[l].mean()), 4) for l in V_BLOCKS}
        del cap, capR
        return pre, rec


def run_batch(ctx: TaskContext, w: str, spec: list[tuple[str, list[int]]], block_id: str,
              fence: str | None = "auto", arm_defs: dict[str, dict[str, Any]] | None = None,
              write: bool = True) -> list[dict[str, Any]]:
    """spec = [(arm, slots)]; every row of the batch shares the prompt ids. Returns the raw rows (also appended to
    data/samples_raw.jsonl when write=True)."""
    model, tok, task = ctx.model, ctx.tok, ctx.task
    defs = arm_defs or ARMS
    t0 = time.time()
    groups, meta, temps, topks, minps, realised = [], [], [], [], [], []
    kinds = {defs[arm]["prompt"] for arm, _ in spec}
    assert len({ctx.prompt(w, k)["prompt_sha256"] for k in kinds}) == 1, f"mixed prompt ids in one batch: {spec}"
    for arm, ks in spec:
        a = defs[arm]
        kind = a["prompt"]
        if a.get("alpha") is not None or a.get("fixed_dir") is not None:
            for k in ks:
                if a.get("fixed_dir") is not None:
                    seed, u = a["fixed_seed"], a["fixed_dir"]
                else:
                    seed, u = pn_direction(task, arm, w, k)
                ut = torch.tensor(u, device=model.device)
                pre, rec = ctx.edited_prefill(w, kind, ut, float(a["alpha"]),
                                              {"arm": arm, "slot": k, "direction_seed": seed}, n=a.get("norms"))
                groups.append({"pre": pre, "us": [u_stream(task, w, k)]})
                meta.append((arm, k, seed, rec))
                realised.append(rec)
        else:
            base = ctx.clean_prefill(w, kind)["pre"]
            groups.append({"pre": base, "us": [u_stream(task, w, k) for k in ks]})
            meta += [(arm, k, None, None) for k in ks]
        temps += [float(a["T"])] * len(ks)
        topks += [int(a["top_k"])] * len(ks)
        minps += [float(a["min_p"])] * len(ks)
    fk = fence_for(task) if fence == "auto" else fence
    res = sample(model, groups, max_new=max_new_for(task), temps=temps, top_ks=topks, min_ps=minps, fence=fk,
                 tok=tok)
    out = []
    B = len(res)
    for (arm, k, seed, rec), r in zip(meta, res):
        a = defs[arm]
        p = ctx.prompt(w, a["prompt"])
        nv = vocab_len(tok)
        text = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
        disp = None
        if rec is not None and "disp_S" in rec:
            disp = {"S_b12": rec["disp_S"][12], "S_b23": rec["disp_S"][23], "S_b35": rec["disp_S"][35],
                    "R_b23": rec["disp_R"][23], "R_b35": rec["disp_R"][35],
                    "relerr_u_max": max(rec["rel_err_along_u"].values())}
        out.append({"task": task, "arm": arm, "knob_class": a.get("knob"), "template": w, "slot": k,
                    "sample_id": f"{task}|{arm}|{w}|{k}", "crn_key": f"{task}|{w}|{k}",
                    "u_seed": stable_seed(task, w, k), "direction_seed": seed, "alpha": a.get("alpha"),
                    "site": "spec_12_23" if a.get("alpha") is not None else None,
                    "temperature": a["T"], "top_k": a["top_k"], "min_p": a["min_p"], "thinking": False,
                    "prompt_kind": a["prompt"], "prompt_sha256": p["prompt_sha256"], "P": p["P"],
                    "model": MODEL_ID, "model_revision": MODEL_REVISION, "quant": QUANT, "engine": ENGINE_TAG,
                    "max_new": max_new_for(task), "stop_rule": f"im_end|fence:{fk}", "block_id": block_id,
                    "batch_B": B, "text": text, "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
                    "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"], "realised_disp": disp,
                    "utc": utc_now()})
    if write:
        append_jsonl(RAW, out)
        if realised:
            append_jsonl(REALISED, realised)
    dt = time.time() - t0
    rec_t = {"block_id": block_id, "task": task, "w": w, "arms": [a for a, _ in spec], "B": B, "seconds": round(dt, 2),
             "steps": res[0]["steps"], "max_len": max(r["n_tokens"] for r in res),
             "n_length": sum(r["finish_reason"] == "length" for r in res), "utc": utc_now()}
    if write:
        append_jsonl(TIMING, [rec_t])
    logger.info(f"{block_id} {task}/{w} {[a for a, _ in spec]}: {dt:.1f}s, {res[0]['steps']} steps, "
                f"cap hits {rec_t['n_length']}/{B}")
    return out


# ------------------------------------------------------------------------------------------------ queue
K10 = list(range(10))
TWIN_PAIRS_P1 = [[("TWIN", K10), ("PN_a0.5", K10)], [("PN_a1", K10), ("PN_a2", K10)],
                 [("PN_a4", K10), ("PN_a8", K10)], [("T1.3", K10), ("TOPK10", K10)]]
TWIN_PAIRS_P2 = [[("T1.6", K10), ("MINP_T2.0", K10)], [("MINP_T1.6", K10)]]
P3_TWIN = [[("TWIN", K10), ("PN_a0.5", K10)], [("PN_a1", K10), ("PN_a2", K10)], [("PN_a4", K10), ("T1.6", K10)],
           [("T1.3", K10), ("TOPK10", K10)]]


def task_batches(task: str, prio: str) -> list[list[tuple[str, list[int]]]]:
    """Batch specs of one task and priority (per template)."""
    if prio == "P1":
        out = list(TWIN_PAIRS_P1) + [[("NONCE", K10)], [("NOVELTY", K10)]]
        if task in PATH_TASKS:
            out.append([("SEMSEED", K10)])
        return out
    if prio == "P2":
        return list(TWIN_PAIRS_P2) + [[("PLAIN", K10), ("PNPLAIN_a1", K10)], [("VS", K10)]]
    if prio == "P3":
        return list(P3_TWIN) + [[("NONCE", K10)], [("NOVELTY", K10)], [("PLAIN", K10)]]
    raise ValueError(prio)


def drop_arms(spec: list[tuple[str, list[int]]], dropped: set[str]) -> list[tuple[str, list[int]]] | None:
    """Remove dropped arms from a batch spec; a 20-row pair whose partner is dropped becomes a 10-row batch."""
    keep = [(a, ks) for a, ks in spec if a not in dropped]
    return keep or None


def run_queue(model: Any, tok: Any, prompts: dict, plan: list[dict[str, Any]], deadline: float,
              dropped: set[str] | None = None, max_batches: int | None = None) -> dict[str, Any]:
    """plan: [{'prio', 'task', 'templates': [...]}]. Runs in order; never starts a batch after the deadline."""
    dropped = dropped or set()
    done = done_slots()
    n_b = 0
    not_run: list[dict[str, Any]] = []
    t_start = time.time()
    for item in plan:
        task, prio, temps_ = item["task"], item["prio"], item["templates"]
        ctx = None
        for w in temps_:
            for spec in task_batches(task, prio):
                spec = drop_arms(spec, dropped | set(item.get("drop", ())))
                if spec is None:
                    continue
                if all((task, w, arm, k) in done for arm, ks in spec for k in ks):
                    continue
                if time.time() > deadline or (max_batches is not None and n_b >= max_batches):
                    not_run.append({"prio": prio, "task": task, "w": w, "arms": [a for a, _ in spec],
                                    "reason": "deadline" if time.time() > deadline else "max_batches"})
                    continue
                if ctx is None:
                    ctx = TaskContext(model, tok, prompts, task)
                # skip slots already done inside a partially done batch (resume): rerun the whole batch shape
                run_batch(ctx, w, spec, f"{prio}:{task}:{w}:{'+'.join(a for a, _ in spec)}")
                n_b += 1
                if n_b % 25 == 0:
                    free, total = torch.cuda.mem_get_info(0)
                    logger.info(f"progress: {n_b} batches in {time.time() - t_start:.0f}s; peak VRAM "
                                f"{torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
            if ctx is not None:
                ctx.clean.clear()
                torch.cuda.empty_cache()
    return {"n_batches": n_b, "not_run": not_run, "seconds": time.time() - t_start}
