#!/usr/bin/env python3
"""One-off: the first pt-chat batch (T2, slots 0-9) ran with the 1,536 cap before the pt-chat cap was lowered to
640. Under CRN sampling the first 640 tokens are identical to a 640-capped run, so the rows are truncated to 640
generated tokens (text re-decoded, finish_reason 'length' when cut) instead of being regenerated."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, write_jsonl
import prompts as PG

CAP = 640
p = DATA_DIR / "raw_ptchat.jsonl"
rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
tok = PG.tokenizer()
n_cut = 0
for r in rows:
    if r["n_new_tokens"] > CAP:
        ids = r["token_ids"][:CAP]
        r["token_ids"] = ids
        r["text"] = tok.decode(ids, skip_special_tokens=True)
        r["n_new_tokens"] = CAP
        r["finish_reason"] = "length"
        r["truncated_from_cap"] = 1536
        n_cut += 1
    r["max_new"] = CAP
write_jsonl(p, rows)
print(f"truncated {n_cut} of {len(rows)} rows to {CAP} tokens")
