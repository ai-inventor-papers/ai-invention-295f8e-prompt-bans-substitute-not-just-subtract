"""GPU jobs A / C / D: vLLM sampling of baseline pilot, association answers and forced attempts.

Seeds: base 20261020 + offsets.  Pilot: 1000*task_idx + s.  Association: 10**5 + 100*mode_idx + s.
Forced: 10**6 + 1000*mode_idx + 10*round + k.  Every row is flushed per task.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from loguru import logger

from .catalogue import TASK_ORDER, TASKS, all_modes
from .prompts import build_association, build_baseline, build_forced, render_chat

BASE_SEED = 20261020
MODEL_ID = "Qwen/Qwen3-8B-FP8"
FENCE_RE = re.compile(r"```(?:python|py|Python)?[ \t]*\n(.*?)```", re.S)


def decoding_dict(max_tokens: int) -> dict:
    return {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0,
            "max_tokens": max_tokens, "thinking": False}


def make_llm(model_id: str, max_num_seqs: int, gpu_util: float):
    # No C compiler on this machine -> Triton (torch.compile, Triton FP8 GEMMs) cannot build its driver module.
    # Eager mode + vLLM's precompiled FP8 Marlin kernels (weight-only FP8, bf16 activations) need no Triton.
    os.environ.setdefault("VLLM_TEST_FORCE_FP8_MARLIN", "1")
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")  # vLLM's logprob-rank op is torch.compile'd (Inductor -> Triton)
    from vllm import LLM
    t0 = time.time()
    llm = LLM(model=model_id, gpu_memory_utilization=gpu_util, max_model_len=2048, max_num_seqs=max_num_seqs,
              enable_prefix_caching=True, generation_config="vllm", seed=BASE_SEED, enforce_eager=True)
    logger.info(f"vLLM engine up in {time.time() - t0:.0f}s (model={model_id}, max_num_seqs={max_num_seqs}, util={gpu_util})")
    return llm


def _sp(seed: int, max_tokens: int, stop_ids: list[int]):
    from vllm import SamplingParams
    return SamplingParams(temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, repetition_penalty=1.0,
                          presence_penalty=0.0, frequency_penalty=0.0, max_tokens=max_tokens, logprobs=0,
                          seed=seed, stop_token_ids=stop_ids)


def run_batch(llm, tok, reqs: list[dict], model_id: str, out_path: Path, prompt_log: Path) -> list[dict]:
    """reqs: dicts with task, condition, mode, paraphrase_id, sample_id, seed, user_text, max_tokens."""
    stop_ids = [tok.convert_tokens_to_ids("<|im_end|>"), tok.convert_tokens_to_ids("<|endoftext|>")]
    prompts, sps = [], []
    for r in reqs:
        chat = render_chat(tok, r["user_text"])
        ids = tok(chat, add_special_tokens=False)["input_ids"]
        r["prompt_token_ids"] = ids
        prompts.append({"prompt_token_ids": ids})
        sps.append(_sp(r["seed"], r["max_tokens"], stop_ids))
    t0 = time.time()
    outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
    dt = time.time() - t0
    rows = []
    n_tok = 0
    with out_path.open("a") as f, prompt_log.open("a") as pf:
        for r, o in zip(reqs, outs):
            c = o.outputs[0]
            lps = []
            if c.logprobs is not None:
                for tid, d in zip(c.token_ids, c.logprobs):
                    lps.append(float(d[tid].logprob))
            n_tok += len(c.token_ids)
            row = {"task": r["task"], "condition": r["condition"], "template": None, "mode": r.get("mode"),
                   "paraphrase_id": r.get("paraphrase_id"), "round": r.get("round"), "attempt_idx": r.get("attempt_idx"),
                   "sample_id": r["sample_id"], "seed": r["seed"], "model": model_id,
                   "decoding": decoding_dict(r["max_tokens"]), "text": c.text, "token_ids": list(c.token_ids),
                   "sum_logprob": float(sum(lps)) if lps else None, "token_logprobs": lps,
                   "finish_reason": c.finish_reason, "n_prompt_tokens": len(r["prompt_token_ids"])}
            f.write(json.dumps(row) + "\n")
            pf.write(json.dumps({"sample_id": r["sample_id"], "condition": r["condition"], "task": r["task"],
                                 "user_text": r["user_text"]}) + "\n")
            rows.append(row)
    logger.info(f"  generated {len(reqs)} seqs, {n_tok} tokens in {dt:.1f}s ({n_tok / max(dt, 1e-9):.0f} tok/s, "
                f"{dt / max(len(reqs), 1):.2f}s/seq)")
    return rows


def extraction_rate(rows: list[dict]) -> float:
    ok = sum(1 for r in rows if FENCE_RE.search(r["text"] or ""))
    return ok / max(len(rows), 1)


def pilot_reqs(task: str, n: int, start: int = 0) -> list[dict]:
    ti = TASK_ORDER.index(task)
    return [{"task": task, "condition": "baseline", "mode": None, "paraphrase_id": None,
             "sample_id": f"{task}:pilot:{s}", "seed": BASE_SEED + 1000 * ti + s,
             "user_text": build_baseline(task), "max_tokens": 1024} for s in range(start, n)]


def assoc_reqs(task: str, n: int) -> list[dict]:
    reqs = []
    for mi, (t, m) in enumerate(all_modes()):
        if t != task:
            continue
        for s in range(n):
            reqs.append({"task": t, "condition": "association", "mode": m, "paraphrase_id": None,
                         "sample_id": f"{t}:assoc:{m}:{s}", "seed": BASE_SEED + 10**5 + 100 * mi + s,
                         "user_text": build_association(t, m), "max_tokens": 96})
    return reqs


def forced_reqs(task: str, rounds: range, paraphrases: list[int], modes: list[str] | None = None) -> list[dict]:
    reqs = []
    for mi, (t, m) in enumerate(all_modes()):
        if t != task or (modes is not None and m not in modes):
            continue
        for r in rounds:
            for k in paraphrases:
                kk = k if k >= 0 else 9  # descriptive variant uses slot 9 of the seed grid (never a template id here)
                reqs.append({"task": t, "condition": "forced", "mode": m, "paraphrase_id": k, "round": r,
                             "attempt_idx": r * len(paraphrases) + paraphrases.index(k),
                             "sample_id": f"{t}:forced:{m}:r{r}:k{k}", "seed": BASE_SEED + 10**6 + 1000 * mi + 10 * r + kk,
                             "user_text": build_forced(t, m, k), "max_tokens": 1024})
    return reqs


def job_a(root: Path, model_id: str, max_num_seqs: int, gpu_util: float, n_pilot: int, n_assoc: int,
          forced_rounds: int, paraphrases: list[int]) -> None:
    data = root / "data"
    data.mkdir(exist_ok=True)
    plog = root / "logs" / "prompts_rendered.jsonl"
    llm = make_llm(model_id, max_num_seqs, gpu_util)
    tok = llm.get_tokenizer()
    # rendered example per prompt type
    ex = {"baseline": render_chat(tok, build_baseline("T03")),
          "forced": render_chat(tok, build_forced("T03", "quickselect", 0)),
          "association": render_chat(tok, build_association("T03", "full_sort"))}
    (root / "logs" / "rendered_examples.json").write_text(json.dumps(ex, indent=1))
    for k, v in ex.items():
        assert v.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"), f"bad chat rendering for {k}: {v[-80:]!r}"
    logger.info("chat rendering check passed (assistant header + empty think block)")
    sp = _sp(0, 1024, [])
    logger.info(f"effective SamplingParams: {sp}")
    (root / "logs" / "effective_sampling_params.txt").write_text(str(sp))

    pilot_path = data / "samples_pilot_raw.jsonl"
    # --- mini gate: 5 + 5 pilot generations for the first two tasks ---
    done = {}
    if pilot_path.exists():
        for line in pilot_path.open():
            r = json.loads(line)
            done[r["sample_id"]] = r
    t0 = time.time()
    mini = [q for t in TASK_ORDER[:2] for q in pilot_reqs(t, 5) if q["sample_id"] not in done]
    if mini:
        rows = run_batch(llm, tok, mini, model_id, pilot_path, plog)
        rate = extraction_rate(rows)
        logger.info(f"MINI GATE: code-block extraction {rate:.2f} on {len(rows)} pilot generations "
                    f"({time.time() - t0:.1f}s)")
        if rate < 0.9:
            raise RuntimeError(f"mini gate failed: extraction rate {rate:.2f} < 0.9")
        for r in rows:
            done[r["sample_id"]] = r
    # --- (a) pilot ---
    for t in TASK_ORDER:
        reqs = [q for q in pilot_reqs(t, n_pilot) if q["sample_id"] not in done]
        if not reqs:
            continue
        t1 = time.time()
        logger.info(f"pilot {t}: {len(reqs)} requests")
        run_batch(llm, tok, reqs, model_id, pilot_path, plog)
        logger.info(f"pilot {t} done in {time.time() - t1:.0f}s; elapsed job {time.time() - t0:.0f}s")
    # --- (b) association ---
    assoc_path = data / "association_raw.jsonl"
    adone = set()
    if assoc_path.exists():
        adone = {json.loads(l)["sample_id"] for l in assoc_path.open()}
    for t in TASK_ORDER:
        reqs = [q for q in assoc_reqs(t, n_assoc) if q["sample_id"] not in adone]
        if reqs:
            logger.info(f"association {t}: {len(reqs)} requests")
            run_batch(llm, tok, reqs, model_id, assoc_path, plog)
    logger.info(f"association done; elapsed job {time.time() - t0:.0f}s")
    # --- (c) forced round 1 ---
    forced_path = data / "samples_forced_raw.jsonl"
    fdone = set()
    if forced_path.exists():
        fdone = {json.loads(l)["sample_id"] for l in forced_path.open()}
    for t in TASK_ORDER:
        reqs = [q for q in forced_reqs(t, range(forced_rounds), paraphrases) if q["sample_id"] not in fdone]
        if reqs:
            t1 = time.time()
            logger.info(f"forced {t}: {len(reqs)} requests")
            run_batch(llm, tok, reqs, model_id, forced_path, plog)
            logger.info(f"forced {t} done in {time.time() - t1:.0f}s; elapsed job {time.time() - t0:.0f}s")
    logger.info(f"JOB A COMPLETE in {time.time() - t0:.0f}s")


def job_c(root: Path, model_id: str, max_num_seqs: int, gpu_util: float, plan_path: Path) -> None:
    """Forced top-ups: plan file lists {task, mode, rounds:[...], paraphrases:[...]} entries."""
    plan = json.loads(plan_path.read_text())
    llm = make_llm(model_id, max_num_seqs, gpu_util)
    tok = llm.get_tokenizer()
    plog = root / "logs" / "prompts_rendered.jsonl"
    forced_path = root / "data" / "samples_forced_raw.jsonl"
    fdone = {json.loads(l)["sample_id"] for l in forced_path.open()} if forced_path.exists() else set()
    for t in TASK_ORDER:
        entries = [e for e in plan if e["task"] == t]
        reqs = []
        for e in entries:
            reqs += [q for q in forced_reqs(t, range(e["rounds"][0], e["rounds"][1]), e["paraphrases"], [e["mode"]])
                     if q["sample_id"] not in fdone]
        if reqs:
            logger.info(f"top-up {t}: {len(reqs)} requests")
            run_batch(llm, tok, reqs, model_id, forced_path, plog)
    logger.info("JOB C COMPLETE")


def job_d(root: Path, model_id: str, max_num_seqs: int, gpu_util: float, tasks: list[str], n: int) -> None:
    llm = make_llm(model_id, max_num_seqs, gpu_util)
    tok = llm.get_tokenizer()
    plog = root / "logs" / "prompts_rendered_llama.jsonl"
    out = root / "data" / "samples_llama_pilot_raw.jsonl"
    for t in tasks:
        reqs = pilot_reqs(t, n)
        for q in reqs:
            q["sample_id"] = q["sample_id"].replace(":pilot:", ":llama_pilot:")
        # Llama has no think block: render without enable_thinking
        stop_ids = [tok.convert_tokens_to_ids("<|eot_id|>")]
        from vllm import SamplingParams  # noqa: F401
        prompts, sps = [], []
        for q in reqs:
            chat = tok.apply_chat_template([{"role": "user", "content": q["user_text"]}], tokenize=False,
                                           add_generation_prompt=True)
            q["prompt_token_ids"] = tok(chat, add_special_tokens=False)["input_ids"]
            prompts.append({"prompt_token_ids": q["prompt_token_ids"]})
            sps.append(_sp(q["seed"], 1024, stop_ids))
        outs = llm.generate(prompts, sampling_params=sps, use_tqdm=False)
        with out.open("a") as f:
            for q, o in zip(reqs, outs):
                c = o.outputs[0]
                f.write(json.dumps({"task": t, "condition": "baseline", "template": None, "paraphrase_id": None,
                                    "sample_id": q["sample_id"], "seed": q["seed"], "model": model_id,
                                    "decoding": decoding_dict(1024), "text": c.text, "finish_reason": c.finish_reason}) + "\n")
        logger.info(f"llama pilot {t}: {len(reqs)} done")
    logger.info("JOB D COMPLETE")


def set_cache_env(root: Path) -> None:
    """Keep compiler caches inside the workspace (never outside it)."""
    os.environ.setdefault("VLLM_NO_USAGE_STATS", "1")  # vLLM telemetry would otherwise write ~/.config/vllm/
    os.environ.setdefault("DO_NOT_TRACK", "1")
    cache = root / ".cache"
    for k, sub in [("VLLM_CACHE_ROOT", "vllm"), ("TRITON_CACHE_DIR", "triton"), ("TORCHINDUCTOR_CACHE_DIR", "inductor"),
                   ("XDG_CACHE_HOME", "xdg"), ("FLASHINFER_WORKSPACE_BASE", "flashinfer")]:
        os.environ.setdefault(k, str(cache / sub))
        (cache / sub).mkdir(parents=True, exist_ok=True)
