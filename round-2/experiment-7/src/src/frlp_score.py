#!/usr/bin/env python3
"""Step 3: teacher-forced scorer (HF bf16, sdpa, prefix-KV reuse) and the resumable scoring queue Q1..Q9.

For a condition c (chat-formatted prompt) and a program p (response '```python\\n' + scrubbed code + '```'):
l(p|c) = sum_t log P(resp_t | prompt, resp_<t), computed as: one prefix pass over the prompt (keeps the KV cache and
the first response token's log-prob), then batches of right-padded responses over a copy of the cache.
Every condition writes one parquet (per-program sums) and one npz (per-token log-probs, float16).
"""

from __future__ import annotations

import argparse
import copy
import gc
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import torch
from loguru import logger

from config import (CHAT_TAIL, DATA, EDIT_LAYERS, LOGS, MODES, PROMPTS, RAND_SEEDS, RESULTS, SCORES, SHAMS, TASKS,
                    TRUNC_TOKENS, VARIANT_II_COEF, VARIANT_II_LAYER, WS, DATA_IN, model_path, read_json, read_jsonl,
                    setup_logging, utc_now, write_json, append_jsonl)

FENCE_OPEN = "```python\n"
FENCE_CLOSE = "```"
UNITS_DONE = SCORES / "units_done.jsonl"


def safe(s: str) -> str:
    return s.replace("|", "__").replace(":", "-").replace("/", "_").replace(" ", "_")


def _linear_fp32(self, x: torch.Tensor) -> torch.Tensor:
    """bf16-stored weights, fp32 activations: weight upcast per call, TF32 tensor-core matmul, fp32 output."""
    return torch.nn.functional.linear(x.float(), self.weight.float(),
                                      None if self.bias is None else self.bias.float())


