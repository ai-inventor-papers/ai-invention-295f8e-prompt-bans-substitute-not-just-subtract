"""GPU job B: log-likelihood scoring of forced programs with vLLM prompt logprobs.

Each forced attempt is scored as its *scrubbed* response text, tokenized separately and appended after the
rendered chat prompt, followed by <|im_end|>:  l(i | c) = sum over response tokens of log p(token | prefix).
Prompts c: the baseline (SPEC alone) and every forced paraphrase F_j^k that generated attempts for mode j.
vLLM computes prompt logprobs without prefix caching, so every request is a full prefill.

Consistency checks (before the full run):
 (a) 20 unscrubbed programs: scorer sum on the sampled token ids, and on the re-tokenized text, under the generating
     paraphrase vs the sampler's summed token logprobs; pass if within max(1 nat, 1%) for >= 19/20;
 (b) batch-composition invariance (replaces the plan's cache-reuse check, which has no analogue here): single-request
     vs in-batch scores within 0.1 nat;
 (c) a shuffled-token control scores >= 50 nats lower;
 (d) re-running the same batch reproduces scores within 0.05 nat.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

from loguru import logger

from .catalogue import TASK_ORDER, TASKS
from .gen_vllm import BASE_SEED
from .harness import extract_code
from .prompts import build_baseline, build_forced, render_chat
from .scrub import scrub_response


def make_scorer(model_id: str, gpu_util: float = 0.85):
    os.environ.setdefault("VLLM_TEST_FORCE_FP8_MARLIN", "1")
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
    from vllm import LLM
    llm = LLM(model=model_id, gpu_memory_utilization=gpu_util, max_model_len=2048, max_num_seqs=64,
              max_num_batched_tokens=2048, enable_prefix_caching=True, generation_config="vllm", seed=BASE_SEED,
              enforce_eager=True)
    return llm


def score_ids(llm, reqs: list[tuple[list[int], int]]) -> list[tuple[float, int]]:
    """reqs: [(full_ids, n_prompt)] -> [(sum logprob of tokens at positions >= n_prompt, n_scored)]"""
    from vllm import SamplingParams
    sp = SamplingParams(max_tokens=1, temperature=1.0, prompt_logprobs=0, detokenize=False)
    outs = llm.generate([{"prompt_token_ids": ids} for ids, _ in reqs], sampling_params=sp, use_tqdm=False)
    res = []
    for (ids, npr), o in zip(reqs, outs):
        pl = o.prompt_logprobs
        tot = 0.0
        for pos in range(npr, len(ids)):
            d = pl[pos]
            tot += float(d[ids[pos]].logprob)
        res.append((tot, len(ids) - npr))
    return res


def build_program_table(root: Path, tok) -> list[dict]:
    """All forced attempts -> scrubbed response, token ids."""
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    rows = [json.loads(l) for l in (root / "data" / "samples_forced_raw.jsonl").open()]
    out = []
    for r in rows:
        code = extract_code(r["text"])
        if code is None:
            continue
        s_text, s_code, info = scrub_response(r["text"], code)
        ids = tok(s_text, add_special_tokens=False)["input_ids"] + [im_end]
        out.append({"program_id": r["sample_id"], "task": r["task"], "mode": r["mode"], "paraphrase_id": r["paraphrase_id"],
                    "scrubbed_text": s_text, "scrub_ok": info["ok"], "resp_ids": ids, "raw": r})
    return out


def prompt_ids(tok, task: str, prompt_id: str, mode: str | None) -> list[int]:
    if prompt_id == "baseline":
        txt = build_baseline(task)
    else:
        txt = build_forced(task, mode, int(prompt_id[1:]))
    return tok(render_chat(tok, txt), add_special_tokens=False)["input_ids"]


def consistency_checks(llm, tok, progs: list[dict]) -> dict:
    rng = random.Random(BASE_SEED)
    sample = rng.sample([p for p in progs if p["raw"]["finish_reason"] == "stop"], 20)
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    reqs_a, reqs_t = [], []
    for p in sample:
        pids = prompt_ids(tok, p["task"], f"F{p['paraphrase_id']}", p["mode"])
        reqs_a.append((pids + p["raw"]["token_ids"], len(pids)))
        retok = tok(p["raw"]["text"], add_special_tokens=False)["input_ids"] + [im_end]
        reqs_t.append((pids + retok, len(pids)))
    sa = score_ids(llm, reqs_a)
    st = score_ids(llm, reqs_t)
    rows = []
    for p, (a, na), (t, nt) in zip(sample, sa, st):
        ref = p["raw"]["sum_logprob"]
        tol = max(1.0, 0.01 * abs(ref))
        rows.append({"program_id": p["program_id"], "sampler_sum": ref, "scorer_same_ids": a, "scorer_retokenized": t,
                     "n_tokens": na, "retok_len_equal": na == nt, "ok_same_ids": abs(a - ref) <= tol,
                     "ok_retokenized": abs(t - ref) <= tol})
    n_ok = sum(r["ok_same_ids"] for r in rows)
    n_ok_t = sum(r["ok_retokenized"] for r in rows)
    # (b) single vs batch
    single = [score_ids(llm, [q])[0][0] for q in reqs_a[:5]]
    b_ok = all(abs(s - x[0]) <= 0.1 for s, x in zip(single, sa[:5]))
    # (c) shuffled control
    ctrl = []
    for (ids, npr), (a, _) in zip(reqs_a[:10], sa[:10]):
        resp = ids[npr:-1]
        sh = resp[:]
        rng.shuffle(sh)
        ctrl.append((ids[:npr] + sh + [ids[-1]], npr))
    sc = score_ids(llm, ctrl)
    c_rows = [{"orig": a, "shuffled": s, "gap": a - s} for (a, _), (s, _) in zip(sa[:10], sc)]
    c_ok = all(r["gap"] >= 50 or len(reqs_a[i][0]) - reqs_a[i][1] < 25 for i, r in enumerate(c_rows))
    # (d) rerun
    sa2 = score_ids(llm, reqs_a)
    d_max = max(abs(x[0] - y[0]) for x, y in zip(sa, sa2))
    res = {"a_rows": rows, "a_pass_same_ids": n_ok >= 19, "a_n_ok_same_ids": n_ok, "a_n_ok_retokenized": n_ok_t,
           "a_pass_retokenized": n_ok_t >= 19, "b_single_vs_batch_ok": b_ok,
           "b_single_minus_batch": [s - x[0] for s, x in zip(single, sa[:5])],
           "c_shuffled_control": c_rows, "c_pass": c_ok, "d_rerun_max_abs_diff": d_max, "d_pass": d_max <= 0.05}
    return res


def job_b(root: Path, model_id: str, gpu_util: float, paraphrases: list[int], only_checks: bool = False) -> None:
    llm = make_scorer(model_id, gpu_util)
    tok = llm.get_tokenizer()
    progs = build_program_table(root, tok)
    logger.info(f"scoring table: {len(progs)} forced programs")
    chk_path = root / "results" / "scoring_consistency.json"
    if not chk_path.exists():
        t0 = time.time()
        chk = consistency_checks(llm, tok, progs)
        chk_path.write_text(json.dumps(chk, indent=1))
        logger.info(f"consistency checks in {time.time() - t0:.0f}s: (a) same-ids {chk['a_n_ok_same_ids']}/20, "
                    f"retokenized {chk['a_n_ok_retokenized']}/20; (b) {chk['b_single_vs_batch_ok']}; (c) {chk['c_pass']}; "
                    f"(d) max diff {chk['d_rerun_max_abs_diff']:.4f}")
        if not chk["a_pass_same_ids"]:
            raise RuntimeError("consistency check (a) failed: chat template / tokenization bug; scoring aborted")
    if only_checks:
        return
    out_path = root / "data" / "program_scores.jsonl"
    done = set()
    if out_path.exists():
        for l in out_path.open():
            r = json.loads(l)
            done.add((r["program_id"], r["prompt_id"]))
    pcache = {}
    order = {t: i for i, t in enumerate(TASK_ORDER)}
    progs.sort(key=lambda p: (order[p["task"]], p["program_id"]))
    # proposal components per mode = every forced prompt that generated attempts for that mode (exact mixture)
    comps = {}
    for p in progs:
        comps.setdefault((p["task"], p["mode"]), set()).add(p["paraphrase_id"])
    jobs = []
    for p in progs:
        for pid in ["baseline"] + [f"F{k}" for k in sorted(comps[(p["task"], p["mode"])])]:
            if (p["program_id"], pid) in done:
                continue
            key = (p["task"], pid, None if pid == "baseline" else p["mode"])
            if key not in pcache:
                pcache[key] = prompt_ids(tok, p["task"], pid, key[2])
            jobs.append((p, pid, pcache[key]))
    logger.info(f"{len(jobs)} scoring requests to run")
    stages = [10, 100, len(jobs)]
    i = 0
    t_all = time.time()
    while i < len(jobs):
        nxt = next((s for s in stages if s > i), len(jobs))
        nxt = min(max(nxt, i + 1), i + 1500, len(jobs))
        chunk = jobs[i:nxt]
        t0 = time.time()
        res = score_ids(llm, [(pi + p["resp_ids"], len(pi)) for p, _, pi in chunk])
        dt = time.time() - t0
        ntok = sum(len(pi) + len(p["resp_ids"]) for p, _, pi in chunk)
        with out_path.open("a") as f:
            for (p, pid, _), (lp, n) in zip(chunk, res):
                f.write(json.dumps({"task": p["task"], "program_id": p["program_id"], "mode": p["mode"],
                                    "prompt_id": pid, "logp_sum": lp, "n_tokens": n}) + "\n")
        i = nxt
        rate = ntok / max(dt, 1e-9)
        eta = (len(jobs) - i) / max(len(chunk) / max(dt, 1e-9), 1e-9)
        logger.info(f"scored {i}/{len(jobs)} ({len(chunk)} in {dt:.1f}s, {rate:.0f} tok/s); ETA {eta / 60:.1f} min")
    logger.info(f"JOB B COMPLETE in {time.time() - t_all:.0f}s")
