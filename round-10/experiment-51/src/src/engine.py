#!/usr/bin/env python3
"""vLLM client (token-id prompts over /v1/completions) and the five sampling arms.

T1.0 / IDEA / NS : temperature 1.0, top_p 1.0.     T1.6 : temperature 1.6, top_p 0.95.
DTB / RPB        : REQ1 = 48 tokens at T 1.0 with top-20 raw logprobs; choose a position j among eligible code tokens
                   (DTB: highest top-20 entropy, earliest on ties; RPB: uniform), force a token drawn uniformly from the
                   allowed candidates at ranks 2..8 of j, then REQ2 continues from prompt + gen1[:j] + [forced].
Every HTTP request: 180 s timeout, at most 2 retries; then the call is recorded as failed and the loop continues.
"""
from __future__ import annotations

import asyncio
import hashlib
import keyword
import math
import re

import aiohttp
import numpy as np

import prompts

ENGINE_TAG = "vllm0.11.0|Qwen3-8B-FP8@220b46e|fp8-marlin-w8a16"
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]
ARM_IDX = {a: i for i, a in enumerate(ARMS)}
SAMPLING = {"T1.0": (1.0, 1.0), "T1.6": (1.6, 0.95), "DTB": (1.0, 1.0), "RPB": (1.0, 1.0), "IDEA": (1.0, 1.0),
            "NS": (1.0, 1.0)}
REQ1_TOKENS, N_LOGPROBS, RANK_LO, RANK_HI = 48, 20, 2, 8
HTTP_TIMEOUT_S, HTTP_RETRIES = 180, 2


def call_seed(*parts: int) -> int:
    h = hashlib.sha256(("|".join(str(p) for p in parts)).encode()).digest()
    return int.from_bytes(h[:4], "little") & 0x7FFFFFFF


class Engine:
    def __init__(self, base_url: str, tokenizer, max_inflight: int = 48, model: str = "qwen3-8b"):
        self.url = base_url.rstrip("/") + "/v1/completions"
        self.tok, self.model = tokenizer, model
        self.sem = asyncio.Semaphore(max_inflight)
        self.session: aiohttp.ClientSession | None = None
        self.special = {tokenizer.eos_token_id, tokenizer.pad_token_id,
                        tokenizer.convert_tokens_to_ids("<|im_end|>"),
                        tokenizer.convert_tokens_to_ids("<|endoftext|>")} - {None}
        self._tok_text: dict[int, str] = {}
        self.n_http_fail = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_S))
        return self

    async def __aexit__(self, *exc):
        await self.session.close()

    def ttext(self, tid: int) -> str:
        if tid not in self._tok_text:
            self._tok_text[tid] = self.tok.decode([tid])
        return self._tok_text[tid]

    async def complete(self, prompt_ids: list[int], *, max_tokens: int, temperature: float, top_p: float, seed: int,
                       logprobs: int) -> dict:
        payload = {"model": self.model, "prompt": prompt_ids, "max_tokens": max_tokens, "temperature": temperature,
                   "top_p": top_p, "seed": seed, "stop": prompts.STOPS, "logprobs": logprobs,
                   "return_tokens_as_token_ids": True, "skip_special_tokens": False}
        last = ""
        for attempt in range(HTTP_RETRIES + 1):
            try:
                async with self.sem:
                    async with self.session.post(self.url, json=payload) as r:
                        if r.status != 200:
                            last = f"HTTP {r.status}: {(await r.text())[:300]}"
                            continue
                        d = await r.json()
                ch = d["choices"][0]
                lp = ch.get("logprobs") or {}
                ids = [int(t.split(":", 1)[1]) for t in lp.get("tokens") or []]
                tops = []
                for tl in lp.get("top_logprobs") or []:
                    tops.append(sorted(((int(k.split(":", 1)[1]), float(v)) for k, v in (tl or {}).items()),
                                       key=lambda x: -x[1]))
                return {"ok": True, "text": ch["text"], "ids": ids, "tops": tops,
                        "finish_reason": ch.get("finish_reason"), "stop_reason": ch.get("stop_reason"),
                        "n_tokens": int(d.get("usage", {}).get("completion_tokens", len(ids))), "attempts": attempt + 1}
            except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError) as e:
                last = repr(e)[:300]
        self.n_http_fail += 1
        return {"ok": False, "error": last, "text": "", "ids": [], "tops": [], "finish_reason": None, "n_tokens": 0}