class Scorer:
    def __init__(self, token_budget: int = 4096, max_b: int = 16, precision: str = "tf32") -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        mp = model_path()
        self.tok = AutoTokenizer.from_pretrained(mp)
        t0 = time.time()
        self.model = AutoModelForCausalLM.from_pretrained(mp, torch_dtype=torch.bfloat16,
                                                          attn_implementation="sdpa").cuda().eval()
        logger.info(f"HF model loaded in {time.time() - t0:.0f}s")
        self.dev = torch.device("cuda")
        self.layers = self.model.model.layers
        self.budget = token_budget
        self.max_b = max_b
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        self.vchunk, self.tchunk = 16384, 2048
        self.precision = precision
        if precision == "tf32":
            import types

            for mod in self.model.model.modules():
                if isinstance(mod, torch.nn.Linear):
                    mod.forward = types.MethodType(_linear_fp32, mod)
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        else:
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False

    def embed(self, ids: torch.Tensor) -> torch.Tensor:
        e = self.model.model.embed_tokens(ids)
        return e.float() if self.precision == "tf32" else e

    @torch.inference_mode()
    def target_logprobs(self, hv: torch.Tensor, tv: torch.Tensor) -> torch.Tensor:
        """log softmax(h W^T)[target] with logits computed in fp32 (bf16 hidden states upcast, lm_head weight
        upcast one vocab chunk at a time; TF32 disabled) -- bf16 logits cost ~1 nat of rounding per program."""
        W = self.model.lm_head.weight
        V = W.shape[0]
        N = hv.shape[0]
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

    def enc(self, s: str) -> list[int]:
        return self.tok(s, add_special_tokens=False).input_ids

    def chat(self, prompt: str) -> str:
        s = self.tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False)
        assert s.endswith(CHAT_TAIL)
        return s

    def _hooks(self, hooks: list[tuple[int, Callable]] | None) -> list:
        return [self.layers[layer].register_forward_hook(fn) for layer, fn in (hooks or [])]

    @torch.inference_mode()
    def prefix(self, prompt_ids: list[int], hooks=None):
        hs = self._hooks(hooks)
        try:
            out = self.model.model(inputs_embeds=self.embed(torch.tensor([prompt_ids], device=self.dev)),
                                   use_cache=True)
            self._h_last = out.last_hidden_state[0, -1:].clone()
        finally:
            for h in hs:
                h.remove()
        cache = out.past_key_values
        del out
        return cache, None

    @torch.inference_mode()
    def hidden_states(self, prompt_ids: list[int], hooks=None) -> tuple:
        hs = self._hooks(hooks)
        try:
            out = self.model.model(inputs_embeds=self.embed(torch.tensor([prompt_ids], device=self.dev)),
                                   output_hidden_states=True, use_cache=False)
        finally:
            for h in hs:
                h.remove()
        return out.hidden_states

    @torch.inference_mode()
    def score_batch(self, cache, logp0, P: int, resps: list[list[int]], hooks=None) -> list[np.ndarray]:
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
        hs = self._hooks(hooks)
        try:
            h = self.model.model(inputs_embeds=self.embed(inp), attention_mask=attn, past_key_values=cb,
                                 cache_position=cpos, use_cache=True).last_hidden_state
        finally:
            for hk in hs:
                hk.remove()
        valid = mask.bool()
        hv = h[valid]
        tv = tgt[valid]
        firsts = torch.tensor([r[0] for r in resps], device=self.dev)
        hv = torch.cat([hv, logp0.expand(B, -1)], dim=0)
        tv = torch.cat([tv, firsts], dim=0)
        lp_all = self.target_logprobs(hv, tv).cpu().numpy()
        lp, first = lp_all[:-B], lp_all[-B:]
        out, off = [], 0
        for i, r in enumerate(resps):
            n = len(r) - 1
            out.append(np.concatenate([[first[i]], lp[off:off + n]]).astype(np.float64))
            off += n
        del cb, h, hv, inp, tgt, mask, attn
        return out

    def score(self, prompt_ids: list[int], resps: list[list[int]], prompt_hooks=None, prog_hooks=None,
              max_b: int | None = None) -> list[np.ndarray]:
        cache, _ = self.prefix(prompt_ids, prompt_hooks)
        logp0 = self._h_last
        P = len(prompt_ids)
        order = sorted(range(len(resps)), key=lambda i: len(resps[i]))
        res: list[np.ndarray | None] = [None] * len(resps)
        i = 0
        mb = max_b or self.max_b
        while i < len(order):
            j = i + 1
            while j < len(order) and (j - i + 1) <= mb and (j - i + 1) * len(resps[order[j]]) <= self.budget:
                j += 1
            batch = order[i:j]
            try:
                lps = self.score_batch(cache, logp0, P, [resps[k] for k in batch], prog_hooks)
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

    @torch.inference_mode()
    def score_full(self, prompt_ids: list[int], resp: list[int]) -> np.ndarray:
        """Reference path: one no-cache forward over prompt + response."""
        ids = torch.tensor([prompt_ids + resp], device=self.dev)
        h = self.model.model(inputs_embeds=self.embed(ids), use_cache=False).last_hidden_state[0]
        P = len(prompt_ids)
        hv = h[P - 1:P - 1 + len(resp)]
        lp = self.target_logprobs(hv, torch.tensor(resp, device=self.dev))
        return lp.cpu().numpy().astype(np.float64)


# ------------------------------------------------------------------------------------------------ programs
def load_programs(sc: Scorer, m_max: int) -> dict[str, list[dict[str, Any]]]:
    rows = read_jsonl(DATA / "forced_selected.jsonl")
    fo = sc.enc(FENCE_OPEN)
    out: dict[str, list[dict[str, Any]]] = {t: [] for t in TASKS}
    for r in rows:
        if r["rank"] >= min(r["m_j"], m_max):
            continue
        for kind, code in (("scrubbed", r["code_scrubbed"]), ("raw", r["code_raw"])):
            text = FENCE_OPEN + code + FENCE_CLOSE
            ids = sc.enc(text)
            if kind == "scrubbed":
                r["resp_ids"] = ids
                r["n_open"] = len(fo) if ids[:len(fo)] == fo else _open_len(sc, ids)
            else:
                r["resp_ids_raw"] = ids
                r["n_open_raw"] = len(fo) if ids[:len(fo)] == fo else _open_len(sc, ids)
        out[r["task"]].append(r)
    for t in TASKS:
        out[t].sort(key=lambda r: (MODES[t].index(r["j"]), r["rank"]))
    return out


