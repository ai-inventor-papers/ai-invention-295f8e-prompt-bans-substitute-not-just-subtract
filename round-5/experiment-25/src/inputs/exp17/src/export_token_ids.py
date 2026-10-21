#!/usr/bin/env python3
"""Write data/token_ids/all.npz: every generated sample's token ids (concatenated int32 + offsets) keyed like
data/labels.jsonl ('task|template|arm|k'). The same ids are also stored per row in data/samples_raw.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    keys, ids, offs = [], [], [0]
    with open(ROOT / "data" / "samples_raw.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            keys.append(f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}")
            ids.extend(r["token_ids"])
            offs.append(len(ids))
    out = ROOT / "data" / "token_ids"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "all.npz", ids=np.array(ids, np.int32), offsets=np.array(offs, np.int64),
                        keys=np.array(keys))
    print(f"{len(keys)} samples, {len(ids)} tokens -> {out / 'all.npz'}")


if __name__ == "__main__":
    sys.exit(main())
