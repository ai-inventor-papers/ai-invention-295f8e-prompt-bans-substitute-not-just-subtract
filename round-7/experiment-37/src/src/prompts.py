#!/usr/bin/env python3
"""Prompt text of every arm (frozen in commit #0; the exact strings are written to predictions/prompts_frozen.json).

S / NE  : spec body + catalogue ban line + two parent blocks (ascending novelty, FunSearch order) + instruction +
          the task's format line.
I0      : the same text without the parent blocks (instruction adapted to 'every listed algorithm').
B0      : the frozen neutral twins W1-W5 (iteration-5 exp27 prompts.jsonl kind 'twin'; T2/T03); A3 has no twin -> plain
          spec_text (deviation D5).
EAP     : iteration-5 enumerate-and-pick, vendored: stage 1 = exp27 'eap' prompt (twin sentence + EAP_A + spec);
          stage 2 = second user turn EAP_B 'Implement approach {i}: {name}. ...' with i drawn by an external RNG.
BINT    : iteration-5 base intent, vendored: Qwen3-8B-Base continues the chat-formatted exp27 'ifg' prompt after a
          forced 'Intent:'; the instruct model continues 'Intent: <intent>\\n' and writes the code.
CAL     : forced 'Implement Y' prompts (spec forced_templates x catalogue display names) + spec_text (non-decisive).
"""

from __future__ import annotations

import ast
import importlib.util
import io
import re
import tokenize
from functools import lru_cache
from typing import Any

from common import VENDOR, read_jsonl

W_TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
IDEA_RE = re.compile(r"^\s*#\s*Idea\s*:\s*(.+?)\s*$", re.M | re.I)
MAX_PARENT_LINES = 120

# iteration-5 exp27 cfg5 strings (vendored copy: inputs/vendor/exp27/src/cfg5.py; verbatim)
EAP_A = ("This is step 1 of 2: do not write any code in this step, and ignore the code-block instruction at the end "
         "of the task for now (you will write the code in step 2). List the distinct algorithms that correctly solve "
         "this task, one per line, formatted as <number>. <algorithm name>: <one-line idea>. List at most 8.")
EAP_B = "Implement approach {i}: {name}. Output only the code in one python code block."
IFG_INSTR = ("Before writing any code, state in one sentence the algorithm you will use, on a single line that "
             "starts with Intent:. Then write the code.")
INTENT_PREFIX = "Intent:"

BAN_LINE = "Known algorithms for this task (your program must not be any of them): {names}."
S_INSTR = ("Write a correct program whose core idea differs from both programs above and from every listed algorithm. "
           "Begin the code with a comment line # Idea: <one sentence>.")
I0_INSTR = ("Write a correct program whose core idea differs from every listed algorithm. "
            "Begin the code with a comment line # Idea: <one sentence>.")
PARENT_HDR = ("Program {letter} (passes all tests; median runtime {ms} ms; novelty {nu:.2f}; core idea: {idea}):")


@lru_cache(maxsize=None)
def _exp27() -> dict[tuple[str, str, str], str]:
    rows = read_jsonl(VENDOR / "exp27" / "prompts" / "prompts.jsonl")
    out = {}
    for r in rows:
        out[(r["task"], r["w"], r["kind"])] = r["user_text"]
    return out