def _open_len(sc: Scorer, ids: list[int]) -> int:
    for k in range(1, 6):
        if sc.tok.decode(ids[:k]).startswith(FENCE_OPEN):
            return k
    return 3


def summarise(lp: np.ndarray, n_open: int) -> dict[str, float]:
    d = {"n_tokens": int(len(lp)), "total": float(lp.sum()), "fence_open": float(lp[:n_open].sum()),
         "body": float(lp[n_open:-1].sum()), "fence_close": float(lp[-1])}
    c = np.cumsum(lp)
    for k in TRUNC_TOKENS:
        d[f"cum{k}"] = float(c[min(k, len(lp)) - 1])
    return d


# ------------------------------------------------------------------------------------------------ edits
def rand_dirs() -> dict[str, np.ndarray]:
    out = {}
    for fam, seeds in RAND_SEEDS.items():
        for s in seeds:
            v = np.random.RandomState(s).standard_normal(4096)
            out[f"{fam}{s}"] = v / np.linalg.norm(v)
    return out


def variant_ii_dirs(task: str) -> dict[str, np.ndarray]:
    out = {}
    T = "T1" if task == "t1" else "T2"
    for name in ("rand1", "rand2"):
        p = DATA_IN / "exp4" / f"{name}_{T}_L18.npy"
        if p.exists():
            v = np.load(p).astype(np.float64).reshape(-1)
            out[f"exp4_{name}"] = v / np.linalg.norm(v)
    v = np.random.RandomState(3001).standard_normal(4096)
    out["new3001"] = v / np.linalg.norm(v)
    return out


def edit_norms(sc: Scorer, conds: dict[str, Any], task: str, suffix: int) -> np.ndarray:
    """n[l, p] = mean over (X, w) of ||h_l,p(ban_w X) - h_l,p(neutral_w X, noun A)|| on the band (last `suffix`
    prompt positions), l in EDIT_LAYERS; also returns the per-layer displacement at R for all layers."""
    acc = None
    accR = None
    n = 0
    for x in MODES[task]:
        for w in WS:
            hb = sc.hidden_states(sc.enc(conds[f"{task}|ban|{x}|{w}"]["chat"]))
            hn = sc.hidden_states(sc.enc(conds[f"{task}|neutral|{x}|{w}|A"]["chat"]))
            d = torch.stack([(hb[l + 1][0, -suffix:].float() - hn[l + 1][0, -suffix:].float()).norm(dim=-1)
                             for l in EDIT_LAYERS])
            dR = torch.stack([(hb[l][0, -1].float() - hn[l][0, -1].float()).norm() for l in range(len(hb))])
            acc = d if acc is None else acc + d
            accR = dR if accR is None else accR + dR
            n += 1
            del hb, hn
    return (acc / n).cpu().numpy(), (accR / n).cpu().numpy()


def make_edit_hooks(clean: dict[int, torch.Tensor], norms: np.ndarray, d: np.ndarray, suffix: int):
    dt = torch.tensor(d, dtype=torch.float32, device="cuda")
    hooks = []
    for li, layer in enumerate(EDIT_LAYERS):
        nl = torch.tensor(norms[li], dtype=torch.float32, device="cuda")
        target = (clean[layer].float() + nl[:, None] * dt[None, :])

        def fn(module, args, output, target=target):
            h = output[0] if isinstance(output, tuple) else output
            h[0, -suffix:] = target.to(h.dtype)
            return output

        hooks.append((layer, fn))
    return hooks


def make_variant_ii_hooks(d: np.ndarray):
    dt = torch.tensor(d, dtype=torch.float32, device="cuda")

    def at_last(module, args, output):
        h = output[0] if isinstance(output, tuple) else output
        v = h[:, -1].float()
        h[:, -1] = (v + VARIANT_II_COEF * v.norm(dim=-1, keepdim=True) * dt).to(h.dtype)
        return output

    def at_all(module, args, output):
        h = output[0] if isinstance(output, tuple) else output
        v = h.float()
        h.copy_((v + VARIANT_II_COEF * v.norm(dim=-1, keepdim=True) * dt).to(h.dtype))
        return output

    return [(VARIANT_II_LAYER, at_last)], [(VARIANT_II_LAYER, at_all)]


