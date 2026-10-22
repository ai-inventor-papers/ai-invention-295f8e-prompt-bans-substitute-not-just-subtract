#!/usr/bin/env python3
"""S5 / G1 (vLLM 0.11, run with .venv_vllm): thinking-on T2 under per-request seeds, plus the U6 smoke tests and the
FP8 cross-check. Never imported together with the HF engine.

Coupling: vLLM's seeded sampler is the exponential race (q = Exp(1) per vocabulary entry from a per-request CUDA
generator seeded with the request seed; token = argmax(probs / q)) = Gumbel-max with step-indexed noise. The same seed
is used for a slot at every temperature, so T is the only thing that differs between a slot's four traces.

Engine: Qwen/Qwen3-8B-FP8 (bf16 does not fit 16 GB), weight-only FP8 Marlin kernels (no C compiler on the machine, so
torch.compile and Triton-built kernels are off: enforce_eager, TORCH_COMPILE_DISABLE=1, VLLM_TEST_FORCE_FP8_MARLIN=1),
VLLM_USE_FLASHINFER_SAMPLER=0 (native PyTorch sampler).

Two-pass thinking (Qwen3 documented early exit): pass A generates up to THINK_CAP tokens and stops at '</think>';
pass B continues prompt + thinking -> answer (seed stable_seed(task, w, k, 'answer')); traces without '</think>' get
pass B' (the early-exit line + '</think>' appended) and are labelled 'forced' (sensitivity only).

usage: .venv_vllm/bin/python src/vllm_think.py {u6|fp8x|g1|t1|all} [--minutes M]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
os.environ.setdefault("VLLM_TEST_FORCE_FP8_MARLIN", "1")
os.environ.setdefault("VLLM_NO_USAGE_STATS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from cfg import (DATA_DIR, MODEL_ID, MODEL_REVISION, RESULTS_DIR, append_jsonl, model_path, read_jsonl,  # noqa: E402
                 sha256_text, stable_seed, utc_now, write_json)
from cfg4 import (ANSWER_MAX, EARLY_EXIT, FIRST_APPROACH_LEXICON, FP8_MODEL_ID, FP8_REVISION, MAX_MODEL_LEN,  # noqa: E402
                  TEMPS, THINK_CAP, THINK_END, MemWatch, fmt_t, wall_guard)

RAW_SAMPLES = DATA_DIR / "samples_raw.jsonl"
RAW_THINK = DATA_DIR / "raw_thinking.jsonl"
RAW_SMOKE = DATA_DIR / "raw_smoke_vllm.jsonl"
TIMING = RESULTS_DIR / "timing_vllm.json"
ENGINE = "vllm==0.11.0 (V1, eager, FP8 Marlin weight-only, native sampler)"
TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]


def first_approach(text: str) -> tuple[str | None, int | None]:
    best: tuple[int, int, str] | None = None
    for pri, (name, pat) in enumerate(FIRST_APPROACH_LEXICON):
        flags = 0 if name == "a_star" else re.IGNORECASE
        m = re.search(pat, text, flags)
        if m and (best is None or (m.start(), pri) < (best[0], best[1])):
            best = (m.start(), pri, name)
    return (best[2], best[0]) if best else (None, None)


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


def twin_prompts(tok, task: str = "T2") -> dict[str, dict[str, Any]]:
    """Twin prompts of one task: thinking-off ids (asserted equal to exp17's) and thinking-on ids."""
    out = {}
    for r in read_jsonl(ROOT / "prompts/prompts.jsonl"):
        if r["task"] != task or r["kind"] != "twin":
            continue
        off = chat(tok, r["user_text"], False)
        assert off == r["ids"], f"{task}/{r['w']}: thinking-off re-render differs from exp17 ids"
        on = chat(tok, r["user_text"], True)
        tail = tok("<think>\n\n</think>\n\n", add_special_tokens=False)["input_ids"]
        assert off[:len(on)] == on and off[len(on):] == tail, "thinking-on prompt is not the thinking-off prefix"
        out[r["w"]] = {"off": off, "on": on, "user_text": r["user_text"], "p1": r["p1"], "spec_end": r["spec_end"],
                       "sha_off": sha256_text(json.dumps(off)), "sha_on": sha256_text(json.dumps(on))}
    return out


# ------------------------------------------------------------------------------------------------ engine
def make_llm():
    from vllm import LLM

    import subprocess
    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=30)
    tot = float(q.stdout.strip().splitlines()[0]) * 2**20      # MiB -> bytes (no CUDA init in the parent)
    bf16_bytes = 16.4e9
    kv_seqs_bf16 = (0.90 * tot - bf16_bytes - 1.5 * 2**30) / (MAX_MODEL_LEN * 147_456)
    use_fp8 = kv_seqs_bf16 < 4
    mid, rev = (FP8_MODEL_ID, FP8_REVISION) if use_fp8 else (MODEL_ID, MODEL_REVISION)
    path = model_path(mid, rev)
    t0 = time.time()
    llm = LLM(model=path, tokenizer=path, dtype="bfloat16", max_model_len=MAX_MODEL_LEN, gpu_memory_utilization=0.90,
              enable_prefix_caching=True, max_num_seqs=16, enforce_eager=True, seed=0, generation_config="vllm",
              logprobs_mode="processed_logprobs", max_logprobs=20, max_num_batched_tokens=4096)
    info = {"model": mid, "revision": rev, "local_path_name": Path(path).name, "kv_seqs_bf16_rule": kv_seqs_bf16,
            "use_fp8": use_fp8, "load_seconds": time.time() - t0, "engine": ENGINE,
            "env": {k: os.environ.get(k) for k in ("VLLM_USE_FLASHINFER_SAMPLER", "TORCH_COMPILE_DISABLE",
                                                     "VLLM_TEST_FORCE_FP8_MARLIN")},
            "params": {"max_model_len": MAX_MODEL_LEN, "gpu_memory_utilization": 0.90, "enable_prefix_caching": True,
                       "max_num_seqs": 16, "enforce_eager": True, "max_num_batched_tokens": 4096}}
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


