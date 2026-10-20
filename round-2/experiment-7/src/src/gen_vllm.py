#!/usr/bin/env python3
"""Step 1 (GPU, vLLM, own process): forced programs F_j (10 paraphrases) in adaptive rounds + free-form answers.

Round 1: 4 samples x 10 paraphrases x 11 algorithms. Labelled between rounds with the canonical labeller.
Round 2: algorithms with < 30 labelled get up to 8 more per paraphrase (cap 120 plain attempts).
Round 3: algorithms still < 30 (or 0 labelled in their first 40) get the descriptive family (cap 120 attempts).
Free-form: 20 samples per catalogue X (T=1.0, max_tokens=32). Every row stores its seed and decoding.
The process exits at the end, releasing the GPU before the HF scorer loads.
"""

from __future__ import annotations

import argparse
import collections
import math
import time
from typing import Any

from loguru import logger

from config import (DATA, MODEL_ID, MODES, N_FORCED_TARGET, PROMPTS, TASKS, append_jsonl, model_path, read_json,
                    read_jsonl, seed_of, setup_logging, utc_now, write_json)

DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"
DECODING_FREE = "T1.0_topp1.0_topk-off_max32_thinkoff"
RAW = DATA / "forced_raw.jsonl"
LAB = DATA / "forced_labelled.jsonl"
FREE_RAW = DATA / "freeform_raw.jsonl"


