#!/usr/bin/env python3
"""Llama-3.1 prompt builders for the frozen bench (protocol v3).

Bench text = cap_first(segment) + blank line + spec.json spec_text (bench/common/prompts.py scaffold); rendered with
the default Llama-3.1 chat template and date_string '26 Jul 2024'; encoded with add_special_tokens=False.
Every prompt is a dict {task, cond, kind, X, w, h, segment, text, ids, sha, seg_start, spec_start, spec_end, R, k, noun}.
Ban / neutral-twin / nonce / novelty segments exist only here (the bench deliberately has no builder for them).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from src.ws import (BENCH, DATE_STRING, EXP10, FILLER, INPUTS, MAX_PAD, NONCE_X, NOVELTY, TEMPLATES, ids_sha,
                    model_path)

from bench.common import catalogue as CAT  # noqa: E402  (frozen bench, read-only copy)
from bench.common import prompts as BP  # noqa: E402

USER_HDR = "<|start_header_id|>user<|end_header_id|>\n\n"
EOT = 128009


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


@lru_cache(maxsize=None)
def spec_json(task: str) -> dict[str, Any]:
    return json.loads((BENCH / CAT.TASKS[task]["task_id"] / "spec.json").read_text())


@lru_cache(maxsize=None)
def neutral_nouns(task: str) -> dict[str, Any]:
    return json.loads((BENCH / CAT.TASKS[task]["task_id"] / "neutral_nouns.json").read_text())


def modes(task: str) -> list[str]:
    return [c["mode"] for c in spec_json(task)["catalogue"]]


def display(task: str, mode: str) -> str:
    return CAT.display_name(task, mode)


@lru_cache(maxsize=1)
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_path())


def render(text: str) -> tuple[str, list[int], list[tuple[int, int]]]:
    tok = tokenizer()
    rendered = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                       add_generation_prompt=True, date_string=DATE_STRING)
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    return rendered, list(enc["input_ids"]), [tuple(o) for o in enc["offset_mapping"]]


def _token_at_char(offsets: list[tuple[int, int]], char: int) -> int:
    for i, (a, b) in enumerate(offsets):
        if a == char and b > a:
            return i
    for i, (a, b) in enumerate(offsets):  # spec start inside a merged token (should not happen; asserted by tests)
        if a <= char < b:
            return i
    raise AssertionError(f"no token covers char {char}")


def build_text(task: str, segment: str | None) -> str:
    spec = spec_json(task)["spec_text"]
    return spec if segment is None else cap(segment) + "\n\n" + spec


def build(task: str, kind: str, segment: str | None, *, cond: str, X: str | None = None, w: int | None = None,
          h: int | None = None, text: str | None = None) -> dict[str, Any]:
    if text is None:
        text = build_text(task, segment)
    rendered, ids, offs = render(text)
    tok = tokenizer()
    assert ids.count(tok.bos_token_id) == 1 and ids[0] == tok.bos_token_id, "exactly one BOS at index 0"
    assert "Today Date: " + DATE_STRING in rendered
    R = len(ids) - 1
    assert ids[R] == 271 and ids[R - 1] == 128007, "R must be the two-newline token after <|end_header_id|>"
    cstart = rendered.index(USER_HDR) + len(USER_HDR)
    seg_start = _token_at_char(offs, cstart)
    spec = spec_json(task)["spec_text"]
    sp = rendered.find(spec, cstart) if kind != "association" else -1
    spec_start = _token_at_char(offs, sp) if sp >= 0 else None
    eot_pos = ids.index(EOT, seg_start)
    spec_end = eot_pos - 1
    return {"task": task, "cond": cond, "kind": kind, "X": X, "w": w, "h": h, "segment": segment, "text": text,
            "ids": ids, "sha": ids_sha(ids), "seg_start": seg_start, "spec_start": spec_start, "spec_end": spec_end,
            "R": R, "k": 0, "noun": None}


# ------------------------------------------------------------------------------------------------ nouns
@lru_cache(maxsize=1)
def noun_bank() -> list[dict[str, Any]]:
    tok = tokenizer()
    bank = json.loads((EXP10 / "data" / "noun_bank.json").read_text())
    excl = set(json.loads((INPUTS / "exp7" / "templates_nouns_padding.json").read_text())["templates"]["noun_exclusions"])
    out = []
    for r in bank:
        if r["word"] in excl:
            continue
        r = dict(r)
        r["llama_tokens"] = len(tok(" " + r["word"], add_special_tokens=False)["input_ids"])
        out.append(r)
    return out


def bank_ranked(name: str, used: set[str]) -> list[str]:
    tok = tokenizer()
    n = len(tok(" " + name, add_special_tokens=False)["input_ids"])
    rk = sorted(noun_bank(), key=lambda r: (abs(r["llama_tokens"] - n), -float(r["subtlex"]), r["word"]))
    return [r["word"] for r in rk if r["word"] not in used]


def used_nouns(task: str) -> set[str]:
    return {nn["word"] for v in neutral_nouns(task).values() for nn in v["nouns"]}


# ------------------------------------------------------------------------------------------------ builders
def p_ban(task: str, mode: str, w: int) -> dict[str, Any]:
    return build(task, "ban", TEMPLATES[w].format(X=display(task, mode)), cond=f"ban:{mode}:w{w}", X=mode, w=w)


def _pad_to(task: str, ban: dict[str, Any], w: int, noun: str, *, cond: str, X: str | None,
            h: int) -> dict[str, Any] | None:
    base = TEMPLATES[w].format(X=noun)
    for k in range(0, MAX_PAD + 1):
        p = build(task, "neutral", base + FILLER * k, cond=cond, X=X, w=w, h=h)
        if len(p["ids"]) > len(ban["ids"]):
            return None
        if (len(p["ids"]) == len(ban["ids"]) and p["spec_start"] == ban["spec_start"]
                and p["ids"][p["spec_start"]:] == ban["ids"][ban["spec_start"]:]):
            p["k"] = k
            p["noun"] = noun
            return p
    return None


@lru_cache(maxsize=None)
def _twin_cached(task: str, mode: str, w: int, h: int, family: str) -> str:
    ban = p_ban(task, mode, w)
    nn = neutral_nouns(task)[mode]["nouns"]
    first = nn[h]["word"]
    cond = f"{family}:w{w}:h{h}"
    p = _pad_to(task, ban, w, first, cond=cond, X=mode, h=h)
    tried = [first]
    if p is None:
        used = used_nouns(task)
        for cand in bank_ranked(display(task, mode), used):
            tried.append(cand)
            p = _pad_to(task, ban, w, cand, cond=cond, X=mode, h=h)
            if p is not None:
                break
    assert p is not None, f"no twin for {task} {mode} w{w} h{h}"
    p["nouns_tried"] = tried
    return json.dumps(p)


def p_twin(task: str, mode: str, w: int, h: int, family: str = "twin") -> dict[str, Any]:
    """Token-length-matched neutral twin of ban(mode, w): noun A (h=0) / B (h=1) + k x ' .'."""
    return json.loads(_twin_cached(task, mode, w, h, family))


def p_nonce(task: str, w: int) -> dict[str, Any]:
    return build(task, "nonce", TEMPLATES[w].format(X=NONCE_X), cond=f"nonce:w{w}", w=w)


def p_novelty(task: str) -> dict[str, Any]:
    return build(task, "novelty", NOVELTY, cond="novelty")


def p_forced(task: str, mode: str, k: int) -> dict[str, Any]:
    kind = "forced_desc" if k == -1 else "forced"
    return build(task, kind, BP.forced_segment(task, mode, k), cond=f"forced:{mode}:k{k}", X=mode, w=k)


def p_assoc(task: str, mode: str) -> dict[str, Any]:
    return build(task, "association", None, cond=f"association:{mode}", X=mode, text=BP.build_association(task, mode))


def p_copy_twin(task: str, prog: str) -> dict[str, Any]:
    seg = "Here is a correct solution to this task:\n```python\n" + prog.strip("\n") + "\n```\nWrite a correct solution."
    return build(task, "copy_twin", seg, cond="copy_twin")


def p_copy_ban(task: str, prog: str, mode: str) -> dict[str, Any]:
    seg = ("Here is a correct solution to this task:\n```python\n" + prog.strip("\n") + "\n```\n"
           f"Write a correct solution that does not use {display(task, mode)}.")
    return build(task, "copy_ban", seg, cond=f"copy_ban:{mode}", X=mode)
