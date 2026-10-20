#!/usr/bin/env python3
"""vLLM session 2 (GPU): thought anchors on thinking-on W1 ban traces.

part 'traces'   (C2): base traces, Qwen3 thinking decoding (T 0.6 / top-p 0.95 / top-k 20), 8,192-token thinking cap.
part 'resample' (C3): from b_0 (after '<think>\\n') and after sentences 1..8 of each chosen trace, 6 continuations each,
                      generated in chunks of 384 tokens (at most 4) and stopped once the early-label detector decides.
part 'complete' (C4): validation completions of randomly chosen continuations, run to the end under the cap.
"""

from __future__ import annotations

import os

os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import random
from typing import Any

from loguru import logger

from core import (MODEL_GEN, RESULTS, SEED_CONT, SEED_TRACE, TASKS, THINK_DECODING, Timer, add_deviation,
                  append_jsonl, read_jsonl, write_json)

RAW = RESULTS / "raw"
THINK_OPEN, THINK_CLOSE = 151667, 151668
THINK_CAP = 8192
N_POINTS = 9          # b_0 .. b_8
N_CONT = 6
CHUNK = 384
MAX_CHUNKS = 4


def _sp(seed: int, max_tokens: int):
    from vllm import SamplingParams

    from vllm_stage import STOP_IDS

    return SamplingParams(temperature=THINK_DECODING["temperature"], top_p=THINK_DECODING["top_p"],
                          top_k=THINK_DECODING["top_k"], max_tokens=max_tokens, seed=seed, stop_token_ids=STOP_IDS)


def trace_record(task: str, trace_id: int, seed: int, prompt_len: int, r: dict[str, Any]) -> dict[str, Any]:
    g = r["gen_token_ids"]
    close = g.index(THINK_CLOSE) if THINK_CLOSE in g else None
    after = r["text"].split("</think>", 1)[1] if "</think>" in r["text"] else ""
    complete = close is not None and close < THINK_CAP and "```python" in after
    return {"task": task, "trace_id": trace_id, "seed": seed, "condition": "ban", "template": "W1",
            "arm": "C2_base_trace", "model": MODEL_GEN, "thinking": True,
            "decoding": "T0.6_topp0.95_topk20_max9600_thinkon", "prompt_len": prompt_len,
            "think_close_idx": close, "complete": complete, **r}


def stage_traces(llm, P: dict[str, Any], n_per_task: int) -> None:
    from vllm_stage import generate

    out = RAW / "c2_base_traces.jsonl"
    have = {r["trace_id"] for r in read_jsonl(out)}
    jobs = []
    for i in range(n_per_task):
        for ti, t in enumerate(TASKS):
            tid = ti * 100 + i  # t1 traces 0.., t2 traces 100..
            if tid not in have:
                jobs.append({"task": t, "trace_id": tid, "seed": SEED_TRACE + tid})
    stages = [jobs[:4], jobs[4:]]
    for k, part in enumerate(stages):
        if not part:
            continue
        with Timer(f"C2_traces_part{k}", gpu=True, n=len(part)):
            ids = [P["prompts"][f"{j['task']}|ban|W1"]["think"]["ids"] for j in part]
            res = generate(llm, ids, [_sp(j["seed"], 9600) for j in part], f"C2 traces part {k}")
            rows = [trace_record(j["task"], j["trace_id"], j["seed"], len(i), r) for j, i, r in zip(part, ids, res)]
            append_jsonl(out, rows)
            for r in rows:
                logger.info(f"C2 trace {r['trace_id']} ({r['task']}): {r['n_gen_tokens']} tokens, </think> at "
                            f"{r['think_close_idx']}, complete={r['complete']}")


