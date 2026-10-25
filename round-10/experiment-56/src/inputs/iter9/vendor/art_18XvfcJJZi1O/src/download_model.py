#!/usr/bin/env python3
"""Download the pinned checkpoint Qwen/Qwen3-8B@b968826d into the shared HF cache (HF_HUB_CACHE is never overridden)."""
import json
import time
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
MID, REV = "Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"
t0 = time.time()
path = snapshot_download(MID, revision=REV, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja",
                                                            "merges.txt", "vocab.json"], max_workers=8)
out = {MID: {"requested_revision": REV, "snapshot_dir_name": Path(path).name, "seconds": round(time.time() - t0, 1)}}
(ROOT / "predictions").mkdir(exist_ok=True)
(ROOT / "predictions" / "model_revisions.json").write_text(json.dumps(out, indent=1))
print(f"{MID}@{Path(path).name} in {time.time() - t0:.0f}s", flush=True)
print("ALL_DONE", flush=True)
