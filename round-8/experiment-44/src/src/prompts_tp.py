#!/usr/bin/env python3
"""Prompt renderer (Stage 1). Prompt = Capitalise(segment) + blank line + SPEC, SPEC = spec.txt verbatim.

baseline(s)   = baseline_templates[s % 10] + '\\n\\n' + SPEC
ban(w, B)     = cap_first(W_w with {X} = display names of B joined 'A, B, C, D or E' in canonical order rotated by
                W_ROT[w]) + '\\n\\n' + SPEC  (W1..W5 rotate by w-1 as in iteration 2; P6/P7 continue the cycle)
forced(a,t,j) = cap_first(forced_templates[t] with {X} = alias_j(a)) + '\\n\\n' + SPEC  (10 x 3 = 30 per algorithm)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from common import (ALIAS_TABLE, CANON_ORDER, CONFIRM_SLOTS, DISPLAY, INPUTS, SCREEN_SLOTS, W_ROT, W_TEMPLATES,
                    cap_first, join_names_or, read_json, rotate, sha256_text, spec_text)

FROZEN_PATH = INPUTS / "exp9" / "prompts" / "frozen_prompts.json"
SPEC_PATH = INPUTS / "exp9" / "tasks" / "t1_grid" / "spec.txt"


@lru_cache(maxsize=1)
def frozen() -> dict[str, Any]:
    return read_json(FROZEN_PATH)


@lru_cache(maxsize=1)
def SPEC() -> str:
    raw = SPEC_PATH.read_text()
    s = raw[:-1] if raw.endswith("\n") else raw
    assert s == spec_text(), "spec.txt differs from the frozen T1 DESCRIPTION + FORMAT"
    assert frozen()["tasks"]["t1"]["spec"] == s, "frozen_prompts spec differs from spec.txt"
    return s


def baseline_templates() -> list[str]:
    t = frozen()["baseline_templates"]
    assert len(t) == 10
    return list(t)


def forced_templates() -> list[str]:
    t = frozen()["forced_templates"]
    assert len(t) == 10 and len(set(t)) == 10
    return list(t)


def make_prompt(segment: str) -> str:
    return cap_first(segment) + "\n\n" + SPEC()


def baseline_prompt(slot: int) -> dict[str, Any]:
    seg = baseline_templates()[slot % 10]
    return {"arm": "baseline", "slot": slot, "template": f"B{slot % 10}", "segment": seg, "prompt": make_prompt(seg)}


def ban_names(banned: list[str], template: str) -> list[str]:
    order = [k for k in CANON_ORDER if k in banned]
    return [DISPLAY[k] for k in rotate(order, W_ROT[template])]


def ban_segment(banned: list[str], template: str) -> str:
    return cap_first(W_TEMPLATES[template].replace("{X}", join_names_or(ban_names(banned, template))))


def ban_prompt(banned: list[str], template: str, slot: int, arm: str = "ban") -> dict[str, Any]:
    seg = ban_segment(banned, template)
    return {"arm": arm, "slot": slot, "template": template, "segment": seg, "prompt": make_prompt(seg),
            "banned": sorted(banned, key=CANON_ORDER.index)}


def split_slots(n: int, plan: list[tuple[str, int]]) -> list[str]:
    """Template per slot. At the planned N the committed counts are used; otherwise the counts scale evenly."""
    planned_n = sum(c for _, c in plan)
    if n == planned_n:
        counts = [c for _, c in plan]
    else:
        base, rem = divmod(n, len(plan))
        counts = [base + (1 if i < rem else 0) for i in range(len(plan))]
    out: list[str] = []
    for (tpl, _), c in zip(plan, counts):
        out += [tpl] * c
    return out


def screen_ban_prompts(banned: list[str], n: int) -> list[dict[str, Any]]:
    return [ban_prompt(banned, tpl, s, "ban") for s, tpl in enumerate(split_slots(n, SCREEN_SLOTS))]


def confirm_ban_prompts(banned: list[str], n: int) -> list[dict[str, Any]]:
    return [ban_prompt(banned, tpl, s, "confirm") for s, tpl in enumerate(split_slots(n, CONFIRM_SLOTS))]


def forced_prompt(alg: str, t: int, j: int) -> dict[str, Any]:
    seg = forced_templates()[t].replace("{X}", ALIAS_TABLE[alg][j])
    return {"arm": "forced", "algorithm": alg, "template": t, "alias": j, "group": t * 3 + j,
            "segment": cap_first(seg), "prompt": make_prompt(seg)}


def forced_set() -> list[dict[str, Any]]:
    """300 forced prompts: 10 algorithms x 10 templates x 3 aliases; group = (template, alias) pair (30 groups)."""
    return [forced_prompt(a, t, j) for a in CANON_ORDER for t in range(10) for j in range(3)]


def render_chat(tokenizer: Any, prompt: str, thinking: bool) -> str:
    """Official HF chat template, add_generation_prompt=True, enable_thinking per configuration (ignored by
    templates without the switch)."""
    msgs = [{"role": "user", "content": prompt}]
    try:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                             enable_thinking=thinking)
    except TypeError:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def renderer_checks(exp9_top5_w1_prompt: str | None) -> dict[str, Any]:
    """T2 renderer tests: byte check vs the iteration-2 TOP5 W1 prompt, rotation, SPEC identity everywhere."""
    out: dict[str, Any] = {}
    top5 = ["bfs", "dfs", "gbfs", "iddfs", "astar"]
    mine = ban_prompt(top5, "W1", 0)["prompt"]
    out["top5_w1_sha256_ours"] = sha256_text(mine)
    if exp9_top5_w1_prompt is not None:
        out["top5_w1_sha256_iter2"] = sha256_text(exp9_top5_w1_prompt)
        out["top5_w1_byte_identical"] = mine == exp9_top5_w1_prompt
    out["rotation"] = {w: ban_names(top5, w)[0] for w in W_ROT}
    out["rotation_ok"] = len({tuple(ban_names(top5, w)) for w in ("W1", "W2", "W3", "W4", "W5")}) == 5
    spec = SPEC()
    prompts = [p["prompt"] for p in forced_set()] + [baseline_prompt(s)["prompt"] for s in range(10)]
    prompts += [ban_prompt(top5, w, 0)["prompt"] for w in W_ROT]
    out["n_checked"] = len(prompts)
    out["spec_identical_all"] = all(p.endswith("\n\n" + spec) for p in prompts)
    out["n_forced"] = len(forced_set())
    out["n_forced_unique"] = len({p["prompt"] for p in forced_set()})
    return out
