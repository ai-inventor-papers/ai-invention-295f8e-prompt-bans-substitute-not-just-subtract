#!/usr/bin/env python3
"""HF GPU stages (bf16 engine on this machine; plan S1, S3, S4, S5).

  base      S3: base intents with Qwen3-8B-Base (identical ids as IFG + forced 'Intent:'), then unload.
  tests     GPU smoke tests U1-U5, U7 -> results/unit_tests_gpu.json.
  ec        S1: exp19's engine check (rand_9002 on T03, rand_9004 on T2, alpha 1 ban unit, exp17 CRN keys) + 20
            decoding-path rows (T1.3 on T03 W1, TOPK10 on T2 W1) -> data/engine_check_raw.jsonl.
  calib     S4: DMD calibration (all 15 tasks, alpha 1 and 2) + the format pilot -> predictions/.
  knobs     S5: the knob queue (waits for commit1): stage 10 -> stage 100 -> timing extrapolation -> drop order ->
            full queue until the hard deadline -> data/samples_raw.jsonl.
Every step is resumable by (task, arm, template, slot).

usage: .venv/bin/python src/gen5.py base,tests,ec,calib,knobs
"""

from __future__ import annotations

import gc
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cfg as C
from cfg import (DATA_DIR, D_MODEL, E17, MODEL_ID, MODEL_REVISION, NORM_BLOCKS, PATH_TASKS, PRED_DIR, RESULTS_DIR, ROOT,
                 TEMPLATE_IDS, V_BLOCKS, append_deviation, append_jsonl, read_json, read_jsonl, sha256_text,
                 stable_seed, utc_now, write_json)
from cfg5 import (ARMS5, BASE_MODEL_ID, CAL_K, CAL_W, D5, DMD_BISECT_TOL, DMD_MAX_SECANT, DMD_ONPOLICY_TOL, DMD_STEPS,
                  DMD_T_RANGE, E23, EAP_A_MAX, EAP_B, INTENT_MAX, K_D5, K_ND10, K_ND10_REDUCED, ND10, P1, P2, P3, P4,
                  P5, PILOT_MIN_RATE, PILOT_N, PILOT_TASKS, PSL_A_MAX, PSL_B, PSL_B_MAX, PSL_C, TASKS15,
                  gen_deadline_unix, hf_engine_tag)
import sampling_v4 as S4
from engine5 import decode_record, decode_rows, kl_rows, kl_scaled, teacher_force_lsm
from engine_v4 import load_model, prefill, u_stream, vocab_len
from parsers import intent_valid, map_modes, parse_enum, parse_intent, parse_observations, pick_pair
from prompts5 import load_prompts, prompt_for, render_history

RAW = DATA_DIR / "samples_raw.jsonl"
STAGES = DATA_DIR / "stages.jsonl"
BASE_INT = DATA_DIR / "base_intents.jsonl"
EC_RAW = DATA_DIR / "engine_check_raw.jsonl"
REALISED = DATA_DIR / "realised.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
UT = RESULTS_DIR / "unit_tests_gpu.json"
DMD_FILE = PRED_DIR / "dmd_temperatures.json"
PILOT_FILE = PRED_DIR / "format_pilot.json"
PROBE_FILE = PRED_DIR / "batch_probe.json"
PRECISION = "bf16"
ENGINE = hf_engine_tag()
MAX_B = 24


def code_max_new(task: str) -> int:
    return 1536 if task in PATH_TASKS else 1024


def fence_kind(task: str) -> str:
    return "path" if task in PATH_TASKS else "bench"


def code_stream(task: str, w: str, k: int) -> np.ndarray:
    return u_stream(task, w, k, n=1536)


def r_q_table() -> tuple[np.ndarray, np.ndarray]:
    q = read_json(E23 / "results" / "qwen_ratio.json")["r_Q"]
    d = np.array([v["depth"] for v in q.values()])
    r = np.array([v["median"] for v in q.values()])
    o = np.argsort(d)
    return d[o], r[o]


_RQ = None


def r_at(l: int) -> float:
    global _RQ
    if _RQ is None:
        _RQ = r_q_table()
    return float(np.interp((l + 1) / 36, _RQ[0], _RQ[1]))


