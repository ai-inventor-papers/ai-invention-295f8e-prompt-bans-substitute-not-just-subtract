#!/usr/bin/env python3
"""Prompt scaffold shared by HF and vLLM: one user turn = segment + blank line + SPEC[task].

build_prompt returns token ids from the Qwen3 chat template with enable_thinking=False and no
system message; the template ends with the assistant header and the empty think block, and the
read position R is the last token. Both engines receive these exact ids.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, DISPLAY, PROMPTS_DIR, SPEC  # noqa: E402

TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


@lru_cache(maxsize=1)
def paraphrases() -> dict[str, list[str]]:
    return json.loads((PROMPTS_DIR / "paraphrases.json").read_text())


def segments(task: str, group: str) -> list[str]:
    """Return the list of instruction segments for a prompt group.

    group in {baseline, enumerate, listall, LIST, IMPLEMENT, ONE, LONGNAMES, SHORTNAMES,
    ban:<mode>, mention:<mode>, succession:<mode1>+<mode2>}.
    """
    P = paraphrases()
    if group.startswith("ban:"):
        x = DISPLAY[task][group.split(":", 1)[1]]
        return [t.replace("{X}", x) for t in P["ban"]]
    if group.startswith("mention:"):
        x = DISPLAY[task][group.split(":", 1)[1]]
        return [t.replace("{X}", x) for t in P["mention"]]
    if group.startswith("succession:"):
        m1, m2 = group.split(":", 1)[1].split("+")
        x = f"{DISPLAY[task][m1]} or {DISPLAY[task][m2]}"
        return [t.replace("{X}", x) for t in P["ban"]]
    return list(P[group])


def user_text(segment: str, task: str) -> str:
    return segment + "\n\n" + SPEC[task]


def build_prompt_text(tok, segment: str, task: str) -> str:
    msgs = [{"role": "user", "content": user_text(segment, task)}]
    return tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, tokenize=False)


def build_prompt(tok, segment: str, task: str) -> list[int]:
    text = build_prompt_text(tok, segment, task)
    assert text.endswith(TEMPLATE_TAIL), repr(text[-80:])
    ids = tok(text, add_special_tokens=False)["input_ids"]
    return list(ids)


def suffix_ids(tok, task: str) -> list[int]:
    """Token ids of SPEC + template tail; every prompt of the task must end with exactly these."""
    return list(tok(SPEC[task] + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"])


def check_suffix(tok, ids: list[int], task: str) -> None:
    suf = suffix_ids(tok, task)
    assert ids[-len(suf):] == suf, "condition-specific token near R: suffix mismatch"


def all_groups(task: str) -> list[str]:
    g = ["LIST", "IMPLEMENT", "ONE", "LONGNAMES", "SHORTNAMES", "baseline", "enumerate", "listall"]
    g += [f"ban:{m}" for m in CATALOGUE[task]] + [f"mention:{m}" for m in CATALOGUE[task]]
    return g
