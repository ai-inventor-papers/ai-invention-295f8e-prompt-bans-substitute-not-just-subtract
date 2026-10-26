#!/usr/bin/env python3
"""Download this artifact's pinned checkpoints into the HF cache (HF_HUB_CACHE is never overridden):
Qwen/Qwen3-8B@b968826d (bf16, every GPU stage) and google/gemma-3-4b-it@093f9f38 (L's opening ranking)."""
import json
import sys
import time
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
WANT = [("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
        ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767")]
only = sys.argv[1:] or [m for m, _ in WANT]
p = ROOT / "predictions" / "model_revisions.json"
out = json.loads(p.read_text()) if p.exists() else {}
for mid, rev in WANT:
    if mid not in only:
        continue
    t0 = time.time()
    path = snapshot_download(mid, revision=rev, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model",
                                                                "*.jinja", "merges.txt", "vocab.json"])
    out[mid] = {"requested_revision": rev, "snapshot_dir_name": Path(path).name, "seconds": round(time.time() - t0, 1)}
    p.write_text(json.dumps(out, indent=1))
    print(f"{mid}@{Path(path).name} in {time.time() - t0:.0f}s", flush=True)
print("ALL_DONE", flush=True)