# ------------------------------------------------------------------------------------------ DTB / RPB helpers
def scan_inside(text: str) -> list[bool]:
    """Per character: inside a '#' comment or a string literal (opening/closing quotes and '#' count as inside).
    The prefill docstring is already closed when the body starts."""
    inside = [False] * len(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "#":
            while i < n and text[i] != "\n":
                inside[i] = True
                i += 1
            continue
        if c in "'\"":
            q3 = text[i:i + 3]
            if q3 in ("'''", '"""'):
                j = i + 3
                while j < n and text[j:j + 3] != q3:
                    j += 2 if text[j] == "\\" else 1
                end = min(n, j + 3)
            else:
                j = i + 1
                while j < n and text[j] != c and text[j] != "\n":
                    j += 2 if text[j] == "\\" else 1
                end = min(n, j + 1)
            for k in range(i, end):
                inside[k] = True
            i = end
            continue
        i += 1
    return inside


def body_char_limit(text: str) -> int:
    """Characters of the decoded completion that survive trimming (up to the first non-empty indent-0 line)."""
    pos = 0
    for ln in text.split("\n"):
        if ln.strip() and not ln[0].isspace():
            return pos
        pos += len(ln) + 1
    return len(text)


def token_class(tok_text: str, prev_text: str) -> str:
    s = tok_text.strip()
    if not s:
        return "whitespace"
    if s in ("np", "math") or (prev_text.rstrip().endswith("np.") and re.fullmatch(r"[A-Za-z_]\w*", s)):
        return "np-call"
    if keyword.iskeyword(s) or s in ("True", "False", "None"):
        return "keyword"
    if re.fullmatch(r"[A-Za-z_]\w*", s):
        return "identifier"
    if re.fullmatch(r"\.?\d[\d_.eE+-]*", s):
        return "number"
    if re.fullmatch(r"[+\-*/%<>=!&|^~@]+", s):
        return "operator"
    return "punctuation"


def entropy_top(top: list[tuple[int, float]]) -> float:
    lp = np.array([v for _, v in top[:N_LOGPROBS]], dtype=float)
    if lp.size == 0:
        return 0.0
    p = np.exp(lp - lp.max())
    p /= p.sum()
    return float(-(p * np.log(np.clip(p, 1e-300, None))).sum())


def allowed(eng: Engine, tid: int) -> bool:
    if tid in eng.special:
        return False
    t = eng.ttext(tid)
    if not t or not t.strip() or "```" in t:
        return False
    return re.search(r"\n\S", t) is None


def choose_fork(eng: Engine, gen1: dict, mode: str, rng: np.random.Generator) -> dict:
    """Return the fork decision for DTB ('entropy') or RPB ('random') on REQ1's output."""
    ids, tops = gen1["ids"], gen1["tops"]
    texts = [eng.ttext(t) for t in ids]
    full = "".join(texts)
    inside = scan_inside(full)
    limit = body_char_limit(gen1["text"])
    H, elig, starts, pos = [], [], [], 0
    for t, (tid, tt) in enumerate(zip(ids, texts)):
        starts.append(pos)
        H.append(entropy_top(tops[t]) if t < len(tops) else 0.0)
        span = range(pos, pos + len(tt))
        code = all(not inside[c] for c in span if not full[c].isspace())
        ws = not tt.strip()
        cands = [(r + 1, cid) for r, (cid, _) in enumerate(tops[t][:N_LOGPROBS]) if RANK_LO <= r + 1 <= RANK_HI
                 and allowed(eng, cid)] if t < len(tops) else []
        if code and not ws and cands and pos < limit:
            elig.append((t, cands))
        pos += len(tt)
    info = {"H": [round(h, 4) for h in H], "n_E": len(elig), "E": [t for t, _ in elig]}
    if len(elig) < 2:
        info["unforced"] = True
        return info
    if mode == "entropy":
        j_idx = int(np.argmax([H[t] for t, _ in elig]))  # earliest on ties
    else:
        j_idx = int(rng.integers(0, len(elig)))
    j, cands = elig[j_idx]
    rank, forced = cands[int(rng.integers(0, len(cands)))]
    realised = ids[j]
    rr = next((r + 1 for r, (cid, _) in enumerate(tops[j]) if cid == realised), None)
    info.update({"unforced": False, "j": j, "forced_rank": rank, "forced_id": forced, "forced_text": eng.ttext(forced),
                 "realised_id": realised, "realised_text": texts[j], "realised_rank": rr,
                 "forced_equals_realised": forced == realised, "H_j": H[j],
                 "class_realised": token_class(texts[j], full[:starts[j]]),
                 "class_forced": token_class(eng.ttext(forced), full[:starts[j]]),
                 "cands": [[r, c] for r, c in cands]})
    return info


async def sample(eng: Engine, arm: str, prompt_ids: list[int], *, seed: int, arm_idx: int, call_id: int) -> dict:
    """One call of one arm. Returns completion text, token ids, n tokens, truncation and the DTB/RPB fields."""
    temp, top_p = SAMPLING[arm]
    s1 = call_seed(seed, arm_idx, call_id)
    if arm not in ("DTB", "RPB"):
        g = await eng.complete(prompt_ids, max_tokens=prompts.MAX_TOKENS, temperature=temp, top_p=top_p, seed=s1,
                               logprobs=0)
        return {"ok": g["ok"], "error": g.get("error"), "text": g["text"], "ids": g["ids"], "n_gen_tokens": g["n_tokens"],
                "truncated": g["finish_reason"] == "length", "finish_reason": g["finish_reason"], "vllm_seed": s1,
                "fork": None, "req_tokens": [g["n_tokens"]], "wasted_tokens": 0}
    g1 = await eng.complete(prompt_ids, max_tokens=REQ1_TOKENS, temperature=1.0, top_p=1.0, seed=s1,
                            logprobs=N_LOGPROBS)
    if not g1["ok"]:
        return {"ok": False, "error": g1.get("error"), "text": "", "ids": [], "n_gen_tokens": 0, "truncated": False,
                "finish_reason": None, "vllm_seed": s1, "fork": None, "req_tokens": [0], "wasted_tokens": 0}
    rng = np.random.default_rng([seed, arm_idx, call_id, 7])
    fork = choose_fork(eng, g1, "entropy" if arm == "DTB" else "random", rng)
    s2 = call_seed(seed, arm_idx, call_id, 2)
    if fork.get("unforced"):
        if g1["finish_reason"] == "stop":
            return {"ok": True, "text": g1["text"], "ids": g1["ids"], "n_gen_tokens": g1["n_tokens"], "truncated": False,
                    "finish_reason": "stop", "vllm_seed": s1, "fork": fork, "req_tokens": [g1["n_tokens"]],
                    "wasted_tokens": 0}
        prefix = g1["ids"]
        rest = prompts.MAX_TOKENS - len(prefix)
        g2 = await eng.complete(prompt_ids + prefix, max_tokens=rest, temperature=1.0, top_p=1.0, seed=s2, logprobs=0)
        fork["req2_prompt_len"] = len(prompt_ids) + len(prefix)
    else:
        j = fork["j"]
        prefix = g1["ids"][:j] + [fork["forced_id"]]
        rest = prompts.MAX_TOKENS - j - 1
        g2 = await eng.complete(prompt_ids + prefix, max_tokens=rest, temperature=1.0, top_p=1.0, seed=s2, logprobs=0)
        fork["req2_prompt_len"] = len(prompt_ids) + len(prefix)
    if not g2["ok"]:
        return {"ok": False, "error": g2.get("error"), "text": "", "ids": [], "n_gen_tokens": g1["n_tokens"],
                "truncated": False, "finish_reason": None, "vllm_seed": s1, "fork": fork,
                "req_tokens": [g1["n_tokens"], 0], "wasted_tokens": g1["n_tokens"]}
    ids = prefix + g2["ids"]
    text = eng.tok.decode(prefix) + g2["text"]
    wasted = len(g1["ids"]) - (len(prefix) if fork.get("unforced") else fork["j"])
    return {"ok": True, "text": text, "ids": ids, "n_gen_tokens": g1["n_tokens"] + g2["n_tokens"],
            "truncated": g2["finish_reason"] == "length", "finish_reason": g2["finish_reason"], "vllm_seed": s1,
            "vllm_seed2": s2, "fork": fork, "req_tokens": [g1["n_tokens"], g2["n_tokens"]], "wasted_tokens": wasted}


def entropy_ok(x: float) -> bool:
    return math.isfinite(x)
