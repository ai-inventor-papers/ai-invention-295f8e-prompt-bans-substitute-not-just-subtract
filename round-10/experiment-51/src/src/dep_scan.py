#!/usr/bin/env python3
"""S1: scan the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json, all 10 datasets) for bin-packing
textbook implementations (regex 'bin pack|first fit|best fit|worst fit|next fit|harmonic'); write the hits with
record ids and sha256 so priority-expressible ones can join the known corpus."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# the declared dependency art_j3Rm_lr2nzR6 (gen_art_dataset_1) is published as a sibling folder; override with ART_J3RM_LR2NZR6_DIR
DEP = Path(os.environ.get("ART_J3RM_LR2NZR6_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6"))) / "full_data_out.json"
RX = re.compile(r"bin[\s_-]*pack|first[\s_-]*fit|best[\s_-]*fit|worst[\s_-]*fit|next[\s_-]*fit|harmonic", re.I)
NAMED = {"thealgorithms_python", "kodcode_algorithmic", "xlcost_python"}


def main() -> None:
    raw = DEP.read_bytes()
    d = json.loads(raw)
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "file_sha256": hashlib.sha256(raw).hexdigest(),
           "regex": RX.pattern, "per_dataset": {}, "hits": []}
    for ds in d["datasets"]:
        name, n_hit = ds["dataset"], 0
        for i, ex in enumerate(ds["examples"]):
            text = (ex.get("input") or "") + "\n" + (ex.get("output") or "")
            m = RX.findall(text)
            if not m:
                continue
            n_hit += 1
            rid = ex.get("metadata_path") or ex.get("metadata_row_index") or ex.get("metadata_question_id") or str(i)
            out["hits"].append({"dataset": name, "index": i, "record_id": f"{name}:{rid}", "named_dataset": name in NAMED,
                                "matches": sorted({x.lower() for x in m}),
                                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                "input_head": (ex.get("input") or "")[:300], "output": (ex.get("output") or "")[:6000]})
        out["per_dataset"][name] = {"n_examples": len(ds["examples"]), "n_regex_hits": n_hit}
    (ROOT / "data" / "corpus" / "dep_scan" / "dep_scan_hits.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["per_dataset"], indent=1))
    for h in out["hits"]:
        print(h["record_id"], h["matches"], h["input_head"][:120].replace("\n", " "))


if __name__ == "__main__":
    sys.exit(main())
