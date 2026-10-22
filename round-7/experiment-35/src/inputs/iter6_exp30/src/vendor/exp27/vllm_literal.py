#!/usr/bin/env python3
"""S2 literal cell F (run with .venv_vllm in its own process; never imported with the HF engine).

The request's literal cell: shortest-path task T2, thinking ON, top-k 10 (top-p 1, min-p 0, no penalties), the SAME
token seed for a slot at every temperature, T in {0.3, 0.7, 1.0, 1.3}, plus a repeat of T 0.7 (noise floor).
Seeds = exp21's 20 slots (T2, W1-W5 x k 0-3): seed = stable_seed('T2', w, k), answer seed = stable_seed('T2', w, k,
'answer'), so every trace pairs slot for slot with exp21's top-p-1 run (data/raw_thinking.jsonl of exp21).

Coupling: vLLM's seeded native sampler is the exponential race (q = Exp(1) per vocabulary entry from a per-request
generator seeded with the request seed; token = argmax(probs / q)); top-k 10 masks before the race, so a seed couples
the four temperatures. VLLM_USE_FLASHINFER_SAMPLER=0 keeps the native sampler.

Engine: exp21's make_llm rule (bf16 only if the KV cache fits >= 4 sequences of 18,432 tokens, else the official
Qwen/Qwen3-8B-FP8 checkpoint); no C compiler on this machine -> enforce_eager, TORCH_COMPILE_DISABLE=1,
VLLM_TEST_FORCE_FP8_MARLIN=1 (exp21's exact flags).

Two-pass thinking (Qwen3 documented early exit, exp21): pass A generates up to THINK_CAP tokens and stops at
'</think>' (151668); pass B continues prompt + thinking -> answer (max 1536 tokens, same T and top-k, the answer seed);
a trace without '</think>' gets the EARLY_EXIT line + '</think>' and is flagged 'forced' (sensitivity only).
Requests are grouped by seed (4 temperatures + the repeat = 5 per seed) and submitted in seed order: stage 10 (2 seed
groups) -> extrapolation -> main, inside the 80-minute time box (hard stop between seed-group chunks).

usage: .venv_vllm/bin/python src/vllm_literal.py {u6|cell|all}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
os.environ.setdefault("VLLM_NO_USAGE_STATS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
_HAS_CC = any(Path(d, c).exists() for d in os.environ.get("PATH", "").split(":") for c in ("gcc", "cc"))
if not _HAS_CC:
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
    os.environ.setdefault("VLLM_TEST_FORCE_FP8_MARLIN", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from cfg import (DATA_DIR, INPUTS, MODEL_ID, MODEL_REVISION, PRED_DIR, RESULTS_DIR, append_jsonl,  # noqa: E402
                 model_path, read_json, read_jsonl, sha256_text, stable_seed, utc_now, write_json)
from cfg5 import (ANSWER_MAX, EARLY_EXIT, F_REPEAT_T, F_SEED_K, F_TASK, F_TEMPS, F_TOPK, FP8_MODEL_ID,  # noqa: E402
                  FP8_REVISION, LITERAL_BOX_S, MAX_MODEL_LEN, THINK_CAP, THINK_END)
from lexicon import first_approach  # noqa: E402

RAW_LIT = DATA_DIR / "literal_raw.jsonl"          # full traces (thinking + answer)
SAMPLES_LIT = DATA_DIR / "literal_samples.jsonl"  # answer rows in the samples_raw format (for the labeller)
TIMING = RESULTS_DIR / "timing_vllm.json"
ENGINE = "vllm==0.11.0 (V1, eager, FP8 Marlin weight-only, native sampler)"
TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]


def fmt_t(t: float) -> str:
    return f"{float(t):.1f}"


def arm_of(T: float, repeat: bool) -> str:
    return f"LIT_REP_T{fmt_t(T)}" if repeat else f"LIT_T{fmt_t(T)}"


# ------------------------------------------------------------------------------------------------ prompts
def load_tok():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))


def chat(tok, text: str, thinking: bool) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True,
                                  enable_thinking=thinking)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def twin_prompts(tok) -> dict[str, dict[str, Any]]:
    """T2 twin prompts: thinking-off ids asserted equal to exp17's; thinking-on ids asserted equal (sha256) to the
    ids exp21's thinking traces were generated from."""
    e21_sha = {}
    for r in read_jsonl(INPUTS / "exp21" / "data" / "raw_thinking.jsonl"):
        if r["task"] == F_TASK:
            e21_sha.setdefault(r["template"], r["prompt_sha256"])
    out = {}
    for r in read_jsonl(INPUTS / "exp17" / "prompts" / "prompts.jsonl"):
        if r["task"] != F_TASK or r["kind"] != "twin":
            continue
        off = chat(tok, r["user_text"], False)
        assert off == r["ids"], f"T2/{r['w']}: thinking-off re-render differs from exp17 ids"
        on = chat(tok, r["user_text"], True)
        tail = tok("<think>\n\n</think>\n\n", add_special_tokens=False)["input_ids"]
        assert off[:len(on)] == on and off[len(on):] == tail, "thinking-on prompt is not the thinking-off prefix"
        sha_on = sha256_text(json.dumps(on))
        assert sha_on == e21_sha[r["w"]], f"T2/{r['w']}: thinking-on ids differ from exp21's"
        out[r["w"]] = {"off": off, "on": on, "user_text": r["user_text"], "sha_on": sha_on,
                       "sha_off": sha256_text(json.dumps(off))}
    assert sorted(out) == TEMPLATES
    return out


