#!/usr/bin/env python3
"""S0.3: download the three pinned checkpoints into the run's shared HF cache (HF_HUB_CACHE, never overridden)."""
import json
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
WANT = [("Qwen/Qwen3-8B-FP8", "220b46e3b2180893580a4454f21f22d3ebb187d3"),
        ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
        ("Qwen/Qwen3-8B-Base", "main")]
only = sys.argv[1:] or [m for m, _ in WANT]
out = {}
p = ROOT / "predictions" / "model_revisions.json"
if p.exists():
    out = json.loads(p.read_text())
for mid, rev in WANT:
    if mid not in only:
        continue
    t0 = time.time()
    sha = rev
    if rev == "main":
        sha = HfApi().model_info(mid, revision="main").sha
    path = snapshot_download(mid, revision=sha, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model",
                                                                "*.jinja", "merges.txt", "vocab.json"])
    out[mid] = {"requested_revision": rev, "resolved_sha": sha, "seconds": round(time.time() - t0, 1),
                "snapshot_dir_name": Path(path).name}
    p.write_text(json.dumps(out, indent=1))
    print(f"{mid}@{sha} in {time.time() - t0:.0f}s", flush=True)
print("ALL_DONE", flush=True)
