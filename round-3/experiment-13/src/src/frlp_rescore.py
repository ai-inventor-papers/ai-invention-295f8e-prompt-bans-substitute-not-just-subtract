#!/usr/bin/env python3
"""S2b(ii) descriptive FRLP rescoring on the fp32-activation path (post-commitment; no ban data involved).

Scorer: exp7's fp32-activation teacher-forced scorer (src/frlp_score.py), re-implemented here with the same numerics:
bf16-stored weights, every nn.Linear run with fp32 activations (weight upcast per call, TF32 tensor-core matmul),
fp32 embeddings, prompt prefix KV reused across a batch of right-padded responses, and target log-probs from an fp32
lm_head computed one vocabulary chunk at a time with TF32 disabled.  Gate before use: it must reproduce 5 stored exp7
program scores (body log-prob sums) within 0.05 nats.
Rescored: for every frozen exp11 FRLP set program (M_j <= 30 per mode, 12 tasks), l(program | baseline) and
l(program | F_k) for every forced prompt k that generated attempts of the mode (the exact mixture proposal); the
program is exp11's scrubbed response text tokenised separately and followed by <|im_end|>.  Cells are recomputed with
exp11's formulas (log q = logsumexp_k[log(n_k/N) + l(i|F_k)], w = l(i|base) - log q, L = logmeanexp w,
L_corr = L + log a, Kish ESS) and compared with exp11's FP8 (vLLM) values: per-cell differences and rank changes.
"""

from __future__ import annotations

import copy
import json
import math
import time
import types
from collections import Counter
from typing import Any

import numpy as np
import torch
from loguru import logger

from common import EXP7, EXP11, RESULTS, TASK_ORDER, bench_import, model_path, read_jsonl, write_json

FENCE_OPEN, FENCE_CLOSE = "```python\n", "```"