# ------------------------------------------------------------------------------------------------ engine
def make_llm(max_num_seqs: int | None = None):
    from vllm import LLM

    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=30)
    tot = float(q.stdout.strip().splitlines()[0]) * 2 ** 20
    bf16_bytes = 16.4e9
    kv_seqs_bf16 = (0.90 * tot - bf16_bytes - 1.5 * 2 ** 30) / (MAX_MODEL_LEN * 147_456)
    use_fp8 = kv_seqs_bf16 < 4
    mid, rev = (FP8_MODEL_ID, FP8_REVISION) if use_fp8 else (MODEL_ID, MODEL_REVISION)
    path = model_path(mid, rev)
    # expected KV tokens before construction (FP8 weights ~9.4 GB) -> max_num_seqs rule (plan: 24 if >= 120k)
    w_bytes = 9.4e9 if use_fp8 else bf16_bytes
    kv_est = (0.90 * tot - w_bytes - 1.5 * 2 ** 30) / 147_456
    mns = max_num_seqs or (24 if kv_est >= 120_000 else 16)
    t0 = time.time()
    llm = LLM(model=path, tokenizer=path, dtype="bfloat16", max_model_len=MAX_MODEL_LEN, gpu_memory_utilization=0.90,
              enable_prefix_caching=True, max_num_seqs=mns, enforce_eager=not _HAS_CC, seed=0,
              generation_config="vllm", logprobs_mode="processed_logprobs", max_logprobs=20,
              max_num_batched_tokens=4096)
    info = {"model": mid, "revision": rev, "local_path_name": Path(path).name, "kv_seqs_bf16_rule": kv_seqs_bf16,
            "use_fp8": use_fp8, "load_seconds": time.time() - t0, "engine": ENGINE, "has_c_compiler": _HAS_CC,
            "kv_tokens_estimate": kv_est,
            "env": {k: os.environ.get(k) for k in ("VLLM_USE_FLASHINFER_SAMPLER", "TORCH_COMPILE_DISABLE",
                                                     "VLLM_TEST_FORCE_FP8_MARLIN")},
            "params": {"max_model_len": MAX_MODEL_LEN, "gpu_memory_utilization": 0.90, "enable_prefix_caching": True,
                       "max_num_seqs": mns, "enforce_eager": not _HAS_CC, "max_num_batched_tokens": 4096}}
    try:
        import vllm
        info["vllm_version"] = vllm.__version__
        cc = llm.llm_engine.vllm_config.cache_config
        info["num_gpu_blocks"] = getattr(cc, "num_gpu_blocks", None)
        info["block_size"] = getattr(cc, "block_size", None)
        if info["num_gpu_blocks"] and info["block_size"]:
            info["kv_tokens"] = info["num_gpu_blocks"] * info["block_size"]
    except (AttributeError, ImportError) as e:
        info["engine_introspection_error"] = str(e)
    logger.info(f"vLLM engine: {info}")
    write_json(RESULTS_DIR / "vllm_engine.json", info)
    return llm, info


