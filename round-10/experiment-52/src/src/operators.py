#!/usr/bin/env python3
"""S5 operators: T1.0, T1.6 (top-p 0.95), IDEA (one extra sentence), NS (fixed parents), and the two-request branching
operators DTB (force a rank-2..8 token at the highest-entropy eligible position among the first 48 body tokens) and its
placebo RPB (the same forcing at a uniformly random eligible position)."""
from __future__ import annotations

import io
import keyword
import math
import re
import tokenize

import numpy as np

import common as C
import prompts as P

ARMS = {
    "T1.0": dict(T=1.0, top_p=1.0, idea=False, branch=None),
    "T1.6": dict(T=1.6, top_p=0.95, idea=False, branch=None),
    "DTB": dict(T=1.0, top_p=1.0, idea=False, branch="entropy"),
    "RPB": dict(T=1.0, top_p=1.0, idea=False, branch="random"),
    "IDEA": dict(T=1.0, top_p=1.0, idea=True, branch=None),
    "NS": dict(T=1.0, top_p=1.0, idea=False, branch=None),
}
R1_TOKENS = 48
TOPK = 20
_STRING_TYPES = {tokenize.STRING}
for _n in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
    if hasattr(tokenize, _n):
        _STRING_TYPES.add(getattr(tokenize, _n))


def req_seed(S: int, arm: str, call: int, req: int) -> int:
    return (S * 1000003 + C.ARM_IDS[arm] * 100003 + call * 7 + req) % (2 ** 31)


def condition(arm: str) -> str:
    a = ARMS[arm]
    return f"{arm}|T={a['T']}|top_p={a['top_p']}|idea={a['idea']}|branch={a['branch']}"


class TokText:
    """Cached single-token decodes and the candidate filter."""

    def __init__(self, tok):
        self.tok = tok
        self.cache: dict[int, str] = {}
        self.special = {i for i in (tok.convert_tokens_to_ids("<|im_end|>"), tok.convert_tokens_to_ids("<|endoftext|>"))
                        if i is not None}

    def text(self, tid: int) -> str:
        if tid not in self.cache:
            self.cache[tid] = self.tok.decode([tid])
        return self.cache[tid]

    def cand_ok(self, tid: int) -> bool:
        if tid in self.special:
            return False
        s = self.text(tid)
        if s in ("<|im_end|>", "<|endoftext|>"):
            return False
        if "```" in s or (s and set(s) == {"`"}):
            return False
        if s.strip() == "":
            return False
        if re.search(r"\n\S", s):
            return False
        return True

    def ws_only(self, tid: int) -> bool:
        return self.text(tid).strip() == ""


def entropy20(pairs: list[tuple[int, float]]) -> float:
    lp = np.array([v for _, v in pairs], dtype=np.float64)
    if lp.size == 0:
        return 0.0
    lp = lp - lp.max()
    p = np.exp(lp)
    p /= p.sum()
    return float(-(p * np.log(np.clip(p, 1e-300, None))).sum())


def comment_string_spans(code: str) -> list[tuple[int, int]]:
    """Absolute character spans of COMMENT and STRING tokens; on TokenError/SyntaxError keep the tokens yielded so far
    and add the per-line fallback (a '#' outside quotes opens a comment)."""
    lines = code.splitlines(keepends=True)
    starts = np.cumsum([0] + [len(x) for x in lines]).tolist()

    def absf(rc):
        r, c = rc
        return starts[r - 1] + c if r - 1 < len(starts) else len(code)

    spans, failed = [], False
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.COMMENT or t.type in _STRING_TYPES:
                spans.append((absf(t.start), absf(t.end)))
    except (tokenize.TokenError, SyntaxError):
        failed = True
    if failed:
        for li, ln in enumerate(lines):
            q = None
            for ci, ch in enumerate(ln):
                if q:
                    if ch == q:
                        q = None
                elif ch in ("'", '"'):
                    q = ch
                elif ch == "#":
                    spans.append((starts[li] + ci, starts[li] + len(ln)))
                    break
    return spans


def token_class(txt: str, prev_text: str) -> str:
    s = txt.strip()
    if not s:
        return "other"
    if keyword.iskeyword(s):
        return "keyword"
    if re.fullmatch(r"\d+(\.\d*)?([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?", s):
        return "number"
    if s.isidentifier():
        if s == "np" or prev_text.rstrip().endswith("np."):
            return "np-call"
        return "identifier"
    if re.fullmatch(r"[\+\-\*/%=<>!&|\^~@:,\.\(\)\[\]\{\};]+", s):
        return "operator"
    return "other"


