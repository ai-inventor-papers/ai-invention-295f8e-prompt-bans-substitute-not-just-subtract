#!/usr/bin/env python3
"""Adjudicate every pending runtime/AST disagreement (all units) with the blind judges before the final analysis;
unresolved items stay 'disputed' (excluded from shares, counted)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import units_extra  # noqa: E402,F401
from cfg5 import LABELS, read_jsonl, setup_logging  # noqa: E402
from labels_view import adjudicate_pending  # noqa: E402

if __name__ == "__main__":
    setup_logging("adjudicate_all")
    units = sorted({l["unit"] for l in read_jsonl(LABELS)})
    total = 0
    while True:
        n = adjudicate_pending(units, max_items=400)
        total += n
        if n == 0:
            break
    print(f"adjudicated {total} disagreements")