# ------------------------------------------------------------------------------------------------ queue
def build_units(conds: dict[str, Any], events: dict[str, Any], progs: dict[str, list], sc: Scorer) -> list[dict]:
    units: list[dict[str, Any]] = []

    def add(q: str, task: str, cond_id: str, chat: str, progset: str, variant: str = "primary", **kw: Any) -> None:
        units.append({"queue": q, "task": task, "cond_id": cond_id, "chat": chat, "progset": progset,
                      "variant": variant, "uid": f"{q}__{safe(cond_id)}__{progset}__{variant}", **kw})

    measurable = {t: sorted({r["j"] for r in progs[t]}, key=MODES[t].index) for t in TASKS}
    fam = {t: {r["j"]: r["family"] for r in progs[t]} for t in TASKS}
    for t in TASKS:  # Q1 denominators
        for j in measurable[t]:
            for k in range(10):
                cid = f"forced|{j}|{fam[t][j]}|k{k}"
                add("Q1", t, cid, conds[f"{t}|{cid}"]["chat"], f"j:{j}")
    for t in TASKS:  # Q2 gate set
        add("Q2", t, "base0", conds[f"{t}|base0"]["chat"], "all")
        for ev in events["events"]:
            if ev["task"] != t:
                continue
            for p in ev["paraphrases"]:
                cid = f"exp1|{ev['condition']}|p{p['paraphrase_id']}"
                add("Q2", t, cid, sc.chat(p["prompt"]), "all" if ev["condition"] == "baseline" else "h1",
                    event=ev["event_id"])
        for sev in events["succession_step2_descriptive"]:
            if sev["task"] != t:
                continue
            for p in sev["paraphrases"]:
                cid = f"exp1|succession:2|p{p['paraphrase_id']}"
                add("Q2", t, cid, sc.chat(p["prompt"]), "h1", event=sev["event_id"])
    for t in TASKS:  # Q3 main
        for x in MODES[t]:
            for w in WS:
                add("Q3", t, f"ban|{x}|{w}", conds[f"{t}|ban|{x}|{w}"]["chat"], "all")
                add("Q3", t, f"neutral|{x}|{w}|A", conds[f"{t}|neutral|{x}|{w}|A"]["chat"], "h1")
                add("Q3", t, f"neutral|{x}|{w}|B", conds[f"{t}|neutral|{x}|{w}|B"]["chat"], "h2")
    for t in TASKS:  # Q4 generic
        for w in WS:
            add("Q4", t, f"ban|nonce|{w}", conds[f"{t}|ban|nonce|{w}"]["chat"], "all")
            add("Q4", t, f"neutral|nonce|{w}|A", conds[f"{t}|neutral|nonce|{w}|A"]["chat"], "h1")
            add("Q4", t, f"neutral|nonce|{w}|B", conds[f"{t}|neutral|nonce|{w}|B"]["chat"], "h2")
        add("Q4", t, "novelty", conds[f"{t}|novelty"]["chat"], "all")
        for dname in rand_dirs():
            add("Q4", t, f"edit|{dname}", conds[f"{t}|base0"]["chat"], "all", variant="edit", direction=dname)
    for t in TASKS:  # Q5 mention (h2 first: never dropped)
        for x in MODES[t]:
            for w in WS:
                add("Q5", t, f"mention|{x}|{w}", conds[f"{t}|mention|{x}|{w}"]["chat"], "all")
    for t in TASKS:  # Q6 two-step
        for w in WS:
            add("Q6", t, f"ban|two_step|{w}", conds[f"{t}|ban|two_step|{w}"]["chat"], "all")
            add("Q6", t, f"neutral|two_step|{w}|A", conds[f"{t}|neutral|two_step|{w}|A"]["chat"], "h1")
            add("Q6", t, f"neutral|two_step|{w}|B", conds[f"{t}|neutral|two_step|{w}|B"]["chat"], "h2")
    for t in TASKS:  # Q7a+b per task (t1 first: its calibration is the one that fails)
        # Q7a unscrubbed denominators: raw programs under all 10 F_j paraphrases (mixture + single)
        for j in measurable[t]:
            for k in range(10):
                cid = f"forced|{j}|{fam[t][j]}|k{k}"
                add("Q7", t, cid, conds[f"{t}|{cid}"]["chat"], f"j:{j}", variant="unscrubbed")
        # Q7b unscrubbed gate set (diagnoses the scrubbing bias of the gate)
        add("Q7", t, "base0", conds[f"{t}|base0"]["chat"], "all", variant="unscrubbed")
        for ev in events["events"]:
            if ev["task"] != t:
                continue
            for p in ev["paraphrases"]:
                cid = f"exp1|{ev['condition']}|p{p['paraphrase_id']}"
                add("Q7", t, cid, sc.chat(p["prompt"]), "all" if ev["condition"] == "baseline" else "h1",
                    variant="unscrubbed", event=ev["event_id"])
    for t in TASKS:  # Q7c unscrubbed W1 ban / neutral (C1 sensitivity, reduced)
        for x in MODES[t]:
            add("Q7", t, f"ban|{x}|W1", conds[f"{t}|ban|{x}|W1"]["chat"], "all", variant="unscrubbed")
            add("Q7", t, f"neutral|{x}|W1|A", conds[f"{t}|neutral|{x}|W1|A"]["chat"], "h1", variant="unscrubbed")
            add("Q7", t, f"neutral|{x}|W1|B", conds[f"{t}|neutral|{x}|W1|B"]["chat"], "h2", variant="unscrubbed")
    for t in TASKS:  # Q8 off-catalogue shams
        for x in SHAMS[t]:
            for w in WS:
                add("Q8", t, f"ban|{x}|{w}", conds[f"{t}|ban|{x}|{w}"]["chat"], "all")
                add("Q8", t, f"neutral|{x}|{w}|A", conds[f"{t}|neutral|{x}|{w}|A"]["chat"], "h1")
                add("Q8", t, f"neutral|{x}|{w}|B", conds[f"{t}|neutral|{x}|{w}|B"]["chat"], "h2")
    for t in TASKS:  # Q9 variant (ii)
        for dname in variant_ii_dirs(t):
            add("Q9", t, f"edit2|{dname}", conds[f"{t}|base0"]["chat"], "all", variant="edit2", direction=dname)
    return units