class Generator:
    def __init__(self, max_num_seqs: int) -> None:
        from transformers import AutoTokenizer
        from vllm import LLM

        mp = model_path()
        self.tok = AutoTokenizer.from_pretrained(mp)
        t0 = time.time()
        self.llm = LLM(model=mp, tokenizer=mp, dtype="bfloat16", gpu_memory_utilization=0.90, max_model_len=2048,
                       max_num_seqs=max_num_seqs, enable_prefix_caching=True, seed=1234, enforce_eager=True,
                       generation_config="vllm")
        logger.info(f"vLLM loaded in {time.time() - t0:.0f}s")

    def run(self, reqs: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
        from vllm import SamplingParams
        from vllm.inputs import TokensPrompt

        prompts, params = [], []
        for r in reqs:
            prompts.append(TokensPrompt(prompt_token_ids=self.tok(r["chat"], add_special_tokens=False).input_ids))
            params.append(SamplingParams(n=1, temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, max_tokens=max_tokens,
                                         seed=r["seed"], repetition_penalty=1.0, presence_penalty=0.0,
                                         frequency_penalty=0.0))
        logger.debug(f"SamplingParams[0]={params[0]!r}")
        t0 = time.time()
        outs = self.llm.generate(prompts, params, use_tqdm=False)
        dt = time.time() - t0
        rows = []
        ntok = 0
        for r, o in zip(reqs, outs):
            c = o.outputs[0]
            ntok += len(c.token_ids)
            row = {k: v for k, v in r.items() if k != "chat"}
            row.update({"text": c.text, "n_output_tokens": len(c.token_ids), "finish_reason": c.finish_reason,
                        "n_prompt_tokens": len(o.prompt_token_ids), "model": MODEL_ID, "gen_utc": utc_now()})
            rows.append(row)
        logger.info(f"generated {len(rows)} in {dt:.0f}s ({dt / max(1, len(rows)):.2f} s/gen, {ntok / dt:.0f} tok/s)")
        return rows


def forced_reqs(conds: dict[str, Any], task: str, j: str, family: str, start: int, per_para: int) -> list[dict]:
    reqs = []
    for k in range(10):
        c = conds[f"{task}|forced|{j}|{family}|k{k}"]
        for i in range(start, start + per_para):
            reqs.append({"task": task, "condition": f"forced:{j}", "j": j, "family": family, "template": f"k{k}",
                         "paraphrase_id": k, "sample_id": i, "decoding": DECODING,
                         "seed": seed_of(f"{task}|forced:{j}|{family}|{k}|{i}|v2"), "chat": c["chat"]})
    return reqs


def label_and_store(rows: list[dict[str, Any]], rnd: int) -> list[dict[str, Any]]:
    from labelling import label_texts

    for r in rows:
        r["round"] = rnd
    append_jsonl(RAW, rows)
    lab = label_texts(rows)
    keep = ("task", "condition", "j", "family", "template", "paraphrase_id", "sample_id", "seed", "model", "decoding",
            "label", "labeller_source", "passed", "code_sha256", "code", "runtime_label", "ast_label", "judge_label",
            "n_output_tokens", "finish_reason", "round", "text", "extract_method", "test_error")
    out = [{k: r.get(k) for k in keep} for r in lab]
    append_jsonl(LAB, out)
    return out


def tally(lab: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, int]]:
    t: dict[tuple[str, str, str], dict[str, int]] = collections.defaultdict(lambda: {"attempts": 0, "labelled": 0})
    for r in lab:
        key = (r["task"], r["j"], r["family"])
        t[key]["attempts"] += 1
        t[key]["labelled"] += int(r["label"] == r["j"])
    return t


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-num-seqs", type=int, default=48)
    ap.add_argument("--smoke", action="store_true", help="10 generations only (format check)")
    args = ap.parse_args()
    setup_logging("gen_vllm")
    conds = read_json(PROMPTS / "prompts_v2.json")["conditions"]
    free_prompts = read_json(PROMPTS / "prompts_v2.json")["free_prompts"]
    g = Generator(args.max_num_seqs)
    timings: dict[str, Any] = {}
    if args.smoke:
        reqs = forced_reqs(conds, "t1", "bfs", "plain", 900, 1)
        rows = g.run(reqs, 1024)
        for r in rows:
            logger.info(f"smoke {r['finish_reason']} {r['n_output_tokens']} tok: {r['text'][:160]!r}")
            assert "<think>" not in r["text"], "thinking text leaked"
        return
    done = read_jsonl(LAB)
    if not done:
        # ---- round 1 + free-form in one engine call
        reqs = [q for t in TASKS for j in MODES[t] for q in forced_reqs(conds, t, j, "plain", 0, 4)]
        t0 = time.time()
        rows = g.run(reqs, 1024)
        timings["round1_s"] = time.time() - t0
        free_reqs = []
        from vllm import SamplingParams  # noqa: F401  (engine already imported)

        for t in TASKS:
            for x in MODES[t]:
                chat = g.tok.apply_chat_template([{"role": "user", "content": free_prompts[t][x]}], tokenize=False,
                                                 add_generation_prompt=True, enable_thinking=False)
                for i in range(20):
                    free_reqs.append({"task": t, "condition": f"free:{x}", "X": x, "sample_id": i,
                                      "template": "free_v2", "paraphrase_id": 0, "decoding": DECODING_FREE,
                                      "seed": seed_of(f"{t}|free:{x}|{i}|v2"), "chat": chat})
        frows = g.run(free_reqs, 32)
        append_jsonl(FREE_RAW, frows)
        t0 = time.time()
        done = label_and_store(rows, 1)
        timings["label1_s"] = time.time() - t0
    tal = tally(done)
    for k in sorted(tal):
        logger.info(f"after round 1: {k} {tal[k]}")
    # ---- round 2 (plain): adaptive count, cap 8 per paraphrase
    reqs = []
    for t in TASKS:
        for j in MODES[t]:
            s = tal[(t, j, "plain")]
            if s["labelled"] >= N_FORCED_TARGET or s["attempts"] >= 120:
                continue
            if s["labelled"] == 0 and s["attempts"] >= 40:
                continue  # zero yield in the first 40 -> descriptive family directly
            y = s["labelled"] / max(1, s["attempts"])
            need = math.ceil((N_FORCED_TARGET - s["labelled"]) / max(y, 0.05) * 1.25)
            per_para = min(8, max(1, math.ceil(need / 10)), (120 - s["attempts"]) // 10)
            if per_para > 0:
                reqs += forced_reqs(conds, t, j, "plain", s["attempts"] // 10, per_para)
    if reqs:
        logger.info(f"round 2: {len(reqs)} requests")
        t0 = time.time()
        done += label_and_store(g.run(reqs, 1024), 2)
        timings["round2_s"] = time.time() - t0
        tal = tally(done)
    # ---- round 3 (descriptive family), cap 120 attempts
    reqs = []
    for t in TASKS:
        for j in MODES[t]:
            s = tal[(t, j, "plain")]
            sd = tal.get((t, j, "desc"), {"attempts": 0, "labelled": 0})
            if s["labelled"] >= N_FORCED_TARGET or sd["attempts"] > 0:
                continue
            reqs += forced_reqs(conds, t, j, "desc", 0, 12)
    if reqs:
        logger.info(f"round 3 (descriptive): {len(reqs)} requests")
        t0 = time.time()
        done += label_and_store(g.run(reqs, 1024), 3)
        timings["round3_s"] = time.time() - t0
        tal = tally(done)
    summary = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in sorted(tal.items())}
    for k, v in summary.items():
        logger.info(f"final: {k} {v}")
    write_json(DATA / "forced_generation_summary.json", {"tally": summary, "timings": timings,
                                                         "max_num_seqs": args.max_num_seqs})


if __name__ == "__main__":
    main()