def sp(T: float, seed: int, max_tokens: int, stop_think: bool = False, ignore_eos: bool = False, logprobs: int | None = None):
    from vllm import SamplingParams

    return SamplingParams(temperature=T, top_p=1.0, top_k=0, min_p=0.0, seed=int(seed) % (2 ** 63),
                          max_tokens=max_tokens, stop_token_ids=[THINK_END] if stop_think else None,
                          include_stop_str_in_output=True, skip_special_tokens=False, ignore_eos=ignore_eos,
                          logprobs=logprobs, repetition_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0)


def run(llm, prompts: list[list[int]], params: list[Any]) -> tuple[list[Any], float]:
    from vllm.inputs import TokensPrompt

    t0 = time.time()
    outs = llm.generate([TokensPrompt(prompt_token_ids=p) for p in prompts], sampling_params=params, use_tqdm=False)
    return outs, time.time() - t0


# ------------------------------------------------------------------------------------------------ U6
def stage_u6(llm, tok, info: dict[str, Any]) -> dict[str, Any]:
    import torch

    words = ["Write one random lowercase English word. Reply with the word only.",
             "Name one random animal. Reply with one word only.",
             "Give one random colour name. Reply with one word only.",
             "Write a random first name. Reply with the name only."]
    base = [chat(tok, w, False) for w in words]
    # (a) same seed + T in two batch compositions: alone vs inside a batch of 12 (different position), 256 forced steps
    seeds = [stable_seed("smoke", "u6a", i) for i in range(6)]
    pa = [base[i % len(base)] for i in range(6)]
    alone, _ = run(llm, pa, [sp(1.0, s, 256, ignore_eos=True) for s in seeds])
    filler_p = [base[(i + 1) % len(base)] for i in range(6)]
    mixed_p = [x for pair in zip(filler_p, pa[::-1]) for x in pair]
    mixed_s = [x for pair in zip([stable_seed("smoke", "fill", i) for i in range(6)], seeds[::-1]) for x in pair]
    mixed, _ = run(llm, mixed_p, [sp(1.0, s, 256, ignore_eos=True) for s in mixed_s])
    got = {s: list(o.outputs[0].token_ids) for s, o in zip(mixed_s, mixed)}
    ident, firstdiv = [], []
    for s, o in zip(seeds, alone):
        a, b = list(o.outputs[0].token_ids), got[s]
        d = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
        ident.append(d is None and len(a) == len(b))
        firstdiv.append(d)
    # (b) different seeds differ
    diff_out, _ = run(llm, [base[0]] * 4, [sp(1.0, stable_seed("smoke", "u6b", i), 64, ignore_eos=True) for i in range(4)])
    seqs = [tuple(o.outputs[0].token_ids) for o in diff_out]
    # (c) first token = argmax over the top-20 processed probs of p / q, q from an identically seeded CUDA generator
    V = 151936
    recs = []
    for i in range(16):
        s = stable_seed("smoke", "u6c", i)
        for T in (0.7, 1.0):
            recs.append((base[i % len(base)], s, T))
    outs, _ = run(llm, [r[0] for r in recs], [sp(T, s, 1, logprobs=20) for _, s, T in recs])
    match, details = 0, []
    for (p, s, T), o in zip(recs, outs):
        tok_id = o.outputs[0].token_ids[0]
        lp = o.outputs[0].logprobs[0]
        g = torch.Generator(device="cuda")
        g.manual_seed(int(s) % (2 ** 63))
        q = torch.empty(V, dtype=torch.float32, device="cuda").exponential_(generator=g)
        ids = list(lp.keys())
        probs = torch.tensor([float(torch.tensor(lp[t].logprob).exp()) for t in ids], device="cuda")
        win = ids[int(torch.argmax(probs / q[torch.tensor(ids, device='cuda')]).item())]
        tail = 1.0 - float(probs.sum())
        ok = win == tok_id
        match += ok
        details.append({"seed": int(s), "T": T, "sampled": int(tok_id), "recomputed": int(win), "match": bool(ok),
                        "top20_tail_mass": tail})
    same_seed_t = {}
    for i in range(16):
        a = [d for d in details if d["seed"] == stable_seed("smoke", "u6c", i)]
        same_seed_t[i] = a[0]["sampled"] == a[1]["sampled"]
    res = {"U6a_identity_rate_256_steps": sum(ident) / len(ident), "U6a_first_divergence": firstdiv,
           "U6b_distinct_seeds_distinct_outputs": len(set(seqs)) == len(seqs),
           "U6c_first_token_recompute_match": f"{match}/{len(recs)}", "U6c_match_rate": match / len(recs),
           "U6c_same_seed_T0.7_vs_T1.0_same_first_token": sum(same_seed_t.values()) / len(same_seed_t),
           "U6c_details": details,
           "note": "exactness across batch compositions is not guaranteed below CC 9.0 (no batch invariance on Ada); "
                   "U6c confirms the step-indexed exponential-race coupling on this build when the match rate is ~1 "
                   "(a mismatch is possible only when the winner lies outside the returned top-20, tail mass given)"}
    write_json(RESULTS_DIR / "u6_vllm.json", res)
    append_jsonl(RAW_SMOKE, [{"utc": utc_now(), "test": "U6", "summary": {k: v for k, v in res.items()
                                                                           if k != "U6c_details"}}])
    logger.info(f"U6: {({k: v for k, v in res.items() if k != 'U6c_details'})}")
    return res


