#!/usr/bin/env python3
"""Download the two pinned Qwen3-8B snapshots into the run's shared HF cache (HF_HUB_CACHE is preset; not overridden)."""
import sys
import time

from huggingface_hub import snapshot_download

MODELS = [("Qwen/Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"),
          ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218")]
which = sys.argv[1:] or ["0", "1"]
for i in which:
    mid, rev = MODELS[int(i)]
    t0 = time.time()
    p = snapshot_download(mid, revision=rev, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
                          max_workers=8)
    print(f"{mid}@{rev[:8]} -> {p} in {time.time() - t0:.0f}s", flush=True)
