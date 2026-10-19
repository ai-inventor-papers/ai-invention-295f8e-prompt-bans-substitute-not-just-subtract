#!/usr/bin/env python3
"""vLLM generation sessions (own process; never load HF here).

  --session s1 : baseline (paraphrases 0-9 x 20, max_tokens 1024) and enumerate (0-9 x 10, max_tokens 1536)
  --session s2 : ban:X_t (0-9 x 10) and, optionally, mention:X_t (E3), after the forecast commit
  --session s3 : succession:2 (0-9 x 10) after the succession forecast commit

Sampling: T=1.0, top_p=1.0, top-k disabled, min_p=0, repetition_penalty=1, per-request seed
stable_hash(task, condition, paraphrase_id). Prompts are passed as token ids from prompts/scaffold.py.
Each arm is staged: paraphrase 0 first (timing logged), then the rest.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (FORECAST_DIR, LOGS_DIR, MODEL_ID, RAW_DIR, RESULTS_DIR, append_jsonl, read_jsonl,  # noqa: E402
                    resolve_model_path, set_ram_limit, setup_logger, stable_hash)
from prompts.scaffold import build_prompt, check_suffix, segments  # noqa: E402
from loguru import logger  # noqa: E402

N_PARA = 10


def make_llm(mp: str):
    from vllm import LLM
    # Session 1 showed torch.compile cannot run here (no C compiler for inductor), so the planned first
    # config (0.92, 16 seqs, compiled) is skipped unless VLLM_TRY_COMPILED=1; eager mode is the logged fallback.
    tries = [dict(gpu_memory_utilization=0.95, max_num_seqs=16, enforce_eager=True),
             dict(gpu_memory_utilization=0.95, max_num_seqs=8, enforce_eager=True)]
    if os.environ.get("VLLM_TRY_COMPILED") == "1":
        tries.insert(0, dict(gpu_memory_utilization=0.92, max_num_seqs=16))
    last = None
    for kw in tries:
        try:
            logger.info(f"starting vLLM with {kw}")
            llm = LLM(model=mp, tokenizer=mp, dtype="bfloat16", max_model_len=2048, seed=1234,
                      enable_prefix_caching=True, max_num_batched_tokens=2048, **kw)
            return llm, kw
        except Exception as e:  # noqa: BLE001 - engine start failures are heterogeneous; logged and retried
            logger.error(f"vLLM start failed with {kw}: {e!r}")
            last = e
    raise RuntimeError(f"vLLM could not start: {last!r}")


def sampling(n: int, max_tokens: int, seed: int):
    from vllm import SamplingParams
    default_top_k = SamplingParams().top_k  # the installed version's "disabled" value (0 or -1)
    sp = SamplingParams(n=n, temperature=1.0, top_p=1.0, top_k=default_top_k, min_p=0.0, repetition_penalty=1.0,
                        max_tokens=max_tokens, seed=seed)
    assert sp.temperature == 1.0 and sp.top_p == 1.0 and sp.top_k in (0, -1) and sp.min_p == 0.0
    assert sp.repetition_penalty == 1.0
    return sp


def committed(event_file: str) -> dict | None:
    for r in read_jsonl(FORECAST_DIR / "commit_log.jsonl"):
        if r.get("file") == event_file:
            return r
    return None


def run_arm(llm, tok, task: str, condition: str, group: str, n: int, max_tokens: int, decoding_note: dict,
            keep_ids: bool = False) -> None:
    out = RAW_DIR / f"vllm_{task}_{condition.replace(':', '-').replace('+', '_')}.jsonl"
    done = {(r["paraphrase_id"], r["sample_id"]) for r in read_jsonl(out)}
    segs = segments(task, group)
    for stage, pids in (("stage", [0]), ("full", list(range(1, N_PARA)))):
        todo = [p for p in pids if any((p, s) not in done for s in range(n))]
        if not todo:
            continue
        prompts, sps = [], []
        for p in todo:
            ids = build_prompt(tok, segs[p], task)
            check_suffix(tok, ids, task)
            prompts.append({"prompt_token_ids": ids})
            sps.append(sampling(n, max_tokens, stable_hash(task, condition, p)))
        if stage == "stage":
            logger.info(f"SamplingParams[{task} {condition} p0] = {sps[0]!r}")
        t0 = time.time()
        outs = llm.generate(prompts, sps, use_tqdm=False)
        dt = time.time() - t0
        rows = []
        for p, o in zip(todo, outs):
            for s, c in enumerate(o.outputs):
                ids = list(c.token_ids)
                row = {"task": task, "condition": condition, "paraphrase_id": p, "sample_id": s, "model": MODEL_ID,
                       "engine": "vllm", "decoding": decoding_note | {"max_tokens": max_tokens},
                       "seed": stable_hash(task, condition, p), "segment": segs[p],
                       "prompt_n_tokens": len(o.prompt_token_ids), "text": c.text, "n_tokens": len(ids),
                       "finish_reason": c.finish_reason, "steering": None}
                if keep_ids and len(ids) > 1024:
                    row["text_1024"] = tok.decode(ids[:1024], skip_special_tokens=True)
                elif keep_ids:
                    row["text_1024"] = c.text
                rows.append(row)
        append_jsonl(out, rows)
        ntok = sum(r["n_tokens"] for r in rows)
        append_jsonl(LOGS_DIR / "timing.jsonl", [{
            "what": f"vllm {task} {condition} {stage}", "n_samples": len(rows), "seconds": round(dt, 2),
            "s_per_sample": round(dt / max(1, len(rows)), 3), "tokens": ntok,
            "extrapolated_full_s": round(dt / max(1, len(rows)) * N_PARA * n, 1) if stage == "stage" else None,
            "utc": datetime.now(timezone.utc).isoformat()}])
        logger.info(f"{task} {condition} {stage}: {len(rows)} samples, {ntok} tokens, {dt:.1f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, choices=["s1", "s2", "s3", "s2hf"])
    ap.add_argument("--with-mention", action="store_true")
    ap.add_argument("--tasks", default="T1,T2")
    args = ap.parse_args()
    setup_logger(f"vllm_{args.session}")
    # no RLIMIT_AS here: the CUDA driver needs large virtual reservations (see gpu/hf_states.py)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from transformers import AutoTokenizer
    mp = resolve_model_path()
    tok = AutoTokenizer.from_pretrained(mp)
    tasks = args.tasks.split(",")
    plan = []  # (task, condition, group, n, max_tokens, keep_ids)
    if args.session == "s1":
        for t in tasks:
            plan.append((t, "baseline", "baseline", 20, 1024, False))
            plan.append((t, "enumerate", "enumerate", 10, 1536, True))
    elif args.session == "s2":
        modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text())
        for t in tasks:
            x = modes[t]["X"]
            ev = f"predict_{t}_ban1.json"
            rec = committed(ev)
            assert rec is not None, f"GUARD: no commit-log entry for {ev}; refusing to generate ban samples"
            assert rec["created_utc"] < datetime.now(timezone.utc).isoformat()
            logger.info(f"guard ok: {ev} committed {rec['created_utc']} sha256={rec['sha256'][:16]}")
            plan.append((t, f"ban:{x}", f"ban:{x}", 10, 1024, False))
            if args.with_mention:
                plan.append((t, f"mention:{x}", f"mention:{x}", 10, 1024, False))
    elif args.session == "s3":
        succ = json.loads((RESULTS_DIR / "succession_plan.json").read_text())
        for t in tasks:
            if t not in succ or succ[t].get("skip"):
                logger.info(f"succession skipped for {t}")
                continue
            ev = f"predict_{t}_succ2.json"
            rec = committed(ev)
            assert rec is not None, f"GUARD: no commit-log entry for {ev}; refusing to generate succession samples"
            x1, x2 = succ[t]["X1"], succ[t]["X2"]
            plan.append((t, "succession:2", f"succession:{x1}+{x2}", 10, 1024, False))
    note = {"temperature": 1.0, "top_p": 1.0, "top_k": "disabled", "min_p": 0.0, "repetition_penalty": 1.0}
    def complete(t, cond, n):
        out = RAW_DIR / f"vllm_{t}_{cond.replace(':', '-').replace('+', '_')}.jsonl"
        return len({(r["paraphrase_id"], r["sample_id"]) for r in read_jsonl(out)}) >= N_PARA * n
    plan = [x for x in plan if not complete(x[0], x[1], x[3])]  # resume: skip arms already on disk
    if not plan:
        logger.info("nothing to do")
        return
    t0 = time.time()
    llm, kw = make_llm(mp)
    logger.info(f"vLLM up in {time.time() - t0:.1f}s with {kw}")
    import vllm
    (LOGS_DIR / f"vllm_engine_{args.session}.json").write_text(json.dumps({"vllm": vllm.__version__, **kw}))
    for (t, cond, group, n, mt, keep) in plan:
        run_arm(llm, tok, t, cond, group, n, mt, note, keep_ids=keep)
    logger.info(f"session {args.session} done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