def sp(T: float, seed: int, max_tokens: int, stop_think: bool = False, top_k: int = F_TOPK,
       ignore_eos: bool = False, logprobs: int | None = None):
    from vllm import SamplingParams

    return SamplingParams(temperature=T, top_p=1.0, top_k=top_k, min_p=0.0, seed=int(seed) % (2 ** 63),
                          max_tokens=max_tokens, stop_token_ids=[THINK_END] if stop_think else None,
                          include_stop_str_in_output=True, skip_special_tokens=False, ignore_eos=ignore_eos,
                          logprobs=logprobs, repetition_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0)


def run(llm, prompts: list[list[int]], params: list[Any]) -> tuple[list[Any], float]:
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    outs = llm.generate([TokensPrompt(prompt_token_ids=p) for p in prompts], sampling_params=params, use_tqdm=False)
    return outs, time.time() - t0


def _timing_update(d: dict[str, Any]) -> None:
    cur = json.loads(TIMING.read_text()) if TIMING.exists() else {}
    cur.update(d)
    write_json(TIMING, cur)


# ------------------------------------------------------------------------------------------------ U6
def stage_u6(llm, tok) -> dict[str, Any]:
    import math

    p = RESULTS_DIR / "u6_vllm.json"
    if p.exists():
        return read_json(p)
    words = ["Write one random lowercase English word. Reply with the word only.",
             "Name one random animal. Reply with one word only.",
             "Give one random colour name. Reply with one word only.",
             "Write a random first name. Reply with the name only."]
    base = [chat(tok, w, False) for w in words]
    seeds = [stable_seed("smoke", "u6_lit", i) for i in range(4)]
    a, _ = run(llm, base, [sp(1.0, s, 256, ignore_eos=True) for s in seeds])
    b, _ = run(llm, base, [sp(1.0, s, 256, ignore_eos=True) for s in seeds])   # second run: prefix-cache hits
    ident = [list(x.outputs[0].token_ids) == list(y.outputs[0].token_ids) for x, y in zip(a, b)]
    # top-k 10 support: processed logprobs (after top-k) have at most 10 finite entries
    c, _ = run(llm, base, [sp(1.0, s, 8, logprobs=20, ignore_eos=True) for s in seeds])
    max_support = 0
    for o in c:
        for step in o.outputs[0].logprobs:
            n_fin = sum(1 for v in step.values() if v.logprob is not None and math.isfinite(v.logprob))
            max_support = max(max_support, n_fin)
    res = {"U6_same_seed_twice_identical": f"{sum(ident)}/{len(ident)}",
           "U6_second_run_is_prefix_cache_hit": True,
           "U6_topk10_max_finite_logprobs": max_support, "U6_topk10_pass": max_support <= 10,
           "note": ("prefix caching on vs off is tested as cache-miss (first run) vs cache-hit (second run) of the same "
                    "requests; toggling enable_prefix_caching would need a second engine load")}
    write_json(p, res)
    logger.info(f"U6: {res}")
    return res


# ------------------------------------------------------------------------------------------------ the cell
def seed_order() -> list[tuple[str, int]]:
    return [(w, k) for w in TEMPLATES for k in F_SEED_K]


def requests_for(seeds: list[tuple[str, int]]) -> list[dict[str, Any]]:
    req = []
    for w, k in seeds:
        for T in F_TEMPS:
            req.append({"arm": arm_of(T, False), "T": T, "w": w, "k": k, "repeat": False})
        req.append({"arm": arm_of(F_REPEAT_T, True), "T": F_REPEAT_T, "w": w, "k": k, "repeat": True})
    for r in req:
        r["seed"] = stable_seed(F_TASK, r["w"], r["k"])
        r["answer_seed"] = stable_seed(F_TASK, r["w"], r["k"], "answer")
    return req


