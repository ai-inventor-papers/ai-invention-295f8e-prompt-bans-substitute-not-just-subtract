#!/usr/bin/env python3
"""GPU runner for Claim E. One model on the GPU at a time.

Usage: python src/gen.py <stage> [--tasks T03,T2] [--limit N]
  it_tests      U1-U4 + U9 memory probe on the it model; saves the U5 reference logits (results/tests_gpu_it.json)
  engine_check  exp23 slot keys / directions / cap: T1 twin + T1 esc9003 alpha 1 + T2 twin (positive control)
  stage1_it     it twin (N=50 per task), novelty instruction (N=30), clean it states at BAND x spec (cache/hit_*.pt)
  stage1_pt     U5 pt loader sanity; pt under the it chat template (N=100, same ids), pt plain completion (N=50),
                pt states at BAND x spec + R (cache/hpt_*.pt)
  ladder        opening-margin rival (teacher forcing, it model; needs commit-#1 draft D_u / r_u)
  stage2        fresh push population (16 dirs x alpha 1, 2 x N=10, defaulted units) + plan noise (all tasks)
  confirm       confirmation top-up (+20) of stage-1-passing direction-alphas
  stage3_valid  U6/U7 transplant tests + validity run of T at N=10 per S_T task (lambda 1)
  stage3        transplant T, matched random RND, cross-task XT, read-position RP on S_T; T on S_C
Rows stream to data/raw_<stage>.jsonl; batch timing to results/timing_batches.jsonl.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHAS, B_CRN, BAND, CACHE_DIR, CAPTURE_BLOCKS, D_MODEL, DATA_DIR, DIR_SEEDS, IT_ID,
                 MAX_NEW_EXP23, MAX_NEW_PLAIN, MODELS, N_NOVELTY, N_PN_PER_T, N_PT_CHAT_PER_T, N_PT_PLAIN,
                 N_STAGE1_PER_T, N_TRANSPLANT_PER_T, N_TWIN_PER_T, PRED_DIR, RESULTS_DIR, SLOT_PREFIX, STAGE2_SLOTS,
                 TEMPLATE_IDS, append_jsonl, cap_of, read_json, read_jsonl, setup_logging, stable_seed, utc_now,
                 write_json)
import engine as EG
import prompts as PG
from push import make_push_edits
from units import ox_norm, unit_n

TIMING = RESULTS_DIR / "timing_batches.jsonl"
RAW = {s: DATA_DIR / f"raw_{s}.jsonl" for s in ("engine_check", "twin", "novelty", "ptchat", "ptplain", "push",
                                                 "confirm", "transplant_valid", "transplant")}
PT_CHAT_CAP = 640   # deviation: exp23 pilot-rule cap (pt rambles under the chat template; see results/deviations.json)
TASK_ORDER_RUN = ("T2", "T03", "T05", "T10", "T1", "T06", "T04", "R1", "T08", "R3", "T13", "R6", "T14", "T11", "R2")


def esc_dir(seed: int) -> np.ndarray:
    return EG.seed_dir(seed)


def pn_dir(task: str, alpha: float, w: str, k: int) -> np.ndarray:
    return EG.unit_dir("iter5E_PN", task, alpha, w, k)


def done_ids(path: Path) -> set[str]:
    return {r["row_id"] for r in read_jsonl(path)}


def hcache_path(kind: str, task: str, w: str) -> Path:
    return CACHE_DIR / f"h{kind}_{task}_{w}.pt"


def load_h(kind: str, task: str, w: str) -> dict[str, Any]:
    d = torch.load(hcache_path(kind, task, w), map_location="cuda")
    return {"S": {l: d["S"][i].float() for i, l in enumerate(BAND)}, "R": {l: d["R"][i].float() for i, l in enumerate(BAND)},
            "a": d["a"], "b": d["b"], "P": d["P"]}


class Runner:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.tok, self.model, self.info = EG.load_model(kind)
        self.ctx: dict[tuple[str, str], dict[str, Any]] = {}

    # -------------------------------------------------------------------------------------------- contexts
    def task_ctx(self, task: str, w: str) -> dict[str, Any]:
        key = (task, w)
        if key not in self.ctx:
            if len(self.ctx) > 4:
                self.ctx.clear()
                torch.cuda.empty_cache()
            tw = PG.p_twin(task, w)
            clean = EG.clean_states(self.model, tw["ids"], tw["spec_start"], tw["spec_end"], CAPTURE_BLOCKS)
            n = unit_n(clean["S"], "ox")
            self.ctx[key] = {"twin": tw, "clean": clean, "n": n}
        return self.ctx[key]

    # -------------------------------------------------------------------------------------------- coupled batches
    def run_crn(self, task: str, w: str, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path,
                batch_id: str, prompt: dict[str, Any] | None = None, transplant: dict[str, Any] | None = None,
                capture: bool = True) -> list[dict[str, Any]]:
        """Single-prompt batch (B = len(rows)). rows: {arm, slot, ukey, alpha, dir_kind, direction_seed, tkind, pad}.
        Push rows (dir_kind 'escape'/'PN', alpha > 0): exp23 displacement-targeted isotropic push at BAND x spec.
        Transplant rows (tkind in T/RND/XT/RP): edits from `transplant` (see stage 3)."""
        B = len(rows)
        t0 = time.time()
        ctx = self.task_ctx(task, w) if self.kind == "it" else None
        p = prompt or PG.p_twin(task, w)
        PG.register(p)
        a, b = p["spec_start"], p["spec_end"]
        U = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
        alpha = torch.zeros(B, dtype=torch.float32, device="cuda")
        for i, r in enumerate(rows):
            d = None
            if r.get("dir_kind") == "escape":
                d = esc_dir(int(r["direction_seed"]))
            elif r.get("dir_kind") == "PN":
                d = pn_dir(task, float(r["alpha"]), w, int(r["slot"]))
            if d is not None and (r.get("alpha") or 0) > 0:
                U[i] = torch.tensor(d, device="cuda")
                alpha[i] = float(r["alpha"])
        edits: dict[int, Any] = {}
        push_dir = None
        if bool((alpha > 0).any()):
            assert ctx is not None
            edits = make_push_edits(BAND, a, b, U, alpha, ctx["n"], {l: ctx["clean"]["S"][l] for l in BAND})
            push_dir = {"U": U, "tgt": {l: alpha[:, None] * ctx["n"][l][None, :] for l in BAND}}
        if transplant is not None:
            t_edits = transplant["builder"](rows)
            for l, f in t_edits.items():
                if l in edits:
                    g = edits[l]
                    edits[l] = (lambda h, f=f, g=g: f(g(h)))
                else:
                    edits[l] = f
        cref = ctx["clean"] if (ctx is not None and capture) else None
        pre = EG.prefill_single(self.model, p["ids"], B, edits=edits, capture_ref=cref, push_dir=push_dir)
        dS = pre.pop("disp_S", None)
        dR = pre.pop("disp_R", None)
        rel = pre.pop("relerr_along", None)
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        temps = np.array([float(r.get("temperature", 1.0)) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, temps, max_new)
        del pre
        out = []
        for i, (r, g) in enumerate(zip(rows, res)):
            rd = None
            if dS is not None:
                rd = {"S_mean_band": float(dS[i, :len(BAND)].mean()), "R_last": float(dR[i, -1]),
                      "S_by_block": [round(float(x), 3) for x in dS[i]], "R_by_block": [round(float(x), 3) for x in dR[i]]}
                if rel is not None and float(alpha[i]) > 0:
                    rd["rel_err_along_u_max"] = float(rel[i].max())
            out.append({"row_id": f"{stage}|{task}|{w}|{r['arm']}|{r['slot']}", "task": task, "arm": r["arm"],
                        "stage": stage, "model": MODELS[self.kind][0], "model_kind": self.kind,
                        "site": r.get("site"), "lambda": r.get("lam"), "alpha": r.get("alpha"),
                        "direction_seed": r.get("direction_seed"), "dir_kind": r.get("dir_kind"),
                        "tkind": r.get("tkind"), "template": w, "slot": int(r["slot"]), "ukey": list(r["ukey"]),
                        "temperature": float(r.get("temperature", 1.0)), "top_k": None, "thinking": False,
                        "precision": "bf16", "prompt_sha256": p["prompt_sha256"], "prompt_kind": p["kind"],
                        "text": g["text"], "token_ids": g["token_ids"], "finish_reason": g["finish_reason"],
                        "n_new_tokens": g["n_tokens"], "realised_disp": rd, "pad": bool(r.get("pad", False)),
                        "batch_id": batch_id, "B": B, "max_new": max_new, "utc": utc_now()})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": task, "w": w, "B": B, "seconds": dt,
                               "steps": res[0]["steps"], "max_new": max_new, "model": self.kind, "utc": utc_now()}])
        fr = dict(zip(*np.unique([g["finish_reason"] for g in res], return_counts=True)))
        logger.info(f"{batch_id}: B={B} {dt:.1f}s, {res[0]['steps']} steps, finish {fr}")
        return out

    # -------------------------------------------------------------------------------------------- multi-prompt / plain
    def run_single_free(self, rows: list[dict[str, Any]], prompt: dict[str, Any], max_new: int, stage: str,
                        raw_path: Path, batch_id: str, fence_stop: bool = True, plain_stop: bool = False):
        """Uncoupled single-prompt batch (novelty, pt plain): no edits, no displacement capture."""
        t0 = time.time()
        PG.register(prompt)
        B = len(rows)
        pre = EG.prefill_single(self.model, prompt["ids"], B)
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, np.ones(B), max_new, fence_stop=fence_stop,
                        plain_stop=plain_stop)
        del pre
        out = []
        for r, g in zip(rows, res):
            out.append({"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "stage": stage,
                        "model": MODELS[self.kind][0], "model_kind": self.kind, "site": None, "lambda": None,
                        "alpha": None, "direction_seed": None, "dir_kind": None, "tkind": None,
                        "template": r.get("template"), "slot": r["slot"], "ukey": list(r["ukey"]), "temperature": 1.0,
                        "top_k": None, "thinking": False, "precision": "bf16", "prompt_sha256": prompt["prompt_sha256"],
                        "prompt_kind": prompt["kind"], "text": g["text"], "token_ids": g["token_ids"],
                        "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"], "realised_disp": None,
                        "pad": False, "batch_id": batch_id, "B": B, "max_new": max_new, "utc": utc_now(),
                        "program_prefix": prompt.get("prefix")})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": rows[0]["task"], "w": None, "B": B,
                               "seconds": dt, "steps": res[0]["steps"], "max_new": max_new, "model": self.kind,
                               "utc": utc_now()}])
        fr = dict(zip(*np.unique([g["finish_reason"] for g in res], return_counts=True)))
        logger.info(f"{batch_id}: B={B} {dt:.1f}s, {res[0]['steps']} steps, finish {fr}")
        return out

    def run_multi(self, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path, batch_id: str,
                  fence_stop: bool = True) -> list[dict[str, Any]]:
        """Multi-prompt batch (several templates of one task): each distinct prompt is prefilled at batch 1, its KV
        right-aligned with masked left pads; rows carry their own CRN uniforms (ukey). No edits (twin, pt-chat)."""
        t0 = time.time()
        for r in rows:
            PG.register(r["prompt"])
        pre = EG.prefill_multi(self.model, [r["prompt"]["ids"] for r in rows])
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, np.ones(len(rows)), max_new, fence_stop=fence_stop)
        del pre
        out = []
        for r, g in zip(rows, res):
            p = r["prompt"]
            out.append({"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "stage": stage,
                        "model": MODELS[self.kind][0], "model_kind": self.kind, "site": None, "lambda": None,
                        "alpha": 0.0, "direction_seed": None, "dir_kind": None, "tkind": None,
                        "template": r["template"], "slot": int(r["slot"]), "ukey": list(r["ukey"]),
                        "temperature": 1.0, "top_k": None, "thinking": False, "precision": "bf16",
                        "prompt_sha256": p["prompt_sha256"], "prompt_kind": p["kind"], "text": g["text"],
                        "token_ids": g["token_ids"], "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"],
                        "realised_disp": None, "pad": False, "batch_id": batch_id, "B": len(rows),
                        "max_new": max_new, "batch_kind": "multi_prompt", "utc": utc_now()})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": rows[0]["task"], "w": None,
                               "B": len(rows), "seconds": dt, "steps": res[0]["steps"], "max_new": max_new,
                               "model": self.kind, "utc": utc_now()}])
        fr = dict(zip(*np.unique([g["finish_reason"] for g in res], return_counts=True)))
        logger.info(f"{batch_id}: B={len(rows)} {dt:.1f}s, {res[0]['steps']} steps, finish {fr}")
        return out

    def tf(self, ids: list[int], targets: list[int]) -> list[float]:
        return EG.tf_logprobs(self.model, ids, targets)


# ================================================================================================ GPU tests (it)
def it_tests(R: Runner) -> dict[str, Any]:
    """U1 alpha-0 rows bit-identical to unhooked rows; U2 pre-band states identical; U3 realised displacement along u
    = alpha n within 0.1%; U4 a slot's tokens do not depend on its batch-mates (fixed shape); U9 memory probe."""
    res: dict[str, Any] = {}
    B = 8
    for task in ("T03", "T2"):
        ctx = R.task_ctx(task, "W1")
        tw, clean, n = ctx["twin"], ctx["clean"], ctx["n"]
        ids, a, b = tw["ids"], tw["spec_start"], tw["spec_end"]
        U = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
        alpha = torch.zeros(B, dtype=torch.float32, device="cuda")
        for i in range(B // 2, B):
            U[i] = torch.tensor(esc_dir(DIR_SEEDS[i]), device="cuda")
            alpha[i] = 1.0 if i % 2 == 0 else 2.0
        edits = make_push_edits(BAND, a, b, U, alpha, n, {l: clean["S"][l] for l in BAND})
        pdir = {"U": U, "tgt": {l: alpha[:, None] * n[l][None, :] for l in BAND}}
        pre_push = EG.prefill_single(R.model, ids, B, edits=edits, capture_ref=clean, push_dir=pdir)
        pre_none = EG.prefill_single(R.model, ids, B)
        z = list(range(B // 2))
        u1 = bool(torch.equal(pre_push["logits"][z], pre_none["logits"][z]))
        got: dict[str, dict[int, torch.Tensor]] = {"p": {}, "n": {}}

        def mk(store, l):
            def g(h):
                store[l] = h.float().clone()
            return g
        inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
        from push import block_hooks
        with torch.no_grad():
            with block_hooks(EG.layers(R.model), edits, {l: mk(got["p"], l) for l in (BAND[0] - 1, BAND[0])}):
                R.model.model(input_ids=inp, use_cache=False)
            with block_hooks(EG.layers(R.model), {}, {l: mk(got["n"], l) for l in (BAND[0] - 1, BAND[0])}):
                R.model.model(input_ids=inp, use_cache=False)
        u2a = bool(torch.equal(got["p"][BAND[0] - 1], got["n"][BAND[0] - 1]))
        outside = list(range(0, a)) + list(range(b, len(ids)))
        u2b = bool(torch.equal(got["p"][BAND[0]][:, outside], got["n"][BAND[0]][:, outside]))
        rel = pre_push["relerr_along"][B // 2:]
        u3 = float(rel.max())
        S6 = clean["S"][BAND[6]]
        res[task] = {"U1_alpha0_bit_identical_logits": u1, "U2_pre_band_identical": u2a,
                     "U2_outside_spec_identical_at_first_band_block": u2b, "U3_max_rel_err_along_u": u3,
                     "U3_pass": u3 < 1e-3, "unit_n_mean_first_band": float(n[BAND[0]].mean()),
                     "unit_n_mean_last_band": float(n[BAND[-1]].mean()),
                     "residual_norm_mean_first_band": float(clean["S"][BAND[0]].norm(dim=-1).mean()),
                     "massive_top5_share": float(((S6 ** 2).topk(5, dim=-1).values.sum(-1) / (S6 ** 2).sum(-1)).mean())}
        del pre_push, pre_none, got
        torch.cuda.empty_cache()
        Uu = np.stack([EG.u_stream(SLOT_PREFIX, task, "W1", k, n=96) for k in range(B)])
        preA = EG.prefill_single(R.model, ids, B)
        outA = EG.decode(R.model, R.tok, preA, Uu, np.ones(B), 96, fence_stop=False)
        U2 = Uu.copy()
        U2[1:] = np.stack([EG.u_stream("u4_other", task, k, n=96) for k in range(1, B)])
        U3d = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
        al3 = torch.zeros(B, dtype=torch.float32, device="cuda")
        for i in range(1, B):
            U3d[i] = torch.tensor(esc_dir(DIR_SEEDS[i]), device="cuda")
            al3[i] = 1.0
        e3 = make_push_edits(BAND, a, b, U3d, al3, n, {l: clean["S"][l] for l in BAND})
        preB = EG.prefill_single(R.model, ids, B, edits=e3)
        outB = EG.decode(R.model, R.tok, preB, U2, np.ones(B), 96, fence_stop=False)
        res[task]["U4_crn_slot0_identical"] = outA[0]["token_ids"] == outB[0]["token_ids"]
        res[task]["U4_example_text"] = outA[0]["text"][:200]
        logger.info(f"{task}: {res[task]}")
        torch.cuda.empty_cache()
    # U5 reference: it logits on a fixed prompt (compared with pt in the pt session)
    tw = PG.p_twin("T03", "W1")
    with torch.no_grad():
        out = R.model.model(input_ids=torch.tensor([tw["ids"]], device="cuda"), use_cache=False)
        lg = EG.lm_logits(R.model, out.last_hidden_state[0, -1])
    torch.save({"logits": lg.cpu(), "ids": tw["ids"]}, CACHE_DIR / "u5_it_logits.pt")
    res["U5_it_greedy_stub"] = greedy_stub(R)
    # U9: KV prealloc at B_CRN with the longest prompt + the longest cap (T1/T2: 1,536)
    longest = max(((t, w) for t in ALL_TASKS for w in TEMPLATE_IDS), key=lambda x: PG.p_twin(*x)["P"])
    tw = PG.p_twin(*longest)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    pre = EG.prefill_single(R.model, tw["ids"], B_CRN)
    Uu = np.stack([EG.u_stream("u9", k, n=1536) for k in range(B_CRN)])
    cache = EG.build_prealloc(pre["kv"], pre["P"] + 1536 + 1)
    peak = torch.cuda.max_memory_allocated() / 1e9
    del cache, pre
    torch.cuda.empty_cache()
    pre = EG.prefill_single(R.model, tw["ids"], B_CRN)
    o = EG.decode(R.model, R.tok, pre, Uu, np.ones(B_CRN), 64, fence_stop=False)
    ms = 1000 * (time.time() - t0) / 64
    free, total = torch.cuda.mem_get_info(0)
    res["U9_memory"] = {"task_w": list(longest), "P": tw["P"], "B": B_CRN, "max_new": 1536,
                        "peak_alloc_gb_full_buffer": peak, "vram_total_gb": total / 1e9,
                        "headroom_gb": total / 1e9 - peak, "pass": total / 1e9 - peak >= 1.5,
                        "ms_per_step_first64_incl_prefill": ms, "example": o[0]["text"][:80]}
    logger.info(f"U9: {res['U9_memory']}")
    res["all_pass"] = all(v["U1_alpha0_bit_identical_logits"] and v["U2_pre_band_identical"]
                          and v["U2_outside_spec_identical_at_first_band_block"] and v["U3_pass"]
                          and v["U4_crn_slot0_identical"] for k, v in res.items() if k in ("T03", "T2")) \
        and res["U9_memory"]["pass"]
    res["model_info"] = R.info
    write_json(RESULTS_DIR / "tests_gpu_it.json", res)
    return res


def greedy_stub(R: Runner) -> dict[str, Any]:
    """T=0 continuation of a 'def solve' stub (plain prompt of T03): syntactically valid Python expected."""
    import ast as _ast

    p = PG.p_plain("T03")
    pre = EG.prefill_single(R.model, p["ids"], 1)
    U = np.zeros((1, 160))
    o = EG.decode(R.model, R.tok, pre, U + 1e-12, np.array([1e-4]), 160, fence_stop=False, plain_stop=True)
    prog = p["prefix"] + cut_plain(o[0]["text"])
    try:
        _ast.parse(prog)
        ok = True
    except SyntaxError:
        ok = False
    return {"valid_python": ok, "program_head": prog[:300]}


def cut_plain(text: str) -> str:
    """Truncate a plain-completion continuation at the end of the function (same rule as engine.plain_ended)."""
    lines = text.split("\n")
    out = []
    body_seen = False
    for ln in lines:
        if ln.strip() and ln[0] not in (" ", "\t"):
            if ln.startswith("if __name__") or (body_seen and not ln.startswith(EG.PLAIN_KEEP)):
                break
        elif ln.strip():
            body_seen = True
        out.append(ln)
    return "\n".join(out).rstrip() + "\n"


# ================================================================================================ engine check
def engine_check(R: Runner) -> None:
    """exp23's slot keys (task, w, k), exp23's direction 9003 (seed_dir), exp23's 640 cap. T1: twin slots 0-9 +
    esc9003_a1 slots 0-5 per template (one batch of 16 per template); T2: twin slots 0-9 per template."""
    raw = RAW["engine_check"]
    done = done_ids(raw)
    for task, arms in (("T1", ("twin", "esc9003_a1")), ("T2", ("twin",))):
        for w in TEMPLATE_IDS:
            rows = [{"arm": "e23_twin", "slot": k, "ukey": (task, w, k), "alpha": 0.0} for k in range(10)]
            if "esc9003_a1" in arms:
                rows += [{"arm": "e23_esc9003_a1", "slot": k, "ukey": (task, w, k), "alpha": 1.0,
                          "dir_kind": "escape", "direction_seed": 9003} for k in range(6)]
            ids = {f"engine_check|{task}|{w}|{r['arm']}|{r['slot']}" for r in rows}
            if ids <= done:
                continue
            R.run_crn(task, w, rows, MAX_NEW_EXP23, "engine_check", raw, f"EC:{task}:{w}")


# ================================================================================================ stage 1
def stage1_it(R: Runner, tasks: list[str]) -> None:
    raw = RAW["twin"]
    done = done_ids(raw)
    t_start = time.time()
    for ti, t in enumerate(tasks):
        rows = [{"row_id": f"twin|{t}|{w}|twin|{k}", "task": t, "arm": "twin", "slot": k, "template": w,
                 "ukey": (SLOT_PREFIX, t, w, k), "prompt": PG.p_twin(t, w)}
                for w in TEMPLATE_IDS for k in range(N_TWIN_PER_T)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            R.run_multi(rows, cap_of(t), "twin", raw, f"TW:{t}")
        el = time.time() - t_start
        logger.info(f"twin {t} done ({ti + 1}/{len(tasks)}); {el / 60:.1f} min; eta {el / (ti + 1) * (len(tasks) - ti - 1) / 60:.1f} min")
    # capture clean it states (BAND x spec + R) for the transplant and the massive-channel set
    for t in tasks:
        for w in TEMPLATE_IDS:
            pth = hcache_path("it", t, w)
            if pth.exists():
                continue
            tw = PG.p_twin(t, w)
            st = EG.clean_states(R.model, tw["ids"], tw["spec_start"], tw["spec_end"], BAND)
            torch.save({"S": torch.stack([st["S"][l] for l in BAND]).to(torch.bfloat16).cpu(),
                        "R": torch.stack([st["R"][l] for l in BAND]).to(torch.bfloat16).cpu(),
                        "a": tw["spec_start"], "b": tw["spec_end"], "P": tw["P"], "prompt_sha256": tw["prompt_sha256"]},
                       pth)
    logger.info("it clean states cached")
    # novelty instruction (rival): one frame, 30 slots, same chat template
    rawn = RAW["novelty"]
    done = done_ids(rawn)
    for t in tasks:
        p = PG.p_novelty(t)
        rows = [{"row_id": f"novelty|{t}|novelty|{k}", "task": t, "arm": "novelty", "slot": k,
                 "ukey": (SLOT_PREFIX, t, "NOV", k), "template": None} for k in range(N_NOVELTY)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            R.run_single_free(rows, p, cap_of(t), "novelty", rawn, f"NOV:{t}")


def u5_pt(R: Runner) -> dict[str, Any]:
    ref = torch.load(CACHE_DIR / "u5_it_logits.pt")
    with torch.no_grad():
        out = R.model.model(input_ids=torch.tensor([ref["ids"]], device="cuda"), use_cache=False)
        lg = EG.lm_logits(R.model, out.last_hidden_state[0, -1]).cpu()
    it_lg = ref["logits"]
    pi, pp = torch.softmax(it_lg, -1), torch.softmax(lg, -1)
    m = 0.5 * (pi + pp)
    js = float(0.5 * ((pi * (pi.clamp_min(1e-30) / m.clamp_min(1e-30)).log()).sum()
                      + (pp * (pp.clamp_min(1e-30) / m.clamp_min(1e-30)).log()).sum()))
    res = {"U5_logits_differ": not torch.equal(lg, it_lg), "js_next_token_it_vs_pt": js,
           "top5_it": it_lg.topk(5).indices.tolist(), "top5_pt": lg.topk(5).indices.tolist(),
           "pt_greedy_stub": greedy_stub(R)}
    res["pass"] = res["U5_logits_differ"] and res["pt_greedy_stub"]["valid_python"]
    return res


def stage1_pt(R: Runner, tasks: list[str], plain: bool = True) -> None:
    it_info = read_json(RESULTS_DIR / "tests_gpu_it.json")["model_info"]
    u5 = u5_pt(R)
    u5["key_map_identical"] = R.info["key_map_sha256"] == it_info["key_map_sha256"]
    u5["tokenizer_vocab_identical"] = R.info["vocab_sha256"] == it_info["vocab_sha256"]
    u5["pass"] = u5["pass"] and u5["key_map_identical"] and u5["tokenizer_vocab_identical"]
    write_json(RESULTS_DIR / "tests_gpu_pt.json", {**u5, "model_info": R.info})
    logger.info(f"U5: {u5}")
    assert u5["key_map_identical"] and u5["tokenizer_vocab_identical"], "pt/it key map or vocab differ"
    raw = RAW["ptchat"]
    done = done_ids(raw)
    t_start = time.time()
    for ti, t in enumerate(tasks):
        for half in (0, 1):
            ks = range(half * N_PT_CHAT_PER_T // 2, (half + 1) * N_PT_CHAT_PER_T // 2)
            rows = [{"row_id": f"ptchat|{t}|{w}|pt_chat|{k}", "task": t, "arm": "pt_chat", "slot": k, "template": w,
                     "ukey": (SLOT_PREFIX, t, w, k), "prompt": PG.p_twin(t, w)} for w in TEMPLATE_IDS for k in ks]
            rows = [r for r in rows if r["row_id"] not in done]
            if rows:
                R.run_multi(rows, min(cap_of(t), PT_CHAT_CAP), "ptchat", raw, f"PTC:{t}:h{half}")
        el = time.time() - t_start
        logger.info(f"pt_chat {t} done ({ti + 1}/{len(tasks)}); {el / 60:.1f} min; eta {el / (ti + 1) * (len(tasks) - ti - 1) / 60:.1f} min")
    for t in tasks:
        for w in TEMPLATE_IDS:
            pth = hcache_path("pt", t, w)
            if pth.exists():
                continue
            tw = PG.p_twin(t, w)
            st = EG.clean_states(R.model, tw["ids"], tw["spec_start"], tw["spec_end"], BAND)
            torch.save({"S": torch.stack([st["S"][l] for l in BAND]).to(torch.bfloat16).cpu(),
                        "R": torch.stack([st["R"][l] for l in BAND]).to(torch.bfloat16).cpu(),
                        "a": tw["spec_start"], "b": tw["spec_end"], "P": tw["P"], "prompt_sha256": tw["prompt_sha256"]},
                       pth)
    logger.info("pt states cached")
    if not plain:
        return
    rawp = RAW["ptplain"]
    done = done_ids(rawp)
    for t in tasks:
        p = PG.p_plain(t)
        rows = [{"row_id": f"ptplain|{t}|pt_plain|{k}", "task": t, "arm": "pt_plain", "slot": k,
                 "ukey": (SLOT_PREFIX, "plain", t, k), "template": None} for k in range(N_PT_PLAIN)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            R.run_single_free(rows, p, MAX_NEW_PLAIN, "ptplain", rawp, f"PTP:{t}", fence_stop=False, plain_stop=True)


# ================================================================================================ stage 2
def commit_e1() -> dict[str, Any]:
    return read_json(PRED_DIR / "commit_E1.json")


def stage2(R: Runner, tasks: list[str], dir_seeds: tuple[int, ...] = DIR_SEEDS, pn_alphas=ALPHAS) -> None:
    c1 = commit_e1()
    raw = RAW["push"]
    done = done_ids(raw)
    t_start = time.time()
    for ti, t in enumerate(tasks):
        defaulted = c1["units"][t]["defaulted"]
        for w in TEMPLATE_IDS:
            rows = []
            if defaulted:
                for s in dir_seeds:
                    for a in ALPHAS:
                        for k in range(N_STAGE1_PER_T):
                            rows.append({"arm": f"esc{s}_a{int(a)}", "slot": k, "ukey": (SLOT_PREFIX, t, w, k),
                                         "alpha": a, "dir_kind": "escape", "direction_seed": s, "site": "spec_band"})
            for a in pn_alphas:
                for k in range(N_PN_PER_T):
                    rows.append({"arm": f"pn_a{int(a)}", "slot": k, "ukey": (SLOT_PREFIX, t, w, k), "alpha": a,
                                 "dir_kind": "PN", "direction_seed": "PN", "site": "spec_band"})
            rows = [r for r in rows if f"push|{t}|{w}|{r['arm']}|{r['slot']}" not in done]
            for bi in range(0, len(rows), B_CRN):
                R.run_crn(t, w, rows[bi:bi + B_CRN], cap_of(t), "push", raw, f"PU:{t}:{w}:b{bi // B_CRN}")
        el = time.time() - t_start
        logger.info(f"stage2 {t} done ({ti + 1}/{len(tasks)}); {el / 60:.1f} min; "
                    f"eta {el / (ti + 1) * (len(tasks) - ti - 1) / 60:.1f} min")


def confirm(R: Runner, tasks: list[str]) -> None:
    import predictors as PR

    raw = RAW["confirm"]
    done = done_ids(raw)
    for t in tasks:
        st1 = PR.stage1(t)
        passing = st1.get("passing", [])
        if not passing:
            logger.info(f"confirm {t}: no direction-alpha passes stage 1")
            continue
        for w in TEMPLATE_IDS:
            rows = [{"arm": f"esc{s}_a{int(a)}", "slot": k, "ukey": (SLOT_PREFIX, t, w, k), "alpha": a,
                     "dir_kind": "escape", "direction_seed": s, "site": "spec_band"}
                    for (s, a) in passing for k in STAGE2_SLOTS]
            rows = [r for r in rows if f"confirm|{t}|{w}|{r['arm']}|{r['slot']}" not in done]
            for bi in range(0, len(rows), B_CRN):
                R.run_crn(t, w, rows[bi:bi + B_CRN], cap_of(t), "confirm", raw, f"CF:{t}:{w}:b{bi // B_CRN}")
        logger.info(f"confirm {t}: {len(passing)} passing direction-alphas topped up")


def wait_rows(row_ids: set[str], timeout_s: float = 1800.0, poll: float = 5.0) -> bool:
    t0 = time.time()
    while True:
        have = {r["row_id"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
        if row_ids <= have:
            return True
        if time.time() - t0 > timeout_s:
            logger.warning(f"label wait timed out: {len(row_ids - have)} of {len(row_ids)} unlabelled")
            return False
        time.sleep(poll)


def stage2_pipelined(R: Runner, tasks: list[str], dir_seeds: tuple[int, ...] = DIR_SEEDS) -> None:
    """Stage-1 push + PN rows task by task; the confirmation top-up of task i-1 runs after task i's stage-1 rows
    (by then the labeller has labelled task i-1), which hides the labelling latency."""
    prev = None
    for t in tasks + [None]:
        if t is not None:
            stage2(R, [t], dir_seeds)
        if prev is not None:
            ids = {r["row_id"] for r in read_jsonl(RAW["push"]) if r["task"] == prev}
            wait_rows(ids)
            confirm(R, [prev])
        prev = t


# ================================================================================================ stage 3
class Transplant:
    """pt -> it transplant arms on (task, w). d = h_pt - h_it_clean at BAND x spec (cached states, bf16 -> fp32).
    T  : live interpolation h <- h + lam (h_pt - h) at spec positions of every band block (lam = 1: replacement)
    RP : the same at position R only (site control)
    RND: displacement-targeted v = lam (d_M + ||d_ox|| g), g a per-sample isotropic unit vector in the non-M subspace
    XT : displacement-targeted v = lam (d_M + ||d_ox|| m_hat_donor[l]), m_donor[l] = mean donor d_ox over spec
         positions and templates (donor = next task in the frozen cyclic order)"""

    def __init__(self, task: str, w: str, lam: float, M: list[int], donor_m: dict[int, torch.Tensor] | None):
        self.task, self.w, self.lam = task, w, lam
        hi, hp = load_h("it", task, w), load_h("pt", task, w)
        assert hi["P"] == hp["P"] and hi["a"] == hp["a"] and hi["b"] == hp["b"]
        self.a, self.b, self.P = hi["a"], hi["b"], hi["P"]
        self.hi, self.hp = hi, hp
        self.Mmask = torch.zeros(D_MODEL, dtype=torch.bool, device="cuda")
        self.Mmask[torch.tensor(M, device="cuda")] = True
        self.d = {l: hp["S"][l] - hi["S"][l] for l in BAND}
        self.dM = {l: self.d[l] * self.Mmask for l in BAND}
        self.dox_norm = {l: (self.d[l] * (~self.Mmask)).norm(dim=-1) for l in BAND}
        self.donor_m = donor_m

    def rnd_dir(self, k: int) -> torch.Tensor:
        g = np.random.Generator(np.random.PCG64(stable_seed("iter5E_RND", self.task, self.w, k))).standard_normal(D_MODEL)
        g = torch.tensor(g, dtype=torch.float32, device="cuda") * (~self.Mmask)
        return g / g.norm()

    def builder(self, rows: list[dict[str, Any]]) -> dict[int, Any]:
        specs = []
        dev = "cuda"
        spos = torch.arange(self.a, self.b, device=dev)
        rpos = torch.tensor([self.P - 1], device=dev)
        by = {k: [i for i, r in enumerate(rows) if r.get("tkind") == k] for k in ("T", "RND", "XT", "RP")}
        if by["T"]:
            specs.append({"rows": torch.tensor(by["T"], device=dev), "pos": spos, "kind": "replace", "lam": self.lam,
                          "target": {l: self.hp["S"][l] for l in BAND}})
        if by["RP"]:
            specs.append({"rows": torch.tensor(by["RP"], device=dev), "pos": rpos, "kind": "replace", "lam": self.lam,
                          "target": {l: self.hp["R"][l][None] for l in BAND}})
        gnorm = {l: self.lam * self.dox_norm[l] for l in BAND}
        if by["RND"]:
            G = torch.stack([self.rnd_dir(int(rows[i]["slot"])) for i in by["RND"]])          # [r, D], zero on M
            specs.append({"rows": torch.tensor(by["RND"], device=dev), "pos": spos, "kind": "split",
                          "Mmask": self.Mmask, "lam": self.lam, "target": {l: self.hp["S"][l] for l in BAND},
                          "ref": {l: self.hi["S"][l] for l in BAND}, "g": {l: G for l in BAND}, "gnorm": gnorm})
        if by["XT"]:
            assert self.donor_m is not None
            specs.append({"rows": torch.tensor(by["XT"], device=dev), "pos": spos, "kind": "split",
                          "Mmask": self.Mmask, "lam": self.lam, "target": {l: self.hp["S"][l] for l in BAND},
                          "ref": {l: self.hi["S"][l] for l in BAND}, "g": {l: self.donor_m[l] for l in BAND},
                          "gnorm": gnorm})
        return EG.make_row_edits(BAND, specs)


def donor_mean(donor: str, M: list[int]) -> dict[int, torch.Tensor]:
    """m_donor[l] = mean over the donor task's spec positions and 5 templates of d_ox (unit-normalised)."""
    Mmask = torch.zeros(D_MODEL, dtype=torch.bool, device="cuda")
    Mmask[torch.tensor(M, device="cuda")] = True
    acc = {l: torch.zeros(D_MODEL, device="cuda") for l in BAND}
    n = 0
    for w in TEMPLATE_IDS:
        hi, hp = load_h("it", donor, w), load_h("pt", donor, w)
        for l in BAND:
            acc[l] += ((hp["S"][l] - hi["S"][l]) * (~Mmask)).sum(0)
        n += hi["b"] - hi["a"]
    out = {l: (acc[l] / n) / (acc[l] / n).norm() for l in BAND}
    assert all(float(out[l][Mmask].abs().max()) == 0.0 for l in BAND)
    return out


def transplant_tests(R: Runner, task: str, M: list[int], donor: str) -> dict[str, Any]:
    """U6: hooked state at block 11 spec positions equals cached h_pt (max rel err < 1e-2), non-spec untouched;
    U7: RND/XT realised displacement at block 11 = ||v|| within 1% and carries exactly d_M on M."""
    from push import block_hooks

    w = "W1"
    X = Transplant(task, w, 1.0, M, donor_mean(donor, M))
    tw = PG.p_twin(task, w)
    rows = [{"tkind": "T", "slot": 0}, {"tkind": "RND", "slot": 0}, {"tkind": "XT", "slot": 0}, {"tkind": None, "slot": 0}]
    edits = X.builder(rows)
    got: dict[int, torch.Tensor] = {}

    def g(h):
        got[BAND[0]] = h.float().clone()
    inp = torch.tensor([tw["ids"]], device="cuda").expand(len(rows), -1).contiguous()
    with torch.no_grad(), block_hooks(EG.layers(R.model), edits, {BAND[0]: g}):
        R.model.model(input_ids=inp, use_cache=False)
    h = got[BAND[0]]
    a, b = X.a, X.b
    l0 = BAND[0]
    hp, hi = X.hp["S"][l0], X.hi["S"][l0]
    rel_T = float(((h[0, a:b] - hp).norm(dim=-1) / hp.norm(dim=-1)).max())
    outside = list(range(0, a)) + list(range(b, len(tw["ids"])))
    untouched = bool(torch.equal(h[0, outside], h[3, outside]))
    res = {"task": task, "U6_max_rel_err_T_vs_hpt_block11": rel_T, "U6_pass": rel_T < 1e-2 and untouched,
           "U6_non_spec_untouched": untouched}
    Mi = torch.nonzero(X.Mmask).flatten()
    Oi = torch.nonzero(~X.Mmask).flatten()
    for i, nm in ((1, "RND"), (2, "XT")):
        disp = h[i, a:b] - hi
        g = X.rnd_dir(0) if nm == "RND" else X.donor_m[l0]
        along = (disp * g[None]).sum(-1)                                  # displacement along g, per position
        tgt = X.dox_norm[l0]
        rel_along = float(((along - tgt).abs() / tgt.clamp(min=1e-6)).max())
        vo = tgt[:, None] * g[None]
        cos = float(torch.nn.functional.cosine_similarity(disp[:, Oi], vo[:, Oi], dim=-1).min())
        relv = float(((disp[:, Oi].norm(dim=-1) - tgt).abs() / tgt.clamp(min=1e-6)).max())
        # massive channels: same as the transplant row (index 0) up to the bf16 spacing of |h|
        ulp = (h[0, a:b][:, Mi].abs()).clamp(min=1.0) * 2.0 ** -7
        same_as_T = bool(((h[i, a:b][:, Mi] - h[0, a:b][:, Mi]).abs() <= ulp).all())
        res[f"U7_{nm}_max_rel_err_along_g"] = rel_along
        res[f"U7_{nm}_max_rel_err_nonmassive_norm"] = relv
        res[f"U7_{nm}_min_cos_nonmassive"] = cos
        res[f"U7_{nm}_massive_equals_transplant"] = same_as_T
        res[f"U7_{nm}_pass"] = rel_along < 0.01 and same_as_T
    res["U8_donor_differs"] = donor != task
    return res


def stage3(R: Runner, which: str) -> None:
    c1 = commit_e1()
    tr = c1["transplant"]
    M = tr["M"]
    amend = PRED_DIR / "commit_E1b_M.json"
    if amend.exists():   # commit #1b: validity-only amendment of the massive set (before any transplant sample)
        M = read_json(amend)["M_star"]
    logger.info(f"massive set M used by the transplant arms: {len(M)} channels {M[:10]}")
    donors = tr["donor"]
    S_T, S_C = tr["S_T"], tr["S_C"]
    lam_path = RESULTS_DIR / "transplant_lambda.json"
    if which == "valid":
        tests = [transplant_tests(R, u, M, donors[u]) for u in S_T[:2]]
        write_json(RESULTS_DIR / "tests_gpu_transplant.json", {"tests": tests,
                                                               "all_pass": all(t["U6_pass"] and t["U7_RND_pass"]
                                                                               and t["U7_XT_pass"] for t in tests)})
        logger.info(f"U6/U7: {tests}")
        raw = RAW["transplant_valid"]
        done = done_ids(raw)
        for u in S_T:
            for w in TEMPLATE_IDS:
                rows = [{"arm": "T", "tkind": "T", "slot": k, "ukey": (SLOT_PREFIX, u, w, k), "lam": 1.0,
                         "site": "spec_band"} for k in range(2)]
                if {f"transplant_valid|{u}|{w}|T|{k}" for k in range(2)} <= done:
                    continue
                X = Transplant(u, w, 1.0, M, None)
                R.run_crn(u, w, rows, cap_of(u), "transplant_valid", raw, f"TV:{u}:{w}", transplant={"builder": X.builder})
        return
    lam = float(read_json(lam_path)["lambda"])
    raw = RAW["transplant"]
    done = done_ids(raw)
    for u in S_T:
        dm = donor_mean(donors[u], M)
        for w in TEMPLATE_IDS:
            rows = []
            for kind, site in (("T", "spec_band"), ("RND", "spec_band"), ("XT", "spec_band"), ("RP", "read_position")):
                rows += [{"arm": kind, "tkind": kind, "slot": k, "ukey": (SLOT_PREFIX, u, w, k), "lam": lam,
                          "site": site} for k in range(N_TRANSPLANT_PER_T)]
            rows += [{"arm": "twin_pad", "tkind": None, "slot": k, "ukey": (SLOT_PREFIX, u, w, k), "lam": None,
                      "pad": True} for k in range(B_CRN - len(rows))]
            if {f"transplant|{u}|{w}|{r['arm']}|{r['slot']}" for r in rows} <= done:
                continue
            X = Transplant(u, w, lam, M, dm)
            R.run_crn(u, w, rows, cap_of(u), "transplant", raw, f"TP:{u}:{w}", transplant={"builder": X.builder})
            del X
            torch.cuda.empty_cache()
    for u in S_C:
        for w in TEMPLATE_IDS:
            rows = [{"arm": "T", "tkind": "T", "slot": k, "ukey": (SLOT_PREFIX, u, w, k), "lam": lam,
                     "site": "spec_band"} for k in range(N_TRANSPLANT_PER_T)]
            if {f"transplant|{u}|{w}|T|{k}" for k in range(N_TRANSPLANT_PER_T)} <= done:
                continue
            X = Transplant(u, w, lam, M, None)
            R.run_crn(u, w, rows, cap_of(u), "transplant", raw, f"TC:{u}:{w}", transplant={"builder": X.builder})
            del X
            torch.cuda.empty_cache()


# ================================================================================================ opening ladder
def ladder(R: Runner, tasks: list[str]) -> None:
    import ladder as LD

    LD.run_ladder(R, tasks)


@logger.catch(reraise=True)
def main() -> None:
    cmd = sys.argv[1]
    tasks = list(TASK_ORDER_RUN)
    if "--tasks" in sys.argv:
        tasks = sys.argv[sys.argv.index("--tasks") + 1].split(",")
    setup_logging(f"gen_{cmd}")
    kind = "pt" if cmd == "stage1_pt" else "it"
    R = Runner(kind)
    if cmd == "it_tests":
        r = it_tests(R)
        logger.info(f"it tests all_pass={r['all_pass']}")
    elif cmd == "engine_check":
        engine_check(R)
    elif cmd == "stage1_it":
        stage1_it(R, tasks)
    elif cmd == "stage1_pt":
        stage1_pt(R, tasks, plain="--no-plain" not in sys.argv)
    elif cmd == "ladder":
        ladder(R, tasks)
    elif cmd == "stage2":
        seeds = DIR_SEEDS
        if "--n-dirs" in sys.argv:
            seeds = DIR_SEEDS[:int(sys.argv[sys.argv.index("--n-dirs") + 1])]
        stage2(R, tasks, seeds)
    elif cmd == "confirm":
        confirm(R, tasks)
    elif cmd == "stage3_valid":
        stage3(R, "valid")
    elif cmd == "stage3":
        stage3(R, "full")
    elif cmd == "stage2_pipelined":
        seeds = DIR_SEEDS
        if "--n-dirs" in sys.argv:
            seeds = DIR_SEEDS[:int(sys.argv[sys.argv.index("--n-dirs") + 1])]
        stage2_pipelined(R, tasks, seeds)
    elif cmd == "stage2_confirm":
        stage2(R, tasks)
        import wait_labels as WL

        WL.wait_for(["raw_push.jsonl"], timeout_s=5400)
        confirm(R, tasks)
    logger.info(f"{cmd} finished")
    EG.free_model(R.model)
    gc.collect()


if __name__ == "__main__":
    main()