def pn5_direction(task: str, w: str, k: int, tag: str = "PN5") -> tuple[int, np.ndarray]:
    seed = stable_seed(task, tag, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return seed, (x / np.linalg.norm(x)).astype(np.float32)


def free_vram() -> int:
    f, _ = torch.cuda.mem_get_info(0)
    return f


# ------------------------------------------------------------------------------------------------ context
class Ctx(S4.TaskContext):
    """exp19 TaskContext (clean prefills with captured states, edited prefills with realised displacement) plus
    uncaptured prefills for prompts that never carry a push, the ban-free unit, and per-template freeing."""

    def __init__(self, model, tok, prompts, task):
        ban = None
        try:
            ban = S4.load_norms(task) if task != "R2" else np.load(C.INPUTS / "exp19" / "results" / "unit_R2.npy")
        except FileNotFoundError:
            ban = np.ones((12, 1), dtype=np.float32)
        super().__init__(model, tok, prompts, task, norms=ban.astype(np.float32), log_realised=True)
        self.plain_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.ban_np = ban

    def pre_of(self, w: str, kind: str, suffix: list[int] | None = None) -> dict[str, Any]:
        if kind in ("twin", "plain") and not suffix:
            return self.clean_prefill(w, kind)["pre"]
        p = self.prompt(w, kind)
        key = (p["w"], kind) if not suffix else None
        if key is not None and key in self.plain_cache:
            return self.plain_cache[key]
        ids = p["ids"] + (p.get("forced_ids") or []) if kind == "ifg" else list(p["ids"])
        if suffix:
            ids = ids + suffix
        pre = prefill(self.model, ids)
        if key is not None:
            self.plain_cache[key] = pre
        return pre

    def banfree(self, w: str, kind: str) -> dict[int, torch.Tensor]:
        base = self.clean_prefill(w, kind)
        return {l: base["S"][l].norm(dim=-1) * r_at(l) for l in V_BLOCKS}

    def release(self) -> None:
        self.clean.clear()
        self.plain_cache.clear()
        gc.collect()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ row specs
def spec_row(task: str, arm: str, w: str, k: int, stage: str = "code", **kw) -> dict[str, Any]:
    return {"task": task, "arm": arm, "w": w, "k": k, "stage": stage, **kw}


def materialise(ctx: Ctx, sp: dict[str, Any], dmd: dict[str, Any]) -> dict[str, Any]:
    """Turn a row spec into a decode_rows row (prefill + streams + controls)."""
    task, arm, w, k, stage = sp["task"], sp["arm"], sp["w"], sp["k"], sp["stage"]
    a = ARMS5[arm]
    mn = code_max_new(task)
    row: dict[str, Any] = {"u": code_stream(task, w, k), "T": a["T"], "top_k": a.get("top_k", 0),
                           "top_p": a.get("top_p", 1.0), "max_new": mn, "fence": True}
    meta: dict[str, Any] = {}
    if stage == "code" and a["decode"] == "pn":
        kind = a["kind"]
        seed, ud = pn5_direction(task, w, k)
        n_bf = ctx.banfree(w, kind)
        pre, rec = ctx.edited_prefill(w, kind, torch.tensor(ud, device=ctx.model.device), float(a["alpha"]),
                                      {"arm": arm, "slot": k, "direction_seed": seed}, n=n_bf)
        row["pre"] = pre
        ban = ctx.n
        ratio = {l: float((n_bf[l] / ban[l].clamp(min=1e-6)).mean()) for l in V_BLOCKS} \
            if ban[V_BLOCKS[0]].numel() == n_bf[V_BLOCKS[0]].numel() else None
        meta.update({"direction_seed": seed, "realised": rec, "unit": "banfree_rQ",
                     "unit_mean_b12": float(n_bf[12].mean()), "unit_ratio_banfree_over_ban": ratio})
    elif stage == "code" and arm in ("BINT",):
        bi = sp["base_intent"]
        row["pre"] = ctx.pre_of(w, "ifg", suffix=bi["intent_ids"])
        meta.update({"intent": bi["intent_text"], "intent_author": "base", "intent_valid": bi["valid"],
                     "intent_capped": bi["capped"], "intent_attempts": bi["attempts"]})
    elif stage == "code" and a["kind"] == "ifg":
        row["pre"] = ctx.pre_of(w, "ifg")
        row["intent"] = {"T": a["t_intent"], "u": u_stream(task, w, k, "IFG:intent", n=INTENT_MAX), "cap": INTENT_MAX}
        meta["intent_author"] = "instruct"
    elif stage == "code" and a["family"] == "DMD":
        row["pre"] = ctx.pre_of(w, "twin")
        T_d = dmd[task][str(float(a["dmd_alpha"]))]["T_dmd"]
        row.update({"T_early": T_d, "n_early": DMD_STEPS})
        meta["dmd_T"] = T_d
    elif stage == "code" and a["kind"] in ("twin", "plain", "novelty", "semseed"):
        row["pre"] = ctx.pre_of(w, a["kind"])
    elif stage == "A":
        kind = a["kind"]
        tag = f"{arm}:A" if sp.get("reask", 0) == 0 else None
        u = u_stream(task, w, k, f"{arm}:A", n=PSL_A_MAX) if sp.get("reask", 0) == 0 else \
            u_stream(task, w, k, f"{arm}:A", 1, n=PSL_A_MAX)
        row.update({"pre": ctx.pre_of(w, kind), "u": u, "max_new": PSL_A_MAX if arm == "PSL" else EAP_A_MAX,
                    "fence": False})
        if arm == "EAP":
            row.update({"T": 1.0, "top_p": 1.0})
        meta["stream_tag"] = tag or f"{arm}:A|1"
    elif stage in ("B", "C", "codeH"):
        ids = sp["hist_ids"]
        row["pre"] = prefill(ctx.model, ids)
        if stage == "B":
            row.update({"u": u_stream(task, w, k, "PSL:B", n=PSL_B_MAX), "max_new": PSL_B_MAX, "fence": False})
    else:
        raise ValueError(f"unknown spec {sp}")
    return {**row, "_meta": meta}


def batch_cap(task: str, P: int, max_steps: int) -> int:
    """Memory probe rule: rows x (P + max_new) x 147,456 B <= 0.8 x free VRAM, counting the transient per-row
    prefill copy (another P per row) and keeping 1 GB for activations and float64 sampler buffers."""
    per = (2 * P + max_steps + 1) * 147_456
    return max(1, min(MAX_B, int(0.8 * (free_vram() - 1.0e9) // per)))


def run_specs(model, tok, ctx: Ctx, specs: list[dict[str, Any]], block: str, dmd: dict[str, Any],
              deadline: float | None = None) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Decode a list of same-stage specs in memory-capped batches; equal-prompt-length rows are kept together.
    Returns (spec, decode result, meta) triples."""
    out = []
    if not specs:
        return out
    P_of = {}
    for sp in specs:
        key = (sp["arm"], sp["w"], sp["stage"])
        if sp["stage"] in ("B", "C", "codeH"):
            P_of[id(sp)] = len(sp["hist_ids"])
        else:
            kind = ARMS5[sp["arm"]]["kind"]
            p = prompt_for(ctx.pr, sp["task"], sp["w"], kind)
            P_of[id(sp)] = p["P"] + (len(p.get("forced_ids") or []) if kind == "ifg" else 0) + \
                (len(sp["base_intent"]["intent_ids"]) if sp["arm"] == "BINT" and sp["stage"] == "code" else 0)
    specs = sorted(specs, key=lambda s: (P_of[id(s)], s["arm"], s["w"], s["k"]))
    stage = specs[0]["stage"]
    ms = {"A": PSL_A_MAX, "B": PSL_B_MAX}.get(stage, code_max_new(specs[0]["task"]) + INTENT_MAX)
    i = 0
    while i < len(specs):
        if deadline is not None and time.time() > deadline:
            logger.warning(f"{block}: deadline reached, {len(specs) - i} rows not run")
            break
        Pmax = max(P_of[id(s)] for s in specs[i:i + MAX_B])
        bmax = batch_cap(specs[i]["task"], Pmax, ms)
        chunk = specs[i:i + bmax]
        i += len(chunk)
        t0 = time.time()
        rows = [materialise(ctx, sp, dmd) for sp in chunk]
        metas = [r.pop("_meta") for r in rows]
        res = decode_rows(model, rows, tok, fence_kind=fence_kind(chunk[0]["task"]))
        dt = time.time() - t0
        for sp, r, m in zip(chunk, res, metas):
            out.append((sp, r, m))
        append_jsonl(TIMING, [{"block": block, "task": chunk[0]["task"], "stage": stage,
                               "arms": dict(Counter(s["arm"] for s in chunk)), "B": len(chunk), "seconds": round(dt, 2),
                               "steps": res[0]["steps"], "n_length": sum(x["finish_reason"] == "length" for x in res),
                               "engine_path": res[0]["engine_path"], "utc": utc_now()}])
        logger.info(f"{block} {chunk[0]['task']} stage {stage} B={len(chunk)} {dict(Counter(s['arm'] for s in chunk))}: "
                    f"{dt:.1f}s, {res[0]['steps']} steps ({res[0]['engine_path']})")
        del rows
        torch.cuda.empty_cache()
    return out


def raw_row(tok, sp: dict[str, Any], r: dict[str, Any], m: dict[str, Any], prompts: dict, block: str,
            extra: dict[str, Any] | None = None) -> dict[str, Any]:
    task, arm, w, k = sp["task"], sp["arm"], sp["w"], sp["k"]
    a = ARMS5[arm]
    nv = vocab_len(tok)
    ids = r["token_ids"] if r is not None else []
    text = tok.decode([t for t in ids if t < nv], skip_special_tokens=True) if r is not None else ""
    p = prompt_for(prompts, task, w, a["kind"])
    rec = m.get("realised") if m else None
    disp = None
    if rec is not None and "disp_S" in rec:
        disp = {"S_b12": rec["disp_S"][12], "S_b23": rec["disp_S"][23], "S_b35": rec["disp_S"][35],
                "R_b23": rec["disp_R"][23], "R_b35": rec["disp_R"][35],
                "relerr_u_max": max(rec["rel_err_along_u"].values())}
    row = {"task": task, "unit": task, "unit_kind": "path_task" if task in PATH_TASKS else "bench_task", "arm": arm,
           "knob_class": a["family"], "template": w, "slot": k, "sample_id": f"{task}|{arm}|{w}|{k}",
           "crn_key": f"{task}|{w}|{k}", "u_seed": stable_seed(task, w, k), "site": "S0" if a.get("alpha") else None,
           "lambda": None, "alpha": a.get("alpha"), "direction_seed": (m or {}).get("direction_seed"),
           "temperature": a["T"], "t_intent": a.get("t_intent"), "dmd_T": (m or {}).get("dmd_T"),
           "temperature_schedule": (f"T={m['dmd_T']:.4f} for tokens 1-32, then {a['T']}" if m and m.get("dmd_T")
                                    else None),
           "top_k": a.get("top_k", 0), "top_p": a.get("top_p", 1.0), "min_p": 0.0, "thinking": False,
           "precision": PRECISION, "engine": ENGINE, "engine_path": r["engine_path"] if r else None,
           "prompt_kind": a["kind"], "prompt_sha256": p["prompt_sha256"], "P": p["P"], "model": MODEL_ID,
           "model_revision": MODEL_REVISION, "max_new": code_max_new(task), "block_id": block,
           "text": text, "token_ids": ids, "n_new_tokens": len(ids), "finish_reason": r["finish_reason"] if r else
           "invalid_stage", "intent_len": r.get("intent_len") if r else None,
           "realised_disp": disp, "utc": utc_now()}
    if m:
        for key in ("intent", "intent_author", "intent_valid", "intent_capped", "intent_attempts", "unit",
                    "unit_mean_b12", "unit_ratio_banfree_over_ban"):
            if key in m:
                row[key] = m[key]
    if r is not None and a["kind"] == "ifg" and arm != "BINT":
        it = parse_intent(text)
        row.update({"intent": it, "intent_valid": intent_valid(it), "intent_capped": r.get("intent_capped")})
    if extra:
        row.update(extra)
    return row


# ------------------------------------------------------------------------------------------------ S3 base intents
def stage_base(prompts: dict) -> None:
    have = {(r["task"], r["template"], int(r["slot"])) for r in read_jsonl(BASE_INT)}
    todo = [(t, w, k) for t in TASKS15 for w in TEMPLATE_IDS for k in (K_D5 if t in D5 else K_ND10)
            if (t, w, k) not in have]
    if not todo:
        logger.info("base intents: all present")
        return
    from transformers import AutoModelForCausalLM

    rev = read_json(PRED_DIR / "model_revisions.json")[BASE_MODEL_ID]["resolved_sha"]
    path = C.model_path(BASE_MODEL_ID, rev)
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0})
    model.eval().requires_grad_(False)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(C.model_path())
    btok = AutoTokenizer.from_pretrained(path)
    assert btok.get_vocab() == tok.get_vocab(), "base and instruct tokenizers differ"
    logger.info(f"base model {BASE_MODEL_ID}@{rev[:8]} loaded in {time.time() - t0:.0f}s")
    by_task = defaultdict(list)
    for t, w, k in todo:
        by_task[t].append((w, k))
    nv = vocab_len(tok)
    for t, items in by_task.items():
        pre_cache = {}
        pending = [(w, k, 0) for w, k in items]
        final: dict[tuple[str, int], dict[str, Any]] = {}
        attempts: dict[tuple[str, int], list[str]] = defaultdict(list)
        while pending:
            rows = []
            for w, k, r_ in pending:
                if w not in pre_cache:
                    p = prompts[(t, w, "ifg")]
                    pre_cache[w] = prefill(model, p["ids"] + p["forced_ids"])
                u = u_stream(t, w, k, "BINT:intent", n=INTENT_MAX) if r_ == 0 else \
                    u_stream(t, w, k, "BINT:intent", r_, n=INTENT_MAX)
                rows.append({"pre": pre_cache[w], "u": np.ones(2), "T": 1.0, "max_new": 1, "fence": False,
                             "intent": {"T": 1.3, "u": u, "cap": INTENT_MAX}})
            res = []
            for i in range(0, len(rows), 20):
                res += decode_rows(model, rows[i:i + 20], tok)
            nxt = []
            for (w, k, r_), r in zip(pending, res):
                ids = r["token_ids"][:r["intent_len"]]
                txt = tok.decode([x for x in ids if x < nv], skip_special_tokens=True)
                it = parse_intent(txt)
                ok = intent_valid(it) and r["intent_len"] > 0 and not any(x >= nv or x in (C.IM_END, C.ENDOFTEXT)
                                                                          for x in ids)
                attempts[(w, k)].append(it)
                if ids and ids[-1] in (C.IM_END, C.ENDOFTEXT):
                    ids = ids[:-1] + [198]
                rec = {"task": t, "template": w, "slot": k, "intent_ids": ids, "intent_text": it, "raw_text": txt,
                       "valid": bool(ok), "capped": bool(r["intent_capped"]), "attempt": r_,
                       "attempts": len(attempts[(w, k)]), "all_attempts": attempts[(w, k)], "model": BASE_MODEL_ID,
                       "revision": rev, "T": 1.3, "top_p": 1.0, "stream": f"{t}|{w}|{k}|BINT:intent" +
                       (f"|{r_}" if r_ else ""), "utc": utc_now()}
                if ok or r_ >= 2:
                    final[(w, k)] = rec
                else:
                    nxt.append((w, k, r_ + 1))
            pending = nxt
        append_jsonl(BASE_INT, [final[(w, k)] for w, k in items])
        logger.info(f"base intents {t}: {len(items)} rows, valid {sum(final[x]['valid'] for x in items)}/"
                    f"{len(items)}, resampled {sum(final[x]['attempts'] > 1 for x in items)}")
        del pre_cache
        torch.cuda.empty_cache()
    del model
    gc.collect()
    torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ unit tests
def stage_tests(model, tok, prompts) -> dict[str, Any]:
    if UT.exists():
        return read_json(UT)
    res: dict[str, Any] = {"utc": utc_now()}
    ctx = Ctx(model, tok, prompts, "T03")
    K10 = list(range(10))
    tw = ctx.pre_of("W1", "twin")

    def twin_rows(T_early=None, intent=None, restart=True):
        out = []
        for k in K10:
            r = {"pre": tw, "u": code_stream("T03", "W1", k), "T": 1.0, "max_new": 256, "fence": False}
            if T_early is not None:
                r.update({"T_early": T_early, "n_early": 32})
            if intent is not None:
                r["intent"] = {"T": 1.0, "u": code_stream("T03", "W1", k)[:64], "cap": 64}
                r["restart_code_stream"] = restart
            out.append(r)
        return out
    a = decode_rows(model, twin_rows(), tok)
    b = decode_rows(model, twin_rows(), tok)
    res["U1_determinism_10"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    d1 = decode_rows(model, twin_rows(T_early=1.0), tok)
    res["U2_dmd_T1_equals_twin_10"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, d1))
    i1 = decode_rows(model, twin_rows(intent=True, restart=False), tok)
    res["U2_ifg_t1_continuing_stream_equals_twin_10"] = sum(
        x["token_ids"][:200] == y["token_ids"][:200] for x, y in zip(a, i1))
    # U3: PN at alpha 0 (fresh directions) == TWIN
    rows0 = []
    n_bf = ctx.banfree("W1", "twin")
    relerr = []
    for k in K10:
        seed, ud = pn5_direction("T03", "W1", k)
        pre, rec = ctx.edited_prefill("W1", "twin", torch.tensor(ud, device=model.device), 0.0,
                                      {"arm": "U3", "slot": k, "direction_seed": seed}, n=n_bf)
        rows0.append({"pre": pre, "u": code_stream("T03", "W1", k), "T": 1.0, "max_new": 256, "fence": False})
    z = decode_rows(model, rows0, tok)
    res["U3_alpha0_equals_twin_10"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, z))
    # U4: displacement accuracy at alpha 1 and 2 (ban-free unit)
    for alpha in (1.0, 2.0):
        for k in range(3):
            seed, ud = pn5_direction("T03", "W1", k)
            _, rec = ctx.edited_prefill("W1", "twin", torch.tensor(ud, device=model.device), alpha,
                                        {"arm": "U4", "slot": k, "direction_seed": seed}, n=n_bf)
            relerr.append(float(np.mean(list(rec["rel_err_along_u"].values()))))
            res.setdefault("U4_disp_R_b23", []).append(rec["disp_R"][23])
    res["U4_mean_relerr_along_u"] = float(np.mean(relerr))
    res["U4_max_relerr_along_u"] = float(np.max(relerr))
    res["U4_pass"] = res["U4_mean_relerr_along_u"] < 1e-3
    # U5: left-padded path vs shared path (10 TWIN rows: with same-length mates vs with PLAIN mates -> padding)
    same = decode_rows(model, twin_rows() + twin_rows(T_early=1.0), tok)[:10]
    pl = ctx.pre_of("W1", "plain")
    mates = [{"pre": pl, "u": code_stream("T03", "W1", k), "T": 1.0, "max_new": 256, "fence": False} for k in K10]
    padded = decode_rows(model, twin_rows() + mates, tok)
    pad10 = padded[:10]
    agree, tot = 0, 0
    for x, y in zip(same, pad10):
        L = max(len(x["token_ids"]), len(y["token_ids"]))
        agree += sum(1 for p_, q_ in zip(x["token_ids"], y["token_ids"]) if p_ == q_)
        tot += L
    res["U5_engine_path_padded"] = padded[0]["engine_path"]
    res["U5_token_agreement"] = agree / max(tot, 1)
    res["U5_rows_identical"] = sum(x["token_ids"] == y["token_ids"] for x, y in zip(same, pad10))
    res["U5_pass"] = res["U5_token_agreement"] >= 0.95
    # U7: memory probe at the largest prompt + max_new
    longest = max((p for p in prompts.values() if p["task"] in TASKS15), key=lambda p: p["P"])
    torch.cuda.reset_peak_memory_stats()
    pre_l = prefill(model, longest["ids"])
    B = batch_cap(longest["task"], longest["P"], 1536 + INTENT_MAX)
    big = [{"pre": pre_l, "u": np.random.default_rng(0).random(1536), "T": 1.0, "max_new": 1536, "fence": False}
           for _ in range(B)]
    from engine5 import assemble_cache
    cache, Pmax, _ = assemble_cache(big, 1536 + INTENT_MAX)
    tokn = torch.full((B, 1), 13, device=model.device, dtype=torch.long)
    with torch.no_grad():
        for s in range(16):
            pos = torch.full((B, 1), Pmax + s, device=model.device, dtype=torch.long)
            model.model(input_ids=tokn, past_key_values=cache, position_ids=pos, use_cache=True)
    del cache, big
    _, total = torch.cuda.mem_get_info(0)
    res.update({"U7_B": B, "U7_longest_P": longest["P"], "U7_peak_GB": torch.cuda.max_memory_allocated() / 1e9,
                "U7_total_GB": total / 1e9})
    res["U7_pass"] = res["U7_peak_GB"] < 0.97 * res["U7_total_GB"]
    ctx.release()
    write_json(UT, res)
    logger.info(f"GPU unit tests: {res}")
    return res


# ------------------------------------------------------------------------------------------------ S1 engine check
def stage_ec(model, tok, prompts) -> None:
    S4.ENGINE_TAG, S4.QUANT = ENGINE, "bf16 (no quantisation)"
    done = {(r["task"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(EC_RAW)}
    K10 = list(range(10))
    for task, seed in (("T03", 9002), ("T2", 9004)):
        nm = S4.load_norms(task, source="exp17")
        ctx = S4.TaskContext(model, tok, prompts, task, norms=nm)
        rdir = np.load(E17 / "directions" / f"rand_{seed}.npy").astype(np.float32)
        defs = {"NEUTRAL": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "EC"},
                f"RAND{seed}_a1.0": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 1.0,
                                     "knob": "EC", "fixed_dir": rdir, "fixed_seed": seed,
                                     "norms": {l: torch.tensor(nm[j], device=model.device)
                                               for j, l in enumerate(V_BLOCKS)}},
                "T1.3": {"prompt": "twin", "T": 1.3, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "TEMP"},
                "TOPK10": {"prompt": "twin", "T": 1.0, "top_k": 10, "min_p": 0.0, "alpha": None, "knob": "TOPK10"}}
        for w in TEMPLATE_IDS:
            spec = [("NEUTRAL", K10), (f"RAND{seed}_a1.0", K10)]
            if all((task, w, a_, k) in done for a_, ks in spec for k in ks):
                continue
            rows = S4.run_batch(ctx, w, spec, f"EC:{task}:{w}", fence="auto", arm_defs=defs, write=False)
            append_jsonl(EC_RAW, rows)
        # decoding-path rows in exp19's own batch shape (a 20-row T1.3 + TOPK10 batch on the W1 twin prefill)
        spec = [("T1.3", K10), ("TOPK10", K10)]
        if not all((task, "W1", a_, k) in done for a_, ks in spec for k in ks):
            rows = S4.run_batch(ctx, "W1", spec, f"EC:{task}:W1:T1.3+TOPK10", fence="auto", arm_defs=defs,
                                write=False)
            append_jsonl(EC_RAW, rows)
        ctx.clean.clear()
        torch.cuda.empty_cache()
    logger.info("engine check rows written")


# ------------------------------------------------------------------------------------------------ S4 calibration
def calibrate_task(model, tok, prompts, task: str) -> dict[str, Any]:
    ctx = Ctx(model, tok, prompts, task)
    out: dict[str, Any] = {}
    clean_tok, clean_lsm = {}, {}
    for w in CAL_W:
        base = ctx.clean_prefill(w, "twin")
        rows = [{"pre": base["pre"], "u": u_stream(task, w, k, "CAL", n=DMD_STEPS), "T": 1.0} for k in CAL_K]
        rec = decode_record(model, rows, DMD_STEPS)
        clean_tok[w], clean_lsm[w] = rec["tokens"], rec["lsm"]

    def f_off(T: float) -> float:
        return float(np.mean([kl_scaled(clean_lsm[w], T).mean().item() for w in CAL_W]))
    for alpha in (1.0, 2.0):
        kls, deps, curves, unit12 = [], [], [], []
        for w in CAL_W:
            n_bf = ctx.banfree(w, "twin")
            unit12.append(float(n_bf[12].mean()))
            rows = []
            for k in CAL_K:
                seed, ud = pn5_direction(task, w, k, tag="PNCAL")
                pre, _ = ctx.edited_prefill(w, "twin", torch.tensor(ud, device=model.device), alpha,
                                            {"arm": "PNCAL", "slot": k, "direction_seed": seed}, n=n_bf)
                rows.append({"pre": pre, "u": u_stream(task, w, k, "CAL", n=DMD_STEPS), "T": 1.0})
            rec = decode_record(model, rows, DMD_STEPS)
            del rows
            lq = teacher_force_lsm(model, prompt_for(prompts, task, w, "twin")["ids"], rec["tokens"])
            kl = kl_rows(rec["lsm"], lq)
            kls.append(kl.cpu())
            deps.append(float((rec["tokens"] != clean_tok[w]).float().mean()))
            del rec, lq
            torch.cuda.empty_cache()
        K = torch.cat(kls, 0)
        K_PN = float(K.mean())
        # bisection on f_off (monotone increasing in T > 1)
        lo, hi = DMD_T_RANGE
        flag = None
        if f_off(hi) < K_PN:
            T_star, flag = hi, "UNREACHABLE"
        else:
            for _ in range(40):
                mid = math.sqrt(lo * hi)
                if f_off(mid) < K_PN:
                    lo = mid
                else:
                    hi = mid
                if hi / lo - 1 < DMD_BISECT_TOL / 4:
                    break
            T_star = math.sqrt(lo * hi)
        f_off_star = f_off(T_star)
        iters = []
        T_cur = T_star
        for it in range(DMD_MAX_SECANT + 1):
            fon_l, dep_l = [], []
            for w in CAL_W:
                base = ctx.clean_prefill(w, "twin")
                rows = [{"pre": base["pre"], "u": u_stream(task, w, k, "CAL", n=DMD_STEPS), "T": T_cur} for k in CAL_K]
                rec = decode_record(model, rows, DMD_STEPS)
                fon_l.append(kl_scaled(rec["lsm"], T_cur).mean().item())
                dep_l.append(float((rec["tokens"] != clean_tok[w]).float().mean()))
                del rec
            f_on = float(np.mean(fon_l))
            iters.append({"T": T_cur, "f_on": f_on, "f_off": f_off(T_cur), "token_departure_DMD": float(np.mean(dep_l))})
            if abs(f_on / K_PN - 1) <= DMD_ONPOLICY_TOL or it == DMD_MAX_SECANT or flag == "UNREACHABLE":
                break
            # secant-type update on log T using the off-policy curve as the local model: aim f_off at the target
            # corrected by the measured on/off ratio
            target = K_PN * f_off(T_cur) / max(f_on, 1e-12)
            lo, hi = DMD_T_RANGE
            if f_off(hi) < target:
                T_cur = hi
            else:
                for _ in range(40):
                    mid = math.sqrt(lo * hi)
                    if f_off(mid) < target:
                        lo = mid
                    else:
                        hi = mid
                    if hi / lo - 1 < DMD_BISECT_TOL / 4:
                        break
                T_cur = math.sqrt(lo * hi)
        last = iters[-1]
        out[str(alpha)] = {"T_dmd": last["T"], "T_bisect_off_policy": T_star, "K_PN": K_PN, "f_off": f_off_star,
                           "f_on": last["f_on"], "f_on_over_K": last["f_on"] / K_PN, "iterations": iters,
                           "n_secant_updates": len(iters) - 1, "flag": flag,
                           "converged": abs(last["f_on"] / K_PN - 1) <= DMD_ONPOLICY_TOL,
                           "token_departure_PN": float(np.mean(deps)),
                           "token_departure_DMD": last["token_departure_DMD"],
                           "kl_curve_PN": [float(x) for x in K.mean(0)], "unit_mean_b12": float(np.mean(unit12))}
        logger.info(f"DMD {task} alpha {alpha}: K_PN {K_PN:.4f} -> T_dmd {last['T']:.3f} (f_on/K {last['f_on'] / K_PN:.2f},"
                    f" {len(iters) - 1} updates); departure PN {np.mean(deps):.3f} DMD {last['token_departure_DMD']:.3f}")
    ctx.release()
    del clean_lsm
    torch.cuda.empty_cache()
    return out


def format_pilot(model, tok, prompts) -> dict[str, Any]:
    res: dict[str, Any] = {}
    nv = vocab_len(tok)
    for task in PILOT_TASKS:
        ctx = Ctx(model, tok, prompts, task)
        slots = [(w, k) for w in CAL_W for k in (0, 1)][:PILOT_N]
        rows = [{"pre": ctx.pre_of(w, "ifg"), "u": np.ones(2), "T": 1.0, "max_new": 1, "fence": False,
                 "intent": {"T": 1.3, "u": u_stream(task, w, k, "CAL", "IFG:intent", n=INTENT_MAX), "cap": INTENT_MAX}}
                for w, k in slots]
        ri = decode_rows(model, rows, tok)
        intents = [parse_intent(tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)) for r in ri]
        rows = [{"pre": ctx.pre_of(w, "psl"), "u": u_stream(task, w, k, "CAL", "PSL:A", n=PSL_A_MAX), "T": 0.9,
                 "top_p": 0.95, "max_new": PSL_A_MAX, "fence": False} for w, k in slots]
        rp = decode_rows(model, rows, tok)
        obs = [parse_observations(tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)) for r in rp]
        rows = [{"pre": ctx.pre_of(w, "eap"), "u": u_stream(task, w, k, "CAL", "EAP:A", n=EAP_A_MAX), "T": 1.0,
                 "max_new": EAP_A_MAX, "fence": False} for w, k in slots]
        re_ = decode_rows(model, rows, tok)
        enums = [parse_enum(tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)) for r in re_]
        res[task] = {"intent_present": sum(intent_valid(s) for s in intents) / len(slots),
                     "observations_ge2": sum(len(o) >= 2 for o in obs) / len(slots),
                     "enum_ge1": sum(len(e) >= 1 for e in enums) / len(slots),
                     "examples": {"intent": intents[:3], "observations": obs[:2],
                                  "enum": [[x["name"] for x in e] for e in enums[:3]],
                                  "raw_psl": [tok.decode([t for t in r["token_ids"] if t < nv],
                                                         skip_special_tokens=True)[:400] for r in rp[:2]],
                                  "raw_eap": [tok.decode([t for t in r["token_ids"] if t < nv],
                                                         skip_special_tokens=True)[:400] for r in re_[:2]]},
                     "n_enum_items": [len(e) for e in enums]}
        ctx.release()
        append_jsonl(PRED_DIR / "format_pilot_raw.jsonl", [
            {"task": task, "w": w, "k": k, "kind": kind,
             "text": tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)}
            for kind, rr in (("ifg", ri), ("psl", rp), ("eap", re_)) for (w, k), r in zip(slots, rr)])
    res["min_rate"] = min(min(v["intent_present"], v["observations_ge2"], v["enum_ge1"])
                          for k, v in res.items() if isinstance(v, dict))
    res["pass"] = res["min_rate"] >= PILOT_MIN_RATE
    return res


def stage_calib(model, tok, prompts) -> None:
    dmd = read_json(DMD_FILE) if DMD_FILE.exists() else {}
    for t in TASKS15:
        if t in dmd:
            continue
        t0 = time.time()
        dmd[t] = calibrate_task(model, tok, prompts, t)
        dmd[t]["seconds"] = time.time() - t0
        write_json(DMD_FILE, dmd)
    if not PILOT_FILE.exists():
        pil = format_pilot(model, tok, prompts)
        write_json(PILOT_FILE, pil)
        logger.info(f"format pilot: {pil}")
    if not PROBE_FILE.exists():
        probe = {"free_vram_GB_after_model": free_vram() / 1e9,
                 "rule": "B = min(24, floor(0.8 x (free - 1.2 GB) / ((P + max_steps + 1) x 147,456 B)))",
                 "B_bench_P400": batch_cap("T03", 400, 1024 + INTENT_MAX),
                 "B_path_P260": batch_cap("T2", 260, 1536 + INTENT_MAX)}
        write_json(PROBE_FILE, probe)


# ------------------------------------------------------------------------------------------------ S5 knob queue
def done_ids() -> set[str]:
    return {r["sample_id"] for r in read_jsonl(RAW)}


def stage_rows() -> dict[tuple, dict[str, Any]]:
    return {(r["task"], r["arm"], r["template"], int(r["slot"]), r["stage"], int(r.get("reask", 0))): r
            for r in read_jsonl(STAGES)}


def run_cell_group(model, tok, prompts, task: str, arms: list[str], items: list[tuple[str, int]], block: str,
                   dmd: dict[str, Any], deadline: float) -> int:
    """Run every (arm, w, k) of one task: single-stage arms in one pass; PSL / EAP through their stages."""
    done = done_ids()
    todo = [(a, w, k) for a in arms for w, k in items if f"{task}|{a}|{w}|{k}" not in done]
    if not todo:
        return 0
    ctx = Ctx(model, tok, prompts, task)
    base_int = {}
    if any(a == "BINT" for a, _, _ in todo):
        base_int = {(r["template"], int(r["slot"])): r for r in read_jsonl(BASE_INT) if r["task"] == task}
    n_written = 0
    try:
        single = [spec_row(task, a, w, k, base_intent=base_int.get((w, k))) for a, w, k in todo
                  if a not in ("PSL", "EAP") and (a != "BINT" or (w, k) in base_int)]
        missing_bint = [(a, w, k) for a, w, k in todo if a == "BINT" and (w, k) not in base_int]
        if missing_bint:
            logger.warning(f"{task}: {len(missing_bint)} BINT rows without a base intent (skipped)")
        # group by template to keep shared twin prefills in one batch and free them per template
        by_w = defaultdict(list)
        for sp in single:
            by_w[sp["w"]].append(sp)
        for w in sorted(by_w):
            res = run_specs(model, tok, ctx, by_w[w], block, dmd, deadline)
            rows = [raw_row(tok, sp, r, m, prompts, block) for sp, r, m in res]
            reals = [dict(m["realised"], sample_id=f"{sp['task']}|{sp['arm']}|{sp['w']}|{sp['k']}")
                     for sp, r, m in res if m.get("realised")]
            append_jsonl(RAW, rows)
            if reals:
                append_jsonl(REALISED, reals)
            n_written += len(rows)
            ctx.release()
            if time.time() > deadline:
                return n_written
        for arm in ("EAP", "PSL"):
            sel = [(w, k) for a, w, k in todo if a == arm]
            if sel:
                n_written += run_multistage(model, tok, prompts, ctx, task, arm, sel, block, dmd, deadline)
                ctx.release()
    finally:
        ctx.release()
    return n_written


def run_multistage(model, tok, prompts, ctx: Ctx, task: str, arm: str, sel: list[tuple[str, int]], block: str,
                   dmd: dict[str, Any], deadline: float) -> int:
    nv = vocab_len(tok)
    st = stage_rows()
    kind = ARMS5[arm]["kind"]
    a = ARMS5[arm]
    # ---- stage A (+ one re-ask on parse failure)
    parsed: dict[tuple[str, int], dict[str, Any]] = {}
    for reask in (0, 1):
        need = [(w, k) for w, k in sel if (w, k) not in parsed]
        if reask == 1:
            need = [(w, k) for w, k in need if (task, arm, w, k, "A", 0) in st]
        specs = []
        for w, k in need:
            key = (task, arm, w, k, "A", reask)
            if key in st:
                continue
            specs.append(spec_row(task, arm, w, k, "A", reask=reask))
        res = run_specs(model, tok, ctx, specs, block + ":A", dmd, deadline)
        recs = []
        for sp, r, m in res:
            txt = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
            recs.append({"task": task, "arm": arm, "template": sp["w"], "slot": sp["k"], "stage": "A", "reask": reask,
                         "text": txt, "n_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                         "stream": m.get("stream_tag"), "utc": utc_now()})
        append_jsonl(STAGES, recs)
        st = stage_rows()
        for w, k in sel:
            if (w, k) in parsed:
                continue
            rec = st.get((task, arm, w, k, "A", reask))
            if rec is None:
                continue
            items = parse_observations(rec["text"]) if arm == "PSL" else parse_enum(rec["text"])
            ok = len(items) >= 2 if arm == "PSL" else len(items) >= 1
            if ok:
                parsed[(w, k)] = {"A": rec, "items": items, "reask": reask}
        if time.time() > deadline:
            break
    rows_out = []
    invalid = [(w, k) for w, k in sel if (w, k) not in parsed and (task, arm, w, k, "A", 1) in st]
    for w, k in invalid:
        recA = st.get((task, arm, w, k, "A", 1)) or st.get((task, arm, w, k, "A", 0))
        sp = spec_row(task, arm, w, k, "code")
        rows_out.append(raw_row(tok, sp, None, {}, prompts, block,
                                extra={"stage_texts": {"A": st.get((task, arm, w, k, "A", 0), {}).get("text"),
                                                       "A_reask": recA.get("text") if recA else None},
                                       "parse_ok": False, "engine_path": None}))
    if rows_out:
        append_jsonl(RAW, rows_out)
    p = {w: prompt_for(prompts, task, w, kind) for w in CAL_W}
    # ---- PSL stage B
    if arm == "PSL":
        specs = []
        for (w, k), d in parsed.items():
            if (task, arm, w, k, "B", 0) in st:
                continue
            i, j = pick_pair(len(d["items"]), stable_seed(task, w, k, "PSL_pair"))
            hist = [{"role": "user", "content": p[w]["user_text"]}, {"role": "assistant", "content": d["A"]["text"]},
                    {"role": "user", "content": PSL_B.format(i=i, j=j)}]
            specs.append(spec_row(task, arm, w, k, "B", hist_ids=render_history(tok, hist), pair=[i, j]))
        res = run_specs(model, tok, ctx, specs, block + ":B", dmd, deadline)
        recs = []
        for sp, r, m in res:
            txt = tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
            recs.append({"task": task, "arm": arm, "template": sp["w"], "slot": sp["k"], "stage": "B", "reask": 0,
                         "text": txt, "pair": sp["pair"], "n_tokens": r["n_tokens"],
                         "finish_reason": r["finish_reason"], "utc": utc_now()})
        append_jsonl(STAGES, recs)
        st = stage_rows()
    # ---- final code stage (PSL C / EAP B)
    specs = []
    for (w, k), d in parsed.items():
        if f"{task}|{arm}|{w}|{k}" in done_ids():
            continue
        if arm == "PSL":
            rb = st.get((task, arm, w, k, "B", 0))
            if rb is None:
                continue
            i, j = rb["pair"]
            hist = [{"role": "user", "content": p[w]["user_text"]}, {"role": "assistant", "content": d["A"]["text"]},
                    {"role": "user", "content": PSL_B.format(i=i, j=j)},
                    {"role": "assistant", "content": rb["text"]}, {"role": "user", "content": PSL_C}]
            extra = {"observations": d["items"], "pair": [i, j], "stage_texts": {"A": d["A"]["text"], "B": rb["text"]},
                     "reask": d["reask"], "parse_ok": True}
        else:
            m_ = len(d["items"])
            pi = stable_seed(task, w, k, "EAP_pick") % m_
            name = d["items"][pi]["name"]
            hist = [{"role": "user", "content": p[w]["user_text"]}, {"role": "assistant", "content": d["A"]["text"]},
                    {"role": "user", "content": EAP_B.format(i=pi + 1, name=name)}]
            extra = {"enum_list": d["items"], "pick_index": pi + 1, "picked_name": name,
                     "stage_texts": {"A": d["A"]["text"]}, "reask": d["reask"], "parse_ok": True}
        specs.append(spec_row(task, arm, w, k, "codeH", hist_ids=render_history(tok, hist), extra=extra))
    res = run_specs(model, tok, ctx, specs, block + ":code", dmd, deadline)
    rows = []
    for sp, r, m in res:
        rows.append(raw_row(tok, sp, r, m, prompts, block, extra=sp["extra"]))
    append_jsonl(RAW, rows)
    return len(rows) + len(rows_out)


def queue_items(reduced_nd: bool, dropped: set[str]) -> list[dict[str, Any]]:
    """The full priority queue (plan S5) after the drop order."""
    items = []
    for t in D5:
        items.append({"prio": "P1", "task": t, "arms": list(P1)})
    for t in D5:
        arms = [a for a in P2 if not (a == "IFG_paper" and "IFG_paper" in dropped)]
        items.append({"prio": "P2", "task": t, "arms": arms})
    for t in D5:
        arms = ["T1.3", "TOPK10", "NOVELTY"] + (["SEMSEED"] if t in PATH_TASKS and "SEMSEED_rerun" not in dropped
                                                 else [])
        items.append({"prio": "P3", "task": t, "arms": arms})
    for t in ND10:
        arms = [a for a in P4 if not (a == "DMD_a2" and "ND10_DMD_a2" in dropped)
                and not (a in ("PLAIN", "PNPLAIN_a1") and "ND10_PLAIN_PNPLAIN" in dropped)]
        items.append({"prio": "P4", "task": t, "arms": arms})
    if "P5" not in dropped:
        for t in ND10:
            items.append({"prio": "P5", "task": t, "arms": list(P5)})
    for it in items:
        ks = K_D5 if it["task"] in D5 else (K_ND10_REDUCED if reduced_nd else K_ND10)
        it["items"] = [(w, k) for w in TEMPLATE_IDS for k in ks]
    return items


def wait_commit(tag: str, max_wait_s: float = 4 * 3600) -> None:
    log = ROOT / "commitments.log"
    t0 = time.time()
    while True:
        if log.exists() and any(l.split()[-1] == tag for l in log.read_text().splitlines() if l.strip()):
            return
        if time.time() - t0 > max_wait_s:
            raise RuntimeError(f"{tag} not committed")
        if int(time.time() - t0) % 120 < 15:
            logger.info(f"waiting for {tag} in commitments.log")
        time.sleep(15)


def stage_knobs(model, tok, prompts) -> None:
    wait_commit("commit1")
    dmd = read_json(DMD_FILE)
    deadline = gen_deadline_unix()
    t_start = time.time()
    # stage 10: P1 arms on T03 and T2, W1 k 0-4
    for t in ("T03", "T2"):
        run_cell_group(model, tok, prompts, t, list(P1), [("W1", k) for k in range(5)], "stage10", dmd, deadline)
    # stage 100: P1 + P2 arms on every D5 task, W2 k 0-1
    for t in D5:
        run_cell_group(model, tok, prompts, t, list(P1) + list(P2), [("W2", k) for k in range(2)], "stage100", dmd,
                       deadline)
    # timing extrapolation -> drop order (plan S5 SCALING)
    tb = read_jsonl(TIMING)
    sec_row = defaultdict(list)
    for b in tb:
        if not str(b.get("block", "")).startswith(("stage10", "stage100")):
            continue
        for arm, n in b["arms"].items():
            sec_row[arm].append(b["seconds"] / b["B"])
    # seconds per row and stage (a PSL row runs 3 stages, an EAP row 2; each stage's batch is logged separately)
    per_arm = {a: float(np.mean(v)) for a, v in sec_row.items()}
    stage_mult = {"PSL": 3.0, "EAP": 2.0}
    done = done_ids()

    def remaining_seconds(items) -> float:
        s = 0.0
        default = float(np.median(list(per_arm.values()))) if per_arm else 1.5
        for it in items:
            for a in it["arms"]:
                n = sum(1 for w, k in it["items"] if f"{it['task']}|{a}|{w}|{k}" not in done)
                base = per_arm.get(a, per_arm.get("TWIN", default))
                s += n * base * stage_mult.get(a, 1.0)
        return s
    dropped: set[str] = set()
    reduced = False
    avail = deadline - time.time() - 120
    plan_log = []
    est = remaining_seconds(queue_items(reduced, dropped))
    plan_log.append({"step": "none", "est_seconds": est, "available_seconds": avail})
    for step in ["P5", "ND10_N20", "SEMSEED_rerun", "ND10_DMD_a2", "IFG_paper", "ND10_PLAIN_PNPLAIN"]:
        if est <= avail:
            break
        if step == "ND10_N20":
            reduced = True
        else:
            dropped.add(step)
        est = remaining_seconds(queue_items(reduced, dropped))
        plan_log.append({"step": step, "est_seconds": est, "available_seconds": avail})
    write_json(RESULTS_DIR / "timing_extrapolation.json",
               {"seconds_per_row_by_arm_stage100": per_arm, "multistage_multipliers": stage_mult,
                "drop_steps": plan_log, "dropped": sorted(dropped), "nd10_reduced_to_k0_3": reduced,
                "deadline_unix": deadline, "utc": utc_now(), "stage10_100_seconds": time.time() - t_start})
    if dropped or reduced:
        append_deviation("D-drop", f"drop order applied before the full run: dropped={sorted(dropped)}, "
                         f"ND10 N30->20={reduced} (extrapolated {est:.0f}s vs available {avail:.0f}s)")
    logger.info(f"drop order: {sorted(dropped)} reduced_nd={reduced}; est {est:.0f}s / available {avail:.0f}s")
    not_run = []
    for it in queue_items(reduced, dropped):
        if time.time() > deadline:
            not_run.append({k: it[k] for k in ("prio", "task", "arms")})
            continue
        run_cell_group(model, tok, prompts, it["task"], it["arms"], it["items"], f"{it['prio']}", dmd, deadline)
    write_json(RESULTS_DIR / "queue_result.json", {"not_run": not_run, "finished_utc": utc_now(),
                                                   "seconds": time.time() - t_start})
    (RESULTS_DIR / "gpu_done.flag").write_text(utc_now())


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("gen5")
    stages = sys.argv[1].split(",") if len(sys.argv) > 1 else ["base", "tests", "ec", "calib", "knobs"]
    torch.backends.cuda.matmul.allow_tf32 = False
    prompts = load_prompts()
    if "base" in stages:
        stage_base(prompts)
    if any(s in stages for s in ("tests", "ec", "calib", "knobs")):
        tok, model = load_model(fp8=False, vram_fraction=0.97)
        if "tests" in stages:
            stage_tests(model, tok, prompts)
        if "calib" in stages:
            stage_calib(model, tok, prompts)
            (RESULTS_DIR / "calib_done.flag").write_text(utc_now())
        if "ec" in stages:
            wait_commit("commit0C")      # the engine check observes TWIN rows of two decisive tasks
            stage_ec(model, tok, prompts)
            (RESULTS_DIR / "ec_done.flag").write_text(utc_now())
        if "knobs" in stages:
            stage_knobs(model, tok, prompts)


if __name__ == "__main__":
    main()