def branch_plan(tt: TokText, gen: list[int], top: list[list[tuple[int, float]]], S: int, arm: str, call: int) -> dict:
    """Pure function: from r1's sampled ids and top-20 tables, the eligible set E, the entropy profile, j, r and the
    forced id. Re-derivable offline from the logged tables (the direction's CHECK)."""
    n = min(len(gen), len(top))
    # drop positions after a stop (cumulative decode)
    keep = n
    pref_txt = []
    for t in range(n):
        s = tt.tok.decode(gen[:t + 1])
        pref_txt.append(s)
        if any(st in s for st in P.STOPS):
            keep = t
            break
    gen_k, top_k = gen[:keep], top[:keep]
    r1_text = tt.tok.decode(gen_k)
    offs = [0] + [len(tt.tok.decode(gen_k[:t + 1])) for t in range(keep)]
    base = len(P.PREFILL_CODE)
    spans = comment_string_spans(P.PREFILL_CODE + r1_text)
    in_cs = []
    for t in range(keep):
        a, b = base + offs[t], base + offs[t + 1]
        in_cs.append(any(not (b <= s0 or a >= s1) for s0, s1 in spans) if b > a else False)
    cand = [[tid for tid, _ in sorted(top_k[t], key=lambda x: -x[1]) if tt.cand_ok(tid)] for t in range(keep)]
    H = [entropy20(top_k[t]) for t in range(keep)]
    E = [t for t in range(keep) if not tt.ws_only(gen_k[t]) and not in_cs[t] and len(cand[t]) >= 2]
    out = {"n_r1": len(gen), "n_kept": keep, "E": E, "H": [round(h, 6) for h in H], "in_comment_string":
           [t for t in range(keep) if in_cs[t]]}
    if len(E) < 2:
        out["no_branch"] = True
        return out
    rng = np.random.default_rng([S, C.ARM_IDS[arm], call, 7])
    if ARMS[arm]["branch"] == "entropy":
        j = E[0]
        for t in E[1:]:
            if H[t] > H[j]:
                j = t
    else:
        j = int(rng.choice(E))
    r = int(rng.integers(2, min(8, len(cand[j])) + 1))
    forced = int(cand[j][r - 1])
    ranked = [tid for tid, _ in sorted(top_k[j], key=lambda x: -x[1])]
    gj = int(gen_k[j])
    prev = tt.tok.decode(gen_k[:j])
    out.update(no_branch=False, j=j, H_j=H[j], r=r, forced_id=forced, forced_text=tt.text(forced), gen_j_id=gj,
               gen_j_text=tt.text(gj), forced_eq_gen=forced == gj,
               gen_j_rank=(ranked.index(gj) + 1) if gj in ranked else TOPK + 1,
               j_is_global_argmax=bool(j == int(np.argmax(H))) if H else False,
               token_class_gen_j=token_class(tt.text(gj), prev), token_class_forced=token_class(tt.text(forced), prev),
               n_cand_j=len(cand[j]))
    return out


async def generate(engine, tt: TokText, arm: str, S: int, call: int, prompt_ids: list[int]) -> dict:
    """One call of an arm. Returns the completion text plus accounting and operator fields."""
    a = ARMS[arm]
    if a["branch"] is None:
        r = await engine.complete(prompt_ids, max_tokens=P.MAX_TOKENS, temperature=a["T"], top_p=a["top_p"],
                                  seed=req_seed(S, arm, call, 0), stop=P.STOPS)
        return {"completion": r["text"], "truncated": r["finish_reason"] == "length", "failed": r["error"] is not None,
                "error": r["error"], "finish_reason": r["finish_reason"], "prompt_tokens": r["prompt_tokens"],
                "completion_tokens": r["completion_tokens"] or 0, "n_requests": 1}
    r1 = await engine.complete(prompt_ids, max_tokens=R1_TOKENS, temperature=1.0, top_p=1.0,
                               seed=req_seed(S, arm, call, 0), stop=P.STOPS, logprobs=TOPK)
    acc = {"prompt_tokens": r1["prompt_tokens"], "r1_tokens": r1["completion_tokens"] or 0, "n_requests": 1}
    if r1["error"] is not None:
        return dict(acc, completion="", truncated=False, failed=True, error=r1["error"], finish_reason="error",
                    completion_tokens=acc["r1_tokens"], branch={"no_branch": True, "r1_failed": True})
    gen, top = r1["token_ids"], r1["top"]
    plan = branch_plan(tt, gen, top, S, arm, call)
    plan["r1_finish_reason"] = r1["finish_reason"]
    if plan.get("no_branch"):
        if r1["finish_reason"] == "stop":
            return dict(acc, completion=r1["text"], truncated=False, failed=False, error=None, finish_reason="stop",
                        completion_tokens=acc["r1_tokens"], branch=plan, r2_tokens=0, r1_ids=gen, r1_top=top)
        prefix = gen
        r2 = await engine.complete(prompt_ids + prefix, max_tokens=max(1, P.MAX_TOKENS - len(prefix)),
                                   temperature=1.0, top_p=1.0, seed=req_seed(S, arm, call, 1), stop=P.STOPS)
        comp = tt.tok.decode(prefix) + r2["text"]
    else:
        j, forced = plan["j"], plan["forced_id"]
        prefix = gen[:j] + [forced]
        r2 = await engine.complete(prompt_ids + prefix, max_tokens=max(1, P.MAX_TOKENS - j - 1), temperature=1.0,
                                   top_p=1.0, seed=req_seed(S, arm, call, 1), stop=P.STOPS)
        comp = tt.tok.decode(prefix) + r2["text"]
        plan["r2_prompt_ids_ok"] = True
    acc["n_requests"] = 2
    r2t = r2["completion_tokens"] or 0
    return dict(acc, completion=comp, truncated=r2["finish_reason"] == "length", failed=r2["error"] is not None,
                error=r2["error"], finish_reason=r2["finish_reason"], r2_tokens=r2t,
                completion_tokens=acc["r1_tokens"] + r2t, branch=plan, r1_ids=gen, r1_top=top,
                r2_prompt_tokens=r2["prompt_tokens"])


def _selfcheck_entropy() -> None:
    assert abs(entropy20([(1, math.log(0.5)), (2, math.log(0.5))]) - math.log(2)) < 1e-9
