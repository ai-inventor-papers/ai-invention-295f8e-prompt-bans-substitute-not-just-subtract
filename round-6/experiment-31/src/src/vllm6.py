#!/usr/bin/env python3
"""vLLM bf16 phases (plan S2 instruct, S3 base): UNHOOKED rows only, raw text, no labels read.

Per-request seed = int(sha256('iter6|panelI|vllm|'+unit+'|'+w+'|'+k)[:8], 16) (cfg6.vllm_seed); top_p 1, top_k off,
T as listed. Instruct: forced (5 wordings x 5 seeds per mode), twin T1.0 k 10..39 and T1.3 k 10..29 (the T1.3 rows reuse
the T1.0 seeds of the same slot ids), association (20 per mode, 64 tokens). Base: chat twin k 0..39 (200), plain k
0..99 (100), base intents (W1..W5 x k 0..5, 48 tokens, stop at newline). Program = the first fenced block (chat) or the
docstring header + body up to the closing fence (plain).
Rows -> data/raw_vllm.jsonl (resumable by (unit, arm, template, slot, model_tag)); timing -> results/timing.jsonl.
Usage: python src/vllm6.py --phase instruct|base --units I1,I2 [--deadline-min 60] [--limit N]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import (BASE_ID, BASE_REVISION, ENDOFTEXT, IM_END, IM_START, MAX_NEW, MAX_NEW_ASSOC, MAX_NEW_INTENT,  # noqa
                  MODEL_ID, MODEL_REVISION, N_ASSOC, N_FORCED_SEEDS, PRECISION, RAW, SLOTS, TEMPLATE_IDS, TIMING,
                  FORCED_WORDINGS, append_jsonl, model_path, read_jsonl, setup_logging, utc_now, vllm_seed)
from prompts6 import load_prompts  # noqa: E402
from units_spec6 import UNITS  # noqa: E402

STOP_IDS = [IM_END, ENDOFTEXT, IM_START]


def requests_instruct(u: str, pr: dict[str, dict]) -> list[dict[str, Any]]:
    out = []
    for m in UNITS[u]["modes"]:
        for f in FORCED_WORDINGS:
            for k in range(N_FORCED_SEEDS):
                out.append({"unit": u, "arm": f"FORCED_{m}", "template": f, "slot": k, "T": 1.0, "kind": "code",
                            "pid": f"{u}|forced|{m}|{f}", "seed_key": (u, f"forced:{m}:{f}", k)})
    for w in TEMPLATE_IDS:
        for k in SLOTS["vllm_t10"]:
            out.append({"unit": u, "arm": "TWIN", "template": w, "slot": k, "T": 1.0, "kind": "code",
                        "pid": f"{u}|twin|-|{w}", "seed_key": (u, w, k)})
    for w in TEMPLATE_IDS:
        for k in SLOTS["vllm_t13"]:
            out.append({"unit": u, "arm": "TWIN13", "template": w, "slot": k, "T": 1.3, "kind": "code",
                        "pid": f"{u}|twin|-|{w}", "seed_key": (u, w, k)})
    for m in UNITS[u]["modes"]:
        for k in range(N_ASSOC):
            out.append({"unit": u, "arm": f"ASSOC_{m}", "template": "ASSOC", "slot": k, "T": 1.0, "kind": "assoc",
                        "pid": f"{u}|assoc|{m}|ASSOC", "seed_key": (u, f"assoc:{m}", k)})
    return out


def requests_base(u: str, pr: dict[str, dict]) -> list[dict[str, Any]]:
    out = []
    for w in TEMPLATE_IDS:
        for k in SLOTS["base_chat"]:
            out.append({"unit": u, "arm": "BASE", "template": w, "slot": k, "T": 1.0, "kind": "base_code",
                        "pid": f"{u}|twin|-|{w}", "seed_key": (u, w, k)})
    for k in SLOTS["plain"]:
        out.append({"unit": u, "arm": "PLAIN", "template": "PLAIN", "slot": k, "T": 1.0, "kind": "plain",
                    "pid": f"{u}|plain|-|PLAIN", "seed_key": (u, "PLAIN", k)})
    for w in TEMPLATE_IDS:
        for k in SLOTS["intent"]:
            out.append({"unit": u, "arm": "BINTENT", "template": w, "slot": k, "T": 1.0, "kind": "intent",
                        "pid": f"{u}|intent|-|{w}", "seed_key": (u, f"intent:{w}", k)})
    return out


def sampling_params(rq: dict[str, Any]):
    from vllm import SamplingParams

    seed = vllm_seed(*rq["seed_key"])
    common = dict(temperature=rq["T"], top_p=1.0, top_k=-1, min_p=0.0, seed=seed, skip_special_tokens=True)
    if rq["kind"] == "code":
        return SamplingParams(max_tokens=MAX_NEW, stop=["\n```\n"], include_stop_str_in_output=True, **common)
    if rq["kind"] == "assoc":
        return SamplingParams(max_tokens=MAX_NEW_ASSOC, **common)
    if rq["kind"] == "base_code":
        return SamplingParams(max_tokens=MAX_NEW, stop=["\n```\n"], stop_token_ids=STOP_IDS,
                              include_stop_str_in_output=True, **common)
    if rq["kind"] == "plain":
        return SamplingParams(max_tokens=MAX_NEW, stop=["\n```"], stop_token_ids=STOP_IDS,
                              include_stop_str_in_output=True, **common)
    if rq["kind"] == "intent":
        return SamplingParams(max_tokens=MAX_NEW_INTENT, stop=["\n"], stop_token_ids=STOP_IDS, **common)
    raise ValueError(rq["kind"])


def make_llm(model_tag: str, eager: bool = False, max_len: int = 2560, util: float = 0.95):
    from vllm import LLM

    mid, rev = (MODEL_ID, MODEL_REVISION) if model_tag == "instruct" else (BASE_ID, BASE_REVISION)
    path = model_path(mid, rev)
    kw: dict[str, Any] = dict(model=path, tokenizer=path, dtype="bfloat16", gpu_memory_utilization=util,
                              max_model_len=max_len, seed=0, enable_prefix_caching=True, generation_config="vllm")
    if eager:
        kw["enforce_eager"] = True
    t0 = time.time()
    llm = LLM(**kw)
    logger.info(f"vLLM {mid}@{rev[:8]} ready in {time.time() - t0:.0f}s (eager={eager}, max_len={max_len})")
    return llm, mid, rev


def run_phase(phase: str, units: list[str], deadline: float | None, limit: int | None, eager: bool) -> None:
    import vllm
    from vllm.inputs import TokensPrompt

    model_tag = "instruct" if phase == "instruct" else "base"
    pr = load_prompts()
    done = {(r["unit"], r["arm"], r["template"], int(r["slot"]), r["model_tag"]) for r in read_jsonl(RAW)}
    try:
        llm, mid, rev = make_llm(model_tag, eager=eager)
    except Exception as e:  # noqa: BLE001 - plan fallback: eager, shorter context, higher utilisation
        logger.error(f"vLLM start failed ({type(e).__name__}: {str(e)[:300]}); retrying with the fallback settings")
        llm, mid, rev = make_llm(model_tag, eager=True, max_len=1792, util=0.97)
    for u in units:
        if deadline is not None and time.time() > deadline:
            logger.warning(f"deadline reached before unit {u}; remaining units dropped (clock)")
            break
        reqs = requests_instruct(u, pr) if phase == "instruct" else requests_base(u, pr)
        reqs = [r for r in reqs if (r["unit"], r["arm"], r["template"], r["slot"], model_tag) not in done]
        if limit:
            reqs = reqs[:limit]
        if not reqs:
            continue
        t0 = time.time()
        prompts = [TokensPrompt(prompt_token_ids=pr[r["pid"]]["ids"]) for r in reqs]
        params = [sampling_params(r) for r in reqs]
        outs = llm.generate(prompts, params, use_tqdm=False)
        rows = []
        ntok = 0
        for r, o in zip(reqs, outs):
            c = o.outputs[0]
            ntok += len(c.token_ids)
            p = pr[r["pid"]]
            rows.append({"unit": u, "arm": r["arm"], "template": r["template"], "slot": r["slot"],
                         "model_tag": model_tag, "model": mid, "model_revision": rev, "precision": PRECISION,
                         "engine": f"vllm-{vllm.__version__}", "temperature": r["T"], "top_p": 1.0, "top_k": None,
                         "thinking": False, "seed": vllm_seed(*r["seed_key"]), "prompt_pid": r["pid"],
                         "prompt_sha256": p["prompt_sha256"], "kind": r["kind"], "text": c.text,
                         "token_ids": list(c.token_ids), "n_tokens": len(c.token_ids),
                         "finish_reason": c.finish_reason, "stop_reason": str(c.stop_reason), "utc": utc_now()})
        append_jsonl(RAW, rows)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"stage": f"vllm_{phase}", "unit": u, "n_requests": len(reqs), "n_tokens": ntok,
                               "seconds": dt, "tok_per_s": ntok / max(dt, 1e-6), "utc": utc_now()}])
        logger.info(f"{phase} {u}: {len(reqs)} requests, {ntok} tokens in {dt:.0f}s ({ntok / max(dt, 1e-6):.0f} tok/s)")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["instruct", "base"], required=True)
    ap.add_argument("--units", required=True)
    ap.add_argument("--deadline-min", type=float, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--eager", action="store_true")
    a = ap.parse_args()
    setup_logging(f"vllm_{a.phase}")
    dl = time.time() + 60 * a.deadline_min if a.deadline_min else None
    run_phase(a.phase, a.units.split(","), dl, a.limit, a.eager)


if __name__ == "__main__":
    main()