def _linear_fp32(self, x: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.linear(x.float(), self.weight.float(), None if self.bias is None else self.bias.float())


class Scorer:
    def __init__(self, token_budget: int = 4096, max_b: int = 16):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        mp = model_path()
        self.tok = AutoTokenizer.from_pretrained(mp)
        t0 = time.time()
        self.model = AutoModelForCausalLM.from_pretrained(mp, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                          device_map={"": 0}).eval()
        logger.info(f"HF model loaded in {time.time() - t0:.0f}s")
        self.dev = torch.device("cuda")
        self.budget, self.max_b = token_budget, max_b
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        self.vchunk, self.tchunk = 16384, 2048
        for mod in self.model.model.modules():
            if isinstance(mod, torch.nn.Linear):
                mod.forward = types.MethodType(_linear_fp32, mod)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    def embed(self, ids: torch.Tensor) -> torch.Tensor:
        return self.model.model.embed_tokens(ids).float()

    @torch.inference_mode()
    def target_logprobs(self, hv: torch.Tensor, tv: torch.Tensor) -> torch.Tensor:
        W = self.model.lm_head.weight
        V, N = W.shape[0], hv.shape[0]
        lse = torch.full((N,), -float("inf"), dtype=torch.float32, device=self.dev)
        tgt = torch.empty(N, dtype=torch.float32, device=self.dev)
        x = hv.float()
        prev = torch.backends.cuda.matmul.allow_tf32
        torch.backends.cuda.matmul.allow_tf32 = False
        for v0 in range(0, V, self.vchunk):
            Wc = W[v0:v0 + self.vchunk].float()
            for s in range(0, N, self.tchunk):
                lg = x[s:s + self.tchunk] @ Wc.T
                lse[s:s + self.tchunk] = torch.logaddexp(lse[s:s + self.tchunk], torch.logsumexp(lg, dim=-1))
                t = tv[s:s + self.tchunk]
                inside = (t >= v0) & (t < v0 + Wc.shape[0])
                if inside.any():
                    rows = torch.nonzero(inside).squeeze(1)
                    tgt[s + rows] = lg[rows, (t[rows] - v0)]
                del lg
            del Wc
        torch.backends.cuda.matmul.allow_tf32 = prev
        return tgt - lse

    @torch.inference_mode()
    def prefix(self, prompt_ids: list[int]):
        out = self.model.model(inputs_embeds=self.embed(torch.tensor([prompt_ids], device=self.dev)), use_cache=True)
        h_last = out.last_hidden_state[0, -1:].clone()
        return out.past_key_values, h_last

    @torch.inference_mode()
    def score_batch(self, cache, h_last, P: int, resps: list[list[int]]) -> list[np.ndarray]:
        B = len(resps)
        T = max(len(r) for r in resps)
        cb = copy.deepcopy(cache)
        if B > 1:
            cb.batch_repeat_interleave(B)
        inp = torch.full((B, max(1, T - 1)), self.pad, dtype=torch.long)
        tgt = torch.zeros((B, max(1, T - 1)), dtype=torch.long)
        mask = torch.zeros((B, max(1, T - 1)), dtype=torch.long)
        for i, r in enumerate(resps):
            n = len(r) - 1
            if n > 0:
                inp[i, :n] = torch.tensor(r[:-1])
                tgt[i, :n] = torch.tensor(r[1:])
                mask[i, :n] = 1
        inp, tgt, mask = inp.to(self.dev), tgt.to(self.dev), mask.to(self.dev)
        attn = torch.cat([torch.ones((B, P), dtype=torch.long, device=self.dev), mask], dim=1)
        cpos = torch.arange(P, P + inp.shape[1], device=self.dev)
        h = self.model.model(inputs_embeds=self.embed(inp), attention_mask=attn, past_key_values=cb,
                             cache_position=cpos, use_cache=True).last_hidden_state
        valid = mask.bool()
        hv = torch.cat([h[valid], h_last.expand(B, -1)], dim=0)
        tv = torch.cat([tgt[valid], torch.tensor([r[0] for r in resps], device=self.dev)], dim=0)
        lp_all = self.target_logprobs(hv, tv).cpu().numpy()
        lp, first = lp_all[:-B], lp_all[-B:]
        out, off = [], 0
        for i, r in enumerate(resps):
            n = len(r) - 1
            out.append(np.concatenate([[first[i]], lp[off:off + n]]).astype(np.float64))
            off += n
        del cb, h, hv, inp, tgt, mask, attn
        return out

    def score(self, prompt_ids: list[int], resps: list[list[int]]) -> list[np.ndarray]:
        cache, h_last = self.prefix(prompt_ids)
        P = len(prompt_ids)
        order = sorted(range(len(resps)), key=lambda i: len(resps[i]))
        res: list[np.ndarray | None] = [None] * len(resps)
        i, mb = 0, self.max_b
        while i < len(order):
            j = i + 1
            while j < len(order) and (j - i + 1) <= mb and (j - i + 1) * len(resps[order[j]]) <= self.budget:
                j += 1
            batch = order[i:j]
            try:
                lps = self.score_batch(cache, h_last, P, [resps[k] for k in batch])
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                if mb == 1 and self.budget <= 512:
                    raise
                mb = max(1, (j - i) // 2)
                self.budget = max(512, self.budget // 2)
                logger.warning(f"OOM -> batch {mb}, budget {self.budget}")
                continue
            for k, lp in zip(batch, lps):
                res[k] = lp
            i = j
        del cache
        return res  # type: ignore[return-value]

    def chat(self, user_text: str) -> list[int]:
        s = self.tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False)
        return self.tok(s, add_special_tokens=False).input_ids


def validate(sc: Scorer, n: int = 5) -> dict[str, Any]:
    """Reproduce n stored exp7 program scores (t1, cond forced|bfs|plain|k0): body log-prob sums within 0.05 nats."""
    import pandas as pd

    df = pd.read_parquet(EXP7 / "scores" / "cells" / "t1" / "Q1__forced__bfs__plain__k0__j:bfs__primary.parquet")
    conds = json.loads((EXP7 / "prompts" / "prompts_v2.json").read_text())["conditions"]
    cond = next(v for k, v in conds.items() if k.startswith("t1|") and v.get("cond_id") == "forced|bfs|plain|k0")
    progs = {r["prog_id"]: r for r in read_jsonl(EXP7 / "data" / "forced_selected.jsonl")}
    pids = df["prog_id"].tolist()[:n]
    fo = sc.tok(FENCE_OPEN, add_special_tokens=False).input_ids
    resps = [sc.tok(FENCE_OPEN + progs[p]["code_scrubbed"] + FENCE_CLOSE, add_special_tokens=False).input_ids
             for p in pids]
    lps = sc.score(sc.chat(cond["prompt"]), resps)
    rows = []
    for p, r, lp in zip(pids, resps, lps):
        n_open = len(fo) if r[:len(fo)] == fo else 1
        body = float(lp[n_open:-1].sum())
        ref = df[df["prog_id"] == p].iloc[0]
        rows.append({"prog_id": p, "body_now": body, "body_exp7": float(ref["body"]), "total_now": float(lp.sum()),
                     "total_exp7": float(ref["total"]), "abs_diff_body": abs(body - float(ref["body"]))})
    ok = all(r["abs_diff_body"] <= 0.05 for r in rows)
    return {"n": len(rows), "rows": rows, "max_abs_diff": max(r["abs_diff_body"] for r in rows), "pass": ok}


def logsumexp(x):
    m = max(x)
    return m + math.log(sum(math.exp(v - m) for v in x))


def rescore(sc: Scorer) -> dict[str, Any]:
    bench_import()
    from bench.common.catalogue import TASKS
    from bench.common.score_vllm import build_program_table, prompt_ids

    progs = build_program_table(EXP11, sc.tok)
    by_id = {p["program_id"]: p for p in progs}
    forced = read_jsonl(EXP11 / "data" / "samples_forced.jsonl")
    fp8 = {(c["task"], c["algorithm"]): c for c in read_jsonl(EXP11 / "data" / "frlp_cells.jsonl")
           if c["variant"] == "main" and c["half"] == "all"}
    cells, scores = [], {}
    t0 = time.time()
    for t in TASK_ORDER:
        sets = json.loads((EXP11 / "bench" / TASKS[t]["task_id"] / "frlp_sets.json").read_text())
        for j, st in sets.items():
            att = [r for r in forced if r["task"] == t and r["forced_mode"] == j]
            nk = Counter(r["paraphrase_id"] for r in att)
            N = sum(nk.values())
            pl = [pr for pr in st["programs"] if pr["program_id"] in by_id]
            if not pl or N == 0:
                cells.append({"task": t, "algorithm": j, "defined": False, "reason": "no programs"})
                continue
            resps = [by_id[pr["program_id"]]["resp_ids"] for pr in pl]
            sc_j: dict[str, list[float]] = {}
            for pid in ["baseline"] + [f"F{k}" for k in sorted(nk)]:
                ids = prompt_ids(sc.tok, t, pid, None if pid == "baseline" else j)
                lps = sc.score(ids, resps)
                sc_j[pid] = [float(x.sum()) for x in lps]
            ws = []
            for i, pr in enumerate(pl):
                lq = logsumexp([math.log(nk[k] / N) + sc_j[f"F{k}"][i] for k in nk])
                ws.append(sc_j["baseline"][i] - lq)
                scores[pr["program_id"]] = {pid: v[i] for pid, v in sc_j.items()}
            L = logsumexp(ws) - math.log(len(ws))
            a = st["adherence"]
            Lc = L + math.log(a) if a > 0 else None
            ess = math.exp(2 * logsumexp(ws) - logsumexp([2 * w for w in ws]))
            ref = fp8.get((t, j), {})
            cells.append({"task": t, "algorithm": j, "defined": True, "n_programs": len(ws), "L_fp32": L,
                          "L_corr_fp32": Lc, "ess_fp32": ess, "L_corr_fp8": ref.get("L_corr"), "ess_fp8": ref.get("ess"),
                          "diff": (Lc - ref["L_corr"]) if (Lc is not None and ref.get("L_corr") is not None) else None})
        logger.info(f"{t}: FRLP rescored ({time.time() - t0:.0f}s)")
    d = [abs(c["diff"]) for c in cells if c.get("diff") is not None]
    ranks = {}
    for t in TASK_ORDER:
        cs = [c for c in cells if c["task"] == t and c.get("diff") is not None]
        a8 = [c["algorithm"] for c in sorted(cs, key=lambda c: -c["L_corr_fp8"])]
        a32 = [c["algorithm"] for c in sorted(cs, key=lambda c: -c["L_corr_fp32"])]
        ranks[t] = {"order_fp8": a8, "order_fp32": a32, "argmax_same": bool(a8 and a8[0] == a32[0]),
                    "n_rank_changes": sum(1 for x, y in zip(a8, a32) if x != y)}
    out = {"cells": cells, "n_cells": len(cells), "median_abs_diff": float(np.median(d)) if d else None,
           "max_abs_diff": float(np.max(d)) if d else None, "rank_changes": ranks,
           "n_tasks_argmax_same": sum(v["argmax_same"] for v in ranks.values())}
    (RESULTS / "frlp_program_scores_fp32.json").write_text(json.dumps(scores))
    return out


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("gpu_D2_frlp")
    sc = Scorer()
    val = validate(sc)
    logger.info(f"exp7 scorer validation: max |diff| {val['max_abs_diff']:.4f} -> {'PASS' if val['pass'] else 'FAIL'}")
    res = {"validation": val}
    if val["pass"]:
        res.update(rescore(sc))
        logger.info(f"FRLP fp32 vs FP8: median |dL_corr| {res['median_abs_diff']}, max {res['max_abs_diff']}, "
                    f"argmax same on {res['n_tasks_argmax_same']}/12 tasks")
    write_json(RESULTS / "frlp_rescore.json", res)
