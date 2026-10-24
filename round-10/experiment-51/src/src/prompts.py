#!/usr/bin/env python3
"""FunSearch-style prompt construction, chat-template rendering with assistant prefill, and body trimming.

The prompt is identical across arms except IDEA's one appended sentence. Stored programs have the form
'def priority(item, bins):\\n' + body; version i is rendered with FunSearch's docstrings and recursive calls renamed."""
from __future__ import annotations

import re

PREAMBLE = ("Online 1-D bin packing: items arrive one at a time and each must be placed immediately. priority(item, bins) "
            "receives the item size and a numpy array with the remaining capacities of every bin that can hold the item "
            "(unused bins, at full capacity, included); the item goes to the bin with the highest score. The goal is to "
            "use as few bins as possible. Only numpy (np) and math may be used.")
MODULE_DOC = '"""Finds good assignment for online 1d bin packing."""'
V0_DOC = ('    """Returns priority with which we want to add item to each bin.\n\n'
          '    Args:\n'
          '        item: Size of item to be added to the bin.\n'
          '        bins: Array of capacities for each bin.\n\n'
          '    Return:\n'
          '        Array of same size as bins with priority score of each bin.\n'
          '    """\n')
SIG = "def priority_v{i}(item: float, bins: np.ndarray) -> np.ndarray:\n"
STOPS = ["```", "\ndef ", "\nclass ", "\nif __name__", "\nprint("]
MAX_TOKENS = 512
SEED_BODY_BF = "    return -(bins - item)\n"
SEED_BODY_FF = "    return -np.arange(len(bins))\n"


def body_of(program: str) -> str:
    """Body of a stored program (everything after the first line 'def priority(item, bins):')."""
    first, _, rest = program.partition("\n")
    assert first.startswith("def priority("), first
    return rest


def render_version(body: str, i: int) -> str:
    body = re.sub(r"\bpriority\s*\(", f"priority_v{i}(", body)
    doc = V0_DOC if i == 0 else f'    """Improved version of `priority_v{i - 1}`."""\n'
    return SIG.format(i=i) + doc + body.rstrip("\n") + "\n"


def user_message(bodies: list[str], idea: bool) -> str:
    """bodies are sorted worse first (v0 = worst). k = len(bodies) in {1, 2}."""
    k = len(bodies)
    block = MODULE_DOC + "\nimport numpy as np\n\n\n" + "\n\n".join(render_version(b, i) for i, b in enumerate(bodies))
    instr = f"Write priority_v{k}, an improved version of priority_v{k - 1}. Return only the code of priority_v{k}."
    if idea:
        instr += (f" Write priority_v{k} based on an idea different from "
                  f"{'the function above' if k == 1 else 'both functions above'}.")
    return PREAMBLE + "\n\n```python\n" + block + "```\n\n" + instr


def prefill(k: int) -> str:
    return "```python\n" + SIG.format(i=k) + f'    """Improved version of `priority_v{k - 1}`."""\n'


def render(tokenizer, bodies: list[str], idea: bool) -> tuple[str, list[int]]:
    """Chat template (thinking off, generation prompt) + assistant prefill; tokenised once."""
    msgs = [{"role": "user", "content": user_message(bodies, idea)}]
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    text += prefill(len(bodies))
    ids = tokenizer.encode(text, add_special_tokens=False)
    return text, ids


def trim_body(completion: str, k: int) -> str:
    """Keep lines up to the first non-empty line with indent 0; rename recursive calls priority_v{k}( -> priority(."""
    out = []
    for ln in completion.split("\n"):
        if ln.strip() and not ln[0].isspace():
            break
        out.append(ln)
    body = "\n".join(out).rstrip() + "\n"
    if not body.strip():
        body = ""
    return re.sub(rf"\bpriority_v{k}\s*\(", "priority(", body)


def program_from(completion: str, k: int) -> str:
    return "def priority(item, bins):\n" + trim_body(completion, k)