@lru_cache(maxsize=None)
def parsers():
    p = VENDOR / "exp27" / "src" / "parsers.py"
    spec = importlib.util.spec_from_file_location("exp27_parsers", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def catalogue_names(task_obj: dict[str, Any]) -> str:
    return "; ".join(c["display_name"] for c in task_obj["catalogue"])


def idea_of(code: str) -> str | None:
    m = IDEA_RE.search(code or "")
    return m.group(1).strip()[:200] if m else None


def strip_code(code: str, max_lines: int = MAX_PARENT_LINES) -> str:
    """Drop docstrings, comments (except '# Idea:'), blank lines; cap at max_lines."""
    lines = code.splitlines()
    drop: set[int] = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and len(node.body) > 1:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and \
                        isinstance(first.value.value, str):
                    drop |= set(range(first.lineno - 1, first.end_lineno))
    except (SyntaxError, ValueError, RecursionError):
        pass
    cuts: dict[int, int] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.COMMENT and not IDEA_RE.match(tok.string):
                cuts[tok.start[0] - 1] = tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    out = []
    for i, ln in enumerate(lines):
        if i in drop:
            continue
        if i in cuts:
            ln = ln[:cuts[i]].rstrip()
        if not ln.strip():
            continue
        out.append(ln)
    return "\n".join(out[:max_lines])


def parent_idea(p: dict[str, Any], task_obj: dict[str, Any]) -> str:
    i = idea_of(p.get("code") or "")
    if i:
        return i
    lab = p.get("runtime_label")
    return task_obj["display"].get(lab, "an unnamed approach")


def s_user_text(task_obj: dict[str, Any], parents: list[dict[str, Any]]) -> str:
    """parents: list of 2 dicts {code, novelty, median_case_ms, runtime_label}; shown in ascending novelty."""
    ps = sorted(parents, key=lambda p: p["novelty"])
    blocks = []
    for letter, p in zip("AB", ps):
        ms = p.get("median_case_ms")
        ms_s = f"{ms:.3f}" if isinstance(ms, (int, float)) else "n/a"
        hdr = PARENT_HDR.format(letter=letter, ms=ms_s, nu=p["novelty"], idea=parent_idea(p, task_obj))
        blocks.append(f"{hdr}\n```python\n{strip_code(p['code'])}\n```")
    return (f"{task_obj['spec_body']}\n\n{BAN_LINE.format(names=catalogue_names(task_obj))}\n\n"
            + "\n\n".join(blocks) + f"\n\n{S_INSTR}\n\n{task_obj['format_line']}")


def i0_user_text(task_obj: dict[str, Any]) -> str:
    return (f"{task_obj['spec_body']}\n\n{BAN_LINE.format(names=catalogue_names(task_obj))}\n\n{I0_INSTR}\n\n"
            f"{task_obj['format_line']}")


def b0_user_text(task_obj: dict[str, Any], w: str) -> tuple[str, str]:
    """(text, source) - the frozen neutral twin of template w; A3: the plain spec_text (deviation D5)."""
    t = task_obj["task"]
    txt = _exp27().get((t, w, "twin"))
    if txt:
        return txt, f"exp27:{t}:{w}:twin"
    return task_obj["spec_text"], "plain_spec_text"


def eap_stage1_text(task_obj: dict[str, Any], w: str) -> tuple[str, str]:
    t = task_obj["task"]
    txt = _exp27().get((t, w, "eap"))
    if txt:
        return txt, f"exp27:{t}:{w}:eap"
    return f"{EAP_A}\n\n{task_obj['spec_text']}", "reconstructed:EAP_A+spec_text"


def ifg_text(task_obj: dict[str, Any], w: str) -> tuple[str, str]:
    t = task_obj["task"]
    txt = _exp27().get((t, w, "ifg"))
    if txt:
        return txt, f"exp27:{t}:{w}:ifg"
    return f"{IFG_INSTR}\n\n{task_obj['spec_text']}", "reconstructed:IFG_INSTR+spec_text"


def cal_user_text(task_obj: dict[str, Any], mode: str, j: int) -> str:
    tpl = task_obj["forced_templates"][j % len(task_obj["forced_templates"])]
    return f"{tpl.format(j=task_obj['display'][mode])}\n\n{task_obj['spec_text']}"


class ChatFormatter:
    """Qwen3 chat template, thinking disabled; raw prompt strings for vLLM."""

    def __init__(self, tokenizer) -> None:
        self.tok = tokenizer

    def user(self, text: str) -> str:
        return self.tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)

    def multi(self, msgs: list[dict[str, str]]) -> str:
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def with_assistant_prefix(self, text: str, prefix: str) -> str:
        return self.user(text) + prefix

    def n_tokens(self, s: str) -> int:
        return len(self.tok(s, add_special_tokens=False)["input_ids"])


def frozen_prompt_record(task_objs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Every prompt template text, for commit #0."""
    rec: dict[str, Any] = {"EAP_A": EAP_A, "EAP_B": EAP_B, "IFG_INSTR": IFG_INSTR, "INTENT_PREFIX": INTENT_PREFIX,
                           "BAN_LINE": BAN_LINE, "S_INSTR": S_INSTR, "I0_INSTR": I0_INSTR, "PARENT_HDR": PARENT_HDR,
                           "MAX_PARENT_LINES": MAX_PARENT_LINES, "tasks": {}}
    for t, o in task_objs.items():
        rec["tasks"][t] = {"spec_body": o["spec_body"], "format_line": o["format_line"],
                           "catalogue_names": catalogue_names(o), "I0": i0_user_text(o),
                           "B0": {w: b0_user_text(o, w) for w in W_TEMPLATES},
                           "EAP1": {w: eap_stage1_text(o, w) for w in W_TEMPLATES},
                           "IFG": {w: ifg_text(o, w) for w in W_TEMPLATES},
                           "CAL_example": cal_user_text(o, o["modes"][0], 0)}
    return rec
