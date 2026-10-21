#!/usr/bin/env python3
"""D2-D4: exact signature vetoes by truncate-and-redraw.

Coupling argument (exactness): take a free sample y.  At the first step where y's token completes a vetoed n-gram,
the vetoed process diverges: that token is redrawn from p(. | not the completing token) (logit_bias -100) and the
generation continues from prompt + y[:t] + [redraw].  Before the first hit the vetoed and free processes coincide
(at every earlier opportunity the free token was not the masked one), so the output is an exact draw of
  - the ONE-SHOT veto (first completion suppressed; continuation unmasked), or
  - the PERSISTENT veto (continuation under the VetoAdapter mask on every n-gram of the set).
Samples without a hit are exact draws of both.  One-shot and persistent arms share pass-1 and the redraw, and their
continuations use the same seed (common random numbers)."""

from __future__ import annotations

from typing import Any

from src.ws import EOS_IDS, MAX_TOKENS, request_seed


def first_hit(prompt_ids: list[int], y: list[int], grams: list[list[int]]) -> tuple[int, list[list[int]]] | None:
    """Earliest index t in y whose token completes some g (context = prompt tail + y); returns (t, all g completing)."""
    if not grams:
        return None
    nmax = max(len(g) for g in grams)
    tail = list(prompt_ids[-(nmax - 1):]) if nmax > 1 else []
    seq = tail + list(y)
    off = len(tail)
    by_last: dict[int, list[list[int]]] = {}
    for g in grams:
        by_last.setdefault(g[-1], []).append(g)
    for t in range(len(y)):
        tokv = y[t]
        if tokv not in by_last:
            continue
        end = off + t
        hit = []
        for g in by_last[tokv]:
            n = len(g)
            s = end - n + 1
            if s >= 0 and seq[s:end + 1] == g:
                hit.append(g)
        if hit:
            return t, hit
    return None


def masked_at(prompt_ids: list[int], prefix: list[int], grams: list[list[int]]) -> list[int]:
    """Completing tokens of every n-gram whose first n-1 tokens match the context end (prompt + prefix)."""
    ctx = list(prompt_ids) + list(prefix)
    out = []
    for g in grams:
        n = len(g)
        if n == 1 or (len(ctx) >= n - 1 and ctx[len(ctx) - (n - 1):] == g[:-1]):
            out.append(g[-1])
    return sorted(set(out))


def plan_sample(*, task: str, tag: str, w: Any, sid: Any, prompt_ids: list[int], y: list[int],
                grams: list[list[int]], n_cont: int = 1) -> dict[str, Any]:
    """Per pass-1 sample: hit position and the redraw request (continuations are built after the redraw)."""
    h = first_hit(prompt_ids, y, grams)
    if h is None:
        return {"hit": False, "t": None}
    t, hit_grams = h
    mask = masked_at(prompt_ids, y[:t], grams)
    seed2 = request_seed(task, f"redraw:{tag}", w, sid)
    return {"hit": True, "t": t, "hit_grams": hit_grams, "mask_tokens": mask,
            "redraw_req": {"prompt_ids": list(prompt_ids) + list(y[:t]), "max_tokens": 1, "seed": seed2,
                           "logit_bias": {int(m): -100.0 for m in mask}},
            "n_cont": n_cont}


def continuation_reqs(*, task: str, tag: str, w: Any, sid: Any, prompt_ids: list[int], y: list[int], t: int,
                      tok: int, grams: list[list[int]], n_cont: int = 1, persistent: bool = True,
                      oneshot: bool = True) -> list[dict[str, Any]]:
    """Continuations after the redraw token; same seed for the one-shot and persistent arm (CRN)."""
    if tok in EOS_IDS:
        return []
    base = list(prompt_ids) + list(y[:t]) + [int(tok)]
    budget = MAX_TOKENS - t - 1
    if budget <= 0:
        return []
    out = []
    for c in range(n_cont):
        seed3 = request_seed(task, f"cont:{tag}", w, f"{sid}:{c}")
        if oneshot:
            out.append({"prompt_ids": base, "max_tokens": budget, "seed": seed3, "arm": "oneshot", "c": c})
        if persistent:
            out.append({"prompt_ids": base, "max_tokens": budget, "seed": seed3, "arm": "persistent", "c": c,
                        "veto": [list(map(int, g)) for g in grams]})
    return out


def in_code_at(text_before: str) -> bool:
    return text_before.count("```") % 2 == 1