# ------------------------------------------------------------------------------------------------ FP8 cross-check
def stage_fp8x(llm, tok, info: dict[str, Any]) -> None:
    wait_for_commit0()
    done = {(r["arm"], r["template"], r["sample_id"]) for r in read_jsonl(RAW_SAMPLES) if r["arm"] == "FP8X_T1.0"}
    pr = twin_prompts(tok, "T2")
    items = [(w, k) for w in TEMPLATES for k in range(10) if ("FP8X_T1.0", w, k) not in done]
    if not items:
        logger.info("FP8 cross-check already done")
        return
    outs, dt = run(llm, [pr[w]["off"] for w, k in items], [sp(1.0, stable_seed("T2", w, k), ANSWER_MAX) for w, k in items])
    rows = []
    for (w, k), o in zip(items, outs):
        c = o.outputs[0]
        rows.append({"task": "T2", "template": w, "arm": "FP8X_T1.0", "condition": "FP8X_T1.0", "sample_id": k,
                     "slot": f"T2|{w}|{k}", "seed": stable_seed("T2", w, k), "token_seed": stable_seed("T2", w, k),
                     "temperature": 1.0, "top_k": 0, "min_p": 0.0, "coupling": "exp_race_vllm", "thinking": False,
                     "model": info["model"], "model_revision": info["revision"], "engine": ENGINE,
                     "prompt_sha256": pr[w]["sha_off"], "text": c.text, "token_ids": list(c.token_ids),
                     "n_tokens": len(c.token_ids), "finish_reason": c.finish_reason, "block_id": "G1:FP8X",
                     "utc": utc_now()})
    append_jsonl(RAW_SAMPLES, rows)
    ntok = sum(r["n_tokens"] for r in rows)
    logger.info(f"FP8 cross-check: {len(rows)} programs, {ntok} tokens in {dt:.0f}s ({ntok / max(dt, 1e-9):.0f} tok/s)")
    _timing_update({"fp8x": {"n": len(rows), "seconds": dt, "tokens": ntok}})


