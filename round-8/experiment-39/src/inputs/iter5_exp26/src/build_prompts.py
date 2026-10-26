#!/usr/bin/env python3
"""Render every panel-B prompt (twins W1-W5, novelty, association, plain completion) with the INSTRUCT tokenizer, check
the banned-word grep on every spec, and assert that the base tokenizer re-encodes every rendered prompt to identical
ids (U4). Writes data/prompts.jsonl, units/<u>/neutral_nouns.json and units/<u>/positions.json. (This is the script
that was run as a scratch file before commit #0; it has to precede src/protocol0.py.)"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transformers import AutoTokenizer  # noqa: E402

from cfg5 import BASE_ID, BASE_REVISION, MODEL_ID, MODEL_REVISION, model_path  # noqa: E402
from prompts5 import build_all  # noqa: E402
from units_spec import UNIT_ORDER, UNITS, grep_banned, spec_text  # noqa: E402

tok = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
btok = AutoTokenizer.from_pretrained(model_path(BASE_ID, BASE_REVISION))
for u in UNIT_ORDER:
    hits = grep_banned(u, UNITS[u]["description"])
    assert not hits, (u, hits)
    print(u, "spec tokens:", len(tok(spec_text(u))["input_ids"]))
rows = build_all(tok, UNIT_ORDER)
for r in rows:
    assert btok(tok.decode(r["ids"]), add_special_tokens=False)["input_ids"] == r["ids"], r["pid"]
print(len(rows), "prompts; base tokenizer ids identical")
