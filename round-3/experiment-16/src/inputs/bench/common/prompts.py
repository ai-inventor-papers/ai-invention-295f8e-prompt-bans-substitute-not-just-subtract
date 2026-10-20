"""The only three prompt builders of the bench: baseline, forced and association.

Scaffold (exp1): [condition segment] + blank line + SPEC, SPEC = DESCRIPTION + blank line + FORMAT,
first character of every segment upper-cased.  No ban / mention / neutral / nonce / novelty
builder exists on purpose.
"""

from __future__ import annotations

from .catalogue import (ASSOCIATION_TEMPLATE, DESCRIPTIVE_FORCED_TEMPLATE, FORCED_TEMPLATES, FORMAT_LINE,
                        TASKS, display_name, mode_description)


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def spec_text(task: str) -> str:
    return _cap(TASKS[task]["description"]) + "\n\n" + _cap(FORMAT_LINE)


def build_baseline(task: str) -> str:
    return spec_text(task)


def forced_segment(task: str, mode: str, k: int) -> str:
    if k == -1:  # descriptive variant (job C only, logged)
        d = mode_description(task, mode)
        d = d[0].upper() + d[1:]
        return _cap(DESCRIPTIVE_FORCED_TEMPLATE.format(d=d.rstrip(".") + "."))
    return _cap(FORCED_TEMPLATES[k].format(j=display_name(task, mode)))


def build_forced(task: str, mode: str, k: int) -> str:
    return forced_segment(task, mode, k) + "\n\n" + spec_text(task)


def build_association(task: str, mode: str) -> str:
    return _cap(TASKS[task]["description"]) + "\n\n" + _cap(ASSOCIATION_TEMPLATE.format(x=display_name(task, mode)))


def render_chat(tokenizer, user_text: str) -> str:
    """Qwen3 chat template, thinking disabled (adds the empty think block)."""
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": user_text}], tokenize=False, add_generation_prompt=True,
        enable_thinking=False)
