#!/usr/bin/env python3
"""Download the two pinned model snapshots into the run's shared HF cache (HF_HUB_CACHE, set by the pipeline)."""
import sys
import time

from huggingface_hub import snapshot_download

MODELS = {
    "qwen": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
    "gemma": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
}
PATTERNS = ["*.json", "*.safetensors", "*.model", "*.txt", "tokenizer*"]

if __name__ == "__main__":
    for key in sys.argv[1:] or list(MODELS):
        rid, rev = MODELS[key]
        t0 = time.time()
        p = snapshot_download(rid, revision=rev, allow_patterns=PATTERNS, max_workers=8)
        print(f"{rid}@{rev} -> {p} in {time.time() - t0:.0f}s", flush=True)