def _timing_update(d: dict[str, Any]) -> None:
    cur = json.loads(TIMING.read_text()) if TIMING.exists() else {}
    cur.update(d)
    write_json(TIMING, cur)


# ------------------------------------------------------------------------------------------------ G1
def _requests(task: str, seeds: list[tuple[str, int]], repeat_seeds: list[tuple[str, int]]) -> list[dict[str, Any]]:
    req = []
    for T in TEMPS:
        for w, k in seeds:
            req.append({"arm": f"THINK_T{fmt_t(T)}", "T": T, "w": w, "k": k, "repeat": False})
    for w, k in repeat_seeds:
        req.append({"arm": "THINK_REP_T0.7", "T": 0.7, "w": w, "k": k, "repeat": True})
    for r in req:
        r["seed"] = stable_seed(task, r["w"], r["k"])
    return req


def _pass_a(llm, pr: dict, reqs: list[dict[str, Any]], task: str) -> list[dict[str, Any]]:
    outs, dt = run(llm, [pr[r["w"]]["on"] for r in reqs], [sp(r["T"], r["seed"], THINK_CAP, stop_think=True) for r in reqs])
    res = []
    for r, o in zip(reqs, outs):
        c = o.outputs[0]
        ids = list(c.token_ids)
        has_end = THINK_END in ids
        if has_end:
            ids = ids[:ids.index(THINK_END) + 1]
        res.append({**r, "think_ids": ids, "think_text": c.text, "n_think_tokens": len(ids),
                    "finish_reason_A": c.finish_reason, "stop_reason_A": c.stop_reason, "closed": has_end})
    ntok = sum(x["n_think_tokens"] for x in res)
    logger.info(f"G1 {task} pass A: {len(res)} traces, {ntok} tokens in {dt:.0f}s ({ntok / max(dt, 1e-9):.0f} tok/s); "
                f"closed {sum(x['closed'] for x in res)}/{len(res)}")
    for x in res:
        x["seconds_batch_A"] = dt
    return res


