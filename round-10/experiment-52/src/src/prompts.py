#!/usr/bin/env python3
"""S4: the fixed user turn (FunSearch best-shot prompt, v0 = worse parent, v1 = better parent), the chat render with
the empty think block and the assistant code prefill, the stop list and the body extraction."""
from __future__ import annotations

import re

INSTRUCTION = "Complete the Python module below by writing the body of priority_v2. Reply with code only."
IDEA_SENTENCE = "Write priority_v2 based on an idea different from both functions above."
MODULE_DOC = '"""Finds good assignment for online 1d bin packing."""'
SIG = "(item: float, bins: np.ndarray) -> np.ndarray:"
V0_DOC = ('    """Returns priority with which we want to add item to each bin.\n\n'
          '    Args:\n'
          '        item: Size of item to be added to the bin.\n'
          '        bins: Array of capacities for each bin.\n\n'
          '    Return:\n'
          '        Array of same size as bins with priority score of each bin.\n'
          '    """')
V1_DOC = '    """Improved version of priority_v0."""'
PREFILL = '```python\ndef priority_v2' + SIG + '\n    """Improved version of priority_v1."""\n'
PREFILL_CODE = PREFILL.split("\n", 1)[1]  # the prefill without the fence line (for tokenize spans)
STOPS = ["\n```", "\ndef ", "\nclass ", "\nif __name__", "\nprint(", "\n@"]
MAX_TOKENS = 512
TEMPLATE_NAME = "funsearch_bestshot_v10"
PROGRAM_HEADER = "def priority" + SIG
BF_BODY = "    return -(bins - item)"
FF_BODY = "    return -np.arange(len(bins))"


def body_of(program: str) -> str:
    """Body of a stored program (everything after the def line), docstring-free by construction."""
    lines = program.split("\n")
    assert lines[0].startswith("def priority"), lines[0]
    body = "\n".join(lines[1:]).rstrip()
    return _drop_leading_docstring(body)


def _drop_leading_docstring(body: str) -> str:
    """Remove a leading docstring the model may have written inside the body (FunSearch replaces docstrings)."""
    m = re.match(r'^(\s*)("""|\'\'\')(.*?)\2[ \t]*\n', body + "\n", flags=re.S)
    if m:
        rest = (body + "\n")[m.end():].rstrip()
        if rest.strip():
            return rest
    return body


def _rename_calls(body: str, k: int) -> str:
    return re.sub(r"\bpriority\s*\(", f"priority_v{k}(", body)


def user_turn(worse_program: str, better_program: str, idea: bool = False) -> str:
    v0 = _rename_calls(body_of(worse_program), 0)
    v1 = _rename_calls(body_of(better_program), 1)
    code = (f"{MODULE_DOC}\nimport numpy as np\n\n\n"
            f"def priority_v0{SIG}\n{V0_DOC}\n{v0}\n\n\n"
            f"def priority_v1{SIG}\n{V1_DOC}\n{v1}\n")
    text = f"{INSTRUCTION}\n\n```python\n{code}```"
    if idea:
        text += f"\n\n{IDEA_SENTENCE}"
    return text


def render(tokenizer, user: str) -> tuple[str, list[int]]:
    """Chat template (thinking off) + assistant prefill, tokenized without special tokens."""
    txt = tokenizer.apply_chat_template([{"role": "user", "content": user}], add_generation_prompt=True,
                                        enable_thinking=False, tokenize=False)
    assert "<think>\n\n</think>" in txt, "empty think block missing from the rendered template"
    txt = txt + PREFILL
    assert txt.endswith(PREFILL)
    ids = tokenizer(txt, add_special_tokens=False)["input_ids"]
    return txt, ids


def cut_at_stop(text: str) -> tuple[str, bool]:
    """Text up to the first stop string (and whether a stop occurred)."""
    pos = [text.find(s) for s in STOPS if s in text]
    if not pos:
        return text, False
    return text[:min(pos)], True


def extract_body(completion: str) -> str:
    """Up to the first stop; keep lines until the first non-empty line with indent 0; rstrip."""
    text, _ = cut_at_stop(completion)
    keep = []
    for ln in text.split("\n"):
        if ln.strip() and not ln[:1].isspace():
            break
        keep.append(ln)
    return "\n".join(keep).rstrip()


def program_from_completion(completion: str) -> str:
    """program = header + newline + body (an empty body is a syntax failure at evaluation)."""
    return PROGRAM_HEADER + "\n" + extract_body(completion)


def seed_program(body: str) -> str:
    return PROGRAM_HEADER + "\n" + body