def _pass_a(llm, pr: dict, reqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outs, dt = run(llm, [pr[r["w"]]["on"] for r in reqs],
                   [sp(r["T"], r["seed"], THINK_CAP, stop_think=True) for r in reqs])
    res = []
    for r, o in zip(reqs, outs):
        c = o.outputs[0]
        ids = list(c.token_ids)
        has_end = THINK_END in ids
        if has_end:
            ids = ids[:ids.index(THINK_END) + 1]
        res.append({**r, "think_ids": ids, "think_text": c.text, "n_think_tokens": len(ids),
                    "finish_reason_A": c.finish_reason, "stop_reason_A": c.stop_reason, "closed": has_end,
                    "seconds_batch_A": dt})
    ntok = sum(x["n_think_tokens"] for x in res)
    logger.info(f"F pass A: {len(res)} traces, {ntok} tokens in {dt:.0f}s ({ntok / max(dt, 1e-9):.0f} tok/s); "
                f"closed {sum(x['closed'] for x in res)}/{len(res)}")
    return res


def _pass_b(llm, tok, pr: dict, res: list[dict[str, Any]]) -> float:
    ee = tok(EARLY_EXIT, add_special_tokens=False)["input_ids"]
    prompts, params = [], []
    for x in res:
        base = pr[x["w"]]["on"] + x["think_ids"]
        if not x["closed"]:
            base = base + ee
        prompts.append(base)
        params.append(sp(x["T"], x["answer_seed"], ANSWER_MAX))
    outs, dt = run(llm, prompts, params)
    for x, o in zip(res, outs):
        c = o.outputs[0]
        x["answer_text"] = c.text
        x["answer_ids"] = list(c.token_ids)
        x["finish_reason_B"] = c.finish_reason
        x["forced"] = not x["closed"]
        x["completed"] = bool(x["closed"] and c.finish_reason == "stop")
    logger.info(f"F pass B: {len(res)} answers in {dt:.0f}s; completed {sum(x['completed'] for x in res)}")
    return dt


def _write(res: list[dict[str, Any]], pr: dict, info: dict[str, Any], block: str) -> None:
    raw, samp = [], []
    for x in res:
        fa, fa_pos = first_approach(x["think_text"])
        common = {"task": F_TASK, "template": x["w"], "arm": x["arm"], "slot": x["k"],
                  "sample_id": f"{F_TASK}|{x['arm']}|{x['w']}|{x['k']}", "crn_key": f"{F_TASK}|{x['w']}|{x['k']}",
                  "seed": x["seed"], "answer_seed": x["answer_seed"], "temperature": x["T"], "top_k": F_TOPK,
                  "top_p": 1.0, "min_p": 0.0, "coupling": "exp_race_vllm", "thinking": True, "repeat": x["repeat"],
                  "model": info["model"], "model_revision": info["revision"], "engine": ENGINE,
                  "precision": "fp8_official_checkpoint" if info["use_fp8"] else "bf16",
                  "prompt_sha256": pr[x["w"]]["sha_on"], "n_think_tokens": x["n_think_tokens"],
                  "completed": x["completed"], "forced": x["forced"], "closed": x["closed"],
                  "first_approach": fa, "first_approach_char": fa_pos, "block_id": block, "utc": utc_now()}
        raw.append({**common, "think_text": x["think_text"], "think_ids": x["think_ids"],
                    "finish_reason_A": x["finish_reason_A"], "stop_reason_A": x["stop_reason_A"],
                    "answer_text": x["answer_text"], "answer_ids": x["answer_ids"],
                    "finish_reason_B": x["finish_reason_B"], "seconds_batch_A": x.get("seconds_batch_A")})
        samp.append({**common, "text": x["answer_text"], "token_ids": x["answer_ids"],
                     "n_new_tokens": len(x["answer_ids"]), "finish_reason": x["finish_reason_B"]})
    append_jsonl(RAW_LIT, raw)
    append_jsonl(SAMPLES_LIT, samp)


def wait_for_commit(tag: str, max_wait_s: float = 2 * 3600) -> None:
    log = ROOT / "commitments.log"
    t0 = time.time()
    while True:
        if log.exists() and any(l.split()[-1] == tag for l in log.read_text().splitlines() if l.strip()):
            logger.info(f"{tag} found in commitments.log: decisive literal-cell sampling may start")
            return
        if time.time() - t0 > max_wait_s:
            raise RuntimeError(f"{tag} not found in commitments.log")
        time.sleep(10)


def stage_cell(llm, tok, info: dict[str, Any]) -> None:
    wait_for_commit("commit0F")
    pr = twin_prompts(tok)
    t_box0 = time.time()
    have = {(r["arm"], r["template"], int(r["slot"])) for r in read_jsonl(RAW_LIT)}
    seeds = seed_order()
    todo_seeds = [s for s in seeds if any((r["arm"], r["w"], r["k"]) not in have for r in requests_for([s]))]
    if not todo_seeds:
        logger.info("F: all traces present")
        return
    # stage 10 = 2 seed groups
    st10 = todo_seeds[:2]
    reqs10 = [r for r in requests_for(st10) if (r["arm"], r["w"], r["k"]) not in have]
    ta = time.time()
    res10 = _pass_a(llm, pr, reqs10)
    _pass_b(llm, tok, pr, res10)
    _write(res10, pr, info, "F:stage10")
    dt10 = time.time() - ta
    comp = sum(x["completed"] for x in res10) / max(len(res10), 1)
    ntok = sum(x["n_think_tokens"] + len(x["answer_ids"]) for x in res10)
    rest = todo_seeds[2:]
    # extrapolation: stage 10 ran 10 requests concurrently; the main run keeps max_num_seqs busy, so its time is
    # roughly (remaining requests / concurrency) x the stage-10 per-wave time (conservatively 1.25x)
    mns = info["params"]["max_num_seqs"]
    n_rest = 5 * len(rest)
    est = dt10 * max(1.0, n_rest / mns) * 1.25
    box_left = LITERAL_BOX_S - (time.time() - t_box0)
    _timing_update({"F_stage10": {"seconds": dt10, "n": len(res10), "tokens": ntok, "completion": comp,
                                  "mean_think_tokens": sum(x["n_think_tokens"] for x in res10) / max(len(res10), 1),
                                  "median_think_tokens": sorted(x["n_think_tokens"] for x in res10)[len(res10) // 2]},
                    "F_extrapolation": {"remaining_requests": n_rest, "est_seconds": est,
                                        "box_left_seconds": box_left, "max_num_seqs": mns}})
    logger.info(f"F stage 10: {dt10:.0f}s, completion {comp:.2f}; remaining {n_rest} requests est {est:.0f}s, "
                f"box left {box_left:.0f}s")
    # main: one submission if it fits the box, else chunks of seed groups with a hard stop between chunks
    if est <= 0.85 * box_left:
        chunks = [rest]
    else:
        per = max(1, int(mns // 5) * 2)
        chunks = [rest[i:i + per] for i in range(0, len(rest), per)]
        logger.warning(f"F: extrapolation over the box -> {len(chunks)} chunks of {per} seed groups")
    for ci, ch in enumerate(chunks):
        if time.time() - t_box0 > LITERAL_BOX_S:
            logger.warning(f"F: time box reached before chunk {ci}; {sum(len(c) for c in chunks[ci:])} seed groups "
                           "not run (reported with denominators)")
            _timing_update({"F_not_run_seed_groups": [f"{w}|{k}" for c in chunks[ci:] for w, k in c]})
            break
        reqs = [r for r in requests_for(ch) if (r["arm"], r["w"], r["k"]) not in have]
        tm = time.time()
        res = _pass_a(llm, pr, reqs)
        _pass_b(llm, tok, pr, res)
        _write(res, pr, info, f"F:main{ci}")
        _timing_update({f"F_main{ci}": {"seconds": time.time() - tm, "n": len(res),
                                        "tokens": sum(x["n_think_tokens"] + len(x["answer_ids"]) for x in res)}})
    _timing_update({"F_total_seconds": time.time() - t_box0})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["u6", "cell", "all"])
    args = ap.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / "vllm_literal.log"), rotation="30 MB", level="DEBUG")
    tok = load_tok()
    twin_prompts(tok)   # assertions before the engine loads
    llm, info = make_llm()
    if args.stage in ("u6", "all"):
        stage_u6(llm, tok)
    if args.stage in ("cell", "all"):
        stage_cell(llm, tok, info)
    (RESULTS_DIR / "literal_done.flag").write_text(utc_now())
    logger.info("vllm_literal done")


if __name__ == "__main__":
    main()
