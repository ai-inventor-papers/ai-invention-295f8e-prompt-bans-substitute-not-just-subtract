#!/usr/bin/env python3
"""Quick per-condition summary of labelled raw samples (pass rate, format, enumerated, label counts)."""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import LABEL_CACHE, RAW_DIR, read_jsonl, sha256_text  # noqa: E402

for f in sorted(RAW_DIR.glob("*.jsonl")):
    rows = read_jsonl(f)
    labs = []
    for r in rows:
        p = LABEL_CACHE / r["task"] / f"{sha256_text(r['text'])}.json"
        if p.exists():
            labs.append(json.loads(p.read_text()))
    if not labs:
        continue
    n = len(labs)
    pc = [l for l in labs if l["passed"]]
    lab = collections.Counter((l["label"] or f"?{l['label_runtime']}/{l['label_ast']}") for l in pc)
    print(f"{f.stem:42s} n={n:3d}/{len(rows):3d} pass={len(pc)/n:.2f} fmt={sum(l['format_ok'] for l in labs)/n:.2f} "
          f"enum={sum(l['enumerated'] for l in labs)/n:.2f} len={sum(r['finish_reason']=='length' for r in rows)/len(rows):.2f} "
          f"{dict(lab.most_common(6))}")
