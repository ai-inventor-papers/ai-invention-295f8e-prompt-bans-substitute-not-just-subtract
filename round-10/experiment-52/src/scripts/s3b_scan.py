#!/usr/bin/env python3
"""S3b: regex scan of the declared dependency (read as data, never executed) for bin-packing implementations."""
import hashlib, json, os, re, sys
from pathlib import Path
# Declared dependency art_j3Rm_lr2nzR6, published as a sibling folder of this artifact (override with the env var).
DEP = Path(os.environ.get("ART_J3RM_LR2NZR6_DIR", Path(__file__).resolve().parent.parent.parent / "art_j3Rm_lr2nzR6")) / "full_data_out.json"
OUT = Path(sys.argv[1])
PAT = re.compile(r"bin.?pack|first.?fit|best.?fit|worst.?fit|next.?fit", re.I)
d = json.loads(DEP.read_text())
hits, counts = [], {}
for ds in d["datasets"]:
    name = ds["dataset"]
    if name not in ("xlcost_python", "thealgorithms_python", "kodcode_algorithmic"):
        continue
    counts[name] = {"records": len(ds["examples"]), "hits": 0}
    for i, ex in enumerate(ds["examples"]):
        txt_in, txt_out = str(ex.get("input", "")), str(ex.get("output", ""))
        m = PAT.findall(txt_in) + PAT.findall(txt_out)
        if m:
            counts[name]["hits"] += 1
            rid = ex.get("metadata_row_index", i)
            hits.append({"dataset": name, "index": i, "record_id": f"{name}:{rid}", "matches": sorted(set(x.lower() for x in m)),
                         "input": txt_in[:3000], "output": txt_out[:6000],
                         "sha256": hashlib.sha256((txt_in + "\n" + txt_out).encode()).hexdigest()})
OUT.write_text(json.dumps({"dependency": "art_j3Rm_lr2nzR6 full_data_out.json", "dep_sha256": hashlib.sha256(DEP.read_bytes()).hexdigest(),
                           "regex": PAT.pattern, "counts": counts, "hits": hits}, indent=1))
print(json.dumps(counts), len(hits))
