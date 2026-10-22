#!/usr/bin/env python3
"""GPU runner for iteration 6 (Claim L, Gemma). One model on the GPU at a time; exp28's engine (bf16, sdpa, CRN
inverse-CDF sampler, displacement-targeted prefill push) is reused unchanged.

Usage: python src/gen6.py <stage> [--tasks R6,T04] [--limit N]
  it_session    U-tests (U1-U3, U5 key maps vs exp28, U7 tf batch, U9) + engine check + clean-state check (U6)
                + forced programs (S5 writers) + it twin top-up (S4)       [it model]
  forced_topup  +20 forced programs for algorithms with < 10 kept (needs labels)                    [it model]
  qlik          teacher-forced q_lik scores (S5) incl. the fp32 subsample                            [it model]
  ptfs          few-shot pt repertoire top-up (S2), staged A/B/C on correct-count support            [pt model]
  push6         fresh FD (8 directions, alpha 2) + fresh PN (alpha 2) + confirmations (S7)          [it model]
Rows stream to data/raw_<stage>.jsonl; batch timing to results/timing_batches6.jsonl.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHA6, BAND, CAPTURE_BLOCKS, D_MODEL, DATA_DIR, DIR_SEEDS6, E28, E28_DATA, E28_RESULTS,
                 FD6_CONFIRM_SLOTS, FD6_STAGE1_SLOTS, FORCED_KEEP, FORCED_N, MAX_NEW_PLAIN, MODELS, NS_FORCED, NS_PN,
                 NS_PTFS, PN6_SLOTS, PRED_DIR, PTFS_B, PTFS_CAP, PTFS_MIN_CORRECT, PTFS_STAGE, PUSH_TASKS6,
                 QLIK_WINDOW, RESULTS_DIR, SLOT_PREFIX, T_HOT, TEMPLATE_IDS, TWIN6_T10_SLOTS, TWIN6_T13_SLOTS,
                 append_jsonl, cap_of, read_json, read_jsonl, setup_logging, utc_now, write_json)
import engine as EG
import prompts as PG
import prompts6 as P6
from push import make_push_edits
from units import unit_n

TIMING = RESULTS_DIR / "timing_batches6.jsonl"
RAW = {s: DATA_DIR / f"raw_{s}.jsonl" for s in ("engine6", "twin6", "forced6", "ptfs6", "push6", "confirm6")}
TWIN_B = 50
FORCED_B = 48
EXP28_TWIN_TASK_ORDER = ("T2", "T03", "T05", "T10", "T1", "T06", "T04", "R1", "T08", "R3", "T13", "R6", "T14", "T11", "R2")


def done_ids(path: Path) -> set[str]:
    return {r["row_id"] for r in read_jsonl(path)}


def labels_now() -> dict[str, dict[str, Any]]:
    return {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}


def wait_labels(row_ids: set[str], timeout_s: float = 2400.0, poll: float = 5.0) -> bool:
    t0 = time.time()
    while True:
        have = set(labels_now())
        miss = row_ids - have
        if not miss:
            return True
        if time.time() - t0 > timeout_s:
            logger.warning(f"label wait timed out: {len(miss)} of {len(row_ids)} unlabelled")
            return False
        time.sleep(poll)


class Runner6:
    def __init__(self, kind: str, dtype: str = "bf16") -> None:
        self.kind = kind
        self.dtype = dtype
        self.tok, self.model, self.info = EG.load_model(kind)
        self.ctx: dict[tuple[str, str], dict[str, Any]] = {}

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

    # -------------------------------------------------------------------------------------------- coupled (push)
    def run_crn(self, task: str, w: str, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path,
                batch_id: str) -> list[dict[str, Any]]:
        """exp28 run_crn: single twin-prompt batch; FD rows (dir_kind 'escape', seed) and PN rows (dir_kind 'PN6',
        per-sample direction PCG64(stable_seed('iter6G-PN', task, w, slot))) pushed at BAND x spec, prefill only."""
        B = len(rows)
        t0 = time.time()
        ctx = self.task_ctx(task, w)
        p = PG.p_twin(task, w)
        PG.register(p)
        a, b = p["spec_start"], p["spec_end"]
        U = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
        alpha = torch.zeros(B, dtype=torch.float32, device="cuda")
        for i, r in enumerate(rows):
            d = None
            if r.get("dir_kind") == "escape":
                d = EG.seed_dir(int(r["direction_seed"]))
            elif r.get("dir_kind") == "PN6":
                d = EG.unit_dir(NS_PN, task, w, int(r["slot"]))
            if d is not None and (r.get("alpha") or 0) > 0:
                U[i] = torch.tensor(d, device="cuda")
                alpha[i] = float(r["alpha"])
        edits: dict[int, Any] = {}
        push_dir = None
        if bool((alpha > 0).any()):
            edits = make_push_edits(BAND, a, b, U, alpha, ctx["n"], {l: ctx["clean"]["S"][l] for l in BAND})
            push_dir = {"U": U, "tgt": {l: alpha[:, None] * ctx["n"][l][None, :] for l in BAND}}
        pre = EG.prefill_single(self.model, p["ids"], B, edits=edits, capture_ref=ctx["clean"], push_dir=push_dir)
        dS = pre.pop("disp_S", None)
        dR = pre.pop("disp_R", None)
        rel = pre.pop("relerr_along", None)
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        temps = np.array([float(r.get("temperature", 1.0)) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, temps, max_new)
        del pre
        # residual norm (ox) at the first band block, for the 'ratio to residual' log
        ox0 = float(ctx["n"][BAND[0]].mean())
        res_norm0 = float(ctx["clean"]["S"][BAND[0]].norm(dim=-1).mean())
        out = []
        for i, (r, g) in enumerate(zip(rows, res)):
            rd = None
            if dS is not None:
                rd = {"S_mean_band": float(dS[i, :len(BAND)].mean()), "R_last": float(dR[i, -1]),
                      "S_by_block": [round(float(x), 3) for x in dS[i]],
                      "ratio_to_residual_first_band": float(dS[i, 0]) / max(res_norm0, 1e-9),
                      "ox_unit_mean_first_band": ox0}
                if rel is not None and float(alpha[i]) > 0:
                    rd["rel_err_along_u_max"] = float(rel[i].max())
            out.append({"row_id": f"{stage}|{task}|{w}|{r['arm']}|{r['slot']}", "task": task, "arm": r["arm"],
                        "stage": stage, "model": MODELS[self.kind][0], "model_kind": self.kind,
                        "unit_kind": "path" if task in ("T1", "T2") else "bench",
                        "site": "spec_b11-22" if r.get("alpha") else None, "lambda": None, "alpha": r.get("alpha"),
                        "direction_seed": r.get("direction_seed"), "dir_kind": r.get("dir_kind"), "tkind": None,
                        "template": w, "slot": int(r["slot"]), "ukey": list(r["ukey"]),
                        "temperature": float(r.get("temperature", 1.0)), "top_k": None, "top_p": 1.0,
                        "thinking": False, "precision": "W16A16", "checkpoint": f"{MODELS[self.kind][0]}@{MODELS[self.kind][1]}",
                        "kernel": "sdpa bf16", "hook_sha256": HOOK_SHA, "prompt_sha256": p["prompt_sha256"],
                        "prompt_kind": p["kind"], "text": g["text"], "token_ids": g["token_ids"],
                        "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"], "realised_disp": rd,
                        "pad": False, "batch_id": batch_id, "B": B, "max_new": max_new, "provenance": "iter6",
                        "utc": utc_now()})
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": task, "w": w, "B": B, "seconds": dt,
                               "steps": res[0]["steps"], "max_new": max_new, "model": self.kind, "utc": utc_now()}])
        fr = dict(zip(*np.unique([g["finish_reason"] for g in res], return_counts=True)))
        logger.info(f"{batch_id}: B={B} {dt:.1f}s, {res[0]['steps']} steps, finish {fr}")
        return out

    # -------------------------------------------------------------------------------------------- single prompt
    def run_single(self, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path, batch_id: str,
                   fence_stop: bool = True, plain_stop: bool = False) -> list[dict[str, Any]]:
        """All rows share one prompt: batched prefill of the prompt repeated B times, decode without an attention
        mask (exp28 run_single_free); rows carry their own CRN uniforms. Same output rows as run_multi."""
        p = rows[0]["prompt"]
        assert all(r["prompt"]["prompt_sha256"] == p["prompt_sha256"] for r in rows)
        t0 = time.time()
        PG.register(p)
        pre = EG.prefill_single(self.model, p["ids"], len(rows))
        return self._finish(rows, pre, max_new, stage, raw_path, batch_id, fence_stop, plain_stop, t0, "single_prompt")

    # -------------------------------------------------------------------------------------------- multi-prompt
    def run_multi(self, rows: list[dict[str, Any]], max_new: int, stage: str, raw_path: Path, batch_id: str,
                  fence_stop: bool = True, plain_stop: bool = False) -> list[dict[str, Any]]:
        """exp28 run_multi with per-row temperatures: each distinct prompt prefilled at batch 1, KV right-aligned
        with masked left pads; rows carry their own CRN uniforms (ukey). No edits (twin, forced, few-shot)."""
        t0 = time.time()
        for r in rows:
            PG.register(r["prompt"])
        pre = EG.prefill_multi(self.model, [r["prompt"]["ids"] for r in rows])
        return self._finish(rows, pre, max_new, stage, raw_path, batch_id, fence_stop, plain_stop, t0, "multi_prompt")

    def _finish(self, rows: list[dict[str, Any]], pre: dict[str, Any], max_new: int, stage: str, raw_path: Path,
                batch_id: str, fence_stop: bool, plain_stop: bool, t0: float, batch_kind: str) -> list[dict[str, Any]]:
        Us = np.stack([EG.u_stream(*r["ukey"], n=max_new) for r in rows])
        temps = np.array([float(r.get("temperature", 1.0)) for r in rows])
        res = EG.decode(self.model, self.tok, pre, Us, temps, max_new, fence_stop=fence_stop, plain_stop=plain_stop)
        del pre
        out = []
        for r, g in zip(rows, res):
            p = r["prompt"]
            rec = {"row_id": r["row_id"], "task": r["task"], "arm": r["arm"], "stage": stage,
                   "model": MODELS[self.kind][0], "model_kind": self.kind,
                   "unit_kind": "path" if r["task"] in ("T1", "T2") else "bench", "site": None, "lambda": None,
                   "alpha": 0.0, "direction_seed": None, "dir_kind": None, "tkind": None,
                   "template": r.get("template"), "slot": int(r["slot"]), "ukey": list(r["ukey"]),
                   "temperature": float(r.get("temperature", 1.0)), "top_k": None, "top_p": 1.0, "thinking": False,
                   "precision": "W16A16", "checkpoint": f"{MODELS[self.kind][0]}@{MODELS[self.kind][1]}",
                   "kernel": "sdpa bf16", "hook_sha256": HOOK_SHA, "prompt_sha256": p["prompt_sha256"],
                   "prompt_kind": p["kind"], "text": g["text"], "token_ids": g["token_ids"],
                   "finish_reason": g["finish_reason"], "n_new_tokens": g["n_tokens"], "realised_disp": None,
                   "pad": False, "batch_id": batch_id, "B": len(rows), "max_new": max_new,
                   "batch_kind": batch_kind, "provenance": "iter6", "utc": utc_now()}
            for k in ("family", "exemplars", "forced_mode", "paraphrase_id", "ptfs_stage"):
                if k in r:
                    rec[k] = r[k]
            if p.get("prefix") and r["arm"] == "pt_fs":
                rec["program_prefix"] = p["prefix"]
            out.append(rec)
        append_jsonl(raw_path, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "stage": stage, "task": rows[0]["task"], "w": None,
                               "B": len(rows), "seconds": dt, "steps": res[0]["steps"], "max_new": max_new,
                               "model": self.kind, "utc": utc_now()}])
        fr = dict(zip(*np.unique([g["finish_reason"] for g in res], return_counts=True)))
        logger.info(f"{batch_id}: B={len(rows)} {dt:.1f}s, {res[0]['steps']} steps, finish {fr}")
        return out


def _hook_sha() -> str:
    import hashlib

    h = hashlib.sha256()
    for f in ("push.py", "engine.py", "units.py"):
        h.update((Path(__file__).resolve().parent / f).read_bytes())
    return h.hexdigest()


HOOK_SHA = _hook_sha()


# ================================================================================================ GPU tests (it)
def it_tests(R: Runner6) -> dict[str, Any]:
    """U1 alpha-0 rows bit-identical to unpushed rows; U2 a CRN slot's tokens do not depend on its batch-mates;
    U3 realised displacement along u = alpha n within 0.2%; U5 key map / vocab identical to exp28's recorded it AND
    pt hashes; U7 tf_logprobs batch 1 vs batch 4 with padding; U9 memory peak at B and P_max."""
    res: dict[str, Any] = {}
    B = 8
    task = "R6"
    ctx = R.task_ctx(task, "W1")
    tw, clean, n = ctx["twin"], ctx["clean"], ctx["n"]
    ids, a, b = tw["ids"], tw["spec_start"], tw["spec_end"]
    U = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
    alpha = torch.zeros(B, dtype=torch.float32, device="cuda")
    for i in range(B // 2, B):
        U[i] = torch.tensor(EG.seed_dir(DIR_SEEDS6[i]), device="cuda")
        alpha[i] = ALPHA6
    edits = make_push_edits(BAND, a, b, U, alpha, n, {l: clean["S"][l] for l in BAND})
    pdir = {"U": U, "tgt": {l: alpha[:, None] * n[l][None, :] for l in BAND}}
    pre_push = EG.prefill_single(R.model, ids, B, edits=edits, capture_ref=clean, push_dir=pdir)
    pre_none = EG.prefill_single(R.model, ids, B)
    z = list(range(B // 2))
    res["U1_alpha0_bit_identical_logits"] = bool(torch.equal(pre_push["logits"][z], pre_none["logits"][z]))
    rel = pre_push["relerr_along"][B // 2:]
    res["U3_max_rel_err_along_u"] = float(rel.max())
    res["U3_pass"] = float(rel.max()) < 2e-3
    del pre_push, pre_none
    torch.cuda.empty_cache()
    Uu = np.stack([EG.u_stream(SLOT_PREFIX, task, "W1", k, n=96) for k in range(B)])
    preA = EG.prefill_single(R.model, ids, B)
    outA = EG.decode(R.model, R.tok, preA, Uu, np.ones(B), 96, fence_stop=False)
    U2 = Uu.copy()
    U2[1:] = np.stack([EG.u_stream("u2_other6", task, k, n=96) for k in range(1, B)])
    U3d = torch.zeros(B, D_MODEL, dtype=torch.float32, device="cuda")
    al3 = torch.zeros(B, dtype=torch.float32, device="cuda")
    for i in range(1, B):
        U3d[i] = torch.tensor(EG.seed_dir(DIR_SEEDS6[i % 8]), device="cuda")
        al3[i] = ALPHA6
    e3 = make_push_edits(BAND, a, b, U3d, al3, n, {l: clean["S"][l] for l in BAND})
    preB = EG.prefill_single(R.model, ids, B, edits=e3)
    outB = EG.decode(R.model, R.tok, preB, U2, np.ones(B), 96, fence_stop=False)
    res["U2_crn_slot0_independent_of_batchmates"] = outA[0]["token_ids"] == outB[0]["token_ids"]
    # U5: key map + vocab against exp28's recorded it and pt hashes
    it28 = read_json(E28_RESULTS / "tests_gpu_it.json")["model_info"]
    pt28 = read_json(E28_RESULTS / "tests_gpu_pt.json")["model_info"]
    res["U5_key_map_equals_exp28_it"] = R.info["key_map_sha256"] == it28["key_map_sha256"]
    res["U5_key_map_equals_exp28_pt"] = R.info["key_map_sha256"] == pt28["key_map_sha256"]
    res["U5_vocab_equals_exp28_it_and_pt"] = R.info["vocab_sha256"] == it28["vocab_sha256"] == pt28["vocab_sha256"]
    # U7: teacher forcing batch 1 vs batch 4 (right-padded) on the same sequence
    seq = ids + R.tok("```python\ndef solve(nums, target):\n    lo, hi = 0, len(nums) - 1\n",
                      add_special_tokens=False)["input_ids"]
    tg = list(range(len(ids), len(seq)))
    lp1 = EG.tf_logprobs(R.model, seq, tg)
    lp4 = tf_logprobs_padded(R.model, [seq, ids + seq[len(ids):len(ids) + 3], seq[:len(seq) - 2], seq], tg)
    res["U7_tf_batch1_vs_batch4_max_abs_delta"] = float(np.max(np.abs(np.array(lp1) - np.array(lp4))))
    # U9: memory at B=50 with the longest twin + the path cap
    longest = max(((t, w) for t in ALL_TASKS for w in TEMPLATE_IDS), key=lambda x: PG.p_twin(*x)["P"])
    p = PG.p_twin(*longest)
    torch.cuda.reset_peak_memory_stats()
    pre = EG.prefill_multi(R.model, [p["ids"]] * TWIN_B)
    cache = EG.build_prealloc(pre["kv"], pre["P"] + 1536 + 1)
    peak = torch.cuda.max_memory_allocated() / 1e9
    del cache, pre
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(0)
    res["U9_memory"] = {"task_w": list(longest), "P": p["P"], "B": TWIN_B, "max_new": 1536, "peak_alloc_gb": peak,
                        "vram_total_gb": total / 1e9, "pass": total / 1e9 - peak >= 1.0}
    res["model_info"] = R.info
    res["all_pass"] = bool(res["U1_alpha0_bit_identical_logits"] and res["U3_pass"]
                           and res["U2_crn_slot0_independent_of_batchmates"] and res["U5_key_map_equals_exp28_it"]
                           and res["U5_vocab_equals_exp28_it_and_pt"] and res["U9_memory"]["pass"])
    write_json(RESULTS_DIR / "tests_gpu_it6.json", res)
    logger.info(f"it tests: { {k: v for k, v in res.items() if k != 'model_info'} }")
    return res


@torch.no_grad()
def tf_logprobs_padded(model: Any, seqs: list[list[int]], targets: list[int], row: int = 3) -> list[float]:
    """Right-padded batch forward (pad id 0, causal mask makes right padding inert); returns row `row` log-probs."""
    L = max(len(s) for s in seqs)
    inp = torch.zeros(len(seqs), L, dtype=torch.long, device="cuda")
    att = torch.zeros(len(seqs), L, dtype=torch.long, device="cuda")
    for i, s in enumerate(seqs):
        inp[i, :len(s)] = torch.tensor(s, device="cuda")
        att[i, :len(s)] = 1
    out = model.model(input_ids=inp, attention_mask=att, use_cache=False)
    pos = torch.tensor([t - 1 for t in targets], device="cuda")
    lg = EG.lm_logits(model, out.last_hidden_state[row, pos])
    lp = torch.log_softmax(lg, dim=-1)
    tg = torch.tensor([seqs[row][t] for t in targets], device="cuda")
    return lp.gather(-1, tg[:, None])[:, 0].cpu().tolist()


# ================================================================================================ engine check
def engine_check(R: Runner6, tasks: list[str]) -> None:
    """exp28 twin slots 0-1 x W1-W5 for all 15 tasks (multi-prompt, B 10 per task, exp28 ukeys, caps) + the exp28
    R6 escaping direction at alpha 2, slots 0-1 x W1-W5 (single-prompt CRN batches)."""
    raw = RAW["engine6"]
    done = done_ids(raw)
    for t in tasks:
        rows = [{"row_id": f"engine6|{t}|{w}|twin|{k}", "task": t, "arm": "twin", "slot": k, "template": w,
                 "ukey": (SLOT_PREFIX, t, w, k), "prompt": PG.p_twin(t, w)} for w in TEMPLATE_IDS for k in (0, 1)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            R.run_multi(rows, cap_of(t), "engine6", raw, f"EC6:{t}")
    esc = read_json(E28_RESULTS / "escape.json")
    r6 = esc.get("R6", {}).get("primary", {})
    conf = [k for k in (r6.get("confirmed") or []) if k.endswith("_a2")]
    if not conf:
        logger.warning("no confirmed R6 alpha-2 escape in exp28 escape.json; engine-check push arm skipped")
        return
    s = int(conf[0].split("_a")[0])
    for w in TEMPLATE_IDS:
        rows = [{"arm": f"esc{s}_a2", "slot": k, "ukey": (SLOT_PREFIX, "R6", w, k), "alpha": 2.0,
                 "dir_kind": "escape", "direction_seed": s} for k in (0, 1)]
        if {f"engine6|R6|{w}|esc{s}_a2|{k}" for k in (0, 1)} <= done:
            continue
        R.run_crn("R6", w, rows, cap_of("R6"), "engine6", raw, f"EC6:R6:{w}:esc{s}")


def clean_state_check(R: Runner6, tasks: list[str]) -> dict[str, Any]:
    """U6: recomputed clean it states (BAND x spec) vs exp28 cache/hit_<task>_<W>.pt (read in place, bf16)."""
    from cfg import upstream

    cdir = upstream()["exp28"] / "cache"      # exp28 (art_hG0QPiaIPNhP) sibling folder, read in place
    out = {}
    for t in tasks:
        for w in TEMPLATE_IDS:
            tw = PG.p_twin(t, w)
            st = EG.clean_states(R.model, tw["ids"], tw["spec_start"], tw["spec_end"], BAND)
            mine = torch.stack([st["S"][l] for l in BAND]).to(torch.bfloat16).float().cpu()
            pth = cdir / f"hit_{t}_{w}.pt"
            if not pth.exists():
                out[f"{t}|{w}"] = {"exp28_cache": "missing"}
                continue
            d = torch.load(pth, map_location="cpu")
            ref = d["S"].float()
            out[f"{t}|{w}"] = {"max_abs_diff": float((mine - ref).abs().max()),
                               "max_rel_diff": float(((mine - ref).norm(dim=-1) / ref.norm(dim=-1).clamp(min=1e-6)).max()),
                               "bit_identical": bool(torch.equal(mine, ref)),
                               "prompt_sha_equal": d.get("prompt_sha256") == tw["prompt_sha256"]}
            del d, st
    res = {"per_task_template": out,
           "n_bit_identical": sum(1 for v in out.values() if v.get("bit_identical")), "n": len(out),
           "max_abs_diff_overall": max((v.get("max_abs_diff", 0.0) for v in out.values()), default=None)}
    write_json(RESULTS_DIR / "clean_state_check.json", res)
    logger.info(f"U6 clean states: {res['n_bit_identical']}/{res['n']} bit-identical; max|diff| {res['max_abs_diff_overall']}")
    return res


# ================================================================================================ S4 twin top-up
def twin_topup(R: Runner6, tasks: list[str]) -> None:
    raw = RAW["twin6"]
    done = done_ids(raw)
    t_start = time.time()
    for ti, t in enumerate(tasks):
        groups = []
        for lo in range(10, 40, 10):      # T 1.0 slots 10-39 (exp28 slots 0-9 reused)
            groups.append((1.0, "twin_T10", range(lo, lo + 10)))
        for lo in (0, 10):                # T 1.3 slots 0-19, same 'iter5E' uniforms
            groups.append((T_HOT, "twin_T13", range(lo, lo + 10)))
        for temp, arm, ks in groups:
            rows = [{"row_id": f"twin6|{t}|{w}|{arm}|{k}", "task": t, "arm": arm, "slot": k, "template": w,
                     "ukey": (SLOT_PREFIX, t, w, k), "prompt": PG.p_twin(t, w), "temperature": temp}
                    for w in TEMPLATE_IDS for k in ks]
            rows = [r for r in rows if r["row_id"] not in done]
            if rows:
                R.run_multi(rows, cap_of(t), "twin6", raw, f"TW6:{t}:{arm}:{ks.start}")
        el = time.time() - t_start
        logger.info(f"twin top-up {t} done ({ti + 1}/{len(tasks)}); {el / 60:.1f} min; "
                    f"eta {el / (ti + 1) * (len(tasks) - ti - 1) / 60:.1f} min")


# ================================================================================================ S5 forced programs
def forced_rows(t: str, modes: list[str], js: range) -> list[dict[str, Any]]:
    rows = []
    for m in modes:
        for k in range(5):
            p = P6.p_forced(t, m, k)
            for j in js:
                rows.append({"row_id": f"forced6|{t}|{m}|k{k}|{j}", "task": t, "arm": f"forced_{m}",
                             "slot": k * 100 + j, "template": f"k{k}", "ukey": (NS_FORCED, t, m, k, j), "prompt": p,
                             "forced_mode": m, "paraphrase_id": k, "temperature": 1.0})
    return rows


def forced_gen(R: Runner6, tasks: list[str], top_up: bool = False) -> None:
    raw = RAW["forced6"]
    done = done_ids(raw)
    for t in tasks:
        modes = P6.forced_modes(t)
        if top_up:
            kept = forced_kept_counts(t)
            modes = [m for m in modes if kept.get(m, 0) < FORCED_KEEP]
            if not modes:
                continue
            rows = forced_rows(t, modes, range(4, 8))       # +20 per algorithm (4 per paraphrase)
        else:
            rows = forced_rows(t, modes, range(0, 4))       # 20 per algorithm (4 per paraphrase)
        rows = [r for r in rows if r["row_id"] not in done]
        for bi in range(0, len(rows), FORCED_B):
            R.run_multi(rows[bi:bi + FORCED_B], cap_of(t), "forced6", raw, f"FO6:{t}:{'top' if top_up else 'b'}{bi // FORCED_B}")


def forced_kept_counts(t: str) -> dict[str, int]:
    labs = labels_now()
    out: dict[str, int] = {}
    for r in read_jsonl(RAW["forced6"]):
        if r["task"] != t:
            continue
        lab = labs.get(r["row_id"])
        if lab and lab.get("passed") and lab.get("label") == r["forced_mode"]:
            out[r["forced_mode"]] = out.get(r["forced_mode"], 0) + 1
    return out


# ================================================================================================ S2 pt few-shot
def ptfs_correct_support(t: str) -> dict[str, int]:
    """Pooled CORRECT pt programs (exp28 chat + exp28 plain + few-shot) for a task (outcome-blind w.r.t. the it model)."""
    n = {"exp28_chat": 0, "exp28_plain": 0, "fewshot": 0}
    for r in read_jsonl(E28_DATA / "labels.jsonl"):
        if r["task"] == t and r.get("stage") in ("ptchat", "ptplain") and r.get("passed") \
                and r["label"] not in ("invalid", "disputed"):
            n["exp28_chat" if r["stage"] == "ptchat" else "exp28_plain"] += 1
    labs = labels_now()
    for r in read_jsonl(RAW["ptfs6"]):
        if r["task"] != t:
            continue
        lab = labs.get(r["row_id"])
        if lab and lab.get("passed") and lab["label"] not in ("invalid", "disputed"):
            n["fewshot"] += 1
    n["total"] = n["exp28_chat"] + n["exp28_plain"] + n["fewshot"]
    return n


def ptfs_rows(t: str, ks: range, stage_tag: str) -> list[dict[str, Any]]:
    prompts = {f: P6.p_fewshot(t, f) for f in ("F_bench", "F_he")}
    rows = []
    for k in ks:
        fam = "F_bench" if k % 2 == 0 else "F_he"
        rows.append({"row_id": f"ptfs6|{t}|{fam}|pt_fs|{k}", "task": t, "arm": "pt_fs", "slot": k, "template": fam,
                     "ukey": (NS_PTFS, t, k), "prompt": prompts[fam], "family": fam,
                     "exemplars": prompts[fam]["exemplars"], "ptfs_stage": stage_tag, "temperature": 1.0})
    return rows


def ptfs(R: Runner6, tasks: list[str], limit: int | None = None, bc_tasks: list[str] | None = None,
         max_stage: str = "C") -> None:
    """Stages A/B/C. Stage A for every task; stages B/C (time-based restriction, decided before any stage-B row
    and independent of outcomes) only for `bc_tasks` (the 8 push units) and up to `max_stage`."""
    raw = RAW["ptfs6"]
    log = []
    for si, tag in enumerate(("A", "B", "C")):
        if tag > max_stage:
            break
        lo, hi = si * PTFS_STAGE, (si + 1) * PTFS_STAGE
        todo = []
        for t in tasks:
            if si > 0 and bc_tasks is not None and t not in bc_tasks:
                continue
            if si > 0:
                ids = {r["row_id"] for r in read_jsonl(raw) if r["task"] == t}
                wait_labels(ids, timeout_s=1800)
                sup = ptfs_correct_support(t)
                log.append({"task": t, "before_stage": tag, **sup, "utc": utc_now()})
                if sup["total"] >= PTFS_MIN_CORRECT:
                    continue
            todo.append(t)
        logger.info(f"few-shot stage {tag}: {len(todo)} tasks {todo}")
        for t in todo:
            done = done_ids(raw)
            rows = [r for r in ptfs_rows(t, range(lo, hi if limit is None else lo + limit), tag)
                    if r["row_id"] not in done]
            for fam in ("F_bench", "F_he"):
                fr = [r for r in rows if r["family"] == fam]
                for bi in range(0, len(fr), 50):
                    R.run_single(fr[bi:bi + 50], MAX_NEW_PLAIN, "ptfs6", raw, f"FS6:{t}:{tag}:{fam}:{bi // 50}",
                                 fence_stop=False, plain_stop=True)
        if not todo or limit is not None:
            break
    for t in tasks:
        ids = {r["row_id"] for r in read_jsonl(raw) if r["task"] == t}
        wait_labels(ids, timeout_s=1800)
        log.append({"task": t, "before_stage": "final", **ptfs_correct_support(t), "utc": utc_now()})
    append_jsonl(RESULTS_DIR / "ptfs_stopping_log.jsonl", log)


# ================================================================================================ S5 q_lik scoring
def qlik(R: Runner6, tasks: list[str], fp32_subsample: bool = False) -> None:
    import qlik6 as Q

    Q.score_all(R, tasks, fp32=fp32_subsample)


# ================================================================================================ S7 fresh pushes
def twin_rates(t: str) -> dict[str, float]:
    """Twin T 1.0 reference (N 200: exp28 slots 0-9 + new 10-39): pass rate and correct off-default catalogue share."""
    fc = read_json(PRED_DIR / "forecasts_G6.json")["units"][t]
    return {"pass": fc["twin_pass_T10"], "off_corr": fc["twin_off_corr_T10"], "D": fc["D"], "catalogue": fc["catalogue"]}


def stage1_pass(t: str, rows: list[dict[str, Any]], tw: dict[str, Any]) -> dict[str, Any]:
    labs = labels_now()
    cells: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["arm"].startswith("esc"):
            lab = labs.get(r["row_id"])
            if lab:
                cells.setdefault(r["arm"], []).append(lab)
    out = {}
    for arm, rr in cells.items():
        n = len(rr)
        oc = sum(1 for x in rr if x.get("passed") and x["label"] in tw["catalogue"] and x["label"] != tw["D"]) / n
        pr = sum(1 for x in rr if x.get("passed")) / n
        out[arm] = {"n": n, "off_corr": oc, "pass": pr,
                    "stage1_pass": (oc - tw["off_corr"] >= 0.20) and (pr >= 0.8 * tw["pass"])}
    return out


def push6(R: Runner6, tasks: list[str], drop_fd_for: tuple[str, ...] = ()) -> None:
    raw, rawc = RAW["push6"], RAW["confirm6"]
    s1log = []
    prev = None
    for t in list(tasks) + [None]:
        if t is not None:
            done = done_ids(raw)
            tw = twin_rates(t)
            if tw["D"] is None:
                logger.info(f"push6 {t}: NO DEFAULT at N 300 -> no push (leaves L)")
            else:
                for w in TEMPLATE_IDS:
                    rows = []
                    if t not in drop_fd_for:
                        for s in DIR_SEEDS6:
                            for k in FD6_STAGE1_SLOTS:
                                rows.append({"arm": f"esc{s}_a2", "slot": k, "ukey": (SLOT_PREFIX, t, w, k),
                                             "alpha": ALPHA6, "dir_kind": "escape", "direction_seed": s})
                    for k in PN6_SLOTS:
                        rows.append({"arm": "pn6_a2", "slot": k, "ukey": (SLOT_PREFIX, t, w, k), "alpha": ALPHA6,
                                     "dir_kind": "PN6", "direction_seed": "PN6"})
                    rows = [r for r in rows if f"push6|{t}|{w}|{r['arm']}|{r['slot']}" not in done]
                    if rows:
                        R.run_crn(t, w, rows, cap_of(t), "push6", raw, f"PU6:{t}:{w}")
        if prev is not None:
            prow = [r for r in read_jsonl(raw) if r["task"] == prev]
            wait_labels({r["row_id"] for r in prow}, timeout_s=1500)
            tw = twin_rates(prev)
            st = stage1_pass(prev, prow, tw)
            passing = sorted(a for a, v in st.items() if v["stage1_pass"])
            s1log.append({"task": prev, "twin": tw, "stage1": st, "passing": passing, "utc": utc_now()})
            done = done_ids(rawc)
            for w in TEMPLATE_IDS:
                rows = [{"arm": a, "slot": k, "ukey": (SLOT_PREFIX, prev, w, k), "alpha": ALPHA6, "dir_kind": "escape",
                         "direction_seed": int(a[3:].split("_a")[0])} for a in passing for k in FD6_CONFIRM_SLOTS]
                rows = [r for r in rows if f"confirm6|{prev}|{w}|{r['arm']}|{r['slot']}" not in done]
                for bi in range(0, len(rows), 42):
                    R.run_crn(prev, w, rows[bi:bi + 42], cap_of(prev), "confirm6", rawc, f"CF6:{prev}:{w}:b{bi // 42}")
            logger.info(f"push6 {prev}: stage-1 passing {passing}")
        prev = t
    append_jsonl(RESULTS_DIR / "push6_stage1_log.jsonl", s1log)


@logger.catch(reraise=True)
def main() -> None:
    cmd = sys.argv[1]
    tasks = list(EXP28_TWIN_TASK_ORDER)
    if "--tasks" in sys.argv:
        tasks = sys.argv[sys.argv.index("--tasks") + 1].split(",")
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    setup_logging(f"gen6_{cmd}")
    kind = "pt" if cmd == "ptfs" else "it"
    R = Runner6(kind)
    if cmd == "it_tests":
        it_tests(R)
    elif cmd == "engine_check":
        engine_check(R, tasks)
    elif cmd == "it_session":
        if not (RESULTS_DIR / "tests_gpu_it6.json").exists():
            it_tests(R)
        engine_check(R, tasks)
        if not (RESULTS_DIR / "clean_state_check.json").exists():
            clean_state_check(R, list(PUSH_TASKS6))
        forced_gen(R, tasks)
        twin_topup(R, tasks)
    elif cmd == "twin":
        twin_topup(R, tasks)
    elif cmd == "forced":
        forced_gen(R, tasks)
    elif cmd == "forced_topup":
        forced_gen(R, tasks, top_up=True)
    elif cmd == "qlik":
        qlik(R, tasks)
    elif cmd == "ptfs":
        bc = sys.argv[sys.argv.index("--bc-tasks") + 1].split(",") if "--bc-tasks" in sys.argv else None
        ms = sys.argv[sys.argv.index("--max-stage") + 1] if "--max-stage" in sys.argv else "C"
        ptfs(R, tasks, limit, bc, ms)
    elif cmd == "push6":
        tasks = list(PUSH_TASKS6) if "--tasks" not in sys.argv else tasks
        drop = tuple(sys.argv[sys.argv.index("--drop-fd") + 1].split(",")) if "--drop-fd" in sys.argv else ()
        push6(R, tasks, drop)
    logger.info(f"{cmd} finished")
    EG.free_model(R.model)
    gc.collect()


if __name__ == "__main__":
    main()
