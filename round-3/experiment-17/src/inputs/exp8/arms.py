#!/usr/bin/env python3
"""Arm construction from prefilled ban / neutral prompts of one (task, template).

a  = ban cache, ban R logits                         b  = neutral cache, neutral R logits
c  = PROMPT ROUTE: neutral [0,p1) + ban [p1,P), R from ban
d  = DIRECT ROUTE: ban [0,p1) + neutral [p1,P), R from neutral
e  = R-only: neutral cache with position P-1 from ban, R from ban
f  = task-spec-only: neutral [0,p1) + ban [p1,P-1) + neutral P-1, R from neutral
pl = placebo: neutral-A [0,p1) + neutral-B [p1,P), R from neutral-B (compared with b under noun B)
K0/K1/K2/B1-B3 = cache a with a condition-span knockout; K0b = cache b with the K0 knockout.
"""

from __future__ import annotations

from typing import Any

from cfg import KO_WINDOW, LAYER_BANDS
from engine import replace_positions, splice


def ko_config(name: str, p0: int, p1: int) -> dict[str, Any] | None:
    base = {"p0": p0, "p1": p1}
    if name in ("K0", "K0b"):
        return {**base, "g_lo": 0, "g_hi": 10 ** 9, "layers": None}
    if name == "K1":
        return {**base, "g_lo": 0, "g_hi": KO_WINDOW, "layers": None}
    if name == "K2":
        return {**base, "g_lo": KO_WINDOW, "g_hi": 10 ** 9, "layers": None}
    if name in LAYER_BANDS:
        return {**base, "g_lo": 0, "g_hi": 10 ** 9, "layers": set(LAYER_BANDS[name])}
    return None


def build_arm(name: str, pre: dict[str, dict[str, Any]], noun: str, p1: int) -> dict[str, Any]:
    """pre: {'ban': prefill, 'A': prefill(neutral A), 'B': prefill(neutral B)}; noun in {'A','B'}."""
    ban, neu = pre["ban"], pre[noun]
    P = ban["P"]
    if name in ("a", "K0", "K1", "K2", "B1", "B2", "B3"):
        return {"kv": ban["kv"], "r_logits": ban["r_logits"]}
    if name in ("b", "K0b"):
        return {"kv": neu["kv"], "r_logits": neu["r_logits"]}
    if name == "c":
        return {"kv": splice(neu["kv"], ban["kv"], p1), "r_logits": ban["r_logits"]}
    if name == "d":
        return {"kv": splice(ban["kv"], neu["kv"], p1), "r_logits": neu["r_logits"]}
    if name == "e":
        return {"kv": replace_positions(neu["kv"], ban["kv"], [P - 1]), "r_logits": ban["r_logits"]}
    if name == "f":
        return {"kv": replace_positions(splice(neu["kv"], ban["kv"], p1), neu["kv"], [P - 1]),
                "r_logits": neu["r_logits"]}
    if name == "pl":
        return {"kv": splice(pre["A"]["kv"], pre["B"]["kv"], p1), "r_logits": pre["B"]["r_logits"]}
    raise ValueError(name)
