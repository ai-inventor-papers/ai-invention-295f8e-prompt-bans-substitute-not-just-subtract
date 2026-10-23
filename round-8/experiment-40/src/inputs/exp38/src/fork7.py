#!/usr/bin/env python3
"""Fork context for iteration 7: c*, the B/D token classes, the fork margin m, prompt builders (twin, 120 noun
variants, forced prompts with equal-length display names) and position classes (FORK, CSTAR, SPEC, COND)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import torch

import prompts as PG
from cfg import (B_IDS, D_IDS, DISPLAY_PAIRS, FORCED_TEMPLATES, I6_RESULTS, TEMPLATE_IDS, cap_first, read_json)


@lru_cache(maxsize=1)
def fork_table() -> dict[str, Any]:
    return read_json(I6_RESULTS / "fork.json")


def cstar() -> list[int]:
    return [int(t) for t in fork_table()["cstar_ids"]]


def token_table() -> dict[int, dict[str, Any]]:
    return {int(k): v for k, v in fork_table()["token_table"].items()}


def margin(logits: torch.Tensor) -> torch.Tensor:
    """m = logsumexp(z[B]) - z['visited'] over the last dim (works on [..., V])."""
    z = logits.float()
    return torch.logsumexp(z[..., list(B_IDS)], -1) - z[..., D_IDS[0]]


def class_probs(logits: torch.Tensor) -> torch.Tensor:
    """[..., 3] probabilities of the classes (B, D, O) at the fork."""
    p = torch.softmax(logits.float(), -1)
    pb = p[..., list(B_IDS)].sum(-1)
    pd = p[..., list(D_IDS)].sum(-1)
    return torch.stack([pb, pd, (1 - pb - pd).clamp(min=0)], -1)


@lru_cache(maxsize=1)
def nouns() -> dict[str, list[str]]:
    n = read_json(I6_RESULTS / "nouns.json")
    return {"frozen": list(n["frozen"]), "new": list(n["new"])}


def twin(w: str) -> dict[str, Any]:
    return PG.p_twin("T1", w)


def variants() -> list[dict[str, Any]]:
    """The 120 neutral twin variants (5 templates x 24 single-token nouns), iteration 6's construction."""
    out = []
    nn = nouns()
    for w in TEMPLATE_IDS:
        for src in ("frozen", "new"):
            for n in nn[src]:
                p = PG.p_noun_variant("T1", w, n)
                assert p is not None, (w, n)
                p = dict(p)
                p.update({"template": w, "noun": n, "noun_source": src, "vid": f"{w}|{n}"})
                out.append(p)
    return out


def forced(mode: str, f: str, pair_idx: int) -> dict[str, Any]:
    """Forced prompt F_f naming `mode` (bfs|dfs) with display pair pair_idx, ' .'-padded to the W-twin's spec_start."""
    w = "W" + f[1:]
    tw = twin(w)
    name = DISPLAY_PAIRS[pair_idx][0 if mode == "bfs" else 1]
    seg = FORCED_TEMPLATES[f].format(Y=name)
    p = PG._pad_segment_to("T1", cap_first(seg), tw["spec_start"], "forced", f"forced:{mode}:{f}:{pair_idx}",
                           X=mode, w=w)
    p = dict(p)
    p.update({"template": f, "mode": mode, "pair": pair_idx, "display": name, "sid": f"{f}|{mode}|{pair_idx}"})
    return p


def forced_sources() -> list[dict[str, Any]]:
    out = []
    for f in FORCED_TEMPLATES:
        for pi in range(len(DISPLAY_PAIRS)):
            for mode in ("bfs", "dfs"):
                out.append(forced(mode, f, pi))
    return out


def positions(p: dict[str, Any], n_prefix: int = 32) -> dict[str, list[int]]:
    """Absolute positions in prompt + c*: FORK = last c* token; CSTAR = c*[0..30]; SPEC = spec text + chat tail;
    COND = the condition segment before the spec."""
    P = p["P"]
    return {"FORK": [P + n_prefix - 1], "CSTAR": list(range(P, P + n_prefix - 1)),
            "SPEC": list(range(p["spec_start"], P)), "COND": list(range(p["seg_start"], p["spec_start"]))}


def offsets_from_end(p: dict[str, Any], cls: str, n_prefix: int = 32) -> list[int]:
    """Positions of class cls as offsets from the end of prompt + c* (alignment across prompts)."""
    L = p["P"] + n_prefix
    return [L - 1 - q for q in positions(p, n_prefix)[cls]]