def select(progs: list[dict[str, Any]], progset: str) -> list[dict[str, Any]]:
    if progset == "all":
        return progs
    if progset in ("h1", "h2"):
        return [r for r in progs if r["half"] == progset]
    if progset.startswith("j:"):
        return [r for r in progs if r["j"] == progset[2:]]
    if progset.startswith("rawgen:"):
        _, j, k = progset.split(":")
        return [r for r in progs if r["j"] == j and int(r["paraphrase_id"]) == int(k)]
    raise ValueError(progset)


def unit_tokens(u: dict[str, Any], progs: dict[str, list]) -> int:
    return sum(len(r["resp_ids"]) for r in select(progs[u["task"]], u["progset"]))


def run_unit(sc: Scorer, u: dict[str, Any], progs: dict[str, list], edit_ctx: dict[str, Any]) -> dict[str, Any]:
    t = u["task"]
    P = select(progs[t], u["progset"])
    raw = u["variant"] == "unscrubbed"
    resps = [r["resp_ids_raw"] if raw else r["resp_ids"] for r in P]
    prompt_ids = sc.enc(u["chat"])
    prompt_hooks = prog_hooks = None
    if u["variant"] == "edit":
        e = edit_ctx[t]
        prompt_hooks = make_edit_hooks(e["clean"], e["norms"], e["dirs"][u["direction"]], e["suffix"])
    elif u["variant"] == "edit2":
        prompt_hooks, prog_hooks = make_variant_ii_hooks(edit_ctx[t]["dirs2"][u["direction"]])
    t0 = time.time()
    lps = sc.score(prompt_ids, resps, prompt_hooks, prog_hooks)
    dt = time.time() - t0
    recs = []
    for r, lp in zip(P, lps):
        d = summarise(lp, r["n_open_raw"] if raw else r["n_open"])
        recs.append({"prog_id": r["prog_id"], "j": r["j"], "half": r["half"], **d})
    out_dir = SCORES / "cells" / t
    tok_dir = SCORES / "tokens" / t
    out_dir.mkdir(parents=True, exist_ok=True)
    tok_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recs).to_parquet(out_dir / f"{u['uid']}.parquet", index=False)
    offs = np.cumsum([0] + [len(x) for x in lps]).astype(np.int64)
    np.savez_compressed(tok_dir / f"{u['uid']}.npz", lp=np.concatenate(lps).astype(np.float16), offsets=offs,
                        prog_ids=np.array([r["prog_id"] for r in P]))
    ntok = int(sum(len(x) for x in lps))
    meta = {k: v for k, v in u.items() if k != "chat"}
    meta.update({"n_programs": len(P), "n_tokens": ntok, "seconds": dt, "utc": utc_now(),
                 "prompt_tokens": len(prompt_ids)})
    append_jsonl(UNITS_DONE, [meta])
    return meta