# ---------------------------------------------------------------- resample points
def boundaries(tok, gen: list[int], n_sent: int = 8) -> dict[str, Any]:
    """b_0 = first token after '<think>' and its newline; b_k = first token index after sentence k (k=1..8),
    found by incremental decoding of the generated ids. Returns indices into gen and the sentences."""
    from early_label import sentences

    if not gen or gen[0] != THINK_OPEN:
        raise ValueError("trace does not start with <think>")
    b0 = 1
    while b0 < len(gen) and tok.decode(gen[1:b0 + 1]).strip() == "":
        b0 += 1
    end = gen.index(THINK_CLOSE) if THINK_CLOSE in gen else len(gen)
    # decode a window large enough for the first n_sent sentences
    win = min(end, b0 + 1200)
    text = tok.decode(gen[b0:win])
    sents = sentences(text)[:n_sent]
    pts = [b0]
    cursor = 0
    checks = []
    j = b0
    for s in sents:
        pos = text.find(s, cursor)
        if pos < 0:
            break
        pos_end = pos + len(s)
        cursor = pos_end
        while j < win and len(tok.decode(gen[b0:j])) < pos_end:
            j += 1
        dec = tok.decode(gen[:j])
        checks.append(dec.rstrip().endswith(s.rstrip()))
        pts.append(j)
    return {"points": pts, "sentences": sents, "boundary_check": checks, "think_end": end}


def stage_resample(llm, P: dict[str, Any], n_trace: int) -> None:
    from transformers import AutoTokenizer

    from core import MODEL_HF
    from early_label import early_label
    from vllm_stage import generate

    tok = AutoTokenizer.from_pretrained(MODEL_HF)
    traces = read_jsonl(RAW / "c2_base_traces.jsonl")
    out = RAW / "c3_continuations.jsonl"
    have = {r["continuation_id"] for r in read_jsonl(out)}
    chosen = []
    for t in TASKS:
        tt = sorted([r for r in traces if r["task"] == t], key=lambda r: r["trace_id"])
        comp = [r for r in tt if r["complete"]]
        pick = (comp + [r for r in tt if not r["complete"]])[:n_trace]
        chosen.extend(pick)
    meta = {}
    jobs = []
    for tr in chosen:
        b = boundaries(tok, tr["gen_token_ids"])
        meta[tr["trace_id"]] = {"task": tr["task"], **{k: v for k, v in b.items()}}
        p_ids = P["prompts"][f"{tr['task']}|ban|W1"]["think"]["ids"]
        for k, bk in enumerate(b["points"]):
            for jj in range(N_CONT):
                cid = f"{tr['trace_id']}|{k}|{jj}"
                if cid in have:
                    continue
                jobs.append({"task": tr["task"], "trace_id": tr["trace_id"], "boundary_k": k, "b_k": bk,
                             "continuation_id": cid, "seed": SEED_CONT + tr["trace_id"] * 1000 + k * 10 + jj,
                             "prefix": p_ids + tr["gen_token_ids"][:bk], "cont_ids": [], "text": ""})
    write_json(RESULTS / "thought_anchor_boundaries.json", meta)
    logger.info(f"C3: {len(chosen)} traces, {len(jobs)} continuations to generate")
    if not jobs:
        return
    # staged: one resample point (6 continuations) first, then everything
    first = jobs[:N_CONT]
    rest = jobs[N_CONT:]
    for name, part in (("C3_stage6", first), ("C3_main", rest)):
        if not part:
            continue
        with Timer(name, gpu=True, n=len(part)):
            active = list(part)
            for ch in range(MAX_CHUNKS):
                if not active:
                    break
                res = generate(llm, [j["prefix"] + j["cont_ids"] for j in active],
                               [_sp(j["seed"] + 100000 * ch, CHUNK) for j in active], f"{name} chunk {ch}")
                nxt = []
                for j, r in zip(active, res):
                    j["cont_ids"] = j["cont_ids"] + r["gen_token_ids"]
                    j["text"] = tok.decode(j["cont_ids"])
                    j["finish_reason"] = r["finish_reason"]
                    j["n_chunks"] = ch + 1
                    el = early_label(j["task"], j["text"])
                    j["early"] = el
                    done = el["label"] != "undecided" or r["finish_reason"] == "stop"
                    if not done and ch < MAX_CHUNKS - 1:
                        nxt.append(j)
                active = nxt
            rows = []
            for j in part:
                el = j.get("early", {})
                rows.append({k2: v for k2, v in j.items() if k2 not in ("prefix", "early")} |
                            {"arm": "C3_continuation", "model": MODEL_GEN, "thinking": True, "condition": "ban",
                             "template": "W1", "decoding": "T0.6_topp0.95_topk20_chunks384x4_thinkon",
                             "early_label": el.get("label"), "early_source": el.get("source"),
                             "early_sentence": el.get("sentence"), "reached_code": bool(el.get("reached_code")),
                             "n_gen_tokens": len(j["cont_ids"]), "gen_token_ids": j["cont_ids"]})
            append_jsonl(out, rows)


