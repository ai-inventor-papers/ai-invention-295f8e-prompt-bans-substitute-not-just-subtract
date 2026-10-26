#!/usr/bin/env python3
"""vLLM block (GPU). Session 1: C1 fresh ban pool + E5 same-seed common-random-numbers (CRN) rows + Gumbel-max
sensitivity + determinism rerun. Session 2 (thought anchors) lives in anchors_stage.py and reuses make_engine().

The CRN sampler is a vLLM V1 per-request logits processor: at step t of row (seed, T) it takes the top-10 logits
sorted by (-logit, token_id), applies softmax(logit / T) over those 10, and picks the first index whose CDF
reaches U[seed][t] with U[seed] = numpy default_rng(seed).random(1024), shared across T, tasks and conditions
(inverse-CDF in descending-probability order). Every other logit is set to -inf and the request is decoded
greedily, so the processor alone decides each token. The Gumbel-max sensitivity uses the same top-10 and
token = argmax(logit / T + G[seed][t][slot]) with G from default_rng(10**6 + seed) (Ravfogel et al. 2025's
structural-equation coupling, keyed by rank slot).
"""

from __future__ import annotations

import os

os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")  # in-process engine: the processor shares globals
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import time
from typing import Any

import numpy as np
import torch
from loguru import logger
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor

from core import (CRN_SEEDS, CRN_TEMPS, GUMBEL_SEED_OFFSET, MAIN_DECODING, MODEL_GEN, MODEL_HF, RESULTS,
                  SEED_FRESH, TASKS, TEMPLATE_IDS, Timer, add_deviation, append_jsonl, read_json, read_jsonl,
                  write_json)

RAW = RESULTS / "raw"
RAW.mkdir(parents=True, exist_ok=True)
STOP_IDS = [151645, 151643]  # <|im_end|>, <|endoftext|>
STEP0: dict[str, dict[str, Any]] = {}  # crn_row -> step-0 sorted top-10 (ids, logits)
CRN_MAX_STEPS = 1024


