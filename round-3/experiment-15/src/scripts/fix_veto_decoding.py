#!/usr/bin/env python3
"""Correct the text of veto hit rows to the exact (no-cleanup) decoding of their token ids, matching vLLM's own
detokenisation, and drop the labels of rows whose extracted code changed so that they are re-labelled."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import label as L  # noqa: E402
from src import prompts_llama as P  # noqa: E402
from src.ws import DATA, RESULTS, read_jsonl, write_json, write_jsonl  # noqa: E402

tok = P.tokenizer()
raw = read_jsonl(DATA / "raw_gen.jsonl")
changed_text, changed_code = 0, set()
for r in raw:
    if r.get("phase") in ("D2", "D3") and r.get("hit"):
        d = tok.decode(r["out_ids"], skip_special_tokens=True, clean_up_tokenization_spaces=False)
        if d != r["text"]:
            changed_text += 1
            a, _ = L.extract(d)
            b, _ = L.extract(r["text"])
            if a != b:
                changed_code.add(r["row_id"])
            r["text_decode_fixed"] = True
            r["text"] = d
write_jsonl(DATA / "raw_gen.jsonl", raw)
labs = read_jsonl(L.LABELS_RAW)
keep = [l for l in labs if l["row_id"] not in changed_code]
write_jsonl(L.LABELS_RAW, keep)
rec = {"rows_text_changed": changed_text, "rows_code_changed_relabelled": len(changed_code),
       "labels_dropped": len(labs) - len(keep)}
write_json(RESULTS / "veto_decode_fix.json", rec)
print(rec)
