"""vLLM generation (STEP 4). One model per process; staged 10 -> 100 -> full per arm.

  .venv/bin/python src/gen_vllm.py --phase A   # Qwen3-8B-Base: A1 base_tf:baseline, A2 base_chat:baseline, A3 base_tf:ban
  .venv/bin/python src/gen_vllm.py --phase B   # Qwen3-8B:      B1 instruct_chat:baseline, B2 instruct_tf:baseline
  .venv/bin/python src/gen_vllm.py --phase C   # Qwen3-8B:      C1 instruct_chat:ban (refuses without the PREDICT hash)
Raw samples -> runs/raw_<arm-tag>.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BAN_COND, MB, MI, PRED, RESULTS, RUNS, EOS_IDS, IM_START_ID, add_deviation, append_jsonl,  # noqa: E402
                    read_jsonl, setup_logging, sha256_file, stable_seed, time_log)
from extract import extract  # noqa: E402
from prompts import load_prompts  # noqa: E402

TF_STOPS = ['\nif __name__', '\n# Test', '\n# test', '\n# Example', '\nprint(', '\nassert ', '\n"""', '\n```',
            '<|endoftext|>', '\n\n\n\n']
BASE_CHAT_STOPS = ['<|im_end|>', '<|im_start|>', '<|endoftext|>']

# arm spec: (arm, template, kind, n_per_prompt, model)
PHASES = {
    "A": (MB, [("base_tf", "tf", "baseline", 20), ("base_chat", "chat", "baseline", 10), ("base_tf", "tf", "ban", 10)]),
    "B": (MI, [("instruct_chat", "chat", "baseline", 20), ("instruct_tf", "tf", "baseline", 10)]),
    "C": (MI, [("instruct_chat", "chat", "ban", 10)]),
    # power extension (fallback 3 for A1; logged deviation for A2): new chunks with new seeds, appended to the same files
    "A_EXT": (MB, [("base_tf", "tf", "baseline", 30), ("base_chat", "chat", "baseline", 30)]),
}
CHUNK = 10


def check_predict_commit() -> None:
    f = PRED / "predict_modal_ban.json"
    log = PRED / "hash_log.txt"
    if not f.exists() or not log.exists():
        raise SystemExit("PHASE C REFUSED: predictions/predict_modal_ban.json or hash_log.txt missing")
    h = sha256_file(f)
    entries = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    if not any(e.get("sha256") == h and e.get("file") == "predictions/predict_modal_ban.json" for e in entries):
        raise SystemExit("PHASE C REFUSED: prediction file does not match any committed hash")
    logger.info(f"PREDICT commit verified (sha256={h})")


def build_requests(phase: str, prompts: dict, model: str) -> list[dict]:
    reqs = []
    for arm, template, kind, n_per in PHASES[phase][1]:
        for task in ("t1", "t2"):
            cond = "baseline" if kind == "baseline" else BAN_COND[task]
            plist = prompts[template][task][kind][:10]  # P0..P9 or B0..B9
            for pi, p in enumerate(plist):
                for ch in range(n_per // CHUNK):
                    seed = stable_seed(arm, task, cond, p["id"], ch)
                    reqs.append({"arm": arm, "template": template, "task": task, "condition": cond,
                                 "prompt_id": p["id"], "paraphrase_id": pi, "chunk": ch, "seed": seed,
                                 "token_ids": p["token_ids"], "prompt_text": p["text"], "model": model,
                                 "arm_tag": f"{arm}__{kind}"})
    return reqs


def make_params(r: dict):
    from vllm import SamplingParams
    if r["template"] == "tf":
        stop, stop_ids = TF_STOPS, [151643]
    elif r["arm"].startswith("base"):
        stop, stop_ids = BASE_CHAT_STOPS, [151645, IM_START_ID, 151643]
    else:
        stop, stop_ids = [], list(EOS_IDS)
    return SamplingParams(n=CHUNK, temperature=1.0, top_p=1.0, top_k=0, min_p=0.0, repetition_penalty=1.0,
                          presence_penalty=0.0, frequency_penalty=0.0, max_tokens=1024, seed=r["seed"], stop=stop,
                          stop_token_ids=stop_ids, skip_special_tokens=False, include_stop_str_in_output=False,
                          ignore_eos=False)


def init_llm(model: str):
    from vllm import LLM
    attempts = [dict(gpu_memory_utilization=0.92, max_model_len=2048),
                dict(gpu_memory_utilization=0.92, max_model_len=1536),
                dict(gpu_memory_utilization=0.95, max_model_len=1536)]
    last = None
    for a in attempts:
        try:
            llm = LLM(model=model, dtype="bfloat16", max_num_seqs=int(os.environ.get("MAX_NUM_SEQS", "48")), seed=0,
                      enable_prefix_caching=True, enforce_eager=True, generation_config="vllm", **a)
            logger.info(f"vLLM engine up: {model} {a}")
            return llm, a
        except Exception as e:  # noqa: BLE001 - engine init raises assorted errors (OOM, ValueError)
            logger.error(f"vLLM init failed with {a}: {e!r}")
            last = e
            import gc
            gc.collect()
    raise RuntimeError(f"vLLM could not start: {last!r}")


def run_stage(llm, reqs: list[dict], stage: str) -> tuple[int, int, float]:
    from vllm.inputs import TokensPrompt
    if not reqs:
        return 0, 0, 0.0
    t0 = time.time()
    outs = llm.generate([TokensPrompt(prompt_token_ids=r["token_ids"]) for r in reqs],
                        [make_params(r) for r in reqs], use_tqdm=False)
    dt = time.time() - t0
    n_tok, n_s = 0, 0
    by_tag: dict[str, list[dict]] = {}
    for r, o in zip(reqs, outs):
        texts = [c.text for c in o.outputs]
        if len(texts) > 1 and len(set(texts)) == 1:
            logger.warning(f"all {len(texts)} samples identical for {r['arm_tag']} {r['task']} {r['prompt_id']}")
        for j, c in enumerate(o.outputs):
            n_tok += len(c.token_ids)
            n_s += 1
            row = {"task": r["task"], "arm": r["arm"], "template": r["template"], "condition": r["condition"],
                   "model": r["model"], "prompt_id": r["prompt_id"], "paraphrase_id": r["paraphrase_id"],
                   "sample_id": r["chunk"] * CHUNK + j, "seed": r["seed"], "child_index": j, "stage": stage,
                   "engine": "vllm", "text": c.text, "finish_reason": c.finish_reason,
                   "stop_reason": (str(c.stop_reason) if c.stop_reason is not None else None),
                   "n_tokens": len(c.token_ids)}
            by_tag.setdefault(r["arm_tag"], []).append(row)
    for tag, rows in by_tag.items():
        append_jsonl(RUNS / f"raw_{tag}.jsonl", rows)
    logger.info(f"[{stage}] {len(reqs)} requests, {n_s} samples, {n_tok} tokens in {dt:.1f}s "
                f"-> {n_tok / max(dt, 1e-9):.0f} tok/s, {dt / max(n_s, 1):.2f} s/sample")
    return n_s, n_tok, dt


def quick_stats(phase: str, prompts: dict) -> dict:
    stats = {}
    for arm, template, kind, _ in PHASES[phase][1]:
        rows = read_jsonl(RUNS / f"raw_{arm}__{kind}.jsonl")
        for task in ("t1", "t2"):
            rr = [r for r in rows if r["task"] == task]
            if not rr:
                continue
            ptext = {p["id"]: p["text"] for p in prompts[template][task][kind]}
            ok = sum(1 for r in rr if extract(r, ptext[r["prompt_id"]])[0] is not None)
            ln = sum(1 for r in rr if r["finish_reason"] == "length")
            stats[f"{arm}__{kind}__{task}"] = {"n": len(rr), "parse_rate": ok / len(rr), "length_cap_rate": ln / len(rr),
                                               "mean_tokens": sum(r["n_tokens"] for r in rr) / len(rr)}
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["A", "B", "C", "A_EXT"])
    ap.add_argument("--stages", default="10,100,full")
    args = ap.parse_args()
    setup_logging(f"gen_vllm_{args.phase}")
    if args.phase == "C":
        check_predict_commit()
    model, _ = PHASES[args.phase]
    prompts = load_prompts()
    reqs = build_requests(args.phase, prompts, model)
    # resume: skip requests already present on disk
    done = set()
    for arm, template, kind, _ in PHASES[args.phase][1]:
        for row in read_jsonl(RUNS / f"raw_{arm}__{kind}.jsonl"):
            done.add((row["arm"], row["condition"], row["task"], row["prompt_id"], row["sample_id"] // CHUNK))
    todo = [r for r in reqs if (r["arm"], r["condition"], r["task"], r["prompt_id"], r["chunk"]) not in done]
    logger.info(f"phase {args.phase}: {len(reqs)} requests ({len(reqs) * CHUNK} samples), {len(todo)} to do")
    time_log(f"gen_{args.phase}_start", n_requests=len(todo))
    if not todo:
        return
    llm, eng = init_llm(model)
    import vllm
    import torch
    sp = make_params(todo[0])
    meta = {"vllm": vllm.__version__, "torch": torch.__version__, "engine": eng,
            "max_num_seqs": int(os.environ.get("MAX_NUM_SEQS", "48")), "enforce_eager": True,
            "generation_config": "vllm (HF generation_config ignored)",
            "effective_sampling": {"temperature": sp.temperature, "top_p": sp.top_p, "top_k": sp.top_k,
                                   "min_p": sp.min_p, "repetition_penalty": sp.repetition_penalty,
                                   "max_tokens": sp.max_tokens}}
    assert sp.top_k in (0, -1) and sp.top_p == 1.0 and sp.temperature == 1.0, meta
    (RESULTS / f"gen_meta_{args.phase}.json").write_text(json.dumps(meta, indent=1))
    logger.info(f"effective sampling: {meta['effective_sampling']}")
    if eng.get("max_model_len") != 2048:
        add_deviation(f"vLLM max_model_len={eng.get('max_model_len')} in phase {args.phase}", "init OOM fallback")

    # staging: first chunk of every (arm, task); then up to 100 samples per (arm, task); then the rest
    groups: dict[tuple, list[dict]] = {}
    for r in todo:
        groups.setdefault((r["arm_tag"], r["task"]), []).append(r)
    stage_lists: list[list[dict]] = [[], [], []]
    for key, lst in groups.items():
        lst.sort(key=lambda r: (r["chunk"], r["paraphrase_id"]))
        stage_lists[0].extend(lst[:1])
        stage_lists[1].extend(lst[1:10])
        stage_lists[2].extend(lst[10:])
    names = ["10", "100", "full"] if args.phase != "A_EXT" else ["ext_10", "ext_100", "ext_full"]
    total_s, total_t = 0, 0.0
    for name, lst in zip(names, stage_lists):
        n_s, _, dt = run_stage(llm, lst, name)
        total_s += n_s
        total_t += dt
        st = quick_stats(args.phase, prompts)
        logger.info(f"after stage {name}: {json.dumps(st)}")
        (RESULTS / f"gen_stats_{args.phase}.json").write_text(json.dumps(st, indent=1))
        remaining = sum(len(x) for x in stage_lists[names.index(name) + 1:]) * CHUNK
        if n_s:
            logger.info(f"extrapolated time for remaining {remaining} samples: {remaining * dt / n_s / 60:.1f} min")
        if name == "10":
            for k, v in st.items():
                if v["parse_rate"] < 0.5:
                    logger.warning(f"GATE: parse rate {v['parse_rate']:.2f} < 0.5 for {k}")
    time_log(f"gen_{args.phase}_end", samples=total_s, seconds=round(total_t, 1))


if __name__ == "__main__":
    main()