# ------------------------------------------------------------------------------------------------ validation
def validate(sc: Scorer, progs: dict[str, list], conds: dict[str, Any]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    t = "t1"
    sample = progs[t][:: max(1, len(progs[t]) // 8)][:8]
    c1, c2 = conds[f"{t}|base0"]["chat"], conds[f"{t}|ban|bfs|W1"]["chat"]
    p1, p2 = sc.enc(c1), sc.enc(c2)
    resps = [r["resp_ids"] for r in sample]
    cached1, cached2 = sc.score(p1, resps), sc.score(p2, resps)
    full1 = [sc.score_full(p1, r) for r in resps]
    full2 = [sc.score_full(p2, r) for r in resps]
    d_prog = [abs(a.sum() - b.sum()) for a, b in zip(cached1 + cached2, full1 + full2)]
    d_con = [abs((a.sum() - b.sum()) - (c.sum() - d.sum())) for a, b, c, d in zip(cached2, cached1, full2, full1)]
    res["i_cached_vs_full"] = {"max_prog_absdiff": float(max(d_prog)), "max_contrast_absdiff": float(max(d_con)),
                               "pass": bool(max(d_prog) <= 0.25 and max(d_con) <= 0.10)}
    b1 = [sc.score(p2, [r], max_b=1)[0] for r in resps]
    b1b = [sc.score(p1, [r], max_b=1)[0] for r in resps]
    d_b = [abs((a.sum() - b.sum()) - (c.sum() - d.sum())) for a, b, c, d in zip(cached2, cached1, b1, b1b)]
    res["ii_B1_vs_B8_contrast"] = {"max_absdiff": float(max(d_b)), "pass": bool(max(d_b) <= 0.10)}
    ok3 = True
    for r in sample:
        text = FENCE_OPEN + r["code_scrubbed"] + FENCE_CLOSE
        if sc.tok.decode(p1 + r["resp_ids"]) != c1 + text or r["resp_ids"] != sc.enc(text):
            ok3 = False
    res["iii_roundtrip"] = {"pass": ok3}
    ex = [r for r in read_jsonl(DATA_IN / "exp1" / "labelled.jsonl") if r["condition"] == "baseline"
          and r["finish_reason"] == "stop" and r.get("code")][:20]
    diffs = []
    same_text = 0
    for r in ex:
        recon = FENCE_OPEN + r["code"] + FENCE_CLOSE
        same_text += int(recon == r["text"])
        diffs.append(len(sc.enc(r["text"])) - int(r["n_output_tokens"]))
    res["iv_exp1_token_counts"] = {"diffs": diffs, "pass": bool(all(abs(d) <= 1 for d in diffs)),
                                   "text_equals_fenced_code": f"{same_text}/{len(ex)}"}
    res["pass"] = bool(res["i_cached_vs_full"]["pass"] and res["ii_B1_vs_B8_contrast"]["pass"] and ok3)
    return res


def known_answer(sc: Scorer, progs: dict[str, list], conds: dict[str, Any], events: dict[str, Any]) -> dict:
    """Gain-based smoke test on 10 programs per algorithm: mean l(p|c) - l(p|BASE0) per algorithm."""
    out = {}
    t = "t1"
    sub = [r for j in MODES[t] for r in [x for x in progs[t] if x["j"] == j][:10]]
    resps = [r["resp_ids"] for r in sub]
    base = sc.score(sc.enc(conds[f"{t}|base0"]["chat"]), resps)
    ment = next(p["prompt"] for ev in events["events"] if ev["event_id"] == "t1|mention:dfs" for p in ev["paraphrases"])
    for name, chat in (("F_dfs_k0", conds[f"{t}|forced|dfs|plain|k0"]["chat"]), ("exp1_mention_dfs", sc.chat(ment))):
        sc_ = sc.score(sc.enc(chat), resps)
        g: dict[str, list[float]] = {}
        for r, a, b in zip(sub, sc_, base):
            g.setdefault(r["j"], []).append(float(a.sum() - b.sum()))
        means = {j: float(np.mean(v)) for j, v in g.items()}
        out[name] = {"mean_gain_vs_base0": means, "argmax": max(means, key=means.get),
                     "pass": max(means, key=means.get) == "dfs"}
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline", required=True, help="HH:MM local wall-clock time after which no unit starts")
    ap.add_argument("--cut-min", type=float, default=150.0)
    ap.add_argument("--force-m", type=int, default=0)
    ap.add_argument("--skip-validation", action="store_true")
    ap.add_argument("--precision", default="tf32", choices=["tf32", "bf16"])
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    setup_logging("frlp_score")
    torch.manual_seed(0)
    now = datetime.now()
    hh, mm = map(int, args.deadline.split(":"))
    deadline = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if deadline < now:
        deadline = deadline.replace(day=now.day + 1)
    pv = read_json(PROMPTS / "prompts_v2.json")
    conds, suffix = pv["conditions"], pv["spec_suffix_tokens"]
    events = read_json(RESULTS / "gate_events.json")
    sc = Scorer(precision=args.precision)
    progs = load_programs(sc, 30)
    if not args.skip_validation and not (LOGS / "scorer_validation.json").exists():
        val = validate(sc, progs, conds)
        val["known_answer"] = known_answer(sc, progs, conds, events)
        val["precision"] = args.precision
        write_json(LOGS / "scorer_validation.json", val)
        if args.validate_only:
            return
        logger.info(f"validation: {json.dumps(val)[:1500]}")
        if not val["pass"]:
            raise SystemExit("scorer validation failed -> inspect before running the queue (FALLBACK F3)")
    # throughput test and cut rule
    tp_file = LOGS / "throughput.json"
    if tp_file.exists():
        tp = read_json(tp_file)
    else:
        resps = [r["resp_ids"] for r in progs["t1"]][:100]
        torch.cuda.synchronize()
        t0 = time.time()
        sc.score(sc.enc(conds["t1|base0"]["chat"]), resps)
        torch.cuda.synchronize()
        dt = time.time() - t0
        tps = sum(len(r) for r in resps) / dt
        units30 = build_units(conds, events, progs, sc)
        q16 = [u for u in units30 if u["queue"] in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")]
        tok30 = sum(unit_tokens(u, progs) for u in q16)
        proj30 = (tok30 / tps + 0.3 * len(q16)) / 60
        m = 30 if proj30 <= args.cut_min else 20
        if args.force_m:
            m = args.force_m
        tp = {"tokens_per_s": tps, "test_programs": len(resps), "test_seconds": dt, "q1_q6_units": len(q16),
              "q1_q6_tokens_M30": tok30, "projected_q1_q6_min_M30": proj30, "cut_rule_min": args.cut_min,
              "M": m, "gate_paraphrases": 5 if m == 30 else 3, "utc": utc_now(),
              "gpu": torch.cuda.get_device_name(0), "batch_token_budget": sc.budget, "max_b": sc.max_b}
        write_json(tp_file, tp)
        logger.info(f"throughput {tps:.0f} tok/s; projected Q1-Q6 at M=30: {proj30:.1f} min -> M={m}")
    m = int(tp["M"])
    if m < 30:
        progs = load_programs(sc, m)
    units = build_units(conds, events, progs, sc)
    if tp.get("gate_paraphrases", 5) < 5:
        keep = {}
        for ev in events["events"]:
            keep[ev["event_id"]] = {p["paraphrase_id"] for p in ev["paraphrases"][:3]}
        units = [u for u in units if u["queue"] not in ("Q2", "Q7") or "event" not in u or u["event"] not in keep
                 or int(u["cond_id"].rsplit("|p", 1)[1]) in keep[u["event"]]]
    # random-edit context (norms, clean BASE0 states, directions)
    edit_ctx: dict[str, Any] = {}
    for t in TASKS:
        nf = SCORES / "edits" / f"{t}_norms.npz"
        nf.parent.mkdir(parents=True, exist_ok=True)
        if nf.exists():
            z = np.load(nf)
            norms, normsR = z["norms"], z["normsR"]
        else:
            norms, normsR = edit_norms(sc, conds, t, suffix[t])
            np.savez(nf, norms=norms, normsR=normsR)
        hs = sc.hidden_states(sc.enc(conds[f"{t}|base0"]["chat"]))
        clean = {l: hs[l + 1][0, -suffix[t]:].clone() for l in EDIT_LAYERS}
        del hs
        edit_ctx[t] = {"norms": norms, "normsR": normsR, "clean": clean, "dirs": rand_dirs(),
                       "dirs2": variant_ii_dirs(t), "suffix": suffix[t]}
    done = {(r["task"], r["uid"]) for r in read_jsonl(UNITS_DONE)}  # uids are unique within a task only
    total_tok = sum(unit_tokens(u, progs) for u in units if (u["task"], u["uid"]) not in done)
    logger.info(f"queue: {len(units)} units, {len(done)} done, {total_tok / 1e6:.1f}M tokens remaining")
    t_start = time.time()
    tok_done = 0
    skipped = []
    for i, u in enumerate(units):
        if (u["task"], u["uid"]) in done:
            continue
        dl_file = LOGS / "deadline.txt"
        if dl_file.exists():
            try:
                h2, m2 = map(int, dl_file.read_text().strip().split(":"))
                deadline = datetime.now().replace(hour=h2, minute=m2, second=0, microsecond=0)
            except ValueError:
                pass
        if datetime.now() >= deadline:
            skipped.append(u["uid"])
            continue
        meta = run_unit(sc, u, progs, edit_ctx)
        tok_done += meta["n_tokens"]
        el = time.time() - t_start
        rate = tok_done / max(el, 1e-6)
        rem = sum(unit_tokens(v, progs) for v in units[i + 1:] if (v["task"], v["uid"]) not in done)
        if i % 10 == 0 or u["queue"] != units[min(i + 1, len(units) - 1)]["queue"]:
            logger.info(f"[{u['queue']}] {i + 1}/{len(units)} {u['uid'][:60]} n={meta['n_programs']} "
                        f"{meta['seconds']:.1f}s | {rate:.0f} tok/s | ETA all {rem / max(rate, 1) / 60:.1f} min")
            write_json(LOGS / "queue_progress.json", {"utc": utc_now(), "done_units": i + 1, "units": len(units),
                                                      "rate_tok_s": rate, "eta_min": rem / max(rate, 1) / 60,
                                                      "current_queue": u["queue"]})
        gc.collect()
    write_json(LOGS / "queue_final.json", {"utc": utc_now(), "n_units": len(units), "skipped_after_deadline": skipped,
                                           "M": m})
    logger.info(f"queue finished; skipped {len(skipped)} units after the deadline")


if __name__ == "__main__":
    main()
