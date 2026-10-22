#!/usr/bin/env python3
"""Unhooked bf16 sampling with vLLM 0.11 (run ONLY with .venv_vllm/bin/python; no import of this repo's HF code, so
the HF pins in .venv are never perturbed). The two processes exchange JSONL only.

Input  (--requests): JSONL rows {"rid", "prompt_token_ids", "temperature", "max_tokens", "seed", "fence"} where fence
       is "bench" (stop at the first CLOSED ```python block, the exp22 HF rule), "plain" (stop at the first ``` of
       the generation: plain completions open the fence in the prompt) or null (association / intents).
Output (--out, appended): {"rid", "token_ids", "text", "n_tokens", "finish_reason" (fence | stop | length),
       "engine": "vllm", "vllm_version", "dtype": "bfloat16", "seed", "utc"}; rows already present are skipped
       (resumable).
FENCE STOP: a V1 AdapterLogitsProcessor (the exp18 veto pattern) -- after a step whose last generated id contains a
backtick, the generation so far is decoded; once the fence rule holds, every logit except <|im_end|> is set to -inf,
so the request ends exactly one token later with an EOS that is not part of the text (identical text to the HF
fence stop, which marks the row finished at the same point).
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor

IM_END = 151645
ENDOFTEXT = 151643
IM_START = 151644
BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
_TOK = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def fence_closed(text: str, kind: str) -> bool:
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
    if kind == "plain":
        return "```" in text
    return False


class _ReqFence:
    def __init__(self, kind: str, tok, tick: set[int]):
        self.kind, self.tok, self.tick = kind, tok, tick
        self.closed = False

    def __call__(self, output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
        if not self.closed and output_ids and output_ids[-1] in self.tick:
            txt = self.tok.decode(output_ids, skip_special_tokens=True)
            if fence_closed(txt, self.kind):
                self.closed = True
        if self.closed:
            keep = logits[IM_END].clone()
            logits.fill_(float("-inf"))
            logits[IM_END] = keep if torch.isfinite(keep) else 0.0
        return logits


class FenceStop(AdapterLogitsProcessor):
    """Per-request fence stop; requests whose extra_args carry no 'fence' get no processor."""

    def __init__(self, vllm_config, device, is_pin_memory):
        super().__init__(vllm_config, device, is_pin_memory)
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(vllm_config.model_config.tokenizer)
        self.tick = {i for i in range(len(self.tok)) if "`" in self.tok.decode([i])}

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(self, params):
        ea = getattr(params, "extra_args", None) or {}
        kind = ea.get("fence")
        if not kind:
            return None
        return _ReqFence(kind, self.tok, self.tick)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--requests", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-num-seqs", type=int, default=96)
    ap.add_argument("--gpu-mem", type=float, default=0.92)
    ap.add_argument("--chunk", type=int, default=2000)
    a = ap.parse_args()
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    reqs = [json.loads(l) for l in Path(a.requests).read_text().splitlines() if l.strip()]
    outp = Path(a.out)
    done = set()
    if outp.exists():
        for l in outp.read_text().splitlines():
            try:
                done.add(json.loads(l)["rid"])
            except (json.JSONDecodeError, KeyError):
                pass
    todo = [r for r in reqs if r["rid"] not in done]
    print(json.dumps({"event": "start", "n_requests": len(reqs), "todo": len(todo), "utc": utc_now()}), flush=True)
    if not todo:
        return
    t0 = time.time()
    llm = LLM(model=a.model, tokenizer=a.model, dtype="bfloat16", gpu_memory_utilization=a.gpu_mem,
              max_model_len=2048, max_num_seqs=a.max_num_seqs, enforce_eager=True, seed=0,
              enable_prefix_caching=True, generation_config="vllm", logits_processors=[FenceStop])
    print(json.dumps({"event": "loaded", "seconds": round(time.time() - t0, 1), "vllm": vllm.__version__}),
          flush=True)
    for i in range(0, len(todo), a.chunk):
        part = todo[i:i + a.chunk]
        prompts = [TokensPrompt(prompt_token_ids=r["prompt_token_ids"]) for r in part]
        params = [SamplingParams(n=1, temperature=float(r["temperature"]), top_p=1.0, top_k=-1, min_p=0.0,
                                 max_tokens=int(r["max_tokens"]), seed=int(r["seed"]), repetition_penalty=1.0,
                                 presence_penalty=0.0, frequency_penalty=0.0,
                                 stop_token_ids=[IM_END, ENDOFTEXT], skip_special_tokens=True,
                                 extra_args={"fence": r["fence"]} if r.get("fence") else None) for r in part]
        t1 = time.time()
        outs = llm.generate(prompts, params, use_tqdm=False)
        dt = time.time() - t1
        ntok = 0
        with open(outp, "a") as fh:
            for r, o in zip(part, outs):
                c = o.outputs[0]
                ids = [int(x) for x in c.token_ids]
                ntok += len(ids)
                text = c.text
                fr = c.finish_reason
                if r.get("fence") and fence_closed(text, r["fence"]):
                    fr = "fence"
                    if r["fence"] == "bench":
                        m = BENCH_FENCE.search(text)
                        text = text[:m.end()]
                    else:
                        text = text[:text.index("```") + 3]
                ids_out = [x for x in ids if x not in (IM_END, ENDOFTEXT)]
                fh.write(json.dumps({"rid": r["rid"], "token_ids": ids_out, "text": text, "n_tokens": len(ids_out),
                                     "finish_reason": fr, "engine": "vllm", "vllm_version": vllm.__version__,
                                     "dtype": "bfloat16", "seed": int(r["seed"]), "utc": utc_now()}) + "\n")
        print(json.dumps({"event": "chunk", "n": len(part), "seconds": round(dt, 1), "tok_per_s": round(ntok / dt),
                          "programs_per_h": round(3600 * len(part) / dt), "done": i + len(part),
                          "utc": utc_now()}), flush=True)


if __name__ == "__main__":
    main()
