#!/usr/bin/env python3
"""Stage 1.3: the base model's repertoire (Qwen3-8B-Base, vLLM bf16, unhooked).

BASE_CHAT  the 75 chat-templated twin prompts (identical ids to the instruct twin): N = 100 per task (5 templates x
           20 slots j), T1/T2 N = 200 (5 x 40) from the start. T = 1.0, top-p 1.0, no top-k, max_tokens 1,024
           (T1/T2 1,536), stop on <|im_end|>, <|im_start|>, <|endoftext|>. One request per slot with its own seed
           sha256(task, W, j, 'base') (vLLM per-request seeds).
BASE_PLAIN plain completion (sensitivity): N = 100 per task (5 x 20), the ITER1 exp5 template-free stop strings.
TOP-UP     (committed in COMMIT #0) after labelling, any task other than T1/T2 with < 30 correct BASE_CHAT programs
           gets 100 more (slots j = 20..39), once.
Rows -> data/base_raw.jsonl (resumable by sample_id).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (BASE_CHAT_N, BASE_CHAT_N_PATH, BASE_ID, BASE_KEY, BASE_PLAIN_N, BASE_REVISION, DATA_DIR,  # noqa: E402
                 ENDOFTEXT, IM_END, IM_START, MAX_NEW_BASE_PATH, MAX_NEW_TOKENS, PATH_TASKS, RESULTS_DIR,
                 TASKS15, TEMPLATE_IDS, TOPUP_MIN_CORRECT, TOPUP_N, append_deviation, append_jsonl, model_path,
                 read_jsonl, setup_logging, stable_seed, utc_now, write_json)
from prompts5 import load_prompts  # noqa: E402

RAW = DATA_DIR / "base_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
TF_STOPS = ['\nif __name__', '\n# Test', '\n# test', '\n# Example', '\nprint(', '\nassert ', '\n"""', '\n```',
            '<|endoftext|>', '\n\n\n\n']  # ITER1 exp5 gen_vllm.py, verbatim


def max_new(task: str) -> int:
    return MAX_NEW_BASE_PATH if task in PATH_TASKS else MAX_NEW_TOKENS


def requests(arm: str, tasks: list[str], slots_of: dict[str, list[int]], prompts: dict) -> list[dict]:
    reqs = []
    for t in tasks:
        for w in TEMPLATE_IDS:
            p = prompts[(t, w)]
            for j in slots_of[t]:
                reqs.append({"task": t, "w": w, "j": j, "arm": arm, "p": p,
                             "seed": stable_seed(t, w, j, BASE_KEY) % (2 ** 31 - 1),
                             "sample_id": f"{t}|{arm}|{w}|{j}"})
    return reqs


def run(llm, reqs: list[dict], plain: bool, stage: str) -> int:
    from vllm import SamplingParams

    done = {r["sample_id"] for r in read_jsonl(RAW)}
    todo = [r for r in reqs if r["sample_id"] not in done]
    if not todo:
        return 0
    sps = []
    for r in todo:
        if plain:
            sp = SamplingParams(n=1, temperature=1.0, top_p=1.0, min_p=0.0, max_tokens=MAX_NEW_TOKENS, seed=r["seed"],
                                stop=TF_STOPS, stop_token_ids=[ENDOFTEXT], skip_special_tokens=False,
                                include_stop_str_in_output=False)
        else:
            sp = SamplingParams(n=1, temperature=1.0, top_p=1.0, min_p=0.0, max_tokens=max_new(r["task"]),
                                seed=r["seed"], stop_token_ids=[IM_END, IM_START, ENDOFTEXT],
                                skip_special_tokens=False)
        sps.append(sp)
    t0 = time.time()
    outs = llm.generate([{"prompt_token_ids": r["p"]["ids"]} for r in todo], sps, use_tqdm=False)
    dt = time.time() - t0
    rows = []
    for r, o in zip(todo, outs):
        c = o.outputs[0]
        rows.append({"task": r["task"], "arm": r["arm"], "template": r["w"], "slot": r["j"],
                     "sample_id": r["sample_id"], "crn_key": f"{r['task']}|{r['w']}|{r['j']}|{BASE_KEY}",
                     "u_seed": r["seed"], "direction_seed": None, "alpha": None, "lambda": None, "site": None,
                     "temperature": 1.0, "top_k": 0, "min_p": 0.0, "thinking": False,
                     "prompt_kind": r["p"]["kind"], "prompt_sha256": r["p"]["prompt_sha256"], "P": r["p"]["P"],
                     "model": BASE_ID, "model_revision": BASE_REVISION, "engine": "vllm_bf16",
                     "quant": "bf16", "max_new": sps[0].max_tokens if plain else max_new(r["task"]),
                     "stop_rule": "tf_stops" if plain else "im_end|im_start|endoftext", "block_id": stage,
                     "batch_B": len(todo), "text": c.text, "n_new_tokens": len(c.token_ids),
                     "finish_reason": "stop" if c.finish_reason == "stop" else "length",
                     "stop_reason": str(c.stop_reason) if c.stop_reason is not None else None,
                     "realised_disp": None, "utc": utc_now()})
    append_jsonl(RAW, rows)
    append_jsonl(RESULTS_DIR / "timing_base_vllm.jsonl",
                 [{"stage": stage, "n": len(rows), "seconds": round(dt, 1), "utc": utc_now(),
                   "tokens": sum(r["n_new_tokens"] for r in rows)}])
    logger.info(f"{stage}: {len(rows)} programs in {dt:.0f}s ({sum(r['n_new_tokens'] for r in rows)} tokens)")
    return len(rows)


def correct_counts(arm: str) -> tuple[dict[str, int], int, int]:
    raw_ids = {r["sample_id"] for r in read_jsonl(RAW) if r["arm"] == arm}
    labs = {r["sample_id"]: r for r in read_jsonl(LABELS) if r.get("sample_id") in raw_ids}
    out: dict[str, int] = {}
    for r in labs.values():
        out[r["task"]] = out.get(r["task"], 0) + int(bool(r.get("passed")))
    return out, len(labs), len(raw_ids)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["pilot", "all"])
    ap.add_argument("--topup-wait-min", type=float, default=25.0)
    args = ap.parse_args()
    setup_logging("base_vllm")
    from vllm import LLM

    tw = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
    pl = {(r["task"], r["w"]): r for r in load_prompts(("plain_tf",))}
    t0 = time.time()
    llm = LLM(model=model_path(BASE_ID, BASE_REVISION), dtype="bfloat16", enforce_eager=True,
              gpu_memory_utilization=0.88, max_model_len=2048, seed=0, max_num_seqs=256)
    logger.info(f"vLLM base loaded in {time.time() - t0:.0f}s")
    if args.stage == "pilot":
        run(llm, requests("BASE_CHAT", ["T03", "T2"], {"T03": [0, 1], "T2": [0, 1]}, tw), False, "pilot10")
        return
    chat_slots = {t: list(range((BASE_CHAT_N_PATH if t in PATH_TASKS else BASE_CHAT_N) // 5)) for t in TASKS15}
    run(llm, requests("BASE_CHAT", list(TASKS15), chat_slots, tw), False, "base_chat")
    run(llm, requests("BASE_PLAIN", list(TASKS15), {t: list(range(BASE_PLAIN_N // 5)) for t in TASKS15}, pl), True,
        "base_plain")
    # top-up rule (COMMIT #0): wait for the BASE_CHAT labels, then N = 200 for tasks with < 30 correct
    t_w = time.time()
    while True:
        cc, n_lab, n_raw = correct_counts("BASE_CHAT")
        if n_lab >= n_raw:
            break
        if time.time() - t_w > args.topup_wait_min * 60:
            append_deviation("D-topup-wait", f"BASE_CHAT labels incomplete ({n_lab}/{n_raw}) after "
                                             f"{args.topup_wait_min} min; top-up decided on the labelled rows")
            break
        logger.info(f"waiting for BASE_CHAT labels: {n_lab}/{n_raw}")
        time.sleep(20)
    need = [t for t in TASKS15 if t not in PATH_TASKS and cc.get(t, 0) < TOPUP_MIN_CORRECT]
    write_json(RESULTS_DIR / "base_topup.json", {"correct_before_topup": cc, "topup_tasks": need,
                                                 "rule": f"< {TOPUP_MIN_CORRECT} correct -> +{TOPUP_N}",
                                                 "engine": "vllm_bf16 (same engine as the main base sample)",
                                                 "utc": utc_now()})
    if need:
        extra = {t: list(range(BASE_CHAT_N // 5, (BASE_CHAT_N + TOPUP_N) // 5)) for t in need}
        run(llm, requests("BASE_CHAT", need, extra, tw), False, "base_chat_topup")
    (DATA_DIR / "base_vllm_done.flag").write_text(utc_now())
    logger.info(f"base sampling finished in {time.time() - t0:.0f}s; top-up tasks {need}")


if __name__ == "__main__":
    main()
