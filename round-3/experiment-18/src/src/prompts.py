"""Prompt builders: neutral twins (walk), leave-one-survivor and two-step bans (prompt reach), long-form novelty.

Scaffold (exp1 make_prompt): cap_first(segment) + blank line + SPEC, SPEC = DESCRIPTION + blank line + FORMAT.
T1/T2 neutral twins are exp8's frozen neutral_A twins (asserted token-identical); bench twins use the first
neutral noun of the default's slot, padded with ' .' fillers to the chat-formatted token length of the matching
single ban (exp7 rule).  Every chat rendering is asserted to end with the empty think block (thinking off).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from config import (BENCH_DIR, FILLER, INPUTS, LF_FORMAT, LF_PROMPTS, TASKS, W_IDS, W_TEMPLATES, cap_first,
                    model_dir, sha256_text)

EMPTY_THINK_TAIL = "<|im_start|>assistant\n<think>\n\n</think>\n\n"
THINK_TAIL = "<|im_start|>assistant\n"


@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_dir("bf16"))


def ids_of(text: str) -> list[int]:
    return tokenizer()(text, add_special_tokens=False)["input_ids"]


def render_chat(user_text: str, thinking: bool = False) -> str:
    s = tokenizer().apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                        add_generation_prompt=True, enable_thinking=thinking)
    if thinking:
        assert s.endswith(THINK_TAIL) and not s.endswith("</think>\n\n"), "thinking-on tail mismatch"
    else:
        assert s.endswith(EMPTY_THINK_TAIL), "empty think block tail missing"
    return s


def chat_ids(user_text: str, thinking: bool = False) -> list[int]:
    return ids_of(render_chat(user_text, thinking))


@lru_cache(maxsize=1)
def _frozen_exp8() -> dict[str, Any]:
    return json.loads((INPUTS / "exp8" / "frozen_prompts.json").read_text())


@lru_cache(maxsize=1)
def _suite_desc() -> dict[str, str]:
    import common as suite_common  # suite/common.py (exp1 canonical)

    return {"T1": suite_common.DESCRIPTION["t1"], "T2": suite_common.DESCRIPTION["t2"],
            "FORMAT": suite_common.FORMAT_TEXT}


def description(task: str) -> str:
    if TASKS[task]["family"] == "path":
        return _suite_desc()[task]
    return cap_first(TASKS[task]["description"])


def spec_text(task: str) -> str:
    if TASKS[task]["family"] == "path":
        return _suite_desc()[task] + "\n\n" + _suite_desc()["FORMAT"]
    return TASKS[task]["spec_text"]


def make_prompt(task: str, segment: str | None) -> str:
    return (cap_first(segment) + "\n\n" + spec_text(task)) if segment else spec_text(task)


def join_or(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


@lru_cache(maxsize=None)
def bench_noun(task: str, mode: str) -> str:
    nn = json.loads((BENCH_DIR / TASKS[task]["task_id"] / "neutral_nouns.json").read_text())
    return nn[mode]["nouns"][0]["word"]


def padded_neutral(task: str, w: str, ban_segment: str, noun: str) -> tuple[str, int, int]:
    """exp7 rule: neutral segment + d x filler with d = ban tokens - neutral tokens (chat-formatted)."""
    base = cap_first(W_TEMPLATES[w].format(N=noun))
    n_ban = len(chat_ids(make_prompt(task, ban_segment)))
    seg = base
    d = n_ban - len(chat_ids(make_prompt(task, seg)))
    if d > 0:
        seg = base + FILLER * d
        for _ in range(6):  # tokenizer merges can make the pad overshoot/undershoot by a token
            diff = n_ban - len(chat_ids(make_prompt(task, seg)))
            if diff == 0:
                break
            d += diff
            seg = base + FILLER * max(0, d)
    n_neu = len(chat_ids(make_prompt(task, seg)))
    return seg, n_ban, n_neu


@lru_cache(maxsize=None)
def neutral_twins(task: str) -> dict[str, dict[str, Any]]:
    """W1-W5 neutral twins of the single ban of the task's default (the walk's ban-free frame)."""
    out: dict[str, dict[str, Any]] = {}
    D = TASKS[task]["default"]
    if TASKS[task]["family"] == "path":
        fz = _frozen_exp8()["tasks"][TASKS[task]["suite"]]["templates"]
        for w in W_IDS:
            nt = fz[w]["neutral_A"]
            ids = chat_ids(nt["user_text"])
            assert ids == nt["ids"], f"{task} {w}: rendered neutral twin differs from exp8 frozen ids"
            ti = render_chat(nt["user_text"]).index("Task:")
            out[w] = {"segment": nt["segment"], "user_text": nt["user_text"], "ids": ids,
                      "ban_tokens": len(fz[w]["ban"]["ids"]), "neutral_tokens": len(ids),
                      "task_offset_chars": ti, "source": "exp8 frozen_prompts.json neutral_A", "noun": nt["noun"]}
        return out
    noun = bench_noun(task, D)
    for w in W_IDS:
        ban_seg = W_TEMPLATES[w].format(N=TASKS[task]["display"][D])
        seg, n_ban, n_neu = padded_neutral(task, w, ban_seg, noun)
        ut = make_prompt(task, seg)
        out[w] = {"segment": seg, "user_text": ut, "ids": chat_ids(ut), "ban_tokens": n_ban, "neutral_tokens": n_neu,
                  "source": f"bench neutral_nouns.json[{D}] noun 0, ' .' padding", "noun": noun}
    return out


def ban_prompt(task: str, w: str, banned: list[str]) -> dict[str, Any]:
    names = [TASKS[task]["display"][m] for m in banned]
    seg = cap_first(W_TEMPLATES[w].format(N=join_or(names)))
    ut = make_prompt(task, seg)
    return {"segment": seg, "user_text": ut, "ids": chat_ids(ut), "prompt_sha256": sha256_text(ut)}


def los_banned(task: str, survivor: str) -> list[str]:
    return [m for m in TASKS[task]["catalogue"] if m != survivor]


def longform_prompt(task: str, lf: str) -> str:
    return LF_PROMPTS[lf] + "\n\n" + description(task) + "\n\n" + LF_FORMAT
