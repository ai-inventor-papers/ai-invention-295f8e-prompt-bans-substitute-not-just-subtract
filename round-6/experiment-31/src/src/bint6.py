#!/usr/bin/env python3
"""BINT knob (plan S7; a knob only, never enters L1): the instruct model codes from the twin prompt + SPEC +
' Planned approach: <base intent>' for slot (w, k), k = 0..5 (N 30 per unit; the clock rule may cut to k 0..3, N 20).
Each slot has its own prompt (its own intent sentence), so the rows are generated on vLLM bf16 (unhooked) with the
per-request seed int(sha256('iter6|panelI|vllm|'+unit+'|bint:'+w+'|'+k)[:8], 16) instead of the HF CRN engine (whose
batches must share one prompt). Rows -> data/raw_vllm.jsonl (arm 'BINT'); prompts -> data/prompts_bint.jsonl.
Usage: python src/bint6.py --units I1,... [--n-slots 6]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import (DATA_DIR, MAX_NEW, MODEL_ID, MODEL_REVISION, PRECISION, RAW, TEMPLATE_IDS, TIMING, append_jsonl,  # noqa
                  model_path, read_jsonl, setup_logging, utc_now, vllm_seed, write_jsonl)
from prompts6 import load_prompts, render_bint  # noqa: E402

PROMPTS_BINT = DATA_DIR / "prompts_bint.jsonl"


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--n-slots", type=int, default=6)
    a = ap.parse_args()
    setup_logging("bint6")
    import vllm
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    path = model_path(MODEL_ID, MODEL_REVISION)
    tok = AutoTokenizer.from_pretrained(path)
    pr = load_prompts()
    intents = {(r["unit"], r["template"], int(r["slot"])): r["text"].strip() for r in read_jsonl(RAW)
               if r["arm"] == "BINTENT"}
    done = {(r["unit"], r["template"], int(r["slot"])) for r in read_jsonl(RAW) if r["arm"] == "BINT"}
    reqs, prompts = [], []
    for u in a.units.split(","):
        for w in TEMPLATE_IDS:
            for k in range(a.n_slots):
                if (u, w, k) in done:
                    continue
                it = intents.get((u, w, k), "")
                it = it.split("\n")[0].strip() or "a correct approach"
                row = render_bint(tok, u, w, k, it, pr[f"{u}|twin|-|{w}"])
                prompts.append(row)
                reqs.append((u, w, k, row))
    write_jsonl(PROMPTS_BINT, read_jsonl(PROMPTS_BINT) + prompts)
    if not reqs:
        logger.info("nothing to do")
        return
    t0 = time.time()
    llm = LLM(model=path, tokenizer=path, dtype="bfloat16", gpu_memory_utilization=0.92, max_model_len=2560, seed=0,
              enable_prefix_caching=True, generation_config="vllm", enforce_eager=True)
    params = [SamplingParams(temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, seed=vllm_seed(u, f"bint:{w}", k),
                             max_tokens=MAX_NEW, stop=["\n```\n"], include_stop_str_in_output=True)
              for u, w, k, _ in reqs]
    outs = llm.generate([TokensPrompt(prompt_token_ids=r["ids"]) for *_, r in reqs], params, use_tqdm=False)
    rows = []
    for (u, w, k, r), o in zip(reqs, outs):
        c = o.outputs[0]
        rows.append({"unit": u, "arm": "BINT", "template": w, "slot": k, "model_tag": "instruct", "model": MODEL_ID,
                     "model_revision": MODEL_REVISION, "precision": PRECISION, "engine": f"vllm-{vllm.__version__}",
                     "temperature": 1.0, "top_p": 1.0, "top_k": None, "thinking": False,
                     "seed": vllm_seed(u, f"bint:{w}", k), "prompt_pid": r["pid"], "prompt_sha256": r["prompt_sha256"],
                     "kind": "code", "intent": r["intent"], "text": c.text, "token_ids": list(c.token_ids),
                     "n_tokens": len(c.token_ids), "finish_reason": c.finish_reason, "stop_reason": str(c.stop_reason),
                     "utc": utc_now()})
    append_jsonl(RAW, rows)
    append_jsonl(TIMING, [{"stage": "vllm_bint", "n_requests": len(reqs), "seconds": time.time() - t0,
                           "utc": utc_now()}])
    logger.info(f"BINT: {len(rows)} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
