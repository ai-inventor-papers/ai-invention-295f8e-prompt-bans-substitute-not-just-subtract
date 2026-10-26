#!/usr/bin/env python3
"""Vendor the small prompt index of iteration 8's 181 MB states file (kind, algorithm, group, template, blocks) into
inputs/forced_index_C6_nf4.json, so that a published copy without the states file can still run item 0e (gates E1-E3
and every statistic; only the E4 cross-check needs the states themselves). Run once; the index records the source hash."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recompute as RC  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
src = RC.ART[RC.TP] / "cache/states/smean_C6_nf4.npz"
z = np.load(src, allow_pickle=False)
h = hashlib.sha256(src.read_bytes()).hexdigest()
out = {"source": f"{RC.TP}:cache/states/smean_C6_nf4.npz", "source_sha256": h,
       **{k: z[k].tolist() for k in ("kind", "algorithm", "group", "template", "blocks", "sel_blocks")}}
(ROOT / "inputs/forced_index_C6_nf4.json").write_text(json.dumps(out))
print(f"wrote index of {len(out['kind'])} rows; source sha256 {h[:16]}")
