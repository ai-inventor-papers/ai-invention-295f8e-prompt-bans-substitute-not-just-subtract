#!/usr/bin/env python3
"""Download the pinned gemma-3-4b-it and gemma-3-4b-pt snapshots into the run's shared HF cache (HF_HUB_CACHE)."""
import sys
import time

from huggingface_hub import snapshot_download

MODELS = [("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
          ("google/gemma-3-4b-pt", "cc012e0a6d0787b4adcc0fa2c4da74402494554d")]
for repo, rev in MODELS:
    t0 = time.time()
    p = snapshot_download(repo, revision=rev, allow_patterns=["*.json", "*.safetensors", "tokenizer.model"],
                          max_workers=8)
    print(f"{repo}@{rev[:8]} -> {p} in {time.time() - t0:.0f}s", flush=True)
sys.exit(0)
