#!/usr/bin/env python3
"""S2 engine checks and S3 behaviour generation on the target (Qwen2.5-7B-Instruct, bf16, HF).

Rows are packed per task into left-padded batches (cfg: <= 64 rows for bench tasks, <= 48 for T1/T2 whose cap is
1,536 new tokens); every row draws from its CRN stream u_stream(task, w, k), shared by every arm. Raw rows stream to
data/samples_raw.jsonl (resumable by sample_id). Causal rows (S8) reuse run_specs() with per-row deltas.

Usage: python src/gen.py engine_check | twin | forced_seed | ban | causal
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (DATA_DIR, ENGINE_TAG, EXTRA_TWIN_SLOTS, FORCED_SLOTS, MAX_NEW_PATH, MAX_NEW_TOKENS, MODEL_ID,
                 MODEL_REVISION, PATH_TASKS, PRECISION, PRED_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, TWIN_SLOTS,
                 append_deviation, append_jsonl, read_json, read_jsonl, setup_logging, stable_seed, utc_now,
                 write_json)
from engine import DeltaEdit, generate_crn, load_model, u_stream
import prompts as PR

RAW = DATA_DIR / "samples_raw.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
BATCH = {"bench": 64, "path": 48}


def max_new_for(task: str) -> int:
    return MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_TOKENS


def fence_for(task: str) -> str:
    return "path" if task in PATH_TASKS else "bench"


def spec_row(p: dict[str, Any], arm: str, k: int, cell: str | None = None, **extra: Any) -> dict[str, Any]:
    """A generation request: prompt record p, CRN slot k (stream keyed by the prompt's task and template)."""
    mode = p.get("mode") or extra.get("mode")
    sid = f"{p['task']}|{cell or arm}|{mode or '-'}|{p['w']}|{k}"
    return {"p": p, "arm": arm, "cell": cell or arm, "k": k, "sample_id": sid, "mode": mode, **extra}


def done_ids(path: Path = RAW) -> set[str]:
    return {r["sample_id"] for r in read_jsonl(path)}


def run_specs(model: Any, tok: Any, specs: list[dict[str, Any]], block: str, out_path: Path = RAW,
              batch_cap: int | None = None, edit_block: int | None = None, write: bool = True,
              skip_done: bool = True) -> list[dict[str, Any]]:
    """Generate every spec (grouped by task, packed into batches). A spec may carry 'pre' ({offset: np[D]}) and/or
    'gen' (np[D]) deltas for the DeltaEdit hook on `edit_block`; rows without them get zero deltas."""
    done = done_ids(out_path) if skip_done else set()
    todo = [s for s in specs if s["sample_id"] not in done]
    out_all: list[dict[str, Any]] = []
    by_task: dict[str, list[dict[str, Any]]] = {}
    for s in todo:
        by_task.setdefault(s["p"]["task"], []).append(s)
    for task, ss in by_task.items():
        cap = batch_cap or BATCH["path" if task in PATH_TASKS else "bench"]
        i = 0
        while i < len(ss):
            part = ss[i:i + cap]
            try:
                rows = _run_batch(model, tok, part, block, edit_block)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                cap = max(1, cap // 2)
                logger.warning(f"OOM at batch {len(part)} -> halving to {cap}")
                append_deviation("D-oom", f"CUDA OOM at batch {len(part)} on {task}; batch cap halved to {cap}")
                continue
            if write:
                append_jsonl(out_path, rows)
            out_all += rows
            i += len(part)
    return out_all


def _run_batch(model: Any, tok: Any, part: list[dict[str, Any]], block: str, edit_block: int | None
               ) -> list[dict[str, Any]]:
    task = part[0]["p"]["task"]
    mx = max_new_for(task)
    prompts = [s["p"]["ids"] for s in part]
    streams = [u_stream(task, s["p"]["w"], s["k"]) for s in part]
    edit = None
    if any(("pre" in s) or ("gen" in s) for s in part):
        D = model.config.hidden_size
        offs = sorted({o for s in part for o in s.get("pre", {})})
        pre = {o: torch.tensor(np.stack([s.get("pre", {}).get(o, np.zeros(D, np.float32)) for s in part]),
                               device=model.device) for o in offs}
        gen = None
        if any("gen" in s for s in part):
            gen = torch.tensor(np.stack([s.get("gen", np.zeros(D, np.float32)) for s in part]), device=model.device)
        edit = DeltaEdit(pre=pre, gen=gen)
    t0 = time.time()
    res = generate_crn(model, tok, prompts, streams, [1.0] * len(part), mx, fence_for(task), edit=edit,
                       edit_block=edit_block)
    dt = time.time() - t0
    rows = []
    for s, r in zip(part, res):
        p = s["p"]
        rows.append({"task": task, "arm": s["arm"], "cell": s["cell"], "mode": s.get("mode"), "template": p["w"],
                     "slot": s["k"], "sample_id": s["sample_id"], "crn_key": f"{task}|{p['w']}|{s['k']}",
                     "u_seed": stable_seed(task, p["w"], s["k"]), "temperature": 1.0, "top_k": None, "top_p": 1.0,
                     "prompt_kind": p["kind"], "prompt_sha256": p["prompt_sha256"], "P": p["P"],
                     "model": f"{MODEL_ID}@{MODEL_REVISION}", "engine": ENGINE_TAG, "precision": PRECISION,
                     "max_new": mx, "stop_rule": f"im_end|fence:{fence_for(task)}", "block_id": block,
                     "batch_B": len(part), "text": r["text"], "token_ids": r["token_ids"],
                     "n_new_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                     "logprob_sum": r["logprob_sum"], "site": s.get("site"), "alpha": s.get("alpha"),
                     "edit_class": s.get("edit_class"), "state_ids": s.get("state_ids"),
                     "delta_norm_ratio": s.get("delta_norm_ratio"), "direction_seed": s.get("direction_seed"),
                     "readback_max_relerr": (max(edit.readback) if (edit is not None and edit.readback) else None),
                     "utc": utc_now()})
    rec = {"block": block, "task": task, "B": len(part), "seconds": round(dt, 2), "steps": res[0]["steps"],
           "sec_per_sample": round(dt / len(part), 3), "n_length": sum(r["finish_reason"] == "length" for r in res),
           "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2), "utc": utc_now()}
    append_jsonl(TIMING, [rec])
    logger.info(f"{block} {task}: B={len(part)} {dt:.1f}s ({rec['sec_per_sample']} s/sample), {rec['steps']} steps, "
                f"cap hits {rec['n_length']}, peak {rec['peak_vram_gb']} GB")
    return rows


# ------------------------------------------------------------------------------------------------ prompt access
def static_prompts(tok: Any) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """(task, kind, w, mode) -> prompt record; built once and stored in data/prompts_static.jsonl."""
    p = DATA_DIR / "prompts_static.jsonl"
    rows = read_jsonl(p)
    if not rows:
        from cfg import write_jsonl
        rows = PR.build_static(tok)
        write_jsonl(p, rows)
    return {(r["task"], r["kind"], r["w"], r.get("mode") or "-"): r for r in rows}


def ban_prompts(tok: Any, defaults: dict[str, str | None]) -> dict[tuple[str, str], dict[str, Any]]:
    from cfg import write_jsonl

    p = DATA_DIR / "prompts_ban.jsonl"
    rows = read_jsonl(p)
    if not rows:
        st = static_prompts(tok)
        rows = []
        for t, D in defaults.items():
            if not D:
                continue
            for w in TEMPLATE_IDS:
                tw = st[(t, "twin", w, "-")]
                b = PR.ban(tok, t, w, D, pad_to=tw["P"])
                if b["P"] != tw["P"]:
                    append_deviation(f"D-banlen-{t}-{w}", f"{t}/{w}: ban of {D} has P={b['P']} vs twin P={tw['P']}; "
                                     "positions are end-relative so the readout and patch sites still align")
                if b.get("n_pad"):
                    append_deviation(f"D-banpad-{t}", f"{t}: ban of this model's default {D} was ' .'-padded to the "
                                     "twin's length (the twin was matched to the prior default's ban)")
                rows.append(b)
        PR.check_tail_identity(rows + [r for r in st.values() if r["task"] in defaults])
        write_jsonl(p, rows)
    return {(r["task"], r["w"]): r for r in rows}


# ------------------------------------------------------------------------------------------------ stages
def stage_engine_check(model: Any, tok: Any) -> dict[str, Any]:
    st = static_prompts(tok)
    out: dict[str, Any] = {}
    # (a) CRN determinism: the same 8 slots twice
    sp = [spec_row(st[("T03", "twin", "W1", "-")], "ENGCHK_A", k) for k in range(8)]
    r1 = run_specs(model, tok, sp, "engchk_a1", write=False, skip_done=False)
    r2 = run_specs(model, tok, sp, "engchk_a2", write=False, skip_done=False)
    out["a_crn_determinism"] = {"n": len(r1), "identical": sum(x["token_ids"] == y["token_ids"] for x, y in zip(r1, r2))}
    # (b) identity hook (delta = 0 at the four prefill positions) vs no hook, 20 slots (two templates x 10)
    sp = [spec_row(st[("T10", "twin", w, "-")], "ENGCHK_B", k) for w in ("W1", "W2") for k in range(10)]
    r0 = run_specs(model, tok, sp, "engchk_b0", write=False, skip_done=False)
    D = model.config.hidden_size
    sp_id = [dict(s, pre={o: np.zeros(D, np.float32) for o in (1, 6, 7, 8)}) for s in sp]
    from cfg import EXTRACTION_LAYER
    rb = run_specs(model, tok, sp_id, "engchk_b1", write=False, skip_done=False, edit_block=EXTRACTION_LAYER)
    out["b_identity_hook"] = {"n": len(r0), "identical": sum(x["token_ids"] == y["token_ids"] for x, y in zip(r0, rb))}
    # (c) batch invariance: 16 slots of T03 twin at batch 1 (rows written as ENGCHK_C1; their batch-64 partners are
    # the production TWIN rows with the same slot) -> label agreement measured after labelling
    sp = [spec_row(st[("T03", "twin", w, "-")], "ENGCHK_C1", k) for w, ks in (("W1", range(10)), ("W2", range(6)))
          for k in ks]
    t0 = time.time()
    run_specs(model, tok, sp, "engchk_c1", batch_cap=1)
    out["c_batch1_seconds"] = round(time.time() - t0, 1)
    out["d_memory"] = {"peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                       "total_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)}
    write_json(RESULTS_DIR / "engine_check.json", out)
    logger.info(f"engine check: {out}")
    return out


def stage_twin(model: Any, tok: Any, staged: bool = True) -> None:
    st = static_prompts(tok)
    specs = [spec_row(st[(t, "twin", w, "-")], "TWIN", k) for t in TASKS for w in TEMPLATE_IDS for k in TWIN_SLOTS]
    if staged:  # 10 -> 100 -> full, with time per sample logged (aii-long-running-tasks)
        run_specs(model, tok, specs[:10], "twin_stage10")
        run_specs(model, tok, specs[:100], "twin_stage100")
    run_specs(model, tok, specs, "twin_full")


def stage_forced_seed(model: Any, tok: Any) -> None:
    st = static_prompts(tok)
    specs = []
    for t in TASKS:
        for c in PR.catalogue(t):
            for w in TEMPLATE_IDS:
                p = st[(t, "forced", w, c["mode"])]
                specs += [spec_row(p, "FORCED", k) for k in FORCED_SLOTS]
    specs += [spec_row(st[("T2", "seed", w, "-")], "SEED", k) for w in TEMPLATE_IDS for k in TWIN_SLOTS]
    run_specs(model, tok, specs, "forced_seed")


def stage_ban(model: Any, tok: Any) -> None:
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    defaults = {t: v["default"] for t, v in c1["tasks"].items()}
    bp = ban_prompts(tok, defaults)
    st = static_prompts(tok)
    specs = []
    for t in TASKS:
        if defaults.get(t):
            specs += [spec_row(bp[(t, w)], "BAN", k) for w in TEMPLATE_IDS for k in TWIN_SLOTS]
        else:  # NO DEFAULT: the ban's 50 samples go to extra twin slots 10-19 (per-sample readout)
            specs += [spec_row(st[(t, "twin", w, "-")], "TWIN", k) for w in TEMPLATE_IDS for k in EXTRA_TWIN_SLOTS]
    run_specs(model, tok, specs, "ban")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="+")
    args = ap.parse_args()
    setup_logging("gen")
    from cfg import set_ram_limit
    set_ram_limit(60)
    tok, model = load_model()
    for s in args.stages:
        t0 = time.time()
        if s == "engine_check":
            stage_engine_check(model, tok)
        elif s == "twin":
            stage_twin(model, tok)
        elif s == "forced_seed":
            stage_forced_seed(model, tok)
        elif s == "ban":
            while not (PRED_DIR / "commit1_defaults.json").exists():
                logger.info("waiting for commit1_defaults.json ...")
                time.sleep(15)
            stage_ban(model, tok)
        else:
            raise ValueError(s)
        logger.info(f"stage {s} done in {time.time() - t0:.0f}s")
        (DATA_DIR / f"flag_{s}.done").write_text(utc_now())


if __name__ == "__main__":
    main()