def stage_complete(llm, P: dict[str, Any], per_trace: int) -> None:
    """C4: validation completions -- per_trace random continuations per resampled trace, run to the end."""
    from vllm_stage import generate

    conts = read_jsonl(RAW / "c3_continuations.jsonl")
    out = RAW / "c4_completions.jsonl"
    have = {r["continuation_id"] for r in read_jsonl(out)}
    traces = {r["trace_id"]: r for r in read_jsonl(RAW / "c2_base_traces.jsonl")}
    rng = random.Random(4)
    jobs = []
    for tid in sorted({c["trace_id"] for c in conts}):
        cs = [c for c in conts if c["trace_id"] == tid]
        for c in rng.sample(cs, min(per_trace, len(cs))):
            if c["continuation_id"] in have:
                continue
            tr = traces[tid]
            prefix = P["prompts"][f"{tr['task']}|ban|W1"]["think"]["ids"] + tr["gen_token_ids"][:c["b_k"]]
            budget = max(256, 9600 - c["b_k"] - len(c["gen_token_ids"]))
            jobs.append((c, prefix + c["gen_token_ids"], budget))
    if not jobs:
        return
    with Timer("C4_completions", gpu=True, n=len(jobs)):
        res = generate(llm, [j[1] for j in jobs], [_sp(j[0]["seed"] + 500000, j[2]) for j in jobs], "C4 completions")
        rows = []
        for (c, _, _), r in zip(jobs, res):
            full_ids = c["gen_token_ids"] + r["gen_token_ids"]
            rows.append({"task": c["task"], "trace_id": c["trace_id"], "boundary_k": c["boundary_k"],
                         "b_k": c["b_k"], "continuation_id": c["continuation_id"], "seed": c["seed"] + 500000,
                         "arm": "C4_completion", "model": MODEL_GEN, "thinking": True, "condition": "ban",
                         "template": "W1", "decoding": "T0.6_topp0.95_topk20_to_end_thinkon",
                         "early_label_at_chunk": c["early_label"], "text": c["text"] + r["text"],
                         "gen_token_ids": full_ids, "n_gen_tokens": len(full_ids), "finish_reason": r["finish_reason"]})
        append_jsonl(out, rows)


def session2(part: str = "traces", n: int | None = None, smoke: bool = False) -> None:
    from prompts import build_prompts
    from vllm_stage import make_engine

    P = build_prompts()
    add_deviation("D06", "Thinking-on arms decode with Qwen3's recommended T=0.6 / top-p 0.95 / top-k 20.",
                  "Protocol T=1.0 targets thinking-off sampling; the recommended settings raise completion within the "
                  "cap.", "Not directly comparable with exp6's T=1.0 thinking cells.")
    if part == "traces":
        llm = make_engine(max_model_len=10240, max_num_seqs=4, gpu_mem=0.92, enforce_eager=True)
        stage_traces(llm, P, n or 5)
    elif part == "resample":
        llm = make_engine(max_model_len=4096, max_num_seqs=32, gpu_mem=0.92, enforce_eager=True)
        stage_resample(llm, P, n or 3)
    elif part == "complete":
        llm = make_engine(max_model_len=10240, max_num_seqs=4, gpu_mem=0.92, enforce_eager=True)
        stage_complete(llm, P, n or 1)
    else:
        raise SystemExit(f"unknown part {part}")
    logger.info(f"session 2 part {part} complete")