def _pass_b(llm, tok, pr: dict, res: list[dict[str, Any]], task: str) -> None:
    ee = tok(EARLY_EXIT, add_special_tokens=False)["input_ids"]
    prompts, params = [], []
    for x in res:
        base = pr[x["w"]]["on"] + x["think_ids"]
        if not x["closed"]:
            base = base + ee
        prompts.append(base)
        params.append(sp(x["T"], stable_seed(task, x["w"], x["k"], "answer"), ANSWER_MAX))
    outs, dt = run(llm, prompts, params)
    for x, o in zip(res, outs):
        c = o.outputs[0]
        x["answer_text"] = c.text
        x["answer_ids"] = list(c.token_ids)
        x["finish_reason_B"] = c.finish_reason
        x["forced"] = not x["closed"]
        x["completed"] = bool(x["closed"] and c.finish_reason == "stop")
    logger.info(f"G1 {task} pass B: {len(res)} answers in {dt:.0f}s; completed {sum(x['completed'] for x in res)}")


def _write(res: list[dict[str, Any]], pr: dict, info: dict[str, Any], task: str, block: str) -> None:
    raw, samp = [], []
    for x in res:
        fa, fa_pos = first_approach(x["think_text"])
        common = {"task": task, "template": x["w"], "arm": x["arm"], "condition": x["arm"], "sample_id": x["k"],
                  "slot": f"{task}|{x['w']}|{x['k']}", "seed": x["seed"], "token_seed": x["seed"],
                  "temperature": x["T"], "top_k": 0, "min_p": 0.0, "coupling": "exp_race_vllm", "thinking": True,
                  "repeat": x["repeat"], "model": info["model"], "model_revision": info["revision"], "engine": ENGINE,
                  "prompt_sha256": pr[x["w"]]["sha_on"], "n_think_tokens": x["n_think_tokens"],
                  "completed": x["completed"], "forced": x["forced"], "closed": x["closed"],
                  "first_approach": fa, "first_approach_char": fa_pos, "block_id": block, "utc": utc_now()}
        raw.append({**common, "think_text": x["think_text"], "think_ids": x["think_ids"],
                    "finish_reason_A": x["finish_reason_A"], "stop_reason_A": x["stop_reason_A"],
                    "answer_text": x["answer_text"], "answer_ids": x["answer_ids"],
                    "finish_reason_B": x["finish_reason_B"], "seconds_batch_A": x.get("seconds_batch_A")})
        samp.append({**common, "text": x["answer_text"], "token_ids": x["answer_ids"],
                     "n_tokens": len(x["answer_ids"]), "finish_reason": x["finish_reason_B"]})
    append_jsonl(RAW_THINK, raw)
    append_jsonl(RAW_SAMPLES, samp)


def wait_for_commit0(max_wait_s: float = 3 * 3600) -> None:
    """Decisive samples start only after commit #0 is in the hash chain (pre-registration)."""
    log = ROOT / "commitments.log"
    t0 = time.time()
    while True:
        if log.exists() and "prereg_c1seed.json" in log.read_text():
            logger.info("commit #0 found in commitments.log: decisive sampling may start")
            return
        if time.time() - t0 > max_wait_s:
            raise RuntimeError("commit #0 not found")
        time.sleep(15)


