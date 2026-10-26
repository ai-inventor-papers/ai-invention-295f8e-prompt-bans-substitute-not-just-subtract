#!/usr/bin/env python3
"""First approach named in a thinking trace: case-insensitive earliest match of the committed lexicon
(cfg5.FIRST_APPROACH_LEXICON; identical logic to vllm_think.first_approach, kept separate so the HF process never
imports the vLLM script)."""

from __future__ import annotations

import re

from cfg5 import FIRST_APPROACH_LEXICON


def first_approach(text: str | None) -> tuple[str | None, int | None]:
    if not text:
        return (None, None)
    best: tuple[int, int, str] | None = None
    for pri, (name, pat) in enumerate(FIRST_APPROACH_LEXICON):
        flags = 0 if name == "a_star" else re.IGNORECASE
        m = re.search(pat, text, flags)
        if m and (best is None or (m.start(), pri) < (best[0], best[1])):
            best = (m.start(), pri, name)
    return (best[2], best[0]) if best else (None, None)