class CRNLogitsProcessor(AdapterLogitsProcessor):
    """Per-request CRN / Gumbel-max sampler; inactive for requests without extra_args['crn_seed']."""

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(self, params):  # noqa: ANN001 - vLLM SamplingParams
        ea = params.extra_args or {}
        if "crn_seed" not in ea:
            return None
        seed, T, mode, rid = int(ea["crn_seed"]), float(ea["crn_T"]), str(ea.get("crn_mode", "icdf")), ea["crn_row"]
        if mode == "icdf":
            U = np.random.default_rng(seed).random(CRN_MAX_STEPS)
            G = None
        else:
            U = None
            G = np.random.default_rng(GUMBEL_SEED_OFFSET + seed).gumbel(size=(CRN_MAX_STEPS, 10))

        def fn(output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
            t = min(len(output_ids), CRN_MAX_STEPS - 1)
            vals, idx = torch.topk(logits, 12)
            v, ix = vals.tolist(), idx.tolist()
            order = sorted(range(len(v)), key=lambda j: (-v[j], ix[j]))[:10]
            lv = np.array([v[j] for j in order], dtype=np.float64)
            li = [ix[j] for j in order]
            if len(output_ids) == 0:
                STEP0[rid] = {"ids": li, "logits": lv.tolist()}
            if mode == "icdf":
                z = lv / T
                z = z - z.max()
                p = np.exp(z)
                p /= p.sum()
                j = int(np.searchsorted(np.cumsum(p), U[t], side="left"))
                j = min(j, 9)
            else:
                j = int(np.argmax(lv / T + G[t]))
            out = torch.full_like(logits, float("-inf"))
            out[li[j]] = 0.0
            return out

        return fn


def make_engine(max_model_len: int, max_num_seqs: int, gpu_mem: float = 0.90, max_batched: int = 4096,
                enforce_eager: bool = False):
    from vllm import LLM

    t0 = time.time()
    llm = LLM(model=MODEL_GEN, tokenizer=MODEL_HF, dtype="auto", max_model_len=max_model_len,
              max_num_seqs=max_num_seqs, gpu_memory_utilization=gpu_mem, max_num_batched_tokens=max_batched,
              enable_prefix_caching=True, seed=0, enforce_eager=enforce_eager,
              logits_processors=[CRNLogitsProcessor])
    logger.info(f"vLLM engine up in {time.time() - t0:.0f}s (max_model_len={max_model_len}, seqs={max_num_seqs}, "
                f"mem={gpu_mem}, eager={enforce_eager})")
    return llm


def generate(llm, prompts_ids: list[list[int]], params: list[Any], desc: str) -> list[dict[str, Any]]:
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    outs = llm.generate([TokensPrompt(prompt_token_ids=p) for p in prompts_ids], params, use_tqdm=False)
    dt = time.time() - t0
    res = []
    ntok = 0
    for o in outs:
        c = o.outputs[0]
        ids = list(c.token_ids)
        ntok += len(ids)
        res.append({"gen_token_ids": ids, "text": c.text, "finish_reason": c.finish_reason, "n_gen_tokens": len(ids)})
    logger.info(f"{desc}: {len(outs)} seqs, {ntok} tokens in {dt:.1f}s -> {ntok / max(dt, 1e-6):.0f} tok/s, "
                f"{dt / max(len(outs), 1):.2f} s/seq")
    return res


def _prompt(P: dict[str, Any], key: str, thinking: bool = False) -> list[int]:
    return P["prompts"][key]["think" if thinking else "nothink"]["ids"]


def stage_c1(llm, P: dict[str, Any], n_per_template: int) -> None:
    """C1 fresh protocol-v2 ban pool: W1-W5 ban x n per task, T=1.0, top_p=1.0, max 1024, thinking off."""
    from vllm import SamplingParams

    out_path = RAW / "c1_fresh_pool.jsonl"
    done = {(r["task"], r["template"], r["sample_id"]) for r in read_jsonl(out_path)}
    jobs = []
    i = 0
    for t in TASKS:
        for w in TEMPLATE_IDS:
            for s in range(n_per_template):
                seed = SEED_FRESH + i
                i += 1
                if (t, w, s) not in done:
                    jobs.append({"task": t, "template": w, "condition": "ban", "sample_id": s, "seed": seed,
                                 "prompt_key": f"{t}|ban|{w}"})
    if not jobs:
        logger.info("C1: all runs present")
        return
    stages = [jobs[:10], jobs[10:100], jobs[100:]]
    for k, part in enumerate(stages):
        if not part:
            continue
        with Timer(f"C1_part{k}", gpu=True, n=len(part)):
            params = [SamplingParams(temperature=MAIN_DECODING["temperature"], top_p=1.0, max_tokens=1024,
                                     seed=j["seed"], stop_token_ids=STOP_IDS) for j in part]
            res = generate(llm, [_prompt(P, j["prompt_key"]) for j in part], params, f"C1 part {k}")
            rows = [{**j, "arm": "C1_fresh_pool", "model": MODEL_GEN, "thinking": False,
                     "decoding": "T1.0_topp1.0_topk-off_max1024_thinkoff",
                     "prompt_len": len(_prompt(P, j["prompt_key"])), **r} for j, r in zip(part, res)]
            append_jsonl(out_path, rows)


def crn_rows(P: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for t in TASKS:
        for cond, key in (("baseline", f"{t}|baseline|P0"), ("ban", f"{t}|ban|W1")):
            for s in CRN_SEEDS:
                for T in CRN_TEMPS:
                    rows.append({"task": t, "condition": cond, "template": "P0" if cond == "baseline" else "W1",
                                 "seed": s, "T": T, "coupling": "icdf_top10", "prompt_key": key,
                                 "crn_row": f"icdf|{t}|{cond}|{s}|{T}"})
    return rows


def run_crn(llm, P: dict[str, Any], jobs: list[dict[str, Any]], out_path, desc: str, mode: str = "icdf",
            tag: str = "") -> list[dict[str, Any]]:
    from vllm import SamplingParams

    params = [SamplingParams(temperature=0.0, max_tokens=CRN_MAX_STEPS, stop_token_ids=STOP_IDS,
                             extra_args={"crn_seed": j["seed"], "crn_T": j["T"], "crn_mode": mode,
                                         "crn_row": j["crn_row"] + tag}) for j in jobs]
    t0 = time.time()
    res = generate(llm, [_prompt(P, j["prompt_key"]) for j in jobs], params, desc)
    rows = [{**j, "arm": "E5_crn" if mode == "icdf" else "E5_gumbel", "model": MODEL_GEN, "thinking": False,
             "decoding": f"{mode}_top10_T{j['T']}_max1024_thinkoff", "wall_s_batch": round(time.time() - t0, 2),
             "step0": STEP0.get(j["crn_row"] + tag), "prompt_len": len(_prompt(P, j["prompt_key"])), **r}
            for j, r in zip(jobs, res)]
    append_jsonl(out_path, rows)
    return rows


def stage_e5(llm, P: dict[str, Any], n_seeds: int) -> None:
    out_path = RAW / "e5_crn.jsonl"
    have = {r["crn_row"] for r in read_jsonl(out_path)}
    all_rows = [r for r in crn_rows(P) if r["seed"] < n_seeds]
    todo = [r for r in all_rows if r["crn_row"] not in have]
    if todo:
        # 10-row stage: 1 seed x 4 T x 2 conditions (+2 repeats of identical rows) -> s/token extrapolation
        first = [r for r in todo if r["seed"] == todo[0]["seed"] and r["task"] == todo[0]["task"]][:8]
        with Timer("E5_stage10", gpu=True, n=len(first) + 2):
            got = run_crn(llm, P, first, out_path, "E5 stage-10")
            rep = run_crn(llm, P, first[:2], RAW / "e5_crn_repeat_stage10.jsonl", "E5 stage-10 repeats",
                          tag="|rep10")
            same = [a["gen_token_ids"] == b["gen_token_ids"] for a, b in zip(got[:2], rep)]
            logger.info(f"stage-10 identical-row repeats byte-identical: {same}")
        rest = [r for r in todo if r["crn_row"] not in {x["crn_row"] for x in first}]
        tok = sum(r["n_gen_tokens"] for r in got)
        logger.info(f"E5 extrapolation: {tok / len(got):.0f} tokens/row; {len(rest)} rows remain")
        with Timer("E5_main", gpu=True, n=len(rest)):
            for i in range(0, len(rest), 200):
                run_crn(llm, P, rest[i:i + 200], out_path, f"E5 main {i + len(rest[i:i + 200])}/{len(rest)}")
    # determinism rerun: 2 seeds x 4 T of the W1 ban, task t1, in one batch of 8
    det_path = RAW / "e5_determinism.jsonl"
    if not det_path.exists():
        jobs = [r for r in all_rows if r["task"] == "t1" and r["condition"] == "ban" and r["seed"] in (0, 1)]
        with Timer("E5_determinism", gpu=True, n=len(jobs)):
            run_crn(llm, P, jobs, det_path, "E5 determinism rerun", tag="|rerun")
    write_json(RAW / "e5_step0.json", STEP0)


def stage_gumbel(llm, P: dict[str, Any], n_seeds: int = 20) -> None:
    out_path = RAW / "e5_gumbel.jsonl"
    have = {r["crn_row"] for r in read_jsonl(out_path)}
    jobs = []
    for t in TASKS:
        for s in range(n_seeds):
            for T in CRN_TEMPS:
                jobs.append({"task": t, "condition": "ban", "template": "W1", "seed": s, "T": T,
                             "coupling": "gumbel_top10", "prompt_key": f"{t}|ban|W1",
                             "crn_row": f"gumbel|{t}|ban|{s}|{T}"})
    jobs = [j for j in jobs if j["crn_row"] not in have]
    if jobs:
        with Timer("E5_gumbel", gpu=True, n=len(jobs)):
            run_crn(llm, P, jobs, out_path, "E5 Gumbel-max sensitivity", mode="gumbel")
    write_json(RAW / "e5_step0.json", {**read_json(RAW / "e5_step0.json", {}), **STEP0})


def session1(n_per_template: int = 40, n_seeds: int = 50, gumbel_seeds: int = 20, smoke: bool = False) -> None:
    from prompts import build_prompts

    P = build_prompts()
    add_deviation("D01", "All vLLM generations use Qwen/Qwen3-8B-FP8 (official block-FP8 checkpoint); every "
                  "state, attention and CE readout uses bf16 Qwen/Qwen3-8B.",
                  "The pod has a 16 GB RTX 2000 Ada (not the planned 20 GB A4500): bf16 Qwen3-8B (16.4 GB of "
                  "weights) does not fit in vLLM.",
                  "Generated texts come from a quantised twin of the analysed model; FP8 can shift sampling "
                  "probabilities slightly, so behavioural shares are not bit-comparable with iteration 1.")
    add_deviation("D05", "The CRN sampler runs inside vLLM as a per-request logits processor (greedy decoding of "
                  "a processor-chosen token) instead of a hand-written HF DynamicCache loop.",
                  "An HF decode loop over 800 rows does not fit the time budget on this GPU; the processor keeps "
                  "the exact coupling (shared U[seed][t], inverse CDF over the (-logit, id)-sorted top-10).",
                  "vLLM batches are not layout-controlled, so run-to-run identity is measured (determinism "
                  "rerun + step-0 logits of identical histories) rather than guaranteed.")
    llm = make_engine(max_model_len=2048, max_num_seqs=48 if not smoke else 8, gpu_mem=0.90, enforce_eager=True)
    if smoke:
        from vllm import SamplingParams

        key = "t1|ban|W1"
        res = generate(llm, [_prompt(P, key)] * 2,
                       [SamplingParams(temperature=1.0, max_tokens=64, seed=1, stop_token_ids=STOP_IDS)] * 2,
                       "smoke native")
        logger.info(f"smoke native: {res[0]['text'][:200]!r}")
        jobs = [{"task": "t1", "condition": "ban", "template": "W1", "seed": 0, "T": T, "coupling": "icdf_top10",
                 "prompt_key": key, "crn_row": f"smoke|{T}"} for T in CRN_TEMPS]
        rows = run_crn(llm, P, jobs, RAW / "smoke_crn.jsonl", "smoke CRN")
        for r in rows:
            logger.info(f"smoke CRN T={r['T']}: {r['n_gen_tokens']} tok {r['text'][:120]!r}")
        return
    stage_c1(llm, P, n_per_template)
    stage_e5(llm, P, n_seeds)
    if gumbel_seeds > 0:
        stage_gumbel(llm, P, gumbel_seeds)
    logger.info("session 1 complete")