def stage_g1(llm, tok, info: dict[str, Any], task: str = "T2", minutes: float | None = None,
             ks: tuple[int, ...] = (0, 1, 2, 3), with_repeat: bool = True) -> None:
    wait_for_commit0()
    pr = twin_prompts(tok, task)
    have = {(r["arm"], r["template"], r["sample_id"]) for r in read_jsonl(RAW_THINK) if r["task"] == task}
    seeds = [(w, k) for w in TEMPLATES for k in ks]
    reqs = [r for r in _requests(task, seeds, seeds if with_repeat else [])
            if (r["arm"], r["w"], r["k"]) not in have]
    if not reqs:
        logger.info(f"G1 {task}: all traces present")
        return
    t_start = time.time()
    stage10 = [r for r in reqs if r["arm"] == "THINK_T1.0" and r["k"] in (0, 1)][:10]
    if len(stage10) == 10:
        res10 = _pass_a(llm, pr, stage10, task)
        _pass_b(llm, tok, pr, res10, task)
        _write(res10, pr, info, task, f"G1:{task}:stage10")
        dt = time.time() - t_start
        ntok = sum(x["n_think_tokens"] + len(x["answer_ids"]) for x in res10)
        comp = sum(x["completed"] for x in res10) / 10
        _timing_update({f"g1_{task}_stage10": {"seconds": dt, "tokens": ntok, "completion": comp,
                                               "mean_think_tokens": ntok / 10}})
        logger.info(f"G1 {task} stage 10: {dt:.0f}s, completion {comp:.2f}, mean tokens {ntok / 10:.0f}")
        if comp < 0.7:
            logger.warning("stage-10 completion < 0.7: stop-token handling checked (151668 + pass B); continuing "
                           "under fallback F4 (16k cap kept, completion reported per T, forced labels as sensitivity)")
        reqs = [r for r in reqs if r not in stage10]
        # extrapolate: the remaining traces run concurrently; the plan's guard is G1 done by t0 + 2h15
        remaining_s = (2.25 * 3600 - wall_guard(RESULTS_DIR / "t0.json")) if minutes is None else minutes * 60 - dt
        est = dt * len(reqs) / 10 * 0.55        # concurrency gain measured on stage 10 is ~2x (logged as estimate)
        _timing_update({f"g1_{task}_extrapolation": {"remaining_requests": len(reqs), "est_seconds": est,
                                                     "remaining_guard_seconds": remaining_s}})
        if with_repeat and est > remaining_s:
            keep = {(w, k) for w, k in seeds[::2]}
            reqs = [r for r in reqs if not r["repeat"] or (r["w"], r["k"]) in keep]
            logger.warning(f"G1 extrapolation {est:.0f}s > guard {remaining_s:.0f}s: repeat halved to 10 seeds "
                           "(drop order item 6)")
    # interleave the repeat requests in reverse order with the others (different batch composition)
    main = [r for r in reqs if not r["repeat"]]
    rep = [r for r in reqs if r["repeat"]][::-1]
    order = []
    step = max(1, len(main) // max(len(rep), 1))
    while main or rep:
        order.extend(main[:step])
        main = main[step:]
        if rep:
            order.append(rep.pop(0))
    res = _pass_a(llm, pr, order, task)
    _pass_b(llm, tok, pr, res, task)
    _write(res, pr, info, task, f"G1:{task}:main")
    _timing_update({f"g1_{task}_main": {"seconds": time.time() - t_start, "n": len(res),
                                        "tokens": sum(x["n_think_tokens"] + len(x["answer_ids"]) for x in res)}})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["u6", "fp8x", "g1", "t1", "all"])
    ap.add_argument("--minutes", type=float, default=None)
    args = ap.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / "vllm_think.log"), rotation="30 MB", level="DEBUG")
    mw = MemWatch(26.0).start()
    tok = load_tok()
    llm, info = make_llm()
    if args.stage in ("u6", "all"):
        stage_u6(llm, tok, info)
    if args.stage in ("g1", "all"):
        stage_g1(llm, tok, info, "T2", args.minutes)
    if args.stage in ("fp8x", "all"):
        stage_fp8x(llm, tok, info)
    if args.stage == "t1":
        stage_g1(llm, tok, info, "T1", args.minutes, with_repeat=False)
    logger.info(f"vllm_think done; peak container RAM {mw.peak / 1e9:.1f} GB")


if __name__ == "__main__":
    main()
